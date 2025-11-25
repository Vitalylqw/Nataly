@echo off
setlocal ENABLEDELAYEDEXPANSION

if exist "..\..\venv\Scripts\activate.bat" (
  call ..\..\venv\Scripts\activate.bat
) else (
  echo [i] Tip: create venv via: python -m venv venv
)

if "%TELEGRAM_TOKEN%"=="" (
  echo [!] TELEGRAM_TOKEN is empty. Set it in .env and reactivate venv.
)

echo [i] Starting bot (polling)...
python -m src.app

endlocal


