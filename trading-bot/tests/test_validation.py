"""Testes do motor de validacao (anti-overfitting)."""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bot import Settings, generate_synthetic_candles  # noqa: E402
from bot.validation import grid_search, train_test, walk_forward  # noqa: E402

GRID = {"ema_fast": [5, 9], "ema_slow": [21, 30], "stop_atr_mult": [1.0, 2.0]}


class TestGridSearch(unittest.TestCase):
    def setUp(self):
        self.candles = generate_synthetic_candles(n_days=120, seed=3)
        self.settings = Settings.default()

    def test_grid_search_returns_valid_params(self):
        best = grid_search(self.candles, self.settings, GRID, min_trades=1)
        self.assertIsNotNone(best)
        # ema_fast deve ser sempre menor que ema_slow (combinacoes invalidas saem)
        self.assertLess(best.params["ema_fast"], best.params["ema_slow"])
        self.assertIn("n_trades", best.metrics)

    def test_min_trades_filters_out_unreliable(self):
        # min_trades altissimo -> nenhuma combinacao qualifica
        best = grid_search(self.candles, self.settings, GRID, min_trades=10_000)
        self.assertIsNone(best)


class TestTrainTest(unittest.TestCase):
    def test_split_produces_in_and_out_of_sample(self):
        candles = generate_synthetic_candles(n_days=150, seed=11)
        res = train_test(candles, Settings.default(), GRID, min_trades=1)
        self.assertIsNotNone(res)
        self.assertIn("expectancy", res.in_sample)
        self.assertIn("expectancy", res.out_of_sample)


class TestWalkForward(unittest.TestCase):
    def test_walk_forward_runs_folds(self):
        candles = generate_synthetic_candles(n_days=200, seed=5)
        folds = walk_forward(candles, Settings.default(), GRID, n_folds=4, min_trades=1)
        self.assertGreater(len(folds), 0)
        for f in folds:
            self.assertLess(f.params["ema_fast"], f.params["ema_slow"])


if __name__ == "__main__":
    unittest.main()
