from flask import Flask, send_from_directory, request, send_file, jsonify, Response, redirect
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
import subprocess
import urllib.request
import urllib.parse
import json
import ssl

# iTunes Search API (No key required)
ITUNES_API_URL = "https://itunes.apple.com/search"

def get_itunes_artwork(query):
    """
    Searches iTunes for a song and returns the high-res artwork URL.
    """
    try:
        # Clean query: Remove (Official Video), [Lyrics], etc.
        # 1. Remove content in brackets/parentheses
        clean_query = re.sub(r'[\(\[\{].*?[\)\]\}]', '', query)
        # 2. Remove common junk words (case insensitive)
        clean_query = re.sub(r'(?i)(official|video|lyrics|audio|hq|hd|4k|mv|music)', '', clean_query)
        # 3. Collapse spaces
        clean_query = " ".join(clean_query.split())
        
        print(f"[Artwork] Searching iTunes for: {clean_query}")
        
        params = {
            'term': clean_query,
            'media': 'music',
            'entity': 'song',
            'limit': 1
        }
        
        url = f"{ITUNES_API_URL}?{urllib.parse.urlencode(params)}"
        
        # Create context to ignore SSL verification if needed (simpler for some envs)
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        
        with urllib.request.urlopen(url, context=ctx, timeout=5) as response:
            data = json.load(response)
            
        if data['resultCount'] > 0:
            track = data['results'][0]
            # Get artwork URL
            artwork_url = track.get('artworkUrl100')
            if artwork_url:
                # Upgrade resolution: 100x100 -> 600x600 or 1000x1000
                hq_art = artwork_url.replace('100x100', '600x600')
                title = track.get('trackName')
                artist = track.get('artistName')
                print(f"[Artwork] Found: {title} by {artist}")
                return hq_art, title, artist
                
    except Exception as e:
        print(f"[Artwork] Search failed: {e}")
    
    return None, None, None

app = Flask(__name__, static_folder='.')

# Enable CORS for API routes and Downloads
CORS(app, resources={
    r"/api/*": {"origins": os.getenv('CORS_ORIGINS', '*')},
    r"/Downloads/*": {"origins": os.getenv('CORS_ORIGINS', '*')}
})

# Ensure downloads folder exists
DOWNLOAD_FOLDER = os.path.join(os.getcwd(), 'Downloads')
if not os.path.exists(DOWNLOAD_FOLDER):
    os.makedirs(DOWNLOAD_FOLDER)

# Global jobs dictionary: { job_id: { status, meta, filename, error, ip } }
jobs = {}

