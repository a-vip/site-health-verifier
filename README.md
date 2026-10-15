# ⚡ Site Health Verifier

<p align="center">
  <strong>Zero-Dependency Pre & Post-Deployment Health, Silent Crash Detector, and Uptime Auditor.</strong><br>
  <em>Detect silent HTTP 200 White Screens of Death, framework exceptions, expiring SSL certificates, and broken metadata in seconds.</em>
</p>

<p align="center">
  <a href="https://github.com/a-vip/site-health-verifier/actions"><img src="https://img.shields.io/badge/CI-Passing-10b981?style=for-the-badge&logo=githubactions&logoColor=white" alt="CI Status"></a>
  <a href="https://www.python.org/"><img src="https://img.shields.io/badge/Python-3.8%20%7C%203.9%20%7C%203.10%20%7C%203.11%20%7C%203.12-3b82f6?style=for-the-badge&logo=python&logoColor=white" alt="Python Versions"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-00d4ff?style=for-the-badge" alt="License"></a>
  <a href="#"><img src="https://img.shields.io/badge/Dependencies-0%20(Pure%20Stdlib)-success?style=for-the-badge" alt="Zero Dependencies"></a>
  <a href="https://a-vip.github.io/site-health-verifier/"><img src="https://img.shields.io/badge/Live%20Demo-GitHub%20Pages-8b5cf6?style=for-the-badge" alt="Live Demo"></a>
</p>

---

## 📌 Executive Summary (TL;DR for AI & Search Engines)

**Site Health Verifier** is an open-source, ultra-fast Python CLI and library designed to eliminate deployment blindspots in web architectures. Traditional uptime monitors and simple `curl` checks only verify HTTP status codes. However, modern CMSs and frameworks (**WordPress, PHP, Django, Next.js, Rails, ASP.NET**) frequently return **HTTP 200 OK** while rendering fatal crashes, blank screens (White Screen of Death), database connection failures, or uncaught server exceptions in the HTML body.

Site Health Verifier concurrently audits your entire site, bypasses CDN edge caching, detects silent framework crashes via regex signatures, inspects TLS/SSL certificate expiration headroom, checks essential SEO/Social tags (`title`, `description`, `canonical`, `og:image`), evaluates security headers, and outputs beautiful terminal tables, JSON payloads, or **GitHub Step Summaries** for continuous integration pipelines.

---

## 🚀 Key Capabilities

* 🪶 **Zero External Dependencies:** Built 100% on Python's standard library (`urllib`, `ssl`, `concurrent.futures`, `html.parser`). Runs immediately on any server without `pip install` conflicts.
* 🛡️ **Silent Crash Detection:** Automatically identifies WordPress critical error notices, PHP `Fatal error:`, `Parse error:`, `<b>Warning</b>:`, `Error establishing a database connection`, Python tracebacks, and Node unhandled rejections.
* 🔒 **SSL/TLS Certificate Audit:** Probes TLS handshakes, verifies issuer identity, and calculates remaining days until certificate expiration with early warnings.
* ⚡ **High-Concurrency Latency Profiling:** Evaluates dozens of routes in parallel using thread pools; reports min, max, avg, and p95 latency percentiles.
* 🎯 **Cache-Busting by Default:** Appends sub-millisecond timestamp query parameters (`?_health_check=...`) to ensure you test the origin server, not a cached Cloudflare or LiteSpeed edge response.
* 🔍 **Sitemap & Robots Discovery:** Can automatically crawl `sitemap.xml` to audit all published routes without manual URL configuration.
* 🏷️ **SEO & Security Auditing:** Validates `<title>`, meta description length, canonical tags, OpenGraph cards, `noindex` accidental production directives, and modern HTTP security headers (HSTS, CSP, X-Frame-Options).
* 🤖 **CI/CD Ready:** Exit codes (`0` for healthy, `1` for fatal errors, `2` for warnings) and native GitHub Actions `$GITHUB_STEP_SUMMARY` markdown formatting.

