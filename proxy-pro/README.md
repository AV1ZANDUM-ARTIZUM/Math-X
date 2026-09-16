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
- 5 MB response limit by default
- Request timeout
- Maximum URL length
- GET-only proxy endpoint
- No arbitrary TCP tunneling or WebSockets
- No forwarding of arbitrary client headers
- `Cache-Control: no-store` on proxied responses
- Security headers on Math-X's own UI/API responses

### Run locally

```bash
cd proxy-pro
pip install -r requirements.txt
python app.py
```

Then open `http://127.0.0.1:5000`.

### Production server

A production WSGI entry point and `Procfile` are included:

```bash
gunicorn --chdir proxy-pro wsgi:app
```

Use a platform that provides HTTPS and a process manager. Before public deployment, review the limits below and consider authentication or an additional host allowlist. Do not operate it as an unrestricted public/open proxy.

### Environment limits

The defaults are intentionally bounded and can be changed by environment variables:

| Variable | Default | Purpose |
|---|---:|---|
| `MATH_X_MAX_BYTES` | `5242880` | Maximum fetched response size |
| `MATH_X_CONNECT_TIMEOUT` | `5` | Connection timeout in seconds |
| `MATH_X_READ_TIMEOUT` | `15` | Read timeout in seconds |
| `MATH_X_MAX_REDIRECTS` | `5` | Maximum redirect hops |
| `MATH_X_RATE_LIMIT` | `30` | Requests per client window |
| `MATH_X_RATE_WINDOW` | `60` | Rate-limit window in seconds |
| `MATH_X_MAX_URL_LENGTH` | `4096` | Maximum destination URL length |

### Diagnostics

- `/health` reports bounded server limits and version information.
- `/api/status` reports the proxy's public capabilities and restrictions without exposing secrets or destination URLs.

### Tests

The server has a standard-library `unittest` test suite covering URL safety, private-address blocking, credential/port restrictions, IPv6 formatting, HTML/CSS rewriting, and diagnostic endpoints.

```bash
cd proxy-pro
python -m unittest discover -s tests -v
```

### What “full” means here

This is a real server-side HTTP proxy, not an iframe-only browser trick. It can fetch HTML, CSS and other normal HTTP resources and rewrite common HTML/CSS URLs. It is **not** a universal browser replacement: sites that depend on WebSockets, browser-integrated APIs, complex authentication, service workers, anti-bot systems, or JavaScript assumptions about their original origin may not work correctly.

## 2. Browser-only edition

`static/index.html`, `static/style.css`, and `static/script.js` remain the GitHub Pages/browser-only edition. That edition does not have permission to bypass CORS or iframe restrictions and does not require Python.

Use responsibly and only access sites you are permitted to access.
