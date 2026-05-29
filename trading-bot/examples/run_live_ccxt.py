"""Esqueleto de paper trading com feed REAL de corretora (via ccxt).

    pip install ccxt
    cd trading-bot
    python3 examples/run_live_ccxt.py BTC/USDT 5m binance

ATENCAO: isto so LE precos reais e simula as ordens no PaperBroker (papel).
Nenhuma ordem e enviada para a corretora -- e o ensaio antes do dinheiro real.
Para operar de verdade, troque o PaperBroker por um broker que envie ordens
(implementando a mesma interface open/update/close) e ai sim use com cautela.
"""

from __future__ import annotations

import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bot import EmaRsiAtrStrategy, Settings  # noqa: E402
from bot.feeds import CcxtLiveFeed  # noqa: E402
from bot.live import LiveTrader, run_live  # noqa: E402


def main() -> None:
    symbol = sys.argv[1] if len(sys.argv) > 1 else "BTC/USDT"
    timeframe = sys.argv[2] if len(sys.argv) > 2 else "5m"
    exchange = sys.argv[3] if len(sys.argv) > 3 else "binance"

    settings = Settings.default()
    settings.risk.starting_equity = 1_000.0
    trader = LiveTrader(EmaRsiAtrStrategy(settings.strategy), settings)

    print(f"Paper trading AO VIVO em {symbol} ({timeframe} @ {exchange}).")
    print("Lendo precos reais; ordens SIMULADAS. Ctrl+C para parar.\n")

    def show(u):
        if u.event:
            ts = datetime.fromtimestamp(u.ts, tz=timezone.utc)
            print(
                f"  {ts:%d/%m %H:%M} | {u.price:12,.2f} | "
                f"equity {u.equity:9,.2f} | {u.event}"
            )

    try:
        feed = CcxtLiveFeed(symbol=symbol, timeframe=timeframe, exchange_id=exchange)
        run_live(trader, feed.stream(), on_update=show)
    except RuntimeError as exc:
        print(exc)
        sys.exit(1)
    except KeyboardInterrupt:
        print(f"\nEncerrado pelo usuario. Equity final: R$ {trader.risk.equity:,.2f}")


if __name__ == "__main__":
    main()
