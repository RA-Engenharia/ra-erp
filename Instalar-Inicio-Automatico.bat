@echo off
chcp 65001 >nul
title RA ERP - Instalar Inicio Automatico
cd /d "%~dp0"

echo ===============================================================
echo    RA ENGENHARIA ERP - Inicio Automatico com o Windows
echo ===============================================================
echo.
echo  Isso faz o servidor do ERP subir SOZINHO toda vez que voce
echo  liga o computador e faz login no Windows. Voce nao precisa
echo  mais abrir o CMD nem rodar nada manualmente.
echo.
echo  Pasta atual: %~dp0
echo.
set /p CONFIRM="Deseja ativar o inicio automatico? (S/N): "
if /i not "%CONFIRM%"=="S" (
    echo Cancelado.
    pause
    exit /b 0
)

set "STARTUP=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"
set "ATALHO=%STARTUP%\RA-ERP.lnk"

REM Descobre o nome real do iniciador (navegador as vezes tira hifens)
set "ALVO="
if exist "%~dp0Iniciar-RA-ERP.bat" set "ALVO=%~dp0Iniciar-RA-ERP.bat"
if not defined ALVO if exist "%~dp0IniciarRAERP.bat" set "ALVO=%~dp0IniciarRAERP.bat"
if not defined ALVO for %%F in ("%~dp0Iniciar*.bat") do set "ALVO=%%F"
if not defined ALVO (
    echo [ERRO] Nao encontrei o arquivo "Iniciar-RA-ERP.bat" nesta pasta.
    echo  Confira se ele esta em: %~dp0
    pause
    exit /b 1
)
echo  Iniciador encontrado: %ALVO%
echo.

REM Comando PowerShell em UMA linha (sem caret de continuacao)
powershell -NoProfile -ExecutionPolicy Bypass -Command "$ws = New-Object -ComObject WScript.Shell; $s = $ws.CreateShortcut('%ATALHO%'); $s.TargetPath = '%ALVO%'; $s.WorkingDirectory = '%~dp0'; $s.WindowStyle = 7; $s.Description = 'RA Engenharia ERP'; $s.Save()"

if exist "%ATALHO%" (
    echo.
    echo [OK] Inicio automatico ATIVADO!
    echo      Atalho criado em: %STARTUP%
    echo.
    echo  A partir do proximo boot, o sistema sobe sozinho.
    echo  Para acessar agora, rode Iniciar-RA-ERP.bat ou abra
    echo  http://localhost:3040 no navegador.
) else (
    echo.
    echo [ERRO] Nao foi possivel criar o atalho automaticamente.
    echo  Alternativa manual ^(funciona 100%%^):
    echo  1. Aperte Win+R, digite: shell:startup  e de Enter
    echo  2. Copie o arquivo "Iniciar-RA-ERP.bat" pra pasta que abriu
    echo     ^(pode ser copiar e colar normal mesmo^)
)
echo.
pause
exit /b 0
