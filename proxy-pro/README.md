# Math-X Proxy Pro

Math-X Proxy Pro now has two editions:

## 1. Full server-side edition

`app.py` is a Flask HTTP proxy for normal GET browsing. The web UI sends destinations to `/proxy?url=...`, the server fetches them, and HTML/CSS references are rewritten so common links and assets continue through the proxy.

### Included safety controls
- HTTP and HTTPS only
- Standard ports 80/443 only
- Embedded username/password credentials blocked
- DNS resolution before requests
- Public/global IP requirement
- Local, private, loopback, link-local, multicast and reserved destinations blocked
- Redirect limit with destination validation on every hop
- 5 MB response limit
- Request timeout
- GET-only proxy endpoint
- No arbitrary TCP tunneling or WebSockets
- No forwarding of arbitrary client headers
- `Cache-Control: no-store` on proxied responses

### Run locally

```bash
cd proxy-pro
pip install -r requirements.txt
python app.py
```

Then open `http://127.0.0.1:5000`.

For public deployment, put the Flask app behind a proper HTTPS-capable production server and consider adding authentication/rate limiting before exposing it to the Internet. Do not operate it as an unrestricted public/open proxy.

### What “full” means here
This is a real server-side HTTP proxy, not an iframe-only browser trick. It can fetch HTML, CSS and other normal HTTP resources and rewrite common HTML/CSS URLs. It is **not** a universal browser replacement: sites that depend on WebSockets, browser-integrated APIs, complex authentication, service workers, anti-bot systems, or JavaScript assumptions about their original origin may not work correctly.

## 2. Browser-only edition

`static/index.html`, `static/style.css`, and `static/script.js` remain the GitHub Pages/browser-only edition. That edition does not have permission to bypass CORS or iframe restrictions and does not require Python.

Use responsibly and only access sites you are permitted to access.