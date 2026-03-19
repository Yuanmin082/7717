"""
Portfolio Manager.
Tracks cash, positions, unrealized/realized P&L.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class Position:
    symbol: str
    quantity: float
    avg_entry_price: float
    current_price: float
    entry_time: datetime
    commission_paid: float = 0.0

    @property
    def market_value(self) -> float:
        return self.quantity * self.current_price

    @property
    def cost_basis(self) -> float:
        return self.quantity * self.avg_entry_price

    @property
    def unrealized_pnl(self) -> float:
        return self.market_value - self.cost_basis - self.commission_paid

    @property
    def unrealized_pnl_pct(self) -> float:
        return self.unrealized_pnl / self.cost_basis if self.cost_basis != 0 else 0.0

    def update_price(self, price: float):
        self.current_price = price

    def to_dict(self) -> dict:
        return {
            "symbol": self.symbol,
            "quantity": round(self.quantity, 4),
            "avg_entry_price": round(self.avg_entry_price, 4),
            "current_price": round(self.current_price, 4),
            "market_value": round(self.market_value, 2),
            "cost_basis": round(self.cost_basis, 2),
            "unrealized_pnl": round(self.unrealized_pnl, 2),
            "unrealized_pnl_pct": round(self.unrealized_pnl_pct * 100, 4),
            "entry_time": self.entry_time.isoformat(),
        }


class Portfolio:
    """Tracks cash and open positions, computes portfolio-level metrics."""

    def __init__(self, initial_capital: float):
        self.initial_capital = initial_capital
        self.cash = initial_capital
        self.positions: dict[str, Position] = {}
        self.realized_pnl: float = 0.0
        self._equity_history: list[tuple[datetime, float]] = []
        self._commission_paid: float = 0.0

    @property
    def market_value(self) -> float:
        return sum(p.market_value for p in self.positions.values())

    @property
    def total_equity(self) -> float:
        return self.cash + self.market_value

    @property
    def unrealized_pnl(self) -> float:
        return sum(p.unrealized_pnl for p in self.positions.values())

    @property
    def total_pnl(self) -> float:
        return self.realized_pnl + self.unrealized_pnl

    @property
    def total_return_pct(self) -> float:
        return (self.total_equity / self.initial_capital - 1) * 100

    def open_position(self, symbol: str, price: float, quantity: float, commission: float = 0.0):
        cost = price * quantity + commission
        self.cash -= cost
        self._commission_paid += commission

        if symbol in self.positions:
            pos = self.positions[symbol]
            total_qty = pos.quantity + quantity
            pos.avg_entry_price = (pos.cost_basis + price * quantity) / total_qty
            pos.quantity = total_qty
            pos.commission_paid += commission
        else:
            self.positions[symbol] = Position(
                symbol=symbol,
                quantity=quantity,
                avg_entry_price=price,
                current_price=price,
                entry_time=datetime.now(),
                commission_paid=commission,
            )

    def close_position(self, symbol: str, price: float, quantity: float, commission: float = 0.0):
        if symbol not in self.positions:
            return
        pos = self.positions[symbol]
        proceeds = price * quantity - commission
        self.cash += proceeds
        self._commission_paid += commission

        pnl = (price - pos.avg_entry_price) * quantity - commission
        self.realized_pnl += pnl

        if quantity >= pos.quantity:
            del self.positions[symbol]
        else:
            pos.quantity -= quantity

    def update_price(self, symbol: str, price: float):
        if symbol in self.positions:
            self.positions[symbol].update_price(price)

    def snapshot(self, timestamp: Optional[datetime] = None) -> dict:
        ts = timestamp or datetime.now()
        self._equity_history.append((ts, self.total_equity))
        return {
            "timestamp": ts.isoformat(),
            "cash": round(self.cash, 2),
            "market_value": round(self.market_value, 2),
            "total_equity": round(self.total_equity, 2),
            "unrealized_pnl": round(self.unrealized_pnl, 2),
            "realized_pnl": round(self.realized_pnl, 2),
            "total_pnl": round(self.total_pnl, 2),
            "total_return_pct": round(self.total_return_pct, 4),
            "commission_paid": round(self._commission_paid, 2),
            "positions": {s: p.to_dict() for s, p in self.positions.items()},
        }
