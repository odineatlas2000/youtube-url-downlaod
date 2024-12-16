from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import os
import sys
import json
import time
import threading
import shutil
from pathlib import Path
from downloaders.youtube_downloader import download_video as youtube_download
from downloaders.tiktok_downloader import download_video as tiktok_download

app = Flask(__name__)

# Configure CORS
CORS(app, 
     origins=["http://localhost:3000", "http://localhost:3001"],
     supports_credentials=True,
     allow_headers=["Content-Type"],
     methods=["GET", "POST", "OPTIONS"])

# Configure Flask middleware
app.config['JSON_SORT_KEYS'] = False
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max request size

@app.after_request
def after_request(response):
    origin = request.headers.get('Origin')
    if origin in ["http://localhost:3000", "http://localhost:3001"]:
        response.headers['Access-Control-Allow-Origin'] = origin
        response.headers['Access-Control-Allow-Credentials'] = 'true'
        response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
    return response

# Constants
MAX_CONCURRENT_DOWNLOADS = 5
DOWNLOAD_TIMEOUT = 300  # 5 minutes
PROGRESS_TIMEOUT = 30   # 30 seconds
CLEANUP_DELAY = 30      # 30 seconds after completion

# Global state
active_downloads = {}
download_id_to_url = {}

# Create downloads directory
downloads_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'downloads')
os.makedirs(downloads_dir, exist_ok=True)

def debug_print(message):
    """Print debug message to stdout and flush immediately"""
    print(message, flush=True)
    sys.stdout.flush()

def cleanup_download(url, download_id):
    """Clean up a download and its resources"""
    debug_print(f'Cleaning up download: {url} ({download_id})')
    
    if url in active_downloads:
        download = active_downloads[url]
        
        # Only clean up if the download is completed or errored
        if download.get('completed') or download.get('error'):
            # Clean up temporary files
            if 'filename' in download and download['filename']:
                try:
                    filepath = os.path.join(downloads_dir, download['filename'])
                    if os.path.exists(filepath):
                        debug_print(f'Keeping completed file: {filepath}')
                except Exception as e:
                    debug_print(f'Error accessing file: {str(e)}')
            
            # Clean up partial files
            try:
                for file in os.listdir(downloads_dir):
                    if '.part' in file or '.temp' in file:
                        filepath = os.path.join(downloads_dir, file)
                        os.unlink(filepath)
                        debug_print(f'Cleaned up partial file: {filepath}')
            except Exception as e:
                debug_print(f'Error cleaning up partial files: {str(e)}')
            
            # Keep the download info for a while to allow progress checks
            def delayed_cleanup():
                time.sleep(CLEANUP_DELAY)
                active_downloads.pop(url, None)
                download_id_to_url.pop(download_id, None)
                debug_print(f'Download info cleaned up after delay: {url} ({download_id})')
            
            cleanup_thread = threading.Thread(target=delayed_cleanup)
            cleanup_thread.daemon = True
            cleanup_thread.start()
        else:
            debug_print(f'Skipping cleanup for incomplete download: {url} ({download_id})')

def monitor_downloads():
    """Monitor downloads for stalls and timeouts"""
    while True:
        current_time = time.time()
        
        for url, download in list(active_downloads.items()):
            # Check for stalls and timeouts
            is_stalled = current_time - download['last_update'] > PROGRESS_TIMEOUT
            is_timed_out = current_time - download['start_time'] > DOWNLOAD_TIMEOUT
            is_errored = download.get('error')
            is_completed = download.get('completed')
            
            if is_stalled or is_timed_out or is_errored or is_completed:
                debug_print(json.dumps({
                    'status': 'cleanup_needed',
                    'url': url,
                    'is_stalled': is_stalled,
                    'is_timed_out': is_timed_out,
                    'is_errored': is_errored,
                    'is_completed': is_completed
                }))
                cleanup_download(url, download['download_id'])
        
        time.sleep(10)  # Check every 10 seconds

# Start monitoring thread
monitor_thread = threading.Thread(target=monitor_downloads, daemon=True)
monitor_thread.start()

def get_video_info(url, platform):
    """Get video information without downloading"""
    try:
        import yt_dlp
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': True,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            
            if platform.lower() == 'youtube':
                return {
                    'title': info.get('title'),
                    'duration': info.get('duration'),
                    'view_count': info.get('view_count'),
                    'thumbnail': info.get('thumbnail'),
                    'channel': info.get('uploader'),
                    'description': info.get('description'),
                    'upload_date': info.get('upload_date'),
                    'platform': 'youtube'
                }
            elif platform.lower() == 'tiktok':
                return {
                    'title': info.get('title', 'TikTok Video'),
                    'duration': info.get('duration'),
                    'view_count': info.get('view_count'),
                    'thumbnail': info.get('thumbnail'),
                    'channel': info.get('uploader'),
                    'description': info.get('description'),
                    'upload_date': info.get('upload_date'),
                    'platform': 'tiktok',
                    'like_count': info.get('like_count'),
                    'repost_count': info.get('repost_count'),
                    'comment_count': info.get('comment_count')
                }
        return None
    except Exception as e:
        debug_print(f'Error getting video info: {str(e)}')
        return None

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'ok',
        'timestamp': time.time(),
        'temp_dir': downloads_dir
    })

