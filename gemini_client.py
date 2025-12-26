import google.generativeai as genai
from config import Config
import json
import pandas as pd

class GeminiClient:
    def __init__(self):
        genai.configure(api_key=Config.GEMINI_API_KEY)
        # Using latest flash model found in list
        self.model = genai.GenerativeModel('gemini-flash-latest')

    def analyze_rebalance(self, actions, market_data_df, user_profile, mode='invest'):
        """
        Generates a user-friendly report explaining the rebalancing actions.
        
        actions: Dict of {ticker: {'action': 'BUY', 'qty': 5, ...}}
        market_data_df: The full DataFrame containing historical prices.
        user_profile: Dict containing user_info and strategy_settings.
        mode: 'rebalance' (no new cash) or 'invest' (new cash added).
        """
        
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
            persona_instructions = "AI Persona: Cautious. Warn about volatility. Suggest selling anything that moves too fast. Focus on stability."
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
             - For Buys: "Deploying fresh capital here."
             """

        # 2. Construct Prompt
        prompt = f"""
        Role: You are a friendly, expert financial advisor named "Investment Agent".
        Task: Explain the following portfolio rebalancing recommendations to the user, "{user_profile.get('user_info', {}).get('name', 'User')}".
        Risk Profile: {risk_profile_str.upper()}
        {persona_instructions}
        
        {mode_instructions}
        
        Input 1: User Profile & Strategy:
        {json.dumps(user_profile, indent=2)}

        Input 2: Recommended Actions (calculated by math optimization):
        {json.dumps(actions, indent=2)}
        
        Input 3: Recent Market Context (Last 15 days of closing prices):
        {recent_prices_str}
        
        Instructions:
        1. Address the user by name.
        2. Consider their "Risk Profile" and "Age" from Input 1 when explaining. 
        3. Look at the "Action" (BUY/SELL/HOLD) for each stock in Input 2.
        4. **CRITICAL**: The user believes "Holding is important too". 
           - If the action is "HOLD", explicitly praise this decision.
        5. **STRICT CONSTRAINT**: ONLY analyse stocks listed in "Input 2: Recommended Actions". 
           - Do NOT discuss stocks that appear in "Input 3" but are NOT in "Input 2". 
           - Do NOT hallucinate holdings that the user does not have.
        6. Explain *WHY* the math recommends the action using the Market Context.
        7. Group the output into "Buys", "Sells", and "Holds".
        
        Output Format: Return ONLY a valid JSON object. Do not wrap in markdown code blocks.
        {{
          "buys": [
            {{ "ticker": "AAPL", "qty": 5, "reason": "..." }}
          ],
          "sells": [
            {{ "ticker": "MSFT", "qty": 2, "reason": "..." }}
          ],
          "holds": [
             {{ "ticker": "KO", "reason": "..."}}
          ]
        }}
        """

        print("Sending data to Gemini for analysis...")
        
        try:
            response = self.model.generate_content(prompt)
            # creating a raw string from the response to clean potential markdown
            text = response.text.replace("```json", "").replace("```", "").strip()
            return json.loads(text)
        except Exception as e:
            print(f"Gemini Error: {e}")
            return None

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
        try:
            print(f"Interpreting Feedback: '{feedback_text}'...")
            response = self.model.generate_content(prompt)
            text = response.text.replace("```json", "").replace("```", "").strip()
            return json.loads(text)
        except Exception as e:
            print(f"Gemini Feedback Error: {e}")
            return {"force_include": [], "force_exclude": []}
