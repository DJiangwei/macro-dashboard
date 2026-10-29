#!/usr/bin/env python3
"""Generate a rich GitHub Actions Step Summary for Macro Dashboard CI/CD.

Usage:
  python scripts/ci_step_summary.py
  python scripts/ci_step_summary.py --output /path/to/summary.md
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "output"


def load_json(name: str) -> dict:
    p = OUTPUT_DIR / name
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {}


def build_markdown_summary() -> str:
    now_utc = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    core_cov = load_json("core_coverage_matrix.json")
    freshness = load_json("freshness_audit.json")
    health = load_json("source_health.json")
    what_changed = load_json("what_changed.json")
    archive = load_json("dashboard_archive_summary.json")

    cards = archive.get("cards", [])
    total_dashboards = len(cards) or 18
    total_charts = sum(c.get("charts", 0) for c in cards)

    # Calculate overall Core 48 coverage
    country_cov = core_cov.get("country_summary", {})
    total_concepts = core_cov.get("concept_count", 48)

    cov_percentages = []
    for c_code, c_info in country_cov.items():
        cov_count = sum(c_info.get(k, 0) for k in ("verified", "watch", "low_confidence", "substitute"))
        cov_percentages.append(cov_count / total_concepts if total_concepts else 0)
    avg_coverage_pct = (sum(cov_percentages) / len(cov_percentages) * 100) if cov_percentages else 0.0

    # Freshness summary
    fresh_list = freshness.get("summary", [])
    total_current = sum(f.get("current", 0) for f in fresh_list)
    total_indicators = sum(f.get("charts", 0) for f in fresh_list) or 1
    fresh_ratio = (total_current / total_indicators * 100)

    # Markdown blocks
    lines: list[str] = []
    lines.append("# 🌐 Macro Dashboard CI/CD Pipeline Summary")
    lines.append("")
    lines.append(f"> ⏱️ **Run Finished**: `{now_utc}` | **Target Environment**: GitHub Pages (`main` branch)")
    lines.append("")

    # KPI Banner Table
    lines.append("### 📊 Operational Overview")
    lines.append("")
    lines.append("| 🏛️ Monitored Economies | 📈 Total Chart Containers | 🎯 Core 48 Average Coverage | 🟢 Data Freshness Ratio |")
    lines.append("| :---: | :---: | :---: | :---: |")
    lines.append(f"| **{total_dashboards} Countries** | **{total_charts:,} Charts** | **{avg_coverage_pct:.1f}%** | **{fresh_ratio:.1f}% Active** |")
    lines.append("")

    # Country Breakdown Table
    lines.append("### 🗺️ Country Coverage & Quality Matrix")
    lines.append("")
    lines.append("| Code | Dashboard | Charts | Latest Historical | Headline KPI | Core 48 Coverage | Status |")
    lines.append("| :--- | :--- | :---: | :---: | :--- | :---: | :---: |")

    # Sort cards by name
    for c in sorted(cards, key=lambda x: x.get("name", "")):
        code = c.get("code", "")
        name = c.get("name", "")
        n_charts = c.get("charts", 0)
        headline = f"{c.get('headline_label', 'KPI')}: `{c.get('headline', 'n/a')}`"

        # Find latest date in freshness summary
        f_info = next((f for f in fresh_list if f.get("dashboard", "").lower() == name.lower()), {})
        latest_date = f_info.get("latest_historical_date", "n/a")

        # Find coverage
        cov_info = country_cov.get(code, {})
        cov_count = sum(cov_info.get(k, 0) for k in ("verified", "watch", "low_confidence", "substitute"))
        cov_str = f"{cov_count}/{total_concepts} ({(cov_count/total_concepts*100):.0f}%)" if total_concepts else "n/a"

        status_badge = "🟢 Verified" if c.get("status") == "clean" else "🟡 Monitored"
        lines.append(f"| **{code}** | [{name}](https://djiangwei.github.io/macro-dashboard/output/{c.get('file', '')}) | {n_charts} | `{latest_date}` | {headline} | {cov_str} | {status_badge} |")

    lines.append("")

    # Source Health & Circuit Breakers
    circuit_breaker = health.get("circuit_breaker", {})
    health_countries = health.get("countries", {})
    total_calls = sum(hc.get("calls", 0) for hc in health_countries.values())
    total_success = sum(hc.get("success", 0) for hc in health_countries.values())
    total_failed = sum(hc.get("failed", 0) for hc in health_countries.values())

    lines.append("### 🩺 Data Source Health & Resilience")
    lines.append("")
    success_rate = (total_success / total_calls * 100) if total_calls else 100.0
    lines.append(f"- **Total Source API Invocations**: `{total_calls:,}`")
    lines.append(f"- **Live Fetch Success Rate**: `{success_rate:.1f}%` (`{total_success}` succeeded, `{total_failed}` failed / gracefully fell back)")
    lines.append(f"- **Circuit Breaker Status**: `{'🟢 Normal (Closed)' if not circuit_breaker.get('tripped') else '🔴 Tripped'}`")
    lines.append("")

    # What Changed / Releases Section
    wc_items = what_changed.get("items", [])
    if wc_items:
        lines.append("### 🔔 What Changed in This Run")
        lines.append("")
        for item in wc_items[:10]:
            detail = item.get("detail", "")
            scope = item.get("scope", "General")
            change = item.get("change", "update")
            lines.append(f"- **[{scope.upper()}]** `{change}`: {detail}")
        lines.append("")

    lines.append("---")
    lines.append("*Dashboard is publicly deployed via [GitHub Pages](https://djiangwei.github.io/macro-dashboard/). All indicators are cross-checked and maintained under `make validate` quality contract.*")

    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Output GitHub Actions Step Summary for Macro Dashboard.")
    parser.add_argument("--output", help="Path to write the markdown summary file.")
    args = parser.parse_args()

    content = build_markdown_summary()

    out_path = args.output or os.environ.get("GITHUB_STEP_SUMMARY")
    if out_path:
        Path(out_path).write_text(content, encoding="utf-8")
        print(f"Wrote Step Summary to {out_path}")
    else:
        print(content)
    return 0


if __name__ == "__main__":
    sys.exit(main())
