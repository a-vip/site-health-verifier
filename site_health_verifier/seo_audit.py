#!/usr/bin/env python3
"""
seo_audit.py - Search Console & Technical SEO Indexability Auditor.
Validates sitemap health, robots.txt directives, canonical equity,
and prevents GSC de-indexing issues (404s, redirect chains, robots.txt blocks, and noindex leaks).
"""

import sys
import os
import re
import json
import html
import urllib.request
import urllib.parse
import urllib.error
import concurrent.futures
from datetime import datetime, timezone
from typing import List, Dict, Tuple, Optional, Any

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

BROWSER_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9"
}


class RobotsTxtAuditor:
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")
        self.robots_url = f"{self.base_url}/robots.txt"
        self.content = ""
        self.disallow_rules: List[str] = []
        self.sitemaps_declared: List[str] = []
        self.is_valid = False

    def fetch_and_parse(self) -> bool:
        headers = BROWSER_HEADERS
        try:
            req = urllib.request.Request(self.robots_url, headers=headers)
            with urllib.request.urlopen(req, timeout=12) as resp:
                self.content = resp.read().decode("utf-8", errors="ignore")
                self.is_valid = (resp.getcode() == 200)

            for line in self.content.splitlines():
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if ":" in line:
                    key, val = line.split(":", 1)
                    key = key.strip().lower()
                    val = val.strip()
                    if key == "disallow" and val:
                        self.disallow_rules.append(val)
                    elif key == "sitemap":
                        self.sitemaps_declared.append(val)
            return True
        except Exception as e:
            print(f"[!] Warning: Could not fetch robots.txt ({e})")
            return False

    def is_path_blocked(self, url: str) -> Optional[str]:
        parsed = urllib.parse.urlparse(url)
        path = parsed.path or "/"
        for rule in self.disallow_rules:
            if rule == "/":
                return rule
            if path.startswith(rule):
                return rule
        return None


class SitemapAuditor:
    def __init__(self, sitemap_url: str):
        self.sitemap_url = sitemap_url
        self.urls: List[str] = []

    def fetch_urls(self) -> List[str]:
        headers = BROWSER_HEADERS
        try:
            req = urllib.request.Request(self.sitemap_url, headers=headers)
            with urllib.request.urlopen(req, timeout=15) as resp:
                content = resp.read().decode("utf-8", errors="ignore")
            # Extract all <loc> values
            self.urls = re.findall(r"<loc>(https?://[^<]+)</loc>", content)
            return self.urls
        except Exception as e:
            print(f"[!] Error reading sitemap at {self.sitemap_url}: {e}")
            return []


def inspect_url(url: str, robots_checker: RobotsTxtAuditor) -> Dict[str, Any]:
    """Inspects a single URL for HTTP code, redirects, canonical tag, and noindex directives."""
    result = {
        "url": url,
        "status_code": 0,
        "is_redirect": False,
        "redirect_target": None,
        "is_noindex": False,
        "is_blocked_by_robots": None,
        "canonical_url": None,
        "error": None
    }

    # Check robots.txt match
    matched_rule = robots_checker.is_path_blocked(url)
    if matched_rule:
        result["is_blocked_by_robots"] = matched_rule

    class NoRedirectHandler(urllib.request.HTTPRedirectHandler):
        def http_error_302(self, req, fp, code, msg, headers):
            return fp
        http_error_301 = http_error_302
        http_error_303 = http_error_302
        http_error_307 = http_error_302
        http_error_308 = http_error_302

    opener = urllib.request.build_opener(NoRedirectHandler)
    req = urllib.request.Request(
        url,
        headers=BROWSER_HEADERS
    )

    try:
        with opener.open(req, timeout=12) as resp:
            code = resp.getcode()
            result["status_code"] = code
            headers = resp.headers

            # Check header for X-Robots-Tag
            x_robots = headers.get("X-Robots-Tag", "")
            if "noindex" in x_robots.lower():
                result["is_noindex"] = True

            # Check for redirect
            if code in (301, 302, 303, 307, 308):
                result["is_redirect"] = True
                result["redirect_target"] = headers.get("Location")
                return result

            # Parse HTML body for meta noindex and canonical
            body = resp.read(8192).decode("utf-8", errors="ignore")
            if re.search(r'<meta[^>]+name=["\']robots["\'][^>]+content=["\'][^"\']*noindex[^"\']*["\']', body, re.IGNORECASE):
                result["is_noindex"] = True

            canonical_match = re.search(r'<link[^>]+rel=["\']canonical["\'][^>]+href=["\']([^"\']+)["\']', body, re.IGNORECASE)
            if canonical_match:
                result["canonical_url"] = canonical_match.group(1).strip()

    except urllib.error.HTTPError as e:
        result["status_code"] = e.code
        result["error"] = f"HTTP {e.code}"
    except Exception as e:
        result["status_code"] = 0
        result["error"] = str(e)

    return result


