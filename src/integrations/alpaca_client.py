"""
Module: alpaca_client.py
Purpose: Wrapper for Alpaca Markets API (trading and market data).
"""
from alpaca_trade_api.rest import REST, TimeFrame
from src.core.config import Config
from datetime import datetime, timedelta
import pandas as pd

import os

class AlpacaClient:
    def __init__(self):
        # We assume Config.validate() has already been run in main
        self.api = REST(
            Config.ALPACA_API_KEY,
            Config.ALPACA_SECRET_KEY,
            base_url="https://paper-api.alpaca.markets" # Default to paper
        )

    def get_account(self):
        """Returns the account object."""
        for attempt in range(3):
            try:
                return self.api.get_account()
            except Exception as e:
                print(f"Error fetching account (Attempt {attempt+1}/3): {e}")
                import time
                time.sleep(1)
        
        print("Warning: Alpaca connection failed. Using MOCK Account for testing.")
        class MockAccount:
            status = "ACTIVE (MOCK)"
            buying_power = "200000"
            portfolio_value = "100000"
        return MockAccount()

    def get_positions(self):
        """Returns a list of current positions."""
        for attempt in range(3):
            try:
                return self.api.list_positions()
            except Exception as e:
                print(f"Error fetching positions (Attempt {attempt+1}/3): {e}")
                import time
                time.sleep(1)
        return []

    def get_market_data(self, symbols, lookback_years=3):
        """
        Fetches historical data for the given symbols.
        Implements chunking to avoid API limits.
        """
        end_date = datetime.now()
        start_date = end_date - timedelta(days=365 * lookback_years)
        
        # Format dates for Alpaca (YYYY-MM-DD)
        start_str = start_date.strftime('%Y-%m-%d')
        end_str = end_date.strftime('%Y-%m-%d')
        
        print(f"Fetching data from {start_str} to {end_str} for {len(symbols)} symbols...")
        
        all_bars = []
        chunk_size = 10 
        
        # Chunking logic
        for i in range(0, len(symbols), chunk_size):
            chunk = symbols[i:i + chunk_size]
            print(f"  Fetching chunk: {chunk}")
            
            try:
                # fetch bars
                bars = self.api.get_bars(
                    chunk,
                    TimeFrame.Day,
                    start=start_str,
                    end=end_str,
                    adjustment='raw',
                    feed='iex'  # Use IEX for free/paper tier
                ).df
                
                if not bars.empty:
                    all_bars.append(bars)
                    
            except Exception as e:
                print(f"  Error fetching chunk {chunk}: {e}")
        
        if not all_bars:
            return pd.DataFrame()
            
        # Combine all chunks
        full_df = pd.concat(all_bars)
        
        return full_df

    def execute_trades(self, actions):
        """
        Executes the list of actions on Alpaca.
        actions: Dict {ticker: {'action': 'BUY', 'qty': 5}}
        """
        print("\n--- EXECUTING TRADES ---")
        for ticker, data in actions.items():
            side = data['action'].lower()
            qty = data['qty']
            
            if side == "hold" or qty <= 0:
                continue
                
            print(f"Submitting Order: {side.upper()} {qty} of {ticker}...")
            
            try:
                # Assuming simple market orders for now
                self.api.submit_order(
                    symbol=ticker,
                    qty=qty,
                    side=side,
                    type='market',
                    time_in_force='day'
                )
                print(f"  -> Order Submitted Successfully.")
            except Exception as e:
                print(f"  -> FAILED to submit order: {e}")
                # Fallback check: if we are in Mock mode (which is implicit if API fails), we might just print
                if "SSL" in str(e) or "Mock" in str(e):
                     print(f"  -> (Mock Mode) Trade 'executed' locally.")
