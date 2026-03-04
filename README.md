# YouTube Playlist Downloader

A collection of scripts designed to download entire YouTube playlists at maximum quality with high speed and zero configuration.

## 🚀 Features

- **Parallel Downloads**: Downloads up to 8 videos at once (Python version) or uses 8 concurrent fragments per video (Batch version).
- **Maximum Quality**: Automatically selects the best available video (1080p, 4K, etc.) and audio streams.
- **Windows Optimized**: Forces M4A/AAC audio encoding so downloads play natively in Windows Media Player without extra codecs.
- **Auto-Setup**: Automatically checks for and installs `python`, `pip`, `yt-dlp`, `tqdm` (for progress bars), and `imageio-ffmpeg` (for merging HD video) as needed.
- **Organized Saving**: Saves all videos to your user's `Videos\YouTube Downloads` folder, prefixed with their playlist index (e.g., `001 - Title.mp4`).

## 🛠️ Usage

### Option 1: Python Script (Recommended)
This version features **8 parallel progress bars** and downloads multiple videos simultaneously for maximum speed.

1.  Navigate to the project folder.
2.  Double-click `download_playlist.py` or run:
    ```powershell
    python download_playlist.py
    ```
3.  Paste your YouTube playlist link when prompted.

### Option 2: Windows Batch Script
A simpler version that doesn't require a terminal.

1.  Navigate to the project folder.
2.  Double-click `download_playlist.bat`.
3.  Paste your YouTube playlist link when prompted.

## 📦 Requirements

- **Python**: Must be installed and added to your system PATH.
- **Internet Connection**: Required for the one-time auto-installation of tools and for downloading videos.

## 📂 File Structure

- `download_playlist.py`: The high-performance Python version with live progress tracking.
- `download_playlist.bat`: The quick-start Windows-friendly batch version.
- `README.md`: This documentation file.
