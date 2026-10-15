"""
formatters.py - Presentation layer for Site Health Verifier.
Generates ANSI color-formatted terminal tables, GitHub Actions markdown summaries,
and machine-readable JSON exports.
"""

import json
from typing import Dict, Any
from .auditor import AuditSummary


class Colors:
    """Standard ANSI terminal escape codes with safe disabling."""
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    CYAN = "\033[96m"
    BLUE = "\033[94m"
    MAGENTA = "\033[95m"
    BG_GREEN = "\033[42m\033[30m"
    BG_RED = "\033[41m\033[97m"
    BG_YELLOW = "\033[43m\033[30m"


class TerminalFormatter:
    """Renders human-readable, high-contrast CLI reports."""

    @staticmethod
    def format(summary: AuditSummary, use_color: bool = True) -> str:
        c = Colors if use_color else type("NoColor", (), {k: "" for k in dir(Colors) if not k.startswith("_")})()
        lines = []

        # Header banner
        lines.append(f"{c.BOLD}{c.CYAN}┌──────────────────────────────────────────────────────────────┐{c.RESET}")
        lines.append(f"{c.BOLD}{c.CYAN}│        ⚡ SITE HEALTH VERIFIER — AUDIT REPORT                │{c.RESET}")
        lines.append(f"{c.BOLD}{c.CYAN}└──────────────────────────────────────────────────────────────┘{c.RESET}")
        lines.append(f"{c.DIM}Target URL:   {c.RESET}{c.BOLD}{summary.target_url}{c.RESET}")
        lines.append(f"{c.DIM}Timestamp:    {c.RESET}{summary.timestamp}")
        lines.append(f"{c.DIM}Endpoints:    {c.RESET}{summary.total_endpoints} checked")

        # SSL Section
        if summary.ssl_info:
            ssl = summary.ssl_info
            if ssl.valid:
                badge = f"{c.GREEN}VALID ({ssl.days_left} days remaining){c.RESET}"
                if ssl.days_left < 14:
                    badge = f"{c.YELLOW}EXPIRING SOON ({ssl.days_left} days left){c.RESET}"
                lines.append(f"{c.DIM}TLS/SSL:      {c.RESET}🔒 {badge} {c.DIM}(Issuer: {ssl.issuer}){c.RESET}")
            else:
                lines.append(f"{c.DIM}TLS/SSL:      {c.RESET}❌ {c.RED}INVALID - {ssl.error}{c.RESET}")

        lines.append("-" * 64)
        lines.append(f"{c.BOLD}{'STATUS':<8} {'ENDPOINT':<24} {'HTTP':<6} {'LATENCY':<10} {'DIAGNOSTICS'}{c.RESET}")
        lines.append("-" * 64)

        for res in summary.results:
            if res.is_healthy and not res.warnings:
                status_badge = f"{c.GREEN}[ PASS ]{c.RESET}"
            elif res.is_healthy:
                status_badge = f"{c.YELLOW}[ WARN ]{c.RESET}"
            else:
                status_badge = f"{c.RED}[ FAIL ]{c.RESET}"

            http_str = f"{res.status_code}" if res.status_code else "---"
            time_str = f"{res.response_time_ms:.0f}ms"

            # Combine diagnostics
            notes = []
            if res.errors:
                notes.extend(res.errors)
            if res.warnings:
                notes.extend(res.warnings)
            diag_str = ", ".join(notes) if notes else "OK"

            # Truncate label if long
            disp_label = (res.label[:22] + "..") if len(res.label) > 24 else res.label

            lines.append(f"{status_badge} {disp_label:<24} {http_str:<6} {time_str:<10} {diag_str}")

        lines.append("-" * 64)

        # Performance summary
        lines.append(
            f"{c.BOLD}Latency Profile:{c.RESET} "
            f"min: {c.CYAN}{summary.min_latency_ms}ms{c.RESET} | "
            f"avg: {c.CYAN}{summary.avg_latency_ms}ms{c.RESET} | "
            f"p95: {c.CYAN}{summary.p95_latency_ms}ms{c.RESET} | "
            f"max: {c.CYAN}{summary.max_latency_ms}ms{c.RESET}"
        )

        # Final verdict banner
        if summary.failed > 0:
            verdict = f"{c.BG_RED} FAILED {c.RESET} {c.RED}{summary.failed} endpoint(s) critical issues detected!{c.RESET}"
        elif summary.warnings_count > 0:
            verdict = f"{c.BG_YELLOW} HEALTHY WITH WARNINGS {c.RESET} All HTTP 200, but {summary.warnings_count} warning(s) flagged."
        else:
            verdict = f"{c.BG_GREEN} 100% HEALTHY {c.RESET} All endpoints passed perfectly with zero errors."

        lines.append("")
        lines.append(verdict)
        lines.append("")
        return "\n".join(lines)


