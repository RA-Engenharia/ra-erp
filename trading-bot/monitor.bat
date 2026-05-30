@echo off
REM Painel de acompanhamento do ensaio (Windows).
REM   monitor.bat                       (le data\live_trades.csv)
REM   monitor.bat caminho\arquivo.csv
setlocal
cd /d "%~dp0"

if not exist ".venv" (
  echo Ambiente nao encontrado. Rode primeiro:  setup.bat
  pause
  exit /b 1
)
call .venv\Scripts\activate.bat
python examples\monitor.py %*
pause
