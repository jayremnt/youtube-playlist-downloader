import os
import subprocess
import sys
from pathlib import Path

def check_and_install_packages():
    """Check if pip and yt-dlp are installed, otherwise attempt to install them."""
    try:
        subprocess.run([sys.executable, "-m", "pip", "--version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
    except subprocess.CalledProcessError:
        print("pip is not installed. Attempting to install it automatically...")
        try:
            subprocess.run([sys.executable, "-m", "ensurepip", "--upgrade"], check=True)
            print("pip installed successfully!\n")
        except subprocess.CalledProcessError:
            print("\nError: Failed to install pip automatically. Downloading get-pip.py...")
            try:
                import urllib.request
                urllib.request.urlretrieve("https://bootstrap.pypa.io/get-pip.py", "get-pip.py")
                subprocess.run([sys.executable, "get-pip.py"], check=True)
                os.remove("get-pip.py")
                print("pip installed successfully!\n")
            except Exception as e:
                print(f"Error: {e}")
                print("Please ensure you have an active internet connection or install pip manually.")
                sys.exit(1)

    try:
        subprocess.run([sys.executable, "-m", "yt_dlp", "--version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        # Also check for tqdm and imageio-ffmpeg
        import tqdm
        import imageio_ffmpeg
    except (subprocess.CalledProcessError, ImportError):
        print("Required packages (yt-dlp, tqdm, imageio-ffmpeg) are missing. Attempting to install them...")
        try:
            subprocess.run([sys.executable, "-m", "pip", "install", "yt-dlp", "tqdm", "imageio-ffmpeg"], check=True)
            print("Packages installed successfully!\n")
        except subprocess.CalledProcessError:
            print("\nError: Failed to install required packages.")
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
    check_and_install_packages()
    
    print("=" * 50)
    print("           YouTube Playlist Downloader")
    print("=" * 50)
    print()
    
    url = input("Please enter the YouTube playlist link: ").strip()
    
    if not url:
        print("Error: No link provided. Exiting.")
        return

    # Determine the download directory (Videos/YouTube Downloads)
    download_dir = Path.home() / "Videos" / "YouTube Downloads"
    download_dir.mkdir(parents=True, exist_ok=True)
    
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