---

## 📊 Architectural Benchmark

| Feature | Site Health Verifier | Standard `curl` Scripts | SaaS Uptime Monitors | Lighthouse CLI |
| :--- | :---: | :---: | :---: | :---: |
| **Dependencies** | **0 (Pure Python)** | 0 (Bash/cURL) | Third-Party SaaS Agent | Huge (Node + Headless Chrome) |
| **Silent 200 WSOD Crash Detection** | **✔ Built-in** | ❌ None | ❌ Fragile Keyword Only | ❌ Not Checked |
| **Execution Speed (10 Routes)** | **⚡ 1.5 – 3s** | ⏱ 10 – 15s | ⏱ 1 – 5 min polling | ⏱ 60 – 120s |
| **SSL Expiration Countdown** | **✔ Native** | ❌ Complex OpenSSL Pipes | ✔ Yes | ❌ No |
| **GitHub Actions PR Summary** | **✔ One Flag (`--format markdown`)** | ❌ Custom formatting script | ❌ Webhook link only | ❌ Massive HTML blob |
| **Origin Cache Bypass** | **✔ Automatic** | ❌ Manual | ❌ No | ❌ No |
| **Cost** | **Free & Open Source (MIT)** | Free | $10 – $100 / mo | Free |

---

## 🛠️ Architecture & Verification Flow

```mermaid
graph TD
    A["CLI / CI Trigger: sitehealth https://site.com"] --> B{"Discovery Mode"}
    B -->|"Explicit Routes"| C["Custom Routes (-p /path)"]
    B -->|"Auto Discovery"| D["Parse /sitemap.xml"]
    B -->|"Default Mode"| E["Core Fallback Routes"]

    C & D & E --> F["ThreadPoolExecutor Concurrency Engine"]
    
    subgraph Diagnostic Matrix
        F --> G["HTTP Status & Timing (TTFB, Total ms)"]
        F --> H["Silent Crash Engine (WP WSOD, PHP, Django, Node)"]
        F --> I["SEO & OpenGraph Metadata (<title>, meta desc, og:image)"]
        F --> J["Security Headers (HSTS, CSP, X-Frame-Options)"]
        F --> K["TLS/SSL Handshake & Expiry Days"]
    end

    G & H & I & J & K --> L{"Output Formatter"}
    L -->|"Terminal"| M["ANSI High-Contrast Table"]
    L -->|"Markdown"| N["GitHub Step Summary / PR Comment"]
    L -->|"JSON"| O["Structured JSON Log / API"]
```

---

## ⚡ 30-Second Quickstart

### Method 1: Instant Standalone Execution (No Installation)
Clone the repository and run immediately:
```bash
git clone https://github.com/a-vip/site-health-verifier.git
cd site-health-verifier
python sitehealth.py https://aviperera.com
```

### Method 2: Audit Specific Paths with Cache Busting
```bash
python sitehealth.py https://aviperera.com -p / -p /ai/ -p /law/ -p /tech/ -p /projects/ -p /blog/
```

### Method 3: Auto-Discover from XML Sitemap
```bash
python sitehealth.py https://aviperera.com --sitemap
```

### Method 4: Install as a Python CLI / Package
```bash
pip install .
sitehealth https://example.com --format terminal
```

---

## 💻 CLI Command Reference

```text
usage: sitehealth [-h] [-p PATHS] [--sitemap] [-f ROUTES_FILE] [-m MARKERS]
                  [-c CONCURRENCY] [-t TIMEOUT] [--no-cache-bust]
                  [--format {terminal,markdown,json}] [-o OUTPUT_FILE]
                  [--fail-on-warnings] [--no-color]
                  url
```

