"""Demonstra a validacao anti-overfitting -- 100% offline (dados sinteticos).

    cd trading-bot
    python3 examples/run_validation.py

Mostra: (1) busca de parametros + teste fora-da-amostra; (2) walk-forward.
A licao: parametros "otimos" no passado costumam decepcionar no futuro.
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bot import Settings, generate_synthetic_candles  # noqa: E402
from bot.validation import (  # noqa: E402
    format_split_report,
    format_walk_forward_report,
    train_test,
    walk_forward,
)

# Grade de parametros a testar (espaco de busca da otimizacao).
GRID = {
    "ema_fast": [5, 9, 12],
    "ema_slow": [21, 30, 50],
    "stop_atr_mult": [1.0, 1.5, 2.0],
    "reward_risk": [1.0, 1.5, 2.0],
}


def main() -> None:
    candles = generate_synthetic_candles(n_days=200, bars_per_day=80, seed=7)
    settings = Settings.default()
    settings.risk.starting_equity = 5_000.0

    split = train_test(candles, settings, GRID, train_frac=0.7)
    if split is None:
        print("Nenhuma combinacao com trades suficientes.")
        return
    print(format_split_report(split))
    print()
    folds = walk_forward(candles, settings, GRID, n_folds=4)
    print(format_walk_forward_report(folds))


if __name__ == "__main__":
    main()
