"""
RSI (Relative Strength Index) Strategy.
Buy on oversold conditions, sell on overbought conditions.
"""

from datetime import datetime
from .base import Strategy, Signal, SignalType


class RSIStrategy(Strategy):
    """
    RSI Mean Reversion Strategy.

    Parameters:
        period (int): RSI lookback period (default 14)
        oversold (float): Buy threshold (default 30)
        overbought (float): Sell threshold (default 70)
    """

    def __init__(self, symbols: list[str], period: int = 14, oversold: float = 30.0, overbought: float = 70.0):
        super().__init__("RSI", symbols, {"period": period, "oversold": oversold, "overbought": overbought})
        self.period = period
        self.oversold = oversold
        self.overbought = overbought
        self._prev_rsi: dict[str, float] = {}

    def generate_signals(self, symbol: str, timestamp: datetime) -> list[Signal]:
        rsi = self.data_manager.rsi(symbol, self.period)
        if rsi is None:
            return []

        bars = self.data_manager.get_bars(symbol, 1)
        if not bars:
            return []
        price = bars[-1].close

        signals = []
        prev_rsi = self._prev_rsi.get(symbol)

        if prev_rsi is not None:
            # Crossover from oversold (buy signal)
            if prev_rsi <= self.oversold and rsi > self.oversold:
                confidence = (self.oversold - min(prev_rsi, rsi)) / self.oversold
                signals.append(Signal(
                    timestamp=timestamp,
                    symbol=symbol,
                    signal_type=SignalType.BUY,
                    price=price,
                    confidence=round(min(confidence, 1.0), 4),
                    metadata={"rsi": rsi, "prev_rsi": prev_rsi},
                ))
            # Crossover from overbought (sell signal)
            elif prev_rsi >= self.overbought and rsi < self.overbought:
                confidence = (max(prev_rsi, rsi) - self.overbought) / (100 - self.overbought)
                signals.append(Signal(
                    timestamp=timestamp,
                    symbol=symbol,
                    signal_type=SignalType.SELL,
                    price=price,
                    confidence=round(min(confidence, 1.0), 4),
                    metadata={"rsi": rsi, "prev_rsi": prev_rsi},
                ))

        self._prev_rsi[symbol] = rsi
        return signals
