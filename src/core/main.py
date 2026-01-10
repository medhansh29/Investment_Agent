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
            try:
                subject, body = EmailTemplates.get_watchdog_content(movers)
                ns = NotificationService()
                ns.send_email(subject, body)
                print("Email notification sent. Please run './run_agent.sh rebalance' to take action.")
            except Exception as e:
                print(f"Failed to send email alert: {e}")
                
        else:
            print("No significant moves detected. Safe.")
            try:
                subject, body = EmailTemplates.get_watchdog_safe_content(positions)
                ns = NotificationService()
                ns.send_email(subject, body)
                print("Daily safety confirmation email sent.")
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

            # Run Optimization
            risk_profile = current_state.get('strategy_settings', {}).get('risk_profile', 'balanced')
            actions, allocation = optimizer.optimize(
                total_value, 
                current_positions_dict, 
                risk_profile=risk_profile,
                market_context=market_context
            )
            
            print("\n--- OPTIMIZED RECOMMENDATIONS ---")
            if not actions:
                print("Portfolio is already balanced!")
            else:
                # Print them nicely
                for ticker, data in actions.items():
                    print(f"{ticker}: {data['action']} {data['qty']} shares (Curr: {data['current']} -> Target: {data['target']})")
                
                # --- STEP 3B: THE AI ---
                print("\n--- AI ANALYSIS (Step 3B) ---")
                from src.integrations.gemini_client import GeminiClient
                
                # We assume Config has GEMINI_API_KEY
                ai = GeminiClient()
                analysis = ai.analyze_rebalance(actions, market_data, current_state, mode=args.mode)
                
                if analysis:
                    print("\n> ADVISOR REPORT:")
                    
                    if "buys" in analysis:
                        print("\n  [BUY RECOMMENDATIONS]")
                        for item in analysis["buys"]:
                            print(f"  * {item['ticker']} ({item['qty']} shares): {item['reason']}")
                            
                    if "sells" in analysis:
                        print("\n  [SELL RECOMMENDATIONS]")
                        for item in analysis["sells"]:
                            print(f"  * {item['ticker']} ({item['qty']} shares): {item['reason']}")
                            
                    if "holds" in analysis:
                        print("\n  [HOLDS / NOTES]")
                        for item in analysis["holds"]:
                            print(f"  * {item['ticker']}: {item['reason']}")
                    
            # --- STEP 4: INTERACTIVE EXECUTION ---
            
            # Initial Recommendations are V1
            final_actions = actions
            universe_list = list(market_data.columns) if 'symbol' not in market_data.columns else list(market_data['symbol'].unique())
            
            # ALWAYS INTERACTIVE
            while True:
                print("\n" + "="*40)
                print("ACTION REQUIRED")
                print("="*40)
                user_choice = input("Do you want to [P]roceed with these trades, [M]odify the plan, or [C]ancel? (P/M/C): ").strip().lower()
                
                if user_choice == 'p':
                    # PROCEED
                    alpaca.execute_trades(final_actions)
                    state_manager.update_last_run()
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
