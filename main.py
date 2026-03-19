#!/usr/bin/env python3
"""
量化交易系统 - 主入口
Quantitative Trading System - Main Entry Point

Usage:
    python main.py                    # Run default backtest + start dashboard
    python main.py --backtest         # Run backtest only (CLI output)
    python main.py --dashboard        # Start web dashboard only
    python main.py --strategy RSI     # Run specific strategy
    python main.py --symbol TSLA      # Run on specific symbol
    python main.py --days 730         # Set backtest period
"""

import argparse
import sys
from datetime import datetime, timedelta

# Add project root to path
sys.path.insert(0, ".")

from quant_trading.data.data_feed import SimulatedDataFeed
from quant_trading.data.data_manager import DataManager
from quant_trading.strategies import (
    MACrossoverStrategy,
    RSIStrategy,
    BollingerBandsStrategy,
    MACDStrategy,
    MeanReversionStrategy,
)
from quant_trading.backtesting.engine import BacktestEngine
from quant_trading.risk.risk_manager import RiskManager, RiskConfig
from quant_trading.analytics.performance import PerformanceAnalytics
from quant_trading.config import DEFAULT_CONFIG


STRATEGY_MAP = {
    "MA_Crossover": MACrossoverStrategy,
    "RSI": RSIStrategy,
    "Bollinger_Bands": BollingerBandsStrategy,
    "MACD": MACDStrategy,
    "Mean_Reversion": MeanReversionStrategy,
}


def build_strategy(name: str, symbols: list[str]):
    cls = STRATEGY_MAP.get(name)
    if cls is None:
        raise ValueError(f"Unknown strategy: {name}. Available: {list(STRATEGY_MAP.keys())}")
    return cls(symbols=symbols)


def run_backtest(strategy_name: str, symbol: str, days: int, verbose: bool = True) -> dict:
    """Run a backtest and return results dict."""
    cfg = DEFAULT_CONFIG.backtest
    rcfg = DEFAULT_CONFIG.risk
    dcfg = DEFAULT_CONFIG.data

    symbols = [symbol]
    end = datetime.now()
    start = end - timedelta(days=days)

    feed = SimulatedDataFeed(
        symbols=symbols,
        start_price=dcfg.simulated_start_price,
        drift=dcfg.simulated_drift,
        volatility=dcfg.simulated_volatility,
        seed=dcfg.seed,
    )

    strategy = build_strategy(strategy_name, symbols)

    risk_config = RiskConfig(
        max_position_pct=rcfg.max_position_pct,
        max_drawdown_pct=rcfg.max_drawdown_pct,
        max_open_positions=rcfg.max_open_positions,
        stop_loss_pct=rcfg.stop_loss_pct,
        take_profit_pct=rcfg.take_profit_pct,
    )
    risk_manager = RiskManager(risk_config)

    engine = BacktestEngine(
        feed=feed,
        strategy=strategy,
        initial_capital=cfg.initial_capital,
        commission_rate=cfg.commission_rate,
        slippage_rate=cfg.slippage_rate,
        position_size_pct=cfg.position_size_pct,
        risk_manager=risk_manager,
    )

    results = engine.run(symbols, start, end)

    # Compute performance metrics
    analytics = PerformanceAnalytics(
        equity_curve=results["equity_curve"],
        trades=results["trades"],
    )
    perf = analytics.full_report()
    results["performance"] = perf

    if verbose:
        print(f"\nStrategy : {strategy_name}")
        print(f"Symbol   : {symbol}")
        print(f"Period   : {start.date()} → {end.date()} ({days} days)")
        analytics.print_report()
        print(f"\nInitial Capital : ${results['initial_capital']:>12,.2f}")
        print(f"Final Equity    : ${results['final_equity']:>12,.2f}")
        print(f"Total Return    : {results['total_return']:>+11.2f}%\n")

    return results


def start_dashboard(host: str = "localhost", port: int = 8080):
    """Launch the web dashboard."""
    from quant_trading.dashboard.app import create_app

    def backtest_runner(strategy_name: str, symbol: str, days: int) -> dict:
        return run_backtest(strategy_name, symbol, int(days), verbose=False)

    HTTPServer, Handler = create_app(backtest_runner)
    server = HTTPServer((host, port), Handler)
    print(f"\n  量化交易系统仪表盘已启动")
    print(f"  访问地址: http://{host}:{port}")
    print(f"  按 Ctrl+C 停止服务\n")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n  服务已停止")
        server.server_close()


def main():
    parser = argparse.ArgumentParser(description="量化交易系统")
    parser.add_argument("--backtest", action="store_true", help="Run backtest only")
    parser.add_argument("--dashboard", action="store_true", help="Start web dashboard only")
    parser.add_argument("--strategy", default="MA_Crossover", choices=list(STRATEGY_MAP.keys()))
    parser.add_argument("--symbol", default="AAPL")
    parser.add_argument("--days", type=int, default=365)
    parser.add_argument("--host", default="localhost")
    parser.add_argument("--port", type=int, default=8080)
    args = parser.parse_args()

    if args.backtest:
        run_backtest(args.strategy, args.symbol, args.days)
    elif args.dashboard:
        start_dashboard(args.host, args.port)
    else:
        # Default: run backtest then launch dashboard
        print("运行默认回测...")
        run_backtest(args.strategy, args.symbol, args.days)
        start_dashboard(args.host, args.port)


if __name__ == "__main__":
    main()
