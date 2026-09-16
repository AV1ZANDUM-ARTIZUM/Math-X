from flask import Flask, request, Response, render_template
import ipaddress, socket
from urllib.parse import urlparse
import requests

app = Flask(__name__)
MAX_BYTES = 5 * 1024 * 1024
TIMEOUT = 12
BLOCKED_HOSTS = {"localhost", "localhost.localdomain"}


def safe_target(raw):
    if not raw or not raw.startswith(("http://", "https://")):
        raise ValueError("Only HTTP and HTTPS URLs are allowed.")
    p = urlparse(raw)
    if not p.hostname:
        raise ValueError("Invalid URL.")
    host = p.hostname.lower().rstrip('.')
    if host in BLOCKED_HOSTS:
        raise ValueError("Local destinations are blocked.")
    try:
        infos = socket.getaddrinfo(host, None)
        for info in infos:
            ip = ipaddress.ip_address(info[4][0])
            if not ip.is_global:
                raise ValueError("Private or local destinations are blocked.")
    except socket.gaierror:
        raise ValueError("Host could not be resolved.")
    return raw


@app.get('/')
def home():
    return render_template('index.html')


@app.get('/health')
def health():
    return {"ok": True, "service": "math-x-proxy"}


@app.get('/proxy')
def proxy():
    try:
        target = safe_target(request.args.get('url', ''))
        r = requests.get(
            target,
            timeout=TIMEOUT,
            allow_redirects=False,
            stream=True,
            headers={"User-Agent": "Math-X-Proxy/1.0"},
        )
        if 300 <= r.status_code < 400 and r.headers.get('Location'):
            return Response("Redirects must be opened explicitly.", status=400)
        data = r.raw.read(MAX_BYTES + 1)
        if len(data) > MAX_BYTES:
            return Response("Response is too large.", status=413)
        content_type = r.headers.get('Content-Type', 'application/octet-stream')
        return Response(data, status=r.status_code, content_type=content_type)
    except ValueError as e:
        return Response(str(e), status=400)
    except requests.RequestException as e:
        return Response(f"Proxy request failed: {e}", status=502)


if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000, debug=False)
