@echo off
chcp 65001 >nul
title RA ERP - Remover Inicio Automatico

set "ATALHO=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\RA-ERP.lnk"

echo ===============================================================
echo    RA ENGENHARIA ERP - Remover Inicio Automatico
echo ===============================================================
echo.

if exist "%ATALHO%" (
    del "%ATALHO%"
    echo [OK] Inicio automatico REMOVIDO.
    echo      O sistema nao sobe mais sozinho no boot.
    echo      Voce ainda pode abrir manualmente com Iniciar-RA-ERP.bat
) else (
    echo [INFO] Inicio automatico nao estava ativado ^(nada a remover^).
)
echo.
pause
exit /b 0
