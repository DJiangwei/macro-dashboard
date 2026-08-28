#!/usr/bin/env python3
"""Audit rendered dashboard chart freshness after a live rebuild.

The dashboard can render successfully while still carrying naturally lagged or
stale source data. This script checks the latest observation dates shown on the
generated pages and the CE-4 data catalog against simple frequency-aware
cadence rules, then writes a human-readable audit plus machine-readable JSON.
"""
from __future__ import annotations

import json
import re
from calendar import monthrange
from dataclasses import asdict, dataclass
from datetime import UTC, date, datetime
from html import unescape
from pathlib import Path

from country_primer.data_quality import assess_series_quality


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "output"
AUDIT_MD = ROOT / "DATA_FRESHNESS_AUDIT.md"
AUDIT_JSON = OUTPUT / "freshness_audit.json"
CATALOG = ROOT / "DATA_SOURCE_CATALOG.md"
TODAY = datetime.now(UTC).date()

DATA_FIRST_PAGES = {
    "China": OUTPUT / "china.html",
    "Japan": OUTPUT / "japan.html",
    "South Africa": OUTPUT / "south_africa.html",
    "United Kingdom": OUTPUT / "uk.html",
    "United States": OUTPUT / "us.html",
}

CE4_COUNTRIES = ("Hungary", "Poland", "Czechia", "Romania")

THRESHOLD_DAYS = {
    "daily": 14,
    "business daily": 14,
    "weekly": 45,
    "monthly": 150,
    "quarterly": 330,
}


@dataclass(frozen=True)
class ChartFreshness:
    dashboard: str
    indicator_id: str
    label: str
    frequency: str
    latest_observation: str
    latest_date: str
    age_basis_date: str
    age_days: int | None
    threshold_days: int | None
    release_calendar_id: str
    expected_release_date: str
    due_date: str
    freshness_status: str
    quality_status: str
    source: str
    series_id: str
    provider_update: str
    note: str


def _clean(value: object) -> str:
    text = re.sub(r"<[^>]+>", "", str(value or ""))
    text = unescape(text).replace("\xa0", " ")
    return " ".join(text.split())


def _parse_date(value: str) -> date | None:
    value = _clean(value)
    if not value or value.lower() in {"missing", "n/a", "nan"}:
        return None
    value = value.split("·", 1)[0].strip()
    iso_match = re.search(r"(\d{4})-(\d{2})-(\d{2})", value)
    if iso_match:
        try:
            return date(int(iso_match.group(1)), int(iso_match.group(2)), int(iso_match.group(3)))
        except ValueError:
            return None
    year_month_match = re.search(r"(\d{4})-(\d{2})$", value)
    if year_month_match:
        try:
            return date(int(year_month_match.group(1)), int(year_month_match.group(2)), 1)
        except ValueError:
            return None
    quarter_match = re.search(r"(\d{4})\s*Q([1-4])", value, flags=re.I)
    if quarter_match:
        year = int(quarter_match.group(1))
        month = int(quarter_match.group(2)) * 3
        day = 31 if month in {3, 12} else 30
        return date(year, month, day)
    year_match = re.fullmatch(r"\d{4}", value)
    if year_match:
        return date(int(value), 12, 31)
    return None


def _threshold_for_frequency(frequency: str) -> int | None:
    normalized = str(frequency or "").lower().strip()
    if normalized in THRESHOLD_DAYS:
        return THRESHOLD_DAYS[normalized]
    if "daily" in normalized:
        return THRESHOLD_DAYS["daily"]
    if "week" in normalized:
        return THRESHOLD_DAYS["weekly"]
    if "month" in normalized:
        return THRESHOLD_DAYS["monthly"]
    if "quarter" in normalized:
        return THRESHOLD_DAYS["quarterly"]
    if "annual" in normalized or "year" in normalized:
        return None
    return None


def _period_end_for_age(latest: date, frequency: str) -> date:
    normalized = str(frequency or "").lower().strip()
    if "quarter" in normalized and latest.day == 1 and latest.month in {1, 4, 7, 10}:
        month = latest.month + 2
        return date(latest.year, month, monthrange(latest.year, month)[1])
    if "month" in normalized and latest.day == 1:
        return date(latest.year, latest.month, monthrange(latest.year, latest.month)[1])
    return latest


