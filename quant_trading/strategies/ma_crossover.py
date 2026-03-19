"""
Moving Average Crossover Strategy.
Buy when fast MA crosses above slow MA; sell when it crosses below.
"""

from datetime import datetime
from .base import Strategy, Signal, SignalType


class MACrossoverStrategy(Strategy):
    """
    Dual Moving Average Crossover.

    Parameters:
        fast_period (int): Fast MA period (default 10)
        slow_period (int): Slow MA period (default 30)
        ma_type (str): 'sma' or 'ema' (default 'sma')
    """

    def __init__(self, symbols: list[str], fast_period: int = 10, slow_period: int = 30, ma_type: str = "sma"):
        super().__init__("MA_Crossover", symbols, {"fast": fast_period, "slow": slow_period, "ma_type": ma_type})
        self.fast_period = fast_period
        self.slow_period = slow_period
        self.ma_type = ma_type
        self._prev_fast: dict[str, float] = {}
        self._prev_slow: dict[str, float] = {}

    def _compute_ma(self, symbol: str, period: int) -> float | None:
        if self.ma_type == "ema":
            return self.data_manager.ema(symbol, period)
        return self.data_manager.sma(symbol, period)

    def generate_signals(self, symbol: str, timestamp: datetime) -> list[Signal]:
        fast = self._compute_ma(symbol, self.fast_period)
        slow = self._compute_ma(symbol, self.slow_period)

        if fast is None or slow is None:
            return []

        bars = self.data_manager.get_bars(symbol, 1)
        if not bars:
            return []
        price = bars[-1].close

        signals = []
        prev_fast = self._prev_fast.get(symbol)
        prev_slow = self._prev_slow.get(symbol)

        if prev_fast is not None and prev_slow is not None:
            if prev_fast <= prev_slow and fast > slow:
                signals.append(Signal(
                    timestamp=timestamp,
                    symbol=symbol,
                    signal_type=SignalType.BUY,
                    price=price,
                    confidence=min((fast - slow) / slow * 100, 1.0),
                    metadata={"fast_ma": fast, "slow_ma": slow},
                ))
            elif prev_fast >= prev_slow and fast < slow:
                signals.append(Signal(
                    timestamp=timestamp,
                    symbol=symbol,
                    signal_type=SignalType.SELL,
                    price=price,
                    confidence=min((slow - fast) / slow * 100, 1.0),
                    metadata={"fast_ma": fast, "slow_ma": slow},
                ))

        self._prev_fast[symbol] = fast
        self._prev_slow[symbol] = slow
        return signals
