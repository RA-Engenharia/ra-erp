#!/usr/bin/env bash
#
# Liga o robo (Linux / macOS). Use depois de rodar setup.sh uma vez.
#
#   bash run.sh                    # ativo padrao (PETR4.SA, 15m, 60d)
#   bash run.sh VALE3.SA 15m 60d   # outra acao da B3
#   bash run.sh AAPL 5m 60d        # acao dos EUA
#   bash run.sh BTC-USD 15m 60d    # cripto
#
set -uo pipefail
cd "$(dirname "$0")"

if [ ! -d ".venv" ]; then
  echo "Ambiente nao encontrado. Rode primeiro:  bash setup.sh"
  exit 1
fi
# shellcheck disable=SC1091
source .venv/bin/activate
python examples/run_brain.py "$@"
