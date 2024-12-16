import sys
import os
import json
import yt_dlp
import logging
import re
import traceback
from datetime import datetime
from pathlib import Path
import subprocess as sp

# Setup logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stderr),
        logging.FileHandler('youtube_downloader.log')
    ]
)

def debug_print(msg):
    """Print debug message to stderr"""
    print(f"DEBUG: {msg}", file=sys.stderr)

def format_bytes(bytes):
    """Format bytes to human readable string"""
    if bytes is None:
        return "0 B"
    for unit in ['B', 'KB', 'MB', 'GB']:
        if bytes < 1024:
            return f"{bytes:.1f} {unit}"
        bytes /= 1024
    return f"{bytes:.1f} TB"

def sanitize_filename(filename):
    """Sanitize filename to be safe for all platforms and encodings"""
    # Remove or replace unsafe characters
    unsafe_chars = r'[<>:"/\\|?*\u0000-\u001F\u007F-\u009F]'
    filename = re.sub(unsafe_chars, '_', filename)
    
    try:
        # Try to encode as ASCII, replacing non-ASCII characters
        filename = filename.encode('ascii', 'ignore').decode('ascii')
    except UnicodeEncodeError:
        # If that fails, try a more aggressive replacement
        filename = ''.join(char if ord(char) < 128 else '_' for char in filename)
    
    # Remove leading/trailing spaces and dots
    filename = filename.strip(' .')
    
    # Ensure filename is not empty
    if not filename:
        filename = 'video'
    
    return filename

def get_ffmpeg_path():
    """Get the FFmpeg path relative to the script location"""
    script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    debug_print(f"Script directory: {script_dir}")
    
    # Try multiple possible FFmpeg locations
    possible_paths = [
        os.path.join(script_dir, 'ffmpeg', 'bin'),
        os.path.join(script_dir, 'ffmpeg'),
        'ffmpeg'  # System PATH
    ]
    
    for path in possible_paths:
        debug_print(f"Checking FFmpeg path: {path}")
        if os.path.isdir(path):
            ffmpeg_exe = os.path.join(path, 'ffmpeg.exe')
            debug_print(f"Checking for ffmpeg.exe at: {ffmpeg_exe}")
            if os.path.exists(ffmpeg_exe):
                debug_print(f"Found ffmpeg.exe at: {ffmpeg_exe}")
                try:
                    # Verify FFmpeg is executable
                    result = sp.run([ffmpeg_exe, '-version'], 
                                         capture_output=True, 
                                         text=True)
                    if result.returncode == 0:
                        debug_print("FFmpeg is executable and working")
                        return path
                    else:
                        debug_print(f"FFmpeg exists but not executable: {result.stderr}")
                except Exception as e:
                    debug_print(f"Error testing FFmpeg: {str(e)}")
            else:
                debug_print("ffmpeg.exe not found in this directory")
    
    debug_print("No working FFmpeg installation found")
    return None

def check_ffmpeg():
    """Check FFmpeg installation"""
    try:
        result = sp.run(['ffmpeg', '-version'], 
                              capture_output=True, 
                              text=True)
        if result.returncode == 0:
            debug_print("FFmpeg is available in system PATH")
            return True
    except FileNotFoundError:
        pass

    # Check in script directory
    script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    ffmpeg_paths = [
        os.path.join(script_dir, 'ffmpeg', 'bin', 'ffmpeg.exe'),
        os.path.join(script_dir, 'ffmpeg', 'ffmpeg.exe'),
    ]
    
    for path in ffmpeg_paths:
        if os.path.exists(path):
            try:
                result = sp.run([path, '-version'], 
                                     capture_output=True, 
                                     text=True)
                if result.returncode == 0:
                    debug_print(f"FFmpeg found at: {path}")
                    os.environ['PATH'] = os.path.dirname(path) + os.pathsep + os.environ['PATH']
                    return True
            except Exception as e:
                debug_print(f"Error testing FFmpeg at {path}: {str(e)}")
    
    debug_print("FFmpeg not found")
    return False

def format_progress(d):
    """Format progress information"""
    if d['status'] == 'downloading':
        progress_data = {
            'status': 'downloading',
            'filename': d.get('info_dict', {}).get('title', 'Unknown Title'),
            'progress': float(d['downloaded_bytes'] * 100 / d['total_bytes']) if d.get('total_bytes') else 0,
            'speed': format_bytes(d.get('speed')),
            'eta': d.get('eta')
        }
        debug_print(json.dumps(progress_data))
    elif d['status'] == 'finished':
        progress_data = {
            'status': 'finished',
            'filename': d.get('info_dict', {}).get('title', 'Unknown Title')
        }
        debug_print(json.dumps(progress_data))

