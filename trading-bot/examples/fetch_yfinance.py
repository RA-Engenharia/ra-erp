"""Fluxo COMPLETO com dados REAIS de acoes (EUA) -- rode NA SUA MAQUINA.

Precisa de internet e da biblioteca yfinance:
    pip install yfinance

Uso:
    cd trading-bot
    python3 examples/fetch_yfinance.py AAPL 60d 5m

Baixa os dados, roda o backtest e a validacao (treino/teste + walk-forward).
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bot import (  # noqa: E402
    EmaRsiAtrStrategy,
    Settings,
    format_report,
    run_backtest,
)
from bot.sources.yfinance_source import load_yfinance  # noqa: E402
from bot.validation import (  # noqa: E402
    format_split_report,
    format_walk_forward_report,
    train_test,
    walk_forward,
)

GRID = {
    "ema_fast": [5, 9, 12],
    "ema_slow": [21, 30, 50],
    "stop_atr_mult": [1.0, 1.5, 2.0],
    "reward_risk": [1.0, 1.5, 2.0],
}


def main() -> None:
    symbol = sys.argv[1] if len(sys.argv) > 1 else "AAPL"
    period = sys.argv[2] if len(sys.argv) > 2 else "60d"
    interval = sys.argv[3] if len(sys.argv) > 3 else "5m"

    print(f"Baixando {symbol} (period={period}, interval={interval})...")
    candles = load_yfinance(symbol, period=period, interval=interval)
    print(f"{len(candles)} candles baixados.\n")

    settings = Settings.default()
    settings.risk.starting_equity = 5_000.0

    # 1) Backtest com os parametros padrao (referencia)
    result = run_backtest(candles, EmaRsiAtrStrategy(settings.strategy), settings)
    print(format_report(result))
    print()

    # 2) Validacao honesta
    split = train_test(candles, settings, GRID, train_frac=0.7)
    if split is not None:
        print(format_split_report(split))
        print()
    print(format_walk_forward_report(walk_forward(candles, settings, GRID, n_folds=4)))


if __name__ == "__main__":
    main()
