"""Teste de estresse dos campeoes do SWING DIARIO (custos 1x/2x/3x).

    cd trading-bot
    python3 examples/stress_swing.py

A analise completa mostrou que o swing diario (1d) e onde aparece vantagem.
Aqui submetemos cada campeao a custos crescentes -- se a vantagem some quando a
corretora/spread piora, era ilusao. So o que aguentar merece o ensaio ao vivo.
"""

from __future__ import annotations

import os
import sys
from dataclasses import replace

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bot import EmaRsiAtrStrategy, Settings  # noqa: E402
from bot.strategies import BreakoutStrategy, MacdStrategy, RocStrategy  # noqa: E402
from bot.validation import StrategySpec, walk_forward  # noqa: E402

# campeoes do 1d-swing (da analyze_full.py): (rotulo, ativo, fabrica, grade)
def _ema_rsi_factory(settings):
    return lambda p: EmaRsiAtrStrategy(replace(settings.strategy, **p))


CANDIDATES = [
    ("PETR4.SA MACD", "PETR4.SA", "macd", MacdStrategy, {"fast": [8, 12], "slow": [21, 26]}),
    ("WEGE3.SA EMA+RSI", "WEGE3.SA", "ema_rsi", None, {"ema_fast": [5, 9], "ema_slow": [21, 30]}),
    ("ITUB4.SA ROC", "ITUB4.SA", "roc", RocStrategy, {"roc_period": [9, 12], "threshold": [0.0, 0.5]}),
    ("BBAS3.SA EMA+RSI", "BBAS3.SA", "ema_rsi", None, {"ema_fast": [5, 9], "ema_slow": [21, 30]}),
    ("ABEV3.SA Breakout", "ABEV3.SA", "breakout", BreakoutStrategy, {"channel": [10, 20, 40]}),
]
COST_MULTS = [1, 2, 3]


def make_settings(mult: int) -> Settings:
    s = Settings.default()
    s.risk.starting_equity = 5_000.0
    s.day_trade = False  # SWING
    s.costs.commission_pct *= mult
    s.costs.slippage_pct *= mult
    return s


def main() -> None:
    try:
        from bot.sources.yfinance_source import load_yfinance
    except ImportError:
        print("yfinance nao instalado. Rode:  pip install yfinance")
        sys.exit(1)

    print("Teste de estresse -- swing diario (1d), custos 1x/2x/3x.\n")
    verdicts = []
    for label, symbol, kind, cls, grid in CANDIDATES:
        try:
            candles = load_yfinance(symbol, period="5y", interval="1d")
        except Exception as exc:
            print(f"{label}: erro ao baixar ({str(exc)[:50]})")
            continue

        cells, passed = [], 0
        for mult in COST_MULTS:
            s = make_settings(mult)
            factory = _ema_rsi_factory(s) if kind == "ema_rsi" else cls
            spec = StrategySpec(label, factory, grid)
            folds = walk_forward(candles, s, spec.grid, n_folds=4, make_strategy=spec.make)
            if folds:
                oos = [f.out_of_sample.get("expectancy", 0.0) for f in folds]
                avg = sum(oos) / len(oos)
                pos = sum(1 for e in oos if e > 0)
            else:
                avg, pos, folds = 0.0, 0, []
            robust = len(folds) > 0 and pos > 0.5 * len(folds) and avg > 0
            passed += 1 if robust else 0
            cells.append(f"{pos}/{len(folds)} R${avg:7.2f} {'OK' if robust else '--'}")
        print(f"  {label:<20} | 1x {cells[0]:>16} | 2x {cells[1]:>16} | 3x {cells[2]:>16}  -> {passed}/3")
        verdicts.append((label, passed))

    print("\n" + "=" * 56)
    print("  VEREDITO (swing diario)")
    print("=" * 56)
    for label, passed in sorted(verdicts, key=lambda x: x[1], reverse=True):
        v = ">>> ROBUSTO" if passed == 3 else ("fragil" if passed >= 1 else "FALSO POSITIVO")
        print(f"  {label:<20} {passed}/3  {v}")
    print("=" * 56)


if __name__ == "__main__":
    main()
