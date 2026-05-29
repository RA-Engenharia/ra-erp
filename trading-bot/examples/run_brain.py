"""Cerebro central: analisa todas as estrategias, monta o comite e opera ao vivo.

    cd trading-bot
    python3 examples/run_brain.py

Fluxo completo do que voce pediu:
  1) busca/gera os dados,
  2) ANALISA cada estrategia (walk-forward) e da peso de voto so as robustas,
  3) monta o CEREBRO (comite ponderado) e mostra quem ganhou voz,
  4) liga o cerebro num feed (aqui replay; troque por DataSourceConfig ccxt
     para precos reais) e opera em paper trading.

Tudo offline. Em dados sinteticos, o esperado e o cerebro ficar PARADO -- e
isso e o sistema te protegendo, nao uma falha.
"""

from __future__ import annotations

import os
import sys
from dataclasses import replace
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bot import EmaRsiAtrStrategy, Settings, generate_synthetic_candles  # noqa: E402
from bot.brain import build_brain, format_brain_report  # noqa: E402
from bot.chart import equity_curve_ascii  # noqa: E402
from bot.live import LiveTrader, run_live  # noqa: E402
from bot.sources import DataSourceConfig, build_feed  # noqa: E402
from bot.strategies import (  # noqa: E402
    BollingerStrategy,
    BreakoutStrategy,
    MacdStrategy,
    MeanReversionStrategy,
    TrendEmaStrategy,
)
from bot.validation import StrategySpec  # noqa: E402


def main() -> None:
    settings = Settings.default()
    settings.risk.starting_equity = 5_000.0
    candles = generate_synthetic_candles(n_days=120, seed=21)

    specs = [
        StrategySpec(
            "EMA+RSI",
            lambda p: EmaRsiAtrStrategy(replace(settings.strategy, **p)),
            {"ema_fast": [5, 9], "ema_slow": [21, 30]},
        ),
        StrategySpec("Breakout", BreakoutStrategy, {"channel": [10, 20, 40]}),
        StrategySpec("Reversao", MeanReversionStrategy, {"oversold": [20, 30]}),
        StrategySpec("EMA+tendencia", TrendEmaStrategy, {"ema_fast": [5, 9], "trend_ema": [100, 200]}),
        StrategySpec("MACD", MacdStrategy, {"fast": [8, 12], "slow": [21, 26]}),
        StrategySpec("Bollinger", BollingerStrategy, {"period": [14, 20], "k": [2.0, 2.5]}),
    ]

    print("Analisando estrategias (walk-forward) e montando o cerebro...\n")
    brain, diags = build_brain(candles, settings, specs, n_folds=4, min_consensus=0.5)
    print(format_brain_report(diags, min_consensus=brain.min_consensus))

    # Liga o cerebro num feed. Para precos REAIS, troque por:
    #   cfg = DataSourceConfig(provider="ccxt", symbol="BTC/USDT", timeframe="5m")
    #   feed = build_feed(cfg)
    cfg = DataSourceConfig(provider="replay")
    feed = build_feed(cfg, candles=candles)
    print(f"\nFonte de dados: {cfg.describe()}")

    trader = LiveTrader(brain, settings, warmup=brain.warmup)

    def show(u):
        if u.event and ("entrada" in u.event or "saida" in u.event):
            ts = datetime.fromtimestamp(u.ts, tz=timezone.utc)
            print(f"  {ts:%d/%m %H:%M} | R$ {u.price:9,.0f} | equity R$ {u.equity:8,.0f} | {u.event}")

    print("\nCerebro operando (paper trading):")
    updates = run_live(trader, feed.stream(), on_update=show)
    if not any(u.event and "entrada" in (u.event or "") for u in updates):
        print("  (o cerebro nao abriu nenhuma operacao -- sem consenso/vantagem)")

    print(f"\nEquity final: R$ {trader.risk.equity:,.2f}  ({len(trader.trades)} trades)")
    print("\n" + equity_curve_ascii(trader.equity_curve))


if __name__ == "__main__":
    main()
