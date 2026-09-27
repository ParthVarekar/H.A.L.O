@echo off
setlocal EnableExtensions
cd /d "%~dp0"

set "PYTHON=%CD%\.venv\Scripts\python.exe"
set "PLAN=%CD%\experiments\red_blue_box\experiment_plan.yaml"
set "WEB_INDEX=%CD%\web\dist\index.html"

if not exist "%PYTHON%" goto missing_venv
if not exist "%PLAN%" goto missing_plan

if not exist "%WEB_INDEX%" (
    if not exist "%CD%\web\node_modules" (
        echo Installing React dependencies...
        pushd "%CD%\web"
        call npm.cmd install --no-audit --no-fund
        set "EXIT_CODE=%ERRORLEVEL%"
        popd
        if not "%EXIT_CODE%"=="0" exit /b %EXIT_CODE%
    )
    echo Building React dashboard...
    pushd "%CD%\web"
    call npm.cmd run build
    set "EXIT_CODE=%ERRORLEVEL%"
    popd
    if not "%EXIT_CODE%"=="0" exit /b %EXIT_CODE%
)

powershell.exe -NoProfile -Command "try { Invoke-WebRequest -UseBasicParsing -Uri 'http://127.0.0.1:5767/api/health' -TimeoutSec 1 | Out-Null; exit 0 } catch { exit 1 }" >nul 2>&1
if errorlevel 1 (
    echo Starting H.A.L.O. Training Studio server...
    start "H.A.L.O. Training Studio" /b "%PYTHON%" -m halo.web.server --plan "%PLAN%" --yolo-model "models\yolo11n.pt" --device auto --host 127.0.0.1 --port 5767 --no-start >nul 2>&1
    for /l %%I in (1,1,20) do (
        powershell.exe -NoProfile -Command "try { Invoke-WebRequest -UseBasicParsing -Uri 'http://127.0.0.1:5767/api/health' -TimeoutSec 1 | Out-Null; exit 0 } catch { exit 1 }" >nul 2>&1
        if not errorlevel 1 goto open_studio
        timeout /t 1 /nobreak >nul
    )
    echo Training Studio server did not become ready on port 5767.
    exit /b 1
)

:open_studio
start "" "http://127.0.0.1:5767/?workspace=studio"
echo Training Studio: http://127.0.0.1:5767/?workspace=studio
exit /b 0

:missing_venv
echo Missing .venv. Create it with Python 3.11, then install .[perception,streaming,voice,dev].
exit /b 1

:missing_plan
echo Missing demo plan: %PLAN%
exit /b 1
