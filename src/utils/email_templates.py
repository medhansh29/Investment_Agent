"""
Module: email_templates.py
Purpose: Provides HTML and Text templates for various email alerts 
         (Daily Watchdog, Trade Confirmation, etc.).
"""
import datetime
import re
import urllib.parse

class EmailTemplates:
    _BASE_CSS = """
    <style>
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; line-height: 1.6; color: #333; background-color: #f4f7f6; margin: 0; padding: 20px; }
        .container { max-width: 600px; margin: 0 auto; background: #fff; border-radius: 8px; overflow: hidden; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
        .header { background: #2c3e50; color: #fff; padding: 20px; text-align: center; }
        .header h1 { margin: 0; font-size: 24px; }
        .header p { margin: 5px 0 0; font-size: 14px; opacity: 0.8; }
        .content { padding: 25px; }
        .section-title { color: #2c3e50; border-bottom: 2px solid #ecf0f1; padding-bottom: 5px; margin-top: 30px; margin-bottom: 15px; }
        .reasoning-panel { background: #f8f9fa; border-left: 4px solid #3498db; padding: 15px; margin-bottom: 20px; font-size: 14px; }
        .reasoning-panel p { margin-top: 0; }
        .trade-item { margin-bottom: 15px; padding-bottom: 15px; border-bottom: 1px solid #ecf0f1; }
        .trade-item:last-child { border-bottom: none; }
        .badge { display: inline-block; padding: 4px 8px; border-radius: 4px; font-size: 12px; font-weight: bold; color: #fff; margin-right: 10px; }
        .badge.buy { background-color: #27ae60; }
        .badge.sell { background-color: #e74c3c; }
        .badge.hold { background-color: #3498db; }
        .badge.watch { background-color: #f39c12; }
        .insight { display: block; margin-top: 8px; font-size: 13px; color: #555; }
        .news-item { margin-bottom: 10px; font-size: 14px; }
        .news-item a { color: #3498db; text-decoration: none; }
        .news-item a:hover { text-decoration: underline; }
        .footer { background: #ecf0f1; padding: 15px; text-align: center; font-size: 12px; color: #7f8c8d; }
    </style>
    """

    @staticmethod
    def _render_latex_to_img(text):
        """Converts LaTeX $$block$$ and $inline$ syntax to CodeCogs image URL tags for email rendering."""
        if not text: return ""
        
        # Replace block $$ ... $$
        def repl_block(m):
            math = m.group(1).strip()
            encoded = urllib.parse.quote(math)
            return f'<div style="text-align: center; margin: 15px 0;"><img src="https://latex.codecogs.com/png.image?\\dpi{{150}}\\bg{{white}}{encoded}" alt="{math}" /></div>'
            
        # Replace inline $ ... $
        def repl_inline(m):
            math = m.group(1).strip()
            encoded = urllib.parse.quote(math)
            return f'<img src="https://latex.codecogs.com/png.image?\\dpi{{110}}\\bg{{white}}{encoded}" alt="{math}" style="vertical-align: middle;" />'
            
        text = re.sub(r'\$\$(.*?)\$\$', repl_block, text)
        text = re.sub(r'\$(.*?)\$', repl_inline, text)
        return text

    @staticmethod
    def _format_market_insights(market_context):
        if not market_context or not market_context.get("market_context_bullets"):
            return "<p>No market context available.</p>"
        html = "<ul style='padding-left: 20px;'>"
        for bullet in market_context["market_context_bullets"]:
            theme = bullet.get("theme", "Observation")
            exp = bullet.get("explanation", "")
            html += f"<li style='margin-bottom: 8px;'><strong>{theme}:</strong> {exp}</li>"
        html += "</ul>"
        return html

    @staticmethod
    def _format_news(news_articles):
        if not news_articles:
            return ""
        html = f"<h2 class='section-title'>📰 News & Sources</h2>"
        html += "<ul style='padding-left: 20px; margin-bottom: 20px;'>"
        for article in news_articles:
            title = article.get('title', 'Article')
            url = article.get('article_url', '#')
            # fallback for the key name from market_intelligence
            if url == '#' and 'link' in article:
                url = article['link']
            summary = article.get("summary", "")
            summary_html = f" - {summary}" if summary else ""
            html += f"<li style='margin-bottom: 8px;'><a href='{url}'><strong>{title}</strong></a>{summary_html}</li>"
        html += "</ul>"
        return html

    @staticmethod
    def _format_trades_html(analysis):
        """Helper to format trades from AI analysis dict into HTML."""
        if not analysis:
             return "<p>No trades executed.</p>"
             
        import re
        html = "<h2 class='section-title'>🔄 Executed Rebalancing Trades</h2>"
        if analysis.get("buys"):
            html += f"<h3 style='color: #27ae60; margin-top: 15px;'>🟢 BUY EXECUTIONS</h3>"
            html += "<ul style='list-style-type: none; padding-left: 0;'>"
            for item in analysis["buys"]:
                 header = item.get('header', f"**{item.get('ticker', '')} ({item.get('qty', '')} Shares):**")
                 reason = item.get('reason', '')
                 header_html = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', header)
                 reason_html = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', reason)
                 html += f"<li style='margin-bottom: 10px;'>{header_html} {reason_html}</li>"
            html += "</ul>"
        if analysis.get("sells"):
            html += f"<h3 style='color: #e74c3c; margin-top: 15px;'>🔴 SELL EXECUTIONS</h3>"
            html += "<ul style='list-style-type: none; padding-left: 0;'>"
            for item in analysis["sells"]:
                 header = item.get('header', f"**{item.get('ticker', '')} ({item.get('qty', '')} Shares):**")
                 reason = item.get('reason', '')
                 header_html = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', header)
                 reason_html = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', reason)
                 html += f"<li style='margin-bottom: 10px;'>{header_html} {reason_html}</li>"
            html += "</ul>"
            
        holds_html = ""
        if analysis.get("holds"):
            holds_html += f"<h2 class='section-title'>🛡️ Core Defensive Holds</h2>"
            holds_html += f"<table style='width: 100%; border-collapse: collapse; margin-top: 10px; margin-bottom: 20px; font-size: 14px;'>"
            holds_html += f"<tr style='background: #34495e; color: #ecf0f1;'><th style='padding: 10px; text-align: left; border: 1px solid #bdc3c7;'>Asset(s)</th><th style='padding: 10px; text-align: left; border: 1px solid #bdc3c7;'>Aegis Rationale</th></tr>"
            for item in analysis["holds"]:
                 assets = item.get('assets', item.get('ticker', ''))
                 reason = item.get('reason', '')
                 reason_html = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', reason)
                 holds_html += f"<tr><td style='padding: 10px; border: 1px solid #bdc3c7;'><strong>{assets}</strong></td><td style='padding: 10px; border: 1px solid #bdc3c7;'>{reason_html}</td></tr>"
            holds_html += f"</table>"
            
        if html == "<h2 class='section-title'>🔄 Executed Rebalancing Trades</h2>":
            html = ""
            
        return html + holds_html if (html or holds_html) else "<p>No trades executed.</p>"

    @staticmethod
    def get_watchdog_content(movers, user_name="User"):
        """Generates HTML content for the Daily Watchdog Alert."""
        count = len(movers)
        movers.sort(key=lambda x: abs(x[1]), reverse=True)
        
        portfolio_rows = ""
        for sym, pct in movers:
            change_str = f"{pct*100:+.2f}%"
            portfolio_rows += f"<div class='trade-item'><span class='badge watch'>WATCH</span> <strong>{sym}</strong>: {change_str}</div>"
        
        trigger_asset = movers[0][0] if movers else "N/A"
        actual_change = movers[0][1] * 100 if movers else 0.0
        
        subject = f"⚠️ [Action Required] Aegis: High Volatility Detected in {trigger_asset}"
        date_str = datetime.date.today().isoformat()
        
        html = f"""
        <html>
        <head>{EmailTemplates._BASE_CSS}</head>
        <body>
            <div class='container'>
                <div class='header' style='background: #e74c3c;'>
                    <h1>High Volatility Detected</h1>
                    <p>Daily Update - {date_str}</p>
                </div>
                <div class='content'>
                    <p>Hey {user_name}, Aegis detected significant market movements in your portfolio.</p>
                    
                    <div class='reasoning-panel' style='border-left-color: #e74c3c;'>
                        <strong>Rebalance Triggered:</strong> True<br>
                        <strong>Trigger Asset:</strong> {trigger_asset}<br>
                        <strong>Volatility Threshold:</strong> 10%<br>
                        <strong>Actual Change:</strong> {actual_change:+.2f}%<br>
                        <br>
                        <strong>Action Summary:</strong> In response, Aegis strongly recommends a mid-cycle rebalance sequence to secure your profits and realign your risk exposure to your target baseline.
                    </div>

                    <h2 class='section-title'>Portfolio Watchlist</h2>
                    {portfolio_rows}
                    
                    <h2 class='section-title'>Instruction</h2>
                    <p>Run the agent in rebalance mode:<br>
                    <code>./run_agent.sh interactive rebalance</code></p>
                </div>
                <div class='footer'>Aegis - Your Autonomous Investment Agent</div>
            </div>
        </body>
        </html>
        """
        return subject, html.strip()

    @staticmethod
    def get_watchdog_safe_content(positions, user_name="User"):
        """Fallback template if Gemini fails to generate the Daily Pulse."""
        subject = "🛡️ Aegis: Daily Portfolio Status"
        date_str = datetime.date.today().isoformat()
        html = f"""
        <html>
        <head>{EmailTemplates._BASE_CSS}</head>
        <body>
            <div class='container'>
                <div class='header' style='background: #27ae60;'>
                    <h1>Market Status: Safe</h1>
                    <p>Daily Update - {date_str}</p>
                </div>
                <div class='content'>
                    <p>Hey {user_name}, Aegis has scanned your portfolio. All assets are trading within normal volatility bounds.</p>
                    <p>The Masterclass module is currently unavailable.</p>
                </div>
                <div class='footer'>Aegis - Your Autonomous Investment Agent</div>
            </div>
        </body>
        </html>
        """
        return subject, html.strip()

    @staticmethod
    def get_daily_pulse_content(pulse_data):
        """Generates HTML content for the new Daily Pulse Masterclass."""
        subject = "🎓 Aegis: Daily Pulse & Masterclass"
        date_str = datetime.date.today().isoformat()
        user_name = pulse_data.get("user_name", "User")
        
        # 0. Market Overview
        market = pulse_data.get("market_overview", {})
        summary_html = f"<p>{market.get('summary', '')}</p>"
        news_html = ""
        for n in market.get("key_news", []):
            title = n.get("title", "Article")
            url = n.get("url", "#")
            summary = n.get("summary", "")
            news_html += f"<li style='margin-bottom: 10px;'><a href='{url}'><strong>[{title}]</strong></a> - {summary}</li>"
        
        if news_html:
            news_html = f"<ul style='list-style-type: none; padding-left: 0;'>{news_html}</ul>"

        # 1. Holdings Context
        consolidation_status = pulse_data.get("portfolio_consolidation_status", "Portfolio Context: Daily Updates")
        holdings_html = f"<div style='margin-bottom: 10px;'><strong>{consolidation_status}</strong></div>"
        
        holdings_html += f"<table style='width: 100%; border-collapse: collapse; margin-top: 10px; margin-bottom: 20px; font-size: 14px;'>"
        holdings_html += f"<tr style='background: #34495e; color: #ecf0f1;'><th style='padding: 10px; text-align: left; border: 1px solid #bdc3c7;'>Sector</th><th style='padding: 10px; text-align: left; border: 1px solid #bdc3c7;'>Tickers</th><th style='padding: 10px; text-align: left; border: 1px solid #bdc3c7;'>Aegis Rationale</th></tr>"
        
        for item in pulse_data.get("holdings_context", []):
            sector = item.get("sector", "")
            tickers = item.get("tickers", "")
            insight = item.get("rag_insight", "")
            holdings_html += f"<tr><td style='padding: 10px; border: 1px solid #bdc3c7;'><strong>{sector}</strong></td><td style='padding: 10px; border: 1px solid #bdc3c7;'>{tickers}</td><td style='padding: 10px; border: 1px solid #bdc3c7;'>{insight}</td></tr>"
            
        holdings_html += f"</table>"
            
        # 2. Masterclass Section
        masterclass = pulse_data.get("masterclass", {})
        topic = masterclass.get("topic", "Daily Concept")
        intro = masterclass.get("introduction", "")
        formula = masterclass.get("formula", "")
        
        formula_html = ""
        if formula:
            rendered_formula = EmailTemplates._render_latex_to_img(formula)
            formula_html = f"""
            <div style='background: #f8f9fa; color: #2c3e50; padding: 15px; margin: 15px 0; border: 1px solid #bdc3c7; border-radius: 5px; font-family: Courier, monospace; text-align: center; font-size: 16px;'>
                {rendered_formula}
            </div>
            """
        
        concepts_html = ""
        for c in masterclass.get("concepts", []):
            term = EmailTemplates._render_latex_to_img(c.get('term', ''))
            definition = EmailTemplates._render_latex_to_img(c.get('definition', ''))
            concepts_html += f"<li style='margin-bottom: 8px;'><strong>{term}</strong>: {definition}</li>"
            
        signal = masterclass.get("key_signal", {})
        signal_html = ""
        if signal:
            signal_html = f"""
            <div style='background: #eaf2f8; padding: 10px; border-left: 3px solid #3498db; margin-top: 15px;'>
                <strong>Key Signal: {signal.get('name', '')}</strong><br>
                <span style='font-size: 13px;'>{signal.get('description', '')}</span>
            </div>
            """

        # 3. Daily Reading & Watchlist
        reading_html = "<ul style='padding-left: 0; list-style-type: none;'>"
        for r in pulse_data.get("daily_reading", []):
            title = r.get("title", "Article")
            url = r.get("url", "#")
            desc = r.get("description", "")
            reading_html += f"<li style='margin-bottom: 10px;'>📖 <a href='{url}'><strong>{title}</strong></a> - {desc}</li>"
            
        video = pulse_data.get("video_recommendation", {})
        video_html = ""
        if video:
            v_title = video.get("title", "Watch")
            v_url = video.get("url", "#")
            v_desc = video.get("description", "")
            reading_html += f"<li style='margin-bottom: 10px;'>▶️ <a href='{v_url}'><strong>{v_title}</strong></a> - {v_desc}</li>"
            
        reading_html += "</ul>"

        html = f"""
        <html>
        <head>{EmailTemplates._BASE_CSS}</head>
        <body>
            <div class='container'>
                <div class='header' style='background: #2980b9;'>
                    <h1>Daily Pulse & Masterclass</h1>
                    <p>{date_str}</p>
                </div>
                <div class='content'>
                    <p>Hey {user_name}, here is your daily market pulse and trading masterclass.</p>
                    
                    <h2 class='section-title'>Market Overview</h2>
                    <div class='reasoning-panel' style='border-left-color: #f39c12;'>
                        {summary_html}
                        {news_html}
                    </div>

                    <h2 class='section-title'>Portfolio Context</h2>
                    <div class='reasoning-panel' style='border-left-color: #2980b9;'>
                        {holdings_html}
                    </div>
                    
                    <h2 class='section-title'>Aegis Masterclass: {topic}</h2>
                    <p>{intro}</p>
                    {formula_html}
                    <ul>
                        {concepts_html}
                    </ul>
                    {signal_html}
                    
                    <h2 class='section-title'>Daily Reading & Watchlist</h2>
                    {reading_html}
                </div>
                <div class='footer'>Aegis - Your Autonomous Investment Agent</div>
            </div>
        </body>
        </html>
        """
        return subject, html.strip()

    @staticmethod
    def get_rebalance_content(market_context=None, analysis=None, user_name="User"):
        """Generates HTML content for Bi-Weekly Rebalance using RAG context."""
        date_str = datetime.date.today().isoformat()
        market_insight_html = EmailTemplates._format_market_insights(market_context)
        news_html = EmailTemplates._format_news(market_context.get("news_articles", [])) if market_context else ""
        trades_html = EmailTemplates._format_trades_html(analysis)
        
        subject = f"⚖️ Aegis: Bi-weekly Rebalance Report"
        
        html = f"""
        <html>
        <head>{EmailTemplates._BASE_CSS}</head>
        <body>
            <div class='container'>
                <div class='header'>
                    <h1>Bi-Weekly Rebalance</h1>
                    <p>Date: {date_str}</p>
                </div>
                <div class='content'>
                    <p>Hey {user_name}, here is what Aegis has executed for you:</p>
                    <h2 class='section-title'>Market Context</h2>
                    <div class='reasoning-panel'>
                        {market_insight_html}
                    </div>
                    
                    {trades_html}
                    
                    {news_html}
                </div>
                <div class='footer'>Aegis - Your Autonomous Investment Agent</div>
            </div>
        </body>
        </html>
        """
        return subject, html.strip()

    @staticmethod
    def get_invest_content(monthly_inv, market_context=None, analysis=None, user_name="User"):
        """Generates HTML content for Monthly Investment using RAG context."""
        date_str = datetime.date.today().isoformat()
        market_insight_html = EmailTemplates._format_market_insights(market_context)
        news_html = EmailTemplates._format_news(market_context.get("news_articles", [])) if market_context else ""
        trades_html = EmailTemplates._format_trades_html(analysis)
        
        subject = f"💰 Aegis: Monthly Investment Report"
        
        html = f"""
        <html>
        <head>{EmailTemplates._BASE_CSS}</head>
        <body>
            <div class='container'>
                <div class='header' style='background: #8e44ad;'>
                    <h1>Monthly Investment</h1>
                    <p>Date: {date_str} | Deposit: ${monthly_inv:,.2f}</p>
                </div>
                <div class='content'>
                    <p>Hey {user_name}, here is what Aegis has executed for you:</p>
                    <h2 class='section-title'>Market Context</h2>
                    <div class='reasoning-panel' style='border-left-color: #8e44ad;'>
                        {market_insight_html}
                    </div>
                    
                    {trades_html}
                    
                    {news_html}
                </div>
                <div class='footer'>Aegis - Your Autonomous Investment Agent</div>
            </div>
        </body>
        </html>
        """
        return subject, html.strip()
