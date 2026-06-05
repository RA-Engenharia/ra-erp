#!/usr/bin/env bash
# Atualizar o robo (Linux/macOS). Tenta git pull; se nao houver git,
# baixa o ZIP mais recente do GitHub e atualiza (preserva .venv e data).
set -uo pipefail
cd "$(dirname "$0")"
BRANCH="claude/friendly-sagan-ULVZ2"
URL="https://github.com/ra-engenharia/ra-erp/archive/refs/heads/${BRANCH}.zip"

echo "============================================================"
echo "  ATUALIZADOR DO ROBO"
echo "============================================================"

if command -v git >/dev/null 2>&1 && { [ -d .git ] || [ -d ../.git ]; }; then
  echo "[git] atualizando..."
  ( [ -d .git ] && git pull ) || ( cd .. && git pull )
else
  echo "[download] baixando a versao mais recente..."
  tmp="$(mktemp -d)"
  if ! curl -fsSL "$URL" -o "$tmp/robo.zip"; then
    echo "ERRO: nao consegui baixar. Verifique a internet."; exit 1
  fi
  ( cd "$tmp" && unzip -q robo.zip )
  src="$(find "$tmp" -maxdepth 1 -type d -name 'ra-erp-*')/trading-bot"
  echo "[copiar] atualizando arquivos (preservando .venv e data)..."
  rsync -a --exclude .venv --exclude data --exclude __pycache__ --exclude .git "$src"/ ./
  rm -rf "$tmp"
fi

echo "[setup] garantindo dependencias..."
bash setup.sh
echo "ATUALIZADO! Para abrir:  bash run.sh  (ou painel:  python examples/painel.py)"
