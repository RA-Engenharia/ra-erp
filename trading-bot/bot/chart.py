"""Grafico da curva de capital em ASCII -- ver o robo ganhar/perder sem libs.

Util para iniciante: numeros nao contam a historia que um grafico conta. Aqui
voce ENXERGA os drawdowns (quedas) e a inclinacao da curva. Python puro, roda
em qualquer terminal, sem matplotlib.
"""

from __future__ import annotations


def equity_curve_ascii(
    curve: list[tuple[int, float]], width: int = 64, height: int = 14
) -> str:
    """Desenha a evolucao do capital. ``curve`` = lista de (ts, equity)."""
    if len(curve) < 2:
        return "(curva de capital insuficiente para desenhar)"

    values = [eq for _, eq in curve]
    # reamostra para caber na largura
    step = max(1, len(values) / width)
    sampled = [values[min(len(values) - 1, int(i * step))] for i in range(width)]

    lo, hi = min(sampled), max(sampled)
    span = hi - lo or 1.0
    grid = [[" "] * width for _ in range(height)]
    for x, v in enumerate(sampled):
        y = int((v - lo) / span * (height - 1))
        grid[height - 1 - y][x] = "•"

    start, final = values[0], values[-1]
    pnl = final - start
    sign = "+" if pnl >= 0 else "-"
    rows = ["".join(r) for r in grid]
    out = [
        f"  capital  (max R$ {hi:,.0f})",
        "  " + "┌" + "─" * width + "┐",
    ]
    for r in rows:
        out.append("  │" + r + "│")
    out.append("  " + "└" + "─" * width + "┘")
    out.append(f"  inicio R$ {start:,.0f}  ->  fim R$ {final:,.0f}")
    out.append(f"  resultado: {sign}R$ {abs(pnl):,.2f}  ({pnl / start:+.2%})")
    return "\n".join(out)
