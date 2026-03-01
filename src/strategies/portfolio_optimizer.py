import pandas as pd
"""
Module: portfolio_optimizer.py
Purpose: Math Engine. Uses PyPortfolioOpt and 'Safe Fortress' logic to 
         calculate optimal asset allocation based on Risk Profile.
"""
from pypfopt import EfficientFrontier, risk_models, expected_returns
from pypfopt.discrete_allocation import DiscreteAllocation, get_latest_prices
from src.core.config import Config

class PortfolioOptimizer:
    def __init__(self, market_data_df):
        """
        Initializes the optimizer with raw market data.
        market_data_df: DataFrame with 'symbol' and 'close' columns (or 'close' per symbol)
        """
        self.prices = self._prepare_prices(market_data_df)

    def _prepare_prices(self, df):
        """
        Converts the fetched data (long format) into a pivot table of closing prices (wide format).
        Index=Date, Columns=Symbols.
        """
        # If already wide format (columns are tickers), return as is
        # But our Alpaca fetch returns long format (check main.py output)
        if 'symbol' in df.columns and 'close' in df.columns:
            pivot = df.pivot_table(index='timestamp', columns='symbol', values='close')
            return pivot
        return df

    def optimize(self, current_portfolio_value, current_positions=None, risk_profile="balanced", constraints=None, market_context=None, volatility_context=None):
        """
        Calculates the Efficient Frontier based on risk profile and user constraints.
        
        risk_profile: 'high_growth', 'balanced', or 'conservative'.
        constraints: Dict {'force_include': ['TICKER'], 'force_exclude': ['TICKER']}
        market_context: Dict {'conflict_score': 8, 'inflation_score': 4} (From RAG)
        volatility_context: Dict {symbol: intraday_pct_change} (From Alpaca positions)
        """
        if current_positions is None:
            current_positions = {}
        if constraints is None:
            constraints = {}
        if market_context is None:
            market_context = {}
        if volatility_context is None:
            volatility_context = {}

        print(f"\n--- Running Portfolio Optimization (Strategy: {risk_profile}) ---")
        if constraints:
            print(f"Applying Constraints: {constraints}")
        
        # 1. Expected Returns (mu)
        mu = expected_returns.mean_historical_return(self.prices)
        
        # 2. Risk Model (S)
        S = risk_models.sample_cov(self.prices)
        
        # 3. Efficient Frontier
        # Add diversification constraint: Max 20% per stock
        ef = EfficientFrontier(mu, S, weight_bounds=(0, 0.20))
        
        # Apple RAG / Thesis Constraints
        # Logic: If Risk Score > Threshold, FORCE HOLD (New >= 0.95 * Current)
        from config import Config
        latest_prices = get_latest_prices(self.prices)
        tickers_list = list(self.prices.columns)
        
        if market_context:
            print("--- RAG: Analyzing Thesis Constraints ---")
            for ticker, rule in Config.THESIS_CONSTRAINTS.items():
                if ticker in current_positions and ticker in tickers_list:
                    current_score = market_context.get(rule['risk_type'], 0)
                    threshold = rule['threshold']
                    
                    if current_score >= threshold:
                        # RAG Logic: Thesis is ACTIVE.
                        # Rule: Do NOT Sell. Target Weight must be >= Current Weight.
                        
                        curr_val = current_positions[ticker] * latest_prices[ticker]
                        curr_weight = curr_val / current_portfolio_value
                        
                        # Add Constraint: w[i] >= curr_weight
                        # We use a tiny epsilon (0.99) to avoid floating point infeasibility if full lock is too tight,
                        # but effectively this blocks selling.
                        floor = curr_weight * 0.999 
                        
                        idx = tickers_list.index(ticker)
                        ef.add_constraint(lambda w, i=idx, f=floor: w[i] >= f)
                        
                        print(f"  [Thesis PROTECTION] {ticker} ({rule['role']})")
                        print(f"   -> {rule['risk_type']} is {current_score}/10 (High). Forced Hold.")

        # Apply User-Defined constraints (Feedback loops)
        # ... existing logic ...
        
        tickers_list = list(self.prices.columns)
        
        # Force Exclude: Weight = 0
        for ticker in constraints.get('force_exclude', []):
            if ticker in tickers_list:
                idx = tickers_list.index(ticker)
                ef.add_constraint(lambda w, i=idx: w[i] == 0)
        
        # Force Include: Weight >= 5% (Example floor)
        for ticker in constraints.get('force_include', []):
             if ticker in tickers_list:
                idx = tickers_list.index(ticker)
                ef.add_constraint(lambda w, i=idx: w[i] >= 0.05)
        
        try:
            # STRATEGY SELECTION (4 Profiles)
            # Normalize profile string
            profile = risk_profile.lower().replace(" ", "_")
            if profile == "high_growth": profile = "speculative" # Alias
            
            print(f"--- Strategy Mapper: Using logic for '{profile}' ---")
            
            if profile == "conservative":
                # 1. Conservative: Fortress Mode
                # Revert to min_volatility but with STRICT constraints to prevent dumping safe assets.
                print("--- CONSERVATIVE MODE: Applying Fortress Constraints ---")
                
                # A. Protect Inflation Hedges & Core Staples (The "Fortress" List)
                # We want to hold at least 90% of our existing position in these to prevent "naked" inflation exposure.
                fortress_assets = [
                    'KO', 'PG', 'JNJ', 'MCD', 'PEP', 'COST', 'XOM', 'CVX', 'LMT', 'RTX',
                    'BRK.B', 'CL', 'DUK', 'AEP', 'LIN'
                ]
                
                # Get current weights to set floors
                # We need to approximate current weight since we only have current_positions (qty) and latest_prices.
                # Total value is passed in.
                latest_prices = get_latest_prices(self.prices)
                
                # First, check for volatility events and report them
                volatile_fortress_assets = []
                for ticker in fortress_assets:
                    if ticker in volatility_context:
                        vol_pct = volatility_context[ticker]
                        if abs(vol_pct) > 0.10:  # 10% threshold
                            volatile_fortress_assets.append((ticker, vol_pct))
                
                if volatile_fortress_assets:
                    print("\n" + "="*60)
                    print("⚠️  VOLATILITY ALERT: Significant Intraday Movements Detected")
                    print("="*60)
                    for ticker, vol_pct in volatile_fortress_assets:
                        print(f"  • {ticker}: {vol_pct*100:+.2f}% intraday change")
                    print("="*60 + "\n")
                
                for ticker in fortress_assets:
                    if ticker in current_positions and ticker in tickers_list:
                        # Calculate current weight
                        curr_val = current_positions[ticker] * latest_prices[ticker]
                        curr_weight = curr_val / current_portfolio_value
                        
                        # Constraint: New Weight >= 90% of Old Weight
                        # (Allow small trimming for rebalance, but no dumping)
                        floor = curr_weight * 0.90
                        idx = tickers_list.index(ticker)
                        ef.add_constraint(lambda w, i=idx, f=floor: w[i] >= f)
                        
                        # Enhanced logging for volatile assets
                        if ticker in volatility_context and abs(volatility_context[ticker]) > 0.10:
                            vol_pct = volatility_context[ticker]
                            print(f"  🛡️  [FORTRESS HOLD] {ticker}: Maintaining position despite {vol_pct*100:+.2f}% move")
                            print(f"      → Min Weight: {floor:.2%} (Long-term defensive asset)")
                            # Check if it's also a thesis constraint
                            from src.core.config import Config
                            if ticker in Config.THESIS_CONSTRAINTS:
                                role = Config.THESIS_CONSTRAINTS[ticker]['role']
                                print(f"      → Strategic Role: {role}")
                                print(f"      → Rationale: Volatility is opportunity, not threat (DCA strategy)")
                        else:
                            print(f"  [Constraint] Protecting {ticker}: Min Weight {floor:.2%}")

                # B. Anti-Casino Rule (Volatility Check)
                # Do NOT increase position in High Vol assets (>35% Annualized Vol)
                # Volatility is diagonal of Covariance Matrix (sqroot) * sqrt(252)
                # But simpler: calculate individual vols from 'mu' helper or just std dev of returns
                # returns = self.prices.pct_change().dropna()
                # std_devs = returns.std() * np.sqrt(252)
                
                # We can access the cov matrix 'S' already calculated.
                # Diagonal of S is ANNUALIZED variance (PyPortfolioOpt default).
                # Sqrt(Variance) = Annualized Volatility.
                import numpy as np # Ensure numpy is available
                variances = np.diag(S)
                vols_array = np.sqrt(variances)
                vols = pd.Series(vols_array, index=tickers_list)
                
                high_vol_threshold = 0.35
                
                for i, ticker in enumerate(tickers_list):
                    vol = vols[i]
                    if vol > high_vol_threshold:
                        # Constraint: New Weight <= Current Weight
                        # We cannot BUY more. We can Hold or Sell.
                        if ticker in current_positions:
                             curr_val = current_positions[ticker] * latest_prices[ticker]
                             curr_weight = curr_val / current_portfolio_value
                             curr_ceil = curr_weight # Cap at current ownership
                        else:
                             curr_ceil = 0.0 # Do not enter if we don't own
                             
                        ef.add_constraint(lambda w, idx=i, ceil=curr_ceil: w[idx] <= ceil)
                        if curr_ceil < 0.01:
                             print(f"  [Constraint] Blocking {ticker} (Vol: {vol:.1%}): Cannot Buy.")
                        else:
                             print(f"  [Constraint] Capping {ticker} (Vol: {vol:.1%}): Max Weight {curr_ceil:.2%}")

                weights = ef.min_volatility()
                
            elif profile == "moderate" or profile == "balanced":
                # 2. Moderate: Balanced Utility (Risk Aversion ~3.0 is standard neutral)
                # Maximize Sharpe is also an option, but Utility(3) often yields less concentration than Sharpe.
                weights = ef.max_quadratic_utility(risk_aversion=3)
                
            elif profile == "aggressive":
                # 3. Aggressive: Maximize Sharpe (Tangent Portfolio)
                # Theoretically optimal risk/reward, usually heavily allocated to winners.
                weights = ef.max_sharpe()
                
            elif profile == "speculative":
                 # 4. Speculative: Maximize Utility with Low Risk Aversion
                 # Ignores volatility to chase returns.
                weights = ef.max_quadratic_utility(risk_aversion=1)
                
            else:
                 # Default to Moderate/Balanced behavior if unknown
                print(f"Unknown profile '{profile}', defaulting to Max Sharpe.")
                weights = ef.max_sharpe()

            cleaned_weights = ef.clean_weights()
            
            performance = ef.portfolio_performance(verbose=True)
            print(f"Target Weights Calculated.")
        
            # 4. Discrete Allocation (Turn % into Integers)
            latest_prices = get_latest_prices(self.prices)
            
            da = DiscreteAllocation(cleaned_weights, latest_prices, total_portfolio_value=current_portfolio_value)
            
            # Allocation is {symbol: integer_qty}
            # Remainder is the leftover cash
            allocation, leftover = da.greedy_portfolio()
            
            print(f"Discrete Allocation performed. Leftover calculated: ${leftover:.2f}")

        except Exception as e:
            print(f"Optimization Failed: {e}")
            return {}, {}

        # 5. Calculate Actions (Diff) with 10-Day Volatility Limits
        actions = self._calculate_diff(allocation, current_positions, latest_prices, mu=mu, vols=vols)
        
        return actions, allocation
    
    def _calculate_diff(self, target_allocation, current_positions, latest_prices, mu=None, vols=None, threshold_value=50.0, drift_threshold=0.05):
        """
        Compares target allocation vs current positions to generate BUY/SELL/HOLD instructions.
        Applies a threshold to prevent churning small amounts.
        """
        all_symbols = set(target_allocation.keys()) | set(current_positions.keys())
        actions = {}
        
        for ticker in all_symbols:
            target_qty = target_allocation.get(ticker, 0)
            current_qty = int(current_positions.get(ticker, 0)) # Ensure int
            
            diff = target_qty - current_qty
            
            if diff > 0:
                action_type = "BUY"
            elif diff < 0:
                action_type = "SELL"
            else:
                action_type = "HOLD"
            
            # CHECK THRESHOLD to prevent micro-adjustments
            # Get current price
            price = latest_prices.get(ticker, 0)
            trade_value = abs(diff) * price
            
            # Logic:
            # 1. If we are liquidating (Target=0), usually we want to sell even if small, 
            #    unless it's dust (< $10). Let's be clean and allow liquidations > $10.
            # 2. If we are keeping the stock (Target > 0), we don't want to trade just to adjust by $20.
            
            is_significant = True
            
            if action_type != "HOLD":
                # Case A: Partial Adjustment (Target > 0)
                if target_qty > 0:
                    # Check 1: Dollar Value Threshold
                    if trade_value < threshold_value:
                        is_significant = False
                    
                    # Check 2: Relative Drift Threshold (prevent churning large positions)
                    # e.g. Sell 1 share of 73 JNJ. Change = 1/73 = 1.3% < 5%. SKIP.
                    if current_qty > 0:
                        change_pct = abs(diff) / current_qty
                        if change_pct < drift_threshold:
                            is_significant = False

                    if not is_significant:
                        # Override to HOLD because the change is too small (churning)
                        action_type = "HOLD"
                        diff = 0
                
                # Case B: Full Liquidation (Target == 0)
                else:
                    # If it's literal dust (<$5), maybe ignore? But for now let's clean up positions.
                    pass

            # Calculate 10-Day Targeted Limit Price (if we have mu and vols)
            limit_price = price
            import numpy as np
            # Now vols is guaranteed to be a Series if it originated from mu calculation
            if mu is not None and vols is not None and hasattr(mu, 'index') and hasattr(vols, 'index') and ticker in mu.index and ticker in vols.index:
                idx = list(mu.index).index(ticker)
                annual_drift = mu.iloc[idx]
                annual_vol = vols.loc[ticker]
                
                # Convert to 10 trading days (2 weeks)
                drift_10d = annual_drift * (10 / 252)
                vol_10d = annual_vol * np.sqrt(10 / 252)
                
                if action_type == "BUY":
                    # We expect price to dip. 
                    expected_low = price * (1 + drift_10d - vol_10d)
                    # Cap the buy limit at a minimum 0.5% discount so we don't accidentally buy above market
                    max_buy_price = price * 0.995
                    limit_price = min(max_buy_price, expected_low)
                    
                elif action_type == "SELL":
                    # We expect price to rip.
                    expected_high = price * (1 + drift_10d + vol_10d)
                    # Cap the sell limit at a minimum 0.5% premium
                    min_sell_price = price * 1.005
                    limit_price = max(min_sell_price, expected_high)

            # Include significant trades OR significant holds (where we already own it)
            # We skip stocks we don't own and don't intend to buy (Target=0, Current=0)
            if action_type != "HOLD" or (action_type == "HOLD" and current_qty > 0):
                # Filter out trivial moves if needed? For now, we trust the integer allocation.
                actions[ticker] = {
                    "action": action_type,
                    "qty": abs(diff),
                    "current": current_qty,
                    "target": target_qty,
                    "limit_price": round(limit_price, 2)
                }
                
        return actions
