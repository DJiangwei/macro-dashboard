"""Shared, multi-dimensional data-quality and freshness assessment."""
from __future__ import annotations

from calendar import monthrange
from datetime import date
from functools import lru_cache
from pathlib import Path
import re
from typing import Any

import yaml


# These are release-aware defaults, not assertions that every source releases
# at the same speed. Individual indicator configs can override max_age_days.
DEFAULT_MAX_AGE_DAYS = {
    "daily": 10,
    "business daily": 10,
    "weekly": 28,
    "monthly": 75,
    "quarterly": 165,
    "annual": 730,
    "irregular": 365,
    "event": 365,
    "seasonal": 270,
}

RELEASE_CALENDAR_PATH = Path(__file__).resolve().parents[2] / "config" / "release_calendars.yaml"


def clean(value: object) -> str:
    return " ".join(str(value or "").replace("\xa0", " ").split())


def parse_date(value: object) -> date | None:
    text = clean(value)
    if not text or text.lower() in {"missing", "n/a", "nan"}:
        return None
    match = re.search(r"(\d{4})-(\d{2})-(\d{2})", text)
    if match:
        try:
            return date(int(match.group(1)), int(match.group(2)), int(match.group(3)))
        except ValueError:
            return None
    quarter = re.search(r"(\d{4})\s*Q([1-4])", text, flags=re.I)
    if quarter:
        year = int(quarter.group(1))
        month = int(quarter.group(2)) * 3
        return date(year, month, monthrange(year, month)[1])
    if re.fullmatch(r"\d{4}", text):
        return date(int(text), 12, 31)
    return None


def normalized_frequency(value: object) -> str:
    text = clean(value).lower()
    if "daily" in text:
        return "daily"
    if "week" in text:
        return "weekly"
    if "month" in text:
        return "monthly"
    if "quarter" in text:
        return "quarterly"
    if "annual" in text or "year" in text:
        return "annual"
    if "season" in text:
        return "seasonal"
    if "event" in text:
        return "event"
    return text or "irregular"


def period_end(value: date, frequency: object) -> date:
    normalized = normalized_frequency(frequency)
    if normalized == "quarterly" and value.day == 1 and value.month in {1, 4, 7, 10}:
        month = value.month + 2
        return date(value.year, month, monthrange(value.year, month)[1])
    if normalized == "monthly" and value.day == 1:
        return date(value.year, value.month, monthrange(value.year, value.month)[1])
    return value


