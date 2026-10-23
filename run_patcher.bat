@echo off
chcp 65001 >nul
set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8
title Bo Cong Cu Tu Dong Kiem Tra va Patch Minted C++ / LaTeX / VS Code
cd /d "%~dp0"

py -3 --version >nul 2>&1
if %errorlevel% equ 0 (
    py -3 setup_latex_cpp.py %*
) else (
    python setup_latex_cpp.py %*
)

set EXITCODE=%errorlevel%
echo.
if %EXITCODE% neq 0 (
    echo [!] Chuong trinh ket thuc voi ma loi: %EXITCODE%
)
pause
exit /b %EXITCODE%
