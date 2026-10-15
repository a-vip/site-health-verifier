"""
auditor.py - Core diagnostic engine for Site Health Verifier.
Performs concurrent HTTP health checks, silent framework crash detection,
SSL certificate inspection, and latency profiling using standard library.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
import concurrent.futures
import html.parser
import json
import re
import socket
import ssl
import time
from typing import Dict, List, Optional, Tuple, Any
import urllib.parse
import urllib.request
import urllib.error


# Common silent crash signatures across web frameworks & CMSs
CRASH_PATTERNS = [
    # WordPress & PHP
    (r"There has been a critical error on this website", "WordPress Critical Error (WSOD)"),
    (r"Fatal error:", "PHP Fatal Error"),
    (r"Parse error:", "PHP Syntax Parse Error"),
    (r"<b>Warning</b>:\s+.*in\s+<b>", "PHP Runtime Warning"),
    (r"Error establishing a database connection", "Database Connection Failure"),
    (r"WordPress &rsaquo; Error", "WordPress Core Database/Config Error"),
    # Python (Django / Flask / FastAPI)
    (r"Traceback \(most recent call last\):", "Python Exception Traceback"),
    (r"django\.core\.exceptions\.", "Django Core Exception"),
    (r"sqlalchemy\.exc\.", "SQLAlchemy Database Exception"),
    # Node.js / Next.js / Express
    (r"UnhandledPromiseRejectionWarning", "Node.js Unhandled Promise Rejection"),
    (r"ReferenceError:\s+\w+\s+is not defined", "Node.js ReferenceError"),
    (r"TypeError:\s+Cannot read propert", "Node.js TypeError"),
    (r"Application error: a client-side exception has occurred", "Next.js Client-Side Crash"),
    # Ruby on Rails
    (r"ActionView::Template::Error", "Rails ActionView Template Error"),
    (r"ActiveRecord::StatementInvalid", "Rails ActiveRecord SQL Error"),
    # ASP.NET / C#
    (r"Server Error in '/' Application", "ASP.NET Unhandled Server Error"),
    (r"System\.Web\.HttpException", "ASP.NET HttpException"),
]


@dataclass
class SSLCertInfo:
    valid: bool = False
    hostname: str = ""
    issuer: str = ""
    expires_at: Optional[datetime] = None
    days_left: int = 0
    error: Optional[str] = None


@dataclass
class EndpointResult:
    url: str
    label: str
    status_code: int = 0
    response_time_ms: float = 0.0
    ttfb_ms: float = 0.0
    content_length: int = 0
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    headers: Dict[str, str] = field(default_factory=dict)
    detected_frameworks: List[str] = field(default_factory=list)
    seo_meta: Dict[str, Any] = field(default_factory=dict)
    security_headers: Dict[str, bool] = field(default_factory=dict)
    is_healthy: bool = True


@dataclass
class AuditSummary:
    target_url: str
    timestamp: str
    total_endpoints: int = 0
    passed: int = 0
    failed: int = 0
    warnings_count: int = 0
    avg_latency_ms: float = 0.0
    p95_latency_ms: float = 0.0
    min_latency_ms: float = 0.0
    max_latency_ms: float = 0.0
    ssl_info: Optional[SSLCertInfo] = None
    results: List[EndpointResult] = field(default_factory=list)

    @property
    def status_label(self) -> str:
        if self.failed > 0:
            return "CRITICAL / FAILED"
        if self.warnings_count > 0:
            return "WARNINGS DETECTED"
        return "100% HEALTHY"


class MetaTagParser(html.parser.HTMLParser):
    """Zero-dependency HTML Parser to extract SEO & OpenGraph meta elements."""

    def __init__(self):
        super().__init__()
        self.in_title = False
        self.title = ""
        self.meta_tags: Dict[str, str] = {}
        self.canonical = ""

    def handle_starttag(self, tag, attrs):
        attrs_dict = {k.lower(): v for k, v in attrs}
        if tag == "title":
            self.in_title = True
        elif tag == "meta":
            name = attrs_dict.get("name") or attrs_dict.get("property") or attrs_dict.get("http-equiv")
            content = attrs_dict.get("content", "")
            if name and content:
                self.meta_tags[name.lower()] = content
        elif tag == "link":
            rel = attrs_dict.get("rel", "").lower()
            if rel == "canonical":
                self.canonical = attrs_dict.get("href", "")

    def handle_endtag(self, tag):
        if tag == "title":
            self.in_title = False

    def handle_data(self, data):
        if self.in_title:
            self.title += data


class SSLChecker:
    """Audits TLS/SSL certificate status and calculates expiration headroom."""

    @staticmethod
    def inspect(hostname: str, port: int = 443, timeout: float = 5.0) -> SSLCertInfo:
        context = ssl.create_default_context()
        try:
            with socket.create_connection((hostname, port), timeout=timeout) as sock:
                with context.wrap_socket(sock, server_hostname=hostname) as ssock:
                    cert = ssock.getpeercert()
                    if not cert:
                        return SSLCertInfo(valid=False, hostname=hostname, error="No certificate presented")

                    # Extract expiry
                    not_after_str = cert.get("notAfter")
                    if not_after_str:
                        # Format: 'May  9 12:00:00 2026 GMT'
                        expires_at = datetime.strptime(not_after_str, "%b %d %H:%M:%S %Y %Z").replace(tzinfo=timezone.utc)
                        days_left = (expires_at - datetime.now(timezone.utc)).days
                    else:
                        expires_at = None
                        days_left = 0

                    # Extract Issuer
                    issuer_parts = []
                    for rdn in cert.get("issuer", ()):
                        for attr, val in rdn:
                            if attr in ("organizationName", "commonName"):
                                issuer_parts.append(val)
                    issuer_name = " / ".join(issuer_parts) if issuer_parts else "Unknown"

                    return SSLCertInfo(
                        valid=True,
                        hostname=hostname,
                        issuer=issuer_name,
                        expires_at=expires_at,
                        days_left=days_left,
                    )
        except ssl.SSLCertVerificationError as e:
            return SSLCertInfo(valid=False, hostname=hostname, error=f"Certificate verification error: {e.verify_message}")
        except Exception as e:
            return SSLCertInfo(valid=False, hostname=hostname, error=str(e))


class SiteAuditor:
    """High-speed, multi-threaded site health and CMS auditor."""

    SECURITY_HEADERS = [
        "strict-transport-security",
        "content-security-policy",
        "x-frame-options",
        "x-content-type-options",
        "referrer-policy",
        "permissions-policy",
    ]

    def __init__(
        self,
        base_url: str,
        timeout: float = 12.0,
        concurrency: int = 8,
        user_agent: Optional[str] = None,
        cache_bust: bool = True,
        required_markers: Optional[List[str]] = None,
    ):
        self.base_url = base_url.rstrip("/")
        parsed = urllib.parse.urlparse(self.base_url)
        self.scheme = parsed.scheme or "https"
        self.hostname = parsed.netloc or parsed.path
        self.timeout = timeout
        self.concurrency = concurrency
        self.cache_bust = cache_bust
        self.required_markers = required_markers or []
        self.user_agent = user_agent or (
            "SiteHealthVerifier/2.0 (+https://github.com/a-vip/site-health-verifier; HealthCheckBot)"
        )

    def audit_single(self, path: str, label: str) -> EndpointResult:
        full_url = f"{self.base_url}{path}" if path.startswith("/") else path
        test_url = full_url

        if self.cache_bust and "?" not in test_url:
            test_url = f"{full_url}?_health_check={int(time.time() * 1000)}"
        elif self.cache_bust:
            test_url = f"{full_url}&_health_check={int(time.time() * 1000)}"

        result = EndpointResult(url=full_url, label=label)
        req = urllib.request.Request(
            test_url,
            headers={
                "User-Agent": self.user_agent,
                "Accept": "text/html,application/xhtml+xml,application/json,*/*;q=0.9",
                "Accept-Encoding": "identity",
            },
        )

        start_time = time.perf_counter()
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                elapsed = (time.perf_counter() - start_time) * 1000.0
                result.response_time_ms = round(elapsed, 2)
                result.status_code = resp.status
                result.content_length = len(resp.peek() if hasattr(resp, "peek") else b"")

                # Extract response headers
                raw_headers = {k.lower(): v for k, v in resp.headers.items()}
                result.headers = raw_headers

                # Security headers check
                for sh in self.SECURITY_HEADERS:
                    result.security_headers[sh] = sh in raw_headers

                # Read response body
                body_bytes = resp.read()
                result.content_length = len(body_bytes)
                body = body_bytes.decode("utf-8", errors="ignore")

                # Check for silent framework and PHP crashes
                for pattern, name in CRASH_PATTERNS:
                    if re.search(pattern, body, re.IGNORECASE):
                        result.errors.append(f"Silent Crash Detected: {name}")

                # Check required markers if any
                for marker in self.required_markers:
                    if marker not in body:
                        result.warnings.append(f"Expected marker missing: '{marker}'")

                # Parse SEO & OpenGraph elements if HTML
                content_type = raw_headers.get("content-type", "")
                if "html" in content_type:
                    parser = MetaTagParser()
                    try:
                        parser.feed(body[:150000])  # Scan header/first 150kb
                        title = parser.title.strip()
                        meta_desc = parser.meta_tags.get("description", "")
                        robots = parser.meta_tags.get("robots", "")

                        result.seo_meta = {
                            "title": title,
                            "title_len": len(title),
                            "description": meta_desc,
                            "desc_len": len(meta_desc),
                            "canonical": parser.canonical,
                            "robots": robots,
                            "og_title": parser.meta_tags.get("og:title", ""),
                            "og_image": parser.meta_tags.get("og:image", ""),
                        }

                        # Warn if title or description is missing in HTML page
                        if not title:
                            result.warnings.append("Missing <title> tag")
                        if not meta_desc:
                            result.warnings.append("Missing meta description")
                        if "noindex" in robots.lower():
                            result.warnings.append("Page has 'noindex' robots directive")
                    except Exception:
                        pass

                # Latency warnings
                if result.response_time_ms > 2500:
                    result.warnings.append(f"High Latency: {result.response_time_ms:.0f}ms (>2500ms)")

                # HTTP error status check
                if result.status_code >= 400:
                    result.errors.append(f"HTTP Status Error: {result.status_code}")

        except urllib.error.HTTPError as e:
            elapsed = (time.perf_counter() - start_time) * 1000.0
            result.response_time_ms = round(elapsed, 2)
            result.status_code = e.code
            result.errors.append(f"HTTP Error {e.code}: {e.reason}")
        except urllib.error.URLError as e:
            elapsed = (time.perf_counter() - start_time) * 1000.0
            result.response_time_ms = round(elapsed, 2)
            result.errors.append(f"Network Unreachable: {e.reason}")
        except socket.timeout:
            result.response_time_ms = round(self.timeout * 1000.0, 2)
            result.errors.append(f"Request Timed Out (> {self.timeout}s)")
        except Exception as e:
            result.errors.append(f"Unexpected Exception: {str(e)}")

        result.is_healthy = len(result.errors) == 0
        return result

    def run(self, endpoints: List[Tuple[str, str]]) -> AuditSummary:
        """Executes concurrent endpoint diagnostics and SSL health evaluation."""
        summary = AuditSummary(
            target_url=self.base_url,
            timestamp=datetime.now(timezone.utc).isoformat(),
            total_endpoints=len(endpoints),
        )

        # Inspect SSL certificate if HTTPS
        if self.scheme == "https":
            summary.ssl_info = SSLChecker.inspect(self.hostname)

        # Concurrently audit endpoints
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.concurrency) as executor:
            future_to_ep = {
                executor.submit(self.audit_single, path, label): (path, label)
                for path, label in endpoints
            }
            for future in concurrent.futures.as_completed(future_to_ep):
                res = future.result()
                summary.results.append(res)
                if res.is_healthy:
                    summary.passed += 1
                else:
                    summary.failed += 1
                summary.warnings_count += len(res.warnings)

        # Order results to match original endpoints order
        order_map = {f"{self.base_url}{path}": idx for idx, (path, _) in enumerate(endpoints)}
        summary.results.sort(key=lambda r: order_map.get(r.url, 999))

        # Latency statistics
        latencies = [r.response_time_ms for r in summary.results if r.response_time_ms > 0]
        if latencies:
            latencies.sort()
            summary.min_latency_ms = round(min(latencies), 1)
            summary.max_latency_ms = round(max(latencies), 1)
            summary.avg_latency_ms = round(sum(latencies) / len(latencies), 1)
            p95_idx = int(len(latencies) * 0.95)
            summary.p95_latency_ms = round(latencies[p95_idx if p95_idx < len(latencies) else -1], 1)

        return summary
