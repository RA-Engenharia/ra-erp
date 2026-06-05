"""VIGIA -- fica rodando e AVISA quando aparece um sinal de operacao.

    cd trading-bot
    python3 examples/vigia.py                      # PETR4.SA 15m, R$ 5.000
    python3 examples/vigia.py VALE3.SA 15m 10000

Calibra o cerebro UMA vez (1-2 min) e depois fica vigiando o ativo em tempo
(quase) real. A cada novo candle fechado, reavalia. Quando surge COMPRAR ou
VENDER, dispara um ALERTA na tela (com um bip) e mostra o cartao de operacao
com stop, alvo, quantidade e risco. Enquanto nao ha sinal, fica quieto.

NAO envia ordem -- so avisa. Voce decide e executa. Ctrl+C para parar.
Lembrete honesto: day trade intraday foi onde os testes NAO acharam vantagem.
"""

from __future__ import annotations

import os
import sys
from dataclasses import replace
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

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
    SuperTrendStrategy,
    TrendEmaStrategy,
)
from bot.validation import StrategySpec  # noqa: E402


def trend(base):
    return lambda p: RegimeFilteredStrategy(base(p), mode="trend")


def build_specs(settings: Settings) -> list[StrategySpec]:
    ema_rsi = lambda p: EmaRsiAtrStrategy(replace(settings.strategy, **p))
    return [
        StrategySpec("EMA+RSI", trend(ema_rsi), {"ema_fast": [5, 9], "ema_slow": [21, 30]}),
        StrategySpec("EMA+tend", trend(TrendEmaStrategy), {"ema_fast": [5, 9], "trend_ema": [100, 200]}),
        StrategySpec("MACD", trend(MacdStrategy), {"fast": [8, 12], "slow": [21, 26]}),
        StrategySpec("Breakout", trend(BreakoutStrategy), {"channel": [10, 20, 40]}),
        StrategySpec("SuperTrend", SuperTrendStrategy, {"period": [7, 10], "mult": [2.0, 3.0]}),
        StrategySpec("Bollinger", BollingerStrategy, {"period": [14, 20], "k": [2.0, 2.5]}),
        StrategySpec("Reversao", MeanReversionStrategy, {"oversold": [20, 30]}),
        StrategySpec("ROC", RocStrategy, {"roc_period": [9, 12], "threshold": [0.0, 0.5]}),
        StrategySpec("Breakdown", BreakdownStrategy, {"channel": [10, 20, 40]}),
        StrategySpec("Downtrend", DowntrendStrategy, {"ema_fast": [5, 9], "trend_ema": [100, 200]}),
    ]


def alerta(symbol, sig, price, settings, capital):
    risk = RiskManager(settings.risk)
    risk.begin()
    qty = int(risk.position_size(price, sig.stop))
    risco = qty * abs(price - sig.stop)
    rr = abs(sig.take - price) / abs(price - sig.stop) if price != sig.stop else 0.0
    acao = "COMPRAR (long)" if sig.action == "long" else "VENDER (short)"
    print("\a")  # bip sonoro
    print("!" * 60)
    print(f"  >>> SINAL EM {symbol}: {acao}  [{sig.reason}]")
    print(f"      Entrada R$ {price:,.2f} | STOP R$ {sig.stop:,.2f} "
          f"({abs(price-sig.stop)/price:.1%}) | ALVO R$ {sig.take:,.2f} (+{abs(sig.take-price)/price:.1%})")
    print(f"      Ganho/risco {rr:.1f}:1 | Qtd {qty} acoes | arrisca R$ {risco:,.2f}")
    if sig.action == "short":
        print("      [SHORT: confira custo de aluguel na corretora.]")
    print("      NAO enviei ordem -- execute voce, com o stop. ")
    print("!" * 60)


def main() -> None:
    symbol = sys.argv[1] if len(sys.argv) > 1 else "PETR4.SA"
    timeframe = sys.argv[2] if len(sys.argv) > 2 else "15m"
    capital = float(sys.argv[3]) if len(sys.argv) > 3 else 5_000.0

    settings = Settings.default()
    settings.risk.starting_equity = capital
    settings.day_trade = True

    try:
        from bot.sources.yfinance_source import YFinanceLiveFeed, load_yfinance
    except ImportError:
        print("yfinance nao instalado. Rode:  pip install yfinance  (ou setup.bat)")
        sys.exit(1)

    period = "30d" if timeframe in ("5m", "15m", "30m") else "180d"
    print(f"Calibrando o cerebro para {symbol} ({timeframe})... aguarde ~1-2 min.")
    buffer = load_yfinance(symbol, period=period, interval=timeframe)[:-1]
    brain, diags = build_brain(buffer, settings, build_specs(settings), n_folds=3)
    ativos = [d.name for d in diags if d.weight > 0]
    if not ativos:
        print(f"\nNenhuma estrategia e robusta em {symbol}. Nao vale vigiar. Tente outro ativo.")
        return

    print(f"\nComite: {', '.join(ativos)}")
    print(f"VIGIANDO {symbol} ({timeframe}). Aviso quando houver sinal. Ctrl+C para parar.\n")

    # avalia o estado atual de cara
    brain.prepare(buffer)
    sig = brain.signal(len(buffer) - 1)
    if sig.action in ("long", "short"):
        alerta(symbol, sig, buffer[-1].close, settings, capital)

    # so candles NOVOS a partir daqui
    feed = YFinanceLiveFeed(symbol=symbol, interval=timeframe, period=period, poll_seconds=60)
    feed._last_ts = buffer[-1].ts
    try:
        for c in feed.stream():
            buffer.append(c)
            brain.prepare(buffer)
            sig = brain.signal(len(buffer) - 1)
            hora = datetime.fromtimestamp(c.ts, tz=timezone.utc).strftime("%d/%m %H:%M")
            if sig.action in ("long", "short"):
                alerta(symbol, sig, c.close, settings, capital)
            else:
                print(f"  {hora} | R$ {c.close:,.2f} | aguardando...")
    except KeyboardInterrupt:
        print("\nVigia encerrado.")


if __name__ == "__main__":
    main()
