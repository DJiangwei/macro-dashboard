#!/usr/bin/env python3
"""Generate a country-indicator data-source catalog for future agents.

The output is intentionally verbose and human-readable. It records the latest
source selected by the pipeline for every rendered country/indicator slot, plus
the country-specific proxy slots that were intentionally dropped from the public
dashboard.
"""
from __future__ import annotations

import json
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path

import yaml

from country_primer.data_fetcher import (
    DROPPED_PROXY_INDICATORS_BY_COUNTRY,
    DataPipeline,
    INDICATOR_MANIFEST_48,
    is_dropped_proxy_indicator,
)


ROOT = Path(__file__).resolve().parents[1]
COUNTRIES = ("HU", "PL", "CZ", "RO")
COUNTRY_NAMES = {
    "HU": "Hungary",
    "PL": "Poland",
    "CZ": "Czechia",
    "RO": "Romania",
}
US_CONFIG_PATH = ROOT / "config" / "us_indicators.yaml"
US_SUMMARY_PATH = ROOT / "output" / "us_dashboard_summary.json"
CHINA_CONFIG_PATH = ROOT / "config" / "china_indicators.yaml"
CHINA_SUMMARY_PATH = ROOT / "output" / "china_dashboard_summary.json"
UK_CONFIG_PATH = ROOT / "config" / "uk_indicators.yaml"
UK_SUMMARY_PATH = ROOT / "output" / "uk_dashboard_summary.json"


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


def _us_config() -> dict:
    if not US_CONFIG_PATH.exists():
        return {}
    return yaml.safe_load(US_CONFIG_PATH.read_text()) or {}


def _us_summary() -> dict:
    if not US_SUMMARY_PATH.exists():
        return {}
    return json.loads(US_SUMMARY_PATH.read_text())


def _append_china_sources(lines: list[str]) -> None:
    if not CHINA_CONFIG_PATH.exists():
        return
    config = yaml.safe_load(CHINA_CONFIG_PATH.read_text()) or {}
    indicators = config.get("indicators", [])
    summary = json.loads(CHINA_SUMMARY_PATH.read_text()) if CHINA_SUMMARY_PATH.exists() else {}
    lines.extend([
        "",
        "## China Data-First Dashboard Sources",
        "",
        "The China page is generated from `config/china_indicators.yaml`. Current rendered charts deliberately use reproducible public endpoints: AKShare-wrapped Eastmoney/Sina/PBC-style tables for selected China-native high-frequency indicators, World Bank WDI for annual national-account and structural series, IMF DataMapper for WEO fiscal ratios, SAFE for RMB central parity, PBC latest-card pages for selected money-market snapshots, and FRED graph CSV mirrors for validated IMF IFS, BIS, OECD, and Federal Reserve series. China-native monthly NBS/PBOC history is not proxied when an official reusable endpoint has not been validated.",
        "",
        f"Configured charts: {len(indicators)}. Latest rendered chart count: {summary.get('charts', 'unknown')}. Source groups: {summary.get('source_groups', 'unknown')}.",
        "",
        "| Section | Indicator | Label | Frequency | Unit | Fetcher | Source | Series / field | Main pitfalls / notes |",
        "|---|---|---|---|---|---|---|---|---|",
    ])
    for item in indicators:
        label = item.get("label_en") or item.get("label_zh") or item.get("id")
        series_id = item.get("series") or item.get("metric") or ""
        lines.append(
            "| "
            + " | ".join([
                _clean(item.get("section")),
                f"`{_clean(item.get('id'))}`",
                _clean(label),
                _clean(item.get("frequency")),
                _clean(item.get("unit")),
                _clean(item.get("fetcher")),
                _clean(item.get("source_name")),
                _clean(series_id),
                _clean(item.get("caveat_en")),
            ])
            + " |"
        )

    cards = config.get("latest_cards", [])
    lines.extend([
        "",
        "### China Latest-Card Snapshots",
        "",
        "| Card | Label | Fetcher | Source page | Main note |",
        "|---|---|---|---|---|",
    ])
    for item in cards:
        lines.append(
            "| "
            + " | ".join([
                f"`{_clean(item.get('id'))}`",
                _clean(item.get("label_en") or item.get("label_zh")),
                _clean(item.get("fetcher")),
                _clean(item.get("url")),
                _clean(f"Expected title: {item.get('expected_title', '')}"),
            ])
            + " |"
        )

    gaps = config.get("data_gaps", [])
    lines.extend([
        "",
        "## China Official Data Gaps",
        "",
        "| Section | Indicator family | Current status |",
        "|---|---|---|",
    ])
    for item in gaps:
        lines.append(
            "| "
            + " | ".join([
                _clean(item.get("section")),
                _clean(item.get("item_en")),
                _clean(item.get("status_en")),
            ])
            + " |"
        )


