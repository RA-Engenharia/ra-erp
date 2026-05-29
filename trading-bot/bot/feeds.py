"""Fontes de candles para o LiveTrader -- do replay historico ao feed REAL.

O LiveTrader so precisa de um iteravel de Candle. Aqui ficam os adaptadores:

  - ReplayFeed   : reproduz candles historicos (ensaio, demo, debug).
  - CcxtLiveFeed : busca candles de uma corretora real (Binance etc.) via ccxt,
                   entregando SO candles ja FECHADOS (nunca o que ainda se forma).

Para ir ao vivo de verdade: instale ``ccxt``, crie o feed apontando para o seu
par/timeframe e passe-o ao run_live(). O motor (estrategia + risco + broker)
nao muda -- so a origem dos dados.
"""

from __future__ import annotations

import time
from collections.abc import Callable, Iterator

from .data import Candle
from .live import candle_feed


class ReplayFeed:
    """Reproduz uma lista de candles como se chegassem ao vivo."""

    def __init__(self, candles: list[Candle], delay: float = 0.0):
        self._candles = candles
        self._delay = delay

    def stream(self) -> Iterator[Candle]:
        return candle_feed(self._candles, self._delay)


# Tipo do "fetcher": devolve linhas OHLCV cruas no formato ccxt
#   [ [ts_ms, open, high, low, close, volume], ... ]
OhlcvFetcher = Callable[[], list[list[float]]]


def _ccxt_fetcher(exchange_id: str, symbol: str, timeframe: str, limit: int) -> OhlcvFetcher:
    """Cria um fetcher que chama ccxt. Import tardio: so exige ccxt no uso real."""
    try:
        import ccxt  # type: ignore
    except ImportError as exc:  # pragma: no cover - depende de lib externa
        raise RuntimeError(
            "Para feed ao vivo instale ccxt:  pip install ccxt\n"
            "(ou use ReplayFeed / dados via CSV para testar sem corretora)."
        ) from exc
    exchange = getattr(ccxt, exchange_id)({"enableRateLimit": True})

    def fetch() -> list[list[float]]:
        return exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)

    return fetch


def _row_to_candle(row: list[float]) -> Candle:
    """Converte uma linha OHLCV do ccxt (ts em ms) em Candle (ts em segundos)."""
    ts_ms, o, h, low, c, v = row[:6]
    return Candle(int(ts_ms) // 1000, float(o), float(h), float(low), float(c), float(v))


class CcxtLiveFeed:
    """Feed ao vivo de uma corretora via ccxt.

    Estrategia anti-lookahead: a cada poll, o ccxt devolve tambem o candle que
    AINDA esta se formando (o ultimo). Nunca entregamos esse -- so candles cujo
    timestamp ja avancou, ou seja, JA FECHARAM. Assim o robo ao vivo decide com
    a mesma honestidade do backtest.
    """

    def __init__(
        self,
        symbol: str = "BTC/USDT",
        timeframe: str = "5m",
        exchange_id: str = "binance",
        poll_seconds: float = 5.0,
        limit: int = 200,
        fetch: OhlcvFetcher | None = None,
        max_candles: int | None = None,
        sleep: Callable[[float], None] = time.sleep,
    ):
        self.symbol = symbol
        self.timeframe = timeframe
        self.poll_seconds = poll_seconds
        self.max_candles = max_candles
        self._sleep = sleep
        self._fetch = fetch or _ccxt_fetcher(exchange_id, symbol, timeframe, limit)
        self._last_ts: int = 0

    def stream(self) -> Iterator[Candle]:
        emitted = 0
        while True:
            rows = self._fetch() or []
            # o ultimo candle ainda esta se formando -> descarta
            closed = rows[:-1] if len(rows) >= 1 else []
            for row in closed:
                c = _row_to_candle(row)
                if c.ts > self._last_ts:
                    self._last_ts = c.ts
                    emitted += 1
                    yield c
                    if self.max_candles is not None and emitted >= self.max_candles:
                        return
            self._sleep(self.poll_seconds)
