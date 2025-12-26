class EmailTemplates:
    @staticmethod
    def get_watchdog_content(movers):
        """
        Generates content for the Daily Watchdog Alert.
        movers: List of tuples (symbol, percentage_change_float)
        """
        count = len(movers)
        
        # Sort by absolute magnitude of move
        movers.sort(key=lambda x: abs(x[1]), reverse=True)
        
        # summary string
        formatted_movers = [f"- {sym}: {pct*100:+.2f}%" for sym, pct in movers]
        movers_text = "\n".join(formatted_movers)
        
        subject = f"⚠️ [Action Required] Investment Agent: High Volatility Detected ({count} assets)"
        
        body = f"""
Daily Watchdog Report
---------------------
The Investment Agent detected significant market movements in your portfolio (>10% intraday).

Assets Affected:
{movers_text}

Recommended Action:
It is recommended to rebalance your portfolio to maintain your risk profile.

Instruction:
Run the agent in rebalance mode:
> ./run_agent.sh rebalance

Your Investment Agent
"""
        return subject, body.strip()

    @staticmethod
    def get_watchdog_safe_content(positions):
        """Generates content for the Daily Watchdog Safe check."""
        subject = "✅ Investment Agent: Daily Check - All Clear"
        
        holdings_text = "Holdings Summary:\n"
        for pos in positions:
            symbol = pos.symbol
            qty = pos.qty
            price = float(pos.current_price)
            # Try to get intraday change if available, else 0
            try:
                pl_pct = float(getattr(pos, 'unrealized_intraday_plpc', 0)) * 100
            except:
                pl_pct = 0.0
            
            holdings_text += f"- {symbol}: {qty} shares @ ${price:.2f} ({pl_pct:+.2f}%)\n"

        body = f"""
Daily Watchdog Report
---------------------
Daily check completed. No significant market movements detected in your portfolio.

{holdings_text}

Your portfolio is within safe parameters. No action is required.

Your Investment Agent
"""
        return subject, body.strip()

    @staticmethod
    def get_rebalance_content():
        """Generates content for Bi-Weekly Rebalance."""
        subject = "⚖️ Investment Agent: Bi-Weekly Rebalance Reminder"
        body = """
Bi-Weekly Rebalance
-------------------
It is time for your scheduled bi-weekly portfolio rebalance.

Regular rebalancing ensures your portfolio stays aligned with your risk tolerance and strategy settings.

Action Required:
Please run the interactive mode to review and apply rebalancing trades:
> ./run_agent.sh rebalance

Your Investment Agent
"""
        return subject, body.strip()

    @staticmethod
    def get_invest_content():
        """Generates content for Monthly Investment."""
        subject = "💰 Investment Agent: Monthly Investment Day"
        body = """
Monthly Investment Reminder
---------------------------
It is the 1st of the month! Time to deploy your monthly contribution.

Strategy:
Usage of Dollar-Cost Averaging (DCA) helps mitigate timing risk.

Action Required:
Please run the interactive mode to invest your monthly contribution:
> ./run_agent.sh invest

Your Investment Agent
"""
        return subject, body.strip()
