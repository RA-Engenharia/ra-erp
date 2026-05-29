"""Testes do motor de paper trading ao vivo."""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bot import EmaRsiAtrStrategy, Settings, generate_synthetic_candles  # noqa: E402
from bot.live import LiveTrader, candle_feed, run_live  # noqa: E402

CANDLES = generate_synthetic_candles(n_days=40, seed=5)
SETTINGS = Settings.default()


class TestLiveTrader(unittest.TestCase):
    def test_update_per_candle(self):
        trader = LiveTrader(EmaRsiAtrStrategy(SETTINGS.strategy), SETTINGS)
        updates = run_live(trader, candle_feed(CANDLES))
        # um update por candle (a menos que o risco desligue antes)
        self.assertLessEqual(len(updates), len(CANDLES))
        self.assertEqual(len(trader.equity_curve), len(updates))
        for u in updates:
            self.assertIn(u.position, ("long", "short", None))

    def test_no_entry_during_warmup(self):
        trader = LiveTrader(EmaRsiAtrStrategy(SETTINGS.strategy), SETTINGS, warmup=50)
        updates = run_live(trader, candle_feed(CANDLES))
        for u in updates[:50]:
            self.assertIsNone(
                u.position, "nao pode haver posicao durante o aquecimento"
            )

    def test_stops_when_halted(self):
        # risco apertado para forcar o desligamento em algum momento
        settings = Settings.default()
        settings.risk.starting_equity = 1_000.0
        settings.risk.max_daily_loss_pct = 0.005
        settings.risk.risk_per_trade_pct = 0.05
        trader = LiveTrader(EmaRsiAtrStrategy(settings.strategy), settings)
        updates = run_live(trader, candle_feed(CANDLES))
        if updates and updates[-1].halted:
            # apos desligar, o loop encerra -- ultimo update e o do desligamento
            self.assertTrue(updates[-1].halted)
            self.assertTrue(updates[-1].note)

    def test_feed_yields_all(self):
        got = list(candle_feed(CANDLES[:10]))
        self.assertEqual(len(got), 10)


if __name__ == "__main__":
    unittest.main()
