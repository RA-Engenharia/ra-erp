@echo off
REM ===========================================================
REM  ATUALIZAR o robo para a versao mais recente -- um clique.
REM  Tenta git pull; se nao houver git, baixa o ZIP mais novo
REM  do GitHub e atualiza os arquivos (preserva .venv e data).
REM ===========================================================
setlocal enabledelayedexpansion
cd /d "%~dp0"

echo ============================================================
echo   ATUALIZADOR DO ROBO
echo ============================================================

REM 1) Se for um repositorio git, o jeito mais rapido e git pull
where git >nul 2>nul
if %errorlevel%==0 (
  if exist ".git" ( echo [git] atualizando... & git pull & goto depois )
  if exist "..\.git" ( echo [git] atualizando... & pushd .. & git pull & popd & goto depois )
)

REM 2) Senao, baixa o ZIP mais recente via PowerShell
set "URL=https://github.com/ra-engenharia/ra-erp/archive/refs/heads/claude/friendly-sagan-ULVZ2.zip"
set "ZIP=%TEMP%\ra_robo.zip"
set "OUT=%TEMP%\ra_robo_extract"

echo [download] baixando a versao mais recente do GitHub...
powershell -NoProfile -Command "$ProgressPreference='SilentlyContinue'; try { Invoke-WebRequest -UseBasicParsing -Uri '%URL%' -OutFile '%ZIP%' } catch { exit 1 }"
if errorlevel 1 (
  echo ERRO: nao consegui baixar. Verifique a internet e tente de novo.
  pause
  exit /b 1
)

echo [extrair] descompactando...
if exist "%OUT%" rmdir /s /q "%OUT%"
powershell -NoProfile -Command "$ProgressPreference='SilentlyContinue'; Expand-Archive -Path '%ZIP%' -DestinationPath '%OUT%' -Force"

echo [copiar] atualizando os arquivos (preservando .venv e seus dados)...
for /d %%D in ("%OUT%\ra-erp-*") do set "SRC=%%D\trading-bot"
if not defined SRC (
  echo ERRO: estrutura inesperada no ZIP.
  pause
  exit /b 1
)
robocopy "!SRC!" "%CD%" /E /XD .venv data __pycache__ .git >nul

echo [limpar] removendo temporarios...
del "%ZIP%" >nul 2>&1
rmdir /s /q "%OUT%" >nul 2>&1

:depois
echo.
echo [setup] garantindo dependencias...
call setup.bat

echo.
echo ============================================================
echo   ATUALIZADO! Para abrir o painel:  painel.bat
echo ============================================================
pause
