"""Corretora simulada (paper trading) com custos e slippage REAIS.

Modelo tipo futuros/CFD: o capital eh controlado pelo RiskManager; aqui so
controlamos a posicao aberta e calculamos o PnL liquido (descontando comissao
e slippage) quando a posicao fecha. Stop e alvo sao checados dentro do candle.

A mesma interface (open/update/close) pode ser implementada por um broker REAL
(Binance via ccxt, MetaTrader5 etc.) sem mudar o resto do robo.
"""

from __future__ import annotations

from dataclasses import dataclass

from .config import CostConfig
from .data import Candle


@dataclass
class Position:
    side: str  # "long" ou "short"
    qty: float
    entry: float
    stop: float
    take: float
    commission_open: float
    entry_ts: int = 0

    @property
    def direction(self) -> int:
        return 1 if self.side == "long" else -1


@dataclass
class Trade:
    side: str
    qty: float
    entry: float
    exit: float
    pnl: float
    reason: str  # "stop", "take", "eod"
    entry_ts: int
    exit_ts: int


class PaperBroker:
    def __init__(self, costs: CostConfig):
        self.costs = costs
        self.position: Position | None = None

    def has_position(self) -> bool:
        return self.position is not None

    # --- custos ----------------------------------------------------------
    def _fill_price(self, price: float, side: str, opening: bool) -> float:
        """Aplica slippage: sempre executa num preco PIOR para nos."""
        slip = self.costs.slippage_pct
        # comprar (abrir long / fechar short) -> paga mais caro
        buying = (side == "long") == opening
        return price * (1 + slip) if buying else price * (1 - slip)

    def _commission(self, notional: float) -> float:
        return abs(notional) * self.costs.commission_pct

    # --- ordens ----------------------------------------------------------
    def open(
        self, side: str, qty: float, price: float, stop: float, take: float, ts: int = 0
    ) -> None:
        assert self.position is None, "ja existe posicao aberta"
        assert side in ("long", "short")
        fill = self._fill_price(price, side, opening=True)
        comm = self._commission(fill * qty)
        self.position = Position(side, qty, fill, stop, take, comm, ts)

    def _borrow_cost(self, pos: Position, ts: int) -> float:
        """Custo de aluguel para shorts, proporcional aos dias segurados."""
        rate = self.costs.short_borrow_annual_pct
        if pos.side != "short" or rate <= 0 or pos.entry_ts <= 0:
            return 0.0
        days = max(0.0, (ts - pos.entry_ts) / 86_400.0)
        return pos.entry * pos.qty * rate * days / 365.0

    def _close_at(self, price: float, reason: str, ts: int) -> Trade:
        pos = self.position
        assert pos is not None
        fill = self._fill_price(price, pos.side, opening=False)
        comm_close = self._commission(fill * pos.qty)
        gross = (fill - pos.entry) * pos.qty * pos.direction
        pnl = gross - pos.commission_open - comm_close - self._borrow_cost(pos, ts)
        trade = Trade(
            side=pos.side,
            qty=pos.qty,
            entry=pos.entry,
            exit=fill,
            pnl=pnl,
            reason=reason,
            entry_ts=pos.entry_ts,
            exit_ts=ts,
        )
        self.position = None
        return trade

    def update(self, candle: Candle) -> Trade | None:
        """Checa se stop ou alvo foram tocados dentro do candle.

        Conservador: se ambos puderem ter sido tocados no mesmo candle,
        assume que o STOP veio primeiro (pior caso).
        """
        pos = self.position
        if pos is None:
            return None
        if pos.side == "long":
            if candle.low <= pos.stop:
                return self._close_at(pos.stop, "stop", candle.ts)
            if candle.high >= pos.take:
                return self._close_at(pos.take, "take", candle.ts)
        else:  # short
            if candle.high >= pos.stop:
                return self._close_at(pos.stop, "stop", candle.ts)
            if candle.low <= pos.take:
                return self._close_at(pos.take, "take", candle.ts)
        return None

    def close(self, price: float, ts: int, reason: str = "eod") -> Trade:
        return self._close_at(price, reason, ts)

    def unrealized(self, price: float) -> float:
        """PnL nao realizado para marcar a curva de capital."""
        pos = self.position
        if pos is None:
            return 0.0
        gross = (price - pos.entry) * pos.qty * pos.direction
        return gross - pos.commission_open
