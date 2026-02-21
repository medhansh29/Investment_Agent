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
- **Core Preservation**: Strict constraints prevent "dumping" your long-term winners. It forces the optimizer to build _around_ your core positions.

### 🤖 Intelligent Rebalancing

- **Bi-Weekly Checkups**: Runs optimization to keep your portfolio aligned with your risk profile.
- **Executive Summaries**: All rebalances and investment reports are generated into executive, highly scannable HTML emails featuring bolded mathematical rationales, tables grouping holds by sector, and detailed news summaries.
- **Tax-Awareness**: The AI Advisor explains _why_ a trade is happening, warning you if a sale might trigger a tax event but is necessary for risk reduction.

### 🔍 Daily Watchdog

- **Auto-Monitoring**: Checks your portfolio every morning.
- **Aegis Masterclass (V3)**: Generates a highly personalized, daily educational curriculum. The agent maintains a persistent topic memory to build a progressive syllabus over time, natively formats math using LaTeX blocks, and curates reading lists.
- **Dynamic Persona**: Analysis is tailored explicitly to your demographic and risk profile.
- **Smart Alerts**: Sends an email ONLY if a stock moves >10% intraday, prompting you to rebalance.

### ☁️ GitHub Actions Automation

The agent runs autonomously in the cloud via GitHub Actions schedulers:

- **Daily Watchdog**: Checks your positions every day at 4:30 PM. Alerts you only if a stock moves >10%.
- **Bi-Weekly Tactical Rebalance**: Reminds you every two weeks to realign your portfolio.
- **Monthly Investment Day**: Reminds you on the 1st of the month to deploy new capital.

### ✉️ Beautiful HTML Emails

- All AI communication is sent beautifully formatted directly to your inbox.
- Supports native LaTeX rendering via CodeCogs, macro-sector tables, conditional green/red market badging, and emojis.

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
GMAIL_USER=your_gmail_here
GMAIL_APP_PASSWORD=your_gmail_app_password
```

### 3. Configuration (`user_state.json`)

Manage your profile, risk settings, and stock universe in `user_state.json`.

```json
{
  "strategy_settings": {
    "risk_profile": "high_growth",
    "monthly_investment": 2000.0,
    "universe": ["NVDA", "AAPL", "MSFT"]
  }
}
```

### 4. Enable Automation

Simply push the codebase to GitHub. The included `.github/workflows/` directory contains all necessary cron pipelines to run the agent in the cloud. Establish your API keys in the GitHub Repository Secrets.

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
