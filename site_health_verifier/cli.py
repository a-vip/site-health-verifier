"""
cli.py - Command Line Interface for Site Health Verifier.
Provides full CLI control, CI/CD pipeline automation, and output formatting.
"""

import argparse
import sys
from typing import List, Tuple

# Enable UTF-8 encoding safely on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
if hasattr(sys.stderr, "reconfigure"):
    try:
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from .auditor import SiteAuditor
from .crawler import RouteDiscoverer
from .formatters import TerminalFormatter, MarkdownFormatter, JSONFormatter


def parse_args(argv: List[str] = None):
    parser = argparse.ArgumentParser(
        prog="sitehealth",
        description="⚡ Site Health Verifier — Zero-dependency Pre/Post-Deployment Health & CMS Crash Auditor.",
        epilog="Example: sitehealth https://example.com --sitemap --format terminal",
    )

    parser.add_argument("url", help="Target website base URL (e.g. https://example.com)")
    parser.add_argument(
        "-p", "--path",
        action="append",
        dest="paths",
        help="Specific path(s) to audit (can be specified multiple times, e.g. -p /about -p /contact)",
    )
    parser.add_argument(
        "--sitemap",
        action="store_true",
        help="Automatically discover and test routes listed in /sitemap.xml",
    )
    parser.add_argument(
        "-f", "--file",
        dest="routes_file",
        help="Path to a text file containing routes (one per line) or JSON config",
    )
    parser.add_argument(
        "-m", "--marker",
        action="append",
        dest="markers",
        help="Required text marker(s) expected in response bodies (flags warning if missing)",
    )
    parser.add_argument(
        "-c", "--concurrency",
        type=int,
        default=8,
        help="Number of concurrent worker threads (default: 8)",
    )
    parser.add_argument(
        "-t", "--timeout",
        type=float,
        default=12.0,
        help="Request timeout in seconds (default: 12.0)",
    )
    parser.add_argument(
        "--no-cache-bust",
        action="store_true",
        help="Disable cache-busting query parameter (?_health_check=...)",
    )
    parser.add_argument(
        "--format",
        choices=["terminal", "markdown", "json"],
        default="terminal",
        help="Output format (default: terminal)",
    )
    parser.add_argument(
        "-o", "--output",
        dest="output_file",
        help="File path to save the generated report",
    )
    parser.add_argument(
        "--fail-on-warnings",
        action="store_true",
        help="Exit with non-zero code if any warnings (SEO, missing markers, high latency) are detected",
    )
    parser.add_argument(
        "--no-color",
        action="store_true",
        help="Disable ANSI colors in terminal output",
    )

    return parser.parse_args(argv)


def main(argv: List[str] = None) -> int:
    args = parse_args(argv)

    endpoints: List[Tuple[str, str]] = []

    # 1. Custom CLI paths
    if args.paths:
        endpoints.extend(RouteDiscoverer.parse_custom_routes(args.paths))

    # 2. File paths
    if args.routes_file:
        try:
            with open(args.routes_file, "r", encoding="utf-8") as f:
                lines = [line.strip() for line in f if line.strip() and not line.startswith("#")]
                endpoints.extend(RouteDiscoverer.parse_custom_routes(lines))
        except Exception as e:
            print(f"Error reading routes file '{args.routes_file}': {e}", file=sys.stderr)
            return 1

    # 3. Sitemap discovery
    if args.sitemap:
        sitemap_routes = RouteDiscoverer.from_sitemap(args.url)
        if sitemap_routes:
            endpoints.extend(sitemap_routes)
        else:
            print("Notice: No routes could be extracted from /sitemap.xml. Using default endpoints.", file=sys.stderr)

    # 4. Fallback defaults if no routes provided
    if not endpoints:
        endpoints = list(RouteDiscoverer.DEFAULT_FALLBACK_ROUTES)

    # Deduplicate routes preserving order
    seen = set()
    deduped_endpoints = []
    for path, label in endpoints:
        if path not in seen:
            seen.add(path)
            deduped_endpoints.append((path, label))

    # Initialize auditor
    auditor = SiteAuditor(
        base_url=args.url,
        timeout=args.timeout,
        concurrency=args.concurrency,
        cache_bust=not args.no_cache_bust,
        required_markers=args.markers or [],
    )

    # Run audit
    summary = auditor.run(deduped_endpoints)

    # Format output
    if args.format == "markdown":
        output = MarkdownFormatter.format(summary)
    elif args.format == "json":
        output = JSONFormatter.format(summary)
    else:
        output = TerminalFormatter.format(summary, use_color=not args.no_color)

    # Output to stdout or file
    if args.output_file:
        try:
            with open(args.output_file, "w", encoding="utf-8") as f:
                f.write(output)
            print(f"Report written to {args.output_file}")
        except Exception as e:
            print(f"Failed to write output file: {e}", file=sys.stderr)
    else:
        print(output)

    # Determine exit code for CI/CD
    if summary.failed > 0:
        return 1
    if args.fail_on_warnings and summary.warnings_count > 0:
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
