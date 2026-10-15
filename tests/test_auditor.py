"""
test_auditor.py - Unit tests for Site Health Verifier.
"""

import unittest
from site_health_verifier.auditor import (
    MetaTagParser,
    CRASH_PATTERNS,
    EndpointResult,
    AuditSummary,
)
from site_health_verifier.formatters import TerminalFormatter, MarkdownFormatter, JSONFormatter
from site_health_verifier.crawler import RouteDiscoverer


class TestSiteHealthVerifier(unittest.TestCase):

    def test_meta_tag_parser(self):
        html = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Test Page Title</title>
            <meta name="description" content="A comprehensive testing page description.">
            <meta name="robots" content="index, follow">
            <meta property="og:title" content="OpenGraph Title">
            <link rel="canonical" href="https://example.com/canonical">
        </head>
        <body>
            <h1>Hello World</h1>
        </body>
        </html>
        """
        parser = MetaTagParser()
        parser.feed(html)
        self.assertEqual(parser.title, "Test Page Title")
        self.assertEqual(parser.meta_tags.get("description"), "A comprehensive testing page description.")
        self.assertEqual(parser.meta_tags.get("robots"), "index, follow")
        self.assertEqual(parser.meta_tags.get("og:title"), "OpenGraph Title")
        self.assertEqual(parser.canonical, "https://example.com/canonical")

    def test_crash_patterns_detection(self):
        import re

        wp_crash = "<html><body>There has been a critical error on this website.</body></html>"
        matches = [name for pattern, name in CRASH_PATTERNS if re.search(pattern, wp_crash, re.IGNORECASE)]
        self.assertIn("WordPress Critical Error (WSOD)", matches)

        php_fatal = "Fatal error: Uncaught Error: Call to undefined function foo() in /var/www/index.php:12"
        matches = [name for pattern, name in CRASH_PATTERNS if re.search(pattern, php_fatal, re.IGNORECASE)]
        self.assertIn("PHP Fatal Error", matches)

        db_error = "<h1>Error establishing a database connection</h1>"
        matches = [name for pattern, name in CRASH_PATTERNS if re.search(pattern, db_error, re.IGNORECASE)]
        self.assertIn("Database Connection Failure", matches)

    def test_formatters_generation(self):
        res = EndpointResult(
            url="https://example.com/",
            label="Home Page",
            status_code=200,
            response_time_ms=120.5,
            is_healthy=True,
        )
        summary = AuditSummary(
            target_url="https://example.com",
            timestamp="2026-10-15T00:00:00Z",
            total_endpoints=1,
            passed=1,
            failed=0,
            results=[res],
            min_latency_ms=120.5,
            max_latency_ms=120.5,
            avg_latency_ms=120.5,
            p95_latency_ms=120.5,
        )

        term_output = TerminalFormatter.format(summary, use_color=False)
        self.assertIn("SITE HEALTH VERIFIER", term_output)
        self.assertIn("100% HEALTHY", term_output)

        md_output = MarkdownFormatter.format(summary)
        self.assertIn("# ✅ Site Health Verifier Report", md_output)
        self.assertIn("https://example.com", md_output)

        json_output = JSONFormatter.format(summary)
        self.assertIn('"target_url": "https://example.com"', json_output)

    def test_route_discoverer(self):
        routes = RouteDiscoverer.parse_custom_routes(["/home", "about", "/api/v1/health"])
        self.assertEqual(len(routes), 3)
        self.assertEqual(routes[0][0], "/home")
        self.assertEqual(routes[1][0], "/about")
        self.assertEqual(routes[2][0], "/api/v1/health")


if __name__ == "__main__":
    unittest.main()
