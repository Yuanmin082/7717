"""
Bollinger Bands Strategy.
Buy when price touches lower band; sell when price touches upper band.
"""

from datetime import datetime
from .base import Strategy, Signal, SignalType


class BollingerBandsStrategy(Strategy):
    """
    Bollinger Bands Mean Reversion Strategy.

    Parameters:
        period (int): Rolling window (default 20)
        num_std (float): Standard deviation multiplier (default 2.0)
    """

    def __init__(self, symbols: list[str], period: int = 20, num_std: float = 2.0):
        super().__init__("Bollinger_Bands", symbols, {"period": period, "num_std": num_std})
        self.period = period
        self.num_std = num_std
        self._in_position: dict[str, bool] = {}

    def generate_signals(self, symbol: str, timestamp: datetime) -> list[Signal]:
        lower, middle, upper = self.data_manager.bollinger_bands(symbol, self.period, self.num_std)
        if lower is None:
            return []

        bars = self.data_manager.get_bars(symbol, 1)
        if not bars:
            return []
        price = bars[-1].close
        in_pos = self._in_position.get(symbol, False)

        signals = []
        band_width = upper - lower

        if not in_pos and price <= lower:
            confidence = round(min((lower - price) / (band_width * 0.1 + 1e-9), 1.0), 4)
            signals.append(Signal(
                timestamp=timestamp,
                symbol=symbol,
                signal_type=SignalType.BUY,
                price=price,
                confidence=confidence,
                metadata={"lower": lower, "middle": middle, "upper": upper},
            ))
            self._in_position[symbol] = True

        elif in_pos and price >= upper:
            confidence = round(min((price - upper) / (band_width * 0.1 + 1e-9), 1.0), 4)
            signals.append(Signal(
                timestamp=timestamp,
                symbol=symbol,
                signal_type=SignalType.SELL,
                price=price,
                confidence=confidence,
                metadata={"lower": lower, "middle": middle, "upper": upper},
            ))
            self._in_position[symbol] = False

        return signals
