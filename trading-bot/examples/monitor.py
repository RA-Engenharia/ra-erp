"""Mostra o painel do ensaio a partir do log de trades ao vivo.

    cd trading-bot
    python3 examples/monitor.py                       # le data/live_trades.csv
    python3 examples/monitor.py caminho/para/arquivo.csv

Use durante as semanas de paper trading para acompanhar o resultado com
numeros (acertos, fator de lucro, drawdown, curva de capital) em vez de
torcida. Nenhuma ordem real envolvida.
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bot.monitor import format_dashboard, load_trades_csv, summarize  # noqa: E402

STARTING_EQUITY = 5_000.0


def main() -> None:
    default = os.path.join(os.path.dirname(__file__), "..", "data", "live_trades.csv")
    path = sys.argv[1] if len(sys.argv) > 1 else default

    if not os.path.exists(path):
        print(f"Log nao encontrado: {os.path.relpath(path)}")
        print("Rode o paper trading ao vivo primeiro:  python3 examples/run_live_brain.py")
        print("(ou no Windows:  live_brain.bat)")
        return

    trades = load_trades_csv(path)
    if not trades:
        print("O log existe, mas ainda nao ha trades registrados.")
        return

    summary = summarize(trades, STARTING_EQUITY)
    print(format_dashboard(summary, STARTING_EQUITY))


if __name__ == "__main__":
    main()
