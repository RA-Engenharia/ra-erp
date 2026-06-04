@echo off
REM ===========================================================
REM  ROTINA DIARIA do cerebro (Windows) -- swing, paper trading.
REM  Roda a checagem do dia: analise + decisao de hoje + painel.
REM  Termina sozinho. NENHUMA ordem real, NENHUM dinheiro.
REM
REM    diario.bat                (WEGE3.SA -- nosso campeao)
REM    diario.bat ITUB4.SA       (outro ativo robusto)
REM ===========================================================
setlocal
cd /d "%~dp0"

if not exist ".venv" (
  echo Ambiente nao encontrado. Rode primeiro:  setup.bat
  pause
  exit /b 1
)
call .venv\Scripts\activate.bat
python examples\daily_check.py %*
echo.
echo ===========================================================
echo  Fim da checagem. Rode de novo amanha apos o pregao (apos ~18h).
echo ===========================================================
pause
