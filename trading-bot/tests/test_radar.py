"""Testes do radar de oportunidades."""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bot.data import Candle  # noqa: E402
from bot.radar import scan_asset  # noqa: E402


def _candles(prices):
    out = []
    for i, p in enumerate(prices):
        out.append(Candle(ts=i * 86400, open=p, high=p + 0.2, low=p - 0.2, close=p, volume=1.0))
    return out


class TestRadar(unittest.TestCase):
    def test_insufficient_data(self):
        self.assertIsNone(scan_asset(_candles([10] * 10)))

    def test_uptrend_reads_alta_and_positive_momentum(self):
        c = _candles([100 + i * 0.5 for i in range(80)])  # alta limpa
        r = scan_asset(c)
        self.assertEqual(r["trend"], "ALTA")
        self.assertGreater(r["momentum"], 0)
        self.assertGreaterEqual(r["strength"], 0.0)
        self.assertLessEqual(r["strength"], 1.0)

    def test_downtrend_reads_baixa(self):
        c = _candles([200 - i * 0.5 for i in range(80)])
        r = scan_asset(c)
        self.assertEqual(r["trend"], "BAIXA")
        self.assertLess(r["momentum"], 0)

    def test_keys_present(self):
        c = _candles([100 + (i % 5) for i in range(80)])
        r = scan_asset(c)
        for k in ("price", "change", "rsi", "trend", "strength", "momentum", "setup", "score"):
            self.assertIn(k, r)


if __name__ == "__main__":
    unittest.main()
