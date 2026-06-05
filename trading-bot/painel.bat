@echo off
REM PAINEL WEB do robo (Windows) -- interface grafica no navegador.
REM Abre o navegador e inicia o servidor. Feche esta janela para encerrar.
setlocal
cd /d "%~dp0"

if not exist ".venv" (
  echo Ambiente nao encontrado. Rode primeiro:  setup.bat
  pause
  exit /b 1
)
call .venv\Scripts\activate.bat
echo Iniciando o painel... o navegador vai abrir em http://127.0.0.1:5000
start "" http://127.0.0.1:5000
python examples\painel.py
pause
