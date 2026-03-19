"""
Performance Analytics.
Computes standard quantitative metrics: Sharpe, Sortino, Calmar,
Max Drawdown, Win Rate, Profit Factor, etc.
"""

import math
from typing import Optional


class PerformanceAnalytics:
    """
    Compute performance statistics from backtest results.

    Args:
        equity_curve: List of dicts with 'timestamp' and 'equity' keys
        trades: List of trade dicts from BacktestEngine
        risk_free_rate: Annual risk-free rate (default 0.02)
        trading_days: Trading days per year (default 252)
    """

    def __init__(
        self,
        equity_curve: list[dict],
        trades: list[dict],
        risk_free_rate: float = 0.02,
        trading_days: int = 252,
    ):
        self.equity_curve = equity_curve
        self.trades = trades
        self.risk_free_rate = risk_free_rate
        self.trading_days = trading_days

        self._equities = [e["equity"] for e in equity_curve]
        self._returns = self._compute_returns()

    def _compute_returns(self) -> list[float]:
        equities = self._equities
        if len(equities) < 2:
            return []
        returns = []
        for i in range(1, len(equities)):
            r = (equities[i] - equities[i - 1]) / equities[i - 1] if equities[i - 1] != 0 else 0
            returns.append(r)
        return returns

    # ── Core Metrics ─────────────────────────────────────────────────────

    def total_return(self) -> float:
        if not self._equities or self._equities[0] == 0:
            return 0.0
        return (self._equities[-1] / self._equities[0] - 1) * 100

    def annualized_return(self) -> float:
        if len(self._equities) < 2 or self._equities[0] == 0:
            return 0.0
        n_years = len(self._returns) / self.trading_days
        if n_years <= 0:
            return 0.0
        return ((self._equities[-1] / self._equities[0]) ** (1 / n_years) - 1) * 100

    def volatility(self) -> float:
        """Annualized volatility."""
        if len(self._returns) < 2:
            return 0.0
        mean = sum(self._returns) / len(self._returns)
        var = sum((r - mean) ** 2 for r in self._returns) / (len(self._returns) - 1)
        return math.sqrt(var * self.trading_days) * 100

    def sharpe_ratio(self) -> float:
        if len(self._returns) < 2:
            return 0.0
        mean_daily = sum(self._returns) / len(self._returns)
        daily_rf = self.risk_free_rate / self.trading_days
        excess = mean_daily - daily_rf
        mean_e = sum(self._returns) / len(self._returns)
        var = sum((r - mean_e) ** 2 for r in self._returns) / max(len(self._returns) - 1, 1)
        std = math.sqrt(var)
        if std == 0:
            return 0.0
        return (excess / std) * math.sqrt(self.trading_days)

    def sortino_ratio(self) -> float:
        if len(self._returns) < 2:
            return 0.0
        daily_rf = self.risk_free_rate / self.trading_days
        mean_excess = sum(r - daily_rf for r in self._returns) / len(self._returns)
        downside = [r for r in self._returns if r < daily_rf]
        if not downside:
            return float("inf")
        downside_var = sum((r - daily_rf) ** 2 for r in downside) / len(downside)
        downside_std = math.sqrt(downside_var)
        if downside_std == 0:
            return 0.0
        return (mean_excess / downside_std) * math.sqrt(self.trading_days)

    def max_drawdown(self) -> float:
        """Maximum peak-to-trough drawdown as a percentage."""
        if not self._equities:
            return 0.0
        peak = self._equities[0]
        max_dd = 0.0
        for e in self._equities:
            if e > peak:
                peak = e
            dd = (peak - e) / peak if peak != 0 else 0
            if dd > max_dd:
                max_dd = dd
        return max_dd * 100

    def calmar_ratio(self) -> float:
        ann_ret = self.annualized_return()
        max_dd = self.max_drawdown()
        if max_dd == 0:
            return 0.0
        return ann_ret / max_dd

    # ── Trade Statistics ──────────────────────────────────────────────────

    def win_rate(self) -> float:
        if not self.trades:
            return 0.0
        wins = sum(1 for t in self.trades if t.get("pnl", 0) > 0)
        return wins / len(self.trades) * 100

    def profit_factor(self) -> float:
        gross_profit = sum(t["pnl"] for t in self.trades if t.get("pnl", 0) > 0)
        gross_loss = abs(sum(t["pnl"] for t in self.trades if t.get("pnl", 0) < 0))
        if gross_loss == 0:
            return float("inf") if gross_profit > 0 else 0.0
        return gross_profit / gross_loss

    def avg_trade_pnl(self) -> float:
        if not self.trades:
            return 0.0
        return sum(t.get("pnl", 0) for t in self.trades) / len(self.trades)

    def avg_win(self) -> float:
        wins = [t["pnl"] for t in self.trades if t.get("pnl", 0) > 0]
        return sum(wins) / len(wins) if wins else 0.0

    def avg_loss(self) -> float:
        losses = [t["pnl"] for t in self.trades if t.get("pnl", 0) < 0]
        return sum(losses) / len(losses) if losses else 0.0

    def avg_trade_duration(self) -> float:
        if not self.trades:
            return 0.0
        return sum(t.get("duration_days", 0) for t in self.trades) / len(self.trades)

    def expectancy(self) -> float:
        wr = self.win_rate() / 100
        avg_w = self.avg_win()
        avg_l = abs(self.avg_loss())
        return wr * avg_w - (1 - wr) * avg_l

    # ── Summary Report ────────────────────────────────────────────────────

    def full_report(self) -> dict:
        return {
            "total_return_pct": round(self.total_return(), 4),
            "annualized_return_pct": round(self.annualized_return(), 4),
            "volatility_pct": round(self.volatility(), 4),
            "sharpe_ratio": round(self.sharpe_ratio(), 4),
            "sortino_ratio": round(self.sortino_ratio(), 4),
            "calmar_ratio": round(self.calmar_ratio(), 4),
            "max_drawdown_pct": round(self.max_drawdown(), 4),
            "total_trades": len(self.trades),
            "win_rate_pct": round(self.win_rate(), 4),
            "profit_factor": round(self.profit_factor(), 4),
            "avg_trade_pnl": round(self.avg_trade_pnl(), 4),
            "avg_win": round(self.avg_win(), 4),
            "avg_loss": round(self.avg_loss(), 4),
            "avg_trade_duration_days": round(self.avg_trade_duration(), 4),
            "expectancy": round(self.expectancy(), 4),
        }

    def print_report(self):
        report = self.full_report()
        print("\n" + "=" * 55)
        print("         PERFORMANCE REPORT")
        print("=" * 55)
        print(f"  Total Return        : {report['total_return_pct']:>10.2f}%")
        print(f"  Annualized Return   : {report['annualized_return_pct']:>10.2f}%")
        print(f"  Volatility          : {report['volatility_pct']:>10.2f}%")
        print(f"  Sharpe Ratio        : {report['sharpe_ratio']:>10.4f}")
        print(f"  Sortino Ratio       : {report['sortino_ratio']:>10.4f}")
        print(f"  Calmar Ratio        : {report['calmar_ratio']:>10.4f}")
        print(f"  Max Drawdown        : {report['max_drawdown_pct']:>10.2f}%")
        print("-" * 55)
        print(f"  Total Trades        : {report['total_trades']:>10d}")
        print(f"  Win Rate            : {report['win_rate_pct']:>10.2f}%")
        print(f"  Profit Factor       : {report['profit_factor']:>10.4f}")
        print(f"  Avg Trade P&L       : {report['avg_trade_pnl']:>10.4f}")
        print(f"  Avg Win             : {report['avg_win']:>10.4f}")
        print(f"  Avg Loss            : {report['avg_loss']:>10.4f}")
        print(f"  Avg Trade Duration  : {report['avg_trade_duration_days']:>10.2f} days")
        print(f"  Expectancy          : {report['expectancy']:>10.4f}")
        print("=" * 55)
