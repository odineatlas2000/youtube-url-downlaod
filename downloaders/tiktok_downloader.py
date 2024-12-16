import os
import json
import sys
import time
import yt_dlp
import traceback
import re
from pathlib import Path

def debug_print(data):
    """Print debug information to stderr"""
    print("DEBUG:", json.dumps(data, indent=2), file=sys.stderr)

def send_progress(data):
    """Send progress data to Node.js"""
    print(json.dumps(data), flush=True)

def get_ffmpeg_path():
    """Get the FFmpeg path relative to the script location"""
    script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    ffmpeg_path = os.path.join(script_dir, 'ffmpeg', 'bin')
    return ffmpeg_path

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

def get_tiktok_info(url):
    """
    Extract video information from TikTok URL
    Returns a dictionary containing video details
    """
    try:
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': True
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            debug_print({"status": "extracting_info", "url": url})
            info = ydl.extract_info(url, download=False)
            
            if not info:
                raise ValueError("Failed to extract video information")
            
            # Process formats with null checks
            formats = []
            if info.get('formats'):
                formats = [{
                    'format_id': f.get('format_id', ''),
                    'ext': f.get('ext', ''),
                    'resolution': f.get('resolution', ''),
                    'filesize': f.get('filesize', 0),
                    'format_note': f.get('format_note', '')
                } for f in info['formats']]
            
            # Get music info with null checks
            music_info = info.get('music_info', {}) or {}
            music_data = {
                'title': music_info.get('title', ''),
                'author': music_info.get('author', ''),
                'duration': music_info.get('duration', 0),
            }
            
            video_info = {
                'title': info.get('title', ''),
                'description': info.get('description', ''),
                'duration': info.get('duration', 0),
                'view_count': info.get('view_count', 0),
                'like_count': info.get('like_count', 0),
                'repost_count': info.get('repost_count', 0),
                'comment_count': info.get('comment_count', 0),
                'upload_date': info.get('upload_date', ''),
                'creator': info.get('creator') or info.get('uploader', ''),
                'creator_id': info.get('creator_id') or info.get('uploader_id', ''),
                'creator_url': info.get('creator_url') or info.get('uploader_url', ''),
                'thumbnail': info.get('thumbnail', ''),
                'music_info': music_data,
                'formats': formats,
                'hashtags': info.get('tags', [])
            }
            
            debug_print({"status": "info_extracted", "title": video_info['title']})
            return video_info
            
    except Exception as e:
        error_info = {
            "status": "error",
            "error": str(e),
            "traceback": traceback.format_exc()
        }
        debug_print(error_info)
        raise

def download_video(url, format_type, download_path):
    """Download a video from TikTok"""
    try:
        # Ensure download directory exists
        os.makedirs(download_path, exist_ok=True)
        
        # Get FFmpeg path
        ffmpeg_path = get_ffmpeg_path()
        debug_print({"message": f"Using FFmpeg from: {ffmpeg_path}"})
        
        if not os.path.exists(os.path.join(ffmpeg_path, 'ffmpeg.exe')):
            raise Exception(f"FFmpeg not found at {ffmpeg_path}")
        
        # Configure yt-dlp options
        ydl_opts = {
            'format': 'bestaudio/best' if format_type.lower() == 'mp3' else 'best',
            'progress_hooks': [lambda d: send_progress({
                "status": "downloading",
                "progress": d.get('percentage', 0),
                "downloaded_bytes": d.get('downloaded_bytes', 0),
                "total_bytes": d.get('total_bytes', 0),
                "speed": d.get('speed', 0),
                "eta": d.get('eta', 0),
                "filename": d.get('filename', '')
            })],
            'outtmpl': os.path.join(download_path, '%(title)s.%(ext)s'),
            'ffmpeg_location': ffmpeg_path,
            'verbose': True,
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
        
        # Download the video
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            try:
                # Get video info first
                debug_print({"status": "info", "message": "Extracting video info"})
                info = ydl.extract_info(url, download=False)
                
                if not info:
                    raise ValueError("Failed to extract video information")

                # Prepare filename
                title = info.get('title', 'tiktok_video')
                ext = 'mp3' if format_type.lower() == 'mp3' else info.get('ext', 'mp4')
                safe_title = sanitize_filename(title)
                base_filename = f"{safe_title}.{ext}"
                
                debug_print({
                    "status": "info",
                    "title": title,
                    "filename": base_filename
                })
                
                # Download the video
                debug_print({"status": "downloading", "message": "Starting download"})
                info = ydl.extract_info(url, download=True)
                
                # Get the actual downloaded file path
                downloaded_path = None
                if info and isinstance(info, dict):
                    if 'requested_downloads' in info and info['requested_downloads']:
                        first_download = info['requested_downloads'][0]
                        if isinstance(first_download, dict) and 'filepath' in first_download:
                            downloaded_path = first_download['filepath']
                
                if not downloaded_path:
                    downloaded_path = os.path.join(download_path, base_filename)
                
                # Verify the download
                if not os.path.exists(downloaded_path):
                    raise ValueError(f"Downloaded file not found at {downloaded_path}")
                
                # Rename file if necessary to ensure safe filename
                final_path = os.path.join(download_path, base_filename)
                if downloaded_path != final_path:
                    os.rename(downloaded_path, final_path)
                
                debug_print({
                    "status": "complete",
                    "filename": base_filename,
                    "message": "Download complete"
                })
                
                print(f"filename: {base_filename}")
                sys.stdout.flush()
                return base_filename
                
            except Exception as e:
                error_msg = str(e)
                debug_print({"status": "error", "error": error_msg, "traceback": traceback.format_exc()})
                send_progress({"status": "error", "error": error_msg})
                raise
                
    except Exception as e:
        error_msg = str(e)
        debug_print({"status": "error", "error": error_msg, "traceback": traceback.format_exc()})
        send_progress({"status": "error", "error": error_msg})
        raise

if __name__ == '__main__':
    if len(sys.argv) != 4:
        print('Usage: python tiktok_downloader.py <url> <format> <download_path>')
        sys.exit(1)
        
    url = sys.argv[1]
    format_type = sys.argv[2]
    download_path = sys.argv[3]
    
    try:
        download_video(url, format_type, download_path)
    except Exception as e:
        debug_print({"error": str(e), "traceback": traceback.format_exc()})
        sys.exit(1)
