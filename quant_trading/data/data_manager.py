"""
Data Manager: caches and serves market data, computes technical indicators.
"""

from datetime import datetime
from typing import Optional
from collections import deque

from .data_feed import DataFeed, Bar


class DataManager:
    """Manages market data subscriptions and indicator computation."""

    def __init__(self, feed: DataFeed, max_window: int = 500):
        self.feed = feed
        self.max_window = max_window
        self._bars: dict[str, deque[Bar]] = {}

    def subscribe(self, symbol: str):
        if symbol not in self._bars:
            self._bars[symbol] = deque(maxlen=self.max_window)

    def load_history(self, symbol: str, start: datetime, end: datetime):
        self.subscribe(symbol)
        bars = self.feed.get_bars(symbol, start, end)
        self._bars[symbol].extend(bars)

    def push_bar(self, bar):
        """Append a single bar (used by streaming/backtesting engine)."""
        symbol = bar.symbol
        self.subscribe(symbol)
        self._bars[symbol].append(bar)

    def get_bars(self, symbol: str, n: Optional[int] = None) -> list[Bar]:
        bars = list(self._bars.get(symbol, []))
        return bars[-n:] if n else bars

    def get_closes(self, symbol: str, n: Optional[int] = None) -> list[float]:
        return [b.close for b in self.get_bars(symbol, n)]

    def get_highs(self, symbol: str, n: Optional[int] = None) -> list[float]:
        return [b.high for b in self.get_bars(symbol, n)]

    def get_lows(self, symbol: str, n: Optional[int] = None) -> list[float]:
        return [b.low for b in self.get_bars(symbol, n)]

    def get_volumes(self, symbol: str, n: Optional[int] = None) -> list[float]:
        return [b.volume for b in self.get_bars(symbol, n)]

    # ── Technical Indicators ──────────────────────────────────────────────

    def sma(self, symbol: str, period: int) -> Optional[float]:
        closes = self.get_closes(symbol, period)
        if len(closes) < period:
            return None
        return sum(closes) / period

    def ema(self, symbol: str, period: int) -> Optional[float]:
        closes = self.get_closes(symbol)
        if len(closes) < period:
            return None
        k = 2 / (period + 1)
        ema_val = sum(closes[:period]) / period
        for price in closes[period:]:
            ema_val = price * k + ema_val * (1 - k)
        return ema_val

    def rsi(self, symbol: str, period: int = 14) -> Optional[float]:
        closes = self.get_closes(symbol, period + 1)
        if len(closes) < period + 1:
            return None
        gains, losses = [], []
        for i in range(1, len(closes)):
            change = closes[i] - closes[i - 1]
            gains.append(max(change, 0))
            losses.append(max(-change, 0))
        avg_gain = sum(gains) / period
        avg_loss = sum(losses) / period
        if avg_loss == 0:
            return 100.0
        rs = avg_gain / avg_loss
        return 100 - (100 / (1 + rs))

    def bollinger_bands(self, symbol: str, period: int = 20, num_std: float = 2.0):
        closes = self.get_closes(symbol, period)
        if len(closes) < period:
            return None, None, None
        mean = sum(closes) / period
        variance = sum((c - mean) ** 2 for c in closes) / period
        std = variance ** 0.5
        return mean - num_std * std, mean, mean + num_std * std

    def atr(self, symbol: str, period: int = 14) -> Optional[float]:
        bars = self.get_bars(symbol, period + 1)
        if len(bars) < period + 1:
            return None
        trs = []
        for i in range(1, len(bars)):
            high = bars[i].high
            low = bars[i].low
            prev_close = bars[i - 1].close
            trs.append(max(high - low, abs(high - prev_close), abs(low - prev_close)))
        return sum(trs) / len(trs)

    def macd(self, symbol: str, fast: int = 12, slow: int = 26, signal: int = 9):
        fast_ema = self.ema(symbol, fast)
        slow_ema = self.ema(symbol, slow)
        if fast_ema is None or slow_ema is None:
            return None, None, None
        macd_line = fast_ema - slow_ema
        # Approximate signal as SMA of recent MACD values
        closes = self.get_closes(symbol, slow + signal)
        if len(closes) < slow + signal:
            return macd_line, None, None
        k_fast = 2 / (fast + 1)
        k_slow = 2 / (slow + 1)
        k_sig = 2 / (signal + 1)
        ema_fast = sum(closes[:fast]) / fast
        ema_slow = sum(closes[:slow]) / slow
        macd_vals = []
        for price in closes[slow:]:
            ema_fast = price * k_fast + ema_fast * (1 - k_fast)
            ema_slow = price * k_slow + ema_slow * (1 - k_slow)
            macd_vals.append(ema_fast - ema_slow)
        if len(macd_vals) < signal:
            return macd_line, None, None
        sig_val = sum(macd_vals[:signal]) / signal
        for m in macd_vals[signal:]:
            sig_val = m * k_sig + sig_val * (1 - k_sig)
        histogram = macd_line - sig_val
        return macd_line, sig_val, histogram
