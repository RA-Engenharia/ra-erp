"""Paper trading AO VIVO (feed simulado). Mostra as decisoes em tempo real.

    cd trading-bot
    python3 examples/run_live.py

Cada linha e uma decisao do robo conforme os candles "chegam". No fim, o
relatorio e a curva de capital. Para ir ao vivo de verdade, troque o feed
sintetico por um feed da sua corretora -- o motor nao muda.

Dica: passe um atraso para ver em camera lenta:  python3 examples/run_live.py 0.01
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bot import EmaRsiAtrStrategy, Settings, generate_synthetic_candles  # noqa: E402
from bot.backtest import compute_metrics, format_report, BacktestResult  # noqa: E402
from bot.chart import equity_curve_ascii  # noqa: E402
from bot.live import LiveTrader, candle_feed, run_live  # noqa: E402


def main() -> None:
    delay = float(sys.argv[1]) if len(sys.argv) > 1 else 0.0

    settings = Settings.default()
    settings.risk.starting_equity = 5_000.0
    candles = generate_synthetic_candles(n_days=30, seed=21)

    trader = LiveTrader(EmaRsiAtrStrategy(settings.strategy), settings)

    print("Robo ligado. Aguardando candles...\n")

    from datetime import datetime, timezone

    def show(u):
        if u.event:  # so imprime quando algo acontece
            ts = datetime.fromtimestamp(u.ts, tz=timezone.utc)
            print(
                f"  {ts:%d/%m %H:%M} | R$ {u.price:9,.0f} | "
                f"equity R$ {u.equity:8,.0f} | {u.event}"
            )

    updates = run_live(trader, candle_feed(candles, delay), on_update=show)

    last = updates[-1] if updates else None
    if last and last.halted:
        print(f"\n  !! ROBO DESLIGADO PELO RISCO: {last.note}\n")

    # Reaproveita o relatorio do backtest a partir do estado final ao vivo.
    metrics = compute_metrics(trader.equity_curve, [], trader.trades, settings)
    result = BacktestResult(
        starting_equity=settings.risk.starting_equity,
        final_equity=trader.risk.equity,
        trades=trader.trades,
        equity_curve=trader.equity_curve,
        halted=trader.risk.halted,
        halt_reason=trader.risk.halt_reason,
        metrics=metrics,
    )
    print("\n" + format_report(result))
    print("\n" + equity_curve_ascii(trader.equity_curve))


if __name__ == "__main__":
    main()
