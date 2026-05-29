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
from typing import Callable

from .backtest import BacktestResult, run_backtest
from .config import Settings
from .data import Candle
from .strategy import EmaRsiAtrStrategy, Strategy

# Uma "fabrica de estrategia": recebe um dict de parametros e devolve a
# estrategia ja configurada. Permite validar QUALQUER estrategia, nao so a EMA.
StrategyFactory = Callable[[dict], Strategy]


def _default_factory(settings: Settings) -> StrategyFactory:
    return lambda params: EmaRsiAtrStrategy(replace(settings.strategy, **params))


def evaluate_params(
    candles: list[Candle],
    settings: Settings,
    params: dict,
    make_strategy: StrategyFactory | None = None,
) -> tuple[dict, BacktestResult]:
    """Roda um backtest com os ``params`` aplicados via ``make_strategy``."""
    factory = make_strategy or _default_factory(settings)
    result = run_backtest(candles, factory(params), settings)
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
    make_strategy: StrategyFactory | None = None,
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
        metrics, _ = evaluate_params(candles, settings, params, make_strategy)
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
    make_strategy: StrategyFactory | None = None,
) -> SplitResult | None:
    """Otimiza no treino, mede no teste. A diferenca expoe o overfitting."""
    split = int(len(candles) * train_frac)
    train, test = candles[:split], candles[split:]
    best = grid_search(train, settings, grid, metric, min_trades, make_strategy)
    if best is None:
        return None
    oos_metrics, _ = evaluate_params(test, settings, best.params, make_strategy)
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
    make_strategy: StrategyFactory | None = None,
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
        best = grid_search(train, settings, grid, metric, min_trades, make_strategy)
        if best is None:
            continue
        oos_metrics, _ = evaluate_params(test, settings, best.params, make_strategy)
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


# ---------------------------------------------------------------------------
# Comparacao de varias estrategias pelo juiz imparcial (walk-forward)
# ---------------------------------------------------------------------------
@dataclass
class StrategySpec:
    """Uma estrategia candidata: como construi-la + seu espaco de busca."""

    name: str
    make: StrategyFactory
    grid: dict[str, list]


@dataclass
class ComparisonRow:
    name: str
    split: SplitResult | None
    folds: list[WalkForwardFold]
    avg_oos_expectancy: float
    folds_positive: int
    n_folds: int


def compare_strategies(
    candles: list[Candle],
    settings: Settings,
    specs: list[StrategySpec],
    n_folds: int = 4,
    train_frac: float = 0.7,
    metric: str = "expectancy",
    min_trades: int = 8,
) -> list[ComparisonRow]:
    """Roda treino/teste + walk-forward para cada estrategia e ranqueia.

    Criterio de ranque: robustez fora-da-amostra (mais folds positivos primeiro,
    depois maior expectancia OOS media). E o resultado honesto que importa.
    """
    rows: list[ComparisonRow] = []
    for spec in specs:
        split = train_test(
            candles, settings, spec.grid, train_frac, metric, min_trades, spec.make
        )
        folds = walk_forward(
            candles, settings, spec.grid, n_folds, metric, min_trades, spec.make
        )
        oos = [f.out_of_sample.get("expectancy", 0.0) for f in folds]
        avg = sum(oos) / len(oos) if oos else float("-inf")
        positive = sum(1 for e in oos if e > 0)
        rows.append(ComparisonRow(spec.name, split, folds, avg, positive, len(folds)))
    rows.sort(key=lambda r: (r.folds_positive, r.avg_oos_expectancy), reverse=True)
    return rows


def format_comparison(rows: list[ComparisonRow]) -> str:
    lines = [
        "=" * 70,
        "  COMPARACAO DE ESTRATEGIAS (ranqueadas por robustez fora-da-amostra)",
        "=" * 70,
        f"  {'#':<2} {'Estrategia':<22} {'folds+':<8} {'exp OOS media':<14}",
        "-" * 70,
    ]
    for i, r in enumerate(rows, 1):
        lines.append(
            f"  {i:<2} {r.name:<22} {f'{r.folds_positive}/{r.n_folds}':<8} "
            f"R$ {r.avg_oos_expectancy:+8.2f}"
        )
    lines.append("=" * 70)
    if rows and rows[0].folds_positive > rows[0].n_folds / 2:
        lines.append(
            f"  Candidata mais promissora: '{rows[0].name}'. "
            "Ainda assim, valide com paper trading antes de dinheiro real."
        )
    else:
        lines.append(
            "  Nenhuma estrategia passou no teste de robustez (maioria dos folds "
            "positiva). NAO opere com dinheiro real -- ainda nao ha vantagem."
        )
    lines.append("=" * 70)
    return "\n".join(lines)
