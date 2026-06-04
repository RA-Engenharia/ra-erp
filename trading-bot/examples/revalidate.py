"""Re-validacao HONESTA: swing diario, todas as estrategias, com o cerebro
corrigido E descontando aluguel (5%/ano) nos shorts.

    cd trading-bot
    python3 examples/revalidate.py

Depois de (1) corrigir o consenso do cerebro e (2) adicionar estrategias de
queda, re-rodamos a analise do zero -- agora com o custo de ALUGUEL que torna
os shorts realistas. So o que continuar robusto AQUI merece o ensaio ao vivo.
"""

from __future__ import annotations

import os
import sys
from dataclasses import replace

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bot import EmaRsiAtrStrategy, Settings  # noqa: E402
from bot.scanner import ScanResult, format_scan, scan_candles  # noqa: E402
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

ASSETS = ["PETR4.SA", "VALE3.SA", "ITUB4.SA", "BBAS3.SA", "WEGE3.SA", "ABEV3.SA", "BBDC4.SA", "B3SA3.SA"]
BORROW_ANNUAL = 0.05  # 5%/ano de aluguel descontado nos shorts (conservador)


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
    try:
        from bot.sources.yfinance_source import load_yfinance
    except ImportError:
        print("yfinance nao instalado. Rode:  pip install yfinance")
        sys.exit(1)

    print(f"Re-validacao swing diario | aluguel nos shorts: {BORROW_ANNUAL:.0%}/ano\n")
    results: list[ScanResult] = []
    for symbol in ASSETS:
        settings = Settings.default()
        settings.risk.starting_equity = 5_000.0
        settings.day_trade = False
        settings.costs.short_borrow_annual_pct = BORROW_ANNUAL
        specs = build_specs(settings)
        label = f"{symbol} 1d-swing"
        try:
            candles = load_yfinance(symbol, period="5y", interval="1d")
        except Exception as exc:
            results.append(ScanResult(label, 0, "-", 0, 0, 0.0, False, str(exc)[:40]))
            continue
        res = scan_candles(label, candles, settings, specs, n_folds=4)
        results.append(res)
        print(
            f"  ... {label:<20}: {res.best_strategy:<12} "
            f"{res.folds_positive}/{res.n_folds} R$ {res.avg_oos_expectancy:7.2f}"
            f"{'  >>> EDGE' if res.robust else ''}"
        )

    print("\n" + format_scan(results))


if __name__ == "__main__":
    main()
