import json
import os
from datetime import datetime

class StateManager:
    DEFAULT_STATE = {
        "user_info": {
            "name": "Alex",
            "age": 30,
            "email": "alex@example.com"
        },
        "strategy_settings": {
            "risk_profile": "high_growth",
            "monthly_investment": 500.00,
            "lookback_years": 3,
            "universe": ["AAPL", "MSFT", "GOOG", "TSLA", "NVDA", "KO"]
        },
        "last_run": None
    }

    def __init__(self, state_file="user_state.json"):
        self.state_file = state_file
        self.state = self.load_state()

    def load_state(self):
        """Loads the state from the JSON file. Creates it if it doesn't exist."""
        if not os.path.exists(self.state_file):
            print(f"State file {self.state_file} not found. Creating new one with defaults.")
            self.save_state(self.DEFAULT_STATE)
            return self.DEFAULT_STATE
        
        try:
            with open(self.state_file, 'r') as f:
                return json.load(f)
        except json.JSONDecodeError:
            print(f"Error decoding {self.state_file}. Resetting to defaults.")
            self.save_state(self.DEFAULT_STATE)
            return self.DEFAULT_STATE

    def save_state(self, state=None):
        """Saves the current state to the JSON file."""
        if state is None:
            state = self.state
        
        with open(self.state_file, 'w') as f:
            json.dump(state, f, indent=2)
        print(f"State saved to {self.state_file}")

    def update_last_run(self):
        """Updates the last_run timestamp."""
        self.state["last_run"] = datetime.now().strftime("%Y-%m-%d")
        self.save_state()

    def get_universe(self):
        return self.state["strategy_settings"]["universe"]

    def get_settings(self):
        return self.state["strategy_settings"]