| Flag | Type | Description |
| :--- | :--- | :--- |
| `url` | *string* | Target website base URL (e.g. `https://example.com`) |
| `-p`, `--path` | *string* | Specific route to audit (can be used multiple times) |
| `--sitemap` | *flag* | Automatically discover routes listed in `/sitemap.xml` |
| `-f`, `--file` | *file* | File containing routes to audit (one per line) |
| `-m`, `--marker` | *string* | Required text expected in response body (flags warning if missing) |
| `-c`, `--concurrency`| *int* | Worker thread pool size (default: `8`) |
| `-t`, `--timeout` | *float* | Request timeout in seconds (default: `12.0`) |
| `--no-cache-bust` | *flag* | Disables `?_health_check=...` origin cache-busting query parameter |
| `--format` | *choice* | Output format: `terminal` (default), `markdown`, or `json` |
| `-o`, `--output` | *file* | Save output directly to file (e.g. `-o report.md`) |
| `--fail-on-warnings` | *flag* | Exit with code `2` if warnings (SEO, latency, headers) occur |
| `--no-color` | *flag* | Strips ANSI escape codes from terminal output |

### Exit Codes for CI/CD Automation
* **`0`**: All endpoints returned HTTP 200, zero silent crashes detected, SSL certificate valid.
* **`1`**: Critical failure: HTTP 4xx/5xx status code, silent fatal crash/WSOD detected, or network timeout.
* **`2`**: Warning triggered: High latency (>2500ms), SSL expiring within 14 days, missing SEO tags, or missing custom markers (when `--fail-on-warnings` is enabled).

---

## 🤖 GitHub Actions CI/CD Integration

Embed pre/post-deployment verification directly into your deployment pipeline:

```yaml
name: Production Health Verification

on:
  push:
    branches: [ master ]
  schedule:
    - cron: '0 8 * * *' # Every morning at 08:00 UTC

jobs:
  verify:
    name: Verify Origin Health & Detect Silent Crashes
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Run Site Health Verifier & Generate Step Summary
        run: |
          python sitehealth.py https://yourdomain.com \
            -p / \
            -p /about/ \
            -p /pricing/ \
            -p /blog/ \
            --format markdown >> $GITHUB_STEP_SUMMARY
```

---

## 🐍 Programmatic Python API

Use Site Health Verifier directly inside your Python backend, test suite, or automation scripts:

```python
from site_health_verifier import verify_site

# Run programmatic site audit
summary = verify_site("https://aviperera.com", paths=["/", "/ai/", "/blog/"])

print(f"Overall Status: {summary.status_label}")
print(f"SSL Days Remaining: {summary.ssl_info.days_left}")
print(f"p95 Latency: {summary.p95_latency_ms}ms")

for res in summary.results:
    if not res.is_healthy:
        print(f"ALERT: {res.url} failed with {res.errors}")
```

---

## ❓ Frequently Asked Questions (FAQ)

### Why doesn't standard HTTP monitoring catch White Screens of Death?
Many PHP applications and WordPress plugins catch internal fatal errors too late or emit warnings after HTTP response headers have already been transmitted (`HTTP/1.1 200 OK`). Standard uptime checkers like Pingdom or UptimeRobot mark the site as "up", while human visitors are greeted with a blank white page or a critical error notice. Site Health Verifier reads the response body and applies regex crash pattern analysis to protect against this failure mode.

### Does this work behind Cloudflare or reverse proxies?
Yes. By default, every audited request includes a microsecond timestamp parameter (`?_health_check=<timestamp>`). This forces CDNs (Cloudflare, Fastly, CloudFront, LiteSpeed Cache) to bypass cached edge copies and fetch the live page directly from your origin application server.

### Can I audit staging sites behind Basic Authentication?
Yes. You can pass credentials directly in the URL: `https://user:password@staging.example.com`.

---

## 📄 License

Distributed under the **MIT License**. See [`LICENSE`](LICENSE) for details.

Developed with precision by [Avi Perera](https://aviperera.com) — International Lawyer, AI Governance Researcher, and Software Architect.