def _append_uk_sources(lines: list[str]) -> None:
    if not UK_CONFIG_PATH.exists():
        return
    config = yaml.safe_load(UK_CONFIG_PATH.read_text()) or {}
    indicators = config.get("indicators", [])
    summary = json.loads(UK_SUMMARY_PATH.read_text()) if UK_SUMMARY_PATH.exists() else {}
    lines.extend([
        "",
        "## United Kingdom Data-First Dashboard Sources",
        "",
        "The UK page is generated from `config/uk_indicators.yaml`. Native ONS time-series JSON and Bank of England IADB CSV endpoints are preferred where validated; FRED/OECD/BIS/IMF mirror series remain for broader public-data coverage.",
        "",
        f"Configured charts: {len(indicators)}. Latest rendered chart count: {summary.get('charts', 'unknown')}. Source groups: {summary.get('source_groups', 'unknown')}.",
        "",
        "| Section | Indicator | Label | Frequency | Unit | Fetcher | Source | Series / field | Main pitfalls / notes |",
        "|---|---|---|---|---|---|---|---|---|",
    ])
    for item in indicators:
        label = item.get("label_en") or item.get("label_zh") or item.get("id")
        series_id = item.get("series") or item.get("metric") or item.get("value_column") or item.get("value_column_contains") or ""
        lines.append(
            "| "
            + " | ".join([
                _clean(item.get("section")),
                f"`{_clean(item.get('id'))}`",
                _clean(label),
                _clean(item.get("frequency")),
                _clean(item.get("unit")),
                _clean(item.get("fetcher")),
                _clean(item.get("source_name")),
                _clean(series_id),
                _clean(item.get("caveat_en")),
            ])
            + " |"
        )

    gaps = config.get("data_gaps", [])
    lines.extend([
        "",
        "## United Kingdom Official / Vendor Data Gaps",
        "",
        "| Section | Indicator family | Current status |",
        "|---|---|---|",
    ])
    for item in gaps:
        lines.append(
            "| "
            + " | ".join([
                _clean(item.get("section")),
                _clean(item.get("item_en")),
                _clean(item.get("status_en")),
            ])
            + " |"
        )


def _append_us_sources(lines: list[str]) -> None:
    config = _us_config()
    if not config:
        return
    indicators = config.get("indicators", [])
    summary = _us_summary()
    lines.extend([
        "",
        "## United States Data-First Dashboard Sources",
        "",
        "The US page is generated from `config/us_indicators.yaml`. This table records configured sources for each rendered chart slot; latest dates are tracked in `output/us_dashboard_summary.json` and the generated HTML rather than fetched again here.",
        "",
        f"Configured charts: {len(indicators)}. Latest rendered chart count: {summary.get('charts', 'unknown')}. Source groups: {summary.get('source_groups', 'unknown')}.",
        "",
        "| Section | Indicator | Label | Frequency | Unit | Fetcher | Source | Series / field | Main pitfalls / notes |",
        "|---|---|---|---|---|---|---|---|---|",
    ])
    for item in indicators:
        label = item.get("label_en") or item.get("label_zh") or item.get("id")
        series_id = item.get("series") or item.get("metric") or ""
        lines.append(
            "| "
            + " | ".join([
                _clean(item.get("section")),
                f"`{_clean(item.get('id'))}`",
                _clean(label),
                _clean(item.get("frequency")),
                _clean(item.get("unit")),
                _clean(item.get("fetcher")),
                _clean(item.get("source_name")),
                _clean(series_id),
                _clean(item.get("caveat_en")),
            ])
            + " |"
        )

    gaps = config.get("data_gaps", [])
    lines.extend([
        "",
        "## United States Official / Vendor Data Gaps",
        "",
        "| Section | Indicator family | Current status |",
        "|---|---|---|",
    ])
    for item in gaps:
        lines.append(
            "| "
            + " | ".join([
                _clean(item.get("section")),
                _clean(item.get("item_en")),
                _clean(item.get("status_en")),
            ])
            + " |"
        )


