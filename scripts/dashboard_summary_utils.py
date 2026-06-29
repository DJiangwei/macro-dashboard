"""Shared summary helpers for the data-first country dashboards.

The generated summary JSON files are intentionally machine-readable handoff
artifacts. Future agents should be able to inspect freshness, gap details, and
transform choices without scraping HTML or refetching live sources.
"""
from __future__ import annotations

import re
from calendar import monthrange
from collections import Counter, defaultdict
from datetime import UTC, date, datetime
from typing import Any


THRESHOLD_DAYS = {
    "daily": 14,
    "business daily": 14,
    "weekly": 45,
    "monthly": 150,
    "quarterly": 330,
}


def _clean(value: object) -> str:
    return " ".join(str(value or "").replace("\xa0", " ").split())


def _parse_date(value: object) -> date | None:
    text = _clean(value)
    if not text or text.lower() in {"missing", "n/a", "nan"}:
        return None
    text = text.split("·", 1)[0].strip()
    iso_match = re.search(r"(\d{4})-(\d{2})-(\d{2})", text)
    if iso_match:
        try:
            return date(int(iso_match.group(1)), int(iso_match.group(2)), int(iso_match.group(3)))
        except ValueError:
            return None
    year_month_match = re.fullmatch(r"(\d{4})-(\d{2})", text)
    if year_month_match:
        try:
            return date(int(year_month_match.group(1)), int(year_month_match.group(2)), 1)
        except ValueError:
            return None
    quarter_match = re.search(r"(\d{4})\s*Q([1-4])", text, flags=re.I)
    if quarter_match:
        year = int(quarter_match.group(1))
        month = int(quarter_match.group(2)) * 3
        return date(year, month, monthrange(year, month)[1])
    if re.fullmatch(r"\d{4}", text):
        return date(int(text), 12, 31)
    return None


def _threshold_for_frequency(frequency: object) -> int | None:
    normalized = _clean(frequency).lower()
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
    return None


def _period_end_for_age(latest: date, frequency: object) -> date:
    normalized = _clean(frequency).lower()
    if "quarter" in normalized and latest.day == 1 and latest.month in {1, 4, 7, 10}:
        month = latest.month + 2
        return date(latest.year, month, monthrange(latest.year, month)[1])
    if "month" in normalized and latest.day == 1:
        return date(latest.year, latest.month, monthrange(latest.year, latest.month)[1])
    return latest


def _classify(latest: date | None, frequency: object, quality_status: object, *, today: date) -> tuple[str, date | None, int | None, int | None]:
    threshold = _threshold_for_frequency(frequency)
    if latest is None:
        return "missing_date", None, None, threshold

    normalized = _clean(frequency).lower()
    if "annual" in normalized or "year" in normalized:
        if latest.year > today.year:
            return "projection", latest, (today - latest).days, None
        age_basis = latest if latest <= today else today
        if latest.year < today.year - 2:
            return "lagged_source", age_basis, (today - age_basis).days, None
        return "current", age_basis, (today - age_basis).days, None

    if latest > today:
        return "future_date", latest, (today - latest).days, threshold

    age_basis = min(_period_end_for_age(latest, frequency), today)
    age_days = (today - age_basis).days
    if threshold is not None and age_days > threshold:
        return "stale", age_basis, age_days, threshold
    if _clean(quality_status) == "low_confidence":
        return "needs_review", age_basis, age_days, threshold
    return "current", age_basis, age_days, threshold


def _latest_observation(series: dict[str, Any]) -> dict[str, Any] | None:
    observations = series.get("observations") or []
    if not observations:
        return None
    return observations[-1]


def _quality_counts(series_list: list[dict[str, Any]]) -> dict[str, int]:
    counts = Counter(_clean(item.get("quality_status") or "unchecked") for item in series_list)
    return {key: counts[key] for key in sorted(counts)}


