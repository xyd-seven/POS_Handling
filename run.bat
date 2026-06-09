@echo off
title GNSS Precision Analysis Tool Launcher

echo ==================================================
echo   Checking Python running dependencies...
echo ==================================================

py -c "import PySide6, matplotlib, numpy" 2>nul
if %errorlevel% neq 0 (
    echo [Info] Missing required python packages. Installing automatically...
    echo Command: py -m pip install PySide6 matplotlib numpy -i https://mirrors.aliyun.com/pypi/simple/
    py -m pip install PySide6 matplotlib numpy -i https://mirrors.aliyun.com/pypi/simple/
    if %errorlevel% neq 0 (
        echo [Error] Failed to install packages. Please check network and try again.
        pause
        exit /b
    )
)

echo [OK] All dependencies checked. Starting application...
py main.py
if %errorlevel% neq 0 (
    echo [Error] Application crashed or main.py exited with error.
    pause
)
