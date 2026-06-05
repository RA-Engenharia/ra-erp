"""Testes do extrato de sinais."""

import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bot.signallog import append_signal, evaluate_outcome, read_signals, seen_keys  # noqa: E402


class TestSignalLog(unittest.TestCase):
    def test_append_dedup_and_read(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "sub", "signal_log.csv")
            seen = set()
            rec = {"ts": 100, "datetime": "x", "symbol": "PETR4.SA", "tf": "15m",
                   "action": "long", "entry": 40, "stop": 39, "take": 42, "qty": 10, "reason": "y"}
            self.assertTrue(append_signal(p, rec, seen))
            self.assertFalse(append_signal(p, rec, seen))  # duplicado nao entra
            rows = read_signals(p)
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["symbol"], "PETR4.SA")
            # seen_keys reconstroi do arquivo
            self.assertIn(("PETR4.SA", "15m", 100, "long"), seen_keys(p))

    def test_outcome_long(self):
        # comprado em 40, stop 39, alvo 42
        # candle que sobe ate 42 -> alvo
        self.assertEqual(evaluate_outcome("long", 40, 39, 42, [(42.5, 40.1)]), "alvo")
        # candle que cai ate 39 -> stop
        self.assertEqual(evaluate_outcome("long", 40, 39, 42, [(40.5, 38.9)]), "stop")
        # nada toca -> aberto
        self.assertEqual(evaluate_outcome("long", 40, 39, 42, [(41, 39.5)]), "aberto")
        # stop e alvo no mesmo candle -> conservador: stop
        self.assertEqual(evaluate_outcome("long", 40, 39, 42, [(42.5, 38.5)]), "stop")

    def test_outcome_short(self):
        # vendido em 40, stop 41, alvo 38
        self.assertEqual(evaluate_outcome("short", 40, 41, 38, [(40.2, 37.9)]), "alvo")
        self.assertEqual(evaluate_outcome("short", 40, 41, 38, [(41.1, 39.5)]), "stop")
        self.assertEqual(evaluate_outcome("short", 40, 41, 38, [(40.5, 39)]), "aberto")


if __name__ == "__main__":
    unittest.main()
