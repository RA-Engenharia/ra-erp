"""Analise completa: day-trade vs swing, com TODAS as estrategias, em dados reais.

    cd trading-bot
    python3 examples/analyze_full.py

Para cada ativo, roda o walk-forward de todas as estrategias em 3 cenarios:
  - 1h day-trade  (zera no fim do dia)   -> nosso ponto de partida
  - 1h swing      (segura por dias)       -> testa a pista do "eod"
  - 1d swing      (candles diarios)       -> swing classico

No fim, ranqueia TUDO junto: onde (se em algum lugar) aparece vantagem robusta.
Honesto sobre multiple-testing: quanto mais cenarios, mais falso-positivo.
"""

from __future__ import annotations

import os
import sys
from dataclasses import replace

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bot import EmaRsiAtrStrategy, Settings  # noqa: E402
from bot.scanner import ScanResult, format_scan, scan_candles  # noqa: E402
from bot.strategies import (  # noqa: E402
    BollingerStrategy,
    BreakoutStrategy,
    MacdStrategy,
    MeanReversionStrategy,
    RocStrategy,
    Rsi2Strategy,
    SuperTrendStrategy,
    TrendEmaStrategy,
)
from bot.validation import StrategySpec  # noqa: E402

ASSETS = ["PETR4.SA", "VALE3.SA", "ITUB4.SA", "BBAS3.SA", "WEGE3.SA", "ABEV3.SA"]
# (rotulo, intervalo, periodo, day_trade)
CONFIGS = [
    ("1h-day", "1h", "360d", True),
    ("1h-swing", "1h", "360d", False),
    ("1d-swing", "1d", "5y", False),
]


def build_all_specs(settings: Settings) -> list[StrategySpec]:
    ema_rsi = lambda p: EmaRsiAtrStrategy(replace(settings.strategy, **p))
    return [
        StrategySpec("EMA+RSI", ema_rsi, {"ema_fast": [5, 9], "ema_slow": [21, 30]}),
        StrategySpec("Breakout", BreakoutStrategy, {"channel": [10, 20, 40]}),
        StrategySpec("Reversao", MeanReversionStrategy, {"oversold": [20, 30]}),
        StrategySpec("EMA+tend", TrendEmaStrategy, {"ema_fast": [5, 9], "trend_ema": [100, 200]}),
        StrategySpec("MACD", MacdStrategy, {"fast": [8, 12], "slow": [21, 26]}),
        StrategySpec("Bollinger", BollingerStrategy, {"period": [14, 20], "k": [2.0, 2.5]}),
        StrategySpec("SuperTrend", SuperTrendStrategy, {"period": [7, 10], "mult": [2.0, 3.0]}),
        StrategySpec("ROC", RocStrategy, {"roc_period": [9, 12], "threshold": [0.0, 0.5]}),
        StrategySpec("RSI-2", Rsi2Strategy, {"oversold": [5, 10], "trend_sma": [100, 200]}),
    ]


def main() -> None:
    try:
        from bot.sources.yfinance_source import load_yfinance
    except ImportError:
        print("yfinance nao instalado. Rode:  pip install yfinance")
        sys.exit(1)

    results: list[ScanResult] = []
    for symbol in ASSETS:
        for clabel, interval, period, day_trade in CONFIGS:
            settings = Settings.default()
            settings.risk.starting_equity = 5_000.0
            settings.day_trade = day_trade
            specs = build_all_specs(settings)
            label = f"{symbol} {clabel}"
            try:
                candles = load_yfinance(symbol, period=period, interval=interval)
            except Exception as exc:
                results.append(ScanResult(label, 0, "-", 0, 0, 0.0, False, str(exc)[:40]))
                continue
            if len(candles) < 200:
                continue
            res = scan_candles(label, candles, settings, specs, n_folds=4)
            results.append(res)
            print(
                f"  ... {label:<20}: {res.best_strategy:<12} "
                f"{res.folds_positive}/{res.n_folds} R$ {res.avg_oos_expectancy:7.2f}"
                f"{'  >>> EDGE' if res.robust else ''}"
            )

    print("\n" + format_scan(results))


if __name__ == "__main__":
    main()
