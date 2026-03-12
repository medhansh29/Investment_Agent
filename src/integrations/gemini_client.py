"""
Module: gemini_client.py
Purpose: Interface for Google Gemini AI. Handles prompt construction 
         and reasoning for Advisor Reports and RAG analysis.
"""
import google.generativeai as genai
from src.core.config import Config
import json
import pandas as pd

class GeminiClient:
    def __init__(self):
        genai.configure(api_key=Config.GEMINI_API_KEY)
        # Using flash-latest for highest analytical quality (resolves to gemini-3-flash with 20 req/day cap)
        self.primary_model = genai.GenerativeModel('gemini-flash-latest')
        self.backup_model = genai.GenerativeModel('gemini-2.5-flash')

    def _generate_with_fallback(self, prompt, context_name):
        try:
            response = self.primary_model.generate_content(prompt)
            text = response.text.replace("```json", "").replace("```", "").strip()
            return json.loads(text)
        except Exception as e:
            error_str = str(e)
            # Catch 429 Rate Limits or 404 Missing Model errors, or JSON decoding failures
            if "429" in error_str or "Quota" in error_str or "quota" in error_str or "404" in error_str or "escape" in error_str or "JSON" in error_str:
                print(f"  [{context_name}] Primary Model Unavailable or Invalid JSON. Falling back to 2.5-flash...")
                try:
                    response = self.backup_model.generate_content(prompt)
                    text = response.text.replace("```json", "").replace("```", "").strip()
                    return json.loads(text)
                except Exception as e2:
                    print(f"  [{context_name}] Backup Model Error: {e2}")
                    return None
            else:
                print(f"  [{context_name}] Primary Model Error: {e}")
                return None

    def analyze_rebalance(self, actions, market_data_df, user_profile, mode='invest', volatility_context=None, volatility_trigger=None):
        """
        Generates a user-friendly report explaining the rebalancing actions.
        
        actions: Dict of {ticker: {'action': 'BUY', 'qty': 5, ...}}
        market_data_df: The full DataFrame containing historical prices.
        user_profile: Dict containing user_info and strategy_settings.
        mode: 'rebalance' (no new cash) or 'invest' (new cash added).
        volatility_context: Dict {symbol: intraday_pct_change} from Alpaca positions.
        """
        if volatility_context is None:
            volatility_context = {}
        
        # 1. Prepare 15-day Price Context
        context_data = {}
        target_tickers = list(actions.keys())
        
        # Ensure correct format (wide format needed for easy slicing)
        if 'symbol' in market_data_df.columns:
             prices = market_data_df.pivot_table(index='timestamp', columns='symbol', values='close')
        else:
            prices = market_data_df

        # Get last 15 days for relevant tickers
        # Only select tickers that exist in our data (e.g. SPY might be in portfolio but not in our fetched universe)
        available_tickers = [t for t in target_tickers if t in prices.columns]
        recent_prices = prices[available_tickers].tail(15)
        
        # Format for Prompt (String representation of the tail)
        recent_prices_str = recent_prices.to_string()

        # Define Persona based on Risk Profile
        # Extract risk profile from the nested user_profile dict
        risk_profile_str = user_profile.get('strategy_settings', {}).get('risk_profile', 'balanced').lower().replace(" ", "_")
        if risk_profile_str == "high_growth": risk_profile_str = "speculative"
        
        persona_instructions = ""
        if risk_profile_str == "conservative":
            persona_instructions = "AI Persona: Cautious. Focus on long-term stability. Distinguish between volatility and fundamental changes. Encourage accumulating quality defenses on dips (DCA)."
        elif risk_profile_str == "moderate" or risk_profile_str == "balanced":
            persona_instructions = "AI Persona: Analytical. Balance Buy recommendations with Hold warnings. Focus on steady growth and efficient risk/reward."
        elif risk_profile_str == "aggressive":
            persona_instructions = "AI Persona: Optimistic. View dips as Buying Opportunities. Focus on long-term wealth building and high-conviction winners."
        elif risk_profile_str == "speculative":
            persona_instructions = "AI Persona: Aggressive/Excited. Focus on Momentum, Breakouts, and Trends. Chase high returns."

        # Define Context based on Mode
        mode_instructions = ""
        if mode == 'rebalance':
             mode_instructions = """
             CONTEXT: This is a Bi-Weekly Tactical Rebalance. NO NEW CASH IS BEING ADDED.
             CRITICAL INSTRUCTION: Your explanations must focus on *shifting* capital. 
             - For Sells: "Selling to lock in gains" or "Selling to fund other opportunities". 
             - For Buys: "Reallocating capital from sales into this asset." 
             - Do NOT say "investing new money". Say "rebalancing into".
             """
        elif mode == 'invest':
             mode_instructions = """
             CONTEXT: This is a Monthly Investment Day. New capital IS being deployed.
             CRITICAL INSTRUCTION: Focus on where the new money is building the future.
             - For Buys: "Deploying fresh capital here." Note that these are likely NEW additions, not rebalancing shifts.
             """

        # 2. Construct Prompt
        prompt = self._construct_rebalance_prompt(user_profile, actions, recent_prices_str, persona_instructions, mode_instructions, volatility_context, volatility_trigger)

        print("  [Invest/Rebalance] Sending data to Gemini for analysis...")
        return self._generate_with_fallback(prompt, "Invest/Rebalance")

    def _construct_rebalance_prompt(self, user_profile, actions, recent_prices_str, persona_instructions, mode_instructions, volatility_context, volatility_trigger=None):
        # Format volatility context for display
        volatility_str = ""
        if volatility_trigger:
            asset = volatility_trigger.get('asset', 'Unknown')
            change = volatility_trigger.get('change', 0.0) * 100
            volatility_str += f"\nCRITICAL CONTEXT: This rebalance was triggered automatically due to {asset} moving {change:+.2f}% intraday.\n"
            volatility_str += "IMPORTANT: You MUST explicitly address this volatility event in your explanations. If we are HOLDING a volatile stock, you MUST explicitly explain why we are holding onto it despite the high volatility (e.g., long-term horizon, inflation hedge, conservative DCA strategy).\n"
            
        if volatility_context:
            volatile_assets = [(sym, pct) for sym, pct in volatility_context.items() if abs(pct) > 0.10]
            if volatile_assets:
                volatility_str += "\nInput 4: INTRADAY VOLATILITY EVENTS (stocks with >10% moves today):\n"
                for sym, pct in volatile_assets:
                    volatility_str += f"  - {sym}: {pct*100:+.2f}%\n"
                volatility_str += "\nIMPORTANT: If a stock experienced high volatility today AND has action='HOLD', you MUST explicitly address this in your HOLDS section. Explain WHY we are holding despite the volatility.\n"
        
        return f"""
        Role: You are an autonomous financial agent named "Aegis".
        Task: Explain the following portfolio rebalancing recommendations to the user, "{user_profile.get('user_info', {}).get('name', 'User')}".
        Risk Profile: {user_profile.get('strategy_settings', {}).get('risk_profile', 'balanced').upper()}
        {persona_instructions}
        
        {mode_instructions}
        
        Input 1: User Profile & Strategy:
        {json.dumps(user_profile, indent=2)}

        Input 2: Recommended Actions (calculated by math optimization):
        {json.dumps(actions, indent=2)}
        
        Input 3: Recent Market Context (Last 15 days of closing prices):
        {recent_prices_str}
        
        {volatility_str}
        
        Instructions:
        1. Address the user by name only at the beginning header.
        2. VERY IMPORTANT: You must write in the THIRD-PERSON as "Aegis" (e.g., "Aegis is reallocating...", "Aegis recommends..."). NEVER use first-person pronouns like "we", "I", "our", or "us".
        3. TONE: Authoritative, analytical, and concise. Speak as an executive summarizing completed actions.
        4. **CRITICAL BOLDING RULE**: For every Buy and Sell rationale, you MUST identify the single most important strategic reason for the trade and **bold that specific phrase** within the rationale sentence (e.g., "...Aegis views this as a **tactical opportunity to accumulate a high-quality asset**...").
        5. **TRADE HEADERS**: Format every buy/sell `header` string exactly like this: "**[TICKER] ([+ or -][Quantity] Share(s) @ $[Execution Price]):**" (use "Market" for price if unknown).
        6. **GROUPED HOLDS**: Do NOT write a separate paragraph for every single hold asset. Group similar assets together into a single string (e.g., "MCD, COST, PG"). Keep the HOLD rationale to a single, punchy sentence.
        7. **MARKET KNOWLEDGE INJECTIONS** (Use these strict definitions):
           - **LLY/NVO**: Growth/Pharma, NOT "Safe Defensive". Volatile.
           - **Energy (XOM/CVX)** & **Defense (LMT)**: Inflation/Conflict Hedges.
        8. **VOLATILITY RESPONSE**: If Input 4 shows high volatility for a HOLD position, MUST explain the strategic rationale (e.g., "Volatility creates DCA opportunities").
        9. **STRICT CONSTRAINT**: ONLY analyse stocks listed in "Input 2: Recommended Actions". Do NOT hallucinate holdings.
        
        Output Format: Return ONLY a valid JSON object matching this exact structure:
        {{
          "buys": [
            {{ 
              "header": "**AAPL (+5 Shares @ $150.00):**", 
              "reason": "Aegis is reallocating capital to **strengthen the tech core**." 
            }}
          ],
          "sells": [
            {{ 
              "header": "**MSFT (-2 Shares @ Market):**", 
              "reason": "Aegis is selling to **manage concentration risk**." 
            }}
          ],
          "holds": [
             {{ 
               "assets": "KO, PG, MCD", 
               "reason": "Reliable consumer staples offering price resilience." 
             }}
          ]
        }}
        """

    def interpret_feedback(self, feedback_text, universe):
        """
        Parses user's natural language feedback into structured constraints.
        
        feedback_text: "I want to invest in NVDA and not in GE"
        universe: List of available ticker symbols.
        """
        prompt = f"""
        Role: Financial Assistant.
        Task: Extract constraints from the user's feedback.
        
        User Input: "{feedback_text}"
        Available Stocks: {universe}
        
        Instructions:
        1. Identify stocks the user wants to FORCE INCLUDE (Buy/Hold).
        2. Identify stocks the user wants to FORCE EXCLUDE (Sell/Avoid).
        3. Only use tickers present in 'Available Stocks'.
        
        Output Format (JSON Only):
        {{
          "force_include": ["TICKER1"],
          "force_exclude": ["TICKER2"]
        }}
        """
        print(f"  [Feedback] Interpreting: '{feedback_text}'...")
        res = self._generate_with_fallback(prompt, "Feedback")
        return res if res else {"force_include": [], "force_exclude": []}

    def generate_daily_pulse(self, positions_context, market_context, user_name="User", masterclass_history=None):
        """
        Generates the Daily Pulse Masterclass content for the stable daily email.
        """
        if masterclass_history is None:
            masterclass_history = []
            
        history_str = ", ".join(masterclass_history) if masterclass_history else "None"
        
        prompt = f"""
        # ROLE & USER CONTEXT
        You are Aegis, an autonomous, highly sophisticated investment agent. 
        The user you are advising is {user_name}, a 19-year-old Artificial Intelligence student at Purdue University in West Lafayette, Indiana. You must seamlessly weave this context into your analysis when relevant (e.g., connecting AI market news to his coursework, or framing long-term horizons for a 19-year-old), but NEVER explicitly state that you are doing so. Do not use prefatory phrases like "Since you are an AI student..." or "Because you go to Purdue...". 

        Input 1: User's Current Portfolio Context
        {positions_context}

        Input 2: Today's Global Headlines (for context and selecting "Daily Reading")
        {json.dumps(market_context, indent=2)}
        
        Input 3: Previously Taught Masterclass Topics
        {history_str}

        # FORMATTING MANDATES
        1. Write strictly in the third-person as "Aegis" (e.g., "Aegis recommends...", "Aegis is watching...").
        2. Market Catalyst & RAG Context: Write a 2-3 sentence macro summary of Wall Street using the headlines in Input 2. Pick 2-3 specific articles to link as `key_news`.
        3. Portfolio Context (The Consolidation Rule): Group the user's current holdings from Input 1 into a single array by macro `Sector` (e.g., "Tech & AI", "Defensive & Staples", "Healthcare"). Keep the rationale very concise and relevant to how that specific sector is reacting to the daily news. Ensure every ticker from Input 1 is included in the groups.
        4. Aegis Masterclass: Choose ONE fundamental trading or mathematical financial concept that helps the user build his trading skills. It MUST be a *new* topic that is not listed in Input 3. Build logically upon the previous topics. 
        5. Math & Formula Formatting: You MUST use standard LaTeX for all formulas and mathematical equations in the masterclass. Enclose inline equations in `$` (e.g., $x = y$) and display equations in `$$`. CRITICAL: Because you are returning a JSON object, you MUST strictly double-escape all LaTeX backslashes (e.g., use `\\\\beta` or `\\\\frac`) so it creates legally parseable JSON! Do NOT use LaTeX for standard text.
        6. Educational Reading: Curate EXACTLY 2 educational reading links (e.g., from Investopedia) that explain the concept further. (Make up a highly probable URL if unknown).
        7. Video Recommendation: Provide a YouTube search query URL for a video related to the topic (Format: "https://www.youtube.com/results?search_query=Your+Topic+Here").

        Output Format: You MUST return a valid JSON object matching this exact structure:
        {{
          "template_id": "daily_pulse_masterclass_06",
          "user_name": "{user_name}",
          "date": "YYYY-MM-DD",
          "market_overview": {{
            "summary": "Aegis observes a stabilizing market as inflationary fears subside...",
            "key_news": [
              {{ "title": "Real Headline from Input 2", "url": "Real URL from Input 2", "summary": "1-2 sentence impact summary." }}
            ]
          }},
          "portfolio_consolidation_status": "Portfolio Context: Broad Consolidation (or other condition based on price action)",
          "holdings_context": [
            {{
              "sector": "Tech & AI",
              "tickers": "NVDA, MSFT, GOOGL",
              "rag_insight": "Consolidating as the market prices in new computing standards, connecting directly to structural shifts in large language models."
            }}
          ],
          "masterclass": {{
            "topic": "The Concept Topic",
            "introduction": "Introductory paragraph explaining why this matters...",
            "formula": "$$Formula goes here$$",
            "concepts": [
              {{ "term": "Term 1", "definition": "Definition 1" }}
            ],
            "key_signal": {{
              "name": "Signal Name",
              "description": "How to use this signal in practice."
            }}
          }},
          "daily_reading": [
            {{ "title": "Investopedia: Concept Name", "url": "https://www.investopedia.com/terms/...", "description": "Why you should read this." }}
          ],
          "video_recommendation": {{
             "title": "Watch: Topic Video",
             "url": "https://www.youtube.com/results?search_query=...",
             "description": "Why you should watch this."
          }}
        }}

        Output ONLY JSON. Do not wrap in backticks or markdown blocks.
        """
        
        print("  [Pulse] Generating Daily Masterclass via Gemini...")
        return self._generate_with_fallback(prompt, "Pulse")
