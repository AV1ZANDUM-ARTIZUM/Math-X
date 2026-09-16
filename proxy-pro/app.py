import ipaddress
import os
import re
import socket
import time
from collections import defaultdict, deque
from urllib.parse import quote, unquote, urljoin, urlparse

import requests
from flask import Flask, Response, render_template, request

app = Flask(__name__)

# Keep the server deliberately bounded. These can be tuned by the host environment.
MAX_BYTES = int(os.getenv("MATH_X_MAX_BYTES", 5 * 1024 * 1024))
TIMEOUT = (int(os.getenv("MATH_X_CONNECT_TIMEOUT", 5)), int(os.getenv("MATH_X_READ_TIMEOUT", 15)))
MAX_REDIRECTS = int(os.getenv("MATH_X_MAX_REDIRECTS", 5))
RATE_LIMIT = int(os.getenv("MATH_X_RATE_LIMIT", 30))
RATE_WINDOW = int(os.getenv("MATH_X_RATE_WINDOW", 60))

BLOCKED_HOSTS = {"localhost", "localhost.localdomain", "0.0.0.0", "::1"}
ALLOWED_SCHEMES = {"http", "https"}
ALLOWED_PORTS = {80, 443}
RATE_BUCKETS = defaultdict(deque)


def client_key():
    # Do not trust arbitrary forwarded IP headers by default.
    return request.remote_addr or "unknown"


def rate_limited():
    now = time.monotonic()
    bucket = RATE_BUCKETS[client_key()]
    cutoff = now - RATE_WINDOW
    while bucket and bucket[0] <= cutoff:
        bucket.popleft()
    if len(bucket) >= RATE_LIMIT:
        return True
    bucket.append(now)
    # Prevent abandoned client keys from growing forever.
    if len(RATE_BUCKETS) > 5000:
        for key in list(RATE_BUCKETS)[:1000]:
            if not RATE_BUCKETS[key]:
                RATE_BUCKETS.pop(key, None)
    return False


def safe_target(raw):
    if not raw or not isinstance(raw, str):
        raise ValueError("A URL is required.")
    raw = raw.strip()
    p = urlparse(raw)
    scheme = p.scheme.lower()
    if scheme not in ALLOWED_SCHEMES or not p.hostname:
        raise ValueError("Only HTTP and HTTPS URLs are allowed.")
    if p.username or p.password:
        raise ValueError("URLs containing embedded credentials are blocked.")
    try:
        host = p.hostname.encode("idna").decode("ascii").lower().rstrip(".")
        port = p.port
    except (UnicodeError, ValueError):
        raise ValueError("Invalid destination host or port.")
    if host in BLOCKED_HOSTS:
        raise ValueError("Local destinations are blocked.")
    if port not in (None, *ALLOWED_PORTS):
        raise ValueError("Only standard HTTP/HTTPS ports are allowed.")

    service_port = port or (443 if scheme == "https" else 80)
    try:
        infos = socket.getaddrinfo(host, service_port, type=socket.SOCK_STREAM)
    except (socket.gaierror, ValueError):
        raise ValueError("Host could not be resolved.")
    if not infos:
        raise ValueError("Host could not be resolved.")

    for info in infos:
        try:
            ip = ipaddress.ip_address(info[4][0])
        except ValueError:
            raise ValueError("Destination resolved to an invalid address.")
        # is_global rejects loopback, private, link-local, multicast,
        # reserved, unspecified and other non-public address ranges.
        if not ip.is_global:
            raise ValueError("Private, local, link-local, multicast, or reserved destinations are blocked.")
    return p._replace(netloc=host if port is None else f"{host}:{port}").geturl()


def proxy_url(target):
    return "/proxy?url=" + quote(target, safe="")


def should_skip_url(value):
    value = value.strip()
    return not value or value.startswith(("#", "data:", "blob:", "javascript:", "mailto:", "tel:", "about:"))


def proxify_url(value, base_url):
    if should_skip_url(value):
        return None
    absolute = urljoin(base_url, value)
    try:
        return proxy_url(safe_target(absolute))
    except ValueError:
        return None


def rewrite_css(text, base_url):
    # CSS url(...) resources.
    def url_repl(match):
        raw = match.group(1).strip().strip("\"'")
        rewritten = proxify_url(raw, base_url)
        return 'url("' + rewritten + '")' if rewritten else match.group(0)

    text = re.sub(r"url\(\s*([^)]*?)\s*\)", url_repl, text, flags=re.I)

    # CSS @import "..." and @import url(...).
    def import_repl(match):
        raw = match.group(2).strip().strip("\"'")
        rewritten = proxify_url(raw, base_url)
        if not rewritten:
            return match.group(0)
        return match.group(1) + '"' + rewritten + '"'

    text = re.sub(r"(@import\s+)([\"'][^\"']+[\"'])", lambda m: import_repl(type("M", (), {"group": lambda self, n: m.group(1) if n == 1 else m.group(2)})()), text, flags=re.I)
    return text


