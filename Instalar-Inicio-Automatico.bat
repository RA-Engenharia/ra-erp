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

REM --- Cria atalho na pasta Inicializar do Windows ---
set "STARTUP=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"
set "ALVO=%~dp0Iniciar-RA-ERP.bat"
set "ATALHO=%STARTUP%\RA-ERP.lnk"

REM Usa PowerShell pra criar o atalho (.lnk)
powershell -NoProfile -Command ^
  "$ws = New-Object -ComObject WScript.Shell; ^
   $s = $ws.CreateShortcut('%ATALHO%'); ^
   $s.TargetPath = '%ALVO%'; ^
   $s.WorkingDirectory = '%~dp0'; ^
   $s.WindowStyle = 7; ^
   $s.Description = 'RA Engenharia ERP - inicio automatico'; ^
   $s.Save()"

if exist "%ATALHO%" (
    echo.
    echo [OK] Inicio automatico ATIVADO!
    echo      Atalho criado em: %STARTUP%
    echo.
    echo  A partir do proximo boot, o sistema sobe sozinho.
    echo  Para acessar agora, use o Iniciar-RA-ERP.bat ou abra
    echo  http://localhost:3040 no navegador.
) else (
    echo.
    echo [ERRO] Nao foi possivel criar o atalho automaticamente.
    echo  Alternativa manual:
    echo  1. Aperte Win+R, digite: shell:startup  e Enter
    echo  2. Copie o arquivo "Iniciar-RA-ERP.bat" pra essa pasta
)
echo.
pause
exit /b 0
