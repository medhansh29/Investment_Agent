# AI Investment Agent

An automated, AI-powered portfolio manager designed to optimize your investments, monitor the market, and execute trades via Alpaca. Combining mathematical precision (Modern Portfolio Theory) with LLM-based reasoning (Gemini), it allows for a "Human-in-the-Loop" automated investing experience.

## 🚀 Key Features

### 1. Intelligent Portfolio Optimization
- **Risk-Based Strategies**: Automatically adjusts optimization logic based on your profile:
    - **Conservative**: Minimizes Volatility.
    - **Balanced/Moderate**: Max Quadratic Utility (Risk Aversion 3).
    - **Aggressive**: Max Sharpe Ratio.
    - **Speculative**: Max Quadratic Utility (Risk Aversion 1).
- **Diversification Constraints**: Enforces position limits (max 20% per asset) to prevent concentration risk.

### 2. Gemini AI Advisor
- **Persona Injection**: The AI adapts its analysis tone to match your risk profile (e.g., warning about volatility for Conservative investors vs. hyping momentum for Speculative ones).
- **Context Awareness**: Accurately distinguishes between "Rebalancing" (shifting assets) and "Investing" (deploying new cash).
- **Interactive Feedback**: You can modify plans with natural language (e.g., *"I don't want to sell Tesla"*), and the agent re-optimizes accordingly.

### 3. Automated Workflows (Human-in-the-Loop)
The agent runs in the background using system schedulers (`cron`) but always requests your final approval:
- **Daily Watchdog**: Checks your positions every weekday at 4:30 PM. Alerts you only if a stock moves >10%.
- **Bi-Weekly Tactical Rebalance**: Reminds you every two weeks to realign your portfolio.
- **Monthly Investment Day**: Reminds you on the 1st of the month to deploy new capital.

### 4. Actionable Alerts
- Uses macOS **Actionable Notifications** (Popups).
- **"Run Now"**: Instantly opens a Terminal and launches the agent in the correct mode.
- **"Later"**: Snoozes the alert for 1 hour.

---

## 🛠️ Setup & Installation

### 1. Requirements
Ensure you have Python 3.9+ and the following libraries:
```bash
pip install -r requirements.txt
```

### 2. API Keys
Create a `.env` file in the project directory:
```bash
ALPACA_API_KEY=your_key_here
ALPACA_SECRET_KEY=your_secret_here
GEMINI_API_KEY=your_gemini_key_here
```

### 3. Configuration (`user_state.json`)
Manage your profile, risk settings, and stock universe in `user_state.json`.
```json
{
  "strategy_settings": {
    "risk_profile": "high_growth",
    "monthly_investment": 2000.0,
    "universe": ["NVDA", "AAPL", "MSFT", ...]
  }
}
```

### 4. Enable Automation
Run the installer script to set up the schedule (Cron jobs):
```bash
chmod +x install_cron.sh
./install_cron.sh
```

---

## 🖥️ Usage

You can interact with the agent manually using the helper script:

### Interactive Mode
The standard way to run the agent manually.
```bash
./run_agent.sh interactive
```

### Trigger Workflows Manually
Simulate the automated alerts:
```bash
./run_agent.sh rebalance   # Triggers Bi-Weekly Alert
./run_agent.sh invest      # Triggers Monthly Alert
./run_agent.sh daily       # Runs Daily Watchdog Check
```

---

## 📂 File Structure

- **`main.py`**: The brain. Orchestrates data fetching, optimization, and the interactive loop.
- **`portfolio_optimizer.py`**: Handles the math (Efficient Frontier, Convex Optimization).
- **`gemini_client.py`**: Handles AI reasoning, prompt generation, and feedback parsing.
- **`alpaca_client.py`**: Wrapper for Alpaca API (Data & Trading).
- **`run_agent.sh`**: Helper script for running creating the macOS alerts.
- **`install_cron.sh`**: Setup script for automation.

---

**Disclaimer**: This is an automated trading tool. Use at your own risk. Paper trading is recommended for testing.
