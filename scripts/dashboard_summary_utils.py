"""Shared summary helpers for the data-first country dashboards.

The generated summary JSON files are intentionally machine-readable handoff
artifacts. Future agents should be able to inspect freshness, gap details, and
transform choices without scraping HTML or refetching live sources.
"""
from __future__ import annotations

import json
from calendar import monthrange
from collections import Counter, defaultdict
from datetime import UTC, date, datetime, timedelta
from typing import Any

from country_primer.data_quality import assess_series_quality, clean as _clean
from country_primer.framework import concept_id_for, framework_summary, load_macro_framework

CANONICAL_OBSERVATION_COLUMNS = ["date", "value"]


def month_index(value: date) -> int:
    """A monotonic month counter (year*12 + month) for calendar-gap arithmetic."""
    return value.year * 12 + value.month


def calendar_gap_matches(frequency: str, periods: int, base_date: date, item_date: date) -> bool:
    """True when ``item_date`` is exactly ``periods`` calendar periods after ``base_date``.

    Used offline over already-built series (canonical frames, freshness
    audits) to check that a declared frequency matches observed spacing, and
    that a lag-transformed series has not drifted from its nominal cadence —
    see validate_outputs.py. For computing a transform's own base
    observation, use `shift_calendar_periods` plus a date lookup instead:
    see its docstring for why index-based lag stepping is unsafe.
    """
    frequency = str(frequency or "").lower()
    if frequency == "weekly":
        return (item_date - base_date).days == periods * 7
    months_per_period = {"quarterly": 3, "annual": 12}.get(frequency, 1)
    return (month_index(item_date) - month_index(base_date)) == periods * months_per_period


def shift_calendar_periods(value: date, frequency: str, periods: int) -> date:
    """Return the date exactly ``periods`` calendar periods before ``value``.

    Lag-based transforms (yoy/qoq/mom/pct_change/diff) must look up their
    base observation by *calendar date*, not by a fixed array offset
    (`observations[index - periods]`). Array-offset stepping breaks
    permanently, not just at the gap: once one interior observation is
    missing (e.g. BLS never published October 2025 CPI during the
    government shutdown), every later index is shifted one slot early
    forever, so "YoY" silently becomes a 13-month change for the rest of
    the series' history — not just at the gap itself. Looking up the exact
    expected date self-heals as soon as that date's own observation exists
    again; only points whose exact calendar-aligned base is itself missing
    should be skipped.
    """
    frequency = str(frequency or "").lower()
    if frequency == "weekly":
        return value - timedelta(days=periods * 7)
    months_per_period = {"quarterly": 3, "annual": 12}.get(frequency, 1)
    total_months = value.year * 12 + (value.month - 1) - periods * months_per_period
    year, month = divmod(total_months, 12)
    month += 1
    day = min(value.day, monthrange(year, month)[1])
    return date(year, month, day)


def _latest_observation(series: dict[str, Any]) -> dict[str, Any] | None:
    observations = series.get("observations") or []
    if not observations:
        return None
    return observations[-1]


