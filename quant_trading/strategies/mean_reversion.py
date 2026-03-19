"""
Mean Reversion Strategy using Z-score.
Buy when price is significantly below its rolling mean; sell when above.
"""

import math
from datetime import datetime
from .base import Strategy, Signal, SignalType


class MeanReversionStrategy(Strategy):
    """
    Z-Score Mean Reversion Strategy.

    Parameters:
        lookback (int): Rolling window for mean/std computation (default 30)
        entry_z (float): Z-score threshold to enter a trade (default 2.0)
        exit_z (float): Z-score threshold to exit a trade (default 0.5)
    """

    def __init__(self, symbols: list[str], lookback: int = 30, entry_z: float = 2.0, exit_z: float = 0.5):
        super().__init__("Mean_Reversion", symbols, {"lookback": lookback, "entry_z": entry_z, "exit_z": exit_z})
        self.lookback = lookback
        self.entry_z = entry_z
        self.exit_z = exit_z
        self._positions: dict[str, str] = {}  # "long", "short", or ""

    def _zscore(self, symbol: str) -> float | None:
        closes = self.data_manager.get_closes(symbol, self.lookback)
        if len(closes) < self.lookback:
            return None
        mean = sum(closes) / len(closes)
        variance = sum((c - mean) ** 2 for c in closes) / len(closes)
        std = math.sqrt(variance)
        if std == 0:
            return 0.0
        return (closes[-1] - mean) / std

    def generate_signals(self, symbol: str, timestamp: datetime) -> list[Signal]:
        z = self._zscore(symbol)
        if z is None:
            return []

        bars = self.data_manager.get_bars(symbol, 1)
        if not bars:
            return []
        price = bars[-1].close
        pos = self._positions.get(symbol, "")

        signals = []

        if pos == "" and z <= -self.entry_z:
            signals.append(Signal(
                timestamp=timestamp, symbol=symbol,
                signal_type=SignalType.BUY, price=price,
                confidence=min(abs(z) / self.entry_z - 1, 1.0),
                metadata={"zscore": z},
            ))
            self._positions[symbol] = "long"

        elif pos == "" and z >= self.entry_z:
            signals.append(Signal(
                timestamp=timestamp, symbol=symbol,
                signal_type=SignalType.SELL, price=price,
                confidence=min(abs(z) / self.entry_z - 1, 1.0),
                metadata={"zscore": z},
            ))
            self._positions[symbol] = "short"

        elif pos == "long" and z >= -self.exit_z:
            signals.append(Signal(
                timestamp=timestamp, symbol=symbol,
                signal_type=SignalType.SELL, price=price,
                confidence=1.0,
                metadata={"zscore": z, "exit": True},
            ))
            self._positions[symbol] = ""

        elif pos == "short" and z <= self.exit_z:
            signals.append(Signal(
                timestamp=timestamp, symbol=symbol,
                signal_type=SignalType.BUY, price=price,
                confidence=1.0,
                metadata={"zscore": z, "exit": True},
            ))
            self._positions[symbol] = ""

        return signals
