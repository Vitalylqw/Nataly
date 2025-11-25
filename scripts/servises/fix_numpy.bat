@echo off
echo Downgrading numpy to <2.0...
venv\Scripts\python.exe -m pip install "numpy<2.0"
echo Done.
pause


