"""
Module: market_intelligence.py
Purpose: The Eyes of the Agent. Fetches external data (RSS) and uses 
         Gemini to compute Risk Scores (Conflict, Inflation, Instability).
"""
import urllib.request
import xml.etree.ElementTree as ET
from src.integrations.gemini_client import GeminiClient
import json
import ssl

class MarketIntelligence:
    def __init__(self):
        self.client = GeminiClient()
        # Initializing search_web tool is not possible here as it's an external tool call
        # but we can simulate the intent in the results.
        self.sources = [
            "http://feeds.bbci.co.uk/news/world/rss.xml",                             # BBC World
            "https://feeds.a.dj.com/rss/WSJcomUSBusiness.xml",                        # WSJ Business
            "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=10000664", # CNBC Finance
            "https://feeds.a.dj.com/rss/RSSMarketsMain.xml",                          # WSJ Markets
            "https://rss.nytimes.com/services/xml/rss/nyt/Business.xml",              # NYT Business
            "https://rss.nytimes.com/services/xml/rss/nyt/Economy.xml"                # NYT Economy
        ]

    def _fetch_rss(self, url):
        try:
            # Bypass SSL verification for macOS Python issues
            context = ssl._create_unverified_context()
            with urllib.request.urlopen(url, timeout=5, context=context) as response:
                xml_data = response.read()
                root = ET.fromstring(xml_data)
                headlines = []
                # Standard RSS structure: channel -> item
                for item in root.findall('./channel/item'):
                    title = item.find('title')
                    link = item.find('link')
                    if title is not None and title.text:
                        href = link.text if (link is not None and link.text) else ""
                        headlines.append({"title": title.text, "link": href})
                if headlines:
                    print(f"  [RAG] Fetched {len(headlines)} headlines from {url}")
                return headlines[:15] # Top 15 per source
        except Exception as e:
            print(f"  [RAG] Source skipped ({url}): {e}")
            return []

    def get_benchmark_stats(self, alpaca_client, extra_tickers=None) -> dict:
        """
        Fetches daily and weekly performance for market (SPY, QQQ) and sector benchmarks.
        Returns a dict mapping ticker -> {daily_pct, weekly_pct}.
        """
        from datetime import datetime, timedelta
        from alpaca_trade_api.rest import TimeFrame

        # Core market + specific sector benchmarks for categorization
        benchmarks = ["SPY", "QQQ", "SOXX", "ITA", "XLF", "XLV", "XLE", "XLP", "VIXY"]
        if extra_tickers:
            benchmarks = list(set(benchmarks + extra_tickers))
            
        result = {}

        try:
            end = datetime.now()
            start = end - timedelta(days=10)
            start_str = start.strftime("%Y-%m-%d")
            end_str = end.strftime("%Y-%m-%d")

            # Batch fetch bars for efficiency
            bars_df = alpaca_client.api.get_bars(
                benchmarks,
                TimeFrame.Day,
                start=start_str,
                end=end_str,
                adjustment="raw",
                feed="iex"
            ).df

            if not bars_df.empty:
                bars_df = bars_df.reset_index()
                for ticker in benchmarks:
                    t_bars = bars_df[bars_df["symbol"] == ticker].sort_values("timestamp")
                    if len(t_bars) >= 2:
                        latest_close = float(t_bars["close"].iloc[-1])
                        prev_close   = float(t_bars["close"].iloc[-2])
                        daily_pct    = (latest_close - prev_close) / prev_close * 100

                        # Weekly: approx 5 trading days ago
                        week_bar = t_bars["close"].iloc[-6] if len(t_bars) >= 6 else t_bars["close"].iloc[0]
                        weekly_pct = (latest_close - float(week_bar)) / float(week_bar) * 100

                        result[ticker] = {
                            "daily_pct": round(daily_pct, 2),
                            "weekly_pct": round(weekly_pct, 2),
                            "current_price": round(latest_close, 2)
                        }
            
            # Map VIX proxy to a clean key if present
            if "VIXY" in result:
                result["VIX"] = {"level": result["VIXY"]["current_price"]}

        except Exception as e:
            print(f"  [Benchmark] Failed to fetch benchmark stats: {e}")

        return result

    def search_ticker_news(self, ticker, sector=None):
        """
        Performs a targeted web search for a specific ticker to find CAUSAL reasons for performance.
        Note: This is intended to be called by the agent loop that has access to search_web.
        """
        query = f"{ticker} stock performance news latest"
        if sector:
            query = f"{ticker} {sector} sector news trends"
        
        print(f"  [RAG] Searching for specific news for {ticker}...")
        # We will use the search_web tool results passed from the main loop
        return query

    def get_market_context(self):
        """
        Fetches headlines and asks AI to score Global Risks.
        """
        all_headlines = []
        print("  [RAG] Fetching Live News Feeds...")
        for src in self.sources:
            headlines = self._fetch_rss(src)
            all_headlines.extend(headlines)
        
        if not all_headlines:
            print("  [RAG] Warning: No headlines fetched. Assuming Default Risk (5/10).")
            return {'conflict_score': 5, 'inflation_score': 5, 'reasoning': "Data fetch failed."}

        # Deduplicate based on title
        unique_headlines = {item['title']: item for item in all_headlines}.values()
        all_headlines = list(unique_headlines)
        
        context_str = "\n".join([f"- {h['title']} (URL: {h['link']})" for h in all_headlines[:40]]) # Limit processing
        
        prompt = f"""
        Role: Senior Geopolitical & Economic Analyst.
        Task: Analyze these news headlines to determine the current level of "Global Conflict Risk" and "Inflationary Pressure".
        
        Headlines:
        {context_str}
        
        Instructions:
        1. 'conflict_score' (0-10): 0 = Global Peace, 10 = World War III / Major Regional Wars Active.
        2. 'inflation_score' (0-10): 0 = Deflation, 10 = Hyperinflation / Soaring Energy Prices.
        3. 'economic_instability_score' (0-10): 0 = Strong Growth, 10 = Deep Recession / Financial Crisis.
        4. Develop a rigorous, highly structured market context broken down into 4-5 distinct strategic themes (e.g., Geopolitical Escalation, Inflationary Pressures, Federal Reserve Stance, Sector Rotations). Provide a comprehensive 3-4 sentence explanation of how each theme impacts the broader market.
        5. Extract 2-3 of the most relevant news articles from the headlines above. Provide their exact Title, exact URL, and write a strict 1-2 sentence summary explaining how this event influences portfolio strategy.
        
        Output Format (JSON Only):
        {{
            "conflict_score": 7,
            "inflation_score": 4,
            "economic_instability_score": 6,
            "market_context_bullets": [
                {{
                    "theme": "Geopolitical Escalation",
                    "explanation": "3-4 sentence comprehensive explanation..."
                }}
            ],
            "news_articles": [
                {{
                    "title": "Headline 1", 
                    "article_url": "URL 1",
                    "summary": "1-2 sentence strategic summary."
                }}
            ]
        }}
        """
        
        print("  [RAG] Analyzing World State via Gemini...")
        try:
            data = self.client._generate_with_fallback(prompt, "RAG")
            if data is None:
                raise Exception("Fallback router returned None (Both APIs failed)")
            print(f"  [RAG] Result: Conflict={data.get('conflict_score', 5)}, Inflation={data.get('inflation_score', 5)}, Instability={data.get('economic_instability_score', 5)}")
            return data
        except Exception as e:
            print(f"  [RAG] Analysis Failed: {e}")
            return {'conflict_score': 5, 'inflation_score': 5, 'economic_instability_score': 5}