def _next_period_end(value: date, frequency: object) -> date | None:
    normalized = normalized_frequency(frequency)
    current = period_end(value, normalized)
    if normalized == "monthly":
        year = current.year + (1 if current.month == 12 else 0)
        month = 1 if current.month == 12 else current.month + 1
        return date(year, month, monthrange(year, month)[1])
    if normalized == "quarterly":
        year = current.year + (1 if current.month >= 10 else 0)
        month = ((current.month // 3) % 4 + 1) * 3
        return date(year, month, monthrange(year, month)[1])
    if normalized == "annual":
        return date(current.year + 1, 12, 31)
    return None


@lru_cache(maxsize=1)
def load_release_calendars() -> dict[str, Any]:
    if not RELEASE_CALENDAR_PATH.exists():
        return {"due_warning_days": 7, "rules": []}
    payload = yaml.safe_load(RELEASE_CALENDAR_PATH.read_text()) or {}
    return {
        "due_warning_days": int(payload.get("due_warning_days") or 7),
        "rules": list(payload.get("rules") or []),
    }


def _release_calendar_rule(series: dict[str, Any]) -> dict[str, Any] | None:
    configured_id = clean(series.get("release_calendar_id")).lower()
    indicator_id = clean(series.get("id") or series.get("indicator_id")).lower()
    frequency = normalized_frequency(series.get("frequency"))
    source = " ".join([
        clean(series.get("source_name") or series.get("source")),
        clean(series.get("source_url")),
    ]).lower()
    candidates: list[tuple[int, dict[str, Any]]] = []
    for rule in load_release_calendars()["rules"]:
        rule_id = clean(rule.get("id")).lower()
        if configured_id and configured_id != rule_id:
            continue
        frequencies = {normalized_frequency(item) for item in (rule.get("frequencies") or [])}
        if frequencies and frequency not in frequencies:
            continue
        indicator_ids = {clean(item).lower() for item in (rule.get("indicator_ids") or [])}
        if indicator_ids and indicator_id not in indicator_ids:
            continue
        source_tokens = [clean(item).lower() for item in (rule.get("source_contains") or []) if clean(item)]
        if source_tokens and not any(token in source for token in source_tokens):
            continue
        score = (100 if configured_id else 0) + (20 if indicator_ids else 0) + (10 if source_tokens else 0)
        candidates.append((score, rule))
    if not candidates:
        return None
    return max(candidates, key=lambda item: item[0])[1]


def expected_next_release(series: dict[str, Any], latest: date) -> dict[str, Any] | None:
    """Return the expected next-publication window for a matched official rule."""
    rule = _release_calendar_rule(series)
    next_period = _next_period_end(latest, series.get("frequency"))
    if not rule or not next_period:
        return None
    lag_days = int(rule.get("publication_lag_days") or 0)
    grace_days = int(rule.get("grace_days") or 0)
    from datetime import timedelta

    expected = next_period + timedelta(days=lag_days)
    due = expected + timedelta(days=grace_days)
    return {
        "calendar_id": clean(rule.get("id")),
        "next_period_end": next_period.isoformat(),
        "expected_release_date": expected.isoformat(),
        "due_date": due.isoformat(),
        "publication_lag_days": lag_days,
        "grace_days": grace_days,
    }


VALID_SOURCE_AUTHORITIES = frozenset({
    "official_primary",
    "official_mirror",
    "public_wrapper",
    "manual_curated",
    "public_secondary",
})


def source_authority(source_name: object, source_url: object = "", declared: object = "") -> str:
    # A config author who validated the source declares its tier explicitly;
    # name matching is only the fallback for series that predate the field.
    declared_value = clean(declared).lower().replace(" ", "_")
    if declared_value in VALID_SOURCE_AUTHORITIES:
        return declared_value
    source = f"{clean(source_name)} {clean(source_url)}".lower()
    if any(token in source for token in ("manual", "curated", "tracker")):
        return "manual_curated"
    if any(token in source for token in ("akshare", "eastmoney", "sina", "yahoo", "stooq")):
        return "public_wrapper"
    if any(token in source for token in ("fred", "world bank", "imf", "bis", "oecd", "db.nomics")):
        return "official_mirror"
    if any(token in source for token in (
        "ons", "bank of england", "boe", "safe", "fiscaldata", "us treasury",
        "bls business", "eurostat", "ecb ", "cnb", "nbp", "mnb", "bnr",
        "bureau of economic analysis", "bea.gov", "bureau of labor statistics", "bls.gov",
        "federal reserve", "treasury.gov", "national bureau of statistics", "stats.gov.cn",
        "people's bank of china", "pbc.gov.cn", "pboc", "safe.gov.cn",
        "bank of japan", "boj", "stat-search.boj", "e-stat", "estat",
        "statistics bureau", "mhlw", "mlit", "meti",
        "sarb", "resbank", "south african reserve bank",
    )):
        return "official_primary"
    return "public_secondary"


def derivation_type(series: dict[str, Any]) -> str:
    haystack = " ".join([
        clean(series.get("id") or series.get("indicator_id")),
        clean(series.get("source_name") or series.get("source")),
        clean(series.get("series")),
        clean(series.get("caveat_en")),
        " ".join(clean(item) for item in (series.get("quality_notes") or [])),
    ]).lower()
    latest = parse_date((series.get("observations") or [{}])[-1].get("date") if series.get("observations") else "")
    actual_through = parse_date(series.get("actual_through"))
    if actual_through and latest and latest > actual_through:
        return "projection"
    if series.get("is_projection") or clean(series.get("observation_type")).lower() == "projection":
        return "projection"
    if clean(series.get("derivation")).lower() == "substitute" or series.get("is_substitute"):
        return "substitute"
    if any(token in haystack for token in (
        "used as a substitute",
        "public substitute",
        "public proxy",
        "fallback proxy",
        "proxy for",
    )):
        return "substitute"
    if any(token in haystack for token in ("manual:", "curated")):
        return "manual"
    if clean(series.get("transform") or "level") != "level" or "derived" in haystack:
        return "derived"
    return "observed"


def assess_series_quality(series: dict[str, Any], *, today: date | None = None) -> dict[str, Any]:
    today = today or date.today()
    observations = series.get("observations") or []
    latest = parse_date(observations[-1].get("date")) if observations else None
    frequency = normalized_frequency(series.get("frequency"))
    max_age = int(series.get("max_age_days") or DEFAULT_MAX_AGE_DAYS.get(frequency, 365))
    derivation = derivation_type(series)
    authority = source_authority(
        series.get("source_name") or series.get("source"),
        series.get("source_url"),
        series.get("source_authority"),
    )
    indicator_id = clean(series.get("id") or series.get("indicator_id"))
    scheduled_policy = indicator_id in {
        "reserve_balance_rate",
        "fed_upper_target",
        "fed_lower_target",
    }

    age_days: int | None = None
    release_window = expected_next_release(series, latest) if latest else None
    if latest is None:
        freshness = "missing"
    elif derivation == "projection":
        freshness = "projection"
    elif latest > today and scheduled_policy:
        freshness = "scheduled_policy"
    elif latest > today:
        freshness = "future_date"
    else:
        age_days = (today - min(period_end(latest, frequency), today)).days
        if release_window and not series.get("max_age_days"):
            due_date = date.fromisoformat(release_window["due_date"])
            expected_date = date.fromisoformat(release_window["expected_release_date"])
            warning_days = int(load_release_calendars()["due_warning_days"])
            max_age = max(0, (due_date - period_end(latest, frequency)).days)
            if today > due_date:
                freshness = "stale"
            elif today >= expected_date or (expected_date - today).days <= warning_days:
                freshness = "due"
            else:
                freshness = "current"
        elif age_days > max_age:
            freshness = "stale"
        elif age_days > max_age * 0.75:
            freshness = "due"
        else:
            freshness = "current"

    notes = [clean(item) for item in (series.get("quality_notes") or []) if clean(item)]
    note_text = " ".join(notes).lower()
    if not observations or "fetch failed" in note_text or "no observations" in note_text:
        validation = "failed"
    elif series.get("refresh_fallback"):
        validation = "watch"
    elif any(token in note_text for token in ("outlier", "unit mismatch", "date could not", "short history")):
        validation = "watch"
    else:
        validation = "passed"

    if derivation == "substitute":
        comparability = "low"
    elif derivation in {"derived", "manual", "projection"} or authority in {"public_wrapper", "official_mirror"}:
        comparability = "medium"
    else:
        comparability = "high"

    if validation == "failed" or freshness in {"missing", "future_date"}:
        status = "unavailable"
    elif comparability == "low" or freshness == "stale":
        status = "low_confidence"
    elif (
        # A declared transform of an official series (YoY from an official index) is
        # normal macro practice, not a trust deduction. Substitutes standing in for a
        # different concept remain excluded via comparability.
        authority == "official_primary"
        and derivation in {"observed", "derived"}
        and freshness == "current"
        and validation == "passed"
    ):
        status = "verified"
    else:
        status = "watch"

    return {
        "status": status,
        "source_authority": authority,
        "derivation": derivation,
        "freshness": freshness,
        "validation": validation,
        "comparability": comparability,
        "latest_date": latest.isoformat() if latest else "",
        "age_days": age_days,
        "max_age_days": max_age,
        "release_calendar_id": release_window["calendar_id"] if release_window else "",
        "expected_release_date": release_window["expected_release_date"] if release_window else "",
        "due_date": release_window["due_date"] if release_window else "",
        "refresh_fallback": bool(series.get("refresh_fallback")),
    }
