# Math-X Proxy

A small, full-stack educational web proxy built with Flask.

## Features

- Responsive web interface
- URL input and quick examples
- HTTP/HTTPS fetching
- Redirect validation
- Basic SSRF protection against localhost, private/reserved IPs, local domains, and URL credentials
- 5 MB response limit
- Simple health endpoint at `/health`
- No frontend API keys

## Run locally

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

On Windows:

```powershell
.venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

Then open `http://127.0.0.1:5000`.

## Important deployment note

GitHub Pages can host the static interface, but it cannot execute this Flask server. To run the complete proxy, deploy `app.py` to a Python-capable service and keep the proxy restricted and rate-limited.

This project is intended for learning and controlled testing. Do not use it to bypass access controls or network restrictions.
