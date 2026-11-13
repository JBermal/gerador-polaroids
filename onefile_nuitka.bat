@echo off
setlocal

REM Compilacao Nuitka (onefile) - Gerador de Polaroids
REM Requisitos no venv .bancada: pip install -r requirements.txt nuitka

set "SCRIPT_DIR=%~dp0"
set "SCRIPT=polaroid_gui.py"
set "OUTPUT=GeradorPolaroids-1.0.0-r2026-06-26"

set "VENV=%SCRIPT_DIR%.bancada\Scripts\python.exe"

if exist "%VENV%" (
    set "PYTHON=%VENV%"
) else (
    echo ERRO: Ambiente virtual nao encontrado: "%VENV%"
    echo Crie ou ative o venv .bancada antes de compilar.
    exit /b 1
)

if not exist "%SCRIPT_DIR%%SCRIPT%" (
    echo ERRO: Arquivo de entrada nao encontrado: "%SCRIPT_DIR%%SCRIPT%"
    exit /b 1
)

if not exist "%SCRIPT_DIR%photo_engine.py" (
    echo ERRO: Modulo nao encontrado: "%SCRIPT_DIR%photo_engine.py"
    exit /b 1
)

if not exist "%SCRIPT_DIR%assets\logo.png" (
    echo ERRO: Logo nao encontrado: "%SCRIPT_DIR%assets\logo.png"
    exit /b 1
)

if not exist "%SCRIPT_DIR%assets\logo.ico" (
    echo Gerando assets\logo.ico a partir de logo.png...
    "%PYTHON%" -c "from PIL import Image; Image.open(r'%SCRIPT_DIR%assets\logo.png').save(r'%SCRIPT_DIR%assets\logo.ico', format='ICO')"
    if errorlevel 1 (
        echo ERRO: Falha ao gerar logo.ico. Instale Pillow: pip install Pillow
        exit /b 1
    )
)

pushd "%SCRIPT_DIR%"

echo Compilando %SCRIPT% com Nuitka...
echo Python: %PYTHON%
echo.

"%PYTHON%" -m nuitka ^
    --onefile ^
    --show-progress ^
    --lto=yes ^
    --jobs=4 ^
    --python-flag=no_docstrings ^
    --python-flag=no_site ^
    --follow-imports ^
    --enable-plugin=pyqt6 ^
    --windows-console-mode=disable ^
    --windows-icon-from-ico=assets/logo.ico ^
    --product-name="Gerador de Polaroids" ^
    --product-version="1.0.0" ^
    --file-description="Gerador de Polaroids - Plugintech" ^
    --company-name="Plugintech" ^
    --onefile-tempdir-spec={TEMP}\gerador-polaroids ^
    --include-module=photo_engine ^
    --include-package=PIL ^
    --include-data-dir=assets=assets ^
    --msvc=latest ^
    --output-dir=dist_nuitka ^
    --remove-output ^
    --output-filename=%OUTPUT%.exe ^
    --assume-yes-for-downloads ^
    %SCRIPT%

set "NUITKA_EXIT=%ERRORLEVEL%"
popd

echo.
if not "%NUITKA_EXIT%"=="0" (
    echo Falha na compilacao. Codigo: %NUITKA_EXIT%
    exit /b %NUITKA_EXIT%
)

echo Concluido. Execute: %SCRIPT_DIR%dist_nuitka\%OUTPUT%.exe
pause
endlocal
