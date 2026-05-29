"""Estrategia de entrada/saida -- trocavel.

IMPORTANTE: a estrategia NAO eh o que faz ganhar dinheiro sozinha. Ela so
gera sinais. Quem protege o capital eh o risk.py. A estrategia padrao aqui
(cruzamento de EMAs filtrado por RSI, com stop por ATR) eh um ponto de
partida classico -- a ser validada e melhorada no backtest, nunca usada as
cegas com dinheiro real.

Para criar sua propria estrategia, herde de ``Strategy`` e implemente
``prepare`` e ``signal``.
"""

from __future__ import annotations

from dataclasses import dataclass

from . import indicators
from .config import StrategyConfig
from .data import Candle


@dataclass
class Signal:
    action: str | None  # "long", "short" ou None
    stop: float = 0.0
    take: float = 0.0
    reason: str = ""


class Strategy:
    """Interface base. ``prepare`` roda 1x; ``signal`` roda a cada candle."""

    warmup: int = 0

    def prepare(self, candles: list[Candle]) -> None:  # pragma: no cover
        raise NotImplementedError

    def signal(self, i: int) -> Signal:  # pragma: no cover
        raise NotImplementedError


class EmaRsiAtrStrategy(Strategy):
    def __init__(self, cfg: StrategyConfig):
        self.cfg = cfg
        self.warmup = max(cfg.ema_slow, cfg.rsi_period, cfg.atr_period) + 2
        self._closes: list[float] = []
        self._ema_f: list[float | None] = []
        self._ema_s: list[float | None] = []
        self._rsi: list[float | None] = []
        self._atr: list[float | None] = []

    def prepare(self, candles: list[Candle]) -> None:
        self._closes = [c.close for c in candles]
        highs = [c.high for c in candles]
        lows = [c.low for c in candles]
        self._ema_f = indicators.ema(self._closes, self.cfg.ema_fast)
        self._ema_s = indicators.ema(self._closes, self.cfg.ema_slow)
        self._rsi = indicators.rsi(self._closes, self.cfg.rsi_period)
        self._atr = indicators.atr(highs, lows, self._closes, self.cfg.atr_period)

    def signal(self, i: int) -> Signal:
        if i < self.warmup:
            return Signal(None)
        ef, es = self._ema_f[i], self._ema_s[i]
        ef_p, es_p = self._ema_f[i - 1], self._ema_s[i - 1]
        rsi_v, atr_v = self._rsi[i], self._atr[i]
        if None in (ef, es, ef_p, es_p, rsi_v, atr_v):
            return Signal(None)

        price = self._closes[i]
        cross_up = ef_p <= es_p and ef > es
        cross_dn = ef_p >= es_p and ef < es
        stop_dist = atr_v * self.cfg.stop_atr_mult  # risk.py manda no tamanho

        if cross_up and self.cfg.rsi_long_min <= rsi_v <= self.cfg.rsi_long_max:
            stop = price - stop_dist
            take = price + stop_dist * self.cfg.reward_risk
            return Signal("long", stop, take, f"cross_up rsi={rsi_v:.0f}")

        if (
            self.cfg.allow_short
            and cross_dn
            and self.cfg.rsi_short_min <= rsi_v <= self.cfg.rsi_short_max
        ):
            stop = price + stop_dist
            take = price - stop_dist * self.cfg.reward_risk
            return Signal("short", stop, take, f"cross_dn rsi={rsi_v:.0f}")

        return Signal(None)
