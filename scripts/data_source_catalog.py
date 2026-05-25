#!/usr/bin/env python3
"""Generate a country-indicator data-source catalog for future agents.

The output is intentionally verbose and human-readable. It records the latest
source selected by the pipeline for every rendered country/indicator slot, plus
the country-specific proxy slots that were intentionally dropped from the public
dashboard.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path

from country_primer.data_fetcher import (
    DROPPED_PROXY_INDICATORS_BY_COUNTRY,
    DataPipeline,
    INDICATOR_MANIFEST_48,
    is_dropped_proxy_indicator,
)


COUNTRIES = ("HU", "PL", "CZ", "RO")
COUNTRY_NAMES = {
    "HU": "Hungary",
    "PL": "Poland",
    "CZ": "Czechia",
    "RO": "Romania",
}


def _clean(value: object) -> str:
    text = str(value or "").replace("\n", " ").replace("|", "\\|")
    return " ".join(text.split())


def _latest_rows(frame: list[dict]) -> dict[str, dict]:
    latest: dict[str, dict] = {}
    for row in frame:
        indicator_id = str(row.get("indicator_id", ""))
        if not indicator_id:
            continue
        if indicator_id not in latest or str(row.get("date", "")) > str(latest[indicator_id].get("date", "")):
            latest[indicator_id] = row
    return latest


def build_catalog() -> str:
    pipeline = DataPipeline()
    specs = {spec.indicator_id: spec for spec in INDICATOR_MANIFEST_48}
    frames = {country: pipeline.fetch_country(country) for country in COUNTRIES}
    latest_by_country = {country: _latest_rows(frame) for country, frame in frames.items()}
    dropped_total = sum(len(items) for items in DROPPED_PROXY_INDICATORS_BY_COUNTRY.values())
    proxy_total = sum(
        1
        for latest in latest_by_country.values()
        for row in latest.values()
        if row.get("is_proxy")
    )

    lines: list[str] = [
        "# Data Source Catalog",
        "",
        f"Generated: {datetime.now(UTC).strftime('%Y-%m-%d')}",
        "",
        "Purpose: help future models and developers understand exactly which source is used for each rendered dashboard series, how often it updates, and where the main definition or quality traps are.",
        "",
        "## Operating Rules",
        "",
        "- Prefer official statistical agencies, central banks, exchanges, and multilateral datasets before vendor or manually curated sources.",
        "- Derived series must be described in the source note, including denominator, transformation, or spread convention.",
        "- Country-indicator slots that would still rely on transparent proxy data are intentionally dropped from the public pages rather than rendered as low-confidence placeholders.",
        "- `watch` does not mean unusable; it means the series is lagged, manually curated, snapshot-based, derived, definition-sensitive, or should be cross-checked before trading use.",
        "- Re-run `make build-v4`, `make validate`, and `make proxy-report` after changing adapters or this catalog.",
        "",
        "## Current Coverage Summary",
        "",
        "| Country | Rendered indicators | Dropped proxy slots | Remaining rendered proxies |",
        "|---|---:|---:|---:|",
    ]
    for country in COUNTRIES:
        rendered = len(latest_by_country[country])
        dropped = len(DROPPED_PROXY_INDICATORS_BY_COUNTRY.get(country, frozenset()))
        proxies = sum(1 for row in latest_by_country[country].values() if row.get("is_proxy"))
        lines.append(f"| {COUNTRY_NAMES[country]} | {rendered} | {dropped} | {proxies} |")

    lines.extend([
        "",
        f"Total intentionally dropped country-indicator slots: {dropped_total}.",
        f"Remaining rendered proxy slots: {proxy_total}.",
        "",
        "## Intentionally Dropped Proxy Slots",
        "",
        "| Country | Indicator | Dashboard label | Reason |",
        "|---|---|---|---|",
    ])
    for country in COUNTRIES:
        for indicator_id in sorted(DROPPED_PROXY_INDICATORS_BY_COUNTRY.get(country, frozenset())):
            spec = specs[indicator_id]
            lines.append(
                f"| {COUNTRY_NAMES[country]} | `{indicator_id}` | {_clean(spec.label)} | Public-source adapter still falls back to transparent proxy data; dropped from rendered page until a reusable source exists. |"
            )

    lines.extend([
        "",
        "## Rendered Data Sources By Country",
        "",
    ])

    for country in COUNTRIES:
        lines.extend([
            f"### {COUNTRY_NAMES[country]}",
            "",
            "| Section | Indicator | Label | Frequency | Unit | Latest date | Source | Series ID | Quality | Main pitfalls / notes |",
            "|---|---|---|---|---|---|---|---|---|---|",
        ])
        latest = latest_by_country[country]
        for spec in INDICATOR_MANIFEST_48:
            if is_dropped_proxy_indicator(country, spec.indicator_id):
                continue
            row = latest.get(spec.indicator_id)
            if not row:
                lines.append(
                    f"| {_clean(spec.section_id)} | `{spec.indicator_id}` | {_clean(spec.label)} | {_clean(spec.frequency)} | {_clean(spec.unit)} | missing | missing | missing | missing | Missing after dropped-slot filtering; investigate adapter coverage. |"
                )
                continue
            lines.append(
                "| "
                + " | ".join([
                    _clean(spec.section_id),
                    f"`{spec.indicator_id}`",
                    _clean(row.get("label") or spec.label),
                    _clean(spec.frequency),
                    _clean(row.get("unit") or spec.unit),
                    _clean(row.get("date")),
                    _clean(row.get("source")),
                    _clean(row.get("series_id")),
                    _clean(row.get("quality_status")),
                    _clean(row.get("quality_note")),
                ])
                + " |"
            )
        lines.append("")

    source_groups: dict[str, set[str]] = defaultdict(set)
    for country, latest in latest_by_country.items():
        for indicator_id, row in latest.items():
            source_groups[str(row.get("source") or "Unknown")].add(f"{country}:{indicator_id}")

    lines.extend([
        "## Source Families",
        "",
        "| Source | Country-indicator slots | Notes |",
        "|---|---:|---|",
    ])
    for source, slots in sorted(source_groups.items(), key=lambda item: (-len(item[1]), item[0])):
        sample = ", ".join(sorted(slots)[:12])
        suffix = "..." if len(slots) > 12 else ""
        lines.append(f"| {_clean(source)} | {len(slots)} | {_clean(sample + suffix)} |")

    return "\n".join(lines) + "\n"


def main() -> None:
    output_path = Path("DATA_SOURCE_CATALOG.md")
    output_path.write_text(build_catalog())
    print(f"Wrote {output_path}")


if __name__ == "__main__":
    main()
