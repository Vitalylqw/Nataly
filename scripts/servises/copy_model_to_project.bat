@echo off
REM Copy faster-whisper model from system cache to project directory

cd /d "%~dp0\..\.."
call venv\Scripts\activate.bat
python scripts\servises\copy_model_to_project.py

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] Failed to copy model
    pause
    exit /b %ERRORLEVEL%
)

echo.
echo [OK] Model copy completed
pause



