@echo off
setlocal ENABLEDELAYEDEXPANSION

if exist "..\..\venv\Scripts\activate.bat" (
  call ..\..\venv\Scripts\activate.bat
)

if "%OPENAI_API_KEY%"=="" (
  echo OPENAI_KEY_MISSING
) else (
  echo OPENAI_KEY_PRESENT
)

endlocal