# Track files per IP for cleanup
ip_files = {}  # {ip: [filepath1, filepath2, ...]}
ip_files_lock = threading.Lock()

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
            'ffmpeg_location': os.getcwd(),
            # SPOOF USER AGENT (Standard Windows Chrome)
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        }
        
        # 1. Try cookies.txt (Best for stability)
        cookie_file = os.path.join(os.getcwd(), 'cookies.txt')
        if os.path.exists(cookie_file):
            print(f"Using cookies from: {cookie_file}")
            ydl_opts['cookiefile'] = cookie_file
        else:
            # 2. Fallback to Native Browser (Might fail if browser is open)
            try:
                 ydl_opts['cookiesfrombrowser'] = ('chrome', )
                 print("Attempting to use Chrome cookies...")
            except:
                 ydl_opts['cookiesfrombrowser'] = ('firefox', )
                 print("Attempting to use Firefox cookies...")
        
        if is_audio:
            # AUDIO CONFIGURATION
            ydl_opts.update({
                'format': 'bestaudio/best',
                'writethumbnail': True,  # Download cover art
                'postprocessors': [
                    {'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3', 'preferredquality': '192'},
                    {'key': 'EmbedThumbnail'}, # Embed in MP3
                ],
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
            
            # Find the actual downloaded media file
            base, ext = os.path.splitext(filename)
            final_filename = filename
            
            # Check for converted files
            expected_exts = ['.mp3'] if is_audio else ['.mp4', '.mkv', '.webm']
            for ext in expected_exts:
                if os.path.exists(base + ext):
                    final_filename = base + ext
                    break
            
            if not os.path.exists(final_filename):
                 # Fallback check original
                 if not os.path.exists(filename):
                     raise Exception(f"File downloaded but not found: {final_filename}")
                 final_filename = filename

            jobs[job_id]['filename'] = final_filename
            # MOVED: jobs[job_id]['status'] = 'finished' (Set at end of metadata block)
            
            # --- Handle Thumbnail (User Request: "Real" cover art & delete with song) ---
            # yt-dlp writes thumbnail as base.jpg or base.webp
            thumb_local_path = None
            for ext in ['.jpg', '.jpeg', '.webp', '.png']:
                t_path = base + ext
                if os.path.exists(t_path):
                    thumb_local_path = t_path
                    break
            
            # iTunes Artwork Lookup (High Quality)
            if is_audio:
                # 1. Try to build query from explicit metadata (most accurate)
                artist = info.get('artist')
                track = info.get('track')
                
                if artist and track:
                    search_query = f"{artist} - {track}"
                    print(f"[Metadata] Using explicit metadata: {search_query}")
                else:
                    # 2. Fallback to cleaned video title
                    search_query = info.get('title', '')
                    print(f"[Metadata] Using video title: {search_query}")

                hq_art_url, clean_title, clean_artist = get_itunes_artwork(search_query)
                
                if hq_art_url:
                    try:
                        # Overwrite existing or create new
                        if thumb_local_path:
                            target_thumb_path = thumb_local_path
                        else:
                            # Use jpg extension for cover art
                            target_thumb_path = os.path.splitext(final_filename)[0] + ".jpg"
                        
                        print(f"[Artwork] Downloading HQ cover to {target_thumb_path}")
                        
                        req = urllib.request.Request(hq_art_url, headers={'User-Agent': 'Mozilla/5.0'})
                        with urllib.request.urlopen(req) as r, open(target_thumb_path, 'wb') as f:
                            f.write(r.read())
                        
                        thumb_local_path = target_thumb_path
                        
                        # UPDATE METADATA WITH OFFICIAL INFO
                        # This fixes "Unknown Track" if YouTube title was messy
                        if clean_title and clean_artist:
                            print(f"[Metadata] Updating title to official: {clean_title} - {clean_artist}")
                            info['title'] = f"{clean_title} - {clean_artist}"
                        
                    except Exception as art_err:
                        print(f"[Artwork] Failed to download HQ cover: {art_err}")
            
            # Store metadata
            jobs[job_id]['meta']['title'] = info.get('title', 'Unknown Title')
            
            if thumb_local_path:
                # Use local path for speed & ensured deletion
                # Convert absolute path to relative /Downloads/ route
                thumb_basename = os.path.basename(thumb_local_path)
                jobs[job_id]['meta']['thumb'] = f"/Downloads/{thumb_basename}"
            else:
                # Fallback to remote URL
                print(f"[Metadata] No local thumbnail. Using remote.")
                jobs[job_id]['meta']['thumb'] = info.get('thumbnails', [{}])[-1].get('url') if info.get('thumbnails') else None


            # Track file for this IP and cleanup old files
            client_ip = jobs[job_id].get('ip')
            if client_ip:
                with ip_files_lock:
                    if client_ip not in ip_files:
                        ip_files[client_ip] = []
                    
                    ip_files[client_ip].append(final_filename)
                    if thumb_local_path:
                        ip_files[client_ip].append(thumb_local_path)

                    # Per-IP Limit Cleanup
                    if len(ip_files[client_ip]) > MAX_FILES_PER_IP:
                        # Delete oldest (from start of list)
                        files_to_delete = ip_files[client_ip][:-MAX_FILES_PER_IP]
                        ip_files[client_ip] = ip_files[client_ip][-MAX_FILES_PER_IP:]
                        
                        for old_file in files_to_delete:
                            try:
                                if os.path.exists(old_file):
                                    os.remove(old_file)
                                    print(f"[Cleanup] Deleted old file for IP {client_ip}: {os.path.basename(old_file)}")
                            except Exception as del_err:
                                print(f"Error deleting old file: {del_err}")
            
            # DONE: Mark as finished AFTER all metadata/artwork logic
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

@app.route('/Downloads/<path:filename>')
def serve_download(filename):
    """Serve downloaded files with HTTP 206 partial content support"""
    file_path = os.path.join(DOWNLOAD_FOLDER, filename)
    
    if not os.path.exists(file_path):
        return jsonify({'error': 'File not found'}), 404
    
    range_header = request.headers.get('Range', None)
    
    if not range_header:
        # No range requested, send full file
        # Check for forced download
        as_attachment = request.args.get('download') == 'true'
        return send_file(file_path, as_attachment=as_attachment)
    
    size = os.path.getsize(file_path)
    byte1, byte2 = 0, None
    
    m = re.search(r'(\d+)-(\d*)', range_header)
    g = m.groups()
    
    if g[0]:
        byte1 = int(g[0])
    if g[1]:
        byte2 = int(g[1])
    
    length = size - byte1
    if byte2 is not None:
        length = byte2 - byte1 + 1
    
    data = None
    with open(file_path, 'rb') as f:
        f.seek(byte1)
        data = f.read(length)
    
    rv = Response(data,
                  206,
                  mimetype='application/octet-stream',
                  direct_passthrough=True)
    rv.headers.add('Content-Range', f'bytes {byte1}-{byte1 + length - 1}/{size}')
    rv.headers.add('Accept-Ranges', 'bytes')
    rv.headers.add('Content-Length', str(length))
    
    # Check for forced download query param
    if request.args.get('download') == 'true':
        rv.headers.add('Content-Disposition', f'attachment; filename="{filename}"')
        
    return rv

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
            opts = {
                'quiet': True, 
                'ignoreerrors': True,
                'extract_flat': True,
                'force_generic_extractor': False
            }
            
            with yt_dlp.YoutubeDL(opts) as ydl:
                print(f"Executing search: ytsearch1:{search_query}")
                info = ydl.extract_info(f"ytsearch1:{search_query}", download=False)
                
                if 'entries' in info and info['entries']:
                    entry = info['entries'][0]
                    if not entry.get('url') and entry.get('id'):
                        entry['url'] = f"https://www.youtube.com/watch?v={entry['id']}"
                    
                    print(f"Found: {entry.get('title', 'Unknown')}")
                    return entry

            print(f"No results for: {search_query}")
            return None

        except Exception as e:
            print(f"Search error for '{search_query}': {e}")
            return None

    # Search for multiple variations and let the results determine what to show
    from concurrent.futures import ThreadPoolExecutor
    
    results = {}
    with ThreadPoolExecutor(max_workers=3) as executor:
        # Search for: Music Video, Lyrics, and plain query
        f_mv = executor.submit(get_meta, f"{query} Official Music Video")
        f_lyric = executor.submit(get_meta, f"{query} Lyrics")
        f_plain = executor.submit(get_meta, query)
        
        mv_meta = f_mv.result()
        lyric_meta = f_lyric.result()
        plain_meta = f_plain.result()
        
        # Validate lyric video - must actually contain "lyric" in title
        if lyric_meta:
            title_lower = lyric_meta.get('title', '').lower()
            if 'lyric' not in title_lower and 'lyrics' not in title_lower:
                print(f"Rejecting fake lyric video: {lyric_meta.get('title')}")
                lyric_meta = None
        
        # Add music video if found
        if mv_meta:
            results['mv'] = {
                'title': mv_meta.get('title'),
                'url': mv_meta.get('url') or mv_meta.get('webpage_url'),
                'thumb': mv_meta.get('thumbnails', [{}])[-1].get('url') if mv_meta.get('thumbnails') else None
            }
            
        # Add lyrics if found and validated
        if lyric_meta:
            results['lyrics'] = {
                'title': lyric_meta.get('title'),
                'url': lyric_meta.get('url') or lyric_meta.get('webpage_url'),
                'thumb': lyric_meta.get('thumbnails', [{}])[-1].get('url') if lyric_meta.get('thumbnails') else None
            }
        
        # If no lyric video found but we have music video, use MV for audio source
        if not lyric_meta and mv_meta:
            results['audio_source'] = {
                'title': mv_meta.get('title'),
                'url': mv_meta.get('url') or mv_meta.get('webpage_url'),
                'thumb': mv_meta.get('thumbnails', [{}])[-1].get('url') if mv_meta.get('thumbnails') else None
            }
        
        # Add plain video if found AND if no music results (to avoid duplicates)
        if plain_meta and not mv_meta and not lyric_meta:
            results['video'] = {
                'title': plain_meta.get('title'),
                'url': plain_meta.get('url') or plain_meta.get('webpage_url'),
                'thumb': plain_meta.get('thumbnails', [{}])[-1].get('url') if plain_meta.get('thumbnails') else None
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

    # 1. IP Rate Limiting
    # Get real client IP from Cloudflare headers (tunnel masks real IP as 127.0.0.1)
    client_ip = request.headers.get('CF-Connecting-IP') or request.headers.get('X-Forwarded-For', request.remote_addr).split(',')[0].strip()
    now = time.time()
    last_req = ip_last_request.get(client_ip, 0)
    if now - last_req < IP_RATE_LIMIT_SECONDS:
        return jsonify({'error': f'Rate limit exceeded. Please wait {IP_RATE_LIMIT_SECONDS} seconds.'}), 429
    ip_last_request[client_ip] = now

    # 2. Concurrency Limiting
    active_jobs = sum(1 for j in jobs.values() if j['status'] in ['starting', 'downloading', 'processing'])
    if active_jobs >= MAX_CONCURRENT_JOBS:
        return jsonify({'error': 'Server is busy (Max 2 concurrent downloads). Please try again later.'}), 503

    job_id = str(uuid.uuid4())
    jobs[job_id] = {
        'status': 'starting',
        'meta': {'raw': 'Initializing...'},
        'filename': None,
        'error': None,
        'is_audio': is_audio,
        'ip': client_ip
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

@app.route('/api/convert', methods=['POST'])
def convert_file():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    target_format = request.form.get('format')
    if not target_format:
        return jsonify({'error': 'No target format specified'}), 400

    # Sanitize input
    target_format = target_format.lower().replace('.', '')
    allowed_formats = ['mp4', 'mkv', 'avi', 'mov', 'webm', 'mp3', 'gif', 'wav', 'flac', 'aac', 'm4a', 'ogg', 'jpg', 'png', 'webp', 'bmp', 'tiff']
    
    if target_format not in allowed_formats:
        return jsonify({'error': 'Unsupported format'}), 400

    # Save Upload
    temp_id = str(uuid.uuid4())
    input_ext = os.path.splitext(file.filename)[1]
    input_path = os.path.join(DOWNLOAD_FOLDER, f"temp_{temp_id}{input_ext}")
    output_filename = f"{os.path.splitext(file.filename)[0]}.{target_format}"
    output_path = os.path.join(DOWNLOAD_FOLDER, f"converted_{temp_id}.{target_format}")

    file.save(input_path)

    try:
        # Build FFmpeg Command
        # This is a basic universal converter logic
        cmd = ['ffmpeg', '-y', '-i', input_path]

        # Specific Logic
        if target_format == 'mp3':
            cmd.extend(['-vn', '-acodec', 'libmp3lame', '-q:a', '2'])
        elif target_format == 'gif':
            # Basic optimization for GIF
            cmd.extend(['-vf', 'fps=10,scale=320:-1:flags=lanczos', '-c:v', 'gif'])
        elif target_format in ['jpg', 'png', 'webp']:
             # If video to image, take 1 frame?
             # For now assume image to image or video to image (first frame)
             # FFmpeg handles this automatically, but might need -vframes 1 if it's a video input to image output
             # Let's just let FFmpeg decide default behavior for now (often extracts one frame or sequence)
             # But for single file output from video, we usually want 1 thumbnail.
             # However, if input is image, it works fine.
             pass
        
        cmd.append(output_path)

        # Run Conversion
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)

        if not os.path.exists(output_path):
             raise Exception("Conversion produced no output")

        # Return file and cleanup input
        # Note: We can't easily cleanup output after sending with flask send_file unless we use a cleanup callback or periodic task
        # Current periodic task will clean it up later if we add it to ip_files or just leave it for the global cleanup
        # Let's add it to ip_files if we have an IP, so it gets cleaned up
        client_ip = request.headers.get('CF-Connecting-IP') or request.headers.get('X-Forwarded-For', request.remote_addr).split(',')[0].strip()
        
        with ip_files_lock:
             if client_ip not in ip_files: ip_files[client_ip] = []
             ip_files[client_ip].append(input_path) # Clean input
             ip_files[client_ip].append(output_path) # Clean output later

        return send_file(output_path, as_attachment=True, download_name=output_filename)

    except subprocess.CalledProcessError as e:
        return jsonify({'error': f"FFmpeg failed: {e.stderr.decode()}"}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/serve/<job_id>', methods=['GET'])
def serve_file_route(job_id):
    job = jobs.get(job_id)
    if not job or not job.get('filename'):
        return jsonify({'error': 'File not ready'}), 404
    
    # Redirect to the Partial Content handler for better streaming support (seeking, etc.)
    filename = os.path.basename(job['filename'])
    safe_filename = urllib.parse.quote(filename)
    
    # Construct the partial content URL
    # We assume /Downloads/ is served by the serve_download function
    # Propagate the 'download' query param if present
    base_url = f"/Downloads/{safe_filename}"
    if request.args.get('download') == 'true':
        base_url += "?download=true"
        
    return redirect(base_url)

# Anti-Abuse Configuration
MAX_CONCURRENT_JOBS = 2
IP_RATE_LIMIT_SECONDS = 3  # Reduced from 10 to 3 seconds
MAX_FILES_PER_IP = 3  # Keep only the 3 most recent files per IP
ip_last_request = {} # {ip: timestamp}

def cleanup_monitor():
    """Background thread to clean up old files and jobs"""
    while True:
        time.sleep(60)  # Check every minute
        try:
            now = time.time()
            
            # 1. Clean up Physical Files
            if os.path.exists(DOWNLOAD_FOLDER):
                for filename in os.listdir(DOWNLOAD_FOLDER):
                    filepath = os.path.join(DOWNLOAD_FOLDER, filename)
                    if os.path.isfile(filepath):
                        # Dynamic Retention Policy
                        # Small Files (<500MB): 10 Minutes
                        # Large Files (>500MB): 2 Minutes (Save disk space)
                        file_size_mb = os.path.getsize(filepath) / (1024 * 1024)
                        if file_size_mb > 500:
                            retention_period = 120 # 2 minutes
                        else:
                            retention_period = 600 # 10 minutes

                        creation_time = os.path.getmtime(filepath)
                        if now - creation_time > retention_period:
                            try:
                                os.remove(filepath)
                                print(f"[Cleanup] Deleted old file ({file_size_mb:.1f}MB): {filename}")
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
