@echo off
setlocal EnableExtensions
cd /d "%~dp0"

if /I "%~1"=="help" goto usage
if /I "%~1"=="-h" goto usage
set "CLOSE_MODE=%~1"

if /I "%CLOSE_MODE%"=="--list" (
    echo Listing the BAS-HAR Training Studio server ^(nothing will be closed^)...
) else (
    echo Closing the BAS-HAR Training Studio server started by startup_training_studio.bat...
)
powershell.exe -NoProfile -ExecutionPolicy Bypass -Command ^
  "$dry = $env:CLOSE_MODE -eq '--list';" ^
  "$procs = @(Get-CimInstance Win32_Process | Where-Object { $_.Name -eq 'python.exe' -and $_.CommandLine -like '*bas_har.web.server*' -and $_.CommandLine -like '*--no-start*' });" ^
  "foreach ($p in $procs) { $short = $p.CommandLine.Substring(0, [Math]::Min(110, $p.CommandLine.Length)); if ($dry) { Write-Host ('  would stop PID ' + $p.ProcessId + ': ' + $short) } else { Write-Host ('  stopping PID ' + $p.ProcessId + ': ' + $short); taskkill /PID $p.ProcessId /T /F 2>$null | Out-Null } };" ^
  "if ($procs.Count -eq 0) { Write-Host 'No Training Studio server is running.' } elseif (-not $dry) { Write-Host ('Closed ' + $procs.Count + ' process(es).') }"
exit /b 0

:usage
echo Usage:
echo   close_training_studio.bat          Close the Training Studio server started by startup_training_studio.bat.
echo   close_training_studio.bat --list   Show what would be closed without closing anything.
exit /b 0
