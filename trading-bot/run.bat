@echo off
REM Liga o robo (Windows). Use depois de rodar setup.bat uma vez.
REM   run.bat                    (ativo padrao PETR4.SA, 15m, 60d)
REM   run.bat VALE3.SA 15m 60d   (outra acao da B3)
REM   run.bat BTC-USD 15m 60d    (cripto)
setlocal
cd /d "%~dp0"

if not exist ".venv" (
  echo Ambiente nao encontrado. Rode primeiro:  setup.bat
  pause
  exit /b 1
)
call .venv\Scripts\activate.bat
python examples\run_brain.py %*
pause
