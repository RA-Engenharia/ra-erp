"""Testes do modulo de risco -- a parte que protege seu dinheiro.

Rode de dentro da pasta trading-bot:
    python3 -m unittest discover -s tests
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bot.config import RiskConfig  # noqa: E402
from bot.risk import RiskManager  # noqa: E402


class TestPositionSizing(unittest.TestCase):
    def test_risk_per_trade_is_respected(self):
        rm = RiskManager(RiskConfig(starting_equity=10_000, risk_per_trade_pct=0.01))
        # arriscar 1% de 10.000 = R$100; stop a 2 pontos -> 50 unidades
        qty = rm.position_size(entry=100.0, stop=98.0)
        self.assertAlmostEqual(qty, 50.0)
        # a perda no stop deve ser exatamente o valor arriscado
        self.assertAlmostEqual(qty * (100.0 - 98.0), 100.0)

    def test_max_position_cap(self):
        rm = RiskManager(
            RiskConfig(
                starting_equity=10_000,
                risk_per_trade_pct=0.01,
                max_position_pct=0.10,  # exposicao max = R$1.000
            )
        )
        # stop minusculo -> tamanho gigante, mas o teto de exposicao limita
        qty = rm.position_size(entry=100.0, stop=99.99)
        self.assertAlmostEqual(qty, 10.0)  # 1.000 / 100

    def test_zero_when_no_stop_distance(self):
        rm = RiskManager(RiskConfig(starting_equity=10_000))
        self.assertEqual(rm.position_size(entry=100.0, stop=100.0), 0.0)


class TestRiskGuards(unittest.TestCase):
    def test_daily_loss_limit_blocks_trading(self):
        rm = RiskManager(
            RiskConfig(starting_equity=10_000, max_daily_loss_pct=0.03)
        )
        rm.begin()
        rm.on_trade_closed(-250)  # -2,5%
        self.assertTrue(rm.can_trade()[0])
        rm.on_trade_closed(-60)  # total -3,1% -> estoura o limite do dia
        self.assertFalse(rm.can_trade()[0])

    def test_new_day_resets_daily_limit(self):
        rm = RiskManager(
            RiskConfig(starting_equity=10_000, max_daily_loss_pct=0.03)
        )
        rm.begin()
        rm.on_trade_closed(-310)
        self.assertFalse(rm.can_trade()[0])
        rm.on_new_day()
        self.assertTrue(rm.can_trade()[0])

    def test_drawdown_circuit_breaker_halts_bot(self):
        rm = RiskManager(
            RiskConfig(starting_equity=10_000, max_total_drawdown_pct=0.20)
        )
        rm.begin()
        rm.on_trade_closed(-2_000)  # -20% do topo dispara o disjuntor
        self.assertTrue(rm.halted)
        self.assertFalse(rm.can_trade()[0])

    def test_halt_persists_across_days(self):
        rm = RiskManager(
            RiskConfig(starting_equity=10_000, max_total_drawdown_pct=0.20)
        )
        rm.begin()
        rm.on_trade_closed(-2_500)
        rm.on_new_day()
        self.assertFalse(rm.can_trade()[0])  # disjuntor nao reseta no novo dia


if __name__ == "__main__":
    unittest.main()
