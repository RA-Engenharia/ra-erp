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


# Ativo padrao: PETR4 na B3, candles de 15 min dos ultimos 60 dias (yfinance).
# Troque pela linha de comando:  python3 examples/run_brain.py VALE3.SA 15m 60d
#   ou para cripto:               python3 examples/run_brain.py BTC-USD 15m 60d
DEFAULT_SYMBOL = "PETR4.SA"
DEFAULT_INTERVAL = "15m"
DEFAULT_PERIOD = "60d"


def load_market_data(symbol: str, interval: str, period: str):
    """Tenta dados REAIS (yfinance). Sem internet/lib, cai para sintetico.

    Devolve (candles, descricao, eh_real).
    """
    try:
        from bot.sources.yfinance_source import load_yfinance

        candles = load_yfinance(symbol, period=period, interval=interval)
        return candles, f"{symbol} REAL via yfinance ({period} @ {interval})", True
    except Exception as exc:  # ImportError (sem lib) ou erro de rede/ticker
        print(f"  [aviso] nao foi possivel baixar dados reais: {exc}")
        print("  [aviso] usando dados SINTETICOS (offline) para demonstrar o fluxo.\n")
        # tamanho proximo de ~1 dado intraday real (mantem o demo rapido)
        synthetic = generate_synthetic_candles(n_days=30, bars_per_day=40, seed=21)
        return synthetic, "SINTETICO (offline)", False


def main() -> None:
    symbol = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_SYMBOL
    interval = sys.argv[2] if len(sys.argv) > 2 else DEFAULT_INTERVAL
    period = sys.argv[3] if len(sys.argv) > 3 else DEFAULT_PERIOD

    settings = Settings.default()
    settings.risk.starting_equity = 5_000.0

    print(f"Carregando dados de {symbol} ({interval}, {period})...")
    candles, fonte_desc, eh_real = load_market_data(symbol, interval, period)
    print(f"  {len(candles)} candles carregados. Fonte: {fonte_desc}\n")

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

    # Reproduz os candles carregados como se chegassem ao vivo. Para operar
    # continuamente em tempo real (precos novos chegando), troque por:
    #   cfg = DataSourceConfig(provider="yfinance", symbol=symbol,
    #                          yf_interval=interval, yf_period=period)
    #   feed = build_feed(cfg)        # cripto ao vivo: provider="ccxt"
    cfg = DataSourceConfig(provider="replay")
    feed = build_feed(cfg, candles=candles)
    print(f"\nFonte de dados: {fonte_desc}")

    trader = LiveTrader(brain, settings, warmup=brain.warmup)

    def show(u):
        if u.event and ("entrada" in u.event or "saida" in u.event):
            ts = datetime.fromtimestamp(u.ts, tz=timezone.utc)
            print(f"  {ts:%d/%m %H:%M} | R$ {u.price:9,.2f} | equity R$ {u.equity:8,.0f} | {u.event}")

    print("\nCerebro operando (paper trading):")
    updates = run_live(trader, feed.stream(), on_update=show)
    if not any(u.event and "entrada" in (u.event or "") for u in updates):
        print("  (o cerebro nao abriu nenhuma operacao -- sem consenso/vantagem)")

    print(f"\nEquity final: R$ {trader.risk.equity:,.2f}  ({len(trader.trades)} trades)")
    print("\n" + equity_curve_ascii(trader.equity_curve))


if __name__ == "__main__":
    main()
