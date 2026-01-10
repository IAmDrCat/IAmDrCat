from flask import Flask, send_from_directory, request, send_file, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
import os

load_dotenv()
import yt_dlp
import os
import re
import threading
import uuid
import time

app = Flask(__name__, static_folder='.')

# Enable CORS for API routes
# This allows your Cloudflare Pages site to make requests to the API
# Replace '*' with your specific CF Pages domain for better security
# Example: CORS(app, resources={r"/api/*": {"origins": "https://iamdcat.pages.dev"}})
CORS(app, resources={r"/api/*": {"origins": os.getenv('CORS_ORIGINS', '*')}})

# Ensure downloads folder exists
DOWNLOAD_FOLDER = os.path.join(os.getcwd(), 'Downloads')
if not os.path.exists(DOWNLOAD_FOLDER):
    os.makedirs(DOWNLOAD_FOLDER)

# Global jobs dictionary: { job_id: { status, meta, filename, error } }
jobs = {}

def sanitize_filename(filename):
    return re.sub(r'[\\/*?:"<>|]', "", filename)

def background_download(job_id, url, is_audio=False):
    def progress_hook(d):
        if d['status'] == 'downloading':
            # Extract useful stats
            p = d.get('_percent_str', '').replace('%','')
            
            # Fallback if percent str is missing
            if not p and d.get('total_bytes') and d.get('downloaded_bytes'):
                p = f"{(d['downloaded_bytes'] / d['total_bytes']) * 100:.1f}"
            elif not p:
                p = '0'

            speed = d.get('_speed_str', 'N/A')
            eta = d.get('_eta_str', 'N/A')
            
            # Simple fallback for total size string
            total = d.get('_total_bytes_str') or d.get('_total_bytes_estimate_str')
            if not total and d.get('total_bytes'):
                 total = f"{d['total_bytes']/1024/1024:.2f}MiB"
            else:
                 total = total or 'N/A'
            
            jobs[job_id]['meta'] = {
                'percent': p,
                'speed': speed,
                'eta': eta,
                'total': total,
                'raw': f"Downloading: {p}% of {total} at {speed} ETA {eta}"
            }
        elif d['status'] == 'finished':
            msg = "Processing audio..." if is_audio else "Processing media..."
            jobs[job_id]['meta']['raw'] = msg
            jobs[job_id]['status'] = 'processing'

    try:
        ydl_opts = {
            'outtmpl': os.path.join(DOWNLOAD_FOLDER, '%(title)s.%(ext)s'),
            'quiet': True,
            'no_warnings': True,
            'restrictfilenames': True,
            'progress_hooks': [progress_hook],
            'ffmpeg_location': os.getcwd()
        }
        
        # Check for cookies.txt
        cookie_file = os.path.join(os.getcwd(), 'cookies.txt')
        if os.path.exists(cookie_file):
            print(f"Using cookies from: {cookie_file}")
            ydl_opts['cookiefile'] = cookie_file
        else:
            browser = os.getenv('COOKIE_BROWSER', 'firefox')
            print(f"cookies.txt not found. Attempting to use {browser} cookies...")
            ydl_opts['cookiesfrombrowser'] = (browser,)
        
        if is_audio:
            # AUDIO CONFIGURATION
            ydl_opts.update({
                'format': 'bestaudio/best',
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }],
            })
        else:
            # VIDEO CONFIGURATION (High Quality MP4)
            ydl_opts.update({
                'format': 'bestvideo+bestaudio/best', 
                'merge_output_format': 'mp4'
            })
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
            
            # Verify file exists
            if not os.path.exists(filename):
                # It might have been post-processed (e.g., converted to mp3)
                base, ext = os.path.splitext(filename)
                
                possible_names = []
                if is_audio:
                    possible_names.append(base + '.mp3')
                else:
                    possible_names.append(base + '.mp4')
                
                found = False
                for p in possible_names:
                    if os.path.exists(p):
                        filename = p
                        found = True
                        break
                
                if not found:
                    raise Exception(f"File downloaded but not found. Expected: {filename}")
                
            jobs[job_id]['filename'] = filename
            jobs[job_id]['status'] = 'finished'
            
    except Exception as e:
        # Strip ANSI color codes
        error_msg = re.sub(r'\x1b\[[0-9;]*m', '', str(e))
        print(f"Primary attempted failed: {error_msg}")
        
        fallback_success = False
        
        # If DRM or generic error, try to get title for fallback search
        # We assume if the user wanted this URL, they might be satisfied with a YouTube version of the same title
        try:
            jobs[job_id]['meta']['raw'] = "Primary source failed. Analyzing metadata for fallback..."
            
            # Try to fetch metadata without downloading
            with yt_dlp.YoutubeDL({'quiet': True, 'ignoreerrors': True}) as ydl_meta:
                 meta = ydl_meta.extract_info(url, download=False)
            
            title = None
            if meta and 'title' in meta:
                title = meta['title']
            elif meta and 'track' in meta and 'artist' in meta: # Music sites
                title = f"{meta['artist']} - {meta['track']}"
            
            if title:
                print(f"Found title for fallback: {title}")
                jobs[job_id]['meta']['raw'] = f"Searching YouTube for: {title}..."
                
                # Initiate Fallback Download
                fallback_query = f"ytsearch1:{title}"
                
                with yt_dlp.YoutubeDL(ydl_opts) as ydl_fallback:
                    info_search = ydl_fallback.extract_info(fallback_query, download=True)
                    
                    if 'entries' in info_search:
                        info = info_search['entries'][0]
                    else:
                        info = info_search
                        
                    filename = ydl_fallback.prepare_filename(info)
                    
                    if os.path.exists(filename):
                        jobs[job_id]['filename'] = filename
                        jobs[job_id]['status'] = 'finished'
                        jobs[job_id]['meta']['raw'] = "Fallback content acquired."
                        fallback_success = True
        except Exception as fallback_e:
            print(f"Fallback failed: {fallback_e}")
            fallback_error_detail = str(fallback_e)

        if not fallback_success:
            if "DRM protection" in error_msg:
                error_msg = "This video is protected by DRM.\n"
                if 'fallback_error_detail' in locals():
                    error_msg += f"Auto-fallback failed: {fallback_error_detail}"
                else:
                    error_msg += "Auto-detect blocked by encryption. Please TYPE THE SONG NAME above to search manually."
                
            print(f"Job {job_id} finally failed.")
            jobs[job_id]['status'] = 'error'
            jobs[job_id]['error'] = error_msg

