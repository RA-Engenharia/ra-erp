"""Checagem DIARIA do cerebro (swing) -- roda uma vez e mostra tudo.

    cd trading-bot
    python3 examples/daily_check.py                # WEGE3.SA swing diario
    python3 examples/daily_check.py ITUB4.SA

Ideal para swing diario: o candle do dia so fecha uma vez, entao voce roda ISTO
uma vez por dia (de preferencia depois do fechamento do pregao) e ele mostra:
  1) quais estrategias o cerebro considera robustas neste ativo (analise);
  2) a POSICAO ATUAL do cerebro hoje (comprado / vendido / de fora);
  3) o historico simulado (paper) e a curva de capital.

Ordens SIMULADAS. Nenhuma ordem real, nenhum dinheiro. Termina sozinho.
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
from bot.monitor import format_dashboard, summarize  # noqa: E402
from bot.monitor import TradeRow  # noqa: E402
from bot.live import candle_feed  # noqa: E402
from bot.strategies import (  # noqa: E402
    BollingerStrategy,
    BreakoutStrategy,
    MacdStrategy,
    MeanReversionStrategy,
    RocStrategy,
    Rsi2Strategy,
    SuperTrendStrategy,
    TrendEmaStrategy,
)
from bot.validation import StrategySpec  # noqa: E402

STARTING_EQUITY = 5_000.0


def build_specs(settings: Settings) -> list[StrategySpec]:
    ema_rsi = lambda p: EmaRsiAtrStrategy(replace(settings.strategy, **p))
    return [
        StrategySpec("EMA+RSI", ema_rsi, {"ema_fast": [5, 9], "ema_slow": [21, 30]}),
        StrategySpec("Breakout", BreakoutStrategy, {"channel": [10, 20, 40]}),
        StrategySpec("Reversao", MeanReversionStrategy, {"oversold": [20, 30]}),
        StrategySpec("EMA+tend", TrendEmaStrategy, {"ema_fast": [5, 9], "trend_ema": [100, 200]}),
        StrategySpec("MACD", MacdStrategy, {"fast": [8, 12], "slow": [21, 26]}),
        StrategySpec("Bollinger", BollingerStrategy, {"period": [14, 20], "k": [2.0, 2.5]}),
        StrategySpec("SuperTrend", SuperTrendStrategy, {"period": [7, 10], "mult": [2.0, 3.0]}),
        StrategySpec("ROC", RocStrategy, {"roc_period": [9, 12], "threshold": [0.0, 0.5]}),
        StrategySpec("RSI-2", Rsi2Strategy, {"oversold": [5, 10], "trend_sma": [100, 200]}),
    ]


def main() -> None:
    symbol = sys.argv[1] if len(sys.argv) > 1 else "WEGE3.SA"

    settings = Settings.default()
    settings.risk.starting_equity = STARTING_EQUITY
    settings.day_trade = False  # SWING

    try:
        from bot.sources.yfinance_source import load_yfinance
    except ImportError:
        print("yfinance nao instalado. Rode:  pip install yfinance  (ou setup.bat)")
        sys.exit(1)

    print("=" * 60)
    print(f"  CHECAGEM DIARIA -- {symbol} (SWING) -- paper, sem dinheiro real")
    print("=" * 60)
    print("Baixando historico diario e analisando...\n")
    history = load_yfinance(symbol, period="5y", interval="1d")

    brain, diags = build_brain(history, settings, build_specs(settings), n_folds=4)
    print(format_brain_report(diags, min_consensus=brain.min_consensus))

    if all(d.weight <= 0 for d in diags):
        print("\n>> Nenhuma estrategia e robusta neste ativo: o cerebro fica DE FORA.")
        print("   Nao opere. Tente outro ativo (ex.: daily_check.py ITUB4.SA).")
        return

    # opera em paper sobre o historico recente -> posicao ATUAL = stance de hoje
    recent = history[-600:]
    trader = LiveTrader(brain, settings, warmup=brain.warmup)
    run_live(trader, candle_feed(recent))

    # 1) decisao de hoje
    pos = trader.broker.position
    print("\n" + "=" * 60)
    print("  DECISAO DO CEREBRO HOJE")
    print("=" * 60)
    if pos is None:
        print("  >> DE FORA (sem posicao). Nenhuma acao hoje -- aguardar sinal.")
    else:
        lado = "COMPRADO (long)" if pos.side == "long" else "VENDIDO (short)"
        print(f"  >> {lado} | entrada ~R$ {pos.entry:,.2f} | stop R$ {pos.stop:,.2f} | alvo R$ {pos.take:,.2f}")
        print("     (no PAPER. Se fosse real, seria esta a posicao a manter.)")

    # 2) historico (painel)
    rows = [
        TradeRow(t.entry, t.exit, t.side, t.qty, t.pnl, t.reason, t.exit_ts)
        for t in trader.trades
    ]
    if rows:
        data_dir = os.path.join(os.path.dirname(__file__), "..", "data")
        os.makedirs(data_dir, exist_ok=True)
        with open(os.path.join(data_dir, "daily_trades.csv"), "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["entry", "exit", "side", "qty", "pnl", "reason", "exit_ts"])
            for t in trader.trades:
                w.writerow([t.entry, t.exit, t.side, t.qty, round(t.pnl, 2), t.reason, t.exit_ts])
        print("\n" + format_dashboard(summarize(rows, STARTING_EQUITY), STARTING_EQUITY))
    else:
        print("\n  (sem operacoes simuladas no periodo recente analisado)")

    stamp = datetime.now(tz=timezone.utc).strftime("%d/%m/%Y")
    print(f"\n  Checagem de {stamp}. Rode novamente amanha apos o pregao.")


if __name__ == "__main__":
    main()
