"""Estruturas de dados de mercado e fontes de dados (candles/OHLCV).

Tudo em Python puro (sem pandas) para rodar em qualquer ambiente, inclusive
offline. A camada de dados eh abstrata: hoje usamos um gerador sintetico e um
leitor de CSV; amanha basta plugar uma fonte real (ccxt/Binance, yfinance,
MetaTrader5) implementando uma funcao que devolva uma lista de Candle.
"""

from __future__ import annotations

import csv
import math
import random
from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass(frozen=True)
class Candle:
    """Um candle OHLCV. ts = epoch em segundos (UTC)."""

    ts: int
    open: float
    high: float
    low: float
    close: float
    volume: float

    @property
    def day_index(self) -> int:
        """Indice do dia (UTC). Usado para regras de day trade (zerar no dia)."""
        return self.ts // 86_400

    @property
    def datetime(self) -> datetime:
        return datetime.fromtimestamp(self.ts, tz=timezone.utc)


def generate_synthetic_candles(
    n_days: int = 120,
    bars_per_day: int = 80,
    start_price: float = 120_000.0,
    daily_vol: float = 0.018,
    seed: int = 42,
) -> list[Candle]:
    """Gera candles intraday realistas via passeio aleatorio (GBM).

    Serve para desenvolver e validar o motor SEM internet. Cada "dia" tem
    ``bars_per_day`` candles de 5 min a partir das 09:00 UTC. Existe um leve
    regime de tendencia diario aleatorio, para que a estrategia veja tanto
    acertos quanto erros -- como no mercado real.
    """
    rnd = random.Random(seed)
    candles: list[Candle] = []
    price = start_price
    bar_vol = daily_vol / math.sqrt(bars_per_day)

    midnight = 1_700_000_000 - (1_700_000_000 % 86_400)
    for d in range(n_days):
        day_base = midnight + d * 86_400 + 9 * 3600  # 09:00 UTC
        drift = rnd.uniform(-0.0009, 0.0011)  # regime do dia
        for b in range(bars_per_day):
            ret = rnd.gauss(drift / bars_per_day, bar_vol)
            new = max(1.0, price * (1.0 + ret))
            o, c = price, new
            hi = max(o, c) * (1.0 + abs(rnd.gauss(0, bar_vol * 0.5)))
            lo = min(o, c) * (1.0 - abs(rnd.gauss(0, bar_vol * 0.5)))
            ts = day_base + b * 300
            candles.append(Candle(ts, o, hi, lo, c, rnd.uniform(100, 1000)))
            price = new
        # pequeno gap overnight
        price = max(1.0, price * (1.0 + rnd.gauss(0, bar_vol)))
    return candles


def generate_regime_candles(
    regime: str = "bull",
    n_days: int = 120,
    bars_per_day: int = 80,
    seed: int = 42,
) -> list[Candle]:
    """Gera candles com um regime de mercado dominante.

    ``regime``: "bull" (alta), "bear" (baixa) ou "sideways" (lateral).

    Por que isso importa: uma estrategia que so ganha em mercado de alta NAO
    tem vantagem -- so esta "torcendo" pela maré. O teste de verdade e: ela
    sobrevive nos TRES regimes? Use junto de compare_across_datasets().
    """
    drift_by_regime = {
        "bull": (0.0010, 0.0030),
        "bear": (-0.0030, -0.0010),
        "sideways": (-0.0006, 0.0006),
    }
    if regime not in drift_by_regime:
        raise ValueError(f"regime invalido: {regime!r}")
    lo, hi = drift_by_regime[regime]

    rnd = random.Random(seed)
    candles: list[Candle] = []
    price = 120_000.0
    daily_vol = 0.018
    bar_vol = daily_vol / math.sqrt(bars_per_day)
    midnight = 1_700_000_000 - (1_700_000_000 % 86_400)
    for d in range(n_days):
        day_base = midnight + d * 86_400 + 9 * 3600
        drift = rnd.uniform(lo, hi)
        for b in range(bars_per_day):
            ret = rnd.gauss(drift / bars_per_day, bar_vol)
            new = max(1.0, price * (1.0 + ret))
            o, c = price, new
            up = max(o, c) * (1.0 + abs(rnd.gauss(0, bar_vol * 0.5)))
            dn = min(o, c) * (1.0 - abs(rnd.gauss(0, bar_vol * 0.5)))
            candles.append(Candle(day_base + b * 300, o, up, dn, c, rnd.uniform(100, 1000)))
            price = new
        price = max(1.0, price * (1.0 + rnd.gauss(0, bar_vol)))
    return candles


def load_candles_csv(path: str) -> list[Candle]:
    """Le candles de um CSV com colunas: ts,open,high,low,close,volume.

    ``ts`` pode ser epoch (segundos) ou ISO 8601 (ex.: 2024-01-02T09:00:00Z).
    Use esta funcao para alimentar o backtest com dados REAIS exportados da
    sua corretora ou de uma API.
    """
    out: list[Candle] = []
    with open(path, newline="") as f:
        for row in csv.DictReader(f):
            raw_ts = row["ts"].strip()
            if raw_ts.isdigit():
                ts = int(raw_ts)
            else:
                ts = int(
                    datetime.fromisoformat(raw_ts.replace("Z", "+00:00")).timestamp()
                )
            out.append(
                Candle(
                    ts=ts,
                    open=float(row["open"]),
                    high=float(row["high"]),
                    low=float(row["low"]),
                    close=float(row["close"]),
                    volume=float(row.get("volume", 0) or 0),
                )
            )
    out.sort(key=lambda c: c.ts)
    return out
