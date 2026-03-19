"""
Backtesting Engine.
Drives historical simulation: iterates through bars, dispatches strategy signals,
executes orders with slippage & commission, and tracks portfolio state.
"""

import uuid
from datetime import datetime
from typing import Optional

from ..data.data_manager import DataManager
from ..data.data_feed import DataFeed
from ..strategies.base import Strategy, Signal, SignalType
from ..risk.risk_manager import RiskManager
from ..portfolio.portfolio import Portfolio
from .order import Order, OrderType, OrderSide, OrderStatus
from .trade import Trade


class BacktestEngine:
    """
    Event-driven backtesting engine.

    Args:
        feed: Market data feed
        strategy: Trading strategy
        initial_capital: Starting cash
        commission_rate: Per-trade commission as fraction of trade value
        slippage_rate: Slippage as fraction of trade price
        position_size_pct: Fraction of portfolio to allocate per trade
    """

    def __init__(
        self,
        feed: DataFeed,
        strategy: Strategy,
        initial_capital: float = 100_000.0,
        commission_rate: float = 0.001,
        slippage_rate: float = 0.0005,
        position_size_pct: float = 0.1,
        risk_manager: Optional[RiskManager] = None,
    ):
        self.feed = feed
        self.strategy = strategy
        self.initial_capital = initial_capital
        self.commission_rate = commission_rate
        self.slippage_rate = slippage_rate
        self.position_size_pct = position_size_pct
        self.risk_manager = risk_manager

        self.portfolio = Portfolio(initial_capital)
        self.data_manager = DataManager(feed)
        self.strategy.set_data_manager(self.data_manager)

        self.orders: list[Order] = []
        self.trades: list[Trade] = []
        self._open_positions: dict[str, dict] = {}  # symbol -> entry info

    def run(self, symbols: list[str], start: datetime, end: datetime) -> dict:
        """Run the backtest and return results summary."""
        # Fetch raw bars from feed (don't load into manager yet — stream them one by one)
        raw_bars = []
        feed = self.feed
        for symbol in symbols:
            bars = feed.get_bars(symbol, start, end)
            raw_bars.extend(bars)
        raw_bars.sort(key=lambda b: b.timestamp)

        equity_curve = []
        seen: dict[str, int] = {s: 0 for s in symbols}

        for bar in raw_bars:
            symbol = bar.symbol

            # Push bar into data manager so indicators are computed on data up to *this* bar
            self.data_manager.push_bar(bar)
            seen[symbol] = seen.get(symbol, 0) + 1

            # Update portfolio market value
            self.portfolio.update_price(symbol, bar.close)

            # Need at least some history before generating signals
            if seen[symbol] < 30:
                equity_curve.append({
                    "timestamp": bar.timestamp.isoformat(),
                    "equity": self.portfolio.total_equity,
                })
                continue

            # Generate signals
            signals = self.strategy.on_bar(symbol, bar.timestamp)

            for signal in signals:
                self._process_signal(signal, bar.close, bar.timestamp)

            equity_curve.append({
                "timestamp": bar.timestamp.isoformat(),
                "equity": round(self.portfolio.total_equity, 2),
            })

        return {
            "initial_capital": self.initial_capital,
            "final_equity": round(self.portfolio.total_equity, 2),
            "total_return": round((self.portfolio.total_equity / self.initial_capital - 1) * 100, 4),
            "total_trades": len(self.trades),
            "orders": [o.to_dict() for o in self.orders],
            "trades": [t.to_dict() for t in self.trades],
            "equity_curve": equity_curve,
        }

    def _process_signal(self, signal: Signal, current_price: float, timestamp: datetime):
        symbol = signal.symbol

        if signal.signal_type == SignalType.BUY:
            if symbol in self._open_positions:
                return  # Already long
            # Risk check
            if self.risk_manager and not self.risk_manager.can_open_position(symbol, self.portfolio):
                return

            # Calculate position size
            trade_value = self.portfolio.cash * self.position_size_pct
            exec_price = current_price * (1 + self.slippage_rate)
            quantity = trade_value / exec_price
            commission = trade_value * self.commission_rate

            if trade_value > self.portfolio.cash:
                return

            order = Order(
                order_id=str(uuid.uuid4())[:8],
                symbol=symbol,
                side=OrderSide.BUY,
                order_type=OrderType.MARKET,
                quantity=quantity,
                timestamp=timestamp,
            )
            order.fill(exec_price, quantity, timestamp, commission)
            self.orders.append(order)

            self.portfolio.open_position(symbol, exec_price, quantity, commission)
            self._open_positions[symbol] = {
                "entry_price": exec_price,
                "quantity": quantity,
                "entry_time": timestamp,
                "commission": commission,
            }

        elif signal.signal_type == SignalType.SELL:
            if symbol not in self._open_positions:
                return  # No position to close

            pos = self._open_positions[symbol]
            exec_price = current_price * (1 - self.slippage_rate)
            commission = pos["quantity"] * exec_price * self.commission_rate

            order = Order(
                order_id=str(uuid.uuid4())[:8],
                symbol=symbol,
                side=OrderSide.SELL,
                order_type=OrderType.MARKET,
                quantity=pos["quantity"],
                timestamp=timestamp,
            )
            order.fill(exec_price, pos["quantity"], timestamp, commission)
            self.orders.append(order)

            trade = Trade(
                trade_id=str(uuid.uuid4())[:8],
                symbol=symbol,
                entry_time=pos["entry_time"],
                exit_time=timestamp,
                entry_price=pos["entry_price"],
                exit_price=exec_price,
                quantity=pos["quantity"],
                side="long",
                commission=pos["commission"] + commission,
            )
            self.trades.append(trade)

            self.portfolio.close_position(symbol, exec_price, pos["quantity"], commission)
            del self._open_positions[symbol]
