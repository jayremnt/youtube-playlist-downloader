import os
import subprocess
import sys
import json
import threading
import concurrent.futures
from pathlib import Path

CONFIG_FILE = Path.home() / ".yt_downloader_config.json"

class PositionManager:
    """Thread-safe manager to track and assign terminal rows for progress bars."""
    def __init__(self, max_positions):
        self.available_positions = list(range(max_positions))
        self.lock = threading.Lock()

    def get_position(self):
        with self.lock:
            if self.available_positions:
                return self.available_positions.pop(0)
            return 0  # Fallback if we run out of rows

    def release_position(self, pos):
        with self.lock:
            self.available_positions.append(pos)
            self.available_positions.sort()

# Global positioning manager instance
position_manager = None

def load_config():
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            print(f"Warning: Failed to load config, using defaults. Error: {e}")
    return {
        "base_dir": str(Path.home() / "Videos"),
        "folder_name": "YouTube Downloads",
        "cookie_method": "none"
    }

def save_config(config):
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=4)
    except OSError as e:
        print(f"Warning: Failed to save config: {e}")

def ensure_virtualenv():
    """Ensure the script runs within an isolated virtual environment."""
    script_dir = Path(__file__).parent
    requirements_file = script_dir / "requirements.txt"
    
    # Create default requirements.txt if it doesn't exist
    if not requirements_file.exists():
        try:
            with open(requirements_file, "w", encoding="utf-8") as f:
                f.write("yt-dlp\ntqdm\nimageio-ffmpeg\n")
        except OSError as e:
            print(f"Warning: Could not write requirements.txt: {e}")
            
    venv_dir = Path.home() / ".yt_downloader_venv"
    
    if os.name == 'nt':
        venv_python = venv_dir / "Scripts" / "python.exe"
    else:
        venv_python = venv_dir / "bin" / "python"
        
    # If we are already running inside the target venv, just return and execute the rest of the script
    if sys.executable == str(venv_python):
        return
        
    print(f"Setting up an isolated environment at: {venv_dir}")
    
    if not venv_python.exists():
        print("Creating virtual environment... (This only happens once)")
        try:
            subprocess.run([sys.executable, "-m", "venv", str(venv_dir)], check=True)
        except subprocess.CalledProcessError:
            print("Error: Failed to create virtual environment.")
            sys.exit(1)
            
    print(f"Checking and installing required packages from {requirements_file.name}...")
    try:
        subprocess.run([str(venv_python), "-m", "pip", "install", "--upgrade", "pip", "-q"], check=True)
        subprocess.run([str(venv_python), "-m", "pip", "install", "-q", "-r", str(requirements_file)], check=True)
    except subprocess.CalledProcessError:
        print("Error: Failed to install required packages.")
        sys.exit(1)
        
    print("Environment ready! Launching downloader...\n")
    try:
        result = subprocess.run([str(venv_python), *sys.argv])
        sys.exit(result.returncode)
    except KeyboardInterrupt:
        sys.exit(1)

