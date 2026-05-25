import unittest
import pandas as pd
import numpy as np
import sys
import os

# Add root directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.utils.performance_analyzer import PerformanceAnalyzer

class TestPerformanceAnalyzer(unittest.TestCase):
    def test_fifo_matching(self):
        # Setup mock activities
        activities_data = [
            {
                "activity_type": "FILL",
                "type": "fill",
                "symbol": "AAPL",
                "side": "buy",
                "qty": 10.0,
                "price": 150.0,
                "transaction_time": "2026-01-01T10:00:00Z"
            },
            {
                "activity_type": "FILL",
                "type": "fill",
                "symbol": "AAPL",
                "side": "buy",
                "qty": 5.0,
                "price": 160.0,
                "transaction_time": "2026-01-02T10:00:00Z"
            },
            {
                "activity_type": "FILL",
                "type": "fill",
                "symbol": "AAPL",
                "side": "sell",
                "qty": 12.0,
                "price": 170.0,
                "transaction_time": "2026-01-03T10:00:00Z"
            }
        ]
        activities_df = pd.DataFrame(activities_data)
        equity_df = pd.DataFrame()
        
        analyzer = PerformanceAnalyzer(activities_df, equity_df)
        completed_trades, open_positions = analyzer.calculate_trade_metrics()
        
        # Verify completed trades
        self.assertEqual(len(completed_trades), 2)
        
        # First match: 10 shares of AAPL bought @ 150, sold @ 170
        trade1 = completed_trades[0]
        self.assertEqual(trade1["symbol"], "AAPL")
        self.assertEqual(trade1["qty"], 10.0)
        self.assertEqual(trade1["entry_price"], 150.0)
        self.assertEqual(trade1["exit_price"], 170.0)
        self.assertEqual(trade1["pnl"], 200.0)  # (170 - 150) * 10
        
        # Second match: 2 shares of AAPL bought @ 160, sold @ 170
        trade2 = completed_trades[1]
        self.assertEqual(trade2["symbol"], "AAPL")
        self.assertEqual(trade2["qty"], 2.0)
        self.assertEqual(trade2["entry_price"], 160.0)
        self.assertEqual(trade2["exit_price"], 170.0)
        self.assertEqual(trade2["pnl"], 20.0)  # (170 - 160) * 2
        
        # Verify open positions
        self.assertIn("AAPL", open_positions)
        self.assertEqual(open_positions["AAPL"]["qty"], 3.0)  # 15 - 12
        self.assertEqual(open_positions["AAPL"]["avg_entry_price"], 160.0)

    def test_irr_solver(self):
        # 10% annual return
        # Initial deposit of 1000 on 2025-01-01, final value of 1100 on 2026-01-01
        cash_flows = [
            ("2025-01-01", -1000.0),
            ("2026-01-01", 1100.0)
        ]
        irr = PerformanceAnalyzer.solve_irr(cash_flows)
        self.assertAlmostEqual(irr, 0.1, places=4)
        
        # Check standard cash flows with multiple deposits
        # Initial 1000, deposit 500 mid year, final value 1600
        cash_flows_2 = [
            ("2025-01-01", -1000.0),
            ("2025-07-02", -500.0),  # half year
            ("2026-01-01", 1600.0)
        ]
        irr_2 = PerformanceAnalyzer.solve_irr(cash_flows_2)
        # Compute exact day fraction (182 days between Jan 1 and Jul 2)
        t2 = 182.0 / 365.0
        t3 = 365.0 / 365.0
        f_val = -1000.0 - 500.0 / ((1 + irr_2) ** t2) + 1600.0 / ((1 + irr_2) ** t3)
        self.assertAlmostEqual(f_val, 0.0, places=4)

    def test_portfolio_metrics(self):
        # Setup mock equity dataframe
        dates = ["2025-08-01", "2025-08-02", "2025-08-03", "2025-08-04", "2025-08-05"]
        equity_values = [100.0, 120.0, 90.0, 110.0, 130.0]
        
        equity_df = pd.DataFrame({
            "Date": dates,
            "Equity": equity_values,
            "Profit_Loss": [0.0] * 5,
            "Profit_Loss_Pct": [0.0] * 5
        })
        activities_df = pd.DataFrame()
        
        analyzer = PerformanceAnalyzer(activities_df, equity_df)
        metrics = analyzer.calculate_portfolio_metrics(risk_free_rate_annual=0.0)
        
        # Max drawdown: Peak 120 -> Trough 90 is (120-90)/120 = 25% drawdown.
        # Next peak is 130 (no drawdown from 130 since it's the final value).
        # So max drawdown should be 25.0%
        self.assertEqual(metrics["max_drawdown_pct"], 25.0)
        self.assertEqual(metrics["initial_equity"], 100.0)
        self.assertEqual(metrics["final_equity"], 130.0)
        self.assertEqual(metrics["absolute_return"], 30.0)
        self.assertEqual(metrics["cumulative_return_pct"], 30.0)

if __name__ == "__main__":
    unittest.main()
