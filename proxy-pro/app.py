from flask import Flask, request, Response, render_template, redirect
import ipaddress, socket, re
from urllib.parse import urlparse, urljoin, quote
import requests

app = Flask(__name__)
MAX_BYTES = 5 * 1024 * 1024
TIMEOUT = (5, 15)
MAX_REDIRECTS = 5
BLOCKED_HOSTS = {"localhost", "localhost.localdomain", "0.0.0.0", "::1"}
ALLOWED_SCHEMES = {"http", "https"}


def safe_target(raw):
    if not raw or not isinstance(raw, str):
        raise ValueError("A URL is required.")
    p = urlparse(raw.strip())
    if p.scheme.lower() not in ALLOWED_SCHEMES or not p.hostname:
        raise ValueError("Only HTTP and HTTPS URLs are allowed.")
    if p.username or p.password:
        raise ValueError("URLs containing embedded credentials are blocked.")
    host = p.hostname.lower().rstrip('.')
    if host in BLOCKED_HOSTS:
        raise ValueError("Local destinations are blocked.")
    port = p.port
    if port not in (None, 80, 443):
        raise ValueError("Only standard HTTP/HTTPS ports are allowed.")
    try:
        infos = socket.getaddrinfo(host, port or (443 if p.scheme.lower() == 'https' else 80), type=socket.SOCK_STREAM)
    except (socket.gaierror, ValueError):
        raise ValueError("Host could not be resolved.")
    if not infos:
        raise ValueError("Host could not be resolved.")
    for info in infos:
        ip = ipaddress.ip_address(info[4][0])
        if not ip.is_global:
            raise ValueError("Private, local, link-local, multicast, or reserved destinations are blocked.")
    return p.geturl()


def proxy_url(target):
    return '/proxy?url=' + quote(target, safe='')


def rewrite_css(text, base_url):
    def repl(m):
        raw = m.group(1).strip().strip('"\'')
        if not raw or raw.startswith(('data:', 'blob:', '#', 'javascript:')):
            return m.group(0)
        absolute = urljoin(base_url, raw)
        try:
            absolute = safe_target(absolute)
        except ValueError:
            return m.group(0)
        return 'url("' + proxy_url(absolute) + '")'
    return re.sub(r'url\(\s*([^)]*?)\s*\)', repl, text, flags=re.I)


def rewrite_html(text, base_url):
    attrs = ('href', 'src', 'action', 'poster', 'data-src')
    pattern = re.compile(r'(?P<attr>\b(?:' + '|'.join(attrs) + r'))(?P<eq>\s*=\s*)(?P<q>["\'])(?P<value>.*?)(?P=q)', re.I | re.S)

    def repl(m):
        value = m.group('value').strip()
        if not value or value.startswith(('#', 'data:', 'blob:', 'javascript:', 'mailto:', 'tel:')):
            return m.group(0)
        absolute = urljoin(base_url, value)
        try:
            absolute = safe_target(absolute)
        except ValueError:
            return m.group(0)
        return m.group('attr') + m.group('eq') + m.group('q') + proxy_url(absolute) + m.group('q')

    text = pattern.sub(repl, text)
    text = re.sub(r'<base\b[^>]*>', '', text, flags=re.I)
    # Rewrite common CSS imports inside HTML style blocks.
    def style_repl(m):
        return '<style>' + rewrite_css(m.group(1), base_url) + '</style>'
    text = re.sub(r'<style\b[^>]*>(.*?)</style>', style_repl, text, flags=re.I | re.S)
    return text


def fetch_remote(target):
    current = safe_target(target)
    session = requests.Session()
    headers = {
        'User-Agent': 'Math-X-Proxy/2.0 (+safe-server-proxy)',
        'Accept': request.headers.get('Accept', '*/*')[:512],
        'Accept-Language': request.headers.get('Accept-Language', 'en-US,en;q=0.8')[:256],
    }
    for _ in range(MAX_REDIRECTS + 1):
        r = session.get(current, headers=headers, timeout=TIMEOUT, allow_redirects=False, stream=True)
        if 300 <= r.status_code < 400 and r.headers.get('Location'):
            current = safe_target(urljoin(current, r.headers['Location']))
            r.close()
            continue
        return current, r
    raise ValueError("Too many redirects.")


@app.get('/')
def home():
    return render_template('index.html')


@app.get('/health')
def health():
    return {"ok": True, "service": "math-x-proxy", "mode": "server", "limits": {"max_bytes": MAX_BYTES, "max_redirects": MAX_REDIRECTS}}


@app.get('/proxy')
def proxy():
    try:
        target = safe_target(request.args.get('url', ''))
        final_url, r = fetch_remote(target)
        data = r.raw.read(MAX_BYTES + 1)
        if len(data) > MAX_BYTES:
            r.close()
            return Response("Response is too large.", status=413)
        content_type = r.headers.get('Content-Type', 'application/octet-stream')
        if 'text/html' in content_type.lower():
            charset = r.encoding or 'utf-8'
            text = data.decode(charset, errors='replace')
            data = rewrite_html(text, final_url).encode('utf-8')
            content_type = 'text/html; charset=utf-8'
        elif 'text/css' in content_type.lower():
            charset = r.encoding or 'utf-8'
            text = data.decode(charset, errors='replace')
            data = rewrite_css(text, final_url).encode('utf-8')
            content_type = 'text/css; charset=utf-8'
        response = Response(data, status=r.status_code, content_type=content_type)
        for header in ('Content-Language', 'ETag', 'Last-Modified'):
            if r.headers.get(header):
                response.headers[header] = r.headers[header]
        response.headers['X-Math-X-Proxy'] = 'server-safe'
        response.headers['Cache-Control'] = 'no-store'
        return response
    except ValueError as e:
        return Response(str(e), status=400)
    except requests.Timeout:
        return Response("The destination timed out.", status=504)
    except requests.RequestException as e:
        return Response(f"Proxy request failed: {e}", status=502)


if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000, debug=False)
