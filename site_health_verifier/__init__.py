"""
Site Health Verifier
Zero-dependency pre/post-deployment health check, silent crash detector, and uptime auditor.
"""

from .auditor import (
    SiteAuditor,
    AuditSummary,
    EndpointResult,
    SSLCertInfo,
    SSLChecker,
)
from .crawler import RouteDiscoverer
from .formatters import (
    TerminalFormatter,
    MarkdownFormatter,
    JSONFormatter,
)

__version__ = "2.0.0"
__author__ = "Avi Perera"
__license__ = "MIT"

__all__ = [
    "SiteAuditor",
    "AuditSummary",
    "EndpointResult",
    "SSLCertInfo",
    "SSLChecker",
    "RouteDiscoverer",
    "TerminalFormatter",
    "MarkdownFormatter",
    "JSONFormatter",
    "verify_site",
]


def verify_site(url: str, paths=None, concurrency: int = 8, timeout: float = 12.0) -> AuditSummary:
    """Convenience helper function to run an audit programmatically in Python."""
    auditor = SiteAuditor(base_url=url, concurrency=concurrency, timeout=timeout)
    if not paths:
        endpoints = RouteDiscoverer.DEFAULT_FALLBACK_ROUTES
    else:
        endpoints = RouteDiscoverer.parse_custom_routes(paths)
    return auditor.run(endpoints)
