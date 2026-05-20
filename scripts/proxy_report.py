#!/usr/bin/env python3
"""Print a proxy-coverage report for the v4 macro dashboard.

The report is intentionally small and dependency-light so any coding agent can
run it before and after adding data adapters.
"""
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from typing import Any

from country_primer.data_fetcher import DataPipeline


DEFAULT_COUNTRIES = ("HU", "PL", "CZ", "RO")


def build_report(countries: list[str]) -> dict[str, Any]:
    pipeline = DataPipeline()
    report: dict[str, Any] = {
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
    report = build_report(countries)
    if args.format == "json":
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print_text(report, details=args.details)


if __name__ == "__main__":
    main()
