@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion
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

REM Lista todos os .bat da pasta (menos este e o desinstalador) e
REM permite escolher qual e o iniciador. Tolerante a qualquer renomeacao.
set "MEU_NOME=%~nx0"
set "CONTADOR=0"
echo  Arquivos .bat encontrados nesta pasta:
echo  -------------------------------------------------
for %%F in ("%~dp0*.bat") do (
    set "NOMEARQ=%%~nxF"
    if /i not "!NOMEARQ!"=="!MEU_NOME!" if /i not "!NOMEARQ!"=="Remover-Inicio-Automatico.bat" if /i not "!NOMEARQ!"=="RemoverInicioAutomatico.bat" if /i not "!NOMEARQ!"=="Criar-Atalho-Desktop.bat" if /i not "!NOMEARQ!"=="CriarAtalhoDesktop.bat" (
        set /a CONTADOR+=1
        set "OPT_!CONTADOR!=%%~fF"
        echo   [!CONTADOR!] %%~nxF
    )
)
echo  -------------------------------------------------
echo.

if "%CONTADOR%"=="0" (
    echo [ERRO] Nenhum arquivo .bat de iniciador encontrado nesta pasta.
    echo  Salve o "Iniciar-RA-ERP.bat" nesta pasta e rode de novo.
    pause
    exit /b 1
)

if "%CONTADOR%"=="1" (
    set "ALVO=!OPT_1!"
    echo  Achei 1 candidato. Usar este?
    set /p CONFIRM="(S/N): "
    if /i not "!CONFIRM!"=="S" (
        echo Cancelado.
        pause
        exit /b 0
    )
) else (
    set /p ESCOLHA="Digite o numero do arquivo iniciador (1-%CONTADOR%): "
    set "ALVO=!OPT_%ESCOLHA%!"
    if not defined ALVO (
        echo Opcao invalida.
        pause
        exit /b 1
    )
)

echo.
echo  Iniciador escolhido: !ALVO!
echo.

set "STARTUP=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"
set "ATALHO=%STARTUP%\RA-ERP.lnk"

powershell -NoProfile -ExecutionPolicy Bypass -Command "$ws = New-Object -ComObject WScript.Shell; $s = $ws.CreateShortcut('%ATALHO%'); $s.TargetPath = '!ALVO!'; $s.WorkingDirectory = '%~dp0'; $s.WindowStyle = 7; $s.Description = 'RA Engenharia ERP'; $s.Save()"

if exist "%ATALHO%" (
    echo.
    echo [OK] Inicio automatico ATIVADO!
    echo      Atalho criado em: %STARTUP%
    echo.
    echo  A partir do proximo boot, o sistema sobe sozinho.
    echo  Para acessar agora, rode o iniciador ou abra
    echo  http://localhost:3040 no navegador.
) else (
    echo.
    echo [ERRO] Nao foi possivel criar o atalho automaticamente.
    echo  Alternativa manual ^(100%% confiavel^):
    echo  1. Aperte Win+R, digite: shell:startup  e de Enter
    echo  2. Copie o arquivo iniciador pra pasta que abriu
)
echo.
pause
exit /b 0
