@echo off
setlocal EnableExtensions
cd /d "%~dp0"

if /I "%~1"=="help" goto usage
if /I "%~1"=="-h" goto usage
set "CLOSE_MODE=%~1"

if /I "%CLOSE_MODE%"=="--list" (
    echo Listing BAS-HAR processes started by startup.bat ^(nothing will be closed^)...
) else (
    echo Closing BAS-HAR processes started by startup.bat...
)
powershell.exe -NoProfile -ExecutionPolicy Bypass -Command ^
  "$root = (Get-Location).Path; $dry = $env:CLOSE_MODE -eq '--list';" ^
  "$scripts = @('*scripts.prepare_dataset*', '*scripts.annotate_dataset*', '*scripts.train_yolo*', '*scripts.analyze_sequence*', '*scripts.run_engine*', '*smoke_web.py*', '*-m pytest*', '*bas_har.schema.cli*');" ^
  "$procs = @();" ^
  "foreach ($p in @(Get-CimInstance Win32_Process | Where-Object { $_.Name -eq 'python.exe' -and $_.CommandLine })) {" ^
  "  $cmd = $p.CommandLine;" ^
  "  if ($cmd -like '*bas_har.web.server*' -and $cmd -notlike '*--no-start*') { $procs += $p; continue };" ^
  "  if ($cmd -like ('*' + $root + '*')) { foreach ($pattern in $scripts) { if ($cmd -like $pattern) { $procs += $p; break } } }" ^
  "};" ^
  "foreach ($p in $procs) { $short = $p.CommandLine.Substring(0, [Math]::Min(110, $p.CommandLine.Length)); if ($dry) { Write-Host ('  would stop PID ' + $p.ProcessId + ': ' + $short) } else { Write-Host ('  stopping PID ' + $p.ProcessId + ': ' + $short); taskkill /PID $p.ProcessId /T /F 2>$null | Out-Null } };" ^
  "if ($procs.Count -eq 0) { Write-Host 'No startup.bat processes are running.' } elseif (-not $dry) { Write-Host ('Closed ' + $procs.Count + ' process(es).') }"
exit /b 0

:usage
echo Usage:
echo   close_startup.bat          Close the dashboard server and any training/analysis scripts started by startup.bat.
echo   close_startup.bat --list   Show what would be closed without closing anything.
exit /b 0
