# Primeiros passos — instalar e rodar o robô

Guia passo a passo para instalar o robô no seu computador e rodá-lo. Funciona
no **Windows** e no **Linux/macOS**. Tudo aqui é **paper trading** (simulação):
o robô lê preços reais, mas **NÃO envia nenhuma ordem** e **não mexe em dinheiro**.

> ⚠️ **A verdade que protege seu dinheiro:** *não existe* operar "sem risco".
> Este robô foi feito para **só operar quando há vantagem comprovada** — e para
> **ficar parado quando não há**. Ficar parado é uma decisão correta, não um erro.

---

## 0. O que você precisa antes

- **Python 3.10 ou superior** instalado.
  - Windows: baixe em <https://www.python.org/downloads/> e, na instalação,
    **marque a caixa "Add Python to PATH"**.
  - macOS/Linux: normalmente já vem; confira com `python3 --version`.
- **Internet** (para baixar dados reais). Sem internet o robô ainda roda, mas
  com dados sintéticos (de mentira), só para você ver o fluxo funcionando.

---

## 1. Baixar o projeto

Se você usa Git:

```bash
git clone <url-do-repositorio>
cd ra-erp/trading-bot
```

Sem Git: baixe o ZIP do repositório, extraia, e entre na pasta `trading-bot`.

---

## 2. Instalar (uma vez só)

O instalador cria um **ambiente isolado** (`.venv`) — ele **não bagunça** o seu
Python nem o resto do computador —, instala as dependências e roda os testes
para provar que está tudo são.

### Windows
Dê **dois cliques** em `setup.bat` (ou rode `setup.bat` no Prompt de Comando).

### Linux / macOS
```bash
bash setup.sh
```

No fim deve aparecer: **"OK — todos os testes passaram"** e **"PRONTO!"**.

---

## 3. Rodar o robô

### Windows
```
run.bat                 (ativo padrão: PETR4.SA)
run.bat VALE3.SA 15m 60d
run.bat BTC-USD 15m 60d
```

### Linux / macOS
```bash
bash run.sh
bash run.sh VALE3.SA 15m 60d
bash run.sh BTC-USD 15m 60d
```

Os três parâmetros são: **ativo**, **intervalo do candle** (`5m`, `15m`, `1h`,
`1d`) e **período** (`60d`, `1y`, ...). Para ações da B3 use o sufixo `.SA`
(ex.: `PETR4.SA`, `VALE3.SA`). Para cripto, ex.: `BTC-USD`.

---

## 4. Como LER o que o robô mostra

Primeiro vem o **relatório do cérebro** — quem ganhou direito de voto:

```
  Estrategia       voto   folds+   exp OOS    robusta?
  MACD             0.0    2/4      R$ -1.56   nao
  ...
→ NENHUMA estrategia foi robusta -> o cerebro fica PARADO.
```

- **folds+**: em quantas janelas de teste (fora-da-amostra) a estratégia foi
  positiva. `2/4` = ganhou em 2 das 4 janelas.
- **exp OOS**: lucro/prejuízo médio esperado por operação, em dados que a
  otimização **nunca viu**. Negativo = sem vantagem.
- **robusta?**: `SIM` só se a maioria das janelas foi positiva **e** a
  expectativa média foi positiva. Só quem é `SIM` ganha voto no cérebro.

Depois o cérebro **opera em paper trading**. Dois finais possíveis — **os dois
são úteis**:

1. **Cérebro PARADO / 0 trades** → nenhuma estratégia tem vantagem comprovada
   naquele ativo. O robô te protegeu de operar no escuro.
2. **Cérebro operando** → uma ou mais estratégias passaram. Ele mostra as
   entradas/saídas e a curva de capital. **Isso ainda não é sinal verde para
   dinheiro real** (veja a seção 6).

---

## 5. Trocar para tempo real contínuo (avançado)

Por padrão o robô reproduz os últimos 60 dias como "ensaio". Para alimentá-lo
com preços novos chegando ao vivo, edite `examples/run_brain.py` e troque o
feed por uma fonte ao vivo:

```python
from bot.sources import DataSourceConfig, build_feed

# cripto ao vivo (Binance), candles de 5 min:
cfg = DataSourceConfig(provider="ccxt", symbol="BTC/USDT", timeframe="5m")
feed = build_feed(cfg)
```

O cérebro e o motor de risco **não mudam** — só a origem dos dados.

---

## 6. Caminho até dinheiro real (leia com calma)

Este robô **não envia ordens reais** de propósito. Antes de chegar perto disso:

1. **Vantagem comprovada**: alguma estratégia precisa aparecer como `robusta?
   SIM` em dados reais — não em uma rodada de sorte, mas de forma consistente.
2. **Semanas de paper trading ao vivo** com resultado positivo e estável.
3. **Só então** trocar o `PaperBroker` por um broker real (mesma interface
   `open/update/close`), começando com o **mínimo** de capital.

Pular qualquer uma dessas etapas é a forma mais rápida de perder dinheiro.
O objetivo do robô é o oposto: **preservar seu capital primeiro, lucrar depois.**

---

## Problemas comuns

- **"Python nao encontrado"** (Windows): reinstale o Python marcando
  *"Add Python to PATH"* e abra um novo Prompt de Comando.
- **"nao foi possivel baixar dados reais"**: você está sem internet ou o
  `yfinance` não instalou. O robô cai para dados sintéticos automaticamente;
  rode o `setup` de novo com internet para habilitar dados reais.
- **Demora um pouco**: a análise (walk-forward das 6 estratégias) leva alguns
  segundos — é normal. É o robô sendo cuidadoso, não travado.
