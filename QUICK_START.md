# Quick Start - Cloudflare Tunnel Setup

## 🚀 Quick Commands

### First Time Setup
```bash
# 1. Login
cloudflared tunnel login

# 2. Create tunnel
cloudflared tunnel create video-downloader-api

# 3. Copy tunnel ID, then edit cloudflared-config.yml
# Replace <TUNNEL_ID> and <YOUR_DOMAIN>

# 4. Configure DNS
cloudflared tunnel route dns video-downloader-api api.yourdomain.com
```

### Daily Use
```bash
# Start everything (use the batch file)
start_tunnel.bat

# OR manually:
# Terminal 1:
python server.py

# Terminal 2:
cloudflared tunnel --config cloudflared-config.yml run video-downloader-api
```

---

## 📝 Configuration Checklist

- [ ] Update `cloudflared-config.yml`:
  - Replace `<TUNNEL_ID>` with your tunnel ID
  - Replace `<YOUR_DOMAIN>` with your domain
  
- [ ] Update `downloader.html` (line ~597):
  ```javascript
  const API_BASE_URL = 'https://api.yourdomain.com';
  ```

- [ ] Optional - Update `server.py` (line 16) for security:
  ```python
  CORS(app, resources={r"/api/*": {"origins": "https://iamdcat.pages.dev"}})
  ```

---

## 🌐 Deployment to CF Pages

### Quick Git Deploy
```bash
git init
git add .
git commit -m "Deploy to CF Pages"
git remote add origin https://github.com/yourusername/repo.git
git push -u origin main
```

Then connect the repo in Cloudflare Pages dashboard.

### Files to Deploy
✅ Include: All HTML, CSS, JS, static assets  
❌ Exclude: `server.py`, `*.bat`, `ffmpeg.exe`, `Downloads/`

(See `.gitignore` for complete list)

---

## 🔍 Testing

### Test Tunnel
```bash
curl https://api.yourdomain.com/api/search -X POST -H "Content-Type: application/json" -d "{\"query\":\"test\"}"
```

### Test Full Flow
1. Visit your CF Pages URL
2. Try downloading a video
3. Try searching for a song
4. Verify preview works

---

## 📚 Documentation Files

- `TUNNEL_SETUP_GUIDE.md` - Detailed tunnel setup
- `CLOUDFLARE_PAGES_DEPLOY.md` - CF Pages deployment guide
- `walkthrough.md` - Complete walkthrough of changes

---

## 🆘 Quick Troubleshooting

**Tunnel won't start:**
```bash
# Check tunnel exists
cloudflared tunnel list

# Check config file
cloudflared tunnel --config cloudflared-config.yml info video-downloader-api
```

**API calls fail:**
- Check Flask server is running on port 8000
- Verify `API_BASE_URL` in downloader.html
- Check browser console for errors

**DNS not working:**
```bash
# Flush DNS cache
ipconfig /flushdns

# Check DNS record in Cloudflare Dashboard
```

---

## 🎯 Your Domain Placeholders

Throughout the config files, replace:
- `<TUNNEL_ID>` → Your actual tunnel ID from step 2
- `<YOUR_DOMAIN>` → Your domain (e.g., `iamdcat.com`)
- `api.yourdomain.com` → Your API subdomain (e.g., `api.iamdcat.com`)
