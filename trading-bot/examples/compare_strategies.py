"""Compara varias estrategias pelo juiz imparcial (walk-forward). Offline.

    cd trading-bot
    python3 examples/compare_strategies.py

Ranqueia as candidatas por robustez FORA-DA-AMOSTRA. A vencedora (se houver)
e a unica que merece ir para a proxima fase -- nunca a que "rendeu mais" no
backtest simples.
"""

from __future__ import annotations

import os
import sys
from dataclasses import replace

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bot import EmaRsiAtrStrategy, Settings, generate_synthetic_candles  # noqa: E402
from bot.strategies import (  # noqa: E402
    BollingerStrategy,
    BreakoutStrategy,
    MacdStrategy,
    MeanReversionStrategy,
    TrendEmaStrategy,
)
from bot.validation import (  # noqa: E402
    StrategySpec,
    compare_strategies,
    format_comparison,
    format_walk_forward_report,
)


def main() -> None:
    candles = generate_synthetic_candles(n_days=240, bars_per_day=80, seed=13)
    settings = Settings.default()
    settings.risk.starting_equity = 5_000.0

    specs = [
        StrategySpec(
            "EMA+RSI (base)",
            lambda p: EmaRsiAtrStrategy(replace(settings.strategy, **p)),
            {"ema_fast": [5, 9, 12], "ema_slow": [21, 30, 50], "stop_atr_mult": [1.0, 1.5, 2.0]},
        ),
        StrategySpec(
            "Breakout Donchian",
            BreakoutStrategy,
            {"channel": [10, 20, 40], "stop_atr_mult": [1.0, 1.5, 2.0], "reward_risk": [1.0, 1.5, 2.0]},
        ),
        StrategySpec(
            "Reversao a media",
            MeanReversionStrategy,
            {"oversold": [20, 30], "overbought": [70, 80], "stop_atr_mult": [1.0, 1.5, 2.0]},
        ),
        StrategySpec(
            "EMA + filtro tendencia",
            TrendEmaStrategy,
            {"ema_fast": [5, 9], "ema_slow": [21, 30], "trend_ema": [100, 200], "stop_atr_mult": [1.0, 1.5]},
        ),
        StrategySpec(
            "MACD",
            MacdStrategy,
            {"fast": [8, 12], "slow": [21, 26], "signal": [9], "stop_atr_mult": [1.0, 1.5]},
        ),
        StrategySpec(
            "Bollinger (reversao)",
            BollingerStrategy,
            {"period": [14, 20], "k": [2.0, 2.5], "stop_atr_mult": [1.0, 1.5]},
        ),
    ]

    rows = compare_strategies(candles, settings, specs, n_folds=4)
    print(format_comparison(rows))
    print("\nDetalhe walk-forward da melhor colocada:\n")
    print(format_walk_forward_report(rows[0].folds))


if __name__ == "__main__":
    main()
