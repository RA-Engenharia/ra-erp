@echo off
chcp 65001 >nul
title RA ENGENHARIA ERP - Servidor
cd /d "%~dp0"

echo ===============================================================
echo    RA ENGENHARIA ERP - Iniciando...
echo ===============================================================
echo.

REM --- Verifica se o Node.js esta instalado ---
where node >nul 2>nul
if errorlevel 1 (
    echo [ERRO] Node.js nao encontrado.
    echo Baixe e instale em https://nodejs.org  ^(versao LTS^)
    echo Depois rode este arquivo de novo.
    echo.
    pause
    exit /b 1
)

REM --- Descobre o nome do arquivo do servidor (com ou sem hifen) ---
set "SERVER="
if exist "sinapi-fetcher.js" set "SERVER=sinapi-fetcher.js"
if not defined SERVER if exist "sinapifetcher.js" set "SERVER=sinapifetcher.js"
if not defined SERVER (
    echo [ERRO] Arquivo do servidor nao encontrado nesta pasta.
    echo Esperado: sinapi-fetcher.js
    echo.
    pause
    exit /b 1
)

REM --- Instala dependencias na primeira vez ---
if not exist "node_modules\xlsx" (
    echo [SETUP] Instalando dependencias ^(so na primeira vez^)...
    call npm install xlsx adm-zip
    echo.
)

REM --- Sobe o servidor em janela minimizada ---
echo [OK] Iniciando servidor em http://localhost:3040 ...
start "RA ERP Servidor" /min cmd /c "node %SERVER%"

REM --- Espera o servidor subir e abre o navegador ---
echo [OK] Abrindo o sistema no navegador...
timeout /t 4 /nobreak >nul
start "" "http://localhost:3040/"

echo.
echo ===============================================================
echo  Sistema aberto no navegador!
echo  O servidor roda numa janela minimizada na barra de tarefas.
echo  Para PARAR o servidor: feche aquela janela "RA ERP Servidor".
echo ===============================================================
echo.
echo  Pode fechar ESTA janela.
timeout /t 6 /nobreak >nul
exit /b 0
