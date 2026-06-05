"""Testes da gestao de operacao aberta."""

import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bot.trademanager import (  # noqa: E402
    add_trade,
    load_trades,
    remove_trade,
    trade_status,
)


class TestTradeStatus(unittest.TestCase):
    def test_long_pnl_and_hits(self):
        t = {"action": "long", "entry": 40, "stop": 39, "take": 42, "qty": 100}
        # preco subiu para 41 -> lucro 100, ainda aberta
        s = trade_status(t, 41)
        self.assertAlmostEqual(s["pnl"], 100)
        self.assertEqual(s["status"], "aberta")
        # bateu o alvo
        self.assertEqual(trade_status(t, 42)["status"], "alvo")
        # bateu o stop
        self.assertEqual(trade_status(t, 39)["status"], "stop")

    def test_long_trailing_after_1R(self):
        t = {"action": "long", "entry": 40, "stop": 39, "take": 45, "qty": 100}  # R = 1
        # +0.5R: ainda nao sugere mover
        self.assertFalse(trade_status(t, 40.5)["move_stop"])
        # +1.5R (preco 41.5): sugere subir o stop (no minimo break-even)
        s = trade_status(t, 41.5)
        self.assertTrue(s["move_stop"])
        self.assertGreaterEqual(s["suggested_stop"], 40)  # >= entrada (break-even)

    def test_short_pnl_and_trailing(self):
        t = {"action": "short", "entry": 40, "stop": 41, "take": 35, "qty": 100}  # R = 1
        s = trade_status(t, 39)  # caiu 1 -> lucro 100, +1R
        self.assertAlmostEqual(s["pnl"], 100)
        self.assertTrue(s["move_stop"])
        self.assertLessEqual(s["suggested_stop"], 40)  # desce o stop p/ proteger


class TestPersistence(unittest.TestCase):
    def test_add_list_remove(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "open_trades.json")
            t = add_trade(p, {"action": "long", "entry": 40, "stop": 39, "take": 42, "qty": 10, "symbol": "X"})
            self.assertIn("id", t)
            self.assertEqual(len(load_trades(p)), 1)
            remove_trade(p, t["id"])
            self.assertEqual(load_trades(p), [])


if __name__ == "__main__":
    unittest.main()
