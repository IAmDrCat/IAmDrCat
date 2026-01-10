# Cloudflare Tunnel Setup Guide

This guide walks you through setting up a Cloudflare Tunnel to expose your video downloader API.

## Prerequisites

- ✅ Cloudflared installed (you have version 2025.11.1)
- ✅ A domain connected to Cloudflare
- ✅ Cloudflare account with access to the domain

---

## Step 1: Login to Cloudflare

Open a terminal and run:

```bash
cloudflared tunnel login
```

This will open a browser window. Select the domain you want to use and authorize cloudflared.

---

## Step 2: Create the Tunnel

```bash
cloudflared tunnel create video-downloader-api
```

**Important**: Copy the **Tunnel ID** from the output. It looks like:
```
Created tunnel video-downloader-api with id 12345678-abcd-1234-abcd-123456789abc
```

The tunnel ID is: `12345678-abcd-1234-abcd-123456789abc`

---

## Step 3: Update Configuration File

Open `cloudflared-config.yml` and replace the placeholders:

1. Replace `<TUNNEL_ID>` with your actual tunnel ID (from Step 2)
2. Replace `<YOUR_DOMAIN>` with your actual domain (e.g., `iamdcat.com`)

**Example:**
```yaml
tunnel: 12345678-abcd-1234-abcd-123456789abc
credentials-file: C:\Users\Catis\.cloudflared\12345678-abcd-1234-abcd-123456789abc.json

ingress:
  - hostname: api.iamdcat.com
    service: http://localhost:8000
  - service: http_status:404
```

---

## Step 4: Configure DNS

You have two options:

### Option A: Automatic DNS (Recommended)

Run this command (replace `yourdomain.com` with your actual domain):

```bash
cloudflared tunnel route dns video-downloader-api api.yourdomain.com
```

### Option B: Manual DNS

1. Go to Cloudflare Dashboard → Your Domain → DNS
2. Add a CNAME record:
   - **Type**: CNAME
   - **Name**: `api`
   - **Target**: `<tunnel-id>.cfargotunnel.com`
   - **Proxy status**: Proxied (orange cloud icon)
   - **TTL**: Auto

---

## Step 5: Test the Tunnel

Start the tunnel to test:

```bash
cloudflared tunnel --config cloudflared-config.yml run video-downloader-api
```

You should see output like:
```
2026-01-09T21:30:00Z INF Connection registered connIndex=0
2026-01-09T21:30:00Z INF Starting metrics server on 127.0.0.1:XXXX
```

Keep this running and test in another terminal:

```bash
# Start your Flask server first
python server.py

# Then test the tunnel endpoint
curl https://api.yourdomain.com/api/search -X POST -H "Content-Type: application/json" -d "{\"query\":\"test\"}"
```

If you get a JSON response, it's working! 🎉

---

## Step 6: Update downloader.html

After confirming the tunnel works, update `downloader.html`:

Find line ~597 and change:
```javascript
const API_BASE_URL = '';
```

To:
```javascript
const API_BASE_URL = 'https://api.yourdomain.com';
```

Replace `yourdomain.com` with your actual domain.

---

## Step 7: Run Both Services

Use the convenience script:

```bash
start_tunnel.bat
```

Or run manually in separate terminals:

**Terminal 1 - Flask Server:**
```bash
python server.py
```

**Terminal 2 - Cloudflare Tunnel:**
```bash
cloudflared tunnel --config cloudflared-config.yml run video-downloader-api
```

---

## Running as a Service (Optional)

To run the tunnel automatically on system startup:

```bash
cloudflared service install
```

Then start/stop with:
```bash
cloudflared service start
cloudflared service stop
```

---

## Troubleshooting

### "tunnel credentials file not found"
- Make sure the path in `cloudflared-config.yml` matches the actual location
- Check `C:\Users\Catis\.cloudflared\` for the JSON file

### "connection refused" or "502 Bad Gateway"
- Make sure Flask server is running on port 8000
- Check if another service is using port 8000: `netstat -ano | findstr :8000`

### DNS not resolving
- Wait a few minutes for DNS propagation
- Clear your DNS cache: `ipconfig /flushdns`
- Check DNS record in Cloudflare Dashboard

### CORS errors in browser
- Verify CORS is enabled in `server.py`
- Check browser console for specific error messages
- Make sure `API_BASE_URL` matches your tunnel domain exactly

---

## Security Notes

1. **CORS**: After testing, update `server.py` to only allow your CF Pages domain:
   ```python
   CORS(app, resources={r"/api/*": {"origins": "https://iamdcat.pages.dev"}})
   ```

2. **Rate Limiting**: Consider adding rate limiting to prevent abuse

3. **Authentication**: For production, consider adding API authentication

---

## Next Steps

1. ✅ Set up tunnel (this guide)
2. Deploy static files to Cloudflare Pages (see `CLOUDFLARE_PAGES_DEPLOY.md`)
3. Test the complete setup
4. Set up tunnel as a Windows service for auto-start

---

## Useful Commands

```bash
# List all tunnels
cloudflared tunnel list

# Get tunnel info
cloudflared tunnel info video-downloader-api

# Delete a tunnel (if needed)
cloudflared tunnel delete video-downloader-api

# View tunnel logs
cloudflared tunnel --config cloudflared-config.yml run video-downloader-api --loglevel debug
```
