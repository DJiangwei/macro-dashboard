"""Shared, multi-dimensional data-quality and freshness assessment."""
from __future__ import annotations

from calendar import monthrange
from datetime import date
import re
from typing import Any


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


def source_authority(source_name: object, source_url: object = "") -> str:
    source = f"{clean(source_name)} {clean(source_url)}".lower()
    if any(token in source for token in (
        "ons", "bank of england", "boe", "safe", "fiscaldata", "us treasury",
        "bls business", "eurostat", "ecb ", "cnb", "nbp", "mnb", "bnr",
    )):
        return "official_primary"
    if any(token in source for token in ("fred", "world bank", "imf", "bis", "oecd", "db.nomics")):
        return "official_mirror"
    if any(token in source for token in ("akshare", "eastmoney", "sina", "yahoo", "stooq")):
        return "public_wrapper"
    if any(token in source for token in ("manual", "curated", "tracker")):
        return "manual_curated"
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
    authority = source_authority(series.get("source_name") or series.get("source"), series.get("source_url"))
    indicator_id = clean(series.get("id") or series.get("indicator_id"))
    scheduled_policy = indicator_id in {
        "reserve_balance_rate",
        "fed_upper_target",
        "fed_lower_target",
    }

    age_days: int | None = None
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
        if age_days > max_age:
            freshness = "stale"
        elif age_days > max_age * 0.75:
            freshness = "due"
        else:
            freshness = "current"

    notes = [clean(item) for item in (series.get("quality_notes") or []) if clean(item)]
    note_text = " ".join(notes).lower()
    if not observations or "fetch failed" in note_text or "no observations" in note_text:
        validation = "failed"
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
    elif authority == "official_primary" and derivation == "observed" and freshness == "current" and validation == "passed":
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
    }
