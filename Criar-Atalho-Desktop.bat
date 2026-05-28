@echo off
chcp 65001 >nul
title RA ERP - Criar Atalho na Area de Trabalho

echo ===============================================================
echo    RA ENGENHARIA ERP - Atalho na Area de Trabalho
echo ===============================================================
echo.
echo  Cria um atalho "RA ERP" na sua Area de Trabalho que abre o
echo  sistema direto no navegador (http://localhost:3040).
echo.
pause

set "DESKTOP=%USERPROFILE%\Desktop"
if not exist "%DESKTOP%" set "DESKTOP=%USERPROFILE%\OneDrive\Desktop"
set "ATALHO=%DESKTOP%\RA ERP.url"

REM Cria um atalho de internet (.url) apontando pro sistema local
(
echo [InternetShortcut]
echo URL=http://localhost:3040/
echo IconIndex=0
) > "%ATALHO%"

if exist "%ATALHO%" (
    echo.
    echo [OK] Atalho criado na Area de Trabalho: "RA ERP"
    echo      Basta dar duplo-clique pra abrir o sistema.
    echo      ^(o servidor precisa estar rodando - use Iniciar-RA-ERP.bat
    echo       ou deixe o inicio automatico ativado^)
) else (
    echo.
    echo [ERRO] Nao consegui criar na Area de Trabalho.
    echo  Crie manualmente: abra o navegador em http://localhost:3040
    echo  e arraste o cadeado/icone da barra de endereco pra Area de Trabalho.
)
echo.
pause
exit /b 0
