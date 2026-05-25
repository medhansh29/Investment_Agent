#!/usr/bin/env python3
"""
Script: analyze_performance.py
Purpose: CLI utility to run the Performance Analyzer, output results,
         and generate charts.
"""
import os
import sys
import argparse
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime
from dotenv import load_dotenv

# Add the workspace root to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.config import Config
from src.integrations.alpaca_client import AlpacaClient
from src.utils.performance_analyzer import PerformanceAnalyzer

# Load environment variables
load_dotenv()

def parse_args():
    parser = argparse.ArgumentParser(description="Investment Agent Performance Analyzer")
    parser.add_argument("--use-csv", action="store_true", help="Use local CSV cache instead of calling Alpaca API")
    parser.add_argument("--activities-csv", type=str, default="alpaca_activities.csv", help="Path to activities CSV")
    parser.add_argument("--equity-csv", type=str, default="alpaca_daily_equity.csv", help="Path to daily equity CSV")
    parser.add_argument("--rf-rate", type=float, default=0.04, help="Annual risk-free rate (default 0.04 / 4%%)")
    parser.add_argument("--output-dir", type=str, default="data", help="Directory to save reports and charts")
    return parser.parse_args()

def fetch_data_from_api(rf_rate: float):
    """Fetches activities and history from the Alpaca API."""
    print("Connecting to Alpaca API...")
    if not Config.validate():
        print("Error: Alpaca credentials missing from .env.")
        sys.exit(1)
        
    client = AlpacaClient()
    
    # 1. Fetch activities
    print("Fetching account activities...")
    activities = client.get_account_activities()
    act_list = []
    for act in activities:
        # Convert AccountActivity entity to dict
        act_dict = act.__dict__ if hasattr(act, "__dict__") else dict(act)
        # Handle lazy loading / properties if any
        if hasattr(act, "activity_type"):
            act_dict["activity_type"] = act.activity_type
        act_list.append(act_dict)
    
    activities_df = pd.DataFrame(act_list)
    
    # 2. Fetch portfolio history
    print("Fetching portfolio history...")
    history = client.get_portfolio_history(period="1A", timeframe="1D")
    
    equity_df = pd.DataFrame()
    if history:
        dates = [pd.to_datetime(ts, unit='s').strftime('%Y-%m-%d') for ts in history.timestamp]
        equity_df = pd.DataFrame({
            "Date": dates,
            "Equity": history.equity,
            "Profit_Loss": history.profit_loss,
            "Profit_Loss_Pct": history.profit_loss_pct
        })
    
    # Cache locally
    if not activities_df.empty:
        activities_df.to_csv("alpaca_activities.csv", index=False)
        print("Cached activities to alpaca_activities.csv")
    if not equity_df.empty:
        equity_df.to_csv("alpaca_daily_equity.csv", index=False)
        print("Cached equity to alpaca_daily_equity.csv")
        
    return activities_df, equity_df, client

def fetch_spy_data(client, start_date_str: str, end_date_str: str) -> pd.DataFrame:
    """Fetches SPY historical data for benchmark comparison."""
    print("Fetching SPY benchmark data from Alpaca...")
    try:
        # Fetch data chunk for SPY
        # We need a lookback period to cover start_date to end_date
        d1 = datetime.strptime(start_date_str, "%Y-%m-%d")
        d2 = datetime.strptime(end_date_str, "%Y-%m-%d")
        # To cover start_date up to end_date, the lookback from TODAY must reach start_date
        days_from_today = (datetime.now() - d1).days
        lookback_years = max(0.1, round(days_from_today / 365.0, 2))
        
        bars = client.get_market_data(["SPY"], lookback_years=lookback_years + 0.05)
        if bars.empty:
            return pd.DataFrame()
            
        if isinstance(bars.columns, pd.MultiIndex):
            spy_df = bars["SPY"].copy()
        else:
            spy_df = bars.copy()
            
        spy_df = spy_df.reset_index()
        # Rename timestamp column
        time_col = next((c for c in spy_df.columns if c.lower() in ["timestamp", "time", "date"]), None)
        if time_col:
            spy_df["Date"] = pd.to_datetime(spy_df[time_col]).dt.strftime("%Y-%m-%d")
        
        # Sort and return
        spy_df = spy_df.sort_values("Date").reset_index(drop=True)
        return spy_df[["Date", "close"]]
    except Exception as e:
        print(f"Warning: Failed to fetch SPY benchmark data: {e}")
        return pd.DataFrame()

