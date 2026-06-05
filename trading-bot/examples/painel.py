"""Painel web -- back-end (Flask) que conecta o cerebro a interface no navegador.

    cd trading-bot
    python3 examples/painel.py
    # abra http://127.0.0.1:5000 no navegador

Expoe uma API JSON:
  /api/candles    -> OHLC recente para o grafico
  /api/calibrate  -> monta o cerebro para o ativo (1-2 min; guarda em cache)
  /api/signal     -> sinal atual (rapido; reusa o cerebro calibrado)
  /api/carteira   -> decisao do cerebro na cesta de acoes (lento)

NAO envia ordem. So mostra sinais. Voce executa na corretora.
"""

from __future__ import annotations

import os
import sys
import threading

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask, jsonify, request, send_from_directory  # noqa: E402

from dataclasses import replace  # noqa: E402

from bot import EmaRsiAtrStrategy, Settings  # noqa: E402
from bot.brain import build_brain  # noqa: E402
from bot.risk import RiskManager  # noqa: E402
from bot.strategies import (  # noqa: E402
    BollingerStrategy,
    BreakdownStrategy,
    BreakoutStrategy,
    DowntrendStrategy,
    MacdStrategy,
    MeanReversionStrategy,
    RegimeFilteredStrategy,
    RocStrategy,
    Rsi2Strategy,
    SuperTrendStrategy,
    TrendEmaStrategy,
)
from bot.signallog import append_signal, evaluate_outcome, read_signals, seen_keys  # noqa: E402
from bot.validation import StrategySpec  # noqa: E402

from datetime import datetime, timezone  # noqa: E402

WEB_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "painel_web")
LOG_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "signal_log.csv")
app = Flask(__name__, static_folder=None)

_brains: dict[tuple, dict] = {}   # (symbol, tf) -> {brain, settings}
_lock = threading.Lock()
_seen = seen_keys(LOG_PATH)        # sinais ja registrados (evita duplicar)
CARTEIRA = ["B3SA3.SA", "PETR4.SA", "BBDC4.SA", "WEGE3.SA", "ITUB4.SA", "ABEV3.SA", "BBAS3.SA"]


def _period(tf: str) -> str:
    if tf in ("5m", "15m", "30m"):
        return "30d"
    if tf in ("1h", "60m", "90m"):
        return "180d"
    return "2y"


def build_specs(settings: Settings) -> list[StrategySpec]:
    ema_rsi = lambda p: EmaRsiAtrStrategy(replace(settings.strategy, **p))
    tr = lambda b: (lambda p: RegimeFilteredStrategy(b(p), mode="trend"))
    return [
        StrategySpec("EMA+RSI", tr(ema_rsi), {"ema_fast": [5, 9], "ema_slow": [21, 30]}),
        StrategySpec("EMA+tend", tr(TrendEmaStrategy), {"ema_fast": [5, 9], "trend_ema": [100, 200]}),
        StrategySpec("MACD", tr(MacdStrategy), {"fast": [8, 12], "slow": [21, 26]}),
        StrategySpec("Breakout", tr(BreakoutStrategy), {"channel": [10, 20, 40]}),
        StrategySpec("SuperTrend", SuperTrendStrategy, {"period": [7, 10], "mult": [2.0, 3.0]}),
        StrategySpec("Bollinger", BollingerStrategy, {"period": [14, 20], "k": [2.0, 2.5]}),
        StrategySpec("Reversao", MeanReversionStrategy, {"oversold": [20, 30]}),
        StrategySpec("ROC", RocStrategy, {"roc_period": [9, 12], "threshold": [0.0, 0.5]}),
        StrategySpec("RSI-2", Rsi2Strategy, {"oversold": [5, 10], "trend_sma": [100, 200]}),
        StrategySpec("Breakdown", BreakdownStrategy, {"channel": [10, 20, 40]}),
        StrategySpec("Downtrend", DowntrendStrategy, {"ema_fast": [5, 9], "trend_ema": [100, 200]}),
    ]


def _make_settings(tf: str, capital: float) -> Settings:
    s = Settings.default()
    s.risk.starting_equity = capital
    s.day_trade = tf != "1d"  # diario = swing
    return s


@app.route("/")
def index():
    return send_from_directory(WEB_DIR, "index.html")


@app.route("/api/candles")
def candles():
    from bot.sources.yfinance_source import load_yfinance
    symbol = request.args.get("symbol", "PETR4.SA")
    tf = request.args.get("tf", "15m")
    try:
        cs = load_yfinance(symbol, period=_period(tf), interval=tf)
    except Exception as exc:
        return jsonify({"error": str(exc)[:120]}), 400
    data = [
        {"time": int(c.ts), "open": c.open, "high": c.high, "low": c.low, "close": c.close}
        for c in cs[-400:]
    ]
    return jsonify({"candles": data, "symbol": symbol, "tf": tf})


