"""
Module: visualizer.py
Purpose: Generates chart URLs for portfolio performance visualization
         compatible with Gmail (using QuickChart.io).
"""
import json
import urllib.parse

class Visualizer:
    @staticmethod
    def generate_performance_chart_url(history_data, benchmark_history=None):
        """
        Constructs a QuickChart.io URL for a line chart.
        
        history_data: List of dicts with 'date' and 'portfolio_value'
        benchmark_history: List of dicts with 'date' and 'price' (e.g. SPY)
        """
        if not history_data:
            return None

        # Sort and limit to last 30 points
        history_data = sorted(history_data, key=lambda x: x['date'])[-30:]
        labels = [d['date'][5:] for d in history_data] # MM-DD
        
        # Normalize to % change from start of period
        start_val = history_data[0].get('portfolio_value', 1.0)
        portfolio_series = [round((d.get('portfolio_value', start_val) - start_val) / start_val * 100, 2) for d in history_data]
        
        datasets = [
            {
                "label": "Portfolio (%)",
                "data": portfolio_series,
                "borderColor": "rgb(39, 174, 96)", # Green
                "backgroundColor": "rgba(39, 174, 96, 0.1)",
                "fill": True,
                "pointRadius": 0,
                "borderWidth": 3
            }
        ]
        
        if benchmark_history:
            # Match benchmark dates to portfolio dates
            bench_map = {d['date']: d['price'] for d in benchmark_history}
            bench_start = None
            bench_series = []
            
            for d in history_data:
                price = bench_map.get(d['date'])
                if price and bench_start is None:
                    bench_start = price
                
                if bench_start:
                    pct = round((price - bench_start) / bench_start * 100, 2) if price else 0.0
                    bench_series.append(pct)
                else:
                    bench_series.append(0.0)
            
            datasets.append({
                "label": "SPY (%)",
                "data": bench_series,
                "borderColor": "rgb(127, 140, 141)", # Grey
                "fill": False,
                "pointRadius": 0,
                "borderWidth": 2,
                "borderDash": [5, 5]
            })

        chart_config = {
            "type": "line",
            "data": {
                "labels": labels,
                "datasets": datasets
            },
            "options": {
                "title": {"display": True, "text": "30-Day Performance Trend", "fontColor": "#2c3e50"},
                "legend": {"position": "bottom"},
                "scales": {
                    "yAxes": [{
                        "ticks": {"callback": "val => val + '%'"}
                    }]
                }
            }
        }
        
        config_str = json.dumps(chart_config)
        encoded_config = urllib.parse.quote(config_str)
        return f"https://quickchart.io/chart?c={encoded_config}&width=600&height=300&backgroundColor=white"
