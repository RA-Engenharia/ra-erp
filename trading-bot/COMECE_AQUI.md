# 🟢 COMECE AQUI — sua rotina para testar amanhã

Guia direto ao ponto. Lê em 3 minutos, testa em 10.

---

## ⚡ Resumo de 30 segundos

Você vai rodar o **cérebro em paper trading (simulação)** no ativo campeão do
nosso estudo (**WEGE3, swing diário**). Ele lê preços **reais**, mas **não envia
ordem nenhuma e não mexe em dinheiro**. É o ensaio antes de qualquer centavo.

**Amanhã, 3 passos:** instalar (1×) → rodar `diario.bat` → ler o resultado.

---

## ✅ O que você precisa — e o que NÃO precisa

### Precisa (tudo grátis, tudo sem custo):
- [ ] **Um computador Windows** com internet.
- [ ] **Python 3.10+** — https://www.python.org/downloads/
      ⚠️ Na instalação, **marque "Add Python to PATH"**.
- [ ] **O projeto** já baixado (você já fez o `git clone`). ✔️

### ❌ NÃO precisa (importante — não perca tempo com isso amanhã):
- ❌ **NÃO precisa criar conta em corretora.**
- ❌ **NÃO precisa de cartão, CPF em corretora, nem depositar dinheiro.**
- ❌ **NÃO precisa de API key, login, nem cadastro em site nenhum.**
- ❌ **NÃO precisa do MetaTrader nem de home broker.**

> Os dados vêm do **yfinance** (Yahoo Finanças), que é **gratuito e sem
> cadastro**. Conta em corretora só será necessária **lá na frente**, na etapa
> de dinheiro real — que está a **meses** de distância (explico no fim).

---

## 📋 Passo a passo de AMANHÃ

Abra o **Prompt de Comando** dentro da pasta `trading-bot`.

**Passo 1 — Instalar (só na primeira vez, ~2 min):**
```cmd
setup.bat
```
Espere aparecer **"OK -- todos os testes passaram"** e **"PRONTO!"**.

**Passo 2 — Rodar a checagem do dia:**
```cmd
diario.bat
```
Vai baixar os dados, analisar e mostrar a decisão de hoje. Leva ~1 min. **Termina sozinho.**

**Passo 3 — Ler o resultado** (próxima seção). Pronto. É isso.

---

## 👀 Como ler o que aparece

O `diario.bat` mostra **3 blocos**:

**1) Quem o cérebro considera robusto** (ganhou voto):
```
  EMA+RSI    voto 3.0   3/4   +R$ 27.04   SIM
  MACD       voto 3.0   3/4   +R$ 11.86   SIM
  Comite ativo (3): EMA+RSI, EMA+tend, MACD.
```

**2) A DECISÃO DE HOJE:**
```
  >> DE FORA (sem posicao). Nenhuma acao hoje -- aguardar sinal.
       OU
  >> COMPRADO (long) | entrada ~R$ 50.00 | stop R$ 47.00 | alvo R$ 56.00
```
Isso é o que o cérebro faria **se fosse real**. Como é paper, é só registro.

**3) O painel do histórico** (acertos, fator de lucro, curva de capital).

> ⚠️ **"AMOSTRA PEQUENA"** vai aparecer no começo — é normal e correto. Swing
> diário gera poucos trades; só dá para concluir algo depois de **meses**.

---

## 🔁 A rotina (o que fazer a cada dia)

Swing diário = o candle do dia **fecha uma vez só**. Então:

- **Rode `diario.bat` uma vez por dia**, de preferência **após o fechamento do
  pregão (depois das ~18h)**, quando o dado do dia já fechou.
- Anote mentalmente (ou deixe o histórico acumular) o que o cérebro decidiu.
- **Não precisa ficar olhando o dia todo.** Swing é o oposto de day trade.

Quer testar outro ativo robusto? `diario.bat ITUB4.SA`

---

## 🤖 O que já está automatizado (tudo que construímos)

| Atalho | O que faz |
|---|---|
| `setup.bat` | Instala tudo (ambiente, dependências, testa) — 1× |
| `diario.bat` | **Sua rotina diária**: análise + decisão de hoje + painel |
| `run.bat` | Análise rápida do cérebro num ativo |
| `live_brain.bat` | Paper trading contínuo (mais para intraday) |
| `monitor.bat` | Painel do histórico de operações simuladas |

Por baixo, o cérebro já faz **sozinho**: baixar dados reais, testar 9
estratégias, descartar as que não têm vantagem (walk-forward), juntar as
robustas num comitê por voto, decidir só com consenso, respeitar as travas de
risco, e registrar tudo. Você só roda `diario.bat`.

---

## 🛣️ O caminho honesto até dinheiro real (leia com calma)

Estamos na **etapa 3 de 4**. Pular etapa é como se perde dinheiro.

| Etapa | O que é | Status |
|---|---|---|
| 1 | Achar estratégia com vantagem | ✅ WEGE3/ITUB4 swing |
| 2 | Teste de estresse (custos) | ✅ sobreviveram |
| 3 | **Paper trading ao vivo por MESES** | ▶️ **você começa amanhã** |
| 4 | Dinheiro real mínimo | ⬜ só depois da etapa 3 dar certo |

**Só QUANDO a etapa 3 for positiva e consistente por meses**, aí sim você vai
precisar (e eu te ajudo a montar):
- abrir conta numa **corretora** (XP, Clear, Rico, BTG, NuInvest, etc.);
- escolher uma que tenha **API ou MetaTrader 5** para automação;
- e começar com o **mínimo** de dinheiro possível.

Nada disso é para amanhã. Amanhã é **ensaio grátis**.

---

## ⚠️ 3 verdades que protegem seu dinheiro

1. **Paper trading não é dinheiro real.** Resultado bom aqui é promissor, não
   garantido. Mercado muda.
2. **Swing segura posição por dias** → existe risco de *gap* (o preço abrir bem
   diferente no dia seguinte). Real teria esse risco; o ensaio mede isso.
3. **Ninguém ganha sempre.** O objetivo do cérebro é só operar quando a
   vantagem é real, e ficar de fora quando não é. Disciplina > empolgação.

Bons testes amanhã. Qualquer erro na tela, me manda o texto que eu resolvo. 🚀
