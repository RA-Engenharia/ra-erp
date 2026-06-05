"""Gestao da operacao ABERTA -- acompanha um trade depois que voce entrou.

Calcula o lucro/prejuizo ao vivo, diz se ja bateu o stop ou o alvo, e sugere
mover o stop para proteger o lucro (trailing) quando a operacao anda a favor.

Regra do trailing (simples e sa): a "unidade de risco" R = distancia da entrada
ate o stop inicial. Quando o lucro chega a +1R, sugere subir o stop para pelo
menos o ZERO A ZERO (break-even) e ir acompanhando o preco a 1R de distancia.
Assim voce nao transforma um lucro em prejuizo.
"""

from __future__ import annotations

import json
import os
import time


def trade_status(trade: dict, price: float) -> dict:
    """Estado atual de um trade dado o preco. Nao altera o trade."""
    action = trade["action"]
    entry = float(trade["entry"])
    stop = float(trade["stop"])
    take = float(trade["take"])
    qty = float(trade.get("qty") or 0)
    R = abs(entry - stop) or 1e-9

    if action == "long":
        pnl = (price - entry) * qty
        profit_r = (price - entry) / R
        status = "alvo" if price >= take else ("stop" if price <= stop else "aberta")
        suggested = stop
        if profit_r >= 1:
            suggested = max(stop, entry, price - R)  # trava no minimo o break-even
    else:  # short
        pnl = (entry - price) * qty
        profit_r = (entry - price) / R
        status = "alvo" if price <= take else ("stop" if price >= stop else "aberta")
        suggested = stop
        if profit_r >= 1:
            suggested = min(stop, entry, price + R)

    return {
        "price": price,
        "pnl": round(pnl, 2),
        "profit_r": round(profit_r, 2),
        "status": status,
        "suggested_stop": round(suggested, 2),
        "move_stop": abs(suggested - stop) > 1e-6,
    }


# ---- persistencia (lista de trades abertos em JSON) ----
def load_trades(path: str) -> list[dict]:
    if not os.path.exists(path):
        return []
    try:
        with open(path) as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return []


def save_trades(path: str, trades: list[dict]) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(trades, f)


def add_trade(path: str, trade: dict) -> dict:
    trades = load_trades(path)
    trade = dict(trade)
    trade["id"] = str(int(time.time() * 1000))
    trades.append(trade)
    save_trades(path, trades)
    return trade


def remove_trade(path: str, trade_id: str) -> None:
    trades = [t for t in load_trades(path) if str(t.get("id")) != str(trade_id)]
    save_trades(path, trades)
