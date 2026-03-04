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
        "folder_name": "YouTube Downloads"
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

def get_playlist_videos(url):
    """Fetch all video URLs and titles from the playlist using yt_dlp Python API."""
    import yt_dlp
    print("Fetching playlist information...")
    
    ydl_opts = {
        'extract_flat': True,
        'quiet': True,
        'no_warnings': True,
    }
    
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
        print(f"Error fetching playlist: {e}")
        return []
    except Exception as e:
        print(f"Unexpected error fetching playlist information: {e}")
        return []

def download_single_video(index, url, download_dir):
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

    # Save preferences for next time
    config["base_dir"] = str(base_dir)
    config["folder_name"] = folder_name
    save_config(config)

    download_dir = base_dir / folder_name
    
    try:
        download_dir.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        print(f"Error creating directory {download_dir}: {e}")
        return
    
    videos = get_playlist_videos(url)
    
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
            futures.append(executor.submit(download_single_video, index, v_url, download_dir))
        
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
