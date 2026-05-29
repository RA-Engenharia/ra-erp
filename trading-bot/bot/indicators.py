"""Indicadores tecnicos em Python puro.

Cada funcao recebe listas de floats e devolve uma lista do mesmo tamanho,
usando ``None`` enquanto nao houver dados suficientes (periodo de aquecimento).
Isso evita "olhar para o futuro" (lookahead bias) no backtest.
"""

from __future__ import annotations


def ema(values: list[float], period: int) -> list[float | None]:
    """Media movel exponencial. Semente = SMA dos primeiros `period` valores."""
    out: list[float | None] = [None] * len(values)
    if period <= 0 or len(values) < period:
        return out
    k = 2.0 / (period + 1.0)
    seed = sum(values[:period]) / period
    out[period - 1] = seed
    prev = seed
    for i in range(period, len(values)):
        prev = values[i] * k + prev * (1.0 - k)
        out[i] = prev
    return out


def rsi(values: list[float], period: int = 14) -> list[float | None]:
    """Indice de Forca Relativa (RSI) com suavizacao de Wilder."""
    out: list[float | None] = [None] * len(values)
    if len(values) <= period:
        return out
    gains: list[float] = []
    losses: list[float] = []
    for i in range(1, len(values)):
        ch = values[i] - values[i - 1]
        gains.append(max(ch, 0.0))
        losses.append(max(-ch, 0.0))

    def _rsi(ag: float, al: float) -> float:
        if al == 0:
            return 100.0
        rs = ag / al
        return 100.0 - 100.0 / (1.0 + rs)

    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period
    out[period] = _rsi(avg_gain, avg_loss)
    for i in range(period + 1, len(values)):
        avg_gain = (avg_gain * (period - 1) + gains[i - 1]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i - 1]) / period
        out[i] = _rsi(avg_gain, avg_loss)
    return out


def macd(
    values: list[float],
    fast: int = 12,
    slow: int = 26,
    signal: int = 9,
) -> tuple[list[float | None], list[float | None], list[float | None]]:
    """MACD: (linha, sinal, histograma). Mede momentum via diferenca de EMAs.

    linha   = EMA(fast) - EMA(slow)
    sinal   = EMA(linha, signal)
    histograma = linha - sinal  (cruza o zero quando a linha cruza o sinal)
    """
    n = len(values)
    ef, es = ema(values, fast), ema(values, slow)
    line: list[float | None] = [None] * n
    for i in range(n):
        if ef[i] is not None and es[i] is not None:
            line[i] = ef[i] - es[i]

    sig: list[float | None] = [None] * n
    start = next((i for i, v in enumerate(line) if v is not None), None)
    if start is not None:
        valid = [v for v in line[start:]]  # sequencia contigua de floats
        sline = ema(valid, signal)
        for k, val in enumerate(sline):
            sig[start + k] = val

    hist: list[float | None] = [None] * n
    for i in range(n):
        if line[i] is not None and sig[i] is not None:
            hist[i] = line[i] - sig[i]
    return line, sig, hist


def bollinger(
    values: list[float],
    period: int = 20,
    k: float = 2.0,
) -> tuple[list[float | None], list[float | None], list[float | None]]:
    """Bandas de Bollinger: (media, banda_superior, banda_inferior).

    Banda = media movel +/- k desvios-padrao. Preco fora das bandas sugere
    extremo (base de estrategias de reversao a media).
    """
    n = len(values)
    mid: list[float | None] = [None] * n
    upper: list[float | None] = [None] * n
    lower: list[float | None] = [None] * n
    if period <= 0:
        return mid, upper, lower
    for i in range(period - 1, n):
        window = values[i - period + 1 : i + 1]
        m = sum(window) / period
        var = sum((x - m) ** 2 for x in window) / period
        sd = var**0.5
        mid[i], upper[i], lower[i] = m, m + k * sd, m - k * sd
    return mid, upper, lower


def efficiency_ratio(values: list[float], period: int = 10) -> list[float | None]:
    """Efficiency Ratio (Kaufman) -- mede FORCA de tendencia, de 0 a 1.

    ER = |variacao liquida no periodo| / (soma das variacoes absolutas).
      ~1  -> movimento direto e limpo (tendencia forte)
      ~0  -> vai-e-volta (mercado lateral / ruidoso)

    Base economica para escolher o regime: momentum quer ER alto; reversao a
    media quer ER baixo. Sem parametro "magico" alem do periodo.
    """
    n = len(values)
    out: list[float | None] = [None] * n
    if period <= 0:
        return out
    for i in range(period, n):
        change = abs(values[i] - values[i - period])
        vol = sum(abs(values[k] - values[k - 1]) for k in range(i - period + 1, i + 1))
        out[i] = (change / vol) if vol > 0 else 0.0
    return out


def atr(
    highs: list[float],
    lows: list[float],
    closes: list[float],
    period: int = 14,
) -> list[float | None]:
    """Average True Range -- mede volatilidade. Base do stop dinamico."""
    n = len(closes)
    out: list[float | None] = [None] * n
    if n <= period:
        return out
    trs = [highs[0] - lows[0]]
    for i in range(1, n):
        tr = max(
            highs[i] - lows[i],
            abs(highs[i] - closes[i - 1]),
            abs(lows[i] - closes[i - 1]),
        )
        trs.append(tr)
    first = sum(trs[1 : period + 1]) / period
    out[period] = first
    prev = first
    for i in range(period + 1, n):
        prev = (prev * (period - 1) + trs[i]) / period
        out[i] = prev
    return out
