"""Testes dos indicadores tecnicos."""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bot import indicators  # noqa: E402


class TestEma(unittest.TestCase):
    def test_constant_series(self):
        out = indicators.ema([5.0] * 10, period=3)
        self.assertIsNone(out[1])
        for v in out[2:]:
            self.assertAlmostEqual(v, 5.0)

    def test_warmup_is_none(self):
        out = indicators.ema([1.0, 2.0], period=5)
        self.assertTrue(all(v is None for v in out))


class TestRsi(unittest.TestCase):
    def test_only_gains_gives_100(self):
        out = indicators.rsi([float(i) for i in range(1, 31)], period=14)
        self.assertAlmostEqual(out[-1], 100.0)

    def test_only_losses_gives_0(self):
        out = indicators.rsi([float(i) for i in range(30, 0, -1)], period=14)
        self.assertAlmostEqual(out[-1], 0.0)


class TestAtr(unittest.TestCase):
    def test_constant_range(self):
        n = 20
        highs = [10.0] * n
        lows = [9.0] * n
        closes = [9.5] * n
        out = indicators.atr(highs, lows, closes, period=3)
        self.assertAlmostEqual(out[-1], 1.0)


if __name__ == "__main__":
    unittest.main()
