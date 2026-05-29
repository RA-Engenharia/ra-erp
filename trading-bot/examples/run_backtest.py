"""Demonstracao executavel do robo -- 100% em simulacao (paper trading).

Rode de dentro da pasta trading-bot:

    python3 examples/run_backtest.py

Nao precisa de internet nem de bibliotecas externas. Usa dados sinteticos.
Para usar dados REAIS, troque generate_synthetic_candles(...) por
load_candles_csv("seus_dados.csv").
"""

from __future__ import annotations

import os
import sys

# permite "import bot" rodando de qualquer lugar
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bot import (  # noqa: E402
    EmaRsiAtrStrategy,
    Settings,
    format_report,
    generate_synthetic_candles,
    run_backtest,
)


def main() -> None:
    candles = generate_synthetic_candles(n_days=120, bars_per_day=80, seed=42)
    print(f"Dados: {len(candles)} candles de 5min (~{len(candles)//80} dias)\n")

    # --- 1) Configuracao conservadora (a recomendada) -------------------
    settings = Settings.default()
    settings.risk.starting_equity = 5_000.0
    result = run_backtest(candles, EmaRsiAtrStrategy(settings.strategy), settings)
    print("### CONSERVADOR: risco 1%/trade, perda diaria 3%, drawdown 20% ###")
    print(format_report(result))

    # --- 2) "Apostado" para mostrar o disjuntor de risco agindo ---------
    aggressive = Settings.default()
    aggressive.risk.starting_equity = 5_000.0
    aggressive.risk.risk_per_trade_pct = 0.05  # 5% por trade = imprudente
    aggressive.risk.max_daily_loss_pct = 0.20
    result2 = run_backtest(
        candles, EmaRsiAtrStrategy(aggressive.strategy), aggressive
    )
    print("\n### AGRESSIVO: risco 5%/trade (so para comparar) ###")
    print(format_report(result2))

    print(
        "\nObservacao: em dados aleatorios, uma estrategia ingenua tende ao "
        "empate MENOS os custos.\nO objetivo das proximas fases e encontrar e "
        "VALIDAR uma vantagem real (edge)."
    )


if __name__ == "__main__":
    main()
