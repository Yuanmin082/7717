"""
System-wide configuration.
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class BacktestConfig:
    initial_capital: float = 100_000.0
    commission_rate: float = 0.001      # 0.1%
    slippage_rate: float = 0.0005       # 0.05%
    position_size_pct: float = 0.10     # 10% per trade


@dataclass
class RiskConfig:
    max_position_pct: float = 0.20
    max_drawdown_pct: float = 0.20
    max_open_positions: int = 10
    max_daily_loss_pct: float = 0.05
    stop_loss_pct: float = 0.05
    take_profit_pct: float = 0.15
    volatility_scale: bool = True


@dataclass
class DataConfig:
    default_symbols: list = field(default_factory=lambda: ["AAPL", "MSFT", "GOOGL", "TSLA", "NVDA"])
    simulated_start_price: float = 100.0
    simulated_drift: float = 0.0002
    simulated_volatility: float = 0.015
    seed: int = 42


@dataclass
class DashboardConfig:
    host: str = "localhost"
    port: int = 8080


@dataclass
class SystemConfig:
    backtest: BacktestConfig = field(default_factory=BacktestConfig)
    risk: RiskConfig = field(default_factory=RiskConfig)
    data: DataConfig = field(default_factory=DataConfig)
    dashboard: DashboardConfig = field(default_factory=DashboardConfig)


DEFAULT_CONFIG = SystemConfig()
