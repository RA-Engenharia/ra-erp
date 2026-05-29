#!/usr/bin/env bash
#
# Instalador do robo (Linux / macOS).
#
#   1. confere o Python
#   2. cria um ambiente isolado (.venv) -- nao bagunca seu sistema
#   3. instala as dependencias (yfinance, ccxt) -- pula se estiver offline
#   4. roda os testes para provar que tudo esta sao
#
# Uso:   bash setup.sh
#
set -uo pipefail
cd "$(dirname "$0")"

echo "============================================================"
echo "  INSTALADOR DO ROBO DE TRADING (paper trading / simulacao)"
echo "============================================================"

# 1) Python 3.10+ ----------------------------------------------------------
if command -v python3 >/dev/null 2>&1; then
  PY=python3
elif command -v python >/dev/null 2>&1; then
  PY=python
else
  echo "ERRO: Python nao encontrado. Instale Python 3.10+ em python.org e tente de novo."
  exit 1
fi
echo "[1/4] Python encontrado: $($PY --version)"

# 2) ambiente isolado ------------------------------------------------------
if [ ! -d ".venv" ]; then
  echo "[2/4] Criando ambiente isolado em .venv ..."
  "$PY" -m venv .venv
else
  echo "[2/4] Ambiente .venv ja existe -- reaproveitando."
fi
# shellcheck disable=SC1091
source .venv/bin/activate

# 3) dependencias ----------------------------------------------------------
echo "[3/4] Instalando dependencias (precisa de internet)..."
python -m pip install --upgrade pip >/dev/null 2>&1 || true
if python -m pip install -r requirements.txt; then
  echo "      Dependencias instaladas (dados reais habilitados)."
else
  echo "      AVISO: nao consegui instalar as dependencias (provavelmente sem"
  echo "      internet). Sem problema: o robo roda com dados SINTETICOS. Rode"
  echo "      este instalador de novo quando tiver internet para habilitar"
  echo "      dados reais (yfinance/ccxt)."
fi

# 4) verificacao -----------------------------------------------------------
echo "[4/4] Rodando os testes (prova que o motor esta integro)..."
if python -m unittest discover -s tests >/dev/null 2>&1; then
  echo "      OK -- todos os testes passaram."
else
  echo "      ERRO: algum teste falhou. Nao use ainda; me avise."
  exit 1
fi

echo "============================================================"
echo "  PRONTO! Para rodar o robo:"
echo "      bash run.sh                 # ativo padrao (PETR4.SA)"
echo "      bash run.sh VALE3.SA 15m 60d"
echo "      bash run.sh BTC-USD 15m 60d"
echo ""
echo "  Lembrete: isto e PAPER TRADING (ordens simuladas). Nenhuma"
echo "  ordem real e enviada e nenhum dinheiro e movimentado."
echo "============================================================"
