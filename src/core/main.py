"""
Module: main.py
Purpose: The Main Entry Point. Orchestrates the flow:
         1. Initialize State
         2. Authenticate Clients (Alpaca, Gemini)
         3. Fetch Market Data & RAG Context
         4. Optimize Portfolio
         5. Generate AI Advice
"""
from src.core.config import Config
from src.core.state_manager import StateManager
from src.integrations.alpaca_client import AlpacaClient
from src.strategies.portfolio_optimizer import PortfolioOptimizer
from src.utils.notification_service import NotificationService
from src.utils.email_templates import EmailTemplates
import sys
import argparse

def setup_parser():
    parser = argparse.ArgumentParser(description='Investment Agent CLI')
    parser.add_argument('--mode', type=str, default='invest', choices=['daily', 'rebalance', 'invest'], 
                        help='Execution mode: daily (watchdog), rebalance, or invest (full optimization)')
    parser.add_argument('--auto', action='store_true', help='Execute trades automatically without confirmation')
    parser.add_argument('--dry-run', action='store_true', help='Simulate execution and send emails without placing actual trades on Alpaca or saving state.')
    return parser

def main():
    parser = setup_parser()
    args = parser.parse_args()
    
    print("--- Investment Agent Initialization ---")
    print(f"Mode: {args.mode.upper()}")
    
    # 1. Validate environment configuration
    if not Config.validate():
        print("Configuration incomplete. Please check your .env file.")
        sys.exit(1)
        
    # 2. Initialize State Manager
    print("\nInitializing State Manager...")
    try:
        state_manager = StateManager()
        current_state = state_manager.state
        print("State loaded successfully.")
        
        # Test saving
        # state_manager.update_last_run() 
        
    except Exception as e:
        print(f"Failed to initialize state: {e}")
        sys.exit(1)

    print("\nStep 1 (Internal State) verification complete.")

    # 3. Initialize Alpaca Client (Step 2)
    print("\n--- Connecting to Alpaca (Step 2) ---")
    alpaca = AlpacaClient()
    
    # A. Get Account Summary
    account = alpaca.get_account()
    if account:
        print(f"Account Status: {account.status}")
        print(f"Buying Power: ${float(account.buying_power):,.2f}")
        print(f"Portfolio Value: ${float(account.portfolio_value):,.2f}")
    
    # B. Get Positions
    positions = alpaca.get_positions()
    print(f"Current Positions: {len(positions)}")
    for pos in positions:
        print(f"  - {pos.symbol}: {pos.qty} shares @ ${float(pos.current_price):.2f}")
        
    # --- MODE: DAILY WATCHDOG ---
    # --- MODE: DAILY WATCHDOG ---
    if args.mode == 'daily':
        print("\n--- DAILY WATCHDOG CHECK ---")
        movers = []
        for pos in positions:
            # Check intraday P/L
            try:
                pl_pct = float(getattr(pos, 'unrealized_intraday_plpc', 0))
            except:
                pl_pct = 0.0
            
            if abs(pl_pct) > 0.10: # 10% move threshold
                movers.append((pos.symbol, pl_pct))
                
        if movers:
            # Sort by absolute magnitude of move
            movers.sort(key=lambda x: abs(x[1]), reverse=True)
            
            print("\n!!! SIGNIFICANT MARKET MOVES DETECTED !!!")
            for sym, pct in movers:
                print(f"{sym}: {pct*100:+.2f}%")
            print("Suggest running: python3 main.py --mode rebalance")
            
            # Send Email Alert
            user_name = current_state.get('user_info', {}).get('name', 'User')
            try:
                subject, body = EmailTemplates.get_watchdog_content(movers, user_name)
                ns = NotificationService()
                ns.send_email(subject, body)
                print("Email notification sent. Please run './run_agent.sh rebalance' to take action.")
            except Exception as e:
                print(f"Failed to send email alert: {e}")
                
        else:
            print("No significant moves detected. Safe.")
            user_name = current_state.get('user_info', {}).get('name', 'User')
            
            # --- Initiate Daily Pulse Masterclass ---
            from src.integrations.market_intelligence import MarketIntelligence
            from src.integrations.gemini_client import GeminiClient
            
            market_int = MarketIntelligence()
            
            print("\n  [Pulse] Fetching Market Context for Daily Masterclass...")
            # We don't need the full Gemini reasoning here, just the raw headlines for Input 2
            # but we use get_market_context() anyway caching the 'reasoning'
            market_context = market_int.get_market_context() 
            
            # Extract raw RSS lines directly from the sources
            all_headlines = []
            for src in market_int.sources:
                all_headlines.extend(market_int._fetch_rss(src))
            unique_headlines = {item['title']: item for item in all_headlines}.values()
            raw_headlines = list(unique_headlines)[:40]

            positions_context = ""
            for pos in positions:
                try:
                    pl_pct = float(getattr(pos, 'unrealized_intraday_plpc', 0)) * 100
                except:
                    pl_pct = 0.0
                positions_context += f"- {pos.symbol}: Current Price ${float(pos.current_price):.2f} (Daily Change: {pl_pct:+.2f}%)\n"

            masterclass_history = state_manager.get_masterclass_history()
            ai = GeminiClient()
            pulse_data = ai.generate_daily_pulse(positions_context, raw_headlines, user_name, masterclass_history)
            
            # Save the new topic to persistent memory
            if pulse_data and "masterclass" in pulse_data and "topic" in pulse_data["masterclass"]:
                state_manager.add_masterclass_topic(pulse_data["masterclass"]["topic"])
                
            try:
                if pulse_data:
                    subject, body = EmailTemplates.get_daily_pulse_content(pulse_data)
                else:
                    # Fallback to simple safe text if Gemini fails
                    subject, body = EmailTemplates.get_watchdog_safe_content(positions, user_name)
                    
                ns = NotificationService()
                ns.send_email(subject, body)
                print("Daily Pulse Masterclass email sent.")
            except Exception as e:
                print(f"Failed to send email: {e}")
        
        # Update last run time
        state_manager.update_last_run()
        sys.exit(0) # Daily check done

    # C. Fetch Market Data (with Cache)
    universe = state_manager.get_universe()
    if universe:
        print(f"\nFetching Market Data for {len(universe)} stocks...")
        
        market_data = alpaca.get_market_data(universe)
        
        if not market_data.empty:
            print(f"Market Data Loaded. Rows: {len(market_data)}")
            
            # --- STEP 3: THE MATH ---
            # Instantiate Optimizer
            optimizer = PortfolioOptimizer(market_data)
            
            # Prepare Inputs
            # 1. Total Portfolio Value (Cash + Equity)
            total_value = float(account.portfolio_value)
            
            # CAPITAL INJECTION FOR INVESTMENT MODE
            if args.mode == 'invest':
                monthly_inv = current_state.get('strategy_settings', {}).get('monthly_investment', 0.0)
                if monthly_inv > 0:
                    print(f"\n>>> INVESTMENT MODE: Injecting ${monthly_inv:,.2f} capital for optimization.")
                    total_value += monthly_inv
                else:
                    print("\n>>> WARNING: Investment mode selected but 'monthly_investment' is 0 in user_state.json.")
            
            # 2. Current Positions {Symbol: Qty}
            # Convert Alpaca Position objects to a simple dict
            current_positions_dict = {p.symbol: int(p.qty) for p in positions}
            
            # --- RAG: Market Intelligence ---
            from src.integrations.market_intelligence import MarketIntelligence
            market_int = MarketIntelligence()
            market_context = market_int.get_market_context()

            # Display RAG Report
            print("\n" + "="*40)
            print("🌍 GLOBAL MARKET INTELLIGENCE REPORT")
            print("="*40)
            print(f"• Conflict Score:       {market_context.get('conflict_score', 'N/A')}/10")
            print(f"• Inflation Score:      {market_context.get('inflation_score', 'N/A')}/10")
            print(f"• Econ Instability:     {market_context.get('economic_instability_score', 'N/A')}/10")
            print("-" * 40)
            print(f"Analyst Insight: {market_context.get('reasoning', 'No insight available.')}")
            print("="*40 + "\n")

            # --- Extract Volatility Context ---
            # Build volatility context from current positions
            volatility_context = {}
            for pos in positions:
                try:
                    intraday_change = float(getattr(pos, 'unrealized_intraday_plpc', 0))
                    volatility_context[pos.symbol] = intraday_change
                except:
                    volatility_context[pos.symbol] = 0.0

            # Run Optimization
            risk_profile = current_state.get('strategy_settings', {}).get('risk_profile', 'balanced')
            actions, allocation = optimizer.optimize(
                total_value, 
                current_positions_dict, 
                risk_profile=risk_profile,
                market_context=market_context,
                volatility_context=volatility_context
            )
            
            print("\n--- OPTIMIZED RECOMMENDATIONS ---")
            if not actions:
                print("Portfolio is already balanced!")
            else:
                # Print them nicely
                for ticker, data in actions.items():
                    action_str = f"LIMIT {data['action']}"
                    limit_str = f" @ ${data.get('limit_price', 0.0):.2f}" if 'limit_price' in data else ""
                    print(f"{ticker}: {action_str} {data['qty']} shares{limit_str} (Curr: {data['current']} -> Target: {data['target']})")
                
                # --- STEP 3B: THE AI ---
                print("\n--- AI ANALYSIS (Step 3B) ---")
                from src.integrations.gemini_client import GeminiClient
                
                # We assume Config has GEMINI_API_KEY
                ai = GeminiClient()
                analysis = ai.analyze_rebalance(actions, market_data, current_state, mode=args.mode, volatility_context=volatility_context)
                
                if analysis:
                    print("\n> ADVISOR REPORT:")
                    
                    if "buys" in analysis:
                        print("\n  [BUY RECOMMENDATIONS]")
                        for item in analysis["buys"]:
                            header = item.get('header', f"**{item.get('ticker', '')} ({item.get('qty', '')} shares):**")
                            print(f"  * {header} {item.get('reason', '')}")
                            
                    if "sells" in analysis:
                        print("\n  [SELL RECOMMENDATIONS]")
                        for item in analysis["sells"]:
                            header = item.get('header', f"**{item.get('ticker', '')} ({item.get('qty', '')} shares):**")
                            print(f"  * {header} {item.get('reason', '')}")
                            
                    if "holds" in analysis:
                        print("\n  [HOLDS / NOTES]")
                        for item in analysis["holds"]:
                            assets = item.get('assets', item.get('ticker', ''))
                            print(f"  * {assets}: {item.get('reason', '')}")
                    
            # --- STEP 4: INTERACTIVE OR AUTOMATED EXECUTION ---
            
            # Initial Recommendations are V1
            final_actions = actions
            universe_list = list(market_data.columns) if 'symbol' not in market_data.columns else list(market_data['symbol'].unique())
            
            def _send_rich_notification(final_actions_used):
                ns = NotificationService()
                
                # Default empty if no AI analysis was returned
                safe_analysis = analysis if 'analysis' in locals() and analysis else {}
                user_name = current_state.get('user_info', {}).get('name', 'User')

                try:
                    if args.mode == 'rebalance':
                        subject, body = EmailTemplates.get_rebalance_content(market_context, safe_analysis, user_name)
                        ns.send_email(subject, body)
                        print("Rich rebalance email notification sent.")
                    elif args.mode == 'invest':
                        inv_amount = current_state.get('strategy_settings', {}).get('monthly_investment', 0.0)
                        subject, body = EmailTemplates.get_invest_content(inv_amount, market_context, safe_analysis, user_name)
                        ns.send_email(subject, body)
                        print("Rich investment email notification sent.")
                except Exception as e:
                    print(f"Warning: Failed to send rich email notification: {e}")

            if args.auto:
                print("\n" + "="*40)
                print("AUTOMATED EXECUTION ACTIVE (--auto)")
                print("="*40)
                
                if args.dry_run:
                    print(">>> DRY RUN ACTIVE: Simulating trades and sending notification but NO actions will be executed on Alpaca.")
                    _send_rich_notification(final_actions)
                else:
                    print("Proceeding with trades automatically...")
                    alpaca.execute_trades(final_actions)
                    state_manager.update_last_run()
                    _send_rich_notification(final_actions)
                
                print("\n--- DONE. Automated Investment Agent Finished. ---")
            else:
                # ALWAYS INTERACTIVE
                while True:
                    print("\n" + "="*40)
                    print("ACTION REQUIRED")
                    print("="*40)
                    user_choice = input("Do you want to [P]roceed with these trades, [M]odify the plan, or [C]ancel? (P/M/C): ").strip().lower()
                    
                    if user_choice == 'p':
                        # PROCEED
                        if args.dry_run:
                            print(">>> DRY RUN ACTIVE: Simulating trades and sending notification but NO actions will be executed on Alpaca.")
                            _send_rich_notification(final_actions)
                        else:
                            alpaca.execute_trades(final_actions)
                            state_manager.update_last_run()
                            _send_rich_notification(final_actions)
                        
                        print("\n--- DONE. Investment Agent Finished. ---")
                        break
                        
                    elif user_choice == 'm':
                        # MODIFY
                        feedback = input("\nEnter your feedback (e.g., 'I want to invest in NVDA and not in GE'): ")
                        print("\n>>> Analyzing feedback with Gemini...")
                        
                        constraints = ai.interpret_feedback(feedback, universe_list)
                        
                        if constraints.get('force_include') or constraints.get('force_exclude'):
                            print(f">>> Re-running Optimization with Constraints: {constraints}")
                            actions_v2, _ = optimizer.optimize(total_value, current_positions_dict, risk_profile=risk_profile, constraints=constraints)
                            
                            print("\n--- MODIFIED RECOMMENDATIONS ---")
                            if not actions_v2:
                                 print("Portfolio is balanced.")
                            else:
                                for ticker, data in actions_v2.items():
                                    print(f"{ticker}: {data['action']} {data['qty']} shares")
                            
                            final_actions = actions_v2
                        else:
                            print(">>> No actionable constraints found. Plan unchanged.")
                            
                    elif user_choice == 'c':
                        # CANCEL
                        print("Operation Cancelled.")
                        break
                    else:
                        print("Invalid input. Please enter P, M, or C.")

        else:
            print("No market data returned.")
    else:
        print("Universe is empty in user_state.json")

if __name__ == "__main__":
    main()
