"""
Web Dashboard using Python's built-in http.server.
Serves a single-page app with real-time backtest results.
"""

import json
import os
from http.server import HTTPServer, BaseHTTPRequestHandler
from datetime import datetime
from urllib.parse import urlparse, parse_qs


def create_app(backtest_runner):
    """
    Create and return a simple HTTP server for the dashboard.

    Args:
        backtest_runner: Callable that accepts strategy name and returns backtest results dict.
    """

    class DashboardHandler(BaseHTTPRequestHandler):
        def log_message(self, format, *args):
            pass  # Suppress default logging

        def _send_json(self, data: dict, status: int = 200):
            body = json.dumps(data, default=str).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(body)

        def _send_html(self, html: str):
            body = html.encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _send_file(self, filepath: str, content_type: str):
            try:
                with open(filepath, "rb") as f:
                    body = f.read()
                self.send_response(200)
                self.send_header("Content-Type", content_type)
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
            except FileNotFoundError:
                self.send_error(404)

        def do_GET(self):
            parsed = urlparse(self.path)
            path = parsed.path
            params = parse_qs(parsed.query)

            if path == "/" or path == "/index.html":
                template_path = os.path.join(os.path.dirname(__file__), "templates", "index.html")
                with open(template_path, "r") as f:
                    self._send_html(f.read())

            elif path == "/api/strategies":
                strategies = ["MA_Crossover", "RSI", "Bollinger_Bands", "MACD", "Mean_Reversion"]
                self._send_json({"strategies": strategies})

            elif path == "/api/backtest":
                strategy = params.get("strategy", ["MA_Crossover"])[0]
                symbol = params.get("symbol", ["AAPL"])[0]
                days = int(params.get("days", [365])[0])
                try:
                    results = backtest_runner(strategy, symbol, days)
                    self._send_json(results)
                except Exception as e:
                    self._send_json({"error": str(e)}, 500)

            elif path.startswith("/static/"):
                static_dir = os.path.join(os.path.dirname(__file__), "static")
                rel_path = path[len("/static/"):]
                filepath = os.path.join(static_dir, rel_path)
                ext = os.path.splitext(filepath)[1]
                content_types = {".css": "text/css", ".js": "application/javascript"}
                self._send_file(filepath, content_types.get(ext, "text/plain"))

            else:
                self.send_error(404)

    return HTTPServer, DashboardHandler
