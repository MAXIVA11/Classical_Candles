@echo off
REM Classical Candles setup: creates a virtualenv and installs everything needed.
setlocal enabledelayedexpansion

echo Classical Candles - setup
echo.

where python >nul 2>nul
if errorlevel 1 (
    echo [X] Python 3.10+ not found. Install it from https://python.org and re-run this script.
    exit /b 1
)
for /f "tokens=*" %%v in ('python --version 2^>^&1') do set PYVER=%%v
echo %PYVER% | findstr /r "^Python 3\.[0-9]" >nul
if errorlevel 1 (
    echo [X] "python" on PATH doesn't look like a real Python 3 install ^(got: %PYVER%^).
    echo     This is often a Microsoft Store alias stub. Install Python from
    echo     https://python.org, or disable the alias under Settings ^>
    echo     Apps ^> Advanced app settings ^> App execution aliases.
    exit /b 1
)
echo [OK] Found %PYVER%

where ffmpeg >nul 2>nul
if errorlevel 1 (
    echo [!] FFmpeg not found on PATH.
    echo     Windows: winget install ffmpeg
    echo     Classical Candles needs it to pull audio and ^(optionally^) export video.
) else (
    echo [OK] Found ffmpeg
)

echo.
echo Creating virtual environment in .venv ...
python -m venv .venv

call .venv\Scripts\activate.bat

echo Installing dependencies ...
python -m pip install --quiet --upgrade pip
python -m pip install --quiet -r requirements.txt

echo.
echo Listed and ready.
echo Start the exchange with:
echo.
echo   .venv\Scripts\activate
echo   python webapp\server.py
echo.
echo Then open http://127.0.0.1:5000 and paste a link.
