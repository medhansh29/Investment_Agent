# AI Investment Agent

An automated, AI-powered portfolio manager designed to optimize your investments, monitor the market, and execute trades via Alpaca. Combining mathematical precision (Modern Portfolio Theory) with LLM-based reasoning (Gemini), it allows for a "Human-in-the-Loop" automated investing experience.

## 🚀 Key Features

### 🧠 Thesis-Driven RAG (New!)
The agent doesn't just look at prices; it reads the news.
- **Market Intelligence**: Fetches live headlines from BBC World and Yahoo Finance.
- **Context Awareness**: Uses Gemini AI to calculate real-time risk scores (0-10) for:
  - **Global Conflict** (Protects Defense stocks like LMT, RTX)
  - **Inflation Trend** (Protects Energy/Real Assets like XOM, CVX)
  - **Economic Instability** (Protects Recession Shields like KO, PG, JNJ)
- **Thesis Protection**: If the world is dangerous, the agent **refuses to sell** your insurance assets, even if they are up.

### 🛡️ "Safe Fortress" Logic
- **Anti-Casino Constraint**: In Conservative mode, the agent is mathematically blocked from buying high-volatility assets (>35% Ann. Vol) like Crypto or Meme stocks.
- **Core Preservation**: Strict constraints prevent "dumping" your long-term winners. It forces the optimizer to build *around* your core positions.

### 🤖 Intelligent Rebalancing
- **Bi-Weekly Checkups**: Runs optimization to keep your portfolio aligned with your risk profile.
- **Tax-Awareness**: The AI Advisor explains *why* a trade is happening, warning you if a sale might trigger a tax event but is necessary for risk reduction.

### 🔍 Daily Watchdog
- **Auto-Monitoring**: Checks your portfolio every morning.
- **Smart Alerts**: Sends an email ONLY if a stock moves >10% intraday, prompting you to rebalance.
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

You can interact with the agent manually using the helper script in the `scripts/` folder:

### Interactive Mode
The standard way to run the agent manually.
```bash
# Verify and execute trades (Bi-Weekly Rebalance)
./scripts/run_agent.sh interactive rebalance

# Deploy monthly capital (Monthly Invest)
./scripts/run_agent.sh interactive invest

# Choose mode interactively
./scripts/run_agent.sh interactive
```

### Trigger Workflows Manually
Simulate the automated alerts (sends actionable notifications/emails):
```bash
./scripts/run_agent.sh rebalance   # Triggers Bi-Weekly Alert
./scripts/run_agent.sh invest      # Triggers Monthly Alert
./scripts/run_agent.sh daily       # Runs Daily Watchdog Check
```

---

## 📂 File Structure

The project follows a modular **Source Layout**:

- **`src/`**: Source Code
  - **`core/`**: The Brain (`main.py`, `config.py`, `state_manager.py`)
  - **`strategies/`**: The Math (`portfolio_optimizer.py`)
  - **`integrations/`**: The Connections (`alpaca_client.py`, `gemini_client.py`)
  - **`utils/`**: Helpers (`notifications`, `templates`)
- **`scripts/`**: Automation Scripts
  - **`run_agent.sh`**: Main entry point helper.
  - **`install_cron.sh`**: Setup script for automation.
- **`data/`**: Storage
  - **`user_state.json`**: Portfolio history and settings.

---

**Disclaimer**: This is an automated trading tool. Use at your own risk. Paper trading is recommended for testing.
