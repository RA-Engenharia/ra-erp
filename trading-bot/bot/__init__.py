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
from .brain import (
    EnsembleStrategy,
    Member,
    MemberDiagnostic,
    build_brain,
    format_brain_report,
)
from .feeds import CcxtLiveFeed, ReplayFeed
from .sources import DataSourceConfig, build_feed
from .live import LiveTrader, LiveUpdate, candle_feed, run_live
from .risk import RiskManager
from .scanner import ScanResult, format_scan, scan_candles
from .strategies import (
    BollingerStrategy,
    BreakoutStrategy,
    MacdStrategy,
    MeanReversionStrategy,
    RegimeFilteredStrategy,
    RocStrategy,
    Rsi2Strategy,
    SuperTrendStrategy,
    TrendEmaStrategy,
)
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
    "DataSourceConfig",
    "build_feed",
    "EnsembleStrategy",
    "Member",
    "MemberDiagnostic",
    "build_brain",
    "format_brain_report",
    "ScanResult",
    "scan_candles",
    "format_scan",
    "equity_curve_ascii",
    "generate_regime_candles",
    "compare_across_datasets",
    "BreakoutStrategy",
    "MeanReversionStrategy",
    "TrendEmaStrategy",
    "MacdStrategy",
    "BollingerStrategy",
    "RegimeFilteredStrategy",
    "SuperTrendStrategy",
    "RocStrategy",
    "Rsi2Strategy",
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
