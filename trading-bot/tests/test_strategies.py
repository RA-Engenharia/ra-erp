"""Testes das estrategias candidatas e da comparacao."""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dataclasses import replace  # noqa: E402

from bot import EmaRsiAtrStrategy, Settings, generate_synthetic_candles  # noqa: E402
from bot.backtest import run_backtest  # noqa: E402
from bot import indicators  # noqa: E402
from bot.strategies import (  # noqa: E402
    BollingerStrategy,
    BreakoutStrategy,
    MacdStrategy,
    MeanReversionStrategy,
    RegimeFilteredStrategy,
    TrendEmaStrategy,
)
from bot.strategy import Signal, Strategy  # noqa: E402
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
        strategies = (
            BreakoutStrategy,
            MeanReversionStrategy,
            TrendEmaStrategy,
            MacdStrategy,
            BollingerStrategy,
        )
        for cls in strategies:
            result = run_backtest(CANDLES, cls(), SETTINGS)
            # roda sem erro e gera ao menos algumas operacoes
            self.assertGreater(result.metrics["n_trades"], 0, cls.__name__)

    def test_no_signal_during_warmup(self):
        strat = TrendEmaStrategy({"trend_ema": 100})
        strat.prepare(CANDLES)
        for i in range(strat.warmup):
            self.assertIsNone(strat.signal(i).action)


class TestNewIndicators(unittest.TestCase):
    def test_macd_alignment_and_warmup(self):
        closes = [c.close for c in CANDLES]
        line, sig, hist = indicators.macd(closes, 12, 26, 9)
        self.assertEqual(len(line), len(closes))
        self.assertEqual(len(sig), len(closes))
        # aquecimento: nada de sinal/histograma no inicio
        self.assertIsNone(sig[0])
        self.assertIsNone(hist[0])
        # onde linha e sinal existem, histograma = linha - sinal
        for i in range(len(closes)):
            if line[i] is not None and sig[i] is not None:
                self.assertAlmostEqual(hist[i], line[i] - sig[i], places=9)

    def test_efficiency_ratio_bounds(self):
        # serie perfeitamente direta -> ER = 1 ; serie vai-e-volta -> ER baixo
        up = list(range(1, 40))
        er_up = indicators.efficiency_ratio([float(x) for x in up], 10)
        self.assertAlmostEqual(er_up[20], 1.0, places=9)
        zig = [10.0 + (1 if k % 2 else -1) for k in range(40)]
        er_zig = indicators.efficiency_ratio(zig, 10)
        self.assertLess(er_zig[20], 0.3)
        for v in er_up[10:]:
            self.assertTrue(0.0 <= v <= 1.0)

    def test_bollinger_bands_order(self):
        closes = [c.close for c in CANDLES]
        mid, up, lo = indicators.bollinger(closes, 20, 2.0)
        self.assertIsNone(mid[0])
        for i in range(len(closes)):
            if mid[i] is not None:
                self.assertLessEqual(lo[i], mid[i])
                self.assertLessEqual(mid[i], up[i])


class _AlwaysLong(Strategy):
    def __init__(self):
        self.warmup = 0

    def prepare(self, candles):
        pass

    def signal(self, i):
        return Signal("long", 90.0, 110.0, "x")


class TestRegimeFilter(unittest.TestCase):
    def test_trend_filter_blocks_in_chop_passes_in_trend(self):
        # serie em tendencia limpa: ER alto -> filtro 'trend' deixa passar
        trend_candles = [
            type(CANDLES[0])(ts=i, open=float(i), high=float(i) + 0.5, low=float(i) - 0.5, close=float(i), volume=1.0)
            for i in range(1, 60)
        ]
        strat = RegimeFilteredStrategy(_AlwaysLong(), mode="trend", er_period=10, er_threshold=0.3)
        strat.prepare(trend_candles)
        self.assertEqual(strat.signal(40).action, "long")

        # serie lateral (vai-e-volta): ER baixo -> filtro 'trend' BLOQUEIA
        chop = []
        base = type(CANDLES[0])
        for i in range(60):
            px = 100.0 + (1 if i % 2 else -1)
            chop.append(base(ts=i, open=px, high=px + 0.2, low=px - 0.2, close=px, volume=1.0))
        strat2 = RegimeFilteredStrategy(_AlwaysLong(), mode="trend", er_period=10, er_threshold=0.3)
        strat2.prepare(chop)
        self.assertIsNone(strat2.signal(40).action)

    def test_invalid_mode(self):
        with self.assertRaises(ValueError):
            RegimeFilteredStrategy(_AlwaysLong(), mode="lol")

    def test_runs_in_backtest(self):
        wrapped = RegimeFilteredStrategy(BreakoutStrategy(), mode="trend")
        result = run_backtest(CANDLES, wrapped, SETTINGS)
        self.assertIn("n_trades", result.metrics)


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
