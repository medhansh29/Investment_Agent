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
        self.sources = [
            "http://feeds.bbci.co.uk/news/world/rss.xml", # BBC World
            "https://finance.yahoo.com/news/rssindex",    # Yahoo Finance
        ]

    def _fetch_rss(self, url):
        try:
            # Bypass SSL verification for macOS Python issues
            context = ssl._create_unverified_context()
            with urllib.request.urlopen(url, timeout=5, context=context) as response:
                xml_data = response.read()
                root = ET.fromstring(xml_data)
                headlines = []
                # Standard RSS structure: channel -> item -> title
                for item in root.findall('./channel/item'):
                    title = item.find('title').text
                    if title:
                        headlines.append(title)
                return headlines[:15] # Top 15 per source
        except Exception as e:
            print(f"Failed to fetch RSS from {url}: {e}")
            return []

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

        # Deduplicate
        all_headlines = list(set(all_headlines))
        
        context_str = "\n".join([f"- {h}" for h in all_headlines[:40]]) # Limit processing
        
        prompt = f"""
        Role: Geopolitical & Economic Analyst.
        Task: Analyze these news headlines to determine the current level of "Global Conflict Risk" and "Inflationary Pressure".
        
        Headlines:
        {context_str}
        
        Instructions:
        1. 'conflict_score' (0-10): 0 = Global Peace, 10 = World War III / Major Regional Wars Active.
        2. 'inflation_score' (0-10): 0 = Deflation, 10 = Hyperinflation / Soaring Energy Prices.
        3. 'economic_instability_score' (0-10): 0 = Strong Growth, 10 = Deep Recession / Financial Crisis.
        4. Provide a brief 1-sentence reasoning for each.
        
        Output Format (JSON Only):
        {{
            "conflict_score": 7,
            "inflation_score": 4,
            "economic_instability_score": 6,
            "reasoning": "Conflict high due to..."
        }}
        """
        
        print("  [RAG] Analyzing World State via Gemini...")
        try:
            response = self.client.model.generate_content(prompt)
            text = response.text.replace("```json", "").replace("```", "").strip()
            data = json.loads(text)
            print(f"  [RAG] Result: Conflict={data.get('conflict_score')}, Inflation={data.get('inflation_score')}, Instability={data.get('economic_instability_score')}")
            return data
        except Exception as e:
            print(f"  [RAG] Analysis Failed: {e}")
            return {'conflict_score': 5, 'inflation_score': 5, 'economic_instability_score': 5}
