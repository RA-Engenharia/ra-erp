"""Teste de estresse dos candidatos -- a vantagem sobrevive ao tranco?

    cd trading-bot
    python3 examples/stress_test.py

Para cada candidato (ativo + estrategia + filtro de regime), reavalia a
robustez fora-da-amostra variando DUAS coisas que matam falsas vantagens:

  1) CUSTOS: 1x, 2x e 3x a comissao+slippage padrao (simula corretora pior,
     spread maior, execucao ruim).
  2) LIMIAR do filtro de regime: 0.25, 0.30, 0.35 (a vantagem nao pode depender
     de um numero magico exato).

Sao 9 combinacoes por candidato. Uma hipotese DE VERDADE sobrevive na maioria.
Uma fragil desmorona ao primeiro empurrao -- e e melhor descobrir aqui, de
graca, do que com dinheiro real.
"""

from __future__ import annotations

import os
import sys
from dataclasses import replace

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bot import Settings  # noqa: E402
from bot.strategies import (  # noqa: E402
    BreakoutStrategy,
    MacdStrategy,
    RegimeFilteredStrategy,
    TrendEmaStrategy,
)
from bot.validation import StrategySpec, walk_forward  # noqa: E402

# Candidatos que passaram na varredura com filtro (scan_filtered.py).
# (rotulo, ativo, fabrica-base, grade, modo-de-regime)
CANDIDATES = [
    ("PETR4.SA EMA+tend", "PETR4.SA", TrendEmaStrategy, {"ema_fast": [5, 9], "trend_ema": [100, 200]}, "trend"),
    ("B3SA3.SA MACD", "B3SA3.SA", MacdStrategy, {"fast": [8, 12], "slow": [21, 26]}, "trend"),
    ("WEGE3.SA Breakout", "WEGE3.SA", BreakoutStrategy, {"channel": [10, 20, 40]}, "trend"),
    ("BBDC4.SA EMA+tend", "BBDC4.SA", TrendEmaStrategy, {"ema_fast": [5, 9], "trend_ema": [100, 200]}, "trend"),
]
THRESHOLDS = [0.25, 0.30, 0.35]
COST_MULTS = [1, 2, 3]


def scaled_settings(mult: int) -> Settings:
    s = Settings.default()
    s.risk.starting_equity = 5_000.0
    s.costs.commission_pct *= mult
    s.costs.slippage_pct *= mult
    return s


def survives(candles, settings, base_factory, grid, mode, threshold) -> tuple[int, int, float]:
    spec = StrategySpec(
        "x",
        lambda p: RegimeFilteredStrategy(base_factory(p), mode=mode, er_threshold=threshold),
        grid,
    )
    folds = walk_forward(candles, settings, spec.grid, n_folds=4, make_strategy=spec.make)
    if not folds:
        return 0, 0, 0.0
    oos = [f.out_of_sample.get("expectancy", 0.0) for f in folds]
    avg = sum(oos) / len(oos)
    pos = sum(1 for e in oos if e > 0)
    return pos, len(folds), avg


def main() -> None:
    try:
        from bot.sources.yfinance_source import load_yfinance
    except ImportError:
        print("yfinance nao instalado. Rode:  pip install yfinance")
        sys.exit(1)

    print("Teste de estresse: 9 combinacoes (3 custos x 3 limiares) por candidato.\n")
    overall = []
    for label, symbol, base, grid, mode in CANDIDATES:
        try:
            candles = load_yfinance(symbol, period="360d", interval="1h")
        except Exception as exc:
            print(f"{label}: erro ao baixar ({str(exc)[:50]})")
            continue

        print(f"=== {label} ===")
        print(f"  {'limiar':>8} |   custo1x      custo2x      custo3x")
        print("  " + "-" * 52)
        passed = 0
        for thr in THRESHOLDS:
            cells = []
            for mult in COST_MULTS:
                s = scaled_settings(mult)
                pos, n, avg = survives(candles, s, base, grid, mode, thr)
                robust = n > 0 and pos > 0.5 * n and avg > 0
                passed += 1 if robust else 0
                mark = "OK" if robust else "--"
                cells.append(f"{pos}/{n} R${avg:6.2f} {mark}")
            print(f"  {thr:>8.2f} | {cells[0]:>12} {cells[1]:>12} {cells[2]:>12}")
        print(f"  -> sobreviveu em {passed}/9 combinacoes\n")
        overall.append((label, passed))

    print("=" * 56)
    print("  VEREDITO DO TESTE DE ESTRESSE")
    print("=" * 56)
    for label, passed in sorted(overall, key=lambda x: x[1], reverse=True):
        if passed >= 6:
            verdict = ">>> ROBUSTO (sobrevive ao tranco)"
        elif passed >= 3:
            verdict = "fragil (depende das condicoes)"
        else:
            verdict = "FALSO POSITIVO (desmorona)"
        print(f"  {label:<22} {passed}/9  {verdict}")
    print("=" * 56)
    print("  So leve adiante o que ficou ROBUSTO. O resto era ilusao do backtest.")
    print("=" * 56)


if __name__ == "__main__":
    main()
