"""Testa as estrategias em ALTA, BAIXA e LATERAL + mostra a curva de capital.

    cd trading-bot
    python3 examples/regime_robustness.py

A pergunta que separa amador de profissional NAO e "quanto rendeu?", e sim
"sobrevive quando o mercado vira?". Aqui cada estrategia enfrenta os tres
regimes; so a que aguenta os tres merece atencao. Tudo offline.
"""

from __future__ import annotations

import os
import sys
from dataclasses import replace

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bot import EmaRsiAtrStrategy, Settings  # noqa: E402
from bot.backtest import run_backtest  # noqa: E402
from bot.chart import equity_curve_ascii  # noqa: E402
from bot.data import generate_regime_candles  # noqa: E402
from bot.strategies import (  # noqa: E402
    BreakoutStrategy,
    MeanReversionStrategy,
    TrendEmaStrategy,
)
from bot.validation import (  # noqa: E402
    StrategySpec,
    compare_across_datasets,
    format_regime_report,
)


def main() -> None:
    settings = Settings.default()
    settings.risk.starting_equity = 5_000.0

    regimes = ["bull", "bear", "sideways"]
    datasets = {r: generate_regime_candles(r, n_days=160, seed=7) for r in regimes}

    specs = [
        StrategySpec(
            "EMA+RSI (base)",
            lambda p: EmaRsiAtrStrategy(replace(settings.strategy, **p)),
            {"ema_fast": [5, 9], "ema_slow": [21, 30], "stop_atr_mult": [1.0, 1.5]},
        ),
        StrategySpec(
            "Breakout Donchian",
            BreakoutStrategy,
            {"channel": [10, 20, 40], "stop_atr_mult": [1.0, 1.5], "reward_risk": [1.0, 1.5]},
        ),
        StrategySpec(
            "Reversao a media",
            MeanReversionStrategy,
            {"oversold": [20, 30], "overbought": [70, 80], "stop_atr_mult": [1.0, 1.5]},
        ),
        StrategySpec(
            "EMA + filtro tendencia",
            TrendEmaStrategy,
            {"ema_fast": [5, 9], "ema_slow": [21, 30], "trend_ema": [100, 200]},
        ),
    ]

    rows = compare_across_datasets(datasets, settings, specs, n_folds=3)
    print(format_regime_report(rows, regimes))

    # Curva de capital da melhor colocada, no regime de ALTA, com defaults.
    best_name = rows[0].name
    best_spec = next(s for s in specs if s.name == best_name)
    result = run_backtest(datasets["bull"], best_spec.make({}), settings)
    print(f"\nCurva de capital de '{best_name}' em mercado de ALTA:\n")
    print(equity_curve_ascii(result.equity_curve))


if __name__ == "__main__":
    main()
