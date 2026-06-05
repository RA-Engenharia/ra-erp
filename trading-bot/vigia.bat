@echo off
REM VIGIA (Windows) -- fica rodando e AVISA quando aparece sinal (com bip).
REM NAO envia ordem: voce executa. Ctrl+C para parar. Use SEMPRE o stop.
REM   vigia.bat                       (PETR4.SA 15m, R$ 5.000)
REM   vigia.bat VALE3.SA 15m 10000
setlocal
cd /d "%~dp0"

if not exist ".venv" (
  echo Ambiente nao encontrado. Rode primeiro:  setup.bat
  pause
  exit /b 1
)
call .venv\Scripts\activate.bat
python examples\vigia.py %*
pause
