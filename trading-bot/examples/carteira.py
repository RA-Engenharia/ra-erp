"""Painel de CARTEIRA -- a decisao do cerebro para varias acoes de uma vez.

    cd trading-bot
    python3 examples/carteira.py

Roda o cerebro (swing diario, com aluguel nos shorts) em cada acao da cesta
robusta e mostra, num quadro so: a decisao de HOJE (comprar/vender/de fora), o
tamanho do comite e o track record simulado de cada uma -- mais o agregado.

Diversificacao: acompanhar a cesta inteira e mais confiavel que uma acao so.
Ordens SIMULADAS, sem dinheiro real.
"""

from __future__ import annotations

import os
import sys
from dataclasses import replace

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bot import EmaRsiAtrStrategy, Settings  # noqa: E402
from bot.brain import build_brain  # noqa: E402
from bot.live import LiveTrader, candle_feed, run_live  # noqa: E402
from bot.monitor import TradeRow, summarize  # noqa: E402
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

# cesta que passou na re-validacao (revalidate.py), swing diario
CARTEIRA = ["B3SA3.SA", "PETR4.SA", "BBDC4.SA", "WEGE3.SA", "ITUB4.SA", "ABEV3.SA", "BBAS3.SA"]
START = 5_000.0
BORROW = 0.05


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


def analisar(symbol: str, load_yfinance):
    settings = Settings.default()
    settings.risk.starting_equity = START
    settings.day_trade = False
    settings.costs.short_borrow_annual_pct = BORROW
    candles = load_yfinance(symbol, period="5y", interval="1d")
    brain, diags = build_brain(candles, settings, build_specs(settings), n_folds=4)
    n_ativos = sum(1 for d in diags if d.weight > 0)
    trader = LiveTrader(brain, settings, warmup=brain.warmup)
    run_live(trader, candle_feed(candles[-600:]))
    pos = trader.broker.position
    decisao = "DE FORA" if pos is None else ("COMPRAR" if pos.side == "long" else "VENDER")
    rows = [TradeRow(t.entry, t.exit, t.side, t.qty, t.pnl, t.reason, t.exit_ts) for t in trader.trades]
    m = summarize(rows, START) if rows else None
    return decisao, n_ativos, m


def main() -> None:
    try:
        from bot.sources.yfinance_source import load_yfinance
    except ImportError:
        print("yfinance nao instalado. Rode:  pip install yfinance  (ou setup.bat)")
        sys.exit(1)

    print("=" * 68)
    print("  PAINEL DE CARTEIRA -- cerebro swing diario (paper, aluguel %.0f%%/ano)" % (BORROW * 100))
    print("=" * 68)
    print(f"  {'Acao':<10} {'HOJE':<9} {'comite':<7} {'trades':<7} {'acerto':<7} {'result%':<8}")
    print("  " + "-" * 60)

    rets, decisoes = [], {"COMPRAR": [], "VENDER": [], "DE FORA": []}
    for sym in CARTEIRA:
        try:
            decisao, n_ativos, m = analisar(sym, load_yfinance)
        except Exception as exc:
            print(f"  {sym:<10} erro: {str(exc)[:40]}")
            continue
        decisoes[decisao].append(sym)
        if m:
            ret = (m["final_equity"] - START) / START
            rets.append(ret)
            print(f"  {sym:<10} {decisao:<9} {n_ativos:<7} {m['n_trades']:<7} "
                  f"{m['win_rate']:<7.0%} {ret:<+8.1%}")
        else:
            print(f"  {sym:<10} {decisao:<9} {n_ativos:<7} {'0':<7} {'-':<7} {'-':<8}")

    print("  " + "-" * 60)
    print("\n  RESUMO DA CARTEIRA:")
    for k in ("COMPRAR", "VENDER", "DE FORA"):
        nomes = ", ".join(s.replace(".SA", "") for s in decisoes[k]) or "-"
        print(f"    {k:<8}: {len(decisoes[k])} ({nomes})")
    if rets:
        media = sum(rets) / len(rets)
        print(f"\n  Resultado simulado medio da cesta: {media:+.1%}  "
              f"(cada acao com R$ {START:,.0f}, ~2.4 anos)")
    print("\n  Lembre: PAPER. So sinal/ensaio. Forward test por meses antes de R$ real.")
    print("=" * 68)


if __name__ == "__main__":
    main()