def apply_quality_assessments(series_list: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Attach the shared quality model before HTML and JSON are rendered."""
    for item in series_list:
        quality = assess_series_quality(item)
        item["data_quality"] = quality
        item["quality_status"] = quality["status"]
    return series_list


def canonical_data_first_series(country_code: str, series_list: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return compact series metadata plus [date, value] observations."""
    output: list[dict[str, Any]] = []
    for item in series_list:
        indicator_id = _clean(item.get("id") or item.get("indicator_id"))
        observations: list[list[Any]] = []
        for observation in item.get("observations") or []:
            try:
                value = float(observation.get("value"))
            except (TypeError, ValueError):
                continue
            observations.append([_clean(observation.get("date")), value])
        if not observations:
            continue
        quality = dict(item.get("data_quality") or assess_series_quality(item))
        output.append({
            "indicator_id": indicator_id,
            "concept_id": concept_id_for(country_code, indicator_id),
            "section": _clean(item.get("section")),
            "label_en": _clean(item.get("label_en") or item.get("label")),
            "label_zh": _clean(item.get("label_zh") or item.get("label_en") or item.get("label")),
            "unit": _clean(item.get("unit")),
            "frequency": _clean(item.get("frequency")),
            "transform": _clean(item.get("transform") or "level"),
            "source": {
                "name": _clean(item.get("source_name")),
                "series": _clean(item.get("series")),
                "url": _clean(item.get("source_url") or item.get("api_url")),
            },
            "quality": quality,
            "quality_notes": list(item.get("quality_notes") or []),
            "actual_through": _clean(item.get("actual_through")),
            "provider_updated": _clean(item.get("provider_updated")),
            "refresh_fallback": bool(item.get("refresh_fallback")),
            "observations": observations,
        })
    return sorted(output, key=lambda row: row["indicator_id"])


def write_canonical_data_first_frame(path: Any, country_code: str, series_list: list[dict[str, Any]]) -> dict[str, Any]:
    """Write canonical v2 without repeating metadata for every observation."""
    from pathlib import Path

    compact_series = canonical_data_first_series(country_code, series_list)
    observation_count = sum(len(item["observations"]) for item in compact_series)
    framework = load_macro_framework()
    payload = {
        "schema_version": "data-first-canonical-v2",
        "generated": datetime.now(UTC).isoformat(),
        "country": country_code,
        "framework": framework_summary(),
        "observation_columns": CANONICAL_OBSERVATION_COLUMNS,
        "legacy_aliases": framework.legacy_aliases,
        "series": compact_series,
    }
    output_path = Path(path)
    output_path.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n")
    return {
        "schema_version": payload["schema_version"],
        "observation_columns": CANONICAL_OBSERVATION_COLUMNS,
        "file": output_path.name,
        "series": len(compact_series),
        "observations": observation_count,
        "series_count": len(compact_series),
        "observation_count": observation_count,
    }


def canonical_frame_metadata(path: Any) -> dict[str, Any]:
    from pathlib import Path

    payload = json.loads(Path(path).read_text())
    compact_series = list(payload.get("series") or [])
    observation_count = sum(len(item.get("observations") or []) for item in compact_series)
    return {
        "schema_version": payload.get("schema_version", ""),
        "observation_columns": list(payload.get("observation_columns") or CANONICAL_OBSERVATION_COLUMNS),
        "file": Path(path).name,
        "series": len(compact_series),
        "observations": observation_count,
        "series_count": len(compact_series),
        "observation_count": observation_count,
        "snapshot_generated": payload.get("generated", ""),
    }


def load_canonical_data_first_frame(path: Any, config: dict[str, Any]) -> list[dict[str, Any]]:
    """Restore renderer-ready series from a committed canonical v2 snapshot."""
    from pathlib import Path

    payload = json.loads(Path(path).read_text())
    if payload.get("schema_version") != "data-first-canonical-v2":
        raise ValueError(f"Unsupported canonical snapshot: {payload.get('schema_version')}")
    specs = {
        _clean(item.get("id")): dict(item)
        for item in (config.get("indicators") or [])
        if _clean(item.get("id"))
    }
    restored: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in payload.get("series") or []:
        indicator_id = _clean(item.get("indicator_id"))
        if not indicator_id:
            continue
        source = dict(item.get("source") or {})
        quality = dict(item.get("quality") or {})
        observations = []
        for row in item.get("observations") or []:
            if not isinstance(row, list) or len(row) < 2:
                continue
            try:
                observations.append({"date": _clean(row[0]), "value": float(row[1])})
            except (TypeError, ValueError):
                continue
        spec = dict(specs.get(indicator_id) or {})
        restored.append({
            **spec,
            "id": indicator_id,
            "section": _clean(item.get("section") or spec.get("section")),
            "label_en": _clean(item.get("label_en") or spec.get("label_en") or indicator_id),
            "label_zh": _clean(item.get("label_zh") or spec.get("label_zh") or indicator_id),
            "unit": _clean(item.get("unit") or spec.get("unit")),
            "frequency": _clean(item.get("frequency") or spec.get("frequency")),
            "transform": _clean(item.get("transform") or spec.get("transform") or "level"),
            "source_name": _clean(source.get("name") or spec.get("source_name")),
            "series": _clean(source.get("series") or spec.get("series")),
            "source_url": _clean(source.get("url") or spec.get("source_url")),
            "api_url": _clean(source.get("url") or spec.get("api_url")),
            "quality_notes": list(item.get("quality_notes") or []),
            "actual_through": _clean(item.get("actual_through") or spec.get("actual_through")),
            "provider_updated": _clean(item.get("provider_updated") or spec.get("provider_updated")),
            "refresh_fallback": bool(item.get("refresh_fallback")),
            "observations": observations,
            "data_quality": quality,
            "quality_status": _clean(quality.get("status") or spec.get("quality_status") or "watch"),
            "snapshot_generated": payload.get("generated", ""),
        })
        seen.add(indicator_id)

    # Keep configured gaps visible in summary metadata without fabricating data.
    for indicator_id, spec in specs.items():
        if indicator_id in seen:
            continue
        restored.append({
            **spec,
            "id": indicator_id,
            "observations": [],
            "quality_status": "unavailable",
            "quality_notes": ["No observations in committed canonical snapshot."],
        })
    return restored


def retain_last_known_good_series(
    series_list: list[dict[str, Any]],
    canonical_path: Any,
    config: dict[str, Any],
) -> list[dict[str, Any]]:
    """Retain prior observations when a live refresh fails for an existing series."""
    from pathlib import Path

    path = Path(canonical_path)
    if not path.exists():
        return series_list
    previous = {
        item["id"]: item
        for item in load_canonical_data_first_frame(path, config)
        if item.get("observations")
    }
    merged: list[dict[str, Any]] = []
    for item in series_list:
        if item.get("observations") or item.get("id") not in previous:
            merged.append(item)
            continue
        prior = dict(previous[item["id"]])
        reason = _clean(item.get("failure_reason") or "live_unavailable")
        prior_notes = [
            note for note in (prior.get("quality_notes") or [])
            if "retained prior canonical snapshot" not in _clean(note).lower()
        ]
        prior.update({
            "refresh_fallback": True,
            "refresh_failure_reason": reason,
            "quality_status": "watch",
            "quality_notes": prior_notes + [
                f"Live refresh unavailable [{reason}]; retained prior canonical snapshot."
            ],
        })
        merged.append(prior)
    return merged


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


def _chart_freshness_records(
    series_list: list[dict[str, Any]], *, country_code: str, today: date
) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for item in series_list:
        quality = dict(item.get("data_quality") or assess_series_quality(item, today=today))
        status = quality["freshness"]
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
            "concept_id": concept_id_for(country_code, _clean(item.get("id"))),
            "label_en": _clean(item.get("label_en") or item.get("label")),
            "latest_date": quality["latest_date"],
            "frequency": _clean(item.get("frequency")),
            "freshness_status": status,
            "age_basis_date": quality["latest_date"],
            "age_days": quality["age_days"],
            "threshold_days": quality["max_age_days"],
            "release_calendar_id": quality.get("release_calendar_id", ""),
            "expected_release_date": quality.get("expected_release_date", ""),
            "due_date": quality.get("due_date", ""),
            "quality_status": quality["status"],
            "source_authority": quality["source_authority"],
            "derivation": quality["derivation"],
            "validation": quality["validation"],
            "comparability": quality["comparability"],
            "source_name": _clean(item.get("source_name")),
            "series": _clean(item.get("series")),
            "transform": _clean(item.get("transform") or "level"),
        })
    return records


def build_summary_metadata(
    config: dict[str, Any], series_list: list[dict[str, Any]], country_code: str
) -> dict[str, Any]:
    """Return structured audit metadata for a dashboard summary JSON."""
    today = datetime.now(UTC).date()
    apply_quality_assessments(series_list)
    charted = [item for item in series_list if item.get("observations")]
    unavailable = [item for item in series_list if not item.get("observations")]
    freshness_records = _chart_freshness_records(charted, country_code=country_code, today=today)
    freshness_counts = Counter(item["freshness_status"] for item in freshness_records)
    attention_statuses = {"stale", "due", "missing", "future_date"}
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
        "framework": framework_summary(),
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
        "canonical_schema": {
            "schema_version": "data-first-canonical-v2",
            "observation_columns": CANONICAL_OBSERVATION_COLUMNS,
            "charted_series": len(charted),
        },
    }
