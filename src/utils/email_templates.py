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
        .badge.green { background-color: #27ae60; }
        .badge.yellow { background-color: #f39c12; }
        .badge.red { background-color: #e74c3c; }
        .perf-positive { color: #27ae60; font-weight: bold; }
        .perf-negative { color: #e74c3c; font-weight: bold; }
        .perf-neutral  { color: #7f8c8d; font-weight: bold; }
        .metric-card { display: inline-block; padding: 8px 14px; border-radius: 6px; margin: 4px; font-size: 13px; text-align: center; }
        .corrective-panel { background: #fff3cd; border-left: 4px solid #f39c12; padding: 15px; margin-bottom: 20px; font-size: 14px; border-radius: 0 4px 4px 0; }
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
        html = "<h2 class='section-title'>🔄 Executed Trades</h2>"
        if analysis.get("buys"):
            html += f"<h3 style='color: #27ae60; margin-top: 15px;'>🟢 LIMIT BUY EXECUTIONS (GTC)</h3>"
            html += "<ul style='list-style-type: none; padding-left: 0;'>"
            for item in analysis["buys"]:
                 limit_str = f" @ Limit ${item.get('limit_price', 0.0):.2f}" if 'limit_price' in item else ""
                 header = item.get('header', f"**{item.get('ticker', '')} ({item.get('qty', '')} Shares{limit_str}):**")
                 reason = item.get('reason', '')
                 header_html = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', header)
                 reason_html = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', reason)
                 html += f"<li style='margin-bottom: 10px;'>{header_html} {reason_html}</li>"
            html += "</ul>"
        if analysis.get("sells"):
            html += f"<h3 style='color: #e74c3c; margin-top: 15px;'>🔴 LIMIT SELL EXECUTIONS (GTC)</h3>"
            html += "<ul style='list-style-type: none; padding-left: 0;'>"
            for item in analysis["sells"]:
                 limit_str = f" @ Limit ${item.get('limit_price', 0.0):.2f}" if 'limit_price' in item else ""
                 header = item.get('header', f"**{item.get('ticker', '')} ({item.get('qty', '')} Shares{limit_str}):**")
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
            
        if html == "<h2 class='section-title'>🔄 Executed Trades</h2>":
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
    def _format_performance_dashboard(portfolio_stats, benchmark_stats):
        """Renders the daily performance dashboard section."""
        if not portfolio_stats:
            return ""

        daily_ret = portfolio_stats.get('daily_return_pct', 0)
        daily_vol = portfolio_stats.get('daily_volatility', 0)
        top_gainers = portfolio_stats.get('top_gainers', [])
        top_losers  = portfolio_stats.get('top_losers', [])
        total_value = portfolio_stats.get('total_value', 0)

        # Return badge color
        if daily_ret > 0.5:
            ret_color = '#27ae60'
        elif daily_ret < -0.5:
            ret_color = '#e74c3c'
        else:
            ret_color = '#7f8c8d'

        ret_sign = '+' if daily_ret >= 0 else ''

        # Volatility label
        if daily_vol < 0.5:
            vol_label, vol_color = 'LOW', '#27ae60'
        elif daily_vol < 1.5:
            vol_label, vol_color = 'MODERATE', '#f39c12'
        else:
            vol_label, vol_color = 'HIGH', '#e74c3c'

        # Benchmark row
        spy_d = benchmark_stats.get('spy_daily_pct') if benchmark_stats else None
        qqq_d = benchmark_stats.get('qqq_daily_pct') if benchmark_stats else None
        spy_str = f"{spy_d:+.2f}%" if spy_d is not None else 'N/A'
        qqq_str = f"{qqq_d:+.2f}%" if qqq_d is not None else 'N/A'
        spy_color = '#27ae60' if (spy_d or 0) >= 0 else '#e74c3c'
        qqq_color = '#27ae60' if (qqq_d or 0) >= 0 else '#e74c3c'

        # Build movers table
        movers_rows = ""
        for sym, pct in top_gainers:
            movers_rows += f"<tr><td style='padding:6px 10px;'><strong>{sym}</strong></td><td style='padding:6px 10px; color:#27ae60; font-weight:bold;'>{pct:+.2f}%</td><td style='padding:6px 10px;'>▲ Top Gainer</td></tr>"
        for sym, pct in top_losers:
            movers_rows += f"<tr><td style='padding:6px 10px;'><strong>{sym}</strong></td><td style='padding:6px 10px; color:#e74c3c; font-weight:bold;'>{pct:+.2f}%</td><td style='padding:6px 10px;'>▼ Top Loser</td></tr>"
        if not movers_rows:
            movers_rows = "<tr><td colspan='3' style='padding:6px 10px; color:#7f8c8d;'>All positions within normal ranges.</td></tr>"

        html = f"""
        <h2 class='section-title'>📊 Daily Performance Dashboard</h2>
        <div class='reasoning-panel' style='border-left-color: {ret_color};'>
            <table style='width:100%; border-collapse:collapse;'>
              <tr>
                <td style='width:33%; text-align:center; padding:10px;'>
                  <div style='font-size:12px; color:#7f8c8d; margin-bottom:4px;'>PORTFOLIO DAILY RETURN</div>
                  <div style='font-size:24px; font-weight:bold; color:{ret_color};'>{ret_sign}{daily_ret:.2f}%</div>
                </td>
                <td style='width:33%; text-align:center; padding:10px; border-left:1px solid #ecf0f1;'>
                  <div style='font-size:12px; color:#7f8c8d; margin-bottom:4px;'>SPY (S&P 500)</div>
                  <div style='font-size:20px; font-weight:bold; color:{spy_color};'>{spy_str}</div>
                </td>
                <td style='width:33%; text-align:center; padding:10px; border-left:1px solid #ecf0f1;'>
                  <div style='font-size:12px; color:#7f8c8d; margin-bottom:4px;'>QQQ (Nasdaq)</div>
                  <div style='font-size:20px; font-weight:bold; color:{qqq_color};'>{qqq_str}</div>
                </td>
              </tr>
            </table>
            <div style='margin-top:8px; text-align:center; font-size:12px; color:#7f8c8d;'>
              Intraday Volatility: <span style='color:{vol_color}; font-weight:bold;'>{vol_label}</span>
              &nbsp;|&nbsp; Portfolio Value: <strong>${total_value:,.2f}</strong>
            </div>
        </div>
        <h3 style='color:#2c3e50; margin-bottom:10px;'>Today's Top Movers</h3>
        <table style='width:100%; border-collapse:collapse; font-size:14px; margin-bottom:20px;'>
          <tr style='background:#34495e; color:#ecf0f1;'>
            <th style='padding:8px 10px; text-align:left;'>Ticker</th>
            <th style='padding:8px 10px; text-align:left;'>Intraday Change</th>
            <th style='padding:8px 10px; text-align:left;'>Note</th>
          </tr>
          {movers_rows}
        </table>
        """
        return html

    @staticmethod
    def _format_since_last_action(portfolio_stats, benchmark_stats):
        """Renders the 'since last rebalance/invest' performance comparison."""
        if not portfolio_stats:
            return ""

        since_pct  = portfolio_stats.get('since_last_action_pct')
        since_days = portfolio_stats.get('since_last_action_days')
        weekly_pct = portfolio_stats.get('weekly_return_pct')
        spy_w  = benchmark_stats.get('spy_weekly_pct') if benchmark_stats else None
        qqq_w  = benchmark_stats.get('qqq_weekly_pct') if benchmark_stats else None

        if since_pct is None and weekly_pct is None:
            return ""  # Not enough history yet

        def _pct_html(pct, label):
            if pct is None:
                return f"<td style='padding:8px 10px;'>{label}</td><td style='padding:8px 10px; color:#7f8c8d;'>N/A</td><td style='padding:8px 10px;'>—</td>"
            color = '#27ae60' if pct >= 0 else '#e74c3c'
            icon  = '🟢' if pct >= 0 else '🔴'
            return f"<td style='padding:8px 10px;'>{label}</td><td style='padding:8px 10px; color:{color}; font-weight:bold;'>{pct:+.2f}%</td><td style='padding:8px 10px;'>{icon}</td>"

        period_label = f"Since Last Action ({since_days}d ago)" if since_days else "Cumulative Return"

        html = f"""
        <h2 class='section-title'>📅 Since Last Action</h2>
        <div class='reasoning-panel' style='border-left-color: #8e44ad;'>
          <table style='width:100%; border-collapse:collapse; font-size:14px;'>
            <tr style='background:#34495e; color:#ecf0f1;'>
              <th style='padding:8px 10px; text-align:left;'>Metric</th>
              <th style='padding:8px 10px; text-align:left;'>Return</th>
              <th style='padding:8px 10px; text-align:left;'>Status</th>
            </tr>
            <tr>{_pct_html(since_pct, period_label)}</tr>
            <tr style='background:#f8f9fa;'>{_pct_html(weekly_pct, 'Last 7 Days')}</tr>
            <tr>{_pct_html(spy_w, 'SPY 7-Day (Benchmark)')}</tr>
            <tr style='background:#f8f9fa;'>{_pct_html(qqq_w, 'QQQ 7-Day (Benchmark)')}</tr>
          </table>
        </div>
        """
        return html

    @staticmethod
    def _format_assessment(assessment):
        """Renders the categorical portfolio assessment section."""
        if not assessment or not isinstance(assessment, dict):
            return ""

        flag = str(assessment.get('assessment_flag', 'green')).lower()
        overall_summary = assessment.get('overall_summary', '')
        categories = assessment.get('categorical_assessments', [])
        if not isinstance(categories, list):
            categories = []

        flag_colors = {'green': '#27ae60', 'yellow': '#f39c12', 'red': '#e74c3c'}
        flag_color = flag_colors.get(flag, '#7f8c8d')
        flag_label = flag.upper()

        category_html = ""
        for cat in categories:
            if not isinstance(cat, dict): continue
            name = cat.get('category_name', 'Unnamed Category')
            tickers_raw = cat.get('tickers', [])
            tickers = ", ".join(tickers_raw) if isinstance(tickers_raw, list) else str(tickers_raw)
            schema = cat.get('mathematical_schema', 'N/A')
            observed = cat.get('performance_vs_benchmark', 'N/A')
            analysis = cat.get('reasoning', '')
            status_icon = cat.get('status_flag', '⚪')
            
            # Formatted citations
            citations_html = ""
            citations = cat.get('sources') or cat.get('citations', [])
            if isinstance(citations, list):
                for cite in citations:
                    if not isinstance(cite, dict): continue
                    title = cite.get('title', 'Source')
                    url = cite.get('url', '#')
                    citations_html += f"<div style='font-size:12px; margin-top:4px;'>🔗 <a href='{url}' style='color:#3498db; text-decoration:none;'>{title}</a></div>"
            
            if citations_html:
                citations_html = f"<div style='margin-top:10px; border-top:1px solid #eee; padding-top:8px;'><strong>Sources Consulted:</strong>{citations_html}</div>"

            # Queued fix if present
            fix_html = ""
            fix = cat.get('queued_fix')
            if isinstance(fix, dict):
                reason = fix.get('human_reason', 'Corrective action required.')
                fix_html = f"""
                <div style='margin-top:12px; padding:10px; background:#fff3cd; border-left:3px solid #f39c12; border-radius:0 4px 4px 0;'>
                  <strong>💡 Queued Fix:</strong> {reason}
                </div>"""

            category_html += f"""
            <div style='margin-bottom:25px; border:1px solid #ecf0f1; border-radius:6px; overflow:hidden;'>
              <div style='background:#f8f9fa; padding:10px; border-bottom:1px solid #ecf0f1;'>
                <span style='float:right;'>{status_icon}</span>
                <strong>{name}</strong> <span style='font-size:12px; color:#7f8c8d;'>({tickers})</span>
              </div>
              <div style='padding:15px; font-size:14px;'>
                <div style='margin-bottom:10px;'>
                  <span style='color:#7f8c8d; font-size:12px;'>MATHEMATICAL SCHEMA:</span><br/>
                  <code style='background:#f1f2f6; padding:2px 4px; border-radius:3px; font-family:monospace;'>{schema}</code>
                </div>
                <div style='margin-bottom:10px;'>
                  <span style='color:#7f8c8d; font-size:12px;'>PERFORMANCE:</span><br/>
                  <strong>{observed}</strong>
                </div>
                <p style='margin:0; line-height:1.4;'>{analysis}</p>
                {citations_html}
                {fix_html}
              </div>
            </div>
            """

        # Global remediation suggestion
        remediation_html = ""
        global_fix = assessment.get('rebalance_suggestion')
        if isinstance(global_fix, dict):
            reason = global_fix.get('human_reason', 'Strategic rebalance recommended.')
            remediation_html = f"""
            <div style='margin-top:20px; padding:15px; background:#fff3cd; border:1px solid #ffeeba; border-radius:6px;'>
              <h3 style='margin:0 0 10px 0; color:#856404; font-size:16px;'>🛠️ Aegis Remediation Strategy</h3>
              <p style='margin:0; font-size:14px; line-height:1.5;'>{reason}</p>
              <div style='margin-top:10px; font-size:12px; color:#856404; font-style:italic;'>
                *This strategy will be automatically applied in the next rebalance cycle.
              </div>
            </div>"""

        html = f"""
        <h2 class='section-title'>🔍 Honest Categorical Assessment</h2>
        <div class='reasoning-panel' style='border-left-color: {flag_color};'>
          <div style='margin-bottom:20px; padding:15px; background:#f8f9fa; border-radius:6px; border:1px solid #eee;'>
            <span class='badge' style='background:{flag_color}; color:#fff; font-size:14px; padding:5px 10px;'>{flag_label}</span>
            <div style='margin-top:10px; font-size:16px; line-height:1.5; color:#2c3e50;'>
              <strong>Verdict:</strong> {overall_summary}
            </div>
          </div>
          
          <h3 style='font-size:14px; color:#7f8c8d; margin-bottom:15px; text-transform:uppercase; letter-spacing:1px;'>Sector-by-Sector Breakdown</h3>
          {category_html}
          
          {remediation_html}
        </div>
        """
        return html

    @staticmethod
    def _format_corrective_context(pending_suggestions, analysis=None):
        """Renders the corrective action panel for rebalance/invest emails."""
        if not pending_suggestions:
            return ""

        # Check if analysis has an explicit corrective_context from AI
        ai_context = ""
        if analysis and analysis.get('corrective_context'):
            ai_context = f"<p style='margin-bottom:10px;'>{analysis['corrective_context']}</p>"

        items_html = ""
        for s in pending_suggestions:
            date   = s.get('date', 'unknown date')
            reason = s.get('human_reason', '')
            constraints = s.get('constraints', {})
            targets = ', '.join(constraints.get('force_include', [])) or ''
            excludes = ', '.join(constraints.get('force_exclude', [])) or ''
            floors = ', '.join(f"{t}: ≥{v:.0%}" for t, v in constraints.get('force_weight_floor', {}).items()) or ''
            detail_parts = []
            if targets:  detail_parts.append(f'<strong>Increase:</strong> {targets}')
            if excludes: detail_parts.append(f'<strong>Reduce:</strong> {excludes}')
            if floors:   detail_parts.append(f'<strong>Weight floors:</strong> {floors}')
            detail = ' &nbsp;|&nbsp; '.join(detail_parts)
            items_html += f"""
            <li style='margin-bottom:10px;'>
              <strong>[{date}]</strong> {reason}<br/>
              <span style='font-size:12px; color:#7f8c8d;'>{detail}</span>
            </li>"""

        html = f"""
        <h2 class='section-title'>🔧 Addressing Prior Underperformance</h2>
        <div class='corrective-panel'>
          {ai_context}
          <p style='margin-bottom:8px;'><strong>The following issues flagged by Aegis's daily assessment are being corrected by this rebalance:</strong></p>
          <ul style='padding-left:20px; margin:0;'>{items_html}</ul>
        </div>
        """
        return html

    @staticmethod
    def get_daily_pulse_content(pulse_data):
        """Generates HTML content for the new Daily Pulse Masterclass."""
        subject = "🎓 Aegis: Daily Pulse & Masterclass"
        date_str = datetime.date.today().isoformat()
        user_name = pulse_data.get("user_name", "User")
        
        # 0. Performance Trend (Visual)
        chart_url = pulse_data.get("chart_url")
        chart_html = ""
        if chart_url:
            chart_html = f"""
            <div class='reasoning-panel' style='border-left-color: #27ae60; text-align: center; padding: 10px;'>
              <img src="{chart_url}" alt="Performance Trend" style="max-width: 100%; height: auto; border-radius: 4px;" />
            </div>
            """

        # 0. Market Overview
        market = pulse_data.get("market_overview", {})
        if not isinstance(market, dict):
            market = {"summary": str(market)}
        summary_html = f"<p>{market.get('summary', '')}</p>"
        news_html = ""
        key_news = market.get("key_news", [])
        if not isinstance(key_news, list):
            key_news = []
            
        for n in key_news:
            if not isinstance(n, dict): continue
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
            if not isinstance(item, dict): continue
            sector = item.get("sector", "")
            tickers = item.get("tickers", "")
            insight = item.get("rag_insight", "")
            holdings_html += f"<tr><td style='padding: 10px; border: 1px solid #bdc3c7;'><strong>{sector}</strong></td><td style='padding: 10px; border: 1px solid #bdc3c7;'>{tickers}</td><td style='padding: 10px; border: 1px solid #bdc3c7;'>{insight}</td></tr>"
            
        holdings_html += f"</table>"
            
        # 2. Masterclass Section
        masterclass = pulse_data.get("masterclass", {})
        if not isinstance(masterclass, dict):
            masterclass = {"topic": str(masterclass)}
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
        concepts = masterclass.get("concepts", [])
        if not isinstance(concepts, list):
            concepts = []
            
        for c in concepts:
            if not isinstance(c, dict): continue
            term = c.get("term", "")
            defn = c.get("definition", "")
            concepts_html += f"<li style='margin-bottom: 8px;'><strong>{term}</strong>: {defn}</li>"
            
        signal = masterclass.get("key_signal", {})
        signal_html = ""
        if signal and isinstance(signal, dict):
            signal_html = f"""
            <div style='background: #eaf2f8; padding: 10px; border-left: 3px solid #3498db; margin-top: 15px;'>
                <strong>Key Signal: {signal.get('name', '')}</strong><br>
                <span style='font-size: 13px;'>{signal.get('description', '')}</span>
            </div>
            """

        # 3. Daily Reading & Watchlist
        reading_html = "<ul style='padding-left: 0; list-style-type: none;'>"
        daily_reading = pulse_data.get("daily_reading", [])
        if not isinstance(daily_reading, list):
            daily_reading = []
            
        for r in daily_reading:
            if not isinstance(r, dict): continue
            title = r.get("title", "Reading")
            url = r.get("url", "#")
            desc = r.get("description", "")
            reading_html += f"<li style='margin-bottom: 10px;'>📖 <a href='{url}'><strong>{title}</strong></a> - {desc}</li>"
            
        video = pulse_data.get("video_recommendation", {})
        video_html = ""
        if video and isinstance(video, dict):
            v_title = video.get("title", "Watch")
            v_url = video.get("url", "#")
            v_desc = video.get("description", "")
            reading_html += f"<li style='margin-bottom: 10px;'>▶️ <a href='{v_url}'><strong>{v_title}</strong></a> - {v_desc}</li>"
            
        reading_html += "</ul>"

        portfolio_stats = pulse_data.get('portfolio_stats')
        benchmark_stats = pulse_data.get('benchmark_stats')
        assessment      = pulse_data.get('assessment')

        perf_dashboard_html = EmailTemplates._format_performance_dashboard(portfolio_stats, benchmark_stats)
        since_last_html     = EmailTemplates._format_since_last_action(portfolio_stats, benchmark_stats)
        assessment_html     = EmailTemplates._format_assessment(assessment)

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

                    {perf_dashboard_html}
                    {chart_html}
                    {since_last_html}

                    <h2 class='section-title'>Market Overview</h2>
                    <div class='reasoning-panel' style='border-left-color: #f39c12;'>
                        {summary_html}
                        {news_html}
                    </div>

                    <h2 class='section-title'>Portfolio Context</h2>
                    <div class='reasoning-panel' style='border-left-color: #2980b9;'>
                        {holdings_html}
                    </div>

                    {assessment_html}

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
    def get_rebalance_content(market_context=None, analysis=None, user_name="User", pending_suggestions=None):
        """Generates HTML content for Bi-Weekly Rebalance using RAG context."""
        date_str = datetime.date.today().isoformat()
        market_insight_html = EmailTemplates._format_market_insights(market_context)
        news_html = EmailTemplates._format_news(market_context.get("news_articles", [])) if market_context else ""
        trades_html = EmailTemplates._format_trades_html(analysis)
        corrective_html = EmailTemplates._format_corrective_context(pending_suggestions, analysis)
        
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
                    {corrective_html}
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
    def get_volatility_rebalance_content(volatility_trigger, market_context=None, analysis=None, user_name="User"):
        """Generates HTML content for a Rebalance specifically triggered by high volatility."""
        date_str = datetime.date.today().isoformat()
        market_insight_html = EmailTemplates._format_market_insights(market_context)
        news_html = EmailTemplates._format_news(market_context.get("news_articles", [])) if market_context else ""
        trades_html = EmailTemplates._format_trades_html(analysis)
        
        trigger_asset = volatility_trigger.get('asset', 'Unknown')
        actual_change = volatility_trigger.get('change', 0.0) * 100
        
        subject = f"🚨 Aegis: Volatility Rebalance Executed ({trigger_asset})"
        
        html = f"""
        <html>
        <head>{EmailTemplates._BASE_CSS}</head>
        <body>
            <div class='container'>
                <div class='header' style='background: #e67e22;'>
                    <h1>Volatility Response Executed</h1>
                    <p>Date: {date_str}</p>
                </div>
                <div class='content'>
                    <p>Hey {user_name},</p>
                    <p>Earlier today, Aegis detected extreme volatility in <strong>{trigger_asset} ({actual_change:+.2f}%)</strong>. In response, an automated portfolio rebalance has been completed to realign your risk exposure to target baselines.</p>
                    
                    <h2 class='section-title'>Volatility Context & Strategy</h2>
                    <div class='reasoning-panel' style='border-left-color: #e67e22;'>
                        <p><strong>Trigger Event:</strong> {trigger_asset} experienced a major intraday move of {actual_change:+.2f}%.</p>
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
    def get_invest_content(monthly_inv, market_context=None, analysis=None, user_name="User", pending_suggestions=None):
        """Generates HTML content for Monthly Investment using RAG context."""
        date_str = datetime.date.today().isoformat()
        market_insight_html = EmailTemplates._format_market_insights(market_context)
        news_html = EmailTemplates._format_news(market_context.get("news_articles", [])) if market_context else ""
        trades_html = EmailTemplates._format_trades_html(analysis)
        corrective_html = EmailTemplates._format_corrective_context(pending_suggestions, analysis)
        
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
                    {corrective_html}
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
