"""Testes das estrategias candidatas e da comparacao."""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dataclasses import replace  # noqa: E402

from bot import EmaRsiAtrStrategy, Settings, generate_synthetic_candles  # noqa: E402
from bot.backtest import run_backtest  # noqa: E402
from bot.strategies import (  # noqa: E402
    BreakoutStrategy,
    MeanReversionStrategy,
    TrendEmaStrategy,
)
from bot.validation import StrategySpec, compare_strategies  # noqa: E402

CANDLES = generate_synthetic_candles(n_days=120, seed=9)
SETTINGS = Settings.default()


class TestStrategiesRun(unittest.TestCase):
    def test_each_strategy_runs_and_trades(self):
        for cls in (BreakoutStrategy, MeanReversionStrategy, TrendEmaStrategy):
            result = run_backtest(CANDLES, cls(), SETTINGS)
            # roda sem erro e gera ao menos algumas operacoes
            self.assertGreater(result.metrics["n_trades"], 0, cls.__name__)

    def test_no_signal_during_warmup(self):
        strat = TrendEmaStrategy({"trend_ema": 100})
        strat.prepare(CANDLES)
        for i in range(strat.warmup):
            self.assertIsNone(strat.signal(i).action)


class TestCompareStrategies(unittest.TestCase):
    def test_comparison_ranks_all_specs(self):
        specs = [
            StrategySpec(
                "base",
                lambda p: EmaRsiAtrStrategy(replace(SETTINGS.strategy, **p)),
                {"ema_fast": [5, 9], "ema_slow": [21, 30]},
            ),
            StrategySpec("breakout", BreakoutStrategy, {"channel": [10, 20]}),
            StrategySpec("meanrev", MeanReversionStrategy, {"oversold": [20, 30]}),
        ]
        rows = compare_strategies(CANDLES, SETTINGS, specs, n_folds=3, min_trades=1)
        self.assertEqual(len(rows), 3)
        # ranqueado por (folds positivos, expectancia) decrescente
        scores = [(r.folds_positive, r.avg_oos_expectancy) for r in rows]
        self.assertEqual(scores, sorted(scores, reverse=True))


if __name__ == "__main__":
    unittest.main()
