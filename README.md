# YouTube Playlist Downloader

A high-performance Python-based utility designed to download entire YouTube playlists at **maximum quality** with **zero manual configuration**. Featuring parallelized downloads, intelligent anti-bot bypassing, and an automated environment setup.

> **Note:** This was built for personal use and is mostly just *VIBE CODE*. Enjoy it for what it is! 🤙

---

## ✨ Features

*   **🚀 Parallel Processing**: High-speed downloads utilizing up to **8 concurrent threads** with live progress tracking for each.
*   **💎 Maximum Quality**: Automatically fetches the highest available bitrate (4K, 1080p, etc.) and merges them into high-quality MP4/M4A containers.
*   **🍪 Intelligent Cookie Support**: 
    *   **Auto-detects** `cookies.txt` for seamless bypassing of YouTube's age-restrictions and bot-detection.
    *   Supports **direct browser extraction** from Chrome, Edge, Firefox, Brave, and more.
*   **🛠️ Zero Config Setup**: Automatically manages an isolated virtual environment (`venv`) and installs all necessary dependencies (`yt-dlp`, `ffmpeg`, etc.) on first run.
*   **💾 Smart Organization**: Saves videos with numerical prefixes (e.g., `001 - Title.mp4`) to maintain the original playlist order.
*   **⚙️ Persistent Preferences**: Remembers your preferred download folder and settings between sessions via a configuration file.

---

## 📋 Prerequisites

To ensure the best experience and bypass modern YouTube protections, ensure you have:

1.  **[Python 3.8+](https://www.python.org/downloads/)**: Ensure "Add Python to PATH" is checked during installation.

---

## 🚀 Quick Start

1.  **Clone or Download** this repository to your local machine.
2.  **Run the Downloader**:
    *   **Highly Recommended**: Open a terminal and run: `python download_playlist.py`
    *   **Alternative**: Double-click `download_playlist.bat` or `download_playlist.py`.
3.  **Follow the Prompts**:
    *   Paste your playlist URL.
    *   (Optional) Customize your download location.
    *   Wait for the parallel progress bars to finish!

---

## 🛡️ Bypassing Anti-Bot Blocks (Recommended)

YouTube frequently blocks automated tools. To ensure 100% reliability, we recommend using the **Cookie Method**:

1.  Install a "Get cookies.txt" extension (e.g., [Get cookies.txt locally](https://chromewebstore.google.com/detail/get-cookiestxt-locally/cclelndahbckbenkjhflpdbgdldlbecc)).
2.  Visit YouTube while logged in and export your cookies.
3.  Place the exported `cookies.txt` file in the same folder as this script.
4.  The script will automatically detect and use these cookies on your next run.

---
