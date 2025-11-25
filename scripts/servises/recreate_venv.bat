@echo off
echo ============================================================
echo Recreating Virtual Environment for Nataly Transcriber
echo ============================================================

cd /d D:\work_d\Projects\Nataly

echo.
echo Step 1: Removing old venv...
if exist venv (
    echo   Removing venv directory...
    rmdir /s /q venv
    if %errorlevel% neq 0 (
        echo   ERROR: Failed to remove old venv
        echo   Please close any programs using venv and try again
        pause
        exit /b 1
    )
    echo   Done: Old venv removed
) else (
    echo   No old venv found
)

echo.
echo Step 2: Creating new venv...
python -m venv venv
if %errorlevel% neq 0 (
    echo   ERROR: Failed to create venv
    echo   Make sure Python 3.10+ is installed
    pause
    exit /b 1
)
echo   Done: New venv created

echo.
echo Step 3: Activating venv...
call venv\Scripts\activate.bat

echo.
echo Step 4: Upgrading pip, setuptools, wheel...
python -m pip install --upgrade pip setuptools wheel
if %errorlevel% neq 0 (
    echo   ERROR: Failed to upgrade pip
    pause
    exit /b 1
)

echo.
echo Step 5: Installing dependencies from requirements.txt...
echo   This may take a few minutes...
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo   ERROR: Failed to install dependencies
    pause
    exit /b 1
)
echo   Done: Dependencies installed

echo.
echo Step 6: Installing project in editable mode...
pip install -e .
if %errorlevel% neq 0 (
    echo   WARNING: Failed to install in editable mode
    echo   This is not critical, continuing...
)

echo.
echo Step 7: Verifying installation...
python -c "import ctranslate2; print('ctranslate2:', ctranslate2.__version__)"
python -c "import faster_whisper; print('faster-whisper: OK')"
python -c "import openai; print('openai: OK')"
python -c "import aiogram; print('aiogram: OK')"
if %errorlevel% neq 0 (
    echo   WARNING: Some imports failed
    echo   Please check the error messages above
)

echo.
echo Step 8: Checking CUDA support...
python -c "import ctranslate2; print('CUDA compute types:', ctranslate2.get_supported_compute_types('cuda'))"

echo.
echo ============================================================
echo SUCCESS: Virtual environment recreated!
echo ============================================================
echo.
echo Next steps:
echo   1. Activate venv: venv\Scripts\activate
echo   2. Test transcription: python scripts\test\test_voce_simple.py
echo.
echo Note: faster-whisper uses ctranslate2 (NOT PyTorch)
echo       CUDA support is built-in if NVIDIA drivers are installed
echo.
pause
