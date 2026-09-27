@echo off
setlocal EnableExtensions
cd /d "%~dp0"

set "PYTHON=%CD%\.venv\Scripts\python.exe"
set "PLAN=%CD%\experiments\red_blue_box\experiment_plan.yaml"
set "YOLO_MODEL=%HALO_MODEL%"
if not defined YOLO_MODEL set "YOLO_MODEL=models\yolo11n.pt"
set "HOST=%HALO_HOST%"
if not defined HOST set "HOST=127.0.0.1"
set "STREAM_ARGS="
if defined HALO_STREAM_TO set "STREAM_ARGS=--stream-to %HALO_STREAM_TO%"
set "WEB_INDEX=%CD%\web\dist\index.html"
set "VIDEO=%USERPROFILE%\Downloads\on cell.mp4"
if not exist "%VIDEO%" set "VIDEO="
if not defined VIDEO for %%F in ("%USERPROFILE%\Downloads\*.mp4") do if exist "%%~fF" if not defined VIDEO set "VIDEO=%%~fF"

if /I "%~1"=="help" goto usage
if /I "%~1"=="-h" goto usage
if /I "%~1"=="--help" goto usage
if not exist "%PYTHON%" goto missing_venv
if not exist "%PLAN%" goto missing_plan
if exist "%~1" goto explicit_video

if /I "%~1"=="test" goto test_only
if /I "%~1"=="verify" goto verify_run
if /I "%~1"=="prepare" goto prepare_training
if /I "%~1"=="annotate" goto annotate_training
if /I "%~1"=="train" goto train_training

call :checks
if errorlevel 1 goto checks_failed

if /I "%~1"=="video" goto video
if /I "%~1"=="video-gui" goto web_video
if /I "%~1"=="web" goto web_video
if /I "%~1"=="live" goto live
if /I "%~1"=="analyze" goto analyze
if /I "%~1"=="sequence" goto analyze
goto web_video

:test_only
call :checks
if errorlevel 1 goto checks_failed
echo.
echo All H.A.L.O. checks passed.
exit /b 0

:verify_run
echo.
"%PYTHON%" -m halo verify
exit /b %ERRORLEVEL%

:prepare_training
set "TRAINING_SOURCE=%~2"
if not defined TRAINING_SOURCE set "TRAINING_SOURCE=%CD%\datasets\red_blue_box\raw\videos"
echo.
echo Preparing YOLO frames from: %TRAINING_SOURCE%
"%PYTHON%" -m scripts.prepare_dataset "%TRAINING_SOURCE%" --dataset "%CD%\datasets\red_blue_box"
exit /b %ERRORLEVEL%

:annotate_training
set "TRAINING_SPLIT=%~2"
if not defined TRAINING_SPLIT set "TRAINING_SPLIT=train"
echo.
echo Opening YOLO annotator for split: %TRAINING_SPLIT%
"%PYTHON%" -m scripts.annotate_dataset "%CD%\datasets\red_blue_box" --split "%TRAINING_SPLIT%"
exit /b %ERRORLEVEL%

:train_training
echo.
echo Training custom YOLO model on %YOLO_MODEL% with device auto...
"%PYTHON%" -m scripts.train_yolo "%CD%\datasets\red_blue_box\data.yaml" --model "%YOLO_MODEL%" --device auto
exit /b %ERRORLEVEL%

:analyze
call :checks
if errorlevel 1 goto checks_failed
set "REQUESTED_VIDEO=%~2"
if defined REQUESTED_VIDEO set "VIDEO=%REQUESTED_VIDEO%"
if not defined VIDEO goto missing_video
if not exist "%VIDEO%" goto missing_video
echo.
echo Analyzing H.A.L.O. sequence: %VIDEO%
"%PYTHON%" -m scripts.analyze_sequence "%PLAN%" "%VIDEO%" --device auto --yolo-model "%YOLO_MODEL%" --require-complete
exit /b %ERRORLEVEL%

:explicit_video
set "VIDEO=%~1"
call :checks
if errorlevel 1 goto checks_failed
goto web_video_start

:live
set "SOURCE=%~2"
if not defined SOURCE set "SOURCE=0"
echo.
echo Starting H.A.L.O. React dashboard on source %SOURCE%...
start "H.A.L.O. web" /b "%PYTHON%" -m halo.web.server --plan "%PLAN%" --source "%SOURCE%" --yolo-model "%YOLO_MODEL%" --host %HOST% --port 5767 %STREAM_ARGS% --open-browser
if errorlevel 1 exit /b %ERRORLEVEL%
echo Dashboard: http://%HOST%:5767
exit /b 0

