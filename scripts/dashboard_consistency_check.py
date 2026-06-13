#!/usr/bin/env python3
"""Check that generated dashboard headline data uses one canonical source.

This catches the easy-to-miss drift where archive cards are rebuilt from the
data pipeline while country-page headline KPI cards keep stale narrative HTML.
"""
from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
OUTPUT = ROOT / "output"

for path in (ROOT, SRC):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from build_v4 import _latest_numeric_value  # noqa: E402
from country_primer.data_fetcher import DataPipeline, INDICATOR_MANIFEST_48  # noqa: E402


CE4_COUNTRIES = {
    "HU": "hungary_2026Q2_v4.html",
    "PL": "poland_2026Q2_v4.html",
    "CZ": "czechia_2026Q2_v4.html",
    "RO": "romania_2026Q2_v4.html",
}

KPI_INDICATORS = {
    "real_gdp_yoy": True,
    "cpi_yoy": False,
    "fiscal_balance_pct_gdp": True,
    "current_account_pct_gdp": True,
    "policy_rate": False,
    "sov_yield_10y": False,
}


def _format_percent(value: float, *, signed: bool) -> str:
    sign = "+" if signed and value > 0 else ""
    return f"{sign}{value:,.2f}%"


def _load_archive_cards() -> dict[str, dict]:
    archive_path = OUTPUT / "dashboard_archive_summary.json"
    if not archive_path.exists():
        raise AssertionError(f"Missing {archive_path}")
    payload = json.loads(archive_path.read_text())
    cards = payload.get("cards") or []
    return {str(card.get("code")): card for card in cards}


def _assert_contains(path: Path, needle: str, *, context: str) -> None:
    text = path.read_text()
    if needle not in text:
        raise AssertionError(f"{path} is missing {needle!r} ({context})")


def main() -> int:
    specs = [
        spec
        for spec in INDICATOR_MANIFEST_48
        if spec.indicator_id in KPI_INDICATORS
    ]
    pipeline = DataPipeline()
    archive_cards = _load_archive_cards()
    root_index = ROOT / "index.html"
    output_index = OUTPUT / "index.html"
    errors: list[str] = []

    for country, filename in CE4_COUNTRIES.items():
        frame = pipeline.fetch_country(country, specs)
        page = OUTPUT / filename
        if not page.exists():
            errors.append(f"Missing country page: {page}")
            continue

        expected: dict[str, str] = {}
        for indicator_id, signed in KPI_INDICATORS.items():
            value = _latest_numeric_value(frame, country, indicator_id)
            if value is None:
                errors.append(f"{country} missing canonical {indicator_id}")
                continue
            expected[indicator_id] = _format_percent(value, signed=signed)

        card = archive_cards.get(country)
        if not card:
            errors.append(f"Archive JSON missing {country} card")
            continue

        policy_rate = expected.get("policy_rate")
        ten_year = expected.get("sov_yield_10y")
        if policy_rate and card.get("headline") != policy_rate:
            errors.append(
                f"{country} archive policy rate {card.get('headline')!r} != canonical {policy_rate!r}"
            )
        if ten_year and card.get("secondary") != ten_year:
            errors.append(
                f"{country} archive 10Y yield {card.get('secondary')!r} != canonical {ten_year!r}"
            )

        for indicator_id, value_text in expected.items():
            try:
                _assert_contains(page, value_text, context=f"{country} {indicator_id}")
            except AssertionError as exc:
                errors.append(str(exc))

        for index_path in (root_index, output_index):
            for label, value_text in (("policy_rate", policy_rate), ("sov_yield_10y", ten_year)):
                if not value_text:
                    continue
                try:
                    _assert_contains(index_path, value_text, context=f"{country} {label}")
                except AssertionError as exc:
                    errors.append(str(exc))

    if errors:
        print("Dashboard consistency check failed:")
        for error in errors:
            print(f"- {error}")
        return 1

    print("Dashboard consistency check passed for CE4 headline KPIs.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