def _source_counts(series_list: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_source: dict[str, set[str]] = defaultdict(set)
    for item in series_list:
        if not item.get("observations"):
            continue
        source = _clean(item.get("source_name") or "Unknown")
        by_source[source].add(_clean(item.get("id")))
    return [
        {"source_name": source, "charts": len(ids)}
        for source, ids in sorted(by_source.items(), key=lambda pair: (-len(pair[1]), pair[0]))
    ]


def _transform_counts(series_list: list[dict[str, Any]]) -> dict[str, int]:
    counts = Counter(_clean(item.get("transform") or "level") for item in series_list if item.get("observations"))
    return {key: counts[key] for key in sorted(counts)}


def _gap_detail(config: dict[str, Any]) -> list[dict[str, str]]:
    gaps = []
    for gap in config.get("data_gaps", []) or []:
        gaps.append({
            "section": _clean(gap.get("section")),
            "item_en": _clean(gap.get("item_en")),
            "item_zh": _clean(gap.get("item_zh")),
            "status_en": _clean(gap.get("status_en")),
            "status_zh": _clean(gap.get("status_zh")),
        })
    return gaps


def _chart_freshness_records(series_list: list[dict[str, Any]], *, today: date) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for item in series_list:
        latest_observation = _latest_observation(item)
        latest_date = _parse_date(latest_observation.get("date") if latest_observation else "")
        status, age_basis, age_days, threshold_days = _classify(
            latest_date,
            item.get("frequency"),
            item.get("quality_status"),
            today=today,
        )
        haystack = " ".join([
            _clean(item.get("id")),
            _clean(item.get("source_name")),
            _clean(item.get("caveat_en")),
        ]).lower()
        if status == "future_date" and (
            item.get("id") in {"reserve_balance_rate", "fed_upper_target", "fed_lower_target"}
            or "administered rate" in haystack
        ):
            status = "scheduled_policy"
        records.append({
            "id": _clean(item.get("id")),
            "label_en": _clean(item.get("label_en") or item.get("label")),
            "latest_date": latest_date.isoformat() if latest_date else "",
            "frequency": _clean(item.get("frequency")),
            "freshness_status": status,
            "age_basis_date": age_basis.isoformat() if age_basis else "",
            "age_days": age_days,
            "threshold_days": threshold_days,
            "quality_status": _clean(item.get("quality_status") or "unchecked"),
            "source_name": _clean(item.get("source_name")),
            "series": _clean(item.get("series")),
            "transform": _clean(item.get("transform") or "level"),
        })
    return records


def build_summary_metadata(config: dict[str, Any], series_list: list[dict[str, Any]]) -> dict[str, Any]:
    """Return structured audit metadata for a dashboard summary JSON."""
    today = datetime.now(UTC).date()
    charted = [item for item in series_list if item.get("observations")]
    unavailable = [item for item in series_list if not item.get("observations")]
    freshness_records = _chart_freshness_records(charted, today=today)
    freshness_counts = Counter(item["freshness_status"] for item in freshness_records)
    attention_statuses = {"stale", "lagged_source", "missing_date", "future_date", "needs_review"}
    attention = [
        item
        for item in freshness_records
        if item["freshness_status"] in attention_statuses
    ]
    attention.sort(key=lambda item: (item["age_days"] is None, -(item["age_days"] or 0), item["id"]))
    latest_historical_date = max(
        [
            item["age_basis_date"] or item["latest_date"]
            for item in freshness_records
            if item["latest_date"] and item["freshness_status"] not in {"projection", "future_date", "scheduled_policy"}
        ],
        default="",
    )

    return {
        "data_gaps_detail": _gap_detail(config),
        "source_health": {
            "source_groups": len({item.get("source_name") for item in charted}),
            "sources": _source_counts(charted),
            "quality_counts": _quality_counts(charted),
            "unavailable_count": len(unavailable),
        },
        "freshness": {
            "as_of_date": today.isoformat(),
            "counts": {key: freshness_counts[key] for key in sorted(freshness_counts)},
            "latest_historical_date": latest_historical_date,
            "attention": attention[:40],
        },
        "transform_audit": {
            "counts": _transform_counts(charted),
            "non_level": [
                {
                    "id": _clean(item.get("id")),
                    "label_en": _clean(item.get("label_en") or item.get("label")),
                    "transform": _clean(item.get("transform")),
                    "unit": _clean(item.get("unit")),
                }
                for item in charted
                if _clean(item.get("transform") or "level") != "level"
            ],
        },
    }