@app.route("/api/calibrate")
def calibrate():
    from bot.sources.yfinance_source import load_yfinance
    symbol = request.args.get("symbol", "PETR4.SA")
    tf = request.args.get("tf", "15m")
    capital = float(request.args.get("capital", 5000))
    with _lock:
        try:
            settings = _make_settings(tf, capital)
            cs = load_yfinance(symbol, period=_period(tf), interval=tf)[:-1]
            if len(cs) < 250:
                return jsonify({"error": f"poucos dados ({len(cs)})"}), 400
            brain, diags = build_brain(cs, settings, build_specs(settings), n_folds=3)
            _brains[(symbol, tf)] = {"brain": brain, "settings": settings}
        except Exception as exc:
            return jsonify({"error": str(exc)[:160]}), 400
    committee = [
        {
            "name": d.name, "weight": round(d.weight, 1),
            "folds": f"{d.folds_positive}/{d.n_folds}",
            "exp": round(d.avg_oos_expectancy, 2), "robust": d.robust,
        }
        for d in sorted(diags, key=lambda x: x.weight, reverse=True)
    ]
    return jsonify({"committee": committee, "active": sum(1 for d in diags if d.weight > 0)})


def _signal_card(symbol, tf, capital):
    from bot.sources.yfinance_source import load_yfinance
    key = (symbol, tf)
    if key not in _brains:
        return {"action": "uncalibrated"}
    entry = _brains[key]
    brain, settings = entry["brain"], entry["settings"]
    settings.risk.starting_equity = capital
    cs = load_yfinance(symbol, period=_period(tf), interval=tf)[:-1]
    brain.prepare(cs)
    sig = brain.signal(len(cs) - 1)
    price, ts = cs[-1].close, int(cs[-1].ts)
    if sig.action in ("long", "short"):
        risk = RiskManager(settings.risk)
        risk.begin()
        qty = int(risk.position_size(price, sig.stop))
        dist = abs(price - sig.stop)
        # registra o sinal no extrato (uma vez por candle/acao)
        append_signal(LOG_PATH, {
            "ts": ts,
            "datetime": datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%d/%m/%Y %H:%M"),
            "symbol": symbol, "tf": tf, "action": sig.action,
            "entry": round(price, 2), "stop": round(sig.stop, 2), "take": round(sig.take, 2),
            "qty": qty, "reason": sig.reason,
        }, _seen)
        return {
            "action": sig.action, "entry": price, "stop": sig.stop, "take": sig.take,
            "qty": qty, "risk_reais": round(qty * dist, 2),
            "risk_pct": dist / price if price else 0,
            "reward_pct": abs(sig.take - price) / price if price else 0,
            "rr": (abs(sig.take - price) / dist) if dist else 0,
            "reason": sig.reason, "price": price, "ts": ts,
        }
    return {"action": "wait", "price": price, "ts": ts}


@app.route("/api/signal")
def signal():
    symbol = request.args.get("symbol", "PETR4.SA")
    tf = request.args.get("tf", "15m")
    capital = float(request.args.get("capital", 5000))
    try:
        return jsonify(_signal_card(symbol, tf, capital))
    except Exception as exc:
        return jsonify({"error": str(exc)[:160]}), 400


@app.route("/api/carteira")
def carteira():
    from bot.sources.yfinance_source import load_yfinance
    capital = float(request.args.get("capital", 5000))
    out = []
    for sym in CARTEIRA:
        try:
            with _lock:
                settings = _make_settings("1d", capital)
                cs = load_yfinance(sym, period="5y", interval="1d")[:-1]
                brain, diags = build_brain(cs, settings, build_specs(settings), n_folds=3)
            brain.prepare(cs)
            sig = brain.signal(len(cs) - 1)
            decis = {"long": "COMPRAR", "short": "VENDER"}.get(sig.action, "AGUARDAR")
            out.append({"symbol": sym.replace(".SA", ""), "decision": decis,
                        "active": sum(1 for d in diags if d.weight > 0)})
        except Exception as exc:
            out.append({"symbol": sym, "decision": "erro", "active": 0, "error": str(exc)[:40]})
    return jsonify({"carteira": out})


@app.route("/api/indicators")
def indicators_api():
    from bot import indicators as ind
    from bot.sources.yfinance_source import load_yfinance
    symbol = request.args.get("symbol", "PETR4.SA")
    tf = request.args.get("tf", "15m")
    try:
        cs = load_yfinance(symbol, period=_period(tf), interval=tf)
    except Exception as exc:
        return jsonify({"error": str(exc)[:120]}), 400
    closes = [c.close for c in cs]
    highs = [c.high for c in cs]
    lows = [c.low for c in cs]
    i = len(closes) - 1
    price = closes[i]
    atr = ind.atr(highs, lows, closes, 14)[i]
    e50 = ind.ema(closes, 50)[i]
    return jsonify({
        "price": price,
        "rsi": ind.rsi(closes, 14)[i],
        "atr_pct": (atr / price) if atr else None,
        "trend_strength": ind.efficiency_ratio(closes, 10)[i],
        "ema9": ind.ema(closes, 9)[i],
        "ema21": ind.ema(closes, 21)[i],
        "ema50": e50,
        "above_ema50": (price > e50) if e50 else None,
        "change": (closes[i] / closes[i - 1] - 1) if i > 0 else 0,
    })


