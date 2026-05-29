@echo off
REM ===========================================================
REM  Instalador do robo de trading (Windows)
REM    1. confere o Python
REM    2. cria ambiente isolado (.venv)
REM    3. instala dependencias (yfinance, ccxt)
REM    4. roda os testes
REM
REM  Uso: clique duas vezes neste arquivo OU rode  setup.bat  no cmd
REM ===========================================================
setlocal
cd /d "%~dp0"

echo ============================================================
echo   INSTALADOR DO ROBO DE TRADING (paper trading / simulacao)
echo ============================================================

REM 1) Python -------------------------------------------------
where py >nul 2>nul
if %errorlevel%==0 (
  set "PY=py"
) else (
  where python >nul 2>nul
  if %errorlevel%==0 (
    set "PY=python"
  ) else (
    echo ERRO: Python nao encontrado. Instale Python 3.10+ de python.org
    echo IMPORTANTE: marque "Add Python to PATH" durante a instalacao.
    pause
    exit /b 1
  )
)
echo [1/4] Python encontrado:
%PY% --version

REM 2) ambiente isolado --------------------------------------
if not exist ".venv" (
  echo [2/4] Criando ambiente isolado em .venv ...
  %PY% -m venv .venv
) else (
  echo [2/4] Ambiente .venv ja existe -- reaproveitando.
)
call .venv\Scripts\activate.bat

REM 3) dependencias ------------------------------------------
echo [3/4] Instalando dependencias (precisa de internet)...
python -m pip install --upgrade pip >nul 2>nul
python -m pip install -r requirements.txt
if %errorlevel%==0 (
  echo       Dependencias instaladas (dados reais habilitados).
) else (
  echo       AVISO: falha ao instalar dependencias (provavelmente sem internet).
  echo       O robo roda com dados SINTETICOS. Rode de novo com internet depois.
)

REM 4) verificacao -------------------------------------------
echo [4/4] Rodando os testes...
python -m unittest discover -s tests
if %errorlevel% neq 0 (
  echo       ERRO: algum teste falhou. Nao use ainda.
  pause
  exit /b 1
)
echo       OK -- todos os testes passaram.

echo ============================================================
echo   PRONTO! Para rodar o robo:
echo       run.bat                 (ativo padrao PETR4.SA)
echo       run.bat VALE3.SA 15m 60d
echo       run.bat BTC-USD 15m 60d
echo.
echo   Lembrete: isto e PAPER TRADING (ordens simuladas).
echo   Nenhuma ordem real e enviada.
echo ============================================================
pause
