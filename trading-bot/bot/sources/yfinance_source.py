"""Adaptador de dados reais de acoes (EUA) via yfinance.

Requer internet e a biblioteca yfinance:

    pip install yfinance

Limites do yfinance para dados INTRADAY (importante para day trade):
  - intervalo "1m"  -> apenas ultimos ~7 dias
  - intervalo "5m"  -> apenas ultimos ~60 dias
  - intervalo "1h"  -> ultimos ~730 dias
  - intervalo "1d"  -> historico longo (anos) -- bom para swing trade
"""

from __future__ import annotations

from ..data import Candle


def load_yfinance(
    symbol: str,
    period: str = "60d",
    interval: str = "5m",
) -> list[Candle]:
    """Baixa candles de ``symbol`` (ex.: "AAPL", "MSFT") e devolve list[Candle].

    ``period`` ex.: "7d", "60d", "1y", "max". ``interval`` ex.: "1m","5m","1h","1d".
    """
    try:
        import yfinance as yf
    except ImportError as exc:  # pragma: no cover - depende de ambiente externo
        raise ImportError(
            "yfinance nao instalado. Rode: pip install yfinance\n"
            "(precisa de internet; o motor em si funciona sem ele)."
        ) from exc

    df = yf.download(
        symbol,
        period=period,
        interval=interval,
        auto_adjust=False,
        progress=False,
    )
    if df is None or len(df) == 0:
        raise ValueError(
            f"Nenhum dado retornado para {symbol} (period={period}, "
            f"interval={interval}). Verifique o ticker e os limites do yfinance."
        )

    candles: list[Candle] = []
    for ts, row in df.iterrows():
        # yfinance pode devolver colunas multi-nivel (com o ticker); normaliza.
        def _get(col: str) -> float:
            val = row[col]
            try:
                return float(val)
            except (TypeError, ValueError):
                return float(val.iloc[0])

        epoch = int(ts.timestamp())
        candles.append(
            Candle(
                ts=epoch,
                open=_get("Open"),
                high=_get("High"),
                low=_get("Low"),
                close=_get("Close"),
                volume=_get("Volume"),
            )
        )
    candles.sort(key=lambda c: c.ts)
    return candles
