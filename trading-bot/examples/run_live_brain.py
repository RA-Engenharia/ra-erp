"""PAPER TRADING AO VIVO do cerebro -- etapa 3 (ensaio antes de dinheiro real).

    cd trading-bot
    python3 examples/run_live_brain.py                 # PETR4.SA 1h
    python3 examples/run_live_brain.py VALE3.SA 1h

O que faz:
  1) baixa o historico real do ativo e ANALISA (walk-forward) -> monta o cerebro
     dando voto so as estrategias robustas (momentum filtrado por regime);
  2) liga num feed AO VIVO (yfinance, preco real com atraso) e opera em PAPER
     TRADING: aquece com o historico recente, mostra a decisao atual e depois
     fica aguardando candles novos (no pregao);
  3) registra cada operacao simulada em data/live_trades.csv.

IMPORTANTE: NENHUMA ordem real e enviada. Nenhum centavo e movimentado. Isto e
o ensaio que deve durar SEMANAS e dar resultado positivo ANTES de qualquer
conversa sobre dinheiro real. yfinance tem atraso (~15min) e so atualiza no
pregao -- para tempo real de verdade seria preciso um feed de corretora.
"""

from __future__ import annotations

import csv
import os
import sys
from dataclasses import replace
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bot import EmaRsiAtrStrategy, Settings  # noqa: E402
from bot.brain import build_brain, format_brain_report  # noqa: E402
from bot.live import LiveTrader, run_live  # noqa: E402
from bot.strategies import (  # noqa: E402
    BreakoutStrategy,
    MacdStrategy,
    RegimeFilteredStrategy,
    TrendEmaStrategy,
)
from bot.validation import StrategySpec  # noqa: E402


def trend(base_factory):
    return lambda p: RegimeFilteredStrategy(base_factory(p), mode="trend")


def build_specs(settings: Settings) -> list[StrategySpec]:
    ema_rsi = lambda p: EmaRsiAtrStrategy(replace(settings.strategy, **p))
    # familia de momentum filtrada por regime (a que sobreviveu ao estresse)
    return [
        StrategySpec("EMA+tend/trend", trend(TrendEmaStrategy), {"ema_fast": [5, 9], "trend_ema": [100, 200]}),
        StrategySpec("EMA+RSI/trend", trend(ema_rsi), {"ema_fast": [5, 9], "ema_slow": [21, 30]}),
        StrategySpec("MACD/trend", trend(MacdStrategy), {"fast": [8, 12], "slow": [21, 26]}),
        StrategySpec("Breakout/trend", trend(BreakoutStrategy), {"channel": [10, 20, 40]}),
    ]


def main() -> None:
    symbol = sys.argv[1] if len(sys.argv) > 1 else "PETR4.SA"
    interval = sys.argv[2] if len(sys.argv) > 2 else "1h"
    # 3o arg opcional: limite de candles (para um teste rapido que TERMINA em vez
    # de ficar aguardando o pregao). Sem ele, opera continuamente (Ctrl+C para).
    max_candles = int(sys.argv[3]) if len(sys.argv) > 3 else None

    settings = Settings.default()
    settings.risk.starting_equity = 5_000.0

    try:
        from bot.sources.yfinance_source import YFinanceLiveFeed, load_yfinance
    except ImportError:
        print("yfinance nao instalado. Rode:  pip install yfinance")
        sys.exit(1)

    print("=" * 60)
    print("  PAPER TRADING AO VIVO -- ordens SIMULADAS (nenhuma real)")
    print("=" * 60)
    print(f"  Ativo: {symbol} | Timeframe: {interval}\n")

    # 1) analise -> cerebro
    print("Baixando historico e analisando (walk-forward)...")
    history = load_yfinance(symbol, period="360d", interval=interval)
    brain, diags = build_brain(history, settings, build_specs(settings), n_folds=4)
    print(format_brain_report(diags, min_consensus=brain.min_consensus))

    if all(d.weight <= 0 for d in diags):
        print("\nNenhuma estrategia ganhou voto neste ativo -> o cerebro ficaria")
        print("PARADO. Nao faz sentido operar (nem simulado). Tente outro ativo.")
        return

    # 2) feed ao vivo (catch-up recente para aquecer + aguardar novos candles)
    feed = YFinanceLiveFeed(
        symbol=symbol, interval=interval, period="60d",
        poll_seconds=300, max_candles=max_candles,
    )
    trader = LiveTrader(brain, settings, warmup=brain.warmup)

    log_path = os.path.join(os.path.dirname(__file__), "..", "data")
    os.makedirs(log_path, exist_ok=True)
    csv_file = os.path.join(log_path, "live_trades.csv")

    print("\nAquecendo com historico recente e operando ao vivo...")
    print("(Ctrl+C para parar e ver o resumo)\n")

    def show(u):
        if u.event and ("entrada" in u.event or "saida" in u.event):
            ts = datetime.fromtimestamp(u.ts, tz=timezone.utc)
            print(f"  {ts:%d/%m %H:%M} | R$ {u.price:8,.2f} | equity R$ {u.equity:8,.0f} | {u.event}")

    try:
        run_live(trader, feed.stream(), on_update=show)
    except KeyboardInterrupt:
        print("\n\nParado pelo usuario.")

    # 3) resumo + log
    pnl = trader.risk.equity - settings.risk.starting_equity
    print("\n" + "=" * 60)
    print(f"  RESUMO (PAPER): {len(trader.trades)} trades | "
          f"equity R$ {trader.risk.equity:,.2f} ({pnl:+,.2f})")
    print("=" * 60)
    if trader.trades:
        with open(csv_file, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["entry", "exit", "side", "qty", "pnl", "reason", "exit_ts"])
            for t in trader.trades:
                w.writerow([t.entry, t.exit, t.side, t.qty, round(t.pnl, 2), t.reason, t.exit_ts])
        print(f"  Operacoes simuladas salvas em: {os.path.relpath(csv_file)}")
    print("  Lembre: isto e ENSAIO. Semanas positivas aqui ANTES de dinheiro real.")


if __name__ == "__main__":
    main()
