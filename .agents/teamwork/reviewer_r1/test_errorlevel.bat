@echo off
setlocal
py -3 --version >nul 2>&1
if %errorlevel% equ 0 (
    cmd /c exit 42
) else (
    cmd /c exit 1
)
set EXITCODE=%errorlevel%
echo Captured exitcode: %EXITCODE%
exit /b %EXITCODE%
