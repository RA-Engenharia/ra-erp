"""Testes do scanner de vantagem (com dados sinteticos)."""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bot import Settings, generate_synthetic_candles  # noqa: E402
from bot.scanner import ScanResult, format_scan, scan_candles  # noqa: E402
from bot.strategies import BreakoutStrategy, MeanReversionStrategy  # noqa: E402
from bot.validation import StrategySpec  # noqa: E402

CANDLES = generate_synthetic_candles(n_days=80, seed=6)
SETTINGS = Settings.default()
SPECS = [
    StrategySpec("breakout", BreakoutStrategy, {"channel": [10, 20]}),
    StrategySpec("meanrev", MeanReversionStrategy, {"oversold": [20, 30]}),
]


class TestScanner(unittest.TestCase):
    def test_scan_candles_returns_best(self):
        res = scan_candles("teste", CANDLES, SETTINGS, SPECS, n_folds=3)
        self.assertIsInstance(res, ScanResult)
        self.assertIn(res.best_strategy, ("breakout", "meanrev", "-"))
        self.assertLessEqual(res.folds_positive, res.n_folds)
        # robusta exige maioria de folds positivos E expectancia positiva
        if res.robust:
            self.assertGreater(res.avg_oos_expectancy, 0)

    def test_format_scan_handles_empty_and_errors(self):
        rows = [ScanResult("X 1d", 0, "-", 0, 0, 0.0, False, "sem internet")]
        out = format_scan(rows)
        self.assertIn("VARREDURA", out)
        self.assertIn("sem internet", out)

    def test_robust_sorts_first(self):
        rows = [
            ScanResult("A", 500, "s1", 1, 4, -1.0, False),
            ScanResult("B", 500, "s2", 3, 4, 5.0, True),
        ]
        out = format_scan(rows)
        # o robusto (B) deve aparecer antes do nao-robusto (A)
        self.assertLess(out.index(" B "), out.index(" A "))


if __name__ == "__main__":
    unittest.main()
