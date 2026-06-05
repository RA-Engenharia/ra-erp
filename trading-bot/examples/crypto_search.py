"""Busca de edge em CRIPTO -- e o teste mais duro: bater buy&hold E o CDI.

    cd trading-bot
    python3 examples/crypto_search.py

Cripto tende a ter tendencias mais fortes que acoes -- terreno mais provavel
para momentum. Mas o juiz aqui e implacavel: a estrategia so vale se superar
(1) simplesmente COMPRAR E SEGURAR o ativo e (2) o CDI (~11%/ano, sem risco).
Muita estrategia "lucrativa" perde feio para o proprio buy&hold.

Dados via yfinance (BTC-USD etc.), sem API key. Swing diario.
"""

from __future__ import annotations

import os
import sys
from dataclasses import replace

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bot import EmaRsiAtrStrategy, Settings  # noqa: E402
from bot.backtest import run_backtest  # noqa: E402
from bot.brain import build_brain  # noqa: E402
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

CRYPTOS = ["BTC-USD", "ETH-USD", "BNB-USD", "SOL-USD", "XRP-USD"]
CDI_ANUAL = 0.11  # referencia Brasil (sem risco)


def build_specs(settings: Settings) -> list[StrategySpec]:
    ema_rsi = lambda p: EmaRsiAtrStrategy(replace(settings.strategy, **p))
    return [
        StrategySpec("EMA+RSI", ema_rsi, {"ema_fast": [5, 9], "ema_slow": [21, 30]}),
        StrategySpec("Breakout", BreakoutStrategy, {"channel": [10, 20, 40]}),
        StrategySpec("EMA+tend", TrendEmaStrategy, {"ema_fast": [5, 9], "trend_ema": [100, 200]}),
        StrategySpec("MACD", MacdStrategy, {"fast": [8, 12], "slow": [21, 26]}),
        StrategySpec("SuperTrend", SuperTrendStrategy, {"period": [7, 10], "mult": [2.0, 3.0]}),
        StrategySpec("ROC", RocStrategy, {"roc_period": [9, 12], "threshold": [0.0, 0.5]}),
        StrategySpec("Bollinger", BollingerStrategy, {"period": [14, 20], "k": [2.0, 2.5]}),
        StrategySpec("Reversao", MeanReversionStrategy, {"oversold": [20, 30]}),
        StrategySpec("RSI-2", Rsi2Strategy, {"oversold": [5, 10], "trend_sma": [100, 200]}),
        StrategySpec("Breakdown", BreakdownStrategy, {"channel": [10, 20, 40]}),
        StrategySpec("Downtrend", DowntrendStrategy, {"ema_fast": [5, 9], "trend_ema": [100, 200]}),
    ]


def annualize(total_return: float, years: float) -> float:
    if years <= 0:
        return 0.0
    return (1.0 + total_return) ** (1.0 / years) - 1.0


def main() -> None:
    try:
        from bot.sources.yfinance_source import load_yfinance
    except ImportError:
        print("yfinance nao instalado. Rode:  pip install yfinance")
        sys.exit(1)

    print("=" * 74)
    print("  BUSCA DE EDGE EM CRIPTO -- estrategia vs comprar-e-segurar vs CDI")
    print("=" * 74)
    print(f"  {'Ativo':<10} {'estrategia':>10} {'/ano':>8} | {'buy&hold/ano':>12} | {'CDI':>6} | veredito")
    print("  " + "-" * 70)

    for sym in CRYPTOS:
        settings = Settings.default()
        settings.risk.starting_equity = 5_000.0
        settings.day_trade = False
        settings.costs.commission_pct = 0.001   # ~0.1% taker em cripto
        settings.costs.slippage_pct = 0.0005
        try:
            candles = load_yfinance(sym, period="5y", interval="1d")
        except Exception as exc:
            print(f"  {sym:<10} erro: {str(exc)[:40]}")
            continue
        if len(candles) < 300:
            print(f"  {sym:<10} poucos dados ({len(candles)})")
            continue

        years = (candles[-1].ts - candles[0].ts) / (365.25 * 86_400)
        brain, _ = build_brain(candles, settings, build_specs(settings), n_folds=4)
        result = run_backtest(candles, brain, settings)
        strat_ann = annualize(result.metrics["total_return"], years)

        bh_total = candles[-1].close / candles[0].close - 1.0
        bh_ann = annualize(bh_total, years)

        bate_bh = strat_ann > bh_ann
        bate_cdi = strat_ann > CDI_ANUAL
        if bate_bh and bate_cdi:
            vereditos = ">>> bate AMBOS"
        elif bate_cdi:
            vereditos = "bate CDI, perde p/ buy&hold"
        elif bate_bh:
            vereditos = "bate buy&hold, perde p/ CDI"
        else:
            vereditos = "perde p/ ambos"
        print(f"  {sym:<10} {strat_ann:>9.1%} {'':>8} | {bh_ann:>11.1%} | {CDI_ANUAL:>5.0%} | {vereditos}")

    print("  " + "-" * 70)
    print("  Regra dura: so vale a pena se BATER buy&hold E CDI. Senao, e melhor")
    print("  (e mais facil) so comprar e segurar, ou deixar no Tesouro.")
    print("=" * 74)


if __name__ == "__main__":
    main()