@app.route('/api/download', methods=['POST'])
def download():
    """Download endpoint"""
    try:
        # Get request data with proper error handling
        if not request.is_json:
            return jsonify({
                'status': 'error',
                'message': 'Request must be JSON'
            }), 400

        data = request.get_json()
        if not data:
            return jsonify({
                'status': 'error',
                'message': 'Empty request body'
            }), 400

        # Extract parameters with defaults
        url = data.get('url', '')
        platform = data.get('platform', '')
        format_type = data.get('format', '')

        # Input validation
        if not all([url, platform, format_type]):
            return jsonify({
                'status': 'error',
                'message': 'Missing required parameters'
            }), 400

        # Platform validation
        if platform.lower() not in ['youtube', 'tiktok']:
            return jsonify({
                'status': 'error',
                'message': 'Invalid platform. Must be "youtube" or "tiktok"'
            }), 400

        # Format validation
        if format_type.lower() not in ['mp3', 'mp4']:
            return jsonify({
                'status': 'error',
                'message': 'Invalid format. Must be "mp3" or "mp4"'
            }), 400

        # Check concurrent downloads limit
        if len(active_downloads) >= MAX_CONCURRENT_DOWNLOADS:
            return jsonify({
                'status': 'error',
                'message': 'Too many concurrent downloads. Please try again later.'
            }), 429

        # Check if URL is already being downloaded
        if url in active_downloads:
            download = active_downloads[url]
            current_time = time.time()
            
            # If download is completed or errored, clean it up and allow new download
            if (download.get('completed') or 
                download.get('error') or 
                current_time - download['last_update'] > PROGRESS_TIMEOUT):
                cleanup_download(url, download['download_id'])
            else:
                # Return existing download ID if download is in progress
                return jsonify({
                    'status': 'in_progress',
                    'download_id': download['download_id'],
                    'message': 'Download already in progress'
                })

        # Create download ID and initialize tracking
        download_id = str(int(time.time() * 1000))
        download_info = {
            'download_id': download_id,
            'url': url,
            'platform': platform,
            'format': format_type,
            'progress': 0,
            'start_time': time.time(),
            'last_update': time.time(),
            'completed': False,
            'error': None,
            'filename': None
        }

        # Store in tracking maps
        active_downloads[url] = download_info
        download_id_to_url[download_id] = url

        # Start download in a separate thread
        def do_download():
            try:
                download_func = youtube_download if platform.lower() == 'youtube' else tiktok_download
                filename = download_func(url, format_type, downloads_dir)
                
                if filename:
                    download_info['filename'] = filename
                    download_info['completed'] = True
                    download_info['progress'] = 100
                else:
                    download_info['error'] = 'Download failed'
                
            except Exception as e:
                download_info['error'] = str(e)
                debug_print(json.dumps({
                    'status': 'error',
                    'error': str(e)
                }))

        download_thread = threading.Thread(target=do_download)
        download_thread.start()

        return jsonify({
            'status': 'started',
            'download_id': download_id
        })

    except Exception as e:
        debug_print(f'Download error: {str(e)}')
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/api/video-info', methods=['POST'])
def video_info():
    """Get video information endpoint"""
    try:
        if not request.is_json:
            return jsonify({
                'status': 'error',
                'message': 'Request must be JSON'
            }), 400

        data = request.get_json()
        url = data.get('url', '')
        platform = data.get('platform', '')

        if not all([url, platform]):
            return jsonify({
                'status': 'error',
                'message': 'Missing required parameters'
            }), 400

        info = get_video_info(url, platform)
        if info:
            return jsonify({
                'status': 'success',
                'data': info
            })
        else:
            return jsonify({
                'status': 'error',
                'message': 'Could not fetch video information'
            }), 404

    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/api/progress/<download_id>', methods=['GET'])
def get_progress(download_id):
    """Get download progress"""
    try:
        url = download_id_to_url.get(download_id)
        if not url:
            return jsonify({
                'status': 'error',
                'message': 'Download not found'
            }), 404

        download = active_downloads.get(url)
        if not download:
            return jsonify({
                'status': 'error',
                'message': 'Download not found'
            }), 404

        response = {
            'status': 'error' if download.get('error') else 'completed' if download.get('completed') else 'downloading',
            'progress': download.get('progress', 0),
            'filename': download.get('filename'),
            'error': download.get('error')
        }

        return jsonify(response)

    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/api/download/<download_id>/file', methods=['GET'])
def get_file(download_id):
    """Get downloaded file"""
    try:
        url = download_id_to_url.get(download_id)
        if not url:
            return jsonify({
                'status': 'error',
                'message': 'Download not found'
            }), 404

        download = active_downloads.get(url)
        if not download:
            return jsonify({
                'status': 'error',
                'message': 'Download not found'
            }), 404

        if not download.get('completed'):
            return jsonify({
                'status': 'error',
                'message': 'Download not completed'
            }), 400

        filepath = os.path.join(downloads_dir, download['filename'])
        if not os.path.exists(filepath):
            return jsonify({
                'status': 'error',
                'message': 'File not found'
            }), 404

        return send_file(
            filepath,
            as_attachment=True,
            download_name=download['filename']
        )

    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=3002, debug=True)