def rewrite_srcset(value, base_url):
    parts = []
    for candidate in value.split(","):
        bits = candidate.strip().split()
        if not bits:
            continue
        rewritten = proxify_url(bits[0], base_url)
        if rewritten:
            bits[0] = rewritten
        parts.append(" ".join(bits))
    return ", ".join(parts)


def rewrite_html(text, base_url):
    attrs = ("href", "src", "action", "poster", "data-src", "data-poster")
    pattern = re.compile(
        r'(?P<attr>\b(?:' + "|".join(attrs) + r'))(?P<eq>\s*=\s*)(?P<q>["\'])(?P<value>.*?)(?P=q)',
        re.I | re.S,
    )

    def attr_repl(match):
        value = match.group("value").strip()
        rewritten = proxify_url(value, base_url)
        if not rewritten:
            return match.group(0)
        return match.group("attr") + match.group("eq") + match.group("q") + rewritten + match.group("q")

    text = pattern.sub(attr_repl, text)

    # Responsive image URLs.
    srcset_pattern = re.compile(r'(?P<attr>\bsrcset)(?P<eq>\s*=\s*)(?P<q>["\'])(?P<value>.*?)(?P=q)', re.I | re.S)
    text = srcset_pattern.sub(
        lambda m: m.group("attr") + m.group("eq") + m.group("q") + rewrite_srcset(m.group("value"), base_url) + m.group("q"),
        text,
    )

    text = re.sub(r"<base\b[^>]*>", "", text, flags=re.I)

    def style_repl(match):
        return "<style>" + rewrite_css(match.group(1), base_url) + "</style>"

    text = re.sub(r"<style\b[^>]*>(.*?)</style>", style_repl, text, flags=re.I | re.S)

    # HTML meta refresh: <meta http-equiv="refresh" content="0; url=/next">.
    def refresh_repl(match):
        content = match.group(1)
        url_match = re.search(r"(url\s*=\s*)([^;]+)", content, flags=re.I)
        if not url_match:
            return match.group(0)
        raw = url_match.group(2).strip().strip("\"'")
        rewritten = proxify_url(raw, base_url)
        if not rewritten:
            return match.group(0)
        new_content = content[:url_match.start(2)] + rewritten + content[url_match.end(2):]
        return match.group(0).replace(content, new_content, 1)

    text = re.sub(
        r'<meta\b[^>]*\bcontent\s*=\s*["\']([^"\']+)["\'][^>]*>',
        refresh_repl,
        text,
        flags=re.I,
    )
    return text


def fetch_remote(target):
    current = safe_target(target)
    session = requests.Session()
    headers = {
        "User-Agent": "Math-X-Proxy/3.0 (+safe-server-proxy)",
        "Accept": request.headers.get("Accept", "*/*")[:512],
        "Accept-Language": request.headers.get("Accept-Language", "en-US,en;q=0.8")[:256],
    }
    for _ in range(MAX_REDIRECTS + 1):
        r = session.get(current, headers=headers, timeout=TIMEOUT, allow_redirects=False, stream=True)
        if 300 <= r.status_code < 400 and r.headers.get("Location"):
            current = safe_target(urljoin(current, r.headers["Location"]))
            r.close()
            continue
        return current, r
    raise ValueError("Too many redirects.")


@app.get("/")
def home():
    return render_template("index.html")


@app.get("/health")
def health():
    return {
        "ok": True,
        "service": "math-x-proxy",
        "mode": "server",
        "version": "3.0",
        "limits": {
            "max_bytes": MAX_BYTES,
            "max_redirects": MAX_REDIRECTS,
            "rate_limit": RATE_LIMIT,
            "rate_window_seconds": RATE_WINDOW,
        },
    }


@app.get("/proxy")
def proxy():
    if rate_limited():
        response = Response("Rate limit exceeded. Please wait a moment and try again.", status=429)
        response.headers["Retry-After"] = str(RATE_WINDOW)
        return response

    try:
        target = safe_target(request.args.get("url", ""))
        final_url, r = fetch_remote(target)
        data = r.raw.read(MAX_BYTES + 1)
        if len(data) > MAX_BYTES:
            r.close()
            return Response("Response is too large.", status=413)

        content_type = r.headers.get("Content-Type", "application/octet-stream")
        if "text/html" in content_type.lower():
            charset = r.encoding or "utf-8"
            text = data.decode(charset, errors="replace")
            data = rewrite_html(text, final_url).encode("utf-8")
            content_type = "text/html; charset=utf-8"
        elif "text/css" in content_type.lower():
            charset = r.encoding or "utf-8"
            text = data.decode(charset, errors="replace")
            data = rewrite_css(text, final_url).encode("utf-8")
            content_type = "text/css; charset=utf-8"

        response = Response(data, status=r.status_code, content_type=content_type)
        for header in ("Content-Language", "ETag", "Last-Modified"):
            if r.headers.get(header):
                response.headers[header] = r.headers[header]
        response.headers["X-Math-X-Proxy"] = "server-safe"
        response.headers["Cache-Control"] = "no-store"
        return response
    except ValueError as e:
        return Response(str(e), status=400)
    except requests.Timeout:
        return Response("The destination timed out.", status=504)
    except requests.RequestException:
        return Response("Proxy request failed while contacting the destination.", status=502)


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)
