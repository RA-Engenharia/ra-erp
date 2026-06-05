@echo off
REM SINAL DE OPERACAO (Windows) -- comprar/vender/aguardar agora, com stop e alvo.
REM NAO envia ordem: voce executa na corretora se quiser. Use SEMPRE o stop.
REM   sinal.bat                       (PETR4.SA 15m, R$ 5.000)
REM   sinal.bat VALE3.SA 15m 10000
REM   sinal.bat PETR4.SA 5m 5000
setlocal
cd /d "%~dp0"

if not exist ".venv" (
  echo Ambiente nao encontrado. Rode primeiro:  setup.bat
  pause
  exit /b 1
)
call .venv\Scripts\activate.bat
python examples\sinal.py %*
pause