def get_video_info(url):
    """
    Extract video information from YouTube URL
    Returns a dictionary containing video details
    """
    try:
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': True
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            debug_print(json.dumps({'status': 'extracting_info', 'url': url}))
            info = ydl.extract_info(url, download=False)
            
            if not info:
                raise ValueError("Failed to extract video information")
            
            formats = []
            if info.get('formats'):
                formats = [{
                    'format_id': f.get('format_id', ''),
                    'ext': f.get('ext', ''),
                    'resolution': f.get('resolution', ''),
                    'filesize': f.get('filesize', 0),
                    'format_note': f.get('format_note', '')
                } for f in info['formats']]
            
            video_info = {
                'title': info.get('title', ''),
                'description': info.get('description', ''),
                'duration': info.get('duration', 0),
                'view_count': info.get('view_count', 0),
                'like_count': info.get('like_count', 0),
                'upload_date': info.get('upload_date', ''),
                'uploader': info.get('uploader', ''),
                'channel_url': info.get('channel_url', ''),
                'thumbnail': info.get('thumbnail', ''),
                'tags': info.get('tags', []),
                'categories': info.get('categories', []),
                'formats': formats
            }
            
            debug_print(json.dumps({'status': 'info_extracted', 'title': video_info['title']}))
            return video_info
            
    except Exception as e:
        error_info = {
            'status': 'error',
            'error': str(e),
            'traceback': traceback.format_exc()
        }
        debug_print(json.dumps(error_info))
        raise

def download_video(url, format_type, temp_dir):
    """Download video from URL"""
    try:
        # Print initial debug info
        debug_print(json.dumps({
            'status': 'start',
            'url': url,
            'format': format_type,
            'temp_dir': temp_dir
        }))

        # Ensure temp directory exists
        os.makedirs(temp_dir, exist_ok=True)

        # Get FFmpeg path
        ffmpeg_path = get_ffmpeg_path()
        if not ffmpeg_path or not os.path.exists(os.path.join(ffmpeg_path, 'ffmpeg.exe')):
            raise Exception(f"FFmpeg not found at {ffmpeg_path}")

        def progress_hook(d):
            if d['status'] == 'downloading':
                progress_data = {
                    'status': 'downloading',
                    'filename': os.path.basename(d.get('filename', '')),
                    'progress': float(d['downloaded_bytes'] * 100 / d['total_bytes']) if d.get('total_bytes') else 0,
                    'speed': format_bytes(d.get('speed')),
                    'eta': d.get('eta')
                }
                debug_print(json.dumps(progress_data))
            elif d['status'] == 'finished':
                progress_data = {
                    'status': 'complete',
                    'filename': os.path.basename(d.get('filename', ''))
                }
                debug_print(json.dumps(progress_data))

        # Configure yt-dlp options
        ydl_opts = {
            'format': 'bestaudio/best' if format_type.lower() == 'mp3' else 'best',
            'progress_hooks': [progress_hook],
            'ffmpeg_location': ffmpeg_path,
            'outtmpl': os.path.join(temp_dir, '%(title)s.%(ext)s'),
            'retries': 3,
            'socket_timeout': 30,
            'restrictfilenames': True,  # Restrict filenames to ASCII characters
        }

        # Add format-specific options
        if format_type.lower() == 'mp3':
            ydl_opts.update({
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }],
            })

        # Initialize downloader
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # Get video info first
            debug_print(json.dumps({"status": "info", "message": "Extracting video info"}))
            info = ydl.extract_info(url, download=False)
            
            if not info:
                raise ValueError("Failed to extract video information")

            # Prepare filename
            title = info.get('title', 'youtube_video')
            ext = 'mp3' if format_type.lower() == 'mp3' else info.get('ext', 'mp4')
            safe_title = sanitize_filename(title)
            base_filename = f"{safe_title}.{ext}"

            # Send initial file info
            debug_print(json.dumps({
                "status": "info",
                "title": title,
                "filename": base_filename
            }))

            # Download the video
            debug_print(json.dumps({"status": "downloading", "message": "Starting download"}))
            info = ydl.extract_info(url, download=True)

            # Get the actual downloaded file path
            downloaded_path = None
            if info and isinstance(info, dict):
                if 'requested_downloads' in info and info['requested_downloads']:
                    first_download = info['requested_downloads'][0]
                    if isinstance(first_download, dict) and 'filepath' in first_download:
                        downloaded_path = first_download['filepath']

            if not downloaded_path:
                downloaded_path = os.path.join(temp_dir, base_filename)

            # Verify the download
            if not os.path.exists(downloaded_path):
                raise ValueError(f"Downloaded file not found at {downloaded_path}")

            # Rename file if necessary to ensure safe filename
            final_path = os.path.join(temp_dir, base_filename)
            if downloaded_path != final_path and os.path.exists(downloaded_path):
                os.rename(downloaded_path, final_path)

            # Send completion status
            debug_print(json.dumps({
                "status": "complete",
                "filename": base_filename,
                "message": "Download complete"
            }))

            print(f"filename: {base_filename}")
            sys.stdout.flush()
            return base_filename

    except Exception as e:
        error_info = {
            'status': 'error',
            'error': str(e),
            'traceback': traceback.format_exc()
        }
        debug_print(json.dumps(error_info))
        raise

if __name__ == "__main__":
    if len(sys.argv) < 3:
        debug_print("Usage: python youtube_downloader.py <url> <format> [--temp-dir <dir>]")
        sys.exit(1)
        
    url = sys.argv[1]
    format_type = sys.argv[2]
    temp_dir = os.getenv('TEMP_DIR') or os.path.join(os.path.dirname(os.path.dirname(__file__)), 'downloads')
    
    try:
        filename = download_video(url, format_type, temp_dir)
        if filename is not None:
            debug_print(f"Downloaded file: {filename}")
        else:
            debug_print("Download failed")
    except Exception as e:
        debug_print(f"Error: {str(e)}")
        debug_print(f"Traceback: {traceback.format_exc()}")
        sys.exit(1)
