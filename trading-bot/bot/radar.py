"""Radar de oportunidades -- leitura tecnica RAPIDA de um ativo.

Diferente do cerebro (que faz walk-forward, lento), aqui e um raio-X rapido:
tendencia, RSI, momentum (ROC), forca da tendencia e se ha um SETUP fresco
(cruzamento de medias a favor da tendencia). Serve para varrer muitos ativos
e achar onde focar -- depois voce roda a analise completa no ativo escolhido.

E uma PRE-SELECAO tecnica, nao uma garantia. O placar honesto continua sendo o
extrato de sinais.
"""

from __future__ import annotations

from . import indicators
from .data import Candle


def scan_asset(candles: list[Candle]) -> dict | None:
    """Raio-X tecnico do ultimo candle. Devolve None se faltam dados."""
    closes = [c.close for c in candles]
    n = len(closes)
    if n < 60:
        return None
    i = n - 1
    price = closes[i]
    rsi = indicators.rsi(closes, 14)[i]
    er = indicators.efficiency_ratio(closes, 10)[i]
    roc = indicators.roc(closes, 12)[i]
    ef = indicators.ema(closes, 9)
    es = indicators.ema(closes, 21)
    el = indicators.ema(closes, 50)
    change = (closes[i] / closes[i - 1] - 1) if i > 0 else 0.0

    trend = "LATERAL"
    if None not in (ef[i], es[i], el[i]):
        if ef[i] > es[i] and price > el[i]:
            trend = "ALTA"
        elif ef[i] < es[i] and price < el[i]:
            trend = "BAIXA"

    setup = "—"
    if None not in (ef[i], es[i], ef[i - 1], es[i - 1], el[i]):
        cross_up = ef[i - 1] <= es[i - 1] and ef[i] > es[i]
        cross_dn = ef[i - 1] >= es[i - 1] and ef[i] < es[i]
        if cross_up and price > el[i]:
            setup = "COMPRA"
        elif cross_dn and price < el[i]:
            setup = "VENDA"

    return {
        "price": price,
        "change": change,
        "rsi": rsi,
        "trend": trend,
        "strength": er,
        "momentum": roc,
        "setup": setup,
        # forca para ranquear: momentum ponderado pela limpeza da tendencia
        "score": (roc or 0.0) * (er or 0.0),
    }
