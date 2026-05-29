"""Cerebro central -- combina TODAS as estrategias numa decisao so.

A ideia que voce pediu: em vez de apostar numa unica estrategia, rodamos varias
ao mesmo tempo e deixamos elas "votarem". O cerebro so abre operacao quando ha
CONSENSO suficiente. E o peso de cada voto vem da ANALISE (walk-forward): quem
nao provou vantagem fora-da-amostra recebe peso ZERO e nao influencia nada.

Por que isso aproxima do "sem risco" (sem nunca prometer isso):
  - se NENHUMA estrategia tem vantagem comprovada, todos os pesos sao 0 -> o
    cerebro fica PARADO (nao opera) -> nao arrisca capital atoa;
  - so age quando varias fontes independentes concordam E ja se mostraram
    robustas. Isso reduz o risco; nao o elimina (nada elimina).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .config import Settings
from .data import Candle
from .strategy import Signal, Strategy
from .validation import StrategySpec, train_test, walk_forward


@dataclass
class Member:
    """Uma estrategia no comite, com seu peso de voto."""

    name: str
    strategy: Strategy
    weight: float = 1.0


class EnsembleStrategy(Strategy):
    """Comite de estrategias. Decide por voto ponderado + limiar de consenso."""

    def __init__(self, members: list[Member], min_consensus: float = 0.5):
        self.members = members
        self.min_consensus = min_consensus
        self.warmup = max((m.strategy.warmup for m in members), default=0)
        self.last_confidence: float = 0.0

    def prepare(self, candles: list[Candle]) -> None:
        for m in self.members:
            m.strategy.prepare(candles)

    def signal(self, i: int) -> Signal:
        total = sum(m.weight for m in self.members)
        self.last_confidence = 0.0
        if total <= 0:
            return Signal(None)  # ninguem tem vantagem comprovada -> fica parado

        long_w = short_w = 0.0
        long_stops: list[float] = []
        long_takes: list[float] = []
        short_stops: list[float] = []
        short_takes: list[float] = []
        voters: list[str] = []
        for m in self.members:
            if m.weight <= 0:
                continue
            s = m.strategy.signal(i)
            if s.action == "long":
                long_w += m.weight
                long_stops.append(s.stop)
                long_takes.append(s.take)
                voters.append(m.name)
            elif s.action == "short":
                short_w += m.weight
                short_stops.append(s.stop)
                short_takes.append(s.take)
                voters.append(m.name)

        # consenso = fracao do peso total que concorda com a direcao vencedora
        if long_w > short_w and long_w / total >= self.min_consensus:
            self.last_confidence = long_w / total
            stop = sum(long_stops) / len(long_stops)
            take = sum(long_takes) / len(long_takes)
            return Signal("long", stop, take, f"consenso {self.last_confidence:.0%}: {'+'.join(voters)}")
        if short_w > long_w and short_w / total >= self.min_consensus:
            self.last_confidence = short_w / total
            stop = sum(short_stops) / len(short_stops)
            take = sum(short_takes) / len(short_takes)
            return Signal("short", stop, take, f"consenso {self.last_confidence:.0%}: {'+'.join(voters)}")
        return Signal(None)


@dataclass
class MemberDiagnostic:
    name: str
    weight: float
    folds_positive: int
    n_folds: int
    avg_oos_expectancy: float
    params: dict = field(default_factory=dict)
    robust: bool = False


def build_brain(
    candles: list[Candle],
    settings: Settings,
    specs: list[StrategySpec],
    n_folds: int = 4,
    min_consensus: float = 0.5,
    min_folds_fraction: float = 0.5,
) -> tuple[EnsembleStrategy, list[MemberDiagnostic]]:
    """Analisa cada estrategia (walk-forward) e monta o cerebro com pesos.

    Regra do peso: so recebe voto quem foi ROBUSTO -- maioria dos folds positiva
    E expectancia OOS media positiva. O peso e proporcional a quantos folds
    passaram. Quem nao passou recebe peso 0 (entra no comite, mas nao vota).

    Devolve (cerebro, diagnosticos) para voce ver exatamente quem ganhou voz.
    """
    members: list[Member] = []
    diags: list[MemberDiagnostic] = []
    for spec in specs:
        folds = walk_forward(
            candles, settings, spec.grid, n_folds, make_strategy=spec.make
        )
        oos = [f.out_of_sample.get("expectancy", 0.0) for f in folds]
        avg = sum(oos) / len(oos) if oos else 0.0
        positive = sum(1 for e in oos if e > 0)
        total_folds = len(folds) or n_folds

        split = train_test(candles, settings, spec.grid, make_strategy=spec.make)
        params = split.params if split else {}

        robust = avg > 0 and positive >= min_folds_fraction * total_folds
        weight = float(positive) if robust else 0.0

        members.append(Member(spec.name, spec.make(params), weight))
        diags.append(
            MemberDiagnostic(spec.name, weight, positive, total_folds, avg, params, robust)
        )

    brain = EnsembleStrategy(members, min_consensus)
    return brain, diags


def format_brain_report(diags: list[MemberDiagnostic], min_consensus: float) -> str:
    active = [d for d in diags if d.weight > 0]
    lines = [
        "=" * 68,
        "  CEREBRO CENTRAL -- quem ganhou direito de voto (e por que)",
        "=" * 68,
        f"  {'Estrategia':<22} {'voto':<6} {'folds+':<8} {'exp OOS':<10} robusta?",
        "-" * 68,
    ]
    for d in sorted(diags, key=lambda x: x.weight, reverse=True):
        lines.append(
            f"  {d.name:<22} {d.weight:<6.1f} {f'{d.folds_positive}/{d.n_folds}':<8} "
            f"R$ {d.avg_oos_expectancy:<7.2f} {'SIM' if d.robust else 'nao'}"
        )
    lines.append("=" * 68)
    if active:
        nomes = ", ".join(d.name for d in active)
        lines.append(f"  Comite ativo ({len(active)}): {nomes}.")
        lines.append(f"  Abre operacao so com consenso >= {min_consensus:.0%} do peso.")
    else:
        lines.append("  NENHUMA estrategia foi robusta -> o cerebro fica PARADO.")
        lines.append("  Isso e proposital: sem vantagem comprovada, nao se arrisca capital.")
    lines.append("=" * 68)
    return "\n".join(lines)
