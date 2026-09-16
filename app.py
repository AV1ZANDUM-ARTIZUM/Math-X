from flask import Flask, request, Response, render_template, jsonify
import ipaddress
import socket
from urllib.parse import urljoin, urlparse
import requests

app = Flask(__name__)

MAX_BYTES = 5 * 1024 * 1024
TIMEOUT = 10
ALLOWED_SCHEMES = {"http", "https"}


def is_public_host(hostname: str) -> bool:
    if not hostname:
        return False
    host = hostname.strip().lower().rstrip('.')
    if host in {"localhost", "localhost.localdomain"} or host.endswith('.local'):
        return False
    try:
        ip = ipaddress.ip_address(host)
        return ip.is_global
    except ValueError:
        pass
    try:
        addresses = socket.getaddrinfo(host, None, type=socket.SOCK_STREAM)
    except socket.gaierror:
        return False
    if not addresses:
        return False
    return all(ipaddress.ip_address(item[4][0]).is_global for item in addresses)


def validate_url(url: str) -> str:
    parsed = urlparse(url)
    if parsed.scheme not in ALLOWED_SCHEMES:
        raise ValueError("Only http:// and https:// URLs are allowed.")
    if parsed.username or parsed.password:
        raise ValueError("Userinfo in URLs is not allowed.")
    if not is_public_host(parsed.hostname):
        raise ValueError("That host is not a public internet address.")
    return url


def fetch_public_url(url: str):
    current = validate_url(url)
    session = requests.Session()
    headers = {
        "User-Agent": "Math-X-Proxy/1.0",
        "Accept": "text/html, text/plain, application/json, application/xml, image/*;q=0.8, */*;q=0.1",
    }
    for _ in range(4):
        response = session.get(current, headers=headers, timeout=TIMEOUT, stream=True, allow_redirects=False)
        if response.is_redirect or response.is_permanent_redirect:
            location = response.headers.get("Location")
            response.close()
            if not location:
                raise ValueError("The destination returned an invalid redirect.")
            current = validate_url(urljoin(current, location))
            continue
        return response
    raise ValueError("Too many redirects.")


@app.get("/")
def index():
    return render_template("index.html")


@app.get("/health")
def health():
    return jsonify(ok=True, service="Math-X Proxy")


@app.get("/proxy")
def proxy():
    target = request.args.get("url", "").strip()
    if not target:
        return jsonify(error="Missing url parameter."), 400
    try:
        response = fetch_public_url(target)
        content_type = response.headers.get("Content-Type", "application/octet-stream")
        content_length = response.headers.get("Content-Length")
        if content_length and int(content_length) > MAX_BYTES:
            response.close()
            return jsonify(error="Response is larger than the 5 MB limit."), 413

        data = response.raw.read(MAX_BYTES + 1)
        response.close()
        if len(data) > MAX_BYTES:
            return jsonify(error="Response is larger than the 5 MB limit."), 413

        blocked = {"set-cookie", "content-security-policy", "x-frame-options", "content-encoding", "content-length"}
        out_headers = {k: v for k, v in response.headers.items() if k.lower() not in blocked}
        out_headers["X-Proxy-By"] = "Math-X"
        out_headers["Cache-Control"] = "no-store"
        return Response(data, status=response.status_code, headers=out_headers, content_type=content_type)
    except requests.Timeout:
        return jsonify(error="The destination timed out."), 504
    except requests.RequestException as exc:
        return jsonify(error=f"Could not fetch destination: {exc}"), 502
    except (ValueError, socket.gaierror) as exc:
        return jsonify(error=str(exc)), 400


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
