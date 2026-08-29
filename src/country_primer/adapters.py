"""Shared source adapters used by more than one country builder.

Fetchers live here rather than inside a builder so that a country page never
has to import from another country page.
"""
from __future__ import annotations

import csv
import io
import re
import threading
from datetime import UTC, datetime
from typing import Any

import requests


IMF_SDMX_BASE = "https://api.imf.org/external/sdmx/2.1/data"
IMF_DATAMAPPER_BASE = "https://www.imf.org/external/datamapper/api/v1"
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 Chrome/124.0 Safari/537.36"
)

# The IMF SDMX endpoint rejects startPeriod on several dataflows and answers the
# unfiltered request instead, so one full pull per dataflow is cached in-process
# and sliced per indicator rather than refetched for every series key.
IMF_SDMX_LOCK = threading.Lock()
IMF_SDMX_CACHE: dict[tuple[str, str], list[dict[str, str]]] = {}


def sdmx_period_to_date(value: str) -> str | None:
    """Normalise SDMX period notation (2026-M06, 2025-Q3, 2024) to ISO dates."""
    text = str(value or "").strip()
    match = re.match(r"^(\d{4})-M(\d{1,2})$", text)
    if match:
        return f"{int(match.group(1)):04d}-{int(match.group(2)):02d}-01"
    match = re.match(r"^(\d{4})-Q([1-4])$", text)
    if match:
        return f"{int(match.group(1)):04d}-{(int(match.group(2)) - 1) * 3 + 1:02d}-01"
    match = re.match(r"^(\d{4})-(\d{2})$", text)
    if match:
        return f"{match.group(1)}-{match.group(2)}-01"
    match = re.match(r"^(\d{4})-(\d{2})-(\d{2})$", text)
    if match:
        return text
    match = re.match(r"^(\d{4})$", text)
    if match:
        return f"{text}-01-01"
    return None


def _imf_sdmx_rows(session: requests.Session, dataflow: str, series_key: str) -> list[dict[str, str]]:
    cache_key = (dataflow, series_key)
    with IMF_SDMX_LOCK:
        cached = IMF_SDMX_CACHE.get(cache_key)
    if cached is not None:
        return cached

    response = session.get(
        f"{IMF_SDMX_BASE}/{dataflow}/{series_key}",
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "application/vnd.sdmx.data+csv;version=1.0.0",
        },
        timeout=(5, 120),
    )
    response.raise_for_status()
    rows = list(csv.DictReader(io.StringIO(response.text)))
    with IMF_SDMX_LOCK:
        IMF_SDMX_CACHE[cache_key] = rows
    return rows


def fetch_imf_sdmx(session: requests.Session, spec: dict[str, Any]) -> dict[str, Any]:
    """Fetch one fully-qualified IMF SDMX 2.1 series key as observations."""
    dataflow = str(spec["dataflow"])
    series_key = str(spec["series"])
    rows = _imf_sdmx_rows(session, dataflow, series_key)

    observations: list[dict[str, Any]] = []
    for row in rows:
        raw_value = row.get("OBS_VALUE")
        if raw_value in (None, "", "."):
            continue
        obs_date = sdmx_period_to_date(str(row.get("TIME_PERIOD", "")))
        if not obs_date:
            continue
        try:
            observations.append({"date": obs_date, "value": float(raw_value)})
        except (TypeError, ValueError):
            continue
    observations.sort(key=lambda item: item["date"])

    start_date = str(spec.get("start_date") or "")
    if start_date:
        observations = [item for item in observations if item["date"] >= start_date]
    if not observations:
        raise RuntimeError(f"IMF SDMX returned no observations for {dataflow}/{series_key}.")

    provider_updated = ""
    for row in rows:
        candidate = str(row.get("UPDATE_DATE") or row.get("PUBLICATION_DATE") or "").strip()
        if candidate:
            provider_updated = candidate[:10]
            break
    return {
        **spec,
        "observations": observations,
        "provider_updated": provider_updated or observations[-1]["date"],
        "api_url": f"{IMF_SDMX_BASE}/{dataflow}/{series_key}",
    }


def fetch_imf_datamapper(session: requests.Session, spec: dict[str, Any]) -> dict[str, Any]:
    """Fetch one IMF WEO DataMapper indicator for a single ISO3 country."""
    code = str(spec["series"])
    iso3 = str(spec.get("country_iso3") or "JPN")
    url = f"{IMF_DATAMAPPER_BASE}/{code}/{iso3}"
    # imf.org answers 403 to the browser User-Agent the other endpoints require,
    # so this call deliberately sends the default requests headers.
    response = session.get(url, timeout=(5, 45))
    response.raise_for_status()
    payload = response.json()
    country_values = ((payload.get("values") or {}).get(code) or {}).get(iso3) or {}
    observations = [
        {"date": str(year), "value": float(value)}
        for year, value in country_values.items()
        if value is not None and str(year).isdigit()
    ]
    observations.sort(key=lambda item: int(item["date"]))
    if not observations:
        raise RuntimeError(f"IMF DataMapper returned no observations for {code}/{iso3}.")
    return {
        **spec,
        "observations": observations,
        "provider_updated": datetime.now(UTC).date().isoformat(),
        "api_url": url,
    }


def apply_scale(series: dict[str, Any]) -> dict[str, Any]:
    """Divide observations by ``spec['scale']`` so units read as bn/mn, not raw."""
    try:
        scale = float(series.get("scale") or 0)
    except (TypeError, ValueError):
        return series
    observations = series.get("observations") or []
    if scale in (0.0, 1.0) or not observations:
        return series
    return {
        **series,
        "observations": [
            {**item, "value": float(item["value"]) / scale} for item in observations
        ],
    }
