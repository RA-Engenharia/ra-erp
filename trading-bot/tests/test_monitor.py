"""Testes do painel de acompanhamento (monitor)."""

import csv
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bot.monitor import format_dashboard, load_trades_csv, summarize  # noqa: E402


def _write_csv(path, rows):
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["entry", "exit", "side", "qty", "pnl", "reason", "exit_ts"])
        for r in rows:
            w.writerow(r)


class TestMonitor(unittest.TestCase):
    def test_summarize_basic_metrics(self):
        # 3 trades: +100, -50, +30  -> pnl=80, 2 wins/3, PF=130/50=2.6
        trades_rows = [
            [100, 110, "long", 1, 100, "take", 10],
            [110, 105, "long", 1, -50, "stop", 20],
            [105, 108, "short", 1, 30, "take", 30],
        ]
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "t.csv")
            _write_csv(p, trades_rows)
            trades = load_trades_csv(p)
            self.assertEqual(len(trades), 3)
            m = summarize(trades, starting_equity=1000.0)

        self.assertEqual(m["n_trades"], 3)
        self.assertAlmostEqual(m["win_rate"], 2 / 3)
        self.assertAlmostEqual(m["total_pnl"], 80.0)
        self.assertAlmostEqual(m["final_equity"], 1080.0)
        self.assertAlmostEqual(m["profit_factor"], 130.0 / 50.0)
        self.assertGreater(m["max_drawdown"], 0)  # houve uma queda no meio
        self.assertEqual(m["reasons"]["take"], 2)
        self.assertEqual(m["reasons"]["stop"], 1)

    def test_dashboard_renders_and_warns_small_sample(self):
        trades_rows = [[100, 110, "long", 1, 10, "take", 1]]
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "t.csv")
            _write_csv(p, trades_rows)
            m = summarize(load_trades_csv(p))
        out = format_dashboard(m)
        self.assertIn("PAINEL DO ENSAIO", out)
        self.assertIn("AMOSTRA PEQUENA", out)  # 1 trade -> aviso

    def test_profit_factor_all_wins(self):
        trades_rows = [[1, 2, "long", 1, 10, "take", i] for i in range(3)]
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "t.csv")
            _write_csv(p, trades_rows)
            m = summarize(load_trades_csv(p))
        self.assertEqual(m["profit_factor"], float("inf"))
        self.assertEqual(m["max_drawdown"], 0.0)


if __name__ == "__main__":
    unittest.main()
