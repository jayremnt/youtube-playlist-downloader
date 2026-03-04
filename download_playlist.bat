@echo off
setlocal
title YouTube Playlist Downloader

REM Check if python is installed
where /q python
if ERRORLEVEL 1 (
    echo Error: Python is not installed or not added to your PATH.
    echo Please download and install Python from https://www.python.org/downloads/
    echo Make sure to check "Add Python to PATH" during installation.
    pause
    exit /b
)

REM Check if pip is installed
where /q pip
if ERRORLEVEL 1 (
    echo pip is not installed. Attempting to install it automatically...
    python -m ensurepip --upgrade
    if ERRORLEVEL 1 (
        echo Ensurepip failed, downloading get-pip.py...
        curl -sSL https://bootstrap.pypa.io/get-pip.py -o get-pip.py
        python get-pip.py
        del get-pip.py
        if ERRORLEVEL 1 (
            echo.
            echo Error: Failed to install pip automatically.
            pause
            exit /b
        )
    )
    echo pip installed successfully!
    echo.
)

REM Check if yt-dlp is installed, automatically install if missing
python -m yt_dlp --version >nul 2>&1
if ERRORLEVEL 1 (
    echo yt-dlp is not installed. Attempting to install it automatically...
    python -m pip install yt-dlp
    if ERRORLEVEL 1 (
        echo.
        echo Error: Failed to install yt-dlp. 
        pause
        exit /b
    )
    echo yt-dlp installed successfully!
    echo.
)

REM Set the download directory to a "YouTube Downloads" folder inside the user's Videos folder
set "DOWNLOAD_DIR=%USERPROFILE%\Videos\YouTube Downloads"

REM Create the download directory if it doesn't exist
if not exist "%DOWNLOAD_DIR%" (
    mkdir "%DOWNLOAD_DIR%"
)

echo ===================================================
echo             YouTube Playlist Downloader
echo ===================================================
echo.
set /p "URL=Please enter the YouTube playlist link: "

if "%URL%"=="" (
    echo Error: No link provided.
    echo.
    pause
    exit /b
)

echo.
echo Starting download to: %DOWNLOAD_DIR%
echo Please wait, this might take a while depending on the playlist size...
echo.

REM Arguments for yt-dlp:
REM --yes-playlist : Confirms it's a playlist
REM -f : Explicitly request the best video and best audio available
REM --merge-output-format : Merge them into an MP4 file (Requires FFmpeg for >720p on YouTube)
REM --concurrent-fragments 8 : Download fragments concurrently using 8 threads to speed up single-video downloads.
python -m yt_dlp --yes-playlist -i -f "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best" --merge-output-format mp4 --concurrent-fragments 8 -o "%DOWNLOAD_DIR%\%%(playlist_index)03d - %%(title)s.%%(ext)s" "%URL%"

echo.
echo ===================================================
echo Download Completed!
echo Files are saved in: %DOWNLOAD_DIR%
echo ===================================================
echo.
pause
