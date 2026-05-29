"""Robo de trading -- motor em Python puro, com gestao de risco no centro.

Filosofia: preservar capital vem antes de lucrar. Veja o README.md.
"""

from .backtest import BacktestResult, format_report, run_backtest
from .broker import PaperBroker, Trade
from .config import CostConfig, RiskConfig, Settings, StrategyConfig
from .data import Candle, generate_synthetic_candles, load_candles_csv
from .risk import RiskManager
from .strategy import EmaRsiAtrStrategy, Signal, Strategy

__all__ = [
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
