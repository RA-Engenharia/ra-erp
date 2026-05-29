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
from bot.chart import equity_curve_ascii  # noqa: E402
from bot.data import generate_regime_candles  # noqa: E402
from bot.validation import (  # noqa: E402
    StrategySpec,
    compare_across_datasets,
    compare_strategies,
)

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


class TestRegimeAndChart(unittest.TestCase):
    def test_regime_generation(self):
        # Um unico caminho aleatorio pode enganar (o ruido vence a tendencia em
        # janelas curtas) -- por isso checamos a TENDENCIA estatistica em varias
        # sementes, que e o que um "regime" de fato significa.
        def up_count(regime):
            return sum(
                1
                for s in range(10)
                if (c := generate_regime_candles(regime, n_days=120, seed=s))[-1].close
                > c[0].close
            )

        self.assertGreaterEqual(up_count("bull"), 8)
        self.assertLessEqual(up_count("bear"), 2)
        with self.assertRaises(ValueError):
            generate_regime_candles("nonsense")

    def test_cross_dataset_aggregates_all_regimes(self):
        datasets = {
            r: generate_regime_candles(r, n_days=80, seed=3)
            for r in ("bull", "bear", "sideways")
        }
        specs = [
            StrategySpec("breakout", BreakoutStrategy, {"channel": [10, 20]}),
            StrategySpec("meanrev", MeanReversionStrategy, {"oversold": [20, 30]}),
        ]
        rows = compare_across_datasets(datasets, SETTINGS, specs, n_folds=2, min_trades=1)
        self.assertEqual(len(rows), 2)
        for r in rows:
            self.assertEqual(set(r.per_dataset), {"bull", "bear", "sideways"})
            self.assertLessEqual(r.total_folds_positive, r.total_folds)
        fracs = [r.fraction_positive for r in rows]
        self.assertEqual(fracs, sorted(fracs, reverse=True))

    def test_equity_chart_renders(self):
        result = run_backtest(CANDLES, BreakoutStrategy(), SETTINGS)
        art = equity_curve_ascii(result.equity_curve)
        self.assertIn("capital", art)
        self.assertEqual(equity_curve_ascii([]), "(curva de capital insuficiente para desenhar)")


if __name__ == "__main__":
    unittest.main()
