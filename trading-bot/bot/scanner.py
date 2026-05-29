"""Scanner de vantagem -- varre varios ativos/timeframes em busca de edge real.

Para cada conjunto de candles, roda o walk-forward de TODAS as estrategias e
reporta a melhor: em quantas janelas fora-da-amostra ela foi positiva e qual a
expectancia media. Marca como "robusta" so quem passou no teste honesto.

A pergunta que isto responde: existe ALGUM ativo/timeframe onde alguma das
nossas estrategias mostra vantagem consistente? Se nao, a resposta tambem e
valiosa -- evita operar no escuro.
"""

from __future__ import annotations

from dataclasses import dataclass

from .config import Settings
from .data import Candle
from .validation import StrategySpec, walk_forward


@dataclass
class ScanResult:
    label: str
    n_candles: int
    best_strategy: str
    folds_positive: int
    n_folds: int
    avg_oos_expectancy: float
    robust: bool
    error: str = ""


def scan_candles(
    label: str,
    candles: list[Candle],
    settings: Settings,
    specs: list[StrategySpec],
    n_folds: int = 4,
    min_folds_fraction: float = 0.5,
) -> ScanResult:
    """Avalia todas as estrategias num conjunto e devolve a MELHOR."""
    best_name = "-"
    best_pos = -1
    best_avg = float("-inf")
    best_total = n_folds
    for spec in specs:
        folds = walk_forward(candles, settings, spec.grid, n_folds, make_strategy=spec.make)
        if not folds:
            continue
        oos = [f.out_of_sample.get("expectancy", 0.0) for f in folds]
        avg = sum(oos) / len(oos)
        positive = sum(1 for e in oos if e > 0)
        # melhor = mais folds positivos; desempate pela expectancia media
        if (positive, avg) > (best_pos, best_avg):
            best_pos, best_avg, best_name, best_total = positive, avg, spec.name, len(folds)

    # bar HONESTO: maioria ESTRITA das janelas positiva (2/4 = moeda jogada,
    # nao conta) E expectancia media positiva. Evita falso-positivo de scan.
    robust = best_pos > 0 and best_avg > 0 and best_pos > min_folds_fraction * best_total
    return ScanResult(
        label=label,
        n_candles=len(candles),
        best_strategy=best_name,
        folds_positive=max(best_pos, 0),
        n_folds=best_total,
        avg_oos_expectancy=best_avg if best_avg != float("-inf") else 0.0,
        robust=robust,
    )


def format_scan(results: list[ScanResult]) -> str:
    ordered = sorted(
        results,
        key=lambda r: (r.robust, r.folds_positive, r.avg_oos_expectancy),
        reverse=True,
    )
    lines = [
        "=" * 74,
        "  VARREDURA DE VANTAGEM (melhor estrategia por ativo/timeframe)",
        "=" * 74,
        f"  {'Ativo/TF':<20} {'melhor estrategia':<20} {'folds+':<8} {'exp OOS':<10} edge?",
        "-" * 74,
    ]
    for r in ordered:
        if r.error:
            lines.append(f"  {r.label:<20} (erro: {r.error})")
            continue
        lines.append(
            f"  {r.label:<20} {r.best_strategy:<20} {f'{r.folds_positive}/{r.n_folds}':<8} "
            f"R$ {r.avg_oos_expectancy:<7.2f} {'>>> SIM' if r.robust else 'nao'}"
        )
    lines.append("=" * 74)
    robustos = [r for r in ordered if r.robust]
    if robustos:
        nomes = ", ".join(f"{r.label}/{r.best_strategy}" for r in robustos)
        lines.append(f"  Candidatos com sinal de vantagem: {nomes}.")
        lines.append(
            f"  CUIDADO: varrer muitos combos ({len(ordered)}) faz surgir 'vantagem' por"
        )
        lines.append(
            "  PURO ACASO. Trate isto como hipotese, nao como certeza."
        )
        lines.append("  PROXIMO PASSO: paper trading ao vivo por semanas antes de dinheiro real.")
    else:
        lines.append("  Nenhum ativo/timeframe mostrou vantagem robusta com estas estrategias.")
        lines.append("  Isso e comum e HONESTO: edge real e raro. Nao opere sem ele.")
    lines.append("=" * 74)
    return "\n".join(lines)
