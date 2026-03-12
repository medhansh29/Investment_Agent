import sys
import os

from src.utils.email_templates import EmailTemplates

# Setup mock inputs
volatility_trigger = {"asset": "NVDA", "change": -0.125}
market_context = {
    "market_context_bullets": [
        {"theme": "Tech Selloff", "explanation": "Semiconductors pulled back sharply."}
    ],
    "news_articles": [
        {"title": "NVDA Drops 12%", "article_url": "https://example.com/nvda", "summary": "Profit taking across the board."}
    ]
}
safe_analysis = {
    "holds": [
        {"assets": "NVDA", "reason": "Aegis explicitly maintains this **core AI hardware allocation** to capitalize on secular trends despite the short-term 12% drop."}
    ],
    "buys": [
        {"header": "**AAPL (+2 Shares @ Market):**", "reason": "Aegis is rotating capital here to **capture defensive value**."}
    ]
}

subject, body = EmailTemplates.get_volatility_rebalance_content(volatility_trigger, market_context, safe_analysis, "Tester")
print(f"Subject: {subject}\n")
print("-" * 40)
print(body)
