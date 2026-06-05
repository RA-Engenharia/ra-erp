@echo off
REM Painel de CARTEIRA (Windows) -- decisao do cerebro para a cesta de acoes.
REM Roda swing diario com aluguel nos shorts. Ordens SIMULADAS. Termina sozinho.
REM   carteira.bat
setlocal
cd /d "%~dp0"

if not exist ".venv" (
  echo Ambiente nao encontrado. Rode primeiro:  setup.bat
  pause
  exit /b 1
)
call .venv\Scripts\activate.bat
python examples\carteira.py
echo.
echo ===========================================================
echo  Fim. Rode de novo amanha apos o pregao (apos ~18h).
echo ===========================================================
pause
