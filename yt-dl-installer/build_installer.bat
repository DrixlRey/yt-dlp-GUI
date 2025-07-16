@echo off
REM Build script for YouTube Downloader GUI Installer

echo Building YouTube Downloader GUI Installer...
echo.

REM Create minimal versions.nsh for FFmpeg and yt-dlp (Python is now checked at runtime)
echo Step 1: Creating version definitions...
echo ; Version definitions - FFmpeg and yt-dlp use latest redirects > versions.nsh
echo !define FFMPEG_VERSION "latest" >> versions.nsh
echo !define YTDLP_VERSION "latest" >> versions.nsh
echo. >> versions.nsh
echo ; Download URLs >> versions.nsh
echo !define FFMPEG_URL "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip" >> versions.nsh
echo !define YTDLP_URL "https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp.exe" >> versions.nsh
echo. >> versions.nsh
echo ; Installation paths >> versions.nsh
echo !define FFMPEG_INSTALL_DIR "$PROGRAMFILES64\FFmpeg" >> versions.nsh
echo !define APP_INSTALL_DIR "$PROGRAMFILES64\YouTube Downloader GUI" >> versions.nsh

echo.
echo Step 2: Building installer with NSIS...

REM Check if NSIS is installed
if exist "C:\Program Files (x86)\NSIS\makensis.exe" (
    set NSIS_PATH="C:\Program Files (x86)\NSIS\makensis.exe"
) else if exist "C:\Program Files\NSIS\makensis.exe" (
    set NSIS_PATH="C:\Program Files\NSIS\makensis.exe"
) else (
    echo ERROR: NSIS not found!
    echo Please install NSIS from: https://nsis.sourceforge.io/Download
    pause
    exit /b 1
)

REM Build the installer
%NSIS_PATH% installer.nsi

if errorlevel 1 (
    echo Build failed!
    pause
    exit /b 1
) else (
    echo.
    echo SUCCESS: YouTube-Downloader-GUI-Installer.exe created!
    echo.
    echo The installer is ready and includes:
    echo - Python check (must be pre-installed)
    echo - PyQt6 (via pip)
    echo - FFmpeg (added to PATH)
    echo - yt-dlp (via pip)
    echo - Your GUI application
    echo.
    pause
)