#!/usr/bin/env python3
"""Print a proxy-coverage report for the v4 macro dashboard.

The report is intentionally small and dependency-light so any coding agent can
run it before and after adding data adapters.

By default the report reads generated archive/catalog artifacts instead of
refetching live data. Use `--mode live` when you explicitly want to exercise the
full data pipeline.
"""
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

from country_primer.data_fetcher import DataPipeline


DEFAULT_COUNTRIES = ("HU", "PL", "CZ", "RO")
ROOT = Path(__file__).resolve().parents[1]
ARCHIVE_JSON = ROOT / "output" / "dashboard_archive_summary.json"
SOURCE_CATALOG = ROOT / "DATA_SOURCE_CATALOG.md"
COUNTRY_NAMES = {
    "HU": "Hungary",
    "PL": "Poland",
    "CZ": "Czechia",
    "RO": "Romania",
}
COUNTRY_CODES = {name: code for code, name in COUNTRY_NAMES.items()}


def _split_markdown_row(row: str) -> list[str]:
    row = row.strip()
    if row.startswith("|"):
        row = row[1:]
    if row.endswith("|"):
        row = row[:-1]
    return [part.strip().replace("\\|", "|") for part in row.split("|")]


def _catalog_proxy_details() -> dict[str, list[str]]:
    """Return rendered transparent proxy indicators by country from catalog."""
    details: dict[str, list[str]] = defaultdict(list)
    if not SOURCE_CATALOG.exists():
        return details

    current_code = ""
    in_table = False
    for line in SOURCE_CATALOG.read_text().splitlines():
        if line.startswith("### "):
            current_code = COUNTRY_CODES.get(line.replace("### ", "", 1).strip(), "")
            in_table = False
            continue
        if not current_code:
            continue
        if line.startswith("| Section | Indicator | Label | Frequency |"):
            in_table = True
            continue
        if in_table and (not line.strip() or line.startswith("## ")):
            in_table = False
            continue
        if not in_table or not line.startswith("|") or line.startswith("|---"):
            continue
        parts = _split_markdown_row(line)
        if len(parts) < 10:
            continue
        indicator_id = parts[1].strip("`")
        source = parts[6]
        series_id = parts[7]
        note = parts[9]
        haystack = " ".join([source, series_id, note]).lower()
        if "transparent proxy fill" in haystack or series_id.startswith("proxy:"):
            details[current_code].append(indicator_id)

    return {country: sorted(set(indicators)) for country, indicators in details.items()}


def build_report_from_outputs(countries: list[str]) -> dict[str, Any]:
    if not ARCHIVE_JSON.exists():
        raise FileNotFoundError(
            f"{ARCHIVE_JSON} does not exist. Run `make build-v4` first or use `--mode live`."
        )
    archive = json.loads(ARCHIVE_JSON.read_text())
    archive_cards = {
        str(card.get("code", "")).upper(): card
        for card in archive.get("cards", [])
        if str(card.get("code", "")).upper() in COUNTRY_NAMES
    }
    details = _catalog_proxy_details()
    report: dict[str, Any] = {
        "mode": "offline",
        "source": str(ARCHIVE_JSON.relative_to(ROOT)),
        "countries": {},
        "proxy_union": [],
        "proxy_counts": {},
    }
    proxy_union: set[str] = set()
    by_indicator: dict[str, list[str]] = defaultdict(list)

    for country in countries:
        card = archive_cards.get(country, {})
        proxies = sorted(details.get(country, []))
        proxy_count = int(card.get("proxy_fills") or len(proxies))
        if proxy_count and not proxies:
            proxies = [f"unknown_proxy_slot_{index + 1}" for index in range(proxy_count)]
        proxy_union.update(proxies)
        for indicator_id in proxies:
            by_indicator[indicator_id].append(country)
        total = int(card.get("charts") or 0)
        report["countries"][country] = {
            "proxy_count": proxy_count,
            "proxy_indicators": proxies,
            "total_indicators": total,
        }
        report["proxy_counts"][country] = proxy_count

    report["proxy_union"] = sorted(proxy_union)
    report["by_indicator"] = {
        indicator_id: country_list
        for indicator_id, country_list in sorted(by_indicator.items())
    }
    return report


def build_report_live(countries: list[str]) -> dict[str, Any]:
    pipeline = DataPipeline()
    report: dict[str, Any] = {
        "mode": "live",
        "countries": {},
        "proxy_union": [],
        "proxy_counts": {},
    }
    proxy_union: set[str] = set()
    by_indicator: dict[str, list[str]] = defaultdict(list)

    for country in countries:
        frame = pipeline.fetch_country(country)
        proxies = sorted({row["indicator_id"] for row in frame if row.get("is_proxy")})
        proxy_union.update(proxies)
        for indicator_id in proxies:
            by_indicator[indicator_id].append(country)
        report["countries"][country] = {
            "proxy_count": len(proxies),
            "proxy_indicators": proxies,
            "total_indicators": len({row["indicator_id"] for row in frame}),
        }
        report["proxy_counts"][country] = len(proxies)

    report["proxy_union"] = sorted(proxy_union)
    report["by_indicator"] = {
        indicator_id: countries
        for indicator_id, countries in sorted(by_indicator.items())
    }
    return report


def print_text(report: dict[str, Any], *, details: bool) -> None:
    print("Proxy coverage report")
    print("=" * 21)
    if report.get("mode"):
        print(f"Mode: {report['mode']}")
    if report.get("source"):
        print(f"Source: {report['source']}")
    print()
    print("Country  Proxy  Total  Share")
    print("-------  -----  -----  -----")
    for country, payload in report["countries"].items():
        proxy_count = payload["proxy_count"]
        total = payload["total_indicators"]
        share = proxy_count / total if total else 0
        print(f"{country:<7}  {proxy_count:>5}  {total:>5}  {share:>5.1%}")

    print()
    print(f"Proxy union: {len(report['proxy_union'])} indicators")

    if details:
        print()
        print("By country")
        print("----------")
        for country, payload in report["countries"].items():
            print(f"{country}: {', '.join(payload['proxy_indicators'])}")

        print()
        print("By indicator")
        print("------------")
        for indicator_id, countries in report["by_indicator"].items():
            print(f"{indicator_id}: {', '.join(countries)}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Report transparent proxy coverage by country.")
    parser.add_argument(
        "--countries",
        default=",".join(DEFAULT_COUNTRIES),
        help="Comma-separated ISO2 country list. Defaults to HU,PL,CZ,RO.",
    )
    parser.add_argument(
        "--mode",
        choices=("offline", "live"),
        default="offline",
        help="offline reads generated archive/catalog artifacts; live refetches the CE4 pipeline.",
    )
    parser.add_argument(
        "--format",
        choices=("text", "json"),
        default="text",
        help="Output format.",
    )
    parser.add_argument(
        "--details",
        action="store_true",
        help="Include proxy lists by country and by indicator.",
    )
    args = parser.parse_args()

    countries = [item.strip().upper() for item in args.countries.split(",") if item.strip()]
    if args.mode == "live":
        report = build_report_live(countries)
    else:
        report = build_report_from_outputs(countries)
    if args.format == "json":
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print_text(report, details=args.details)


if __name__ == "__main__":
    main()
