# 🖥️ Como usar o Painel — guia rápido

O painel é a sua central. Mostra gráfico real, sinais, análise técnica e o
placar dos sinais. **Ele NÃO envia ordem** — mostra, você decide e executa na
corretora (sempre com o stop).

---

## ▶️ Abrir o painel

Na pasta `trading-bot`, dois cliques em **`painel.bat`**.
O navegador abre sozinho em **http://127.0.0.1:5000**.

> Para fechar: feche a janela preta (o servidor) que abriu junto.

---

## 🧭 Tour da tela (de cima para baixo)

**Barra do topo (controles):**
- **Ativo** — escolha na lista (PETR4, VALE3, BTC-USD…) ou digite o código
- **5m / 15m / 1h / 1d** — o intervalo de tempo (timeframe)
- **Capital (R$)** — quanto você considera para calcular a quantidade e o risco
- Botões: **⚡ Analisar**, **👁 Vigiar**, **📊 Carteira**, **📒 Extrato**

**Esquerda — o gráfico:**
- Candles reais + **médias móveis** (EMA9 laranja, EMA21 azul)
- Quando há sinal, aparecem as linhas de **entrada (azul)**, **STOP (vermelho)** e **ALVO (verde)**

**Direita — os painéis:**
1. **Cartão de sinal** — COMPRAR / VENDER / AGUARDAR + stop, alvo, quantidade, risco
2. **Comitê do cérebro** — quais estratégias são robustas no ativo
3. **Leitura técnica** — RSI, volatilidade, força da tendência, variação
4. **Tendência por tempo** — alinhamento 15m / 1h / 1d
5. **Desempenho (backtest)** — estatísticas + curva de capital
6. **Extrato** — o placar real dos sinais (acertos, erros, R$)

---

## 🔄 O fluxo em 3 passos

### 1️⃣ ANALISAR
Escolha o ativo e o timeframe → clique em **⚡ Analisar**.
- Na 1ª vez demora **1-2 min** (o cérebro está se calibrando — normal).
- Aparece o **comitê**, a **leitura técnica** e o **multi-timeframe**.
- O **cartão de sinal** mostra a situação atual: COMPRAR, VENDER ou AGUARDAR.

> 💡 Clique em **Calcular** (painel Desempenho) para ver como o cérebro teria se
> saído no histórico — retorno, acerto, drawdown e a curva de capital.

### 2️⃣ VIGIAR
Clique em **👁 Vigiar** → o painel passa a se atualizar **sozinho** (a cada ~20s).
- Quando aparece um sinal, ele **alerta** e desenha stop/alvo no gráfico.
- **Cada sinal é salvo automaticamente** no extrato.
- Deixe rodando durante o pregão. Clique de novo em Vigiar para parar.

### 3️⃣ EXTRATO
Clique em **📒 Extrato** → o placar real dos sinais que já apareceram:
- **Acertos** (bateu o alvo) × **Erros** (bateu o stop) × **Em aberto**
- **Taxa de acerto**
- **Resultado simulado (R$)** — quanto você teria feito seguindo TODOS os
  sinais, já com custos descontados
- A lista de cada sinal com o resultado individual

---

## 🎯 Como ler o cartão de sinal

```
  ▲ COMPRAR  (consenso 67%: EMA+tend)
  Entrada R$ 38,50   |   Ganho/Risco 1,9 : 1
  STOP    R$ 37,90 (1,6% de risco)   |   ALVO R$ 39,70 (+3,1%)
  Quantidade 80 ações   |   Você arrisca R$ 50 (1% do capital)
```
- **STOP**: onde sair se der errado (limita a perda). **Use SEMPRE.**
- **ALVO**: onde realizar o lucro.
- **Quantidade / arrisca**: já calculado para você não perder mais que ~1% por operação.

**AGUARDAR** aparece na maioria do tempo — é disciplina, não falha. O robô só
sinaliza com consenso.

---

## ✅ O plano de validação honesta (faça isto antes de dinheiro real)

1. Ligue o **👁 Vigiar** em 2-3 ações durante uns **30 pregões**.
2. Os sinais vão entrando no **📒 Extrato** sozinhos.
3. Acompanhe o **Resultado simulado (R$)**:
   - 🟢 **Verde e crescendo por semanas** → aí sim pense em dinheiro real, começando com o mínimo.
   - 🔴 **Vermelho ou instável** → o robô te poupou do prejuízo. Não arrisque.

> ⚠️ **Cuidado com a armadilha:** dá pra ter taxa de acerto alta e ainda perder
> dinheiro (se as perdas forem maiores que os ganhos). Por isso, olhe o
> **Resultado em R$**, não só a taxa de acerto.

---

## ⚠️ 3 regras que não mudam

1. **Use SEMPRE o stop** que o robô calcula.
2. **O painel mostra o sinal, você executa** na corretora. Ele não opera sozinho.
3. **Day trade intraday foi onde os testes não acharam vantagem.** Comece no
   papel (extrato), com dinheiro que pode perder, sem pressa.

---

## 🛠️ Problemas comuns

| Aconteceu | Solução |
|---|---|
| Navegador não abriu | Digite à mão: `http://127.0.0.1:5000` |
| "No module named flask" | Rode o `setup.bat` de novo |
| Gráfico vazio | Confira o código do ativo (ex.: `PETR4.SA`, com `.SA`) e a internet |
| "poucos dados" | Esse timeframe não tem histórico suficiente; tente outro |
| Demora ao Analisar | Normal na 1ª vez (1-2 min calibrando) |
