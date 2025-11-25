@echo off
setlocal ENABLEDELAYEDEXPANSION

if exist "..\..\venv\Scripts\activate.bat" (
  call ..\..\venv\Scripts\activate.bat
)

echo [i] faster-whisper quick import & tiny model check (device=auto)
python - <<PYCODE
try:
    from faster_whisper import WhisperModel
    m = WhisperModel("tiny", device="auto")
    print("FAST_WHISPER_OK")
except Exception as e:
    print("FAST_WHISPER_ERROR:", e)
PYCODE

endlocal