def get_playlist_videos(url, cookie_method=None):
    """Fetch all video URLs and titles from the playlist using yt_dlp Python API."""
    import yt_dlp
    print("Fetching playlist information...")
    
    ydl_opts = {
        'extract_flat': True,
        'quiet': True,
        'no_warnings': True,
    }
    
    if cookie_method:
        # Check if the user provided a file path (cookies.txt) or a browser name
        if Path(cookie_method).is_file():
            ydl_opts['cookiefile'] = cookie_method
        else:
            ydl_opts['cookiesfrombrowser'] = (cookie_method,)
        
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            videos = []
            
            if 'entries' in info:
                # It's a playlist
                for index, entry in enumerate(info['entries'], start=1):
                    if not entry:
                        continue
                        
                    video_url = entry.get('url')
                    if not video_url and entry.get('id'):
                        video_url = f"https://www.youtube.com/watch?v={entry.get('id')}"
                        
                    if video_url:
                        videos.append((index, video_url))
            else:
                # It's a single video
                video_url = info.get('url')
                if not video_url and info.get('id'):
                    video_url = f"https://www.youtube.com/watch?v={info.get('id')}"
                if video_url:
                    videos.append((1, video_url))
            
            return videos
            
    except yt_dlp.utils.DownloadError as e:
        error_msg = str(e)
        if "Could not copy Chrome cookie database" in error_msg:
            print(f"\n[!] BROWSER LOCKED ERROR:")
            print(f"    Your browser ({cookie_method}) is currently OPEN and locking the cookie file.")
            print(f"    Please completely CLOSE the browser (and any background tabs) and run this script again.")
            print(f"    Alternatively, use the 'cookies.txt' file method instead.\n")
        elif "Failed to decrypt with DPAPI" in error_msg:
            print(f"\n[!] WINDOWS ENCRYPTION ERROR:")
            print(f"    Windows is blocking direct cookie extraction from your browser.")
            print(f"    Please use the 'cookies.txt' file workaround described above instead.\n")
        else:
            print(f"Error fetching playlist: {e}")
        return []
    except Exception as e:
        print(f"Unexpected error fetching playlist information: {e}")
        return []

def download_single_video(index, url, download_dir, cookie_method=None):
    """Download a single video using the yt_dlp Python API with a tqdm progress bar."""
    import yt_dlp
    import imageio_ffmpeg
    import re
    from tqdm import tqdm

    # Get an available position for the progress bar
    pos = position_manager.get_position() if position_manager else 0

    pbar = tqdm(total=100, position=pos, leave=True, desc=f"Video {index:03d}", unit="%", bar_format='{desc}: {percentage:3.0f}%|{bar}| {remaining}')

    def progress_hook(d):
        if d['status'] == 'downloading':
            # Extract percentage from the string (e.g., " 45.2%")
            p_str = d.get('_percent_str', '0%').replace('%', '').strip()
            # Remove ANSI color codes that yt-dlp sometimes adds
            p_str = re.sub(r'\x1b\[[0-9;]*m', '', p_str)
            try:
                p_val = float(p_str)
                pbar.n = p_val
                pbar.refresh()
            except ValueError:
                pass
        elif d['status'] == 'finished':
            pbar.n = 100
            pbar.refresh()

    ydl_opts = {
        'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
        'outtmpl': str(download_dir / f"{index:03d} - %(title)s.%(ext)s"),
        'merge_output_format': 'mp4',
        'ffmpeg_location': imageio_ffmpeg.get_ffmpeg_exe(),
        'progress_hooks': [progress_hook],
        'quiet': True,
        'no_warnings': True,
        'nocheckcertificate': True,
    }

    if cookie_method:
        if Path(cookie_method).is_file():
            ydl_opts['cookiefile'] = cookie_method
        else:
            ydl_opts['cookiesfrombrowser'] = (cookie_method,)

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
    except yt_dlp.utils.DownloadError:
        pbar.set_description(f"Video {index:03d} (FAILED)")
    except Exception:
        # Catch other unexpected errors to prevent thread crashes
        pbar.set_description(f"Video {index:03d} (ERROR)")
    finally:
        pbar.close()
        # Release the terminal row for the next video
        if position_manager:
            position_manager.release_position(pos)

