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

### 🎯 Smart Limit Orders (New!)

Instead of executing blindly at market prices, Aegis computes **10-day forward volatility and drift forecasts**.

- **Dynamic Limits**: Calculates the statistically probable "local low" for Buys, and "local high" for Sells individually for each stock based on its historical variance.
- **Good-Till-Cancelled (GTC)**: Orders sit patiently on the books waiting for the perfect technical entry or exit within your 2-week execution block.

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

Follow these steps to deploy Aegis as your personal autonomous investment agent.

### 1. Clone & Install

```bash
git clone https://github.com/medhansh29/Investment_Agent.git
cd Investment_Agent
pip install -r requirements.txt
```

### 2. Obtaining API Keys

Aegis relies on three free services to operate. You must obtain the following keys:

1. **Alpaca Trading API (Broker)**:
   - Go to the [Alpaca Dashboard](https://app.alpaca.markets/brokerage/dashboard/overview).
   - Sign up and generate your **Paper Trading** API Key and Secret Key. Use Paper keys first to safely test the agent with play money!
2. **Google Gemini (AI Brain)**:
   - Medhansh will provide you with the shared `GEMINI_API_KEY` to use.
3. **Gmail SMTP (Email Alerts)**:
   - You need an App Password to allow the agent to send you Masterclass emails.
   - Go to your Google Account -> Security -> 2-Step Verification -> [App Passwords](https://myaccount.google.com/apppasswords).
   - Create a new App Password named "Aegis". It will be a 16-character string.

### 3. Initialize Templates

Copy the provided template files to create your personal local configuration.

**Environment Variables:**

```bash
cp .env.example .env
```

Open `.env` and paste the exact keys you generated in Step 2.

**User State & Portfolio Memory:**

```bash
cp data/user_state.example.json data/user_state.json
```

Open `data/user_state.json` and configure your `name`, `email`, baseline `monthly_investment` (e.g., $1000), and your `universe` of stock tickers you want the agent to track.

### 4. Enable Cloud Automation

To have the agent run in the background 24/7 without keeping your computer on, simply push it to a private GitHub repository!

1. Go to your repository **Settings** -> **Secrets and variables** -> **Actions**.
2. Add the following **New repository secrets**:
   - `ALPACA_API_KEY`
   - `ALPACA_SECRET_KEY`
   - `GEMINI_API_KEY`
   - `SMTP_EMAIL` (Your Gmail address)
   - `SMTP_PASSWORD` (Your 16-digit App Password)
3. Under the **Actions** tab, ensure workflows are enabled. The `.github/workflows/` cron jobs will now automatically run the Daily Watchdog, Bi-Weekly Rebalance, and Monthly Investment loops.

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