def generate_chart(equity_df: pd.DataFrame, spy_df: pd.DataFrame, output_path: str):
    """Generates and saves performance chart comparing portfolio equity and SPY, with a drawdown subplot."""
    if equity_df.empty:
        return
    
    # Filter for non-zero equity
    equity_df = equity_df[equity_df["Equity"] > 0].copy()
    if equity_df.empty:
        return
        
    dates = pd.to_datetime(equity_df["Date"])
    equity_vals = equity_df["Equity"].values
    
    # Calculate returns
    initial_equity = equity_vals[0]
    portfolio_pct = (equity_vals - initial_equity) / initial_equity * 100
    
    # Calculate drawdowns
    peaks = np.maximum.accumulate(equity_vals)
    drawdowns = (peaks - equity_vals) / peaks * 100
    
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 7), sharex=True, gridspec_kw={'height_ratios': [2, 1]})
    
    # Subplot 1: Returns
    ax1.plot(dates, portfolio_pct, label="Portfolio Return (%)", color="#27ae60", linewidth=2.5)
    
    if not spy_df.empty:
        # Align SPY dates with portfolio dates
        spy_aligned = spy_df[spy_df["Date"].isin(equity_df["Date"])].copy()
        if not spy_aligned.empty:
            initial_spy = spy_aligned["close"].iloc[0]
            spy_pct = (spy_aligned["close"] - initial_spy) / initial_spy * 100
            spy_dates = pd.to_datetime(spy_aligned["Date"])
            ax1.plot(spy_dates, spy_pct, label="S&P 500 (SPY) (%)", color="#7f8c8d", linestyle="--", linewidth=1.5)
            
    ax1.set_title("Portfolio Cumulative Performance vs S&P 500", fontsize=12, fontweight="bold", pad=10)
    ax1.set_ylabel("Return (%)", fontsize=10)
    ax1.grid(True, linestyle=":", alpha=0.6)
    ax1.legend(loc="upper left")
    
    # Subplot 2: Drawdown
    ax2.fill_between(dates, -drawdowns, 0, label="Drawdown (%)", color="#e74c3c", alpha=0.3)
    ax2.plot(dates, -drawdowns, color="#e74c3c", linewidth=1.0)
    ax2.set_title("Portfolio Drawdown (%)", fontsize=10, fontweight="bold", pad=5)
    ax2.set_xlabel("Date", fontsize=10)
    ax2.set_ylabel("Drawdown (%)", fontsize=10)
    ax2.grid(True, linestyle=":", alpha=0.6)
    
    plt.tight_layout()
    
    # Save chart
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    plt.savefig(output_path, dpi=300)
    print(f"Saved performance chart to {output_path}")
    plt.close()

def generate_trade_analysis_chart(results: dict, output_path: str):
    """Generates and saves trade performance and contribution charts."""
    trades = results.get("completed_trades", [])
    if not trades:
        print("No completed trades to plot for trade analysis.")
        return
        
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 8))
    
    # 1. Individual Trade Returns (%)
    trade_indices = list(range(1, len(trades) + 1))
    trade_pcts = [t["pnl_pct"] * 100 for t in trades]
    trade_symbols = [t["symbol"] for t in trades]
    
    colors = ["#27ae60" if r > 0 else "#e74c3c" for r in trade_pcts]
    
    bars1 = ax1.bar(trade_indices, trade_pcts, color=colors, edgecolor="black", alpha=0.8)
    ax1.axhline(0, color="black", linewidth=1.0, linestyle="-")
    ax1.set_title("Individual Closed Trade Returns (%)", fontsize=12, fontweight="bold", pad=10)
    ax1.set_ylabel("Return (%)", fontsize=10)
    ax1.set_xlabel("Trade #", fontsize=10)
    ax1.set_xticks(trade_indices)
    
    # Add symbol label above/below the bar
    for idx, bar in enumerate(bars1):
        yval = bar.get_height()
        va = 'bottom' if yval >= 0 else 'top'
        offset = 0.5 if yval >= 0 else -0.5
        ax1.text(bar.get_x() + bar.get_width()/2.0, yval + offset, trade_symbols[idx], 
                 ha='center', va=va, fontsize=8, fontweight="bold")
                 
    ax1.grid(True, linestyle=":", alpha=0.6)
    
    # 2. PnL Contribution by Symbol ($)
    ticker_pnl = {}
    for t in trades:
        sym = t["symbol"]
        ticker_pnl[sym] = ticker_pnl.get(sym, 0.0) + t["pnl"]
        
    sorted_pnl = sorted(ticker_pnl.items(), key=lambda x: x[1])
    symbols = [item[0] for item in sorted_pnl]
    pnls = [item[1] for item in sorted_pnl]
    
    bar_colors = ["#27ae60" if p > 0 else "#e74c3c" for p in pnls]
    
    bars2 = ax2.barh(symbols, pnls, color=bar_colors, edgecolor="black", alpha=0.8)
    ax2.axvline(0, color="black", linewidth=1.0)
    ax2.set_title("Realized PnL Contribution by Symbol ($)", fontsize=12, fontweight="bold", pad=10)
    ax2.set_xlabel("PnL ($)", fontsize=10)
    ax2.set_ylabel("Ticker", fontsize=10)
    
    # Add values next to the bars
    for bar in bars2:
        xval = bar.get_width()
        ha = 'left' if xval >= 0 else 'right'
        offset = 2 if xval >= 0 else -2
        ax2.text(xval + offset, bar.get_y() + bar.get_height()/2.0, f"${xval:+.2f}", 
                 ha=ha, va='center', fontsize=8, fontweight="bold")
                 
    ax2.grid(True, linestyle=":", alpha=0.6)
    
    plt.tight_layout()
    
    # Save chart
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    plt.savefig(output_path, dpi=300)
    print(f"Saved trade analysis chart to {output_path}")
    plt.close()


