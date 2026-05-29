"""Validacao de estrategia -- a defesa contra o auto-engano (overfitting).

O erro nº1 de quem cria robo: otimizar parametros nos dados historicos ate o
resultado ficar lindo, e achar que vai funcionar ao vivo. Quase sempre nao
funciona -- voce ajustou a estrategia ao RUIDO do passado.

A defesa profissional:
  1) train/test split  -> otimiza no "treino", confere no "teste" (dados que a
     otimizacao NUNCA viu). Se cai muito no teste, era overfitting.
  2) walk-forward       -> repete isso em varias janelas no tempo, simulando
     como voce reotimizaria periodicamente na vida real.

Tudo roda sobre uma lista de Candle, entao funciona offline (dados sinteticos)
ou com dados reais (yfinance/CSV).
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from itertools import product

from .backtest import BacktestResult, run_backtest
from .config import Settings
from .data import Candle
from .strategy import EmaRsiAtrStrategy


def evaluate_params(
    candles: list[Candle], settings: Settings, params: dict
) -> tuple[dict, BacktestResult]:
    """Roda um backtest com a StrategyConfig sobrescrita por ``params``."""
    scfg = replace(settings.strategy, **params)
    result = run_backtest(candles, EmaRsiAtrStrategy(scfg), settings)
    return result.metrics, result


@dataclass
class GridResult:
    params: dict
    score: float
    metrics: dict


def grid_search(
    candles: list[Candle],
    settings: Settings,
    grid: dict[str, list],
    metric: str = "expectancy",
    min_trades: int = 10,
) -> GridResult | None:
    """Busca em grade os melhores parametros SEGUNDO ``metric`` (in-sample).

    Ignora combinacoes invalidas (ema_fast >= ema_slow) e combinacoes com
    poucos trades (resultado nao confiavel).
    """
    keys = list(grid)
    best: GridResult | None = None
    for combo in product(*(grid[k] for k in keys)):
        params = dict(zip(keys, combo))
        if (
            "ema_fast" in params
            and "ema_slow" in params
            and params["ema_fast"] >= params["ema_slow"]
        ):
            continue
        metrics, _ = evaluate_params(candles, settings, params)
        if metrics.get("n_trades", 0) < min_trades:
            continue
        score = metrics.get(metric, float("-inf"))
        if best is None or score > best.score:
            best = GridResult(params, score, metrics)
    return best


@dataclass
class SplitResult:
    params: dict
    in_sample: dict
    out_of_sample: dict


def train_test(
    candles: list[Candle],
    settings: Settings,
    grid: dict[str, list],
    train_frac: float = 0.7,
    metric: str = "expectancy",
    min_trades: int = 10,
) -> SplitResult | None:
    """Otimiza no treino, mede no teste. A diferenca expoe o overfitting."""
    split = int(len(candles) * train_frac)
    train, test = candles[:split], candles[split:]
    best = grid_search(train, settings, grid, metric, min_trades)
    if best is None:
        return None
    oos_metrics, _ = evaluate_params(test, settings, best.params)
    return SplitResult(best.params, best.metrics, oos_metrics)


@dataclass
class WalkForwardFold:
    fold: int
    params: dict
    in_sample: dict
    out_of_sample: dict


def walk_forward(
    candles: list[Candle],
    settings: Settings,
    grid: dict[str, list],
    n_folds: int = 4,
    metric: str = "expectancy",
    min_trades: int = 8,
) -> list[WalkForwardFold]:
    """Walk-forward de janela expansiva.

    Divide a serie em (n_folds + 1) blocos. No fold k: treina nos blocos
    [0..k], testa no bloco seguinte (k+1). Coleta as metricas FORA-DA-AMOSTRA
    de cada teste -- o resultado mais honesto que existe.
    """
    n = len(candles)
    block = n // (n_folds + 1)
    if block < 30:
        return []
    folds: list[WalkForwardFold] = []
    for k in range(1, n_folds + 1):
        train = candles[: block * k]
        test = candles[block * k : block * (k + 1)]
        best = grid_search(train, settings, grid, metric, min_trades)
        if best is None:
            continue
        oos_metrics, _ = evaluate_params(test, settings, best.params)
        folds.append(WalkForwardFold(k, best.params, best.metrics, oos_metrics))
    return folds


def format_split_report(r: SplitResult) -> str:
    def line(label: str, m: dict) -> str:
        return (
            f"  {label:<14}: retorno {m.get('total_return', 0):+7.2%} | "
            f"DD {m.get('max_drawdown', 0):5.2%} | "
            f"PF {m.get('profit_factor', 0):4.2f} | "
            f"exp R$ {m.get('expectancy', 0):7.2f} | "
            f"trades {m.get('n_trades', 0)}"
        )

    gap = r.out_of_sample.get("expectancy", 0) - r.in_sample.get("expectancy", 0)
    verdict = (
        "SUSPEITO de overfitting (caiu muito no teste)"
        if r.out_of_sample.get("expectancy", 0) <= 0 < r.in_sample.get("expectancy", 0)
        else "consistente entre treino e teste"
        if r.out_of_sample.get("expectancy", 0) > 0
        else "sem vantagem (negativo dos dois lados)"
    )
    return "\n".join(
        [
            "=" * 64,
            "  VALIDACAO TREINO/TESTE (out-of-sample)",
            "=" * 64,
            f"  Melhores parametros (no treino): {r.params}",
            line("IN-SAMPLE", r.in_sample),
            line("OUT-OF-SAMPLE", r.out_of_sample),
            f"  Delta expectancia (teste - treino): R$ {gap:+.2f}",
            f"  Veredito: {verdict}",
            "=" * 64,
        ]
    )


def format_walk_forward_report(folds: list[WalkForwardFold]) -> str:
    if not folds:
        return "Walk-forward: dados insuficientes para as janelas pedidas."
    lines = ["=" * 64, "  WALK-FORWARD (cada teste e fora-da-amostra)", "=" * 64]
    oos_exps = []
    for f in folds:
        oos = f.out_of_sample
        oos_exps.append(oos.get("expectancy", 0))
        lines.append(
            f"  Fold {f.fold}: OOS retorno {oos.get('total_return', 0):+7.2%} | "
            f"PF {oos.get('profit_factor', 0):4.2f} | "
            f"exp R$ {oos.get('expectancy', 0):7.2f} | "
            f"trades {oos.get('n_trades', 0)} | params {f.params}"
        )
    avg = sum(oos_exps) / len(oos_exps)
    positivos = sum(1 for e in oos_exps if e > 0)
    lines.append("-" * 64)
    lines.append(
        f"  Expectancia OOS media: R$ {avg:+.2f} | "
        f"folds positivos: {positivos}/{len(folds)}"
    )
    lines.append(
        "  Regra de ouro: so leve adiante se a maioria dos folds for positiva."
    )
    lines.append("=" * 64)
    return "\n".join(lines)
