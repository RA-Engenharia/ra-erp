"""Configuracao central -- principalmente os PARAMETROS DE RISCO.

Este eh o arquivo mais importante do projeto. Os valores padrao aqui sao
deliberadamente conservadores. Mexer neles e o que separa "preservar capital"
de "quebrar a conta".
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class RiskConfig:
    """Travas de risco -- aplicadas como regras obrigatorias em risk.py."""

    starting_equity: float = 5_000.0
    # Fracao do capital arriscada por trade (distancia ate o stop). 0.01 = 1%.
    risk_per_trade_pct: float = 0.01
    # Perda maxima no dia. Atingiu -> para de operar ate o proximo dia.
    max_daily_loss_pct: float = 0.03
    # Drawdown maximo desde o topo. Atingiu -> DESLIGA o robo (disjuntor).
    max_total_drawdown_pct: float = 0.20
    # Exposicao maxima (notional) por posicao, como fracao do capital.
    max_position_pct: float = 1.00
    # Multiplo de ATR para o stop e razao risco:retorno do alvo.
    stop_atr_mult: float = 1.5
    reward_risk: float = 1.5

    def validate(self) -> None:
        assert self.starting_equity > 0, "capital inicial deve ser > 0"
        assert 0 < self.risk_per_trade_pct <= 0.05, (
            "risco por trade fora da faixa sensata (0 < x <= 5%)"
        )
        assert 0 < self.max_daily_loss_pct <= 0.20
        assert 0 < self.max_total_drawdown_pct <= 0.50
        assert self.stop_atr_mult > 0 and self.reward_risk > 0


@dataclass
class CostConfig:
    """Custos de transacao. Ignorar isso eh a fantasia nº1 de quem perde."""

    # Comissao + taxas por lado (entrada e saida), como fracao do notional.
    commission_pct: float = 0.0005  # 0.05%
    # Slippage estimado por lado (execucao pior que o preco visto).
    slippage_pct: float = 0.0003  # 0.03%


@dataclass
class StrategyConfig:
    ema_fast: int = 9
    ema_slow: int = 21
    rsi_period: int = 14
    atr_period: int = 14
    rsi_long_min: float = 40.0
    rsi_long_max: float = 70.0
    rsi_short_min: float = 30.0
    rsi_short_max: float = 60.0
    allow_short: bool = True


@dataclass
class Settings:
    risk: RiskConfig
    costs: CostConfig
    strategy: StrategyConfig

    @staticmethod
    def default() -> "Settings":
        s = Settings(RiskConfig(), CostConfig(), StrategyConfig())
        s.risk.validate()
        return s
