"""SINAL DE OPERACAO -- diz COMPRAR/VENDER/AGUARDAR agora, com stop e alvo.

    cd trading-bot
    python3 examples/sinal.py                       # PETR4.SA 15m, R$ 5.000
    python3 examples/sinal.py VALE3.SA 15m 10000     # ticker timeframe capital

Para um ativo e um intervalo curto (intraday), monta o cerebro, olha o ultimo
candle FECHADO e devolve um cartao de operacao com tudo calculado: entrada,
STOP (protecao), ALVO, quantidade e quanto voce arrisca (1% do capital).

IMPORTANTE / HONESTO:
  - Isto NAO envia ordem. Voce executa na sua corretora se quiser. Voce decide.
  - Day trade intraday foi JUSTAMENTE onde os testes NAO acharam vantagem.
    Use com ceticismo, com dinheiro que pode perder, e SEMPRE com o stop.
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
    # foco intraday: momentum filtrado por regime + reversao + especialistas de queda
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


def main() -> None:
    symbol = sys.argv[1] if len(sys.argv) > 1 else "PETR4.SA"
    timeframe = sys.argv[2] if len(sys.argv) > 2 else "15m"
    capital = float(sys.argv[3]) if len(sys.argv) > 3 else 5_000.0

    settings = Settings.default()
    settings.risk.starting_equity = capital
    settings.day_trade = True  # intervalo curto (intraday)

    try:
        from bot.sources.yfinance_source import load_yfinance
    except ImportError:
        print("yfinance nao instalado. Rode:  pip install yfinance  (ou setup.bat)")
        sys.exit(1)

    print(f"Analisando {symbol} ({timeframe})... aguarde ~1-2 min.\n")
    period = "30d" if timeframe in ("5m", "15m", "30m") else "180d"
    candles = load_yfinance(symbol, period=period, interval=timeframe)
    if len(candles) < 250:
        print(f"Poucos dados ({len(candles)}). Tente outro timeframe.")
        return

    # avalia no ultimo candle JA FECHADO (descarta o que ainda se forma)
    closed = candles[:-1]
    brain, diags = build_brain(closed, settings, build_specs(settings), n_folds=3)
    ativos = [d.name for d in diags if d.weight > 0]

    brain.prepare(closed)
    sig = brain.signal(len(closed) - 1)
    price = closed[-1].close
    when = datetime.fromtimestamp(closed[-1].ts, tz=timezone.utc).strftime("%d/%m %H:%M UTC")

    print("=" * 60)
    print(f"  SINAL DE OPERACAO -- {symbol} ({timeframe})")
    print("=" * 60)
    print(f"  Preco (ult. fechado): R$ {price:,.2f}   |  {when}")
    print(f"  Comite robusto: {', '.join(ativos) if ativos else '(nenhum -- sem vantagem neste ativo)'}")
    print("  " + "-" * 56)

    if not ativos:
        print("  >> AGUARDAR. Nenhuma estrategia e robusta aqui: nao operar.")
        print("=" * 60)
        return

    if sig.action not in ("long", "short"):
        print("  >> AGUARDAR. Sem sinal de qualidade neste candle.")
        print("     (o cerebro so sinaliza com consenso; a maior parte do")
        print("      tempo fica de fora -- isso e disciplina, nao falha.)")
        print("=" * 60)
        return

    # cartao de operacao
    risk = RiskManager(settings.risk)
    risk.begin()
    qty = int(risk.position_size(price, sig.stop))
    risco_reais = qty * abs(price - sig.stop)
    risco_pct = abs(price - sig.stop) / price
    alvo_pct = abs(sig.take - price) / price
    rr = abs(sig.take - price) / abs(price - sig.stop) if price != sig.stop else 0.0
    acao = "COMPRAR (long)" if sig.action == "long" else "VENDER (short)"

    print(f"  >> {acao}   [{sig.reason}]")
    print(f"     Entrada .............: R$ {price:,.2f}")
    print(f"     STOP (protecao) .....: R$ {sig.stop:,.2f}   ({risco_pct:.1%} de risco)")
    print(f"     ALVO ................: R$ {sig.take:,.2f}   (+{alvo_pct:.1%})")
    print(f"     Ganho/risco .........: {rr:.1f} : 1")
    print(f"     Quantidade ..........: {qty} acoes")
    print(f"     Voce arrisca ........: R$ {risco_reais:,.2f}  (~{risco_reais/capital:.1%} de R$ {capital:,.0f})")
    if sig.action == "short":
        print("     [SHORT: vender alugado tem custo/risco de aluguel. Cheque na corretora.]")
    print("  " + "-" * 56)
    print("  Isto NAO envia ordem. Execute na sua corretora se decidir -- e")
    print("  use SEMPRE o stop. Day trade foi onde nao achamos vantagem real.")
    print("=" * 60)


if __name__ == "__main__":
    main()