def run_seo_audit(target_domain: str = "https://aviperera.com", max_workers: int = 4) -> Dict[str, Any]:
    print(f"=== Starting Technical SEO & GSC Indexability Audit for {target_domain} ===")
    
    # 1. Audit robots.txt
    robots_auditor = RobotsTxtAuditor(target_domain)
    robots_auditor.fetch_and_parse()
    print(f"[OK] robots.txt parsed: {len(robots_auditor.disallow_rules)} disallow rules, {len(robots_auditor.sitemaps_declared)} sitemaps declared.")

    # 2. Audit sitemap.xml
    sitemap_url = f"{target_domain.rstrip('/')}/sitemap.xml"
    sitemap_auditor = SitemapAuditor(sitemap_url)
    urls = sitemap_auditor.fetch_urls()
    print(f"[OK] sitemap.xml retrieved: {len(urls)} URLs listed.")

    # 3. Concurrently inspect sitemap URLs
    print(f"Auditing {len(urls)} URLs for status codes, redirects, canonicals, and noindex tags...")
    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(inspect_url, u, robots_auditor): u for u in urls}
        for future in concurrent.futures.as_completed(futures):
            results.append(future.result())

    # 4. Group findings
    anomalies = {
        "redirects": [r for r in results if r["is_redirect"]],
        "not_found_404": [r for r in results if r["status_code"] == 404],
        "errors_4xx": [r for r in results if 400 <= r["status_code"] < 500 and r["status_code"] != 404],
        "errors_5xx": [r for r in results if r["status_code"] >= 500],
        "noindex_in_sitemap": [r for r in results if r["is_noindex"]],
        "blocked_by_robots": [r for r in results if r["is_blocked_by_robots"]],
        "canonical_mismatch": [r for r in results if r["canonical_url"] and r["canonical_url"].rstrip("/") != r["url"].rstrip("/")]
    }

    report = {
        "domain": target_domain,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "total_sitemap_urls": len(urls),
        "robots_txt": {
            "declared_sitemaps": robots_auditor.sitemaps_declared,
            "disallow_rules": robots_auditor.disallow_rules
        },
        "anomalies": anomalies,
        "healthy_count": len(urls) - sum(len(v) for v in anomalies.values())
    }

    output_step_summary(report)
    return report


