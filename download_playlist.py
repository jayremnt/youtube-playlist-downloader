import os
import subprocess
import sys
import json
from pathlib import Path

CONFIG_FILE = Path.home() / ".yt_downloader_config.json"

def load_config():
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {
        "base_dir": str(Path.home() / "Videos"),
        "folder_name": "YouTube Downloads"
    }

def save_config(config):
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=4)
    except Exception as e:
        print(f"Warning: Failed to save config: {e}")

def ensure_virtualenv():
    """Ensure the script runs within an isolated virtual environment."""
    script_dir = Path(__file__).parent
    requirements_file = script_dir / "requirements.txt"
    
    # Create default requirements.txt if it doesn't exist
    if not requirements_file.exists():
        with open(requirements_file, "w", encoding="utf-8") as f:
            f.write("yt-dlp\ntqdm\nimageio-ffmpeg\n")
            
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
    """Fetch all video URLs and titles from the playlist."""
    print("Fetching playlist information...")
    command = [
        sys.executable,
        "-m",
        "yt_dlp",
        "--flat-playlist",
        "--dump-json",
        url
    ]
    
    try:
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        videos = []
        # JSON output per line
        import json
        for index, line in enumerate(result.stdout.strip().split('\n'), start=1):
            if not line:
                continue
            try:
                data = json.loads(line)
                video_url = data.get('url', '')
                if not video_url:
                    video_url = f"https://www.youtube.com/watch?v={data.get('id', '')}"
                videos.append((index, video_url))
            except json.JSONDecodeError:
                continue
        return videos
    except subprocess.CalledProcessError:
        print("Failed to fetch playlist information.")
        return []

def download_single_video(index, url, download_dir, pos):
    """Download a single video using the yt_dlp Python API with a tqdm progress bar."""
    from tqdm import tqdm
    import yt_dlp
    import imageio_ffmpeg

    # Initialize a progress bar for this specific thread
    pbar = tqdm(total=100, position=pos, leave=True, desc=f"Video {index:03d}", unit="%", bar_format='{desc}: {percentage:3.0f}%|{bar}| {remaining}')

    def progress_hook(d):
        if d['status'] == 'downloading':
            # Extract percentage from the string (e.g., " 45.2%")
            p_str = d.get('_percent_str', '0%').replace('%', '').strip()
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
    except Exception:
        pbar.set_description(f"Video {index:03d} (FAILED)")
    finally:
        pbar.close()

def main():
    ensure_virtualenv()
    
    print("=" * 50)
    print("           YouTube Playlist Downloader")
    print("=" * 50)
    print()
    
    url = input("Please enter the YouTube playlist link: ").strip()
    
    if not url:
        print("Error: No link provided. Exiting.")
        return

    config = load_config()

    default_base_dir = config.get("base_dir", str(Path.home() / "Videos"))
    print(f"\n[Base Directory]")
    print(f"Default: {default_base_dir}")
    user_base_dir = input("Enter new path (or press Enter to use default): ").strip()
    base_dir_str = user_base_dir if user_base_dir else default_base_dir
    base_dir = Path(base_dir_str)

    default_folder_name = config.get("folder_name", "YouTube Downloads")
    print(f"\n[Playlist Folder Name]")
    print(f"Default: {default_folder_name}")
    user_folder_name = input("Enter new name (or press Enter to use default): ").strip()
    folder_name = user_folder_name if user_folder_name else default_folder_name

    # Save preferences for next time
    config["base_dir"] = str(base_dir)
    config["folder_name"] = folder_name
    save_config(config)

    download_dir = base_dir / folder_name
    
    try:
        download_dir.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        print(f"Error creating directory {download_dir}: {e}")
        return
    
    videos = get_playlist_videos(url)
    
    if not videos:
        print("No videos found in the playlist or playlist is private.")
        input("\nPress Enter to exit...")
        return
        
    print(f"\nFound {len(videos)} videos. Starting parallel download with 8 threads to: {download_dir}")
    print("Please wait, this might take a while depending on the playlist size...\n")
    
    import concurrent.futures
    from tqdm import tqdm

    # This prevents overlapping bars in some terminals
    print("\n" * 8) 

    # Use ThreadPoolExecutor to run up to 8 downloads concurrently
    # We pass the index of the thread (0-7) to position the progress bars
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
        futures = []
        for i, (index, v_url) in enumerate(videos):
            # We use (i % 8) as the terminal line position for the bar
            futures.append(executor.submit(download_single_video, index, v_url, download_dir, i % 8))
        
        # Wait for all futures to complete
        concurrent.futures.wait(futures)
    
    print("\n" + "=" * 50)
    print("All Downloads Completed!")
    print(f"Files are saved in: {download_dir}")
    print("=" * 50)
    
    input("\nPress Enter to exit...")

if __name__ == "__main__":
    main()
