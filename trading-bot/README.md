# Robô de Trading — plataforma completa (motor + cérebro + painel)

Plataforma de trading com **gestão de risco no centro de tudo**: motor em
**Python puro** (o núcleo roda sem dependências), 11 estratégias, cérebro que
combina e valida tudo, e um **painel web** com gráficos reais. Dados reais via
`yfinance`/`ccxt` (opcionais). Sempre **paper trading** — mostra sinais, não
envia ordem.

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

### Instalação automática (recomendado)

Não quer rodar comando por comando? Use o instalador — cria um ambiente
isolado, instala as dependências e roda os testes:

| Sistema | Instalar (1x) | Rodar |
|---|---|---|
| Windows | `setup.bat` (dois cliques) | `run.bat` / `live_brain.bat` |
| Linux/macOS | `bash setup.sh` | `bash run.sh` |

**Atualizar para a versão mais nova:** rode **`atualizar.bat`** (Windows) ou
`bash atualizar.sh` — baixa e atualiza tudo sozinho (preserva seus dados).

`live_brain.bat` roda o **paper trading ao vivo** do cérebro (ordens simuladas,
preços reais) — a etapa de ensaio antes de qualquer dinheiro real.
`monitor.bat` mostra o **painel** do ensaio (acertos, fator de lucro, drawdown,
curva de capital) lendo o log de operações simuladas.

**Day trade vs swing:** `Settings.day_trade` (True = zera no fim do dia;
False = swing, segura por dias). A análise em dados reais mostrou que o **swing
diário** é onde as estratégias clássicas têm vantagem mais robusta — veja
`examples/analyze_full.py` e `examples/stress_swing.py`.

Guia completo passo a passo: [`PRIMEIROS_PASSOS.md`](PRIMEIROS_PASSOS.md).

### Painel web (interface gráfica)

`painel.bat` abre uma interface no navegador com **gráfico de candles real**,
sinais (comprar/vender com stop e alvo), leitura técnica ao vivo, análise
multi-timeframe, desempenho (backtest) e o **extrato de sinais** (placar real,
com resultado em R$). Guia de uso: [`COMO_USAR_PAINEL.md`](COMO_USAR_PAINEL.md).

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
| `bot/config.py` | **Parâmetros de risco** (o arquivo mais importante) + custos/aluguel |
| `bot/risk.py` | **O coração:** tamanho de posição + travas de risco |
| `bot/indicators.py` | EMA, SMA, RSI, ATR, MACD, Bollinger, ROC, SuperTrend, Efficiency Ratio |
| `bot/strategy.py` | Estratégia base + EMA+RSI (padrão) |
| `bot/strategies.py` | 11 estratégias (alta/baixa) + `RegimeFilteredStrategy` (filtro de regime) |
| `bot/broker.py` | Corretora simulada com **custos, slippage e aluguel de short reais** |
| `bot/backtest.py` | Motor de backtest (day trade/swing) + métricas ajustadas ao risco |
| `bot/validation.py` | **Anti-overfitting:** treino/teste, walk-forward, comparador, regimes |
| `bot/scanner.py` | Varre ativos/timeframes procurando vantagem (com bar honesto) |
| `bot/brain.py` | **Cérebro central:** comitê que combina estratégias robustas por voto |
| `bot/live.py` | Paper trading **ao vivo**: candle a candle, sem lookahead |
| `bot/feeds.py` | Fontes de candles: replay e **feed real** (ccxt) |
| `bot/sources/` | `DataSourceConfig`/`build_feed` + adaptador `yfinance` (ações/ETFs/cripto) |
| `bot/monitor.py` | Painel/resumo do ensaio (acertos, fator de lucro, curva) |
| `bot/radar.py` | Raio-X técnico rápido (radar de oportunidades) |
| `bot/signallog.py` | Extrato de sinais: registra e avalia (acerto/stop, R$) |
| `bot/trademanager.py` | Gestão da operação aberta: PnL ao vivo + trailing stop |
| `bot/chart.py` | Curva de capital em ASCII |
| `bot/data.py` | Candles: gerador sintético/regimes + leitor de CSV |
| `tests/` | **70 testes** (risco, validação, estratégias, painel) |

---

## 🚀 Ferramentas (atalhos)

Depois de instalar (`setup.bat` no Windows / `bash setup.sh` no Linux/macOS):

| Atalho | O que faz |
|---|---|
| **`painel.bat`** | **Painel web completo** (gráfico real, sinais, radar, extrato, gestão) |
| `sinal.bat` | Sinal agora (compra/venda) com stop, alvo, quantidade e risco |
| `vigia.bat` | Vigia um ativo e **avisa** quando aparece sinal |
| `diario.bat` | Decisão do dia (swing) de um ativo |
| `carteira.bat` | Decisão do cérebro na cesta de ações |
| `monitor.bat` | Painel do histórico de operações simuladas |
| `run.bat` | Análise rápida do cérebro num ativo |
| `live_brain.bat` | Paper trading contínuo do cérebro |

Guias: [`COMECE_AQUI.md`](COMECE_AQUI.md) (instalação) ·
[`COMO_USAR_PAINEL.md`](COMO_USAR_PAINEL.md) (painel) ·
[`PRIMEIROS_PASSOS.md`](PRIMEIROS_PASSOS.md) (detalhado).

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

- [x] **Fase 1 — Fundação:** motor de risco + backtest + paper trading
- [x] **Fase 2 — Dados reais + validação:** `yfinance`/`ccxt` + anti-overfitting
      (treino/teste, walk-forward, teste de estresse)
- [x] **Fase 3 — Buscar a vantagem:** 11 estratégias (alta/baixa) + filtro de
      regime + comparador + scanner. Conclusão honesta dos dados reais: o swing
      diário é o terreno mais robusto, mas o edge é **fino** (perto/abaixo do CDI)
      — por isso a validação ao vivo é obrigatória antes de qualquer aposta.
- [x] **Fase 4 — Paper trading ao vivo + painel:** `live.py` (sem lookahead),
      feed real (`ccxt`/`yfinance`), **painel web** (gráficos, radar, gestão de
      trade) e **extrato** que avalia os sinais em R$ — o validador honesto.
- [ ] **Fase 5 — Dinheiro real (só depois de provado):** semanas de extrato
      positivo e consistente → trocar o PaperBroker por execução real (mesma
      interface), começando com o **mínimo** de capital e escalando com evidência.

---

## Aviso legal

Software **educacional**. Não é recomendação de investimento. Operar na bolsa
envolve risco de perda total do capital. Você é o único responsável pelas suas
decisões. Valide tudo em simulação antes de qualquer dinheiro real.
