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


def sma(values: list[float], period: int) -> list[float | None]:
    """Media movel simples."""
    n = len(values)
    out: list[float | None] = [None] * n
    if period <= 0:
        return out
    s = 0.0
    for i, v in enumerate(values):
        s += v
        if i >= period:
            s -= values[i - period]
        if i >= period - 1:
            out[i] = s / period
    return out


def roc(values: list[float], period: int = 12) -> list[float | None]:
    """Rate of Change (%) -- momentum puro: variacao percentual em ``period``."""
    n = len(values)
    out: list[float | None] = [None] * n
    for i in range(period, n):
        prev = values[i - period]
        out[i] = ((values[i] / prev) - 1.0) * 100.0 if prev != 0 else 0.0
    return out


def supertrend(
    highs: list[float],
    lows: list[float],
    closes: list[float],
    period: int = 10,
    mult: float = 3.0,
) -> tuple[list[float | None], list[int | None]]:
    """SuperTrend -- seguidor de tendencia baseado em ATR.

    Devolve (linha, direcao). direcao = +1 (alta) ou -1 (baixa). A linha serve
    de stop dinamico que sobe na alta e desce na baixa.
    """
    n = len(closes)
    line: list[float | None] = [None] * n
    direction: list[int | None] = [None] * n
    atr_v = atr(highs, lows, closes, period)
    final_upper = final_lower = st_prev = None
    for i in range(n):
        if atr_v[i] is None:
            continue
        hl2 = (highs[i] + lows[i]) / 2.0
        basic_upper = hl2 + mult * atr_v[i]
        basic_lower = hl2 - mult * atr_v[i]
        if final_upper is None:
            fu, fl = basic_upper, basic_lower
        else:
            fu = basic_upper if (basic_upper < final_upper or closes[i - 1] > final_upper) else final_upper
            fl = basic_lower if (basic_lower > final_lower or closes[i - 1] < final_lower) else final_lower

        if st_prev is None or st_prev == final_upper:
            # vinha em baixa (ou primeira barra): viramos para alta se rompe o topo
            if closes[i] > fu:
                st, d = fl, 1
            else:
                st, d = fu, -1
        else:
            # vinha em alta: viramos para baixa se perde o piso
            if closes[i] < fl:
                st, d = fu, -1
            else:
                st, d = fl, 1

        line[i], direction[i] = st, d
        final_upper, final_lower, st_prev = fu, fl, st
    return line, direction


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
