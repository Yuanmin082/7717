"""
Risk Manager.
Controls position sizing, drawdown limits, concentration, and stop-loss logic.
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class RiskConfig:
    max_position_pct: float = 0.20        # Max % of portfolio per position
    max_drawdown_pct: float = 0.20        # Stop trading if drawdown exceeds this
    max_open_positions: int = 10          # Maximum simultaneous positions
    max_daily_loss_pct: float = 0.05      # Stop trading for the day
    stop_loss_pct: float = 0.05           # Per-trade stop-loss
    take_profit_pct: float = 0.15         # Per-trade take-profit
    max_sector_pct: float = 0.40          # Max exposure per sector
    volatility_scale: bool = True         # Scale position size by inverse volatility


class RiskManager:
    """
    Portfolio-level risk management.

    Checks:
    - Maximum drawdown gate
    - Maximum open positions
    - Per-position concentration limit
    - Daily loss limit
    """

    def __init__(self, config: Optional[RiskConfig] = None):
        self.config = config or RiskConfig()
        self._peak_equity: float = 0.0
        self._daily_start_equity: float = 0.0
        self._trading_halted: bool = False
        self._stop_loss_prices: dict[str, float] = {}
        self._take_profit_prices: dict[str, float] = {}

    def update_equity(self, equity: float):
        if equity > self._peak_equity:
            self._peak_equity = equity
        if self._daily_start_equity == 0:
            self._daily_start_equity = equity

    def reset_daily(self, equity: float):
        self._daily_start_equity = equity
        self._trading_halted = False

    def current_drawdown(self, equity: float) -> float:
        if self._peak_equity == 0:
            return 0.0
        return (self._peak_equity - equity) / self._peak_equity

    def daily_loss(self, equity: float) -> float:
        if self._daily_start_equity == 0:
            return 0.0
        return (self._daily_start_equity - equity) / self._daily_start_equity

    def can_open_position(self, symbol: str, portfolio) -> bool:
        """Check if a new position can be opened under risk constraints."""
        if self._trading_halted:
            return False

        equity = portfolio.total_equity

        # Drawdown check
        if self.current_drawdown(equity) >= self.config.max_drawdown_pct:
            self._trading_halted = True
            return False

        # Daily loss check
        if self.daily_loss(equity) >= self.config.max_daily_loss_pct:
            self._trading_halted = True
            return False

        # Max open positions
        if len(portfolio.positions) >= self.config.max_open_positions:
            return False

        # Already in this symbol
        if symbol in portfolio.positions:
            return False

        return True

    def set_stop_loss(self, symbol: str, entry_price: float):
        self._stop_loss_prices[symbol] = entry_price * (1 - self.config.stop_loss_pct)

    def set_take_profit(self, symbol: str, entry_price: float):
        self._take_profit_prices[symbol] = entry_price * (1 + self.config.take_profit_pct)

    def should_stop_loss(self, symbol: str, current_price: float) -> bool:
        sl = self._stop_loss_prices.get(symbol)
        return sl is not None and current_price <= sl

    def should_take_profit(self, symbol: str, current_price: float) -> bool:
        tp = self._take_profit_prices.get(symbol)
        return tp is not None and current_price >= tp

    def clear_levels(self, symbol: str):
        self._stop_loss_prices.pop(symbol, None)
        self._take_profit_prices.pop(symbol, None)

    def get_position_size_multiplier(self, symbol: str, volatility: float, base_size: float) -> float:
        """Inverse-volatility position sizing."""
        if not self.config.volatility_scale or volatility <= 0:
            return base_size
        target_vol = 0.01  # 1% target daily volatility
        scale = target_vol / volatility
        return min(base_size * scale, self.config.max_position_pct)

    def get_risk_report(self, portfolio) -> dict:
        equity = portfolio.total_equity
        return {
            "equity": round(equity, 2),
            "peak_equity": round(self._peak_equity, 2),
            "current_drawdown_pct": round(self.current_drawdown(equity) * 100, 4),
            "daily_loss_pct": round(self.daily_loss(equity) * 100, 4),
            "open_positions": len(portfolio.positions),
            "max_open_positions": self.config.max_open_positions,
            "trading_halted": self._trading_halted,
            "stop_loss_pct": self.config.stop_loss_pct * 100,
            "take_profit_pct": self.config.take_profit_pct * 100,
            "max_drawdown_limit_pct": self.config.max_drawdown_pct * 100,
        }
