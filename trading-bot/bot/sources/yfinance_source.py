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


class YFinanceLiveFeed:
    """Feed 'ao vivo' de acoes via yfinance (preco real, com atraso).

    Importante e honesto: o yfinance NAO e tempo-real de verdade -- os dados sao
    atrasados (~15 min) e so atualizam no horario do pregao. Para PAPER TRADING
    e ensaio isso serve; para execucao real seria preciso um feed de corretora
    (ex.: MetaTrader 5). Usa a mesma interface .stream() do CcxtLiveFeed.

    A cada poll baixa o historico recente e entrega so candles JA FECHADOS
    (descarta o ultimo, que ainda se forma), sem repetir. O primeiro poll ja
    entrega o historico (catch-up) para o robo aquecer.
    """

    def __init__(
        self,
        symbol: str = "PETR4.SA",
        interval: str = "1h",
        period: str = "60d",
        poll_seconds: float = 300.0,
        max_candles: int | None = None,
        loader=None,
        sleep=None,
    ):
        import time

        self.symbol = symbol
        self.interval = interval
        self.period = period
        self.poll_seconds = poll_seconds
        self.max_candles = max_candles
        self._loader = loader or (lambda: load_yfinance(symbol, period, interval))
        self._sleep = sleep or time.sleep
        self._last_ts = 0

    def stream(self):
        emitted = 0
        while True:
            candles = self._loader() or []
            closed = candles[:-1] if len(candles) >= 1 else []
            for c in closed:
                if c.ts > self._last_ts:
                    self._last_ts = c.ts
                    emitted += 1
                    yield c
                    if self.max_candles is not None and emitted >= self.max_candles:
                        return
            self._sleep(self.poll_seconds)