@app.route('/')
def home():
    return "IAmDrCat API Backend is Running!", 200

@app.route('/<path:path>')
def serve_static(path):
    return send_from_directory('.', path)

@app.route('/api/search', methods=['POST'])
def search_media():
    data = request.json
    query = data.get('query')
    if not query:
        return jsonify({'error': 'No query provided'}), 400

    print(f"Searching for: {query}")

    def get_meta(search_query):
        try:
            # OPTION 1: Try fast search (extract_flat=True)
            # This avoids visiting the video page, reducing bot detection
            opts = {
                'quiet': True, 
                'ignoreerrors': True,
                'extract_flat': True,  # FAST MODE
                'force_generic_extractor': False
            }
            
            with yt_dlp.YoutubeDL(opts) as ydl:
                print(f"Executing fast search: ytsearch1:{search_query}")
                info = ydl.extract_info(f"ytsearch1:{search_query}", download=False)
                
                if 'entries' in info and info['entries']:
                    entry = info['entries'][0]
                    # Ensure we have a valid URL
                    if not entry.get('url') and entry.get('id'):
                        entry['url'] = f"https://www.youtube.com/watch?v={entry['id']}"
                    
                    print(f"Found (Fast): {entry.get('title', 'Unknown')}")
                    return entry

            # OPTION 2: Fallback to slow search if fast failed (unlikely for ytsearch)
            # Only do this if we really got nothing
            print(f"Fast search yielded no results for: {search_query}")
            return None

        except Exception as e:
            print(f"Search error for '{search_query}': {e}")
            return None
        return None

    # Run searches in parallel threads to be fast
    # We search for "Query (Official Music Video)" and "Query (Lyrics)"
    # For Audio, we will reuse the Lyrics result in the frontend
    from concurrent.futures import ThreadPoolExecutor
    
    results = {}
    with ThreadPoolExecutor(max_workers=2) as executor:
        f_mv = executor.submit(get_meta, f"{query} Official Music Video")
        f_lyric = executor.submit(get_meta, f"{query} Lyrics")
        
        mv_meta = f_mv.result()
        lyric_meta = f_lyric.result()
        
        if mv_meta:
            results['mv'] = {
                'title': mv_meta.get('title'),
                'url': mv_meta.get('url') or mv_meta.get('webpage_url'),
                'thumb': mv_meta.get('thumbnails', [{}])[-1].get('url') if mv_meta.get('thumbnails') else None
            }
            
        if lyric_meta:
            results['lyrics'] = {
                'title': lyric_meta.get('title'),
                'url': lyric_meta.get('url') or lyric_meta.get('webpage_url'),
                'thumb': lyric_meta.get('thumbnails', [{}])[-1].get('url') if lyric_meta.get('thumbnails') else None
            }

    return jsonify(results)

