"""Extrato de sinais -- registra cada sinal e avalia se teria dado certo.

Salva os sinais num CSV e, depois, olha o que o preco fez DEPOIS de cada um:
bateu o ALVO (acerto) ou o STOP (erro)? E o jeito honesto de validar o robo
sem dinheiro real -- voce ve o placar dos sinais que ele deu.
"""

from __future__ import annotations

import csv
import os

FIELDS = ["ts", "datetime", "symbol", "tf", "action", "entry", "stop", "take", "qty", "reason"]


def append_signal(path: str, rec: dict, seen: set) -> bool:
    """Anexa um sinal ao CSV. Evita duplicar pela chave (symbol,tf,ts,action)."""
    key = (rec.get("symbol"), rec.get("tf"), int(rec.get("ts", 0)), rec.get("action"))
    if key in seen:
        return False
    seen.add(key)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    new_file = not os.path.exists(path)
    with open(path, "a", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        if new_file:
            w.writeheader()
        w.writerow({k: rec.get(k) for k in FIELDS})
    return True


def read_signals(path: str) -> list[dict]:
    if not os.path.exists(path):
        return []
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def seen_keys(path: str) -> set:
    s = set()
    for r in read_signals(path):
        try:
            s.add((r["symbol"], r["tf"], int(r["ts"]), r["action"]))
        except (KeyError, ValueError):
            continue
    return s


def evaluate_outcome(action: str, entry: float, stop: float, take: float,
                     future: list[tuple[float, float]]) -> str:
    """Olha os candles DEPOIS do sinal (lista de (high, low)) e devolve:
       'alvo' (acertou), 'stop' (errou) ou 'aberto' (ainda nao resolveu).

    Conservador: se stop e alvo caem no mesmo candle, assume o STOP primeiro
    (pior caso) -- igual ao motor de backtest.
    """
    for hi, lo in future:
        if action == "long":
            if lo <= stop:
                return "stop"
            if hi >= take:
                return "alvo"
        else:  # short
            if hi >= stop:
                return "stop"
            if lo <= take:
                return "alvo"
    return "aberto"
