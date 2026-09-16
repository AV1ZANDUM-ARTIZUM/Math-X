import ipaddress
import unittest
from unittest.mock import patch

from app import app, rewrite_css, rewrite_html, safe_target


class ProxySafetyTests(unittest.TestCase):
    def fake_dns(self, host, port, type=None):
        return [(None, None, None, None, ("93.184.216.34", port))]

    def test_public_http_target_is_normalized(self):
        with patch("app.socket.getaddrinfo", self.fake_dns):
            self.assertEqual(safe_target("http://example.com/path"), "http://example.com/path")

    def test_private_destination_is_blocked(self):
        def private_dns(host, port, type=None):
            return [(None, None, None, None, ("192.168.1.10", port))]

        with patch("app.socket.getaddrinfo", private_dns):
            with self.assertRaisesRegex(ValueError, "Private"):
                safe_target("http://example.com")

    def test_credentials_are_blocked(self):
        with self.assertRaisesRegex(ValueError, "credentials"):
            safe_target("https://user:pass@example.com/")

    def test_non_standard_port_is_blocked(self):
        with self.assertRaisesRegex(ValueError, "standard HTTP/HTTPS ports"):
            safe_target("https://example.com:8443/")

    def test_url_length_is_bounded(self):
        with self.assertRaisesRegex(ValueError, "too long"):
            safe_target("https://example.com/" + ("x" * 5000))

    def test_ipv6_netloc_uses_brackets(self):
        def ipv6_dns(host, port, type=None):
            return [(None, None, None, None, ("2001:4860:4860::8888", port, 0, 0))]

        with patch("app.socket.getaddrinfo", ipv6_dns):
            self.assertEqual(
                safe_target("https://[2001:4860:4860::8888]:443/"),
                "https://[2001:4860:4860::8888]:443/",
            )


class RewriteTests(unittest.TestCase):
    def setUp(self):
        self.dns = patch("app.socket.getaddrinfo", self.fake_dns)
        self.dns.start()
        self.addCleanup(self.dns.stop)

    def fake_dns(self, host, port, type=None):
        return [(None, None, None, None, ("93.184.216.34", port))]

    def test_html_links_are_proxied(self):
        output = rewrite_html('<a href="/next">Next</a>', "https://example.com/start")
        self.assertIn('/proxy?url=https%3A%2F%2Fexample.com%2Fnext', output)

    def test_css_urls_are_proxied(self):
        output = rewrite_css('body { background: url("/img/bg.png"); }', "https://example.com/css/app.css")
        self.assertIn('/proxy?url=https%3A%2F%2Fexample.com%2Fimg%2Fbg.png', output)


class EndpointTests(unittest.TestCase):
    def test_status_endpoint(self):
        client = app.test_client()
        response = client.get("/api/status")
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["service"], "math-x-proxy")

    def test_health_endpoint(self):
        client = app.test_client()
        response = client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertIn("max_url_length", response.get_json()["limits"])


if __name__ == "__main__":
    unittest.main()