def _classify(latest: date | None, frequency: str, quality_status: str) -> tuple[str, date | None, int | None, int | None]:
    if latest is None:
        return "missing_date", None, None, _threshold_for_frequency(frequency)

    normalized = str(frequency or "").lower().strip()
    if "annual" in normalized or "year" in normalized:
        if latest.year > TODAY.year:
            return "projection", latest, (TODAY - latest).days, None
        age_basis = latest if latest <= TODAY else TODAY
        if latest.year < TODAY.year - 2:
            return "lagged_source", age_basis, (TODAY - age_basis).days, None
        return "current", age_basis, (TODAY - age_basis).days, None

    if latest > TODAY:
        return "future_date", latest, (TODAY - latest).days, _threshold_for_frequency(frequency)
    age_basis = min(_period_end_for_age(latest, frequency), TODAY)
    age_days = (TODAY - age_basis).days
    threshold = _threshold_for_frequency(frequency)
    if threshold is not None and age_days > threshold:
        return "stale", age_basis, age_days, threshold
    if quality_status == "low_confidence":
        return "needs_review", age_basis, age_days, threshold
    return "current", age_basis, age_days, threshold


def _split_markdown_row(row: str) -> list[str]:
    row = row.strip()
    if row.startswith("|"):
        row = row[1:]
    if row.endswith("|"):
        row = row[:-1]

    parts: list[str] = []
    current: list[str] = []
    escaped = False
    for char in row:
        if char == "\\" and not escaped:
            escaped = True
            current.append(char)
            continue
        if char == "|" and not escaped:
            parts.append("".join(current).strip().replace("\\|", "|"))
            current = []
            continue
        current.append(char)
        escaped = False
    parts.append("".join(current).strip().replace("\\|", "|"))
    return parts


def _record(
    *,
    dashboard: str,
    indicator_id: str,
    label: str,
    frequency: str,
    latest_observation: str,
    quality_status: str,
    source: str,
    series_id: str = "",
    provider_update: str = "",
    note: str = "",
) -> ChartFreshness:
    latest = _parse_date(latest_observation)
    freshness_status, age_basis, age_days, threshold_days = _classify(latest, frequency, quality_status)
    shared_quality: dict = {}
    if latest:
        shared_quality = assess_series_quality(
            {
                "id": indicator_id,
                "frequency": frequency,
                "source_name": source,
                "quality_notes": [note] if note else [],
                "observations": [{"date": latest.isoformat(), "value": 0.0}],
            },
            today=TODAY,
        )
        if freshness_status != "projection":
            freshness_status = shared_quality["freshness"]
            if freshness_status == "current" and quality_status == "low_confidence":
                freshness_status = "needs_review"
        age_days = shared_quality.get("age_days")
        threshold_days = shared_quality.get("max_age_days")
        age_basis = min(_period_end_for_age(latest, frequency), TODAY) if latest <= TODAY else latest
    scheduled_haystack = " ".join([indicator_id, source, note]).lower()
    if freshness_status == "future_date" and (
        indicator_id in {"reserve_balance_rate", "fed_upper_target", "fed_lower_target"}
        or "administered rate" in scheduled_haystack
    ):
        freshness_status = "scheduled_policy"
    return ChartFreshness(
        dashboard=dashboard,
        indicator_id=indicator_id,
        label=label,
        frequency=frequency,
        latest_observation=_clean(latest_observation),
        latest_date=latest.isoformat() if latest else "",
        age_basis_date=age_basis.isoformat() if age_basis else "",
        age_days=age_days,
        threshold_days=threshold_days,
        release_calendar_id=str(shared_quality.get("release_calendar_id") or ""),
        expected_release_date=str(shared_quality.get("expected_release_date") or ""),
        due_date=str(shared_quality.get("due_date") or ""),
        freshness_status=freshness_status,
        quality_status=_clean(quality_status),
        source=_clean(source),
        series_id=_clean(series_id).strip("`"),
        provider_update=_clean(provider_update),
        note=_clean(note),
    )


def _parse_data_first_page(dashboard: str, path: Path) -> list[ChartFreshness]:
    if not path.exists():
        return []
    html = path.read_text()
    # The chart card carries data-dashboard-view / data-concept-id attributes
    # after the quality class, so the class match must not be anchored to '">'.
    article_re = re.compile(
        r'<article class="chart-card chart-quality-([^" ]+)"[^>]*>(.*?)</article>',
        flags=re.S,
    )
    records: list[ChartFreshness] = []
    for quality, body in article_re.findall(html):
        chart_match = re.search(r'id="chart-([^"]+)" class="plotly-chart"', body)
        label_match = re.search(r"<h3>.*?<span data-lang=\"en\">(.*?)</span>", body, flags=re.S)
        latest_match = re.search(r'data-latest-date="([^"]+)"', body)
        source_match = re.search(r"Source:\s*<a [^>]+>(.*?)</a>", body, flags=re.S)
        series_match = re.search(r"<span>Series:\s*(.*?)</span>", body, flags=re.S)
        frequency_match = re.search(r"<span>Frequency:\s*(.*?)</span>", body, flags=re.S)
        provider_match = re.search(r"<span>Provider update:\s*(.*?)</span>", body, flags=re.S)
        caveat_match = re.search(r'<p class="caveat">.*?<span data-lang="en">(.*?)</span>', body, flags=re.S)
        indicator_id = _clean(chart_match.group(1)) if chart_match else ""
        records.append(
            _record(
                dashboard=dashboard,
                indicator_id=indicator_id,
                label=_clean(label_match.group(1) if label_match else indicator_id),
                frequency=_clean(frequency_match.group(1) if frequency_match else ""),
                latest_observation=_clean(latest_match.group(1) if latest_match else ""),
                quality_status=_clean(quality),
                source=_clean(source_match.group(1) if source_match else ""),
                series_id=_clean(series_match.group(1) if series_match else ""),
                provider_update=_clean(provider_match.group(1) if provider_match else ""),
                note=_clean(caveat_match.group(1) if caveat_match else ""),
            )
        )
    return records