class MarkdownFormatter:
    """Formats markdown reports suitable for GitHub Actions $GITHUB_STEP_SUMMARY or PR comments."""

    @staticmethod
    def format(summary: AuditSummary) -> str:
        lines = []
        status_icon = "✅" if summary.failed == 0 else "❌"
        lines.append(f"# {status_icon} Site Health Verifier Report")
        lines.append(f"**Target Host:** `{summary.target_url}`  ")
        lines.append(f"**Timestamp:** `{summary.timestamp}`  ")
        lines.append(f"**Overall Verdict:** `{summary.status_label}`  ")

        if summary.ssl_info:
            ssl = summary.ssl_info
            if ssl.valid:
                lines.append(f"🔒 **SSL Certificate:** Valid (`{ssl.days_left}` days remaining, Issuer: `{ssl.issuer}`)")
            else:
                lines.append(f"⚠️ **SSL Certificate:** Invalid (`{ssl.error}`)")

        lines.append("\n### 📊 Endpoint Health Breakdown")
        lines.append("| Status | Endpoint | Route | HTTP | Latency | Findings |")
        lines.append("| :--- | :--- | :--- | :--- | :--- | :--- |")

        for res in summary.results:
            icon = "✅" if res.is_healthy and not res.warnings else ("⚠️" if res.is_healthy else "❌")
            findings = []
            if res.errors:
                findings.extend([f"**ERROR:** {e}" for e in res.errors])
            if res.warnings:
                findings.extend([f"**WARN:** {w}" for w in res.warnings])
            findings_str = "<br>".join(findings) if findings else "Optimal"

            lines.append(
                f"| {icon} | **{res.label}** | `{res.url}` | `{res.status_code}` | `{res.response_time_ms:.0f}ms` | {findings_str} |"
            )

        lines.append("\n### ⚡ Performance Metrics")
        lines.append(
            f"- **Average Latency:** `{summary.avg_latency_ms}ms`\n"
            f"- **p95 Latency:** `{summary.p95_latency_ms}ms`\n"
            f"- **Min / Max Latency:** `{summary.min_latency_ms}ms` / `{summary.max_latency_ms}ms`\n"
            f"- **Endpoints Evaluated:** `{summary.total_endpoints}` (Passed: `{summary.passed}`, Failed: `{summary.failed}`)"
        )

        lines.append("\n---\n*Report generated by [Site Health Verifier](https://github.com/a-vip/site-health-verifier) — Zero-Dependency Pre/Post-Deployment Assurance.*")
        return "\n".join(lines)


class JSONFormatter:
    """Exports structured JSON for ingestion into automated loggers, webhooks, or telemetry."""

    @staticmethod
    def format(summary: AuditSummary, indent: int = 2) -> str:
        data: Dict[str, Any] = {
            "target_url": summary.target_url,
            "timestamp": summary.timestamp,
            "status": summary.status_label,
            "metrics": {
                "total_endpoints": summary.total_endpoints,
                "passed": summary.passed,
                "failed": summary.failed,
                "warnings": summary.warnings_count,
                "latency_min_ms": summary.min_latency_ms,
                "latency_max_ms": summary.max_latency_ms,
                "latency_avg_ms": summary.avg_latency_ms,
                "latency_p95_ms": summary.p95_latency_ms,
            },
            "ssl": {
                "valid": summary.ssl_info.valid if summary.ssl_info else None,
                "days_left": summary.ssl_info.days_left if summary.ssl_info else None,
                "issuer": summary.ssl_info.issuer if summary.ssl_info else None,
                "error": summary.ssl_info.error if summary.ssl_info else None,
            } if summary.ssl_info else None,
            "endpoints": [
                {
                    "url": r.url,
                    "label": r.label,
                    "is_healthy": r.is_healthy,
                    "status_code": r.status_code,
                    "response_time_ms": r.response_time_ms,
                    "errors": r.errors,
                    "warnings": r.warnings,
                    "security_headers": r.security_headers,
                    "seo_meta": r.seo_meta,
                }
                for r in summary.results
            ],
        }
        return json.dumps(data, indent=indent)
