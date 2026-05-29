"""Estrategias candidatas para a comparacao (Fase 3).

Cada uma aceita um dict de parametros (com defaults), entao serve direto como
"fabrica" para o motor de validacao: ``BreakoutStrategy(params)``.

Nenhuma delas e "a resposta". Sao hipoteses -- o walk-forward decide qual (se
alguma) tem vantagem real. Todas usam stop por ATR e respeitam o risk.py.
"""

from __future__ import annotations

from . import indicators
from .data import Candle
from .strategy import Signal, Strategy


def _ohlc(candles: list[Candle]) -> tuple[list[float], list[float], list[float]]:
    return (
        [c.close for c in candles],
        [c.high for c in candles],
        [c.low for c in candles],
    )


class BreakoutStrategy(Strategy):
    """Rompimento de canal (Donchian): compra novas maximas, vende novas minimas.

    Logica de SEGUIR tendencia/momentum. Canal calculado APENAS com barras
    anteriores (sem olhar o candle atual) para nao trapacear.
    """

    def __init__(self, params: dict | None = None):
        p = params or {}
        self.channel = int(p.get("channel", 20))
        self.atr_period = int(p.get("atr_period", 14))
        self.stop_atr_mult = float(p.get("stop_atr_mult", 1.5))
        self.reward_risk = float(p.get("reward_risk", 1.5))
        self.allow_short = bool(p.get("allow_short", True))
        self.warmup = max(self.channel, self.atr_period) + 2

    def prepare(self, candles: list[Candle]) -> None:
        self._closes, highs, lows = _ohlc(candles)
        self._atr = indicators.atr(highs, lows, self._closes, self.atr_period)
        n = len(candles)
        self._hh: list[float | None] = [None] * n
        self._ll: list[float | None] = [None] * n
        for i in range(self.channel, n):
            self._hh[i] = max(highs[i - self.channel : i])
            self._ll[i] = min(lows[i - self.channel : i])

    def signal(self, i: int) -> Signal:
        if i < self.warmup:
            return Signal(None)
        atr_v, hh, ll = self._atr[i], self._hh[i], self._ll[i]
        if None in (atr_v, hh, ll):
            return Signal(None)
        price = self._closes[i]
        dist = atr_v * self.stop_atr_mult
        if price > hh:
            return Signal("long", price - dist, price + dist * self.reward_risk, "brk_up")
        if self.allow_short and price < ll:
            return Signal("short", price + dist, price - dist * self.reward_risk, "brk_dn")
        return Signal(None)


class MeanReversionStrategy(Strategy):
    """Reversao a media via RSI: compra muito sobrevendido, vende sobrecomprado.

    Aposta CONTRARIA: que extremos voltam. Funciona em mercados laterais e
    costuma sofrer em tendencias fortes -- o oposto do breakout.
    """

    def __init__(self, params: dict | None = None):
        p = params or {}
        self.rsi_period = int(p.get("rsi_period", 14))
        self.oversold = float(p.get("oversold", 30.0))
        self.overbought = float(p.get("overbought", 70.0))
        self.atr_period = int(p.get("atr_period", 14))
        self.stop_atr_mult = float(p.get("stop_atr_mult", 1.5))
        self.reward_risk = float(p.get("reward_risk", 1.0))
        self.allow_short = bool(p.get("allow_short", True))
        self.warmup = max(self.rsi_period, self.atr_period) + 2

    def prepare(self, candles: list[Candle]) -> None:
        self._closes, highs, lows = _ohlc(candles)
        self._rsi = indicators.rsi(self._closes, self.rsi_period)
        self._atr = indicators.atr(highs, lows, self._closes, self.atr_period)

    def signal(self, i: int) -> Signal:
        if i < self.warmup:
            return Signal(None)
        rsi_v, atr_v = self._rsi[i], self._atr[i]
        if None in (rsi_v, atr_v):
            return Signal(None)
        price = self._closes[i]
        dist = atr_v * self.stop_atr_mult
        if rsi_v < self.oversold:
            return Signal("long", price - dist, price + dist * self.reward_risk, "mr_long")
        if self.allow_short and rsi_v > self.overbought:
            return Signal("short", price + dist, price - dist * self.reward_risk, "mr_short")
        return Signal(None)


