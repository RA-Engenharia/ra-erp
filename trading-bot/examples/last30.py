"""Diario dos ultimos N dias -- mostra o COMPORTAMENTO do cerebro dia a dia.

    cd trading-bot
    python3 examples/last30.py                 # WEGE3.SA, 30 dias
    python3 examples/last30.py ITUB4.SA 30

Para cada dia recente exibe: preco de fechamento, a POSICAO do cerebro (de fora
/ comprado / vendido) e o evento (entrada/saida). No fim, resume o padrao: quanto
tempo ficou em cada estado e quais estrategias dispararam as entradas.

Swing diario, ordens SIMULADAS. Ajuda a ver se ha um padrao/estrategia estavel
de comportamento, nao so um numero final.
"""

from __future__ import annotations

import os
import sys
from dataclasses import replace
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bot import EmaRsiAtrStrategy, Settings  # noqa: E402
from bot.brain import build_brain  # noqa: E402
from bot.live import LiveTrader, candle_feed, run_live  # noqa: E402
from bot.strategies import (  # noqa: E402
    BollingerStrategy,
    BreakdownStrategy,
    BreakoutStrategy,
    DowntrendStrategy,
    MacdStrategy,
    MeanReversionStrategy,
    RocStrategy,
    Rsi2Strategy,
    SuperTrendStrategy,
    TrendEmaStrategy,
)
from bot.validation import StrategySpec  # noqa: E402


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
        StrategySpec("Breakdown", BreakdownStrategy, {"channel": [10, 20, 40]}),
        StrategySpec("Downtrend", DowntrendStrategy, {"ema_fast": [5, 9], "trend_ema": [100, 200]}),
    ]


def main() -> None:
    symbol = sys.argv[1] if len(sys.argv) > 1 else "WEGE3.SA"
    n_days = int(sys.argv[2]) if len(sys.argv) > 2 else 30

    settings = Settings.default()
    settings.risk.starting_equity = 5_000.0
    settings.day_trade = False  # SWING

    try:
        from bot.sources.yfinance_source import load_yfinance
    except ImportError:
        print("yfinance nao instalado. Rode:  pip install yfinance  (ou setup.bat)")
        sys.exit(1)

    print("=" * 64)
    print(f"  DIARIO DOS ULTIMOS {n_days} DIAS -- {symbol} (SWING, paper)")
    print("=" * 64)
    print("Baixando historico e montando o cerebro...\n")
    history = load_yfinance(symbol, period="5y", interval="1d")
    brain, diags = build_brain(history, settings, build_specs(settings), n_folds=4)

    ativos = [d.name for d in diags if d.weight > 0]
    if not ativos:
        print(">> Nenhuma estrategia robusta neste ativo: o cerebro fica DE FORA sempre.")
        print("   Sem padrao a mostrar. Tente outro ativo.")
        return
    print(f"Comite ativo: {', '.join(ativos)}\n")

    # roda o cerebro sobre o historico recente e captura o estado de cada dia
    recent = history[-(n_days + 260):]  # folga para aquecer (trend_sma ate 200)
    trader = LiveTrader(brain, settings, warmup=brain.warmup)
    updates = run_live(trader, candle_feed(recent))

    last = updates[-n_days:]
    print(f"  {'Data':<8} {'Fech.':>10}  {'Posicao':<8}  Evento")
    print("  " + "-" * 56)
    counts = {"FORA": 0, "LONG": 0, "SHORT": 0}
    entradas: dict[str, int] = {}
    for u in last:
        d = datetime.fromtimestamp(u.ts, tz=timezone.utc).strftime("%d/%m")
        pos = {None: "FORA", "long": "LONG", "short": "SHORT"}[u.position]
        counts[pos] += 1
        ev = u.event or ""
        if u.event and "entrada" in u.event:
            # extrai os nomes das estrategias do motivo (apos "consenso X%:")
            tag = u.event.split(":")[-1]
            entradas[tag] = entradas.get(tag, 0) + 1
        print(f"  {d:<8} {u.price:>10,.2f}  {pos:<8}  {ev}")

    print("  " + "-" * 56)
    total = len(last)
    print("\n  PADRAO DE COMPORTAMENTO (ultimos %d dias):" % total)
    for estado in ("LONG", "SHORT", "FORA"):
        c = counts[estado]
        print(f"    {estado:<6}: {c:>3} dias ({c/total:.0%})")
    if entradas:
        print("\n  Entradas dispararam por (consenso de estrategias):")
        for tag, c in sorted(entradas.items(), key=lambda x: -x[1]):
            print(f"    {c}x  {tag}")
    else:
        print("\n  Nenhuma ENTRADA nova nesta janela (so manutencao/espera).")

    pos_now = trader.broker.position
    estado_hoje = "DE FORA" if pos_now is None else (
        "COMPRADO" if pos_now.side == "long" else "VENDIDO")
    print(f"\n  Estado de HOJE: {estado_hoje}.")
    print("=" * 64)


if __name__ == "__main__":
    main()
