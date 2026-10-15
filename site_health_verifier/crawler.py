"""
crawler.py - Discovery engine for sitemaps and route endpoints.
Discovers pages from sitemap.xml, robots.txt, or custom input lists without external dependencies.
"""

import re
import urllib.parse
import urllib.request
import urllib.error
import xml.etree.ElementTree as ET
from typing import List, Tuple, Set


class RouteDiscoverer:
    """Discovers paths and endpoints from sitemaps, robots.txt, or default routes."""

    DEFAULT_FALLBACK_ROUTES = [
        ("/", "Home Page"),
        ("/robots.txt", "Robots.txt"),
        ("/sitemap.xml", "XML Sitemap"),
        ("/about/", "About Page"),
        ("/contact/", "Contact Page"),
        ("/blog/", "Blog / Archive"),
    ]

    @staticmethod
    def from_sitemap(base_url: str, max_urls: int = 25, timeout: float = 8.0) -> List[Tuple[str, str]]:
        """Parses sitemap.xml and returns a list of (path, label) tuples."""
        sitemap_url = urllib.parse.urljoin(base_url, "/sitemap.xml")
        req = urllib.request.Request(
            sitemap_url,
            headers={"User-Agent": "SiteHealthVerifier/2.0 (SitemapCrawler)"},
        )

        routes: List[Tuple[str, str]] = []
        seen_paths: Set[str] = set()

        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                xml_content = resp.read()
                try:
                    root = ET.fromstring(xml_content)
                    # Handle namespace wildcard
                    for elem in root.iter():
                        if elem.tag.endswith("loc") and elem.text:
                            url = elem.text.strip()
                            # Check if it is a sub-sitemap or page
                            if url.endswith(".xml"):
                                continue
                            parsed = urllib.parse.urlparse(url)
                            path = parsed.path or "/"
                            if parsed.query:
                                path += f"?{parsed.query}"
                            if path not in seen_paths:
                                seen_paths.add(path)
                                label = path.strip("/").replace("-", " ").title() or "Home Page"
                                routes.append((path, label))
                                if len(routes) >= max_urls:
                                    break
                except ET.ParseError:
                    # Regex fallback if malformed XML
                    text = xml_content.decode("utf-8", errors="ignore")
                    urls = re.findall(r"<loc>(https?://[^<]+)</loc>", text)
                    for url in urls:
                        if not url.endswith(".xml"):
                            parsed = urllib.parse.urlparse(url)
                            path = parsed.path or "/"
                            if path not in seen_paths:
                                seen_paths.add(path)
                                label = path.strip("/").replace("-", " ").title() or "Home Page"
                                routes.append((path, label))
                                if len(routes) >= max_urls:
                                    break
        except Exception:
            pass

        return routes

    @staticmethod
    def parse_custom_routes(routes_input: List[str]) -> List[Tuple[str, str]]:
        """Converts user-supplied route strings into structured endpoint tuples."""
        endpoints = []
        for r in routes_input:
            path = r.strip()
            if not path:
                continue
            if not path.startswith("http") and not path.startswith("/"):
                path = "/" + path
            label = path.strip("/").replace("-", " ").replace("/", " > ").title() or "Home Page"
            endpoints.append((path, label))
        return endpoints
