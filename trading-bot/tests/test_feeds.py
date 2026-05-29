"""Testes dos adaptadores de feed (replay e ccxt ao vivo, com fetch falso)."""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bot import Settings, generate_synthetic_candles  # noqa: E402
from bot.feeds import CcxtLiveFeed, ReplayFeed, _row_to_candle  # noqa: E402
from bot.live import LiveTrader, run_live  # noqa: E402
from bot.strategy import EmaRsiAtrStrategy  # noqa: E402


def _row(ts_s, price):
    # linha OHLCV no formato ccxt (timestamp em MILISSEGUNDOS)
    return [ts_s * 1000, price, price + 1, price - 1, price, 10.0]


class TestReplayFeed(unittest.TestCase):
    def test_replays_all(self):
        candles = generate_synthetic_candles(n_days=5, seed=1)
        feed = ReplayFeed(candles)
        self.assertEqual(list(feed.stream()), candles)

    def test_drives_live_trader(self):
        candles = generate_synthetic_candles(n_days=10, seed=2)
        trader = LiveTrader(EmaRsiAtrStrategy(Settings.default().strategy), Settings.default())
        updates = run_live(trader, ReplayFeed(candles).stream())
        self.assertEqual(len(updates), len(candles))


class TestCcxtLiveFeed(unittest.TestCase):
    def test_only_closed_candles_no_duplicates(self):
        # duas "rodadas" de polling; o ULTIMO de cada rodada esta se formando
        polls = [
            [_row(300, 100), _row(600, 101), _row(900, 102)],  # 900 forma-se
            [_row(600, 101), _row(900, 102), _row(1200, 103)],  # 1200 forma-se
            [_row(900, 102), _row(1200, 103), _row(1500, 104)],
        ]
        state = {"i": 0}

        def fake_fetch():
            rows = polls[min(state["i"], len(polls) - 1)]
            state["i"] += 1
            return rows

        feed = CcxtLiveFeed(
            fetch=fake_fetch, poll_seconds=0, max_candles=3, sleep=lambda _s: None
        )
        got = list(feed.stream())
        ts = [c.ts for c in got]
        # candles fechados em ordem, sem repetir, sem o que estava se formando
        self.assertEqual(ts, [300, 600, 900])
        self.assertTrue(all(ts[k] < ts[k + 1] for k in range(len(ts) - 1)))

    def test_row_conversion_ms_to_s(self):
        c = _row_to_candle(_row(300, 120.5))
        self.assertEqual(c.ts, 300)  # ms -> s
        self.assertEqual(c.close, 120.5)


if __name__ == "__main__":
    unittest.main()
