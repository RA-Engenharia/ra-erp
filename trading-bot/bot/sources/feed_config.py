"""Parametros de fonte de dados -- de onde o cerebro le precos em tempo real.

Um unico objeto de configuracao descreve a fonte (cripto via ccxt, acoes via
yfinance, CSV, ou replay) e os parametros de coleta. build_feed() transforma
essa config no feed certo para o LiveTrader. Trocar de mercado/ativo e so mudar
a config -- o cerebro e o motor de risco nao mudam nada.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..data import Candle, load_candles_csv
from ..feeds import CcxtLiveFeed, ReplayFeed


@dataclass
class DataSourceConfig:
    """Parametros de coleta de dados em tempo real (ou replay).

    provider:
      - "ccxt"     : corretora cripto ao vivo (Binance etc.) -- precisa internet
      - "yfinance" : acoes/ETFs (baixa historico e reproduz) -- precisa internet
      - "csv"      : le candles de um arquivo e reproduz como se fosse ao vivo
      - "replay"   : reproduz uma lista de Candle ja em memoria (testes/demo)
    """

    provider: str = "ccxt"
    symbol: str = "BTC/USDT"
    timeframe: str = "5m"
    exchange: str = "binance"
    poll_seconds: float = 5.0
    lookback: int = 200  # candles por chamada (ccxt)
    delay: float = 0.0  # atraso entre candles no replay/csv (segundos)
    csv_path: str | None = None
    max_candles: int | None = None  # corta o stream ao vivo apos N candles
    # parametros yfinance
    yf_period: str = "60d"
    yf_interval: str = "5m"

    def describe(self) -> str:
        if self.provider == "ccxt":
            return f"{self.symbol} {self.timeframe} ao vivo @ {self.exchange} (poll {self.poll_seconds}s)"
        if self.provider == "yfinance":
            return f"{self.symbol} via yfinance (period={self.yf_period}, interval={self.yf_interval})"
        if self.provider == "csv":
            return f"replay de CSV: {self.csv_path}"
        return "replay em memoria"


def build_feed(config: DataSourceConfig, candles: list[Candle] | None = None):
    """Constroi o feed a partir da config. Devolve um objeto com .stream().

    ``candles`` so e usado quando provider == "replay".
    """
    if config.provider == "ccxt":
        return CcxtLiveFeed(
            symbol=config.symbol,
            timeframe=config.timeframe,
            exchange_id=config.exchange,
            poll_seconds=config.poll_seconds,
            limit=config.lookback,
            max_candles=config.max_candles,
        )
    if config.provider == "yfinance":
        from .yfinance_source import load_yfinance

        data = load_yfinance(config.symbol, config.yf_period, config.yf_interval)
        return ReplayFeed(data, config.delay)
    if config.provider == "yfinance_live":
        from .yfinance_source import YFinanceLiveFeed

        return YFinanceLiveFeed(
            symbol=config.symbol,
            interval=config.yf_interval,
            period=config.yf_period,
            poll_seconds=config.poll_seconds,
            max_candles=config.max_candles,
        )
    if config.provider == "csv":
        if not config.csv_path:
            raise ValueError("provider 'csv' exige csv_path na config.")
        return ReplayFeed(load_candles_csv(config.csv_path), config.delay)
    if config.provider == "replay":
        if candles is None:
            raise ValueError("provider 'replay' exige a lista de candles.")
        return ReplayFeed(candles, config.delay)
    raise ValueError(f"provider desconhecido: {config.provider!r}")