class MacdStrategy(Strategy):
    """Cruzamento do MACD: compra quando a linha cruza o sinal para cima.

    Captura momentum. O histograma trocando de sinal marca o cruzamento --
    olhamos a barra atual vs a anterior para detectar a virada (sem lookahead).
    """

    def __init__(self, params: dict | None = None):
        p = params or {}
        self.fast = int(p.get("fast", 12))
        self.slow = int(p.get("slow", 26))
        self.signal_period = int(p.get("signal", 9))
        self.atr_period = int(p.get("atr_period", 14))
        self.stop_atr_mult = float(p.get("stop_atr_mult", 1.5))
        self.reward_risk = float(p.get("reward_risk", 1.5))
        self.allow_short = bool(p.get("allow_short", True))
        self.warmup = self.slow + self.signal_period + 2

    def prepare(self, candles: list[Candle]) -> None:
        self._closes, highs, lows = _ohlc(candles)
        _, _, self._hist = indicators.macd(self._closes, self.fast, self.slow, self.signal_period)
        self._atr = indicators.atr(highs, lows, self._closes, self.atr_period)

    def signal(self, i: int) -> Signal:
        if i < self.warmup:
            return Signal(None)
        h, hp, atr_v = self._hist[i], self._hist[i - 1], self._atr[i]
        if None in (h, hp, atr_v):
            return Signal(None)
        price = self._closes[i]
        dist = atr_v * self.stop_atr_mult
        if hp <= 0 < h:  # histograma cruzou para cima
            return Signal("long", price - dist, price + dist * self.reward_risk, "macd_up")
        if self.allow_short and hp >= 0 > h:  # cruzou para baixo
            return Signal("short", price + dist, price - dist * self.reward_risk, "macd_dn")
        return Signal(None)


class BollingerStrategy(Strategy):
    """Reversao por Bollinger: compra abaixo da banda inferior, vende acima da

    superior. Aposta que o preco volta para a media. Funciona em mercado
    lateral e sofre em tendencia forte -- por isso o comparador a julga.
    """

    def __init__(self, params: dict | None = None):
        p = params or {}
        self.period = int(p.get("period", 20))
        self.k = float(p.get("k", 2.0))
        self.atr_period = int(p.get("atr_period", 14))
        self.stop_atr_mult = float(p.get("stop_atr_mult", 1.5))
        self.reward_risk = float(p.get("reward_risk", 1.0))
        self.allow_short = bool(p.get("allow_short", True))
        self.warmup = max(self.period, self.atr_period) + 2

    def prepare(self, candles: list[Candle]) -> None:
        self._closes, highs, lows = _ohlc(candles)
        _, self._up, self._lo = indicators.bollinger(self._closes, self.period, self.k)
        self._atr = indicators.atr(highs, lows, self._closes, self.atr_period)

    def signal(self, i: int) -> Signal:
        if i < self.warmup:
            return Signal(None)
        up, lo, atr_v = self._up[i], self._lo[i], self._atr[i]
        if None in (up, lo, atr_v):
            return Signal(None)
        price = self._closes[i]
        dist = atr_v * self.stop_atr_mult
        if price < lo:
            return Signal("long", price - dist, price + dist * self.reward_risk, "bb_long")
        if self.allow_short and price > up:
            return Signal("short", price + dist, price - dist * self.reward_risk, "bb_short")
        return Signal(None)


class TrendEmaStrategy(Strategy):
    """Cruzamento de EMAs, mas SO a favor da tendencia maior (filtro de EMA longa).

    Refinamento da estrategia base: evita comprar em tendencia de baixa e
    vender em tendencia de alta -- erro classico que gera muitos falsos sinais.
    """

    def __init__(self, params: dict | None = None):
        p = params or {}
        self.ema_fast = int(p.get("ema_fast", 9))
        self.ema_slow = int(p.get("ema_slow", 21))
        self.trend_ema = int(p.get("trend_ema", 100))
        self.atr_period = int(p.get("atr_period", 14))
        self.stop_atr_mult = float(p.get("stop_atr_mult", 1.5))
        self.reward_risk = float(p.get("reward_risk", 1.5))
        self.allow_short = bool(p.get("allow_short", True))
        self.warmup = max(self.ema_slow, self.trend_ema, self.atr_period) + 2

    def prepare(self, candles: list[Candle]) -> None:
        self._closes, highs, lows = _ohlc(candles)
        self._ef = indicators.ema(self._closes, self.ema_fast)
        self._es = indicators.ema(self._closes, self.ema_slow)
        self._trend = indicators.ema(self._closes, self.trend_ema)
        self._atr = indicators.atr(highs, lows, self._closes, self.atr_period)

    def signal(self, i: int) -> Signal:
        if i < self.warmup:
            return Signal(None)
        ef, es, efp, esp = self._ef[i], self._es[i], self._ef[i - 1], self._es[i - 1]
        trend, atr_v = self._trend[i], self._atr[i]
        if None in (ef, es, efp, esp, trend, atr_v):
            return Signal(None)
        price = self._closes[i]
        dist = atr_v * self.stop_atr_mult
        cross_up = efp <= esp and ef > es
        cross_dn = efp >= esp and ef < es
        if cross_up and price > trend:
            return Signal("long", price - dist, price + dist * self.reward_risk, "trend_up")
        if self.allow_short and cross_dn and price < trend:
            return Signal("short", price + dist, price - dist * self.reward_risk, "trend_dn")
        return Signal(None)
