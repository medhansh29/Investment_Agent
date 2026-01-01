import pandas as pd
from pypfopt import expected_returns, risk_models
from pypfopt.efficient_frontier import EfficientFrontier
from pypfopt.discrete_allocation import DiscreteAllocation, get_latest_prices

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

    def optimize(self, current_portfolio_value, current_positions=None, risk_profile="balanced", constraints=None):
        """
        Calculates the Efficient Frontier based on risk profile and user constraints.
        
        risk_profile: 'high_growth', 'balanced', or 'conservative'.
        constraints: Dict {'force_include': ['TICKER'], 'force_exclude': ['TICKER']}
        """
        if current_positions is None:
            current_positions = {}
        if constraints is None:
            constraints = {}

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
        
        # Apply Logic Constraints
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
                # 1. Conservative: Minimize Volatility
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

        # 5. Calculate Actions (Diff)
        actions = self._calculate_diff(allocation, current_positions, latest_prices)
        
        return actions, allocation

    def _calculate_diff(self, target_allocation, current_positions, latest_prices, threshold_value=50.0, drift_threshold=0.05):
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

            # Include significant trades OR significant holds (where we already own it)
            # We skip stocks we don't own and don't intend to buy (Target=0, Current=0)
            if action_type != "HOLD" or (action_type == "HOLD" and current_qty > 0):
                # Filter out trivial moves if needed? For now, we trust the integer allocation.
                actions[ticker] = {
                    "action": action_type,
                    "qty": abs(diff),
                    "current": current_qty,
                    "target": target_qty
                }
                
        return actions