@app.route('/api/start', methods=['POST'])
def start_download():
    data = request.json
    url = data.get('url')
    is_audio = data.get('is_audio', False)
    
    if not url:
        return jsonify({'error': 'No URL provided'}), 400

    # If direct search (not URL) and NOT coming from our new search UI (implied by lack of http),
    # legacy fallback is handled by client calling /api/search now.
    # But let's keep the safeguard:
    if not url.startswith(('http://', 'https://')) and not url.startswith('ytsearch'):
        # This shouldn't happen with new frontend logic, but just in case treat as direct download request?
        # Actually safer to convert to search if it slipps through
        url = f"ytsearch1:{url}"

    job_id = str(uuid.uuid4())
    jobs[job_id] = {
        'status': 'starting',
        'meta': {'raw': 'Initializing...'},
        'filename': None,
        'error': None,
        'is_audio': is_audio
    }
    
    thread = threading.Thread(target=background_download, args=(job_id, url, is_audio))
    thread.daemon = True
    thread.start()
    
    return jsonify({'job_id': job_id})

@app.route('/api/progress/<job_id>', methods=['GET'])
def get_progress(job_id):
    job = jobs.get(job_id)
    if not job:
        return jsonify({'error': 'Job not found'}), 404
    return jsonify(job)

@app.route('/api/serve/<job_id>', methods=['GET'])
def serve_file_route(job_id):
    job = jobs.get(job_id)
    if not job or not job.get('filename'):
        return jsonify({'error': 'File not ready'}), 404
    
    # Check if user wants to download as attachment or view inline
    as_attachment = request.args.get('download') == 'true'
    
    # Explicitly set MIME type
    mime_type = None
    lower_name = job['filename'].lower()
    if lower_name.endswith('.mp4'):
        mime_type = 'video/mp4'
    elif lower_name.endswith('.mp3'):
        mime_type = 'audio/mpeg'
        
    return send_file(job['filename'], as_attachment=as_attachment, mimetype=mime_type)

def cleanup_monitor():
    """Background thread to clean up old files and jobs"""
    while True:
        time.sleep(60)  # Check every minute
        try:
            now = time.time()
            retention_period = 600  # 10 minutes in seconds

            # 1. Clean up Physical Files
            if os.path.exists(DOWNLOAD_FOLDER):
                for filename in os.listdir(DOWNLOAD_FOLDER):
                    filepath = os.path.join(DOWNLOAD_FOLDER, filename)
                    # If file is older than retention period
                    if os.path.isfile(filepath):
                        creation_time = os.path.getmtime(filepath)
                        if now - creation_time > retention_period:
                            try:
                                os.remove(filepath)
                                print(f"[Cleanup] Deleted old file: {filename}")
                            except Exception as e:
                                print(f"[Cleanup] Failed to delete {filename}: {e}")

            # 2. Clean up Job History (Memory)
            # We don't have timestamps in jobs, but we can assume if the file is gone 
            # and status is 'finished', it's dead. Or just clear very old stale jobs.
            # For now, let's strictly clean up the files to save disk space.
            
        except Exception as e:
            print(f"[Cleanup] Error in monitor: {e}")

if __name__ == '__main__':
    # Start Cleanup Thread
    cleanup_thread = threading.Thread(target=cleanup_monitor, daemon=True)
    cleanup_thread.start()

    print("Starting IAmDrCat Server on http://localhost:" + os.getenv('FLASK_PORT', '8000'))
    print("Background Cleanup Crew matches active (10 min retention)")
    print("Press Ctrl+C to stop")
    # threaded=True is default in recent Flask versions, but good to be explicit for concurrency
    app.run(host='0.0.0.0', port=int(os.getenv('FLASK_PORT', 8000)), debug=os.getenv('FLASK_DEBUG', 'True') == 'True', threaded=True)
