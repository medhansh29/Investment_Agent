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
            "http://feeds.bbci.co.uk/news/world/rss.xml",                             # BBC World
            "https://finance.yahoo.com/news/rssindex",                                # Yahoo Finance
            "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=10000664", # CNBC Finance
            "https://feeds.a.dj.com/rss/RSSMarketsMain.xml",                          # WSJ Markets
            "https://rss.nytimes.com/services/xml/rss/nyt/Business.xml",              # NYT Business
            "https://www.ft.com/?format=rss"                                          # Financial Times
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
            response = self.client.model.generate_content(prompt)
            text = response.text.replace("```json", "").replace("```", "").strip()
            data = json.loads(text)
            print(f"  [RAG] Result: Conflict={data.get('conflict_score')}, Inflation={data.get('inflation_score')}, Instability={data.get('economic_instability_score')}")
            return data
        except Exception as e:
            print(f"  [RAG] Analysis Failed: {e}")
            return {'conflict_score': 5, 'inflation_score': 5, 'economic_instability_score': 5}