def _parse_ce4_catalog() -> list[ChartFreshness]:
    if not CATALOG.exists():
        return []
    lines = CATALOG.read_text().splitlines()
    records: list[ChartFreshness] = []
    current_country = ""
    in_country_table = False

    for line in lines:
        if line.startswith("### "):
            title = line.replace("### ", "", 1).strip()
            current_country = title if title in CE4_COUNTRIES else ""
            in_country_table = False
            continue
        if not current_country:
            continue
        if line.startswith("| Section | Indicator | Label | Frequency | Unit | Latest date |"):
            in_country_table = True
            continue
        if in_country_table and (not line.strip() or line.startswith("## ")):
            in_country_table = False
            continue
        if not in_country_table or not line.startswith("|") or line.startswith("|---"):
            continue
        parts = _split_markdown_row(line)
        if len(parts) < 10:
            continue
        _, indicator_id, label, frequency, _, latest, source, series_id, quality, note = parts[:10]
        records.append(
            _record(
                dashboard=current_country,
                indicator_id=indicator_id.strip("`"),
                label=label,
                frequency=frequency,
                latest_observation=latest,
                quality_status=quality,
                source=source,
                series_id=series_id,
                note=note,
            )
        )
    return records


def _load_summary(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text())


def _summaries(records: list[ChartFreshness]) -> list[dict[str, object]]:
    by_dashboard: dict[str, list[ChartFreshness]] = {}
    for record in records:
        by_dashboard.setdefault(record.dashboard, []).append(record)

    headline_latest = {
        "China": _load_summary(OUTPUT / "china_dashboard_summary.json").get("usd_cny_latest", ""),
        "United Kingdom": _load_summary(OUTPUT / "uk_dashboard_summary.json").get("bank_rate_latest", ""),
        "United States": _load_summary(OUTPUT / "us_dashboard_summary.json").get("fed_funds_latest", ""),
    }

    rows: list[dict[str, object]] = []
    for dashboard, items in sorted(by_dashboard.items()):
        rows.append({
            "dashboard": dashboard,
            "charts": len(items),
            "current": sum(1 for item in items if item.freshness_status == "current"),
            "stale": sum(1 for item in items if item.freshness_status == "stale"),
            "lagged_source": sum(1 for item in items if item.freshness_status == "lagged_source"),
            "projection": sum(1 for item in items if item.freshness_status == "projection"),
            "scheduled_policy": sum(1 for item in items if item.freshness_status == "scheduled_policy"),
            "future_date": sum(1 for item in items if item.freshness_status == "future_date"),
            "missing_date": sum(1 for item in items if item.freshness_status == "missing_date"),
            "needs_review": sum(1 for item in items if item.freshness_status == "needs_review"),
            "low_confidence": sum(1 for item in items if item.quality_status == "low_confidence"),
            "latest_historical_date": max(
                [
                    item.age_basis_date or item.latest_date
                    for item in items
                    if item.latest_date and item.freshness_status not in {"projection", "future_date", "scheduled_policy"}
                ],
                default="",
            ),
            "headline_latest": headline_latest.get(dashboard, ""),
        })
    return rows


def _md_table(headers: list[str], rows: list[list[object]]) -> list[str]:
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    for row in rows:
        lines.append("| " + " | ".join(_clean(item) for item in row) + " |")
    return lines


