"""
Data feed module for market data ingestion.
Supports CSV files, simulated data, and extensible to live data sources.
"""

import csv
import random
import math
from datetime import datetime, timedelta
from abc import ABC, abstractmethod
from typing import Optional, Iterator
from dataclasses import dataclass


@dataclass
class Bar:
    """OHLCV bar data."""
    timestamp: datetime
    symbol: str
    open: float
    high: float
    low: float
    close: float
    volume: float

    def to_dict(self) -> dict:
        return {
            "timestamp": self.timestamp.isoformat(),
            "symbol": self.symbol,
            "open": self.open,
            "high": self.high,
            "low": self.low,
            "close": self.close,
            "volume": self.volume,
        }


class DataFeed(ABC):
    """Abstract base class for data feeds."""

    @abstractmethod
    def get_bars(self, symbol: str, start: datetime, end: datetime) -> list[Bar]:
        pass

    @abstractmethod
    def get_latest_bar(self, symbol: str) -> Optional[Bar]:
        pass


class CSVDataFeed(DataFeed):
    """Load market data from CSV files."""

    def __init__(self, filepath: str, symbol: str):
        self.filepath = filepath
        self.symbol = symbol
        self._bars: list[Bar] = []
        self._load()

    def _load(self):
        try:
            with open(self.filepath, "r") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    ts = datetime.fromisoformat(row.get("timestamp", row.get("date", "")))
                    bar = Bar(
                        timestamp=ts,
                        symbol=self.symbol,
                        open=float(row["open"]),
                        high=float(row["high"]),
                        low=float(row["low"]),
                        close=float(row["close"]),
                        volume=float(row.get("volume", 0)),
                    )
                    self._bars.append(bar)
            self._bars.sort(key=lambda b: b.timestamp)
        except FileNotFoundError:
            self._bars = []

    def get_bars(self, symbol: str, start: datetime, end: datetime) -> list[Bar]:
        return [b for b in self._bars if start <= b.timestamp <= end and b.symbol == symbol]

    def get_latest_bar(self, symbol: str) -> Optional[Bar]:
        bars = [b for b in self._bars if b.symbol == symbol]
        return bars[-1] if bars else None


class SimulatedDataFeed(DataFeed):
    """Generate simulated market data using Geometric Brownian Motion."""

    def __init__(
        self,
        symbols: list[str],
        start_price: float = 100.0,
        drift: float = 0.0002,
        volatility: float = 0.015,
        seed: Optional[int] = 42,
    ):
        self.symbols = symbols
        self.start_price = start_price
        self.drift = drift
        self.volatility = volatility
        self._rng = random.Random(seed)
        self._cache: dict[str, list[Bar]] = {}

    def _generate_bars(self, symbol: str, start: datetime, end: datetime) -> list[Bar]:
        bars: list[Bar] = []
        price = self.start_price
        current = start

        while current <= end:
            # Skip weekends
            if current.weekday() >= 5:
                current += timedelta(days=1)
                continue

            # GBM price simulation
            z = self._rng.gauss(0, 1)
            ret = self.drift + self.volatility * z
            close = price * math.exp(ret)

            daily_vol = abs(self._rng.gauss(0, close * 0.005))
            open_price = price * (1 + self._rng.gauss(0, 0.002))
            high = max(open_price, close) + daily_vol
            low = min(open_price, close) - daily_vol
            volume = abs(self._rng.gauss(1_000_000, 200_000))

            bars.append(Bar(
                timestamp=current,
                symbol=symbol,
                open=round(open_price, 4),
                high=round(high, 4),
                low=round(low, 4),
                close=round(close, 4),
                volume=round(volume, 0),
            ))

            price = close
            current += timedelta(days=1)

        return bars

    def get_bars(self, symbol: str, start: datetime, end: datetime) -> list[Bar]:
        key = f"{symbol}_{start.date()}_{end.date()}"
        if key not in self._cache:
            self._cache[key] = self._generate_bars(symbol, start, end)
        return self._cache[key]

    def get_latest_bar(self, symbol: str) -> Optional[Bar]:
        end = datetime.now()
        start = end - timedelta(days=5)
        bars = self.get_bars(symbol, start, end)
        return bars[-1] if bars else None
