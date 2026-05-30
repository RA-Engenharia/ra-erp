"""Painel de acompanhamento do ensaio -- le o log de trades e resume.

Transforma o data/live_trades.csv (gerado pelo paper trading ao vivo) num
resumo honesto: acertos, fator de lucro, expectancia, drawdown e a curva de
capital. Serve para voce monitorar as SEMANAS de ensaio antes de pensar em
dinheiro real -- olhando numeros, nao torcida.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass

from .chart import equity_curve_ascii


@dataclass
class TradeRow:
    entry: float
    exit: float
    side: str
    qty: float
    pnl: float
    reason: str
    exit_ts: int


def load_trades_csv(path: str) -> list[TradeRow]:
    """Le o CSV de trades (colunas: entry,exit,side,qty,pnl,reason,exit_ts)."""
    rows: list[TradeRow] = []
    with open(path, newline="") as f:
        for r in csv.DictReader(f):
            rows.append(
                TradeRow(
                    entry=float(r["entry"]),
                    exit=float(r["exit"]),
                    side=r.get("side", ""),
                    qty=float(r.get("qty", 0) or 0),
                    pnl=float(r["pnl"]),
                    reason=r.get("reason", ""),
                    exit_ts=int(r.get("exit_ts", 0) or 0),
                )
            )
    return rows


def summarize(trades: list[TradeRow], starting_equity: float = 5_000.0) -> dict:
    """Calcula as metricas do ensaio + a curva de capital trade a trade."""
    n = len(trades)
    wins = [t for t in trades if t.pnl > 0]
    losses = [t for t in trades if t.pnl <= 0]
    gross_profit = sum(t.pnl for t in wins)
    gross_loss = -sum(t.pnl for t in losses)
    pnl = sum(t.pnl for t in trades)

    if gross_loss > 0:
        profit_factor = gross_profit / gross_loss
    else:
        profit_factor = float("inf") if gross_profit > 0 else 0.0

    # curva de capital e drawdown maximo (trade a trade)
    eq = starting_equity
    curve: list[tuple[int, float]] = [(0, eq)]
    peak = eq
    max_dd = 0.0
    for i, t in enumerate(sorted(trades, key=lambda x: x.exit_ts), start=1):
        eq += t.pnl
        curve.append((t.exit_ts or i, eq))
        peak = max(peak, eq)
        if peak > 0:
            max_dd = max(max_dd, (peak - eq) / peak)

    # quebra por motivo de saida
    reasons: dict[str, int] = {}
    for t in trades:
        reasons[t.reason] = reasons.get(t.reason, 0) + 1

    return {
        "n_trades": n,
        "win_rate": len(wins) / n if n else 0.0,
        "gross_profit": gross_profit,
        "gross_loss": gross_loss,
        "profit_factor": profit_factor,
        "expectancy": pnl / n if n else 0.0,
        "total_pnl": pnl,
        "final_equity": starting_equity + pnl,
        "max_drawdown": max_dd,
        "reasons": reasons,
        "curve": curve,
    }


def format_dashboard(summary: dict, starting_equity: float = 5_000.0) -> str:
    m = summary
    pf = m["profit_factor"]
    pf_str = "inf" if pf == float("inf") else f"{pf:.2f}"
    lines = [
        "=" * 56,
        "  PAINEL DO ENSAIO (paper trading -- ordens simuladas)",
        "=" * 56,
        f"  Trades ..................: {m['n_trades']}",
        f"  Taxa de acerto ..........: {m['win_rate']:.1%}",
        f"  Fator de lucro ..........: {pf_str}",
        f"  Expectancia por trade ...: R$ {m['expectancy']:,.2f}",
        f"  Resultado acumulado .....: R$ {m['total_pnl']:+,.2f}",
        f"  Capital atual ...........: R$ {m['final_equity']:,.2f}",
        f"  Drawdown maximo .........: {m['max_drawdown']:.1%}",
        "-" * 56,
    ]
    if m["reasons"]:
        quebra = " | ".join(f"{k or '?'}: {v}" for k, v in sorted(m["reasons"].items()))
        lines.append(f"  Saidas por motivo: {quebra}")
        lines.append("-" * 56)

    # veredito honesto do ensaio
    if m["n_trades"] < 20:
        lines.append("  AMOSTRA PEQUENA: poucos trades para concluir nada ainda.")
        lines.append("  Deixe o ensaio rodar mais pregoes antes de avaliar.")
    elif m["total_pnl"] > 0 and pf >= 1.3:
        lines.append("  Ensaio POSITIVO ate aqui. Continue acompanhando -- consistencia")
        lines.append("  por semanas e o que conta, nao um pico de sorte.")
    else:
        lines.append("  Ensaio NAO positivo. Sem vantagem ao vivo -> nao va para dinheiro")
        lines.append("  real. Isto e o sistema te protegendo.")
    lines.append("=" * 56)
    lines.append(equity_curve_ascii(m["curve"]))
    return "\n".join(lines)
