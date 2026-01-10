# Cloudflare Pages Deployment Guide

## Files to Deploy

Deploy **ONLY** these static files to Cloudflare Pages:

### ✅ Include:
- `index.html`
- `downloader.html`
- `navbar.html`
- `news.html`
- `fortnite-shop.html`
- `ads.txt`
- `posts.json`
- `Fortnite` (file)
- `games/` (entire directory)
- `server/` (entire directory - appears to contain static files)

### ❌ Exclude (Backend files - stay local):
- `server.py`
- `downloader.py`
- `start_server.bat`
- `start_tunnel.bat`
- `cloudflared-config.yml`
- `ffmpeg.exe`
- `ffprobe.exe`
- `Downloads/` (directory)
- `.git/` (directory)

---

## Deployment Methods

### Method 1: Git Repository (Recommended)

1. **Create `.gitignore`** to exclude backend files:
   ```
   # Python backend
   server.py
   downloader.py
   *.bat
   cloudflared-config.yml
   
   # FFmpeg binaries
   ffmpeg.exe
   ffprobe.exe
   
   # Downloads folder
   Downloads/
   
   # Python cache
   __pycache__/
   *.pyc
   ```

2. **Push to GitHub**:
   ```bash
   git init
   git add .
   git commit -m "Initial commit - static files only"
   git branch -M main
   git remote add origin https://github.com/yourusername/iamdcat-site.git
   git push -u origin main
   ```

3. **Connect to Cloudflare Pages**:
   - Go to Cloudflare Dashboard → Pages
   - Click "Create a project"
   - Connect your GitHub repository
   - Build settings:
     - **Build command**: (leave empty)
     - **Build output directory**: `/`
     - **Root directory**: `/`
   - Click "Save and Deploy"

### Method 2: Direct Upload

1. Create a folder with only the static files listed above
2. Go to Cloudflare Dashboard → Pages
3. Click "Create a project" → "Upload assets"
4. Drag and drop the folder
5. Click "Deploy"

---

## Post-Deployment Configuration

### 1. Update API_BASE_URL in downloader.html

After your tunnel is set up, update line 597 in `downloader.html`:

```javascript
// Change from:
const API_BASE_URL = '';

// To:
const API_BASE_URL = 'https://api.yourdomain.com';
```

Then redeploy to Cloudflare Pages.

### 2. Update CORS in server.py (Optional - More Secure)

For better security, update line 16 in `server.py` to only allow your CF Pages domain:

```python
# Change from:
CORS(app, resources={r"/api/*": {"origins": "*"}})

# To (replace with your actual CF Pages URL):
CORS(app, resources={r"/api/*": {"origins": "https://iamdcat.pages.dev"}})
```

---

## Custom Domain Setup

### On Cloudflare Pages:
1. Go to your Pages project → Custom domains
2. Add your domain (e.g., `iamdcat.com`)
3. Follow DNS configuration instructions

### For the API Tunnel:
1. Add a CNAME record:
   - **Type**: CNAME
   - **Name**: `api`
   - **Target**: `<tunnel-id>.cfargotunnel.com`
   - **Proxy**: Enabled (orange cloud)

---

## Testing Checklist

- [ ] Static site loads on CF Pages URL
- [ ] Navigation works between pages
- [ ] Downloader page loads correctly
- [ ] API calls go to tunnel endpoint
- [ ] Video download functionality works
- [ ] Search functionality works
- [ ] Preview player works
- [ ] Save to disk works

---

## Troubleshooting

### "Failed to fetch" errors
- Check that `API_BASE_URL` is set correctly in `downloader.html`
- Verify tunnel is running: `cloudflared tunnel info video-downloader-api`
- Check CORS settings in `server.py`

### Tunnel not connecting
- Verify DNS record is set correctly
- Check `cloudflared-config.yml` has correct tunnel ID and domain
- Run: `cloudflared tunnel route dns video-downloader-api api.yourdomain.com`

### Video downloads fail
- Check Flask server is running on localhost:8000
- Verify ffmpeg.exe and ffprobe.exe are in the correct directory
- Check Downloads folder exists and is writable
