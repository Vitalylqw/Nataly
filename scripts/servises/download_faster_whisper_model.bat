@echo off
setlocal ENABLEDELAYEDEXPANSION

rem Resolve project root relative to this script
set "SCRIPT_DIR=%~dp0"
pushd "%SCRIPT_DIR%\..\.."

set "VENV_PY=venv\Scripts\python.exe"
if not exist "%VENV_PY%" (
  echo [i] Virtualenv not found at venv\Scripts\python.exe
  echo [i] Create and activate venv, then install faster-whisper:
  echo     python -m venv venv
  echo     venv\Scripts\activate.bat
  echo     python -m pip install -U pip faster-whisper
  popd
  endlocal
  exit /b 1
)

406rem Ensure src package is importable
set "PYTHONPATH=%CD%;%PYTHONPATH%"

set "DL_SCRIPT=scripts\servises\download_faster_whisper_model.py"
if not exist "%DL_SCRIPT%" (
  echo [!] Script not found: %DL_SCRIPT%
  popd
  endlocal
  exit /b 1
)

echo Ensuring faster-whisper model (arguments pass-through: %*)
"%VENV_PY%" "%DL_SCRIPT%" %*
set "EXIT_CODE=%ERRORLEVEL%"

popd
endlocal & exit /b %EXIT_CODE%

pause


