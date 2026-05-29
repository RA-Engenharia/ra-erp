"""Robo de trading -- motor em Python puro, com gestao de risco no centro.

Filosofia: preservar capital vem antes de lucrar. Veja o README.md.
"""

from .backtest import BacktestResult, format_report, run_backtest
from .broker import PaperBroker, Trade
from .chart import equity_curve_ascii
from .config import CostConfig, RiskConfig, Settings, StrategyConfig
from .data import (
    Candle,
    generate_regime_candles,
    generate_synthetic_candles,
    load_candles_csv,
)
from .feeds import CcxtLiveFeed, ReplayFeed
from .live import LiveTrader, LiveUpdate, candle_feed, run_live
from .risk import RiskManager
from .strategies import BreakoutStrategy, MeanReversionStrategy, TrendEmaStrategy
from .strategy import EmaRsiAtrStrategy, Signal, Strategy
from .validation import (
    StrategySpec,
    compare_across_datasets,
    compare_strategies,
    grid_search,
    train_test,
    walk_forward,
)

__all__ = [
    "LiveTrader",
    "LiveUpdate",
    "candle_feed",
    "run_live",
    "ReplayFeed",
    "CcxtLiveFeed",
    "equity_curve_ascii",
    "generate_regime_candles",
    "compare_across_datasets",
    "BreakoutStrategy",
    "MeanReversionStrategy",
    "TrendEmaStrategy",
    "StrategySpec",
    "compare_strategies",
    "grid_search",
    "train_test",
    "walk_forward",
    "BacktestResult",
    "format_report",
    "run_backtest",
    "PaperBroker",
    "Trade",
    "CostConfig",
    "RiskConfig",
    "Settings",
    "StrategyConfig",
    "Candle",
    "generate_synthetic_candles",
    "load_candles_csv",
    "RiskManager",
    "EmaRsiAtrStrategy",
    "Signal",
    "Strategy",
]