def _write_outputs(records: list[ChartFreshness]) -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    summaries = _summaries(records)
    attention = [
        item
        for item in records
        if item.freshness_status in {"stale", "lagged_source", "missing_date", "future_date", "needs_review"}
    ]
    attention.sort(key=lambda item: (item.age_days is None, -(item.age_days or 0), item.dashboard, item.indicator_id))

    payload = {
        "generated": datetime.now(UTC).isoformat(),
        "as_of_date": TODAY.isoformat(),
        "thresholds": {
            "daily": "14 days",
            "weekly": "45 days",
            "monthly": "150 days",
            "quarterly": "330 days",
            "annual": f"current if latest year >= {TODAY.year - 2}",
        },
        "summary": summaries,
        "records": [asdict(item) for item in records],
        "attention": [asdict(item) for item in attention],
    }
    AUDIT_JSON.write_text(json.dumps(payload, indent=2, ensure_ascii=False))

    lines = [
        "# Data Freshness Audit",
        "",
        f"Generated: {datetime.now(UTC).strftime('%Y-%m-%d %H:%M:%S UTC')}",
        f"As-of date: {TODAY.isoformat()}",
        "",
        "This audit checks the latest observation dates rendered on the data-first China, UK, and US pages, plus the CEE-4 source catalog generated by the pipeline. It is meant to be run after `make build-v4 data-catalog`.",
        "",
        "Freshness rules are deliberately cadence-based rather than release-calendar-perfect: daily data should be within 14 days, weekly within 45 days, monthly within 150 days, quarterly within 330 days, and annual data is considered current if the latest year is within the last two calendar years.",
        "",
        "## Dashboard Summary",
        "",
    ]
    lines.extend(
        _md_table(
            [
                "Dashboard",
                "Charts",
                "Current",
                "Stale",
                "Lagged source",
                "Projection",
                "Scheduled",
                "Future date",
                "Missing date",
                "Low confidence",
                "Latest historical date",
                "Headline latest",
            ],
            [
                [
                    row["dashboard"],
                    row["charts"],
                    row["current"],
                    row["stale"],
                    row["lagged_source"],
                    row["projection"],
                    row["scheduled_policy"],
                    row["future_date"],
                    row["missing_date"],
                    row["low_confidence"],
                    row["latest_historical_date"],
                    row["headline_latest"],
                ]
                for row in summaries
            ],
        )
    )
    lines.extend([
        "",
        "## Attention List",
        "",
        "Items below are not necessarily wrong: many are structural annual datasets, FRED/OECD mirrors, or official sources that publish with long lags. They are the places to check first when improving data coverage.",
        "",
    ])
    if attention:
        lines.extend(
            _md_table(
                ["Dashboard", "Indicator", "Latest", "Frequency", "Age days", "Status", "Source", "Note"],
                [
                    [
                        item.dashboard,
                        f"`{item.indicator_id}` {item.label}",
                        item.latest_observation,
                        item.frequency,
                        item.age_days if item.age_days is not None else "",
                        item.freshness_status,
                        item.source,
                        item.note,
                    ]
                    for item in attention[:120]
                ],
            )
        )
        if len(attention) > 120:
            lines.extend([
                "",
                f"Only the first 120 attention items are shown here; see `output/freshness_audit.json` for all {len(attention)} flagged records.",
            ])
    else:
        lines.append("No stale, lagged, missing-date, or low-confidence rendered chart records were detected.")

    projection_items = [item for item in records if item.freshness_status in {"projection", "scheduled_policy"}]
    lines.extend([
        "",
        "## Projection / Scheduled Charts",
        "",
        "These charts intentionally render forecast horizons, current-year annual markers, or scheduled policy-effective dates. They should not be read as stale historical observations.",
        "",
    ])
    if projection_items:
        lines.extend(
            _md_table(
                ["Dashboard", "Indicator", "Latest", "Status", "Source", "Note"],
                [
                    [
                        item.dashboard,
                        f"`{item.indicator_id}` {item.label}",
                        item.latest_observation,
                        item.freshness_status,
                        item.source,
                        item.note,
                    ]
                    for item in projection_items
                ],
            )
        )
    else:
        lines.append("No projection charts detected.")

    lines.extend([
        "",
        "## Maintenance Notes",
        "",
        "- A clean rebuild can change only timestamps if source values have not revised; that is still useful because it proves the adapters are alive.",
        "- `stale` usually means a high-frequency chart is beyond its expected cadence and should be source-checked.",
        "- `lagged_source` usually means the series is annual or structural and the public provider itself is slow; replace it only if a better reusable source is available.",
        "- `projection` means the latest rendered point is a forecast horizon rather than a realised historical observation.",
        "- `scheduled_policy` means the latest point is a near-future official effective date for an administered policy series.",
        "- Keep `FRED_API_KEY` in the local environment or `.env.local`; never commit it.",
        "",
    ])
    AUDIT_MD.write_text("\n".join(lines))


def main() -> None:
    records: list[ChartFreshness] = []
    records.extend(_parse_ce4_catalog())
    for dashboard, path in DATA_FIRST_PAGES.items():
        records.extend(_parse_data_first_page(dashboard, path))
    _write_outputs(records)
    print(f"Wrote {AUDIT_MD}")
    print(f"Wrote {AUDIT_JSON}")


if __name__ == "__main__":
    main()