DATA_FIRST_PAGES = (
    {
        "name": "Japan",
        "config": ROOT / "config" / "japan_indicators.yaml",
        "summary": ROOT / "output" / "japan_dashboard_summary.json",
        "config_ref": "config/japan_indicators.yaml",
        "summary_ref": "output/japan_dashboard_summary.json",
        "note": (
            "The Japan page is generated from `config/japan_indicators.yaml`. FRED (official API when "
            "`FRED_API_KEY` is set) carries national accounts, production, labour, trade, rates, and BIS "
            "series. Because OECD discontinued its Japan CPI, retail-value, and money-stock mirrors between "
            "2021 and 2024, national CPI and bank soundness come from the IMF SDMX 2.1 API instead, and IMF "
            "WEO DataMapper carries fiscal ratios with an explicit forecast split. Japan-native releases "
            "behind the e-Stat application-ID wall are recorded as gaps rather than proxied."
        ),
    },
    {
        "name": "South Africa",
        "config": ROOT / "config" / "south_africa_indicators.yaml",
        "summary": ROOT / "output" / "south_africa_dashboard_summary.json",
        "config_ref": "config/south_africa_indicators.yaml",
        "summary_ref": "output/south_africa_dashboard_summary.json",
        "note": (
            "The South Africa page is generated from `config/south_africa_indicators.yaml`. The SARB Web "
            "Indicators JSON API is preferred wherever SARB is the compiling authority (policy and prime "
            "rates, SABOR/ZARONIA, benchmark bond yields, CPI, PPI, rand crosses, NEER). FRED carries the "
            "OECD/Stats SA/BIS mirrors for national accounts, production, labour, trade, and credit; IMF "
            "SDMX supplies the CPI cross-check and Financial Soundness Indicators; IMF WEO supplies fiscal "
            "ratios. Eskom supply data and vendor-controlled BER/PMI surveys remain explicit gaps."
        ),
    },
)


def _append_data_first_sources(lines: list[str], page: dict) -> None:
    if not page["config"].exists():
        return
    config = yaml.safe_load(page["config"].read_text()) or {}
    indicators = config.get("indicators", [])
    summary = json.loads(page["summary"].read_text()) if page["summary"].exists() else {}
    name = page["name"]
    lines.extend([
        "",
        f"## {name} Data-First Dashboard Sources",
        "",
        page["note"],
        "",
        f"Generated from `{page['config_ref']}`; latest dates are tracked in `{page['summary_ref']}` and the generated HTML rather than fetched again here.",
        "",
        f"Configured charts: {len(indicators)}. Latest rendered chart count: {summary.get('charts', 'unknown')}. Source groups: {summary.get('source_groups', 'unknown')}.",
        "",
        "| Section | Indicator | Label | Frequency | Unit | Fetcher | Source | Series / field | Main pitfalls / notes |",
        "|---|---|---|---|---|---|---|---|---|",
    ])
    for item in indicators:
        label = item.get("label_en") or item.get("label_zh") or item.get("id")
        lines.append(
            "| "
            + " | ".join([
                _clean(item.get("section")),
                f"`{_clean(item.get('id'))}`",
                _clean(label),
                _clean(item.get("frequency")),
                _clean(item.get("unit")),
                _clean(item.get("fetcher")),
                _clean(item.get("source_name")),
                _clean(item.get("series") or ""),
                _clean(item.get("caveat_en")),
            ])
            + " |"
        )

    lines.extend([
        "",
        f"## {name} Official / Vendor Data Gaps",
        "",
        "| Section | Indicator family | Current status |",
        "|---|---|---|",
    ])
    for item in config.get("data_gaps", []):
        lines.append(
            "| "
            + " | ".join([
                _clean(item.get("section")),
                _clean(item.get("item_en")),
                _clean(item.get("status_en")),
            ])
            + " |"
        )


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
        "- External harnesses and generic aggregator libraries are treated as source-discovery aids, not automatic authority. Do not install heavy optional dependencies or substitute proxy series unless the native endpoint, definition, frequency, and update behavior have been validated.",
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

    _append_china_sources(lines)
    for page in DATA_FIRST_PAGES:
        _append_data_first_sources(lines, page)
    _append_uk_sources(lines)
    _append_us_sources(lines)

    return "\n".join(lines) + "\n"


def main() -> None:
    output_path = Path("DATA_SOURCE_CATALOG.md")
    output_path.write_text(build_catalog())
    print(f"Wrote {output_path}")


if __name__ == "__main__":
    main()
