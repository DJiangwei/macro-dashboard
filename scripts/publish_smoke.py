#!/usr/bin/env python3
"""Smoke-test the published (or local) dashboard for every registered scope.

    publish_smoke.py                       # live GitHub Pages site
    publish_smoke.py --version <commit>    # cache-busted live check after a publish
    publish_smoke.py --local               # the working tree, no network

Every page and artifact must contain all of its markers; the scope list comes
from config/scopes.yaml, so a new scope is covered without editing this file.
"""
from __future__ import annotations

import argparse
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from country_primer.scopes import all_scopes  # noqa: E402

DEFAULT_BASE = "https://djiangwei.github.io/macro-dashboard"
USER_AGENT = "country-primer-smoke/0.1 (+https://github.com/DJiangwei/macro-dashboard)"


def checks() -> list[tuple[str, list[str]]]:
    scopes = all_scopes()
    items: list[tuple[str, list[str]]] = [
        ("index.html", ["Macro Dashboard", "dashboard_archive_summary.json"]),
        ("output/index.html", ["Macro Dashboard", *[s.html_file for s in scopes]]),
        ("output/macro_workbench_summary.json", ["macro-workbench-v1"]),
        ("output/core_coverage_matrix.json", ["core-coverage-v1"]),
        ("output/source_health.json", ["source-health-v1"]),
        ("output/release_monitor.json", ['"items"']),
        ("output/cee_canonical_frame.json", ["cee-canonical-v2"]),
        ("output/chart_studio.html", ["Macro Chart Studio", "chart_studio_catalog.json"]),
        ("output/chart_studio_catalog.json", ['"countries"', '"series"']),
        ("output/my_dashboard.html", ["My Macro Dashboard"]),
        ("output/policy_tracker.html", ["Central Bank Policy"]),
    ]
    for scope in scopes:
        markers = [f"{scope.name_en} Dashboard", "Core 48"]
        if scope.is_data_first:
            markers.append("Official Data Gaps")
            items.append((f"output/{scope.canonical_file}", ["data-first-canonical-v2", '"series"']))
        items.append((f"output/{scope.html_file}", markers))
    return items


def _read(path: str, base: str | None, version: str | None) -> str:
    if base is None:
        return (ROOT / path).read_text(encoding="utf-8")
    url = f"{base.rstrip('/')}/{path}" + (f"?v={version}" if version else "")
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=60) as response:
        return response.read().decode("utf-8", errors="replace")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--base", default=DEFAULT_BASE)
    parser.add_argument("--version", help="cache-busting query value (e.g. the published commit)")
    parser.add_argument("--local", action="store_true", help="check the working tree instead of the site")
    args = parser.parse_args(argv)
    base = None if args.local else args.base

    failures = []
    items = checks()
    for path, markers in items:
        try:
            text = _read(path, base, args.version)
        except Exception as exc:
            failures.append(f"{path}: {exc}")
            continue
        missing = [m for m in markers if m not in text]
        if missing:
            failures.append(f"{path}: missing {missing}")
    where = "working tree" if base is None else base
    for failure in failures:
        print(f"FAIL {failure}")
    print(f"{len(items) - len(failures)}/{len(items)} smoke checks passed ({where})")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
