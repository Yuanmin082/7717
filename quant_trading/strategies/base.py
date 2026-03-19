"""
Base strategy interface and signal types.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
from typing import Optional

from ..data.data_manager import DataManager


class SignalType(Enum):
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"


@dataclass
class Signal:
    timestamp: datetime
    symbol: str
    signal_type: SignalType
    price: float
    quantity: float = 0.0
    confidence: float = 1.0
    metadata: dict = field(default_factory=dict)

    def __str__(self):
        return (
            f"[{self.timestamp.date()}] {self.signal_type.value} {self.symbol} "
            f"@ {self.price:.4f} (conf={self.confidence:.2f})"
        )


class Strategy(ABC):
    """Abstract base class for all trading strategies."""

    def __init__(self, name: str, symbols: list[str], params: Optional[dict] = None):
        self.name = name
        self.symbols = symbols
        self.params = params or {}
        self.data_manager: Optional[DataManager] = None

    def set_data_manager(self, dm: DataManager):
        self.data_manager = dm

    @abstractmethod
    def generate_signals(self, symbol: str, timestamp: datetime) -> list[Signal]:
        """Generate trading signals for a given symbol at a given time."""
        pass

    def on_bar(self, symbol: str, timestamp: datetime) -> list[Signal]:
        """Called by the backtester/live engine on each new bar."""
        if symbol not in self.symbols:
            return []
        return self.generate_signals(symbol, timestamp)

    def __repr__(self):
        return f"{self.__class__.__name__}(name={self.name}, symbols={self.symbols})"
