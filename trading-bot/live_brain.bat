@echo off
REM Paper trading AO VIVO do cerebro (Windows). Ordens SIMULADAS.
REM   live_brain.bat                       (WEGE3.SA, swing diario -- nosso campeao)
REM   live_brain.bat ITUB4.SA 1d swing
REM   live_brain.bat PETR4.SA 1h day       (intraday/day trade)
REM   live_brain.bat WEGE3.SA 1d swing 400 (teste rapido: para apos 400 candles)
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
