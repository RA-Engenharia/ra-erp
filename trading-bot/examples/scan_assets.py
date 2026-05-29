"""Varre varios ativos/timeframes procurando vantagem real (dados reais).

    cd trading-bot
    python3 examples/scan_assets.py

Para cada ativo e timeframe, baixa dados reais (yfinance), roda o walk-forward
de todas as estrategias e reporta a melhor. No fim, diz se ALGUM combo mostrou
vantagem robusta -- e, em geral, a resposta honesta e "nenhum", o que ja te
protege de operar no escuro.

Edite ASSETS/TIMEFRAMES para varrer o que quiser.
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
    TrendEmaStrategy,
)
from bot.validation import StrategySpec  # noqa: E402

# Acoes liquidas da B3 (sufixo .SA). Edite a vontade.
ASSETS = [
    "PETR4.SA", "VALE3.SA", "ITUB4.SA", "BBDC4.SA",
    "BBAS3.SA", "ABEV3.SA", "WEGE3.SA", "B3SA3.SA",
]
# (intervalo, periodo). Limites do yfinance: 15m->60d, 1h->730d, 1d->anos.
TIMEFRAMES = [("1d", "3y"), ("1h", "360d")]


def build_specs(settings: Settings) -> list[StrategySpec]:
    return [
        StrategySpec(
            "EMA+RSI",
            lambda p: EmaRsiAtrStrategy(replace(settings.strategy, **p)),
            {"ema_fast": [5, 9], "ema_slow": [21, 30]},
        ),
        StrategySpec("Breakout", BreakoutStrategy, {"channel": [10, 20, 40]}),
        StrategySpec("Reversao", MeanReversionStrategy, {"oversold": [20, 30]}),
        StrategySpec("EMA+tendencia", TrendEmaStrategy, {"ema_fast": [5, 9], "trend_ema": [100, 200]}),
        StrategySpec("MACD", MacdStrategy, {"fast": [8, 12], "slow": [21, 26]}),
        StrategySpec("Bollinger", BollingerStrategy, {"period": [14, 20], "k": [2.0, 2.5]}),
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
                print(f"  ... {label}: erro ({str(exc)[:40]})")
                continue
            if len(candles) < 200:
                results.append(ScanResult(label, len(candles), "-", 0, 0, 0.0, False, "poucos dados"))
                print(f"  ... {label}: poucos dados ({len(candles)})")
                continue
            res = scan_candles(label, candles, settings, specs, n_folds=4)
            results.append(res)
            print(
                f"  ... {label}: {res.best_strategy} "
                f"{res.folds_positive}/{res.n_folds} exp R$ {res.avg_oos_expectancy:.2f}"
                f"{'  >>> EDGE' if res.robust else ''}"
            )

    print("\n" + format_scan(results))


if __name__ == "__main__":
    main()
