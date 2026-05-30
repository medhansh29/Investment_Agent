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
from src.utils.visualizer import Visualizer
import sys
import argparse
import pandas as pd

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
    
    volatility_trigger = None
    
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

    # Clear stale Limit Orders from last run before fetching settled cash balance
    if args.mode in ['invest', 'rebalance']:
         import time
         alpaca.clear_open_orders()
         time.sleep(2) # Give Alpaca REST API a second to update Buying Power and Unfreeze stocks natively.
    
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
            print("Triggering automatic rebalance...")
            
            # Send Email Alert
            user_name = current_state.get('user_info', {}).get('name', 'User')
            try:
                subject, body = EmailTemplates.get_watchdog_content(movers, user_name)
                ns = NotificationService()
                ns.send_email(subject, body)
                print("Email notification sent.")
            except Exception as e:
                print(f"Failed to send email alert: {e}")
                
            print("\n>>> INITIATING AUTOMATIC REBALANCE DUE TO HIGH VOLATILITY <<<")
            args.mode = 'rebalance'
            args.auto = True
            volatility_trigger = {"asset": movers[0][0], "change": movers[0][1]}
            
            import time
            print("Clearing open orders before rebalance...")
            alpaca.clear_open_orders()
            time.sleep(2)
            
            account = alpaca.get_account()
            if account:
                print(f"Account Status: {account.status}")
                print(f"Buying Power: ${float(account.buying_power):,.2f}")
                print(f"Portfolio Value: ${float(account.portfolio_value):,.2f}")
                
        else:
            print("No significant moves detected. Safe.")
            user_name = current_state.get('user_info', {}).get('name', 'User')
            
            # --- Initiate Daily Pulse Masterclass ---
            from src.integrations.market_intelligence import MarketIntelligence
            from src.integrations.gemini_client import GeminiClient
            import datetime
            import statistics
            
            market_int = MarketIntelligence()
            
            print("\n  [Pulse] Fetching Market Context for Daily Masterclass...")
            market_context = market_int.get_market_context()

            # --- Fetch Benchmark Stats (SPY/QQQ/VIX) ---
            print("  [Pulse] Fetching Benchmark Stats (SPY/QQQ)...")
            benchmark_stats = market_int.get_benchmark_stats(alpaca)

            # --- Compute Portfolio Stats from Current Positions ---
            print("  [Pulse] Computing portfolio performance stats...")
            total_value = float(account.portfolio_value)
            daily_changes = []  # list of weighted daily changes
            position_details = []  # (ticker, daily_pct, market_value)
            positions_pct_snapshot = {}  # {ticker: weight}

            for pos in positions:
                try:
                    pl_pct = float(getattr(pos, 'unrealized_intraday_plpc', 0))
                except:
                    pl_pct = 0.0
                mkt_val = float(pos.qty) * float(pos.current_price)
                weight = mkt_val / total_value if total_value > 0 else 0.0
                daily_changes.append(pl_pct * weight)  # weighted contribution
                position_details.append((pos.symbol, pl_pct * 100, mkt_val))
                positions_pct_snapshot[pos.symbol] = round(weight, 4)

            portfolio_daily_return = sum(daily_changes) * 100  # in %
            daily_vol = statistics.stdev([p[1] for p in position_details]) if len(position_details) > 1 else 0.0

            # Sort for top gainers / losers
            sorted_positions = sorted(position_details, key=lambda x: x[1], reverse=True)
            top_gainers = [(sym, pct) for sym, pct, _ in sorted_positions[:3] if pct > 0]
            top_losers  = [(sym, pct) for sym, pct, _ in sorted_positions[-3:] if pct < 0]

            # Since-last-action stats from snapshot history
            history = state_manager.get_portfolio_history(days=30)
            since_last_action_pct = None
            since_last_action_days = None
            weekly_return_pct = None
            last_action_date = current_state.get('last_run')

            if history:
                oldest_snapshot = history[0]
                old_val = oldest_snapshot.get('portfolio_value', total_value)
                if old_val and old_val > 0:
                    since_last_action_pct = round((total_value - old_val) / old_val * 100, 2)
                    try:
                        from datetime import datetime as dt_cls
                        d1 = dt_cls.strptime(oldest_snapshot['date'], '%Y-%m-%d')
                        d2 = dt_cls.now()
                        since_last_action_days = (d2 - d1).days
                    except:
                        since_last_action_days = len(history)

                # Weekly: use snapshot from 7 days ago if available
                week_snapshots = state_manager.get_portfolio_history(days=7)
                if week_snapshots:
                    wk_val = week_snapshots[0].get('portfolio_value', total_value)
                    if wk_val and wk_val > 0:
                        weekly_return_pct = round((total_value - wk_val) / wk_val * 100, 2)

            portfolio_stats = {
                'daily_return_pct': round(portfolio_daily_return, 2),
                'weekly_return_pct': weekly_return_pct,
                'since_last_action_pct': since_last_action_pct,
                'since_last_action_days': since_last_action_days,
                'top_gainers': top_gainers,
                'top_losers': top_losers,
                'daily_volatility': round(daily_vol, 4),
                'total_value': total_value,
                'composition': positions_pct_snapshot
            }

            # Generate Performance Chart URL (Sparkline)
            chart_url = None
            if history:
                try:
                    # Fetch 30-day SPY history for comparison
                    spy_bars = alpaca.get_market_data(['SPY'], lookback_years=0.1) # ~36 days
                    spy_history = []
                    if not spy_bars.empty:
                        # Alpaca market data usually has MultiIndex columns (Symbol, Metric)
                        if isinstance(spy_bars.columns, pd.MultiIndex):
                            try:
                                spy_history_df = spy_bars['SPY']
                            except:
                                spy_history_df = spy_bars
                        else:
                            spy_history_df = spy_bars

                        for idx, row in spy_history_df.iterrows():
                            # idx is the timestamp
                            spy_history.append({'date': idx.strftime('%Y-%m-%d'), 'price': float(row['close'])})
                    
                    chart_url = Visualizer.generate_performance_chart_url(history, spy_history)
                except Exception as ce:
                    print(f"  [Pulse] Warning: Failed to generate chart: {ce}")

            print(f"  [Stats] Daily Return: {portfolio_daily_return:+.2f}% | Vol: {daily_vol:.3f}")
            print(f"  [Stats] Top Gainers: {top_gainers} | Top Losers: {top_losers}")
            spy_stats = benchmark_stats.get('SPY', {})
            qqq_stats = benchmark_stats.get('QQQ', {})
            if spy_stats:
                print(f"  [Stats] SPY: {spy_stats.get('daily_pct'):+.2f}% | QQQ: {qqq_stats.get('daily_pct', 'N/A')}")

            # --- Targeted Research Injection (Phase 7) ---
            # These are specific causal drivers identified through dynamic research
            targeted_research = [
                {
                    "ticker": "LMT",
                    "sector": "Defense",
                    "findings": "All-time highs in March due to 'Operation Epic Fury' (Iran conflict) and flight-to-safety. Fundamental driver: $194B backlog and quadrupling Precision Strike Missile (PrSM) production. Recent dip is a 'war premium' consolidation."
                },
                {
                    "ticker": "NVDA",
                    "sector": "AI / Tech",
                    "findings": "Blackwell architecture rollout and $1T revenue opportunity announced at GTC 2026. Recent -8% monthly dip is 'sell the news' behavior and macro headwinds, despite 92% GPU market share dominance."
                },
                {
                    "ticker": "LLY",
                    "sector": "Healthcare / GLP-1",
                    "findings": "Positive Phase 3 trials for Retatrutide (weight loss). Recent 6% drop due to HSBC downgrade citing U.S. pricing pressure and competition from Novo Nordisk's oral pills."
                }
            ]

            # --- Honest Portfolio Assessment ---
            ai = GeminiClient()
            pending_suggestions = state_manager.get_pending_rebalance_suggestions()
            
            # Combine general context with specific targeted research
            context_with_research = market_context.copy()
            context_with_research['targeted_research'] = targeted_research

            assessment = ai.generate_portfolio_assessment(
                portfolio_stats, benchmark_stats, context_with_research, pending_suggestions
            )

            # Save rebalance suggestion to state if AI flagged yellow or red
            if assessment:
                flag = assessment.get('assessment_flag', 'green')
                print(f"  [Assessment] Flag: {flag.upper()}")
                
                # Collect all fixes from categories
                all_fixes = []
                cat_list = assessment.get('categorical_assessments') or assessment.get('categories', [])
                for cat in cat_list:
                    fix = cat.get('queued_fix')
                    if fix and isinstance(fix, dict):
                        # Ensure the date is set
                        fix['date'] = datetime.date.today().isoformat()
                        all_fixes.append(fix)
                
                # Also check top-level suggestion if present
                top_suggestion = assessment.get('rebalance_suggestion')
                if top_suggestion and isinstance(top_suggestion, dict):
                    top_suggestion['date'] = datetime.date.today().isoformat()
                    all_fixes.append(top_suggestion)

                for suggestion in all_fixes:
                    state_manager.save_rebalance_suggestion(suggestion)
                    print(f"  [Assessment] Rebalance suggestion saved: {suggestion.get('human_reason', '')}")
                    print(f"  [Assessment] Constraints: {suggestion.get('constraints', {})}")

            # Save today's portfolio snapshot
            state_manager.save_portfolio_snapshot(
                date=datetime.date.today().isoformat(),
                portfolio_value=total_value,
                positions_pct=positions_pct_snapshot
            )
            
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
            pulse_data = ai.generate_daily_pulse(positions_context, raw_headlines, user_name, masterclass_history)
            
            # Attach portfolio stats, benchmark stats, and assessment to pulse_data for email rendering
            if pulse_data is None or not isinstance(pulse_data, dict):
                pulse_data = {}
            # Compatibility mapping for legacy dashboard keys
            flat_benchmarks = benchmark_stats.copy()
            if 'SPY' in benchmark_stats:
                flat_benchmarks['spy_daily_pct'] = benchmark_stats['SPY'].get('daily_pct')
                flat_benchmarks['spy_weekly_pct'] = benchmark_stats['SPY'].get('weekly_pct')
            if 'QQQ' in benchmark_stats:
                flat_benchmarks['qqq_daily_pct'] = benchmark_stats['QQQ'].get('daily_pct')
                flat_benchmarks['qqq_weekly_pct'] = benchmark_stats['QQQ'].get('weekly_pct')
            if 'VIX' in benchmark_stats:
                flat_benchmarks['vix_level'] = benchmark_stats['VIX'].get('level')

            pulse_data['portfolio_stats'] = portfolio_stats
            pulse_data['benchmark_stats'] = flat_benchmarks
            pulse_data['assessment'] = assessment
            pulse_data['chart_url'] = chart_url

            # Save the new topic to persistent memory
            if pulse_data and "masterclass" in pulse_data and "topic" in pulse_data["masterclass"]:
                state_manager.add_masterclass_topic(pulse_data["masterclass"]["topic"])
                
            try:
                if pulse_data and pulse_data.get("market_overview"):
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

            # --- Load Pending Rebalance Suggestions from Memory ---
            constraints = {}
            pending_suggestions = state_manager.get_pending_rebalance_suggestions()
            if pending_suggestions:
                print(f"\n  [Memory] {len(pending_suggestions)} pending corrective suggestion(s) found:")
                for s in pending_suggestions:
                    print(f"    - [{s.get('date', '?')}] {s.get('human_reason', '')}")
                    print(f"      Constraints: {s.get('constraints', {})}")

                # Merge all pending suggestion constraints into the optimizer constraints
                merged_force_include = list(constraints.get('force_include', []))
                merged_force_exclude = list(constraints.get('force_exclude', []))
                merged_weight_floors = dict(constraints.get('force_weight_floor', {}))
                for s in pending_suggestions:
                    c = s.get('constraints', {})
                    for t in c.get('force_include', []):
                        if t not in merged_force_include:
                            merged_force_include.append(t)
                    for t in c.get('force_exclude', []):
                        if t not in merged_force_exclude:
                            merged_force_exclude.append(t)
                    for t, floor in c.get('force_weight_floor', {}).items():
                        # Take the highest floor if there are duplicates
                        merged_weight_floors[t] = max(merged_weight_floors.get(t, 0), floor)
                constraints = {
                    'force_include': merged_force_include,
                    'force_exclude': merged_force_exclude,
                    'force_weight_floor': merged_weight_floors
                }
                print(f"  [Memory] Merged optimizer constraints: {constraints}")

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
                constraints=constraints,
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
                analysis = ai.analyze_rebalance(
                    actions, market_data, current_state,
                    mode=args.mode,
                    volatility_context=volatility_context,
                    volatility_trigger=volatility_trigger,
                    pending_suggestions=pending_suggestions
                )
                
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
                # Use pending_suggestions captured before the run (outer scope)
                _pending = pending_suggestions if 'pending_suggestions' in locals() else []

                try:
                    if volatility_trigger:
                        subject, body = EmailTemplates.get_volatility_rebalance_content(volatility_trigger, market_context, safe_analysis, user_name)
                        ns.send_email(subject, body)
                        print("Rich volatility rebalance email notification sent.")
                    elif args.mode == 'rebalance':
                        subject, body = EmailTemplates.get_rebalance_content(market_context, safe_analysis, user_name, pending_suggestions=_pending)
                        ns.send_email(subject, body)
                        print("Rich rebalance email notification sent.")
                    elif args.mode == 'invest':
                        inv_amount = current_state.get('strategy_settings', {}).get('monthly_investment', 0.0)
                        subject, body = EmailTemplates.get_invest_content(inv_amount, market_context, safe_analysis, user_name, pending_suggestions=_pending)
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
                    # Clear pending suggestions now that they've been acted upon
                    if pending_suggestions:
                        state_manager.clear_rebalance_suggestions()
                
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
                            # Clear pending suggestions now that they've been acted upon
                            if pending_suggestions:
                                state_manager.clear_rebalance_suggestions()
                        
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