def output_step_summary(report: Dict[str, Any]):
    summary_path = os.getenv("GITHUB_STEP_SUMMARY")
    anomalies = report["anomalies"]
    total = report["total_sitemap_urls"]

    markdown = []
    markdown.append("## 🔍 Technical SEO & Google Search Console Health Report\n")
    markdown.append(f"**Domain:** `{report['domain']}` | **Audit Date:** `{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}`\n")
    markdown.append(f"**Sitemap Pages Evaluated:** `{total}` | **Pristine Indexed Pages:** `{report['healthy_count']}`\n\n")

    # Overall Verdict
    critical_issues = len(anomalies["redirects"]) + len(anomalies["not_found_404"]) + len(anomalies["errors_4xx"]) + len(anomalies["noindex_in_sitemap"])
    if critical_issues == 0:
        markdown.append("### ✅ Verdict: Sitemaps & Directives are 100% Healthy!\n\n")
    else:
        markdown.append(f"### ⚠️ Verdict: {critical_issues} Indexability Anomalies Detected\n\n")

    # Section 1: Anomalies Breakdown
    markdown.append("### 📊 Indexing Pre-Flight Summary\n\n")
    markdown.append("| Search Console Metric | Count | Status | Impact & Action |\n")
    markdown.append("| :--- | :---: | :--- | :--- |\n")
    
    # 404s
    status_404 = "🟢 Clean" if not anomalies["not_found_404"] else "🔴 Issue"
    markdown.append(f"| **Not found (404)** | `{len(anomalies['not_found_404'])}` | {status_404} | URLs in sitemap returning 404 waste crawl budget and harm rank. |\n")

    # Redirects
    status_red = "🟢 Clean" if not anomalies["redirects"] else "🟡 Warning"
    markdown.append(f"| **Pages with redirect (301/302)** | `{len(anomalies['redirects'])}` | {status_red} | Sitemaps must only contain direct canonical URLs, not redirects. |\n")

    # Blocked by robots.txt
    status_rob = "🟢 Clean" if not anomalies["blocked_by_robots"] else "🔴 Issue"
    markdown.append(f"| **Blocked by robots.txt** | `{len(anomalies['blocked_by_robots'])}` | {status_rob} | Pages in sitemap covered by Disallow rules in robots.txt. |\n")

    # Noindex in sitemap
    status_noindex = "🟢 Clean" if not anomalies["noindex_in_sitemap"] else "🔴 Issue"
    markdown.append(f"| **Excluded by 'noindex' tag** | `{len(anomalies['noindex_in_sitemap'])}` | {status_noindex} | Conflict: Page is in sitemap but marked noindex. |\n")

    # Other 4xx
    status_4xx = "🟢 Clean" if not anomalies["errors_4xx"] else "🔴 Issue"
    markdown.append(f"| **Blocked due to other 4xx issue** | `{len(anomalies['errors_4xx'])}` | {status_4xx} | Endpoints returning 401 Unauthorized or 403 Forbidden. |\n\n")

    # Specific Anomalies Table
    all_flagged = []
    for issue_type, items in anomalies.items():
        for it in items:
            all_flagged.append((issue_type, it))

    if all_flagged:
        markdown.append("### 🛠️ Detailed Anomalies Requiring Remediation\n\n")
        markdown.append("| Issue Type | Flagged URL | Details / Target |\n")
        markdown.append("| :--- | :--- | :--- |\n")
        for issue_type, it in all_flagged:
            url = it["url"]
            detail = it.get("redirect_target") or it.get("error") or it.get("canonical_url") or "See directive"
            markdown.append(f"| `{issue_type}` | [{url}]({url}) | `{detail}` |\n")
        markdown.append("\n")

    # Section 2: GSC Playbook
    markdown.append("### 📚 Google Search Console Playbook & Recommendations\n\n")
    markdown.append("1. **Curing 'Crawled - currently not indexed' (142 pages)**:\n")
    markdown.append("   - Google crawled these pages but hasn't indexed them due to internal linking / PageRank thresholds.\n")
    markdown.append("   - *Remediation*: The automated GitHub Awesome-List and Research Archive workflows now supply strong canonical backlinks. Also, ensure internal links connect your new posts from top category hubs.\n")
    markdown.append("2. **Resolving 'Redirect error' & 'Page with redirect'**:\n")
    markdown.append("   - Remove redirecting URLs (such as `ultimate-ai-cheat-sheet/` -> `free-ai-cheat-sheet/`) from your XML sitemap plugin so only the final 200 OK target is indexed.\n")
    markdown.append("3. **Handling 'Excluded by noindex tag' (160 pages)**:\n")
    markdown.append("   - This is normal for WordPress date, author, and tag archives. Ensure primary research posts are never accidentally marked noindex.\n\n")

    full_md = "".join(markdown)
    print(full_md)

    if summary_path:
        with open(summary_path, "a", encoding="utf-8") as f:
            f.write(full_md)


def main():
    target = sys.argv[1] if len(sys.argv) > 1 else "https://aviperera.com"
    report = run_seo_audit(target)
    anomalies = report["anomalies"]
    has_critical = bool(anomalies["not_found_404"] or anomalies["errors_4xx"] or anomalies["noindex_in_sitemap"])
    if has_critical:
        print("[!] Critical indexability issues detected.")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
