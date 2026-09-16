# Math-X Proxy Pro security notes

Math-X Proxy Pro is designed as a bounded HTTP/HTTPS fetching service, not as an unrestricted network tunnel.

## Current boundaries

- HTTP and HTTPS only.
- Standard ports only (80 and 443).
- Destination DNS results are checked and private, loopback, link-local, multicast, reserved, and unspecified destinations are rejected.
- Redirect destinations are validated again.
- Embedded URL credentials are rejected.
- GET requests only.
- No arbitrary TCP tunneling or WebSocket proxying.
- Responses are size-limited.
- Requests have connect/read timeouts and a redirect limit.
- A basic per-client rate limit is enabled by default.

## Public deployment

Before exposing Proxy Pro to the public internet, use HTTPS and put an additional authentication/rate-limiting layer in front of it when appropriate. Consider an explicit destination allowlist if the service is intended for a controlled group of sites.

Run the application on its own origin or host when possible. Do not assume that rewriting HTML makes every modern website compatible with iframe-based proxy viewing.

## Reporting

If you discover a security issue, do not publish sensitive exploit details in a public issue. Contact the repository maintainer privately through the repository's available contact channels.
