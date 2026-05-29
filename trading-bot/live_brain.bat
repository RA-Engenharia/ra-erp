@echo off
REM Paper trading AO VIVO do cerebro (Windows). Ordens SIMULADAS.
REM   live_brain.bat                 (PETR4.SA 1h, continuo -- Ctrl+C para parar)
REM   live_brain.bat VALE3.SA 1h
REM   live_brain.bat PETR4.SA 1h 50  (teste rapido: para apos 50 candles)
setlocal
cd /d "%~dp0"

if not exist ".venv" (
  echo Ambiente nao encontrado. Rode primeiro:  setup.bat
  pause
  exit /b 1
)
call .venv\Scripts\activate.bat
python examples\run_live_brain.py %*
pause
