"""Testes do cerebro central (ensemble) e da config de fonte de dados."""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dataclasses import replace  # noqa: E402

from bot import EmaRsiAtrStrategy, Settings, generate_synthetic_candles  # noqa: E402
from bot.backtest import run_backtest  # noqa: E402
from bot.brain import EnsembleStrategy, Member, build_brain  # noqa: E402
from bot.sources import DataSourceConfig, build_feed  # noqa: E402
from bot.strategies import BreakoutStrategy, MeanReversionStrategy  # noqa: E402
from bot.strategy import Signal, Strategy  # noqa: E402
from bot.validation import StrategySpec  # noqa: E402

CANDLES = generate_synthetic_candles(n_days=60, seed=4)
SETTINGS = Settings.default()


class _FixedStrategy(Strategy):
    """Estrategia de teste que sempre devolve o mesmo sinal."""

    def __init__(self, action, stop=90.0, take=110.0):
        self._sig = Signal(action, stop, take, "fixo")
        self.warmup = 0

    def prepare(self, candles):
        pass

    def signal(self, i):
        return self._sig


class TestEnsembleVoting(unittest.TestCase):
    def test_zero_weight_means_flat(self):
        members = [Member("a", _FixedStrategy("long"), 0.0)]
        brain = EnsembleStrategy(members, min_consensus=0.5)
        self.assertIsNone(brain.signal(10).action)

    def test_consensus_long(self):
        members = [
            Member("a", _FixedStrategy("long", 90, 110), 1.0),
            Member("b", _FixedStrategy("long", 92, 112), 1.0),
            Member("c", _FixedStrategy("short", 100, 80), 1.0),
        ]
        brain = EnsembleStrategy(members, min_consensus=0.5)
        sig = brain.signal(10)
        self.assertEqual(sig.action, "long")  # 2/3 do peso -> long
        self.assertAlmostEqual(sig.stop, 91.0)  # media dos stops que concordam
        self.assertAlmostEqual(brain.last_confidence, 2 / 3)

    def test_no_consensus_when_split(self):
        members = [
            Member("a", _FixedStrategy("long"), 1.0),
            Member("b", _FixedStrategy("short"), 1.0),
        ]
        brain = EnsembleStrategy(members, min_consensus=0.6)
        # empate 50/50 < 60% exigido -> fica parado
        self.assertIsNone(brain.signal(10).action)


class TestBuildBrain(unittest.TestCase):
    def test_build_brain_assigns_weights_and_runs(self):
        specs = [
            StrategySpec("breakout", BreakoutStrategy, {"channel": [10, 20]}),
            StrategySpec("meanrev", MeanReversionStrategy, {"oversold": [20, 30]}),
        ]
        brain, diags = build_brain(CANDLES, SETTINGS, specs, n_folds=3)
        self.assertEqual(len(diags), 2)
        for d in diags:
            # peso 0 quando nao robusta; senao igual aos folds positivos
            if d.robust:
                self.assertGreater(d.weight, 0)
            else:
                self.assertEqual(d.weight, 0.0)
        # o cerebro roda no motor sem erro
        result = run_backtest(CANDLES, brain, SETTINGS)
        self.assertIn("n_trades", result.metrics)


class TestDataSource(unittest.TestCase):
    def test_replay_feed_from_config(self):
        cfg = DataSourceConfig(provider="replay")
        feed = build_feed(cfg, candles=CANDLES[:20])
        self.assertEqual(len(list(feed.stream())), 20)

    def test_replay_requires_candles(self):
        with self.assertRaises(ValueError):
            build_feed(DataSourceConfig(provider="replay"))

    def test_unknown_provider(self):
        with self.assertRaises(ValueError):
            build_feed(DataSourceConfig(provider="nasa"))

    def test_describe(self):
        cfg = DataSourceConfig(provider="ccxt", symbol="ETH/USDT", timeframe="1h")
        self.assertIn("ETH/USDT", cfg.describe())


if __name__ == "__main__":
    unittest.main()
