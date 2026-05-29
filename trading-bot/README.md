# Robô de Trading — Fase 1 (fundação)

Motor de trading automatizado em **Python puro** (sem dependências externas),
com **gestão de risco no centro de tudo**. Roda offline, em qualquer máquina.

> **Filosofia:** preservar o capital vem **antes** de lucrar. O sucesso é medido
> por desempenho ajustado ao risco (drawdown, Sharpe), não por "quanto rendeu".

---

## ⚠️ Leia antes de tudo — expectativas realistas

- **Nenhum robô garante lucro nem "nunca perder".** Quem promete isso está
  mentindo ou é golpe.
- Estudo de Chague & Giovannetti (FGV/USP) com day traders de mini-índice da
  B3 (2013–2017): entre quem persistiu +300 dias, **~97% perderam dinheiro** e
  apenas **~1%** ganhou algo relevante.
- O que separa quem sobrevive **não é a estratégia de entrada** — é **gestão de
  risco implacável** + **validação antes de arriscar dinheiro real**.
- Este projeto codifica essas travas como **regras obrigatórias** (ver
  `bot/risk.py`). O robô se recusa a fazer o que quebra a maioria.

---

## Como rodar (sem internet, sem instalar nada)

```bash
cd trading-bot
python3 -m unittest discover -s tests   # roda os testes
python3 examples/run_backtest.py        # backtest em simulação
python3 examples/run_validation.py      # validação anti-overfitting (offline)
python3 examples/compare_strategies.py  # compara 4 estratégias (offline)
python3 examples/regime_robustness.py   # alta/baixa/lateral + curva de capital
python3 examples/run_live.py            # paper trading "ao vivo" (feed simulado)
python3 examples/run_brain.py           # cérebro: combina TODAS as estratégias
```

### O "cérebro central" (ensemble)

`bot/brain.py` junta todas as estratégias num **comitê**. Antes de operar, ele
**analisa cada uma no walk-forward** e só dá direito de voto às que provaram
vantagem fora-da-amostra (peso proporcional aos folds positivos). Depois, só
abre operação quando há **consenso** (maioria do peso concorda na direção).

> **Importante e honesto:** se nenhuma estratégia for robusta, todos os votos
> são zero e o cérebro **fica parado** — não opera, não arrisca capital. Não
> existe "operar sem risco"; o mais perto disso é **não operar sem vantagem
> comprovada**, e é exatamente o que o cérebro impõe.

Para alimentá-lo em tempo real, descreva a fonte com `DataSourceConfig`
(provider `ccxt`/`yfinance`/`csv`/`replay`) e use `build_feed(config)`.

Com dados **reais** de ações (na sua máquina, com internet):

```bash
pip install yfinance
python3 examples/fetch_yfinance.py AAPL 60d 5m   # baixa, testa e valida
```

---

## Estrutura

| Arquivo | Papel |
|---|---|
| `bot/config.py` | **Parâmetros de risco** (o arquivo mais importante) |
| `bot/risk.py` | **O coração:** tamanho de posição + travas de risco |
| `bot/strategy.py` | Estratégia base + EMA+RSI (padrão) — trocável |
| `bot/strategies.py` | 5 candidatas: Breakout, Reversão, EMA+tendência, MACD, Bollinger |
| `bot/broker.py` | Corretora simulada com **custos e slippage reais** |
| `bot/backtest.py` | Motor de backtest + métricas ajustadas ao risco |
| `bot/validation.py` | **Anti-overfitting:** treino/teste, walk-forward, comparador, robustez entre regimes |
| `bot/chart.py` | Curva de capital em ASCII (ver os drawdowns sem libs) |
| `bot/live.py` | Paper trading **ao vivo**: candle a candle, sem lookahead |
| `bot/feeds.py` | Fontes de candles: replay e **feed real** de corretora (ccxt) |
| `bot/brain.py` | **Cérebro central:** comitê que combina todas as estratégias por voto |
| `bot/sources/` | `DataSourceConfig` + `build_feed`: parâmetros de coleta em tempo real |
| `bot/sources/` | Adaptadores de dados reais (ex.: `yfinance` para ações) |
| `bot/indicators.py` | EMA, RSI, ATR em Python puro |
| `bot/data.py` | Candles: gerador sintético + leitor de CSV |
| `tests/` | Testes (risco e validação testados a fundo) |

---

## Os parâmetros que importam (em `bot/config.py`)

| Parâmetro | Padrão | O que faz |
|---|---|---|
| `risk_per_trade_pct` | 1% | Máximo do capital arriscado por trade (até o stop) |
| `max_daily_loss_pct` | 3% | Perdeu isso no dia → **para de operar** até o dia seguinte |
| `max_total_drawdown_pct` | 20% | Queda desde o topo → **desliga o robô** (disjuntor) |
| `max_position_pct` | 100% | Teto de exposição por posição |
| `stop_atr_mult` | 1.5 | Distância do stop em múltiplos de ATR (volatilidade) |
| `reward_risk` | 1.5 | Razão alvo:risco (ganho-alvo por unidade de risco) |
| `commission_pct` | 0.05% | Comissão+taxas por lado (custo real) |
| `slippage_pct` | 0.03% | Execução pior que o preço visto (custo real) |

**Stop-loss é obrigatório**: sem stop, não há tamanho de posição (o robô não
opera "no escuro").

---

## O que o backtest de demonstração ensina

Rodando a estratégia ingênua em dados quase aleatórios, ela **perde** (fator de
lucro < 1, expectância negativa) — exatamente como acontece com a maioria.
**Mas o disjuntor de drawdown segura a perda em ~20%** em vez de zerar a conta.

Lições:
1. Indicadores soltos **não** são uma vantagem (edge). Custos só pioram.
2. A vantagem precisa ser **encontrada e validada** (próximas fases).
3. A gestão de risco é o que mantém você vivo para tentar de novo.

---

## Plano (roadmap)

- [x] **Fase 1 — Fundação:** motor de risco + backtest + paper trading (offline)
- [x] **Fase 2 — Dados reais + validação:** adaptador `yfinance` (ações EUA) e
      motor anti-overfitting (treino/teste + walk-forward)
- [~] **Fase 3 — Buscar a vantagem:** 4 estratégias (EMA+RSI, Breakout,
      Reversão à média, EMA+tendência) + comparador que ranqueia por robustez
      fora-da-amostra. Falta rodar nos **dados reais** e iterar com features novas.
- [x] **Fase 4 — Paper trading ao vivo:** motor `live.py` (candle a candle, sem
      lookahead) + adaptador de **feed real** de corretora em `feeds.py`
      (`CcxtLiveFeed`, entrega só candles fechados). Veja `examples/run_live_ccxt.py`.
- [ ] **Fase 5 — Dinheiro real:** trocar o PaperBroker por um broker que envie
      ordens de verdade (mesma interface open/update/close), com extrema cautela
      fictício por semanas
- [ ] **Fase 5 — Go-live mínimo:** só depois de provado, capital pequeno,
      escalando com evidência

---

## Aviso legal

Software **educacional**. Não é recomendação de investimento. Operar na bolsa
envolve risco de perda total do capital. Você é o único responsável pelas suas
decisões. Valide tudo em simulação antes de qualquer dinheiro real.