def write_markdown_report(results: dict, output_path: str):
    """Writes a detailed markdown report of the analysis."""
    p_metrics = results["portfolio_metrics"]
    t_stats = results["trade_stats"]
    trades = results["completed_trades"]
    positions = results["open_positions"]
    
    report_content = f"""# Portfolio Performance Report
Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Summary Metrics

| Metric | Value |
| :--- | :--- |
| **Initial Equity** | ${p_metrics['initial_equity']:,.2f} |
| **Final Equity** | ${p_metrics['final_equity']:,.2f} |
| **Net Cash Flow (Deposits)** | ${p_metrics['net_cash_flow']:,.2f} |
| **Absolute PnL** | ${p_metrics['absolute_return']:+,.2f} |
| **Cumulative Return** | **{p_metrics['cumulative_return_pct']:+.2f}%** |
| **Internal Rate of Return (IRR / MWR)** | **{p_metrics['annualized_irr_pct']:+.2f}% (Annualized)** |
| **Annualized Sharpe Ratio** | {p_metrics['sharpe_ratio']:.2f} |
| **Annualized Sortino Ratio** | {p_metrics['sortino_ratio']:.2f} |
| **Maximum Drawdown** | **{p_metrics['max_drawdown_pct']:.2f}%** |
| **Total Fees Paid** | ${results['total_fees']:,.2f} |

---

## Trading Statistics (FIFO Matched Fills)

| Metric | Value |
| :--- | :--- |
| **Total Closed Trades** | {t_stats['total_trades']} |
| **Winning Trades** | {t_stats['winning_trades']} |
| **Losing Trades** | {t_stats['losing_trades']} |
| **Win Rate** | **{t_stats['win_rate_pct']:.2f}%** |
| **Profit Factor** | {t_stats['profit_factor']:.2f} |
| **Average PnL per Trade** | ${t_stats['average_pnl']:+,.2f} ({t_stats['average_pnl_pct']:+.2f}%) |
| **Gross Profit** | ${t_stats['gross_profit']:+,.2f} |
| **Gross Loss** | ${t_stats['gross_loss']:+,.2f} |

---

## Current Open Positions (Calculated from Fills)

| Symbol | Quantity | Average Cost | Current Position Value* |
| :--- | :---: | :--- | :--- |
"""
    if positions:
        for sym, data in positions.items():
            report_content += f"| **{sym}** | {data['qty']:.4f} | ${data['avg_entry_price']:,.2f} | *Calculated from executions* |\n"
    else:
        report_content += "| *None* | | | |\n"

    report_content += "\n---\n\n## Closed Trades History\n\n"
    report_content += "| Trade # | Symbol | Qty | Entry Date | Entry Price | Exit Date | Exit Price | PnL ($) | PnL (%) |\n"
    report_content += "| :--- | :--- | :---: | :--- | :--- | :--- | :--- | :--- | :--- |\n"
    
    if trades:
        for idx, t in enumerate(trades, 1):
            entry_d = t['entry_time'][:10]
            exit_d = t['exit_time'][:10]
            report_content += f"| {idx} | **{t['symbol']}** | {t['qty']:.4f} | {entry_d} | ${t['entry_price']:,.2f} | {exit_d} | ${t['exit_price']:,.2f} | {t['pnl']:+,.2f} | {t['pnl_pct']*100:+.2f}% |\n"
    else:
        report_content += "| *No closed trades found.* | | | | | | | | |\n"
        
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w") as f:
        f.write(report_content)
    print(f"Saved Markdown report to {output_path}")

