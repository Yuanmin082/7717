"""
MACD (Moving Average Convergence Divergence) Strategy.
Buy on MACD line crossing above signal line; sell on crossing below.
"""

from datetime import datetime
from .base import Strategy, Signal, SignalType


class MACDStrategy(Strategy):
    """
    MACD Crossover Strategy.

    Parameters:
        fast (int): Fast EMA period (default 12)
        slow (int): Slow EMA period (default 26)
        signal (int): Signal line period (default 9)
    """

    def __init__(self, symbols: list[str], fast: int = 12, slow: int = 26, signal: int = 9):
        super().__init__("MACD", symbols, {"fast": fast, "slow": slow, "signal": signal})
        self.fast = fast
        self.slow = slow
        self.signal = signal
        self._prev_macd: dict[str, float] = {}
        self._prev_signal: dict[str, float] = {}

    def generate_signals(self, symbol: str, timestamp: datetime) -> list[Signal]:
        macd_line, signal_line, histogram = self.data_manager.macd(symbol, self.fast, self.slow, self.signal)

        if macd_line is None or signal_line is None:
            return []

        bars = self.data_manager.get_bars(symbol, 1)
        if not bars:
            return []
        price = bars[-1].close

        signals = []
        prev_macd = self._prev_macd.get(symbol)
        prev_sig = self._prev_signal.get(symbol)

        if prev_macd is not None and prev_sig is not None:
            if prev_macd <= prev_sig and macd_line > signal_line:
                signals.append(Signal(
                    timestamp=timestamp,
                    symbol=symbol,
                    signal_type=SignalType.BUY,
                    price=price,
                    confidence=min(abs(histogram or 0) / (abs(macd_line) + 1e-9), 1.0),
                    metadata={"macd": macd_line, "signal": signal_line, "histogram": histogram},
                ))
            elif prev_macd >= prev_sig and macd_line < signal_line:
                signals.append(Signal(
                    timestamp=timestamp,
                    symbol=symbol,
                    signal_type=SignalType.SELL,
                    price=price,
                    confidence=min(abs(histogram or 0) / (abs(macd_line) + 1e-9), 1.0),
                    metadata={"macd": macd_line, "signal": signal_line, "histogram": histogram},
                ))

        self._prev_macd[symbol] = macd_line
        self._prev_signal[symbol] = signal_line
        return signals
