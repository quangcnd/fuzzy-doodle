@echo off
chcp 65001 >nul
title Bo Cong Cu Tu Dong Kiem Tra va Patch Minted C++ / LaTeX / VS Code
cd /d "%~dp0"
python setup_latex_cpp.py %*
echo.
pause
