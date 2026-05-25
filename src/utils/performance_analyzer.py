"""
Module: performance_analyzer.py
Purpose: Computes trade-level and portfolio-level performance metrics
         from Alpaca account activities and daily equity history.
"""
import pandas as pd
import numpy as np
import datetime
from typing import List, Dict, Tuple, Optional

class PerformanceAnalyzer:
    def __init__(self, activities_df: pd.DataFrame, equity_df: pd.DataFrame):
        """
        activities_df: DataFrame of account activities (FILL, FEE, TRANS)
        equity_df: DataFrame of daily portfolio history (Date, Equity, Profit_Loss, Profit_Loss_Pct)
        """
        self.activities_df = activities_df
        self.equity_df = equity_df
        
        # Clean data
        self._clean_data()

    def _clean_data(self):
        # Clean equity data (filter out zeros and sort)
        if not self.equity_df.empty:
            # Ensure Date is string or datetime
            if "Date" in self.equity_df.columns:
                self.equity_df = self.equity_df.copy()
                self.equity_df["Date"] = pd.to_datetime(self.equity_df["Date"]).dt.strftime("%Y-%m-%d")
                self.equity_df = self.equity_df.sort_values("Date").reset_index(drop=True)
                # Filter out zero equity days (inactive periods)
                self.equity_df = self.equity_df[self.equity_df["Equity"] > 0].reset_index(drop=True)

        # Clean activities data
        if not self.activities_df.empty:
            self.activities_df = self.activities_df.copy()
            # Handle column names if they are slightly different (e.g. transaction_time vs transactionTime)
            time_col = next((c for c in self.activities_df.columns if c.lower() in ["transaction_time", "transactiontime", "time"]), None)
            if time_col:
                self.activities_df["transaction_time"] = pd.to_datetime(self.activities_df[time_col])
                # Create a date string column for daily groupings
                self.activities_df["date"] = self.activities_df["transaction_time"].dt.strftime("%Y-%m-%d")
            else:
                self.activities_df["transaction_time"] = pd.to_datetime(datetime.date.today())
                self.activities_df["date"] = datetime.date.today().isoformat()

            # Ensure numeric values
            for col in ["price", "qty", "net_amount"]:
                if col in self.activities_df.columns:
                    self.activities_df[col] = pd.to_numeric(self.activities_df[col], errors="coerce").fillna(0.0)

            # Sort chronologically
            self.activities_df = self.activities_df.sort_values("transaction_time").reset_index(drop=True)

    def calculate_trade_metrics(self) -> Tuple[List[Dict], Dict]:
        """
        Runs FIFO matching on FILL activities to group buys/sells into completed trades.
        
        Returns:
            - List of dicts representing completed trades.
            - Dict of remaining open positions and their average cost.
        """
        if self.activities_df.empty:
            return [], {}

        # Filter for fill activities
        fill_types = ["fill", "partial_fill"]
        fills = self.activities_df[
            (self.activities_df["activity_type"] == "FILL") | 
            (self.activities_df["type"].str.lower().isin(fill_types))
        ].copy()

        if fills.empty:
            return [], {}

        completed_trades = []
        queues = {}  # symbol -> list of dicts (buy fills)

        for _, fill in fills.iterrows():
            symbol = fill.get("symbol")
            side = str(fill.get("side", "")).lower()
            qty = float(fill.get("qty", 0))
            price = float(fill.get("price", 0))
            time_val = str(fill.get("transaction_time"))

            if not symbol or qty <= 0:
                continue

            if symbol not in queues:
                queues[symbol] = []

            if side == "buy":
                # Add buy fill to queue
                queues[symbol].append({
                    "qty": qty,
                    "price": price,
                    "time": time_val
                })
            elif side == "sell":
                # Match sell fill against buy queue (FIFO)
                sell_qty_remaining = qty
                while sell_qty_remaining > 0 and queues[symbol]:
                    oldest_buy = queues[symbol][0]
                    buy_qty = oldest_buy["qty"]
                    buy_price = oldest_buy["price"]
                    buy_time = oldest_buy["time"]

                    matched_qty = min(buy_qty, sell_qty_remaining)

                    pnl = (price - buy_price) * matched_qty
                    pnl_pct = (price - buy_price) / buy_price if buy_price > 0 else 0.0

                    completed_trades.append({
                        "symbol": symbol,
                        "qty": matched_qty,
                        "entry_time": buy_time,
                        "exit_time": time_val,
                        "entry_price": buy_price,
                        "exit_price": price,
                        "pnl": round(pnl, 2),
                        "pnl_pct": round(pnl_pct, 4)
                    })

                    # Update remaining quantities
                    sell_qty_remaining -= matched_qty
                    oldest_buy["qty"] -= matched_qty

                    if oldest_buy["qty"] <= 0:
                        queues[symbol].pop(0)

        # Remaining open positions
        open_positions = {}
        for symbol, buy_list in queues.items():
            total_qty = sum(b["qty"] for b in buy_list)
            if total_qty > 0:
                weighted_price = sum(b["price"] * b["qty"] for b in buy_list) / total_qty
                open_positions[symbol] = {
                    "qty": round(total_qty, 4),
                    "avg_entry_price": round(weighted_price, 4)
                }

        return completed_trades, open_positions

    @staticmethod
    def solve_irr(cash_flows: List[Tuple[str, float]], max_iters: int = 1000, tol: float = 1e-6) -> float:
        """
        Solves for the annualized Internal Rate of Return (IRR) using Newton-Raphson
        with a binary search fallback.
        
        cash_flows: List of (date_str, amount) where date_str is 'YYYY-MM-DD'.
        Negative amount represents capital investment (deposits).
        Positive amount represents withdrawals/liquidations.
        """
        if not cash_flows or len(cash_flows) < 2:
            return 0.0

        # Sort chronologically
        sorted_cf = sorted(cash_flows, key=lambda x: x[0])
        start_date = datetime.datetime.strptime(sorted_cf[0][0], "%Y-%m-%d")

        flows = []
        for date_str, amount in sorted_cf:
            d = datetime.datetime.strptime(date_str, "%Y-%m-%d")
            days = (d - start_date).days
            flows.append((days / 365.0, amount))

        # Newton-Raphson
        r = 0.1
        for _ in range(max_iters):
            f_val = 0.0
            df_val = 0.0
            for t, amount in flows:
                if r <= -0.99:
                    r = -0.95
                denom = (1 + r) ** t
                f_val += amount / denom
                df_val += -t * amount / ((1 + r) ** (t + 1))

            if abs(df_val) < 1e-12:
                break

            delta = f_val / df_val
            r_new = r - delta

            if abs(r_new - r) < tol:
                # Sanity check
                if -0.99 < r_new < 10.0:
                    return r_new

            r = r_new

        # Binary Search Fallback
        low = -0.99
        high = 10.0
        for _ in range(100):
            mid = (low + high) / 2.0
            f_val = 0.0
            for t, amount in flows:
                f_val += amount / ((1 + mid) ** t)

            if abs(f_val) < tol:
                return mid
            if f_val > 0:
                low = mid
            else:
                high = mid

        return (low + high) / 2.0

    def calculate_portfolio_metrics(self, risk_free_rate_annual: float = 0.04) -> Dict:
        """
        Calculates portfolio returns, Sharpe ratio, Sortino ratio, Drawdowns, and IRR.
        """
        metrics = {
            "initial_equity": 0.0,
            "final_equity": 0.0,
            "net_cash_flow": 0.0,
            "absolute_return": 0.0,
            "cumulative_return_pct": 0.0,
            "annualized_irr_pct": 0.0,
            "sharpe_ratio": 0.0,
            "sortino_ratio": 0.0,
            "max_drawdown_pct": 0.0,
            "volatility_daily": 0.0
        }

        if self.equity_df.empty:
            return metrics

        # Equity metrics
        initial_equity = float(self.equity_df["Equity"].iloc[0])
        final_equity = float(self.equity_df["Equity"].iloc[-1])
        start_date = self.equity_df["Date"].iloc[0]
        end_date = self.equity_df["Date"].iloc[-1]

        metrics["initial_equity"] = initial_equity
        metrics["final_equity"] = final_equity

        # Determine transfers/deposits
        # In a real account, we fetch 'TRANS' activities.
        # If no TRANS activity exists, we assume the initial equity is the sole deposit.
        cash_flows = []
        
        # 1. Add initial portfolio value as a deposit (outflow from user to portfolio)
        cash_flows.append((start_date, -initial_equity))

        # 2. Add transfers from activities
        if not self.activities_df.empty:
            transfers = self.activities_df[
                (self.activities_df["activity_type"] == "TRANS") | 
                (self.activities_df["type"].str.lower() == "transfer")
            ]
            for _, row in transfers.iterrows():
                date_str = row.get("date")
                amount = float(row.get("net_amount", 0))
                # net_amount is positive for deposits on Alpaca, which we invert for cash flow perspective
                # (cash flow from user to portfolio is negative)
                if amount != 0:
                    cash_flows.append((date_str, -amount))
                    metrics["net_cash_flow"] += amount

        # 3. Add final portfolio value as a liquidation (inflow from portfolio back to user)
        cash_flows.append((end_date, final_equity))

        # Calculate IRR
        irr = self.solve_irr(cash_flows)
        metrics["annualized_irr_pct"] = round(irr * 100, 2)

        # Calculate returns
        metrics["absolute_return"] = round(final_equity - initial_equity - metrics["net_cash_flow"], 2)
        total_invested = initial_equity + metrics["net_cash_flow"]
        if total_invested > 0:
            metrics["cumulative_return_pct"] = round((metrics["absolute_return"] / total_invested) * 100, 2)

        # Daily returns & Sharpe/Sortino
        if len(self.equity_df) > 1:
            daily_series = self.equity_df["Equity"].values
            daily_returns = np.diff(daily_series) / daily_series[:-1]
            
            # Filter out extreme anomalies if any (like 0 equity days)
            daily_returns = daily_returns[~np.isnan(daily_returns) & ~np.isinf(daily_returns)]
            
            if len(daily_returns) > 0:
                mean_return = np.mean(daily_returns)
                std_return = np.std(daily_returns)
                metrics["volatility_daily"] = round(std_return, 6)

                # Risk-free rate adjusted to daily
                rf_daily = risk_free_rate_annual / 252.0

                # Sharpe Ratio
                if std_return > 0:
                    metrics["sharpe_ratio"] = round(np.sqrt(252) * (mean_return - rf_daily) / std_return, 2)
                
                # Sortino Ratio
                downside_returns = daily_returns[daily_returns < rf_daily]
                if len(downside_returns) > 0:
                    downside_std = np.std(downside_returns)
                    if downside_std > 0:
                        metrics["sortino_ratio"] = round(np.sqrt(252) * (mean_return - rf_daily) / downside_std, 2)
                else:
                    metrics["sortino_ratio"] = metrics["sharpe_ratio"]

            # Maximum Drawdown calculation
            peaks = np.maximum.accumulate(daily_series)
            drawdowns = (peaks - daily_series) / peaks
            metrics["max_drawdown_pct"] = round(np.max(drawdowns) * 100, 2)

        return metrics

    def run_analysis(self, risk_free_rate_annual: float = 0.04) -> Dict:
        """
        Runs both trade-level and portfolio-level calculations.
        """
        portfolio_metrics = self.calculate_portfolio_metrics(risk_free_rate_annual)
        completed_trades, open_positions = self.calculate_trade_metrics()

        # Aggregate trade stats
        trade_stats = {
            "total_trades": len(completed_trades),
            "winning_trades": 0,
            "losing_trades": 0,
            "win_rate_pct": 0.0,
            "gross_profit": 0.0,
            "gross_loss": 0.0,
            "profit_factor": 0.0,
            "average_pnl": 0.0,
            "average_pnl_pct": 0.0
        }

        if completed_trades:
            pnls = [t["pnl"] for t in completed_trades]
            pnl_pcts = [t["pnl_pct"] for t in completed_trades]

            trade_stats["winning_trades"] = sum(1 for p in pnls if p > 0)
            trade_stats["losing_trades"] = sum(1 for p in pnls if p <= 0)
            trade_stats["win_rate_pct"] = round((trade_stats["winning_trades"] / len(completed_trades)) * 100, 2)
            
            trade_stats["gross_profit"] = round(sum(p for p in pnls if p > 0), 2)
            trade_stats["gross_loss"] = round(sum(p for p in pnls if p < 0), 2)
            
            abs_gross_loss = abs(trade_stats["gross_loss"])
            if abs_gross_loss > 0:
                trade_stats["profit_factor"] = round(trade_stats["gross_profit"] / abs_gross_loss, 2)
            else:
                trade_stats["profit_factor"] = float("inf") if trade_stats["gross_profit"] > 0 else 1.0

            trade_stats["average_pnl"] = round(np.mean(pnls), 2)
            trade_stats["average_pnl_pct"] = round(np.mean(pnl_pcts) * 100, 2)

        # Calculate fees details
        fees_total = 0.0
        if not self.activities_df.empty:
            fees = self.activities_df[
                (self.activities_df["activity_type"] == "FEE") | 
                (self.activities_df["type"].str.lower() == "fee")
            ]
            fees_total = round(float(fees["net_amount"].sum()), 2)

        return {
            "portfolio_metrics": portfolio_metrics,
            "trade_stats": trade_stats,
            "completed_trades": completed_trades,
            "open_positions": open_positions,
            "total_fees": fees_total
        }
