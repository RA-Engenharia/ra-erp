"""Paper trading "ao vivo" -- mesmo motor, alimentado candle a candle.

Diferenca para o backtest: aqui os candles chegam UM DE CADA VEZ, como na vida
real. A estrategia so enxerga o passado (recalculamos os indicadores apenas
sobre o que ja chegou), entao e impossivel trapacear olhando o futuro.

E o ensaio final antes do dinheiro real: troque o feed simulado por um feed de
verdade (corretora/API) e o ``broker`` simulado por um broker real -- o resto
do robo (estrategia + risco) nao muda uma linha.
"""

from __future__ import annotations

from collections.abc import Iterable, Iterator
from dataclasses import dataclass

from .broker import PaperBroker, Trade
from .config import Settings
from .data import Candle
from .strategy import Strategy


@dataclass
class LiveUpdate:
    """Foto da conta logo apos processar um candle."""

    ts: int
    price: float
    equity: float
    position: str | None  # "long" / "short" / None
    event: str | None  # o que acabou de acontecer (entrada, saida, bloqueio)
    halted: bool
    note: str = ""


class LiveTrader:
    """Mantem estado entre candles e decide a cada novo candle que chega.

    Uso:
        trader = LiveTrader(strategy, settings)
        for candle in feed:
            update = trader.on_candle(candle)
            print(update)
    """

    def __init__(self, strategy: Strategy, settings: Settings, warmup: int = 30):
        self.strategy = strategy
        self.settings = settings
        self.warmup = warmup
        from .risk import RiskManager  # import local evita ciclo

        self.risk = RiskManager(settings.risk)
        self.risk.begin()
        self.broker = PaperBroker(settings.costs)

        self._buf: list[Candle] = []
        self._day: int | None = None
        self._last_close: float = 0.0
        self._last_ts: int = 0
        self.trades: list[Trade] = []
        self.equity_curve: list[tuple[int, float]] = []

    def on_candle(self, c: Candle) -> LiveUpdate:
        events: list[str] = []

        # 1) virou o dia? em day trade, zera a posicao do dia anterior; em swing,
        #    segura. Em ambos, reseta as travas diarias de risco.
        if self._day is not None and c.day_index != self._day:
            if self.settings.day_trade and self.broker.has_position():
                closed = self.broker.close(self._last_close, self._last_ts, "eod")
                self.risk.on_trade_closed(closed.pnl)
                self.trades.append(closed)
                events.append("saida_eod")
            self.risk.on_new_day()
        self._day = c.day_index

        # 2) gerencia posicao aberta: stop/alvo dentro do candle
        closed = self.broker.update(c)
        if closed is not None:
            self.risk.on_trade_closed(closed.pnl)
            self.trades.append(closed)
            events.append(f"saida_{closed.reason}")

        # 3) decide nova entrada (so com dados ja vistos -> sem lookahead)
        self._buf.append(c)
        if len(self._buf) > self.warmup and not self.broker.has_position():
            ok, reason = self.risk.can_trade()
            if ok:
                self.strategy.prepare(self._buf)
                sig = self.strategy.signal(len(self._buf) - 1)
                if sig.action in ("long", "short"):
                    qty = self.risk.position_size(c.close, sig.stop)
                    if qty > 0:
                        self.broker.open(sig.action, qty, c.close, sig.stop, sig.take, c.ts)
                        events.append(f"entrada_{sig.action}")
            elif reason:
                events.append(f"bloqueado:{reason}")

        # 4) marca a curva de capital
        equity = self.risk.equity + self.broker.unrealized(c.close)
        self.equity_curve.append((c.ts, equity))
        self._last_close, self._last_ts = c.close, c.ts

        pos = self.broker.position.side if self.broker.has_position() else None
        return LiveUpdate(
            ts=c.ts,
            price=c.close,
            equity=equity,
            position=pos,
            event=";".join(events) or None,
            halted=self.risk.halted,
            note=self.risk.halt_reason,
        )


def candle_feed(candles: Iterable[Candle], delay: float = 0.0) -> Iterator[Candle]:
    """Feed simulado: entrega candles um a um, com atraso opcional (segundos).

    Troque esta funcao por uma que leia de uma API/websocket para ir ao vivo de
    verdade -- o LiveTrader nao precisa saber a origem dos candles.
    """
    import time

    for c in candles:
        if delay > 0:
            time.sleep(delay)
        yield c


def run_live(
    trader: LiveTrader,
    feed: Iterable[Candle],
    on_update=None,
) -> list[LiveUpdate]:
    """Roda o trader sobre um feed. ``on_update`` (opcional) recebe cada update."""
    updates: list[LiveUpdate] = []
    for c in feed:
        u = trader.on_candle(c)
        updates.append(u)
        if on_update is not None:
            on_update(u)
        if u.halted:
            break
    return updates