def main():
    ensure_virtualenv()
    
    global position_manager
    
    print("=" * 50)
    print("           YouTube Playlist Downloader")
    print("=" * 50)
    print()
    
    try:
        url = input("Please enter the YouTube playlist link: ").strip()
    except (EOFError, KeyboardInterrupt):
        return
    
    if not url:
        print("Error: No link provided. Exiting.")
        return

    config = load_config()

    default_base_dir = config.get("base_dir", str(Path.home() / "Videos"))
    print(f"\n[Base Directory]")
    print(f"Default: {default_base_dir}")
    try:
        user_base_dir = input("Enter new path (or press Enter to use default): ").strip()
    except (EOFError, KeyboardInterrupt):
        return
        
    base_dir_str = user_base_dir if user_base_dir else default_base_dir
    base_dir = Path(base_dir_str)

    default_folder_name = config.get("folder_name", "YouTube Downloads")
    print(f"\n[Playlist Folder Name]")
    print(f"Default: {default_folder_name}")
    try:
        user_folder_name = input("Enter new name (or press Enter to use default): ").strip()
    except (EOFError, KeyboardInterrupt):
        return
        
    folder_name = user_folder_name if user_folder_name else default_folder_name

    script_dir = Path(__file__).parent
    local_cookies_file = script_dir / "cookies.txt"
    
    # Check if the file has actual content (beyond simple comments)
    has_cookies = False
    if local_cookies_file.exists():
        try:
            with open(local_cookies_file, "r", encoding="utf-8") as f:
                content = f.read()
                # A populated cookies.txt usually has a good amount of text and specific domains
                if len(content.strip()) > 100 and ".youtube.com" in content:
                    has_cookies = True
        except OSError:
            pass

    if has_cookies:
        print(f"\n[Cookies] Local 'cookies.txt' found and loaded automatically!")
        print("Bypassing bot blocks using your exported cookies.")
        cookie_method_str = "cookies.txt"
        cookie_method = str(local_cookies_file)
    else:
        print(f"\n[Cookies] No cookies found in your local 'cookies.txt' file.")
        print("To easily bypass YouTube's anti-bot blocks, we highly recommend exporting your cookies:")
        print("1. Install this extension: https://chromewebstore.google.com/detail/get-cookiestxt-locally/cclelndahbckbenkjhflpdbgdldlbecc")
        print("2. Go to youtube.com while logged in and click the extension to export.")
        print("3. Open the file 'cookies.txt' in this folder and paste the contents inside.")
        print("\nFalling back to direct browser extraction...")
        
        default_browser = config.get("cookie_method", "none")
        # If their last saved default was cookies.txt or a path, reset it so we don't crash
        if default_browser == "cookies.txt" or "\\" in default_browser or "/" in default_browser:
            default_browser = "none"
            
        print(f"Default: {default_browser}")
        print("Options: chrome, edge, firefox, brave, opera, vivaldi, safari, none")
        try:
            user_browser = input("Enter browser name (or press Enter to use default): ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            return
            
        cookie_method_str = user_browser if user_browser else default_browser
        cookie_method = cookie_method_str if cookie_method_str != "none" else None

    # Save preferences for next time
    config["base_dir"] = str(base_dir)
    config["folder_name"] = folder_name
    config["cookie_method"] = cookie_method_str
    save_config(config)

    download_dir = base_dir / folder_name
    
    try:
        download_dir.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        print(f"Error creating directory {download_dir}: {e}")
        return
    
    videos = get_playlist_videos(url, cookie_method)
    
    if not videos:
        print("No videos found in the playlist or playlist is private.")
        try:
            input("\nPress Enter to exit...")
        except (EOFError, KeyboardInterrupt):
            pass
        return
        
    max_workers = 8
    print(f"\nFound {len(videos)} videos. Starting parallel download with {max_workers} threads to: {download_dir}")
    print("Please wait, this might take a while depending on the playlist size...\n")
    
    position_manager = PositionManager(max_workers)

    # This prevents overlapping bars in some terminals
    print("\n" * max_workers) 

    # Use ThreadPoolExecutor to run downloads concurrently
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = []
        for index, v_url in videos:
            futures.append(executor.submit(download_single_video, index, v_url, download_dir, cookie_method))
        
        # Wait for all futures to complete
        concurrent.futures.wait(futures)
    
    print("\n" + "=" * 50)
    print("All Downloads Completed!")
    print(f"Files are saved in: {download_dir}")
    print("=" * 50)
    
    try:
        input("\nPress Enter to exit...")
    except (EOFError, KeyboardInterrupt):
        pass

if __name__ == "__main__":
    main()