def print_terminal_dashboard(results: dict):
    """Outputs a clean terminal dashboard."""
    p = results["portfolio_metrics"]
    t = results["trade_stats"]
    
    print("\n" + "="*50)
    print("📈 INVESTMENT AGENT PERFORMANCE DASHBOARD 📈")
    print("="*50)
    print(f"  Initial Equity:        ${p['initial_equity']:,.2f}")
    print(f"  Final Equity:          ${p['final_equity']:,.2f}")
    print(f"  Net Cash Deposits:     ${p['net_cash_flow']:,.2f}")
    print(f"  Absolute P/L:          ${p['absolute_return']:+,.2f}")
    print(f"  Cumulative Return:     {p['cumulative_return_pct']:+.2f}%")
    print(f"  Annualized IRR (MWR):  {p['annualized_irr_pct']:+.2f}%")
    print("-" * 50)
    print(f"  Annual Sharpe Ratio:   {p['sharpe_ratio']:.2f}")
    print(f"  Annual Sortino Ratio:  {p['sortino_ratio']:.2f}")
    print(f"  Maximum Drawdown:      {p['max_drawdown_pct']:.2f}%")
    print(f"  Total Fees Paid:       ${results['total_fees']:,.2f}")
    print("="*50)
    print("📊 TRADING STATISTICS (FIFO matched fills) 📊")
    print("="*50)
    print(f"  Total Closed Trades:   {t['total_trades']}")
    print(f"  Win Rate:              {t['win_rate_pct']:.2f}% ({t['winning_trades']} wins, {t['losing_trades']} losses)")
    print(f"  Profit Factor:         {t['profit_factor']:.2f}")
    print(f"  Average Profit/Trade:  ${t['average_pnl']:+,.2f} ({t['average_pnl_pct']:+.2f}%)")
    print("="*50 + "\n")

def main():
    args = parse_args()
    
    activities_df = pd.DataFrame()
    equity_df = pd.DataFrame()
    client = None
    
    if args.use_csv:
        print(f"Loading data from local CSV cache: {args.activities_csv}, {args.equity_csv}")
        if os.path.exists(args.activities_csv):
            activities_df = pd.read_csv(args.activities_csv)
        else:
            print(f"Error: Activities CSV {args.activities_csv} not found.")
            
        if os.path.exists(args.equity_csv):
            equity_df = pd.read_csv(args.equity_csv)
        else:
            print(f"Error: Equity CSV {args.equity_csv} not found.")
            
        if activities_df.empty or equity_df.empty:
            print("Failed to load CSV data. Exiting.")
            sys.exit(1)
            
        # Try to initialize client to fetch benchmark data, but do not crash if keys missing
        try:
            if Config.validate():
                client = AlpacaClient()
        except Exception:
            pass
    else:
        # Fetch from API
        activities_df, equity_df, client = fetch_data_from_api(args.rf_rate)
        
    # Run analyzer
    analyzer = PerformanceAnalyzer(activities_df, equity_df)
    results = analyzer.run_analysis(risk_free_rate_annual=args.rf_rate)
    
    # Print console output
    print_terminal_dashboard(results)
    
    # Save markdown report
    report_path = os.path.join(args.output_dir, "performance_report.md")
    write_markdown_report(results, report_path)
    
    # Clean equity_df to only include non-zero equity days for plotting and benchmark fetch
    clean_equity_df = pd.DataFrame()
    if not equity_df.empty:
        clean_equity_df = equity_df[equity_df["Equity"] > 0].copy()
        
    # Try benchmark plotting
    spy_df = pd.DataFrame()
    if client and not clean_equity_df.empty:
        start_date = clean_equity_df["Date"].iloc[0]
        end_date = clean_equity_df["Date"].iloc[-1]
        spy_df = fetch_spy_data(client, start_date, end_date)
        
    chart_path = os.path.join(args.output_dir, "performance_chart.png")
    generate_chart(clean_equity_df, spy_df, chart_path)
    
    trade_chart_path = os.path.join(args.output_dir, "trade_analysis_chart.png")
    generate_trade_analysis_chart(results, trade_chart_path)


if __name__ == "__main__":
    main()
