@echo off
setlocal ENABLEDELAYEDEXPANSION

set FF_DIR=%~dp0..\bin\ffmpeg
set FF_EXE=%FF_DIR%\ffmpeg.exe

if exist "%FF_EXE%" (
  echo ffmpeg already exists: %FF_EXE%
  goto :end
)

echo Target: %FF_EXE%
mkdir "%FF_DIR%" 2>nul

where curl >nul 2>&1
if %errorlevel%==0 (
  echo [i] Attempting to download FFmpeg (static build) using curl...
  echo This may require manual update of URL if vendor changes.
  rem Gyan.dev static build (URL may change)
  set URL=https://www.gyan.dev/ffmpeg/builds/ffmpeg-git-essentials.7z
  set ARCHIVE=%FF_DIR%\ffmpeg.7z
  curl -L -o "%ARCHIVE%" "%URL%"
  if exist "%ARCHIVE%" (
    echo [i] Downloaded archive: %ARCHIVE%
    echo [!] Please extract ffmpeg.exe from the archive into: %FF_DIR%
    echo     Then set paths.ffmpeg_bin in src\config\settings.yaml if not in PATH.
    goto :end
  )
)

echo [!] Automatic download failed or curl not found.
echo     Please download static build manually and place ffmpeg.exe to:
echo     %FF_DIR%
echo     Examples:
echo       - https://www.gyan.dev/ffmpeg/builds/
echo       - https://github.com/BtbN/FFmpeg-Builds/releases

:end
endlocal