@app.route("/api/mtf")
def mtf():
    from bot import indicators as ind
    from bot.sources.yfinance_source import load_yfinance
    symbol = request.args.get("symbol", "PETR4.SA")
    out = []
    for tf in ("15m", "1h", "1d"):
        trend = "—"
        try:
            cs = load_yfinance(symbol, period=_period(tf), interval=tf)
            closes = [c.close for c in cs]
            i = len(closes) - 1
            ef, es, el = ind.ema(closes, 9)[i], ind.ema(closes, 21)[i], ind.ema(closes, 50)[i]
            if None not in (ef, es, el):
                if ef > es and closes[i] > el:
                    trend = "ALTA"
                elif ef < es and closes[i] < el:
                    trend = "BAIXA"
                else:
                    trend = "LATERAL"
        except Exception:
            trend = "—"
        out.append({"tf": tf, "trend": trend})
    return jsonify({"mtf": out})


@app.route("/api/backtest")
def backtest():
    from bot.backtest import run_backtest
    from bot.sources.yfinance_source import load_yfinance
    symbol = request.args.get("symbol", "PETR4.SA")
    tf = request.args.get("tf", "15m")
    capital = float(request.args.get("capital", 5000))
    key = (symbol, tf)
    if key not in _brains:
        return jsonify({"error": "calibre primeiro (Analisar)"}), 400
    settings = _brains[key]["settings"]
    settings.risk.starting_equity = capital
    try:
        cs = load_yfinance(symbol, period=_period(tf), interval=tf)[:-1]
        res = run_backtest(cs, _brains[key]["brain"], settings)
    except Exception as exc:
        return jsonify({"error": str(exc)[:160]}), 400
    m = res.metrics
    eq = res.equity_curve
    step = max(1, len(eq) // 240)
    curve = [{"time": int(t), "value": round(v, 2)} for j, (t, v) in enumerate(eq) if j % step == 0]
    pf = m.get("profit_factor", 0)
    return jsonify({
        "metrics": {
            "total_return": m.get("total_return", 0),
            "final_equity": res.final_equity,
            "win_rate": m.get("win_rate", 0),
            "profit_factor": (None if pf == float("inf") else round(pf, 2)),
            "max_drawdown": m.get("max_drawdown", 0),
            "expectancy": round(m.get("expectancy", 0), 2),
            "sharpe": round(m.get("sharpe", 0), 2),
            "n_trades": m.get("n_trades", 0),
        },
        "curve": curve, "start": capital,
    })


@app.route("/api/extrato")
def extrato():
    from bot.sources.yfinance_source import load_yfinance
    sigs = read_signals(LOG_PATH)
    groups: dict[tuple, list] = {}
    for s in sigs:
        groups.setdefault((s["symbol"], s["tf"]), []).append(s)
    cache: dict[tuple, list] = {}
    out = []
    acertos = erros = abertos = 0
    for (sym, tf), items in groups.items():
        try:
            if (sym, tf) not in cache:
                cs = load_yfinance(sym, period=_period(tf), interval=tf)
                cache[(sym, tf)] = [(int(c.ts), c.high, c.low) for c in cs]
            data = cache[(sym, tf)]
        except Exception:
            data = []
        for s in items:
            ts = int(s["ts"])
            fut = [(hi, lo) for (t, hi, lo) in data if t > ts]
            res = evaluate_outcome(s["action"], float(s["entry"]), float(s["stop"]),
                                   float(s["take"]), fut)
            if res == "alvo":
                acertos += 1
            elif res == "stop":
                erros += 1
            else:
                abertos += 1
            out.append({
                "datetime": s.get("datetime", ""), "symbol": sym.replace(".SA", ""),
                "tf": tf, "action": s["action"], "entry": float(s["entry"]),
                "stop": float(s["stop"]), "take": float(s["take"]), "result": res, "ts": ts,
            })
    out.sort(key=lambda x: x["ts"], reverse=True)
    fechados = acertos + erros
    return jsonify({
        "signals": out[:150], "acertos": acertos, "erros": erros, "abertos": abertos,
        "taxa": (acertos / fechados) if fechados else None, "total": len(sigs),
    })


def main():
    print("=" * 56)
    print("  PAINEL DO ROBO -- abra no navegador:  http://127.0.0.1:5000")
    print("  (Ctrl+C aqui para encerrar o painel)")
    print("=" * 56)
    app.run(host="127.0.0.1", port=5000, threaded=True)


if __name__ == "__main__":
    main()
