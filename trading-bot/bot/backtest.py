"""Motor de backtest + metricas ajustadas ao risco.

Junta dados + estrategia + risco + corretora simulada e roda barra a barra,
SEM olhar para o futuro. No fim, reporta o que realmente importa: drawdown
maximo, Sharpe, fator de lucro e expectancia -- nao apenas "quanto rendeu".
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from .broker import PaperBroker, Trade
from .config import Settings
from .data import Candle
from .risk import RiskManager
from .strategy import Strategy


@dataclass
class BacktestResult:
    starting_equity: float
    final_equity: float
    trades: list[Trade]
    equity_curve: list[tuple[int, float]] = field(default_factory=list)
    daily_equity: list[float] = field(default_factory=list)
    halted: bool = False
    halt_reason: str = ""
    metrics: dict = field(default_factory=dict)


def run_backtest(
    candles: list[Candle], strategy: Strategy, settings: Settings
) -> BacktestResult:
    risk = RiskManager(settings.risk)
    risk.begin()
    broker = PaperBroker(settings.costs)
    strategy.prepare(candles)

    equity_curve: list[tuple[int, float]] = []
    daily_equity: list[float] = []
    trades: list[Trade] = []

    if not candles:
        return BacktestResult(risk.equity, risk.equity, trades)

    n = len(candles)
    prev_day = candles[0].day_index
    for i, c in enumerate(candles):
        if c.day_index != prev_day:
            risk.on_new_day()
            prev_day = c.day_index

        # 1) gerencia posicao aberta (stop / alvo dentro do candle)
        closed = broker.update(c)
        if closed is not None:
            risk.on_trade_closed(closed.pnl)
            trades.append(closed)

        # 2) day trade: zera a posicao no fim de cada dia. Em swing, segura.
        is_day_end = (i == n - 1) or (candles[i + 1].day_index != c.day_index)
        is_last = i == n - 1
        force_close = is_last or (settings.day_trade and is_day_end)
        if force_close and broker.has_position():
            reason = "eod" if (settings.day_trade and is_day_end and not is_last) else "end"
            closed = broker.close(c.close, c.ts, reason)
            risk.on_trade_closed(closed.pnl)
            trades.append(closed)

        # 3) novas entradas (respeitando as travas de risco). Em day trade nao
        #    abrimos no ultimo candle do dia (seria zerado em seguida).
        block_entry = is_last or (settings.day_trade and is_day_end)
        if not block_entry and not broker.has_position():
            ok, _reason = risk.can_trade()
            if ok:
                sig = strategy.signal(i)
                if sig.action in ("long", "short"):
                    qty = risk.position_size(c.close, sig.stop)
                    if qty > 0:
                        broker.open(sig.action, qty, c.close, sig.stop, sig.take)

        # 4) marca a curva de capital
        equity_curve.append((c.ts, risk.equity + broker.unrealized(c.close)))
        if is_day_end:
            daily_equity.append(risk.equity)

    metrics = compute_metrics(equity_curve, daily_equity, trades, settings)
    return BacktestResult(
        starting_equity=settings.risk.starting_equity,
        final_equity=risk.equity,
        trades=trades,
        equity_curve=equity_curve,
        daily_equity=daily_equity,
        halted=risk.halted,
        halt_reason=risk.halt_reason,
        metrics=metrics,
    )


def compute_metrics(
    equity_curve: list[tuple[int, float]],
    daily_equity: list[float],
    trades: list[Trade],
    settings: Settings,
) -> dict:
    start = settings.risk.starting_equity
    final = equity_curve[-1][1] if equity_curve else start
    total_return = (final - start) / start if start > 0 else 0.0

    # Drawdown maximo (sobre a curva marcada a mercado)
    peak = float("-inf")
    max_dd = 0.0
    for _, eq in equity_curve:
        peak = max(peak, eq)
        if peak > 0:
            max_dd = max(max_dd, (peak - eq) / peak)

    n = len(trades)
    wins = [t for t in trades if t.pnl > 0]
    losses = [t for t in trades if t.pnl <= 0]
    gross_profit = sum(t.pnl for t in wins)
    gross_loss = -sum(t.pnl for t in losses)
    win_rate = len(wins) / n if n else 0.0
    if gross_loss > 0:
        profit_factor = gross_profit / gross_loss
    else:
        profit_factor = float("inf") if gross_profit > 0 else 0.0
    avg_win = gross_profit / len(wins) if wins else 0.0
    avg_loss = gross_loss / len(losses) if losses else 0.0
    expectancy = (sum(t.pnl for t in trades) / n) if n else 0.0

    # Sharpe anualizado a partir dos retornos diarios
    rets = []
    for j in range(1, len(daily_equity)):
        prev = daily_equity[j - 1]
        if prev > 0:
            rets.append((daily_equity[j] - prev) / prev)
    sharpe = 0.0
    if len(rets) > 1:
        mean = sum(rets) / len(rets)
        var = sum((r - mean) ** 2 for r in rets) / (len(rets) - 1)
        std = math.sqrt(var)
        if std > 0:
            sharpe = mean / std * math.sqrt(252)

    return {
        "total_return": total_return,
        "max_drawdown": max_dd,
        "n_trades": n,
        "win_rate": win_rate,
        "profit_factor": profit_factor,
        "avg_win": avg_win,
        "avg_loss": avg_loss,
        "expectancy": expectancy,
        "sharpe": sharpe,
    }


def format_report(result: BacktestResult) -> str:
    m = result.metrics
    start = result.starting_equity
    final = result.final_equity
    lines = [
        "=" * 56,
        "  RELATORIO DE BACKTEST (paper trading / simulacao)",
        "=" * 56,
        f"  Capital inicial .........: R$ {start:,.2f}",
        f"  Capital final ...........: R$ {final:,.2f}",
        f"  Retorno total ...........: {m.get('total_return', 0):+.2%}",
        f"  Drawdown maximo .........: {m.get('max_drawdown', 0):.2%}",
        f"  Sharpe (anualizado) .....: {m.get('sharpe', 0):.2f}",
        "-" * 56,
        f"  Numero de trades ........: {m.get('n_trades', 0)}",
        f"  Taxa de acerto ..........: {m.get('win_rate', 0):.1%}",
        f"  Fator de lucro ..........: {m.get('profit_factor', 0):.2f}",
        f"  Ganho medio .............: R$ {m.get('avg_win', 0):,.2f}",
        f"  Perda media .............: R$ {m.get('avg_loss', 0):,.2f}",
        f"  Expectancia por trade ...: R$ {m.get('expectancy', 0):,.2f}",
        "=" * 56,
    ]
    if result.halted:
        lines.append(f"  !! ROBO DESLIGADO: {result.halt_reason}")
        lines.append("=" * 56)
    lines.append("  Custos (comissao + slippage) JA descontados em cada trade.")
    lines.append("  Resultado passado NAO garante resultado futuro.")
    return "\n".join(lines)
