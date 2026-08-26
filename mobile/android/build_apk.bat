@echo off
setlocal
cd /d "%~dp0"

REM Forward any args (-Dev, -Install, -Bundle) to the PowerShell build script.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0build_apk.ps1" %*
set ERR=%ERRORLEVEL%

if %ERR% neq 0 (
  echo.
  echo Build failed with exit code %ERR%.
  pause
  exit /b %ERR%
)

echo.
pause
exit /b 0
