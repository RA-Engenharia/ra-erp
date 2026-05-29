"""Gestao de risco -- o CORACAO do robo.

A filosofia: preservar capital vem antes de lucrar. Este modulo decide
quanto arriscar e, principalmente, QUANDO NAO OPERAR. As travas aqui sao
o que falta para os 97% que perdem dinheiro no day trade.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .config import RiskConfig


@dataclass
class RiskManager:
    cfg: RiskConfig
    equity: float = field(init=False)
    peak_equity: float = field(init=False)
    day_start_equity: float = field(init=False)
    day_pnl: float = field(init=False, default=0.0)
    halted: bool = field(init=False, default=False)
    halt_reason: str = field(init=False, default="")

    def __post_init__(self) -> None:
        self.cfg.validate()
        self.equity = self.cfg.starting_equity
        self.peak_equity = self.cfg.starting_equity
        self.day_start_equity = self.cfg.starting_equity

    # --- ciclo de vida ---------------------------------------------------
    def begin(self) -> None:
        self.equity = self.cfg.starting_equity
        self.peak_equity = self.cfg.starting_equity
        self.day_start_equity = self.cfg.starting_equity
        self.day_pnl = 0.0
        self.halted = False
        self.halt_reason = ""

    def on_new_day(self) -> None:
        """Zera os contadores diarios (limite de perda do dia volta a valer)."""
        self.day_start_equity = self.equity
        self.day_pnl = 0.0

    # --- decisoes --------------------------------------------------------
    def position_size(self, entry: float, stop: float) -> float:
        """Quantidade tal que a perda no stop = risk_per_trade_pct do capital.

        Respeita o teto de exposicao (max_position_pct). Retorna 0 se nao der.
        """
        per_unit_risk = abs(entry - stop)
        if per_unit_risk <= 0 or entry <= 0:
            return 0.0
        risk_amount = self.equity * self.cfg.risk_per_trade_pct
        qty = risk_amount / per_unit_risk
        max_notional = self.equity * self.cfg.max_position_pct
        if qty * entry > max_notional:
            qty = max_notional / entry
        return max(qty, 0.0)

    def can_trade(self) -> tuple[bool, str]:
        """Pode abrir nova posicao agora? Aplica as travas obrigatorias."""
        if self.halted:
            return False, f"robo desligado: {self.halt_reason}"
        daily_loss_limit = self.day_start_equity * self.cfg.max_daily_loss_pct
        if self.day_pnl <= -daily_loss_limit:
            return False, "limite de perda diaria atingido"
        return True, "ok"

    def on_trade_closed(self, pnl: float) -> None:
        """Atualiza capital, drawdown e dispara o disjuntor se necessario."""
        self.equity += pnl
        self.day_pnl += pnl
        if self.equity > self.peak_equity:
            self.peak_equity = self.equity
        drawdown = (
            (self.peak_equity - self.equity) / self.peak_equity
            if self.peak_equity > 0
            else 0.0
        )
        if drawdown >= self.cfg.max_total_drawdown_pct:
            self.halted = True
            self.halt_reason = (
                f"drawdown {drawdown:.1%} >= limite "
                f"{self.cfg.max_total_drawdown_pct:.0%}"
            )

    @property
    def drawdown(self) -> float:
        if self.peak_equity <= 0:
            return 0.0
        return (self.peak_equity - self.equity) / self.peak_equity