:video
set "REQUESTED_VIDEO=%~2"
if defined REQUESTED_VIDEO set "VIDEO=%REQUESTED_VIDEO%"
if not defined VIDEO goto missing_video
if not exist "%VIDEO%" goto missing_video
echo.
echo Testing H.A.L.O. with video: %VIDEO%
"%PYTHON%" -m scripts.run_engine "%PLAN%" "%VIDEO%" --yolo-model "%YOLO_MODEL%" --max-frames 60
set "EXIT_CODE=%ERRORLEVEL%"
if not "%EXIT_CODE%"=="0" echo Video test exited with code %EXIT_CODE%.
exit /b %EXIT_CODE%

:web_video
set "REQUESTED_VIDEO=%~2"
if defined REQUESTED_VIDEO set "VIDEO=%REQUESTED_VIDEO%"
:web_video_start
if not defined VIDEO goto missing_video
if not exist "%VIDEO%" goto missing_video
echo.
echo Starting H.A.L.O. React dashboard with video: %VIDEO%
start "H.A.L.O. web" /b "%PYTHON%" -m halo.web.server --plan "%PLAN%" --source "%VIDEO%" --yolo-model "%YOLO_MODEL%" --host %HOST% --port 5767 %STREAM_ARGS% --open-browser
if errorlevel 1 exit /b %ERRORLEVEL%
echo Dashboard: http://%HOST%:5767
exit /b 0

:checks
echo Running pytest...
"%PYTHON%" -m pytest -q
if errorlevel 1 exit /b 1

echo Running Ruff...
"%PYTHON%" -m ruff check .
if errorlevel 1 exit /b 1

echo Checking Ruff formatting...
"%PYTHON%" -m ruff format --check .
if errorlevel 1 exit /b 1

echo Validating the demo plan...
"%PYTHON%" -m halo.schema.cli "%PLAN%" --quiet
if errorlevel 1 exit /b 1

call :ensure_web_build
if errorlevel 1 exit /b 1

echo Running React dashboard smoke test...
"%PYTHON%" scripts\smoke_web.py
if errorlevel 1 exit /b 1
exit /b 0

:ensure_web_build
if not exist "%CD%\web\node_modules" (
    echo Installing React dependencies...
    pushd "%CD%\web"
    call npm install --no-audit --no-fund
    set "EXIT_CODE=%ERRORLEVEL%"
    popd
    if not "%EXIT_CODE%"=="0" exit /b %EXIT_CODE%
)
if not exist "%WEB_INDEX%" (
    echo Building React dashboard...
    pushd "%CD%\web"
    call npm run build
    set "EXIT_CODE=%ERRORLEVEL%"
    popd
    if not "%EXIT_CODE%"=="0" exit /b %EXIT_CODE%
)
exit /b 0

:checks_failed
echo.
echo Checks failed. The dashboard was not started.
exit /b 1

:missing_venv
echo Missing .venv. Create it with Python 3.11, then install .[perception,streaming,voice,dev].
exit /b 1

:missing_plan
echo Missing demo plan: %PLAN%
exit /b 1

:missing_video
echo No MP4 video found. Pass one explicitly: startup.bat web C:\path\to\video.mp4
exit /b 1

:usage
echo Usage:
echo   startup.bat              Run checks and start the React dashboard with Downloads video.
echo   startup.bat test         Run checks only.
echo   startup.bat verify       Reproduce the ISS reference run and verify its signed log.
echo   startup.bat prepare      Extract frames from datasets/red_blue_box/raw/videos.
echo   startup.bat prepare DIR  Extract frames from a video or folder.
echo   startup.bat annotate     Open the local YOLO drag-box labeler for train.
echo   startup.bat annotate val Open the local YOLO drag-box labeler for val.
echo   startup.bat train        Train the custom model on the prepared dataset.
echo   startup.bat video        Run the real engine against the first available Downloads MP4.
echo   startup.bat video FILE   Run the real engine against a specific video.
echo   startup.bat analyze FILE Verify the red/blue pick-return-close sequence and write timed events.
echo   startup.bat FILE         Start the React dashboard with a specific video.
echo   startup.bat web          Start the React dashboard with the first available Downloads MP4.
echo   startup.bat video-gui    Alias for web.
echo   startup.bat live         Start the React dashboard with webcam 0.
echo   startup.bat live 1       Start the React dashboard with webcam 1.
echo   startup.bat live FILE    Start the React dashboard with an MP4 or RTSP source.
echo.
echo   set HALO_STREAM_TO=udp://192.168.1.20:5000   also stream the video to that computer (VLC: udp://@:5000)
echo   set HALO_HOST=0.0.0.0                        let other computers on the network open the dashboard
exit /b 0
