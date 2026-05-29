"""A/B honesto: as mesmas estrategias, agora com FILTRO DE REGIME.

    cd trading-bot
    python3 examples/scan_filtered.py

Cada estrategia so opera no ambiente onde faz sentido (momentum em tendencia,
reversao em mercado lateral). Comparamos com a varredura SEM filtro
(scan_assets.py) para ver se o filtro melhora a robustez fora-da-amostra --
sem trapacear: o limiar do filtro e fixo, nao otimizado.
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
    RegimeFilteredStrategy,
    TrendEmaStrategy,
)
from bot.validation import StrategySpec  # noqa: E402

ASSETS = [
    "PETR4.SA", "VALE3.SA", "ITUB4.SA", "BBDC4.SA",
    "BBAS3.SA", "ABEV3.SA", "WEGE3.SA", "B3SA3.SA",
]
TIMEFRAMES = [("1h", "360d")]  # onde a varredura base mostrou algum sinal


def trend(base_factory):
    """Embrulha uma estrategia de momentum: so opera em tendencia forte."""
    return lambda p: RegimeFilteredStrategy(base_factory(p), mode="trend")


def ranging(base_factory):
    """Embrulha uma estrategia de reversao: so opera em mercado lateral."""
    return lambda p: RegimeFilteredStrategy(base_factory(p), mode="range")


def build_specs(settings: Settings) -> list[StrategySpec]:
    ema_rsi = lambda p: EmaRsiAtrStrategy(replace(settings.strategy, **p))
    return [
        StrategySpec("EMA+RSI/trend", trend(ema_rsi), {"ema_fast": [5, 9], "ema_slow": [21, 30]}),
        StrategySpec("Breakout/trend", trend(BreakoutStrategy), {"channel": [10, 20, 40]}),
        StrategySpec("MACD/trend", trend(MacdStrategy), {"fast": [8, 12], "slow": [21, 26]}),
        StrategySpec("EMA+tend/trend", trend(TrendEmaStrategy), {"ema_fast": [5, 9], "trend_ema": [100, 200]}),
        StrategySpec("Reversao/range", ranging(MeanReversionStrategy), {"oversold": [20, 30]}),
        StrategySpec("Bollinger/range", ranging(BollingerStrategy), {"period": [14, 20], "k": [2.0, 2.5]}),
    ]


def main() -> None:
    settings = Settings.default()
    settings.risk.starting_equity = 5_000.0
    specs = build_specs(settings)

    try:
        from bot.sources.yfinance_source import load_yfinance
    except ImportError:
        print("yfinance nao instalado. Rode:  pip install yfinance")
        sys.exit(1)

    results: list[ScanResult] = []
    for interval, period in TIMEFRAMES:
        for symbol in ASSETS:
            label = f"{symbol} {interval}"
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
                f"  ... {label}: {res.best_strategy} {res.folds_positive}/{res.n_folds} "
                f"exp R$ {res.avg_oos_expectancy:.2f}{'  >>> EDGE' if res.robust else ''}"
            )

    print("\n  COM FILTRO DE REGIME:")
    print(format_scan(results))


if __name__ == "__main__":
    main()
