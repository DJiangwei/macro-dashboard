"""Shared source adapters used by more than one country builder.

Fetchers live here rather than inside a builder so that a country page never
has to import from another country page.
"""
from __future__ import annotations

import csv
import io
import os
import re
import threading
import zipfile
from datetime import UTC, datetime
from typing import Any

import requests


IMF_SDMX_BASE = "https://api.imf.org/external/sdmx/2.1/data"
IMF_DATAMAPPER_BASE = "https://www.imf.org/external/datamapper/api/v1"
BOJ_FLATFILE_BASE = "https://www.stat-search.boj.or.jp/info"
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


def parse_boj_wide_csv(text: str, series_code: str) -> list[dict[str, Any]]:
    """Parse a BOJ flat file. Row 1 holds YYYYMM periods from column 4 onward;
    each data row is `code,dataset,label,v1..vN`."""
    rows = list(csv.reader(io.StringIO(text)))
    if not rows:
        return []
    periods = rows[0][3:]
    for row in rows[1:]:
        if not row or row[0].strip() != series_code:
            continue
        observations: list[dict[str, Any]] = []
        for period, raw in zip(periods, row[3:]):
            period = period.strip()
            if len(period) != 6 or not period.isdigit():
                continue
            try:
                value = float(str(raw).strip())
            except (TypeError, ValueError):
                continue
            observations.append({"date": f"{period[:4]}-{period[4:6]}-01", "value": value})
        observations.sort(key=lambda item: item["date"])
        return observations
    return []


def fetch_boj_flatfile(session: requests.Session, spec: dict[str, Any]) -> dict[str, Any]:
    name = str(spec["boj_file"])
    url = f"{BOJ_FLATFILE_BASE}/{name}.zip"
    response = session.get(url, headers={"User-Agent": USER_AGENT}, timeout=(5, 120))
    response.raise_for_status()
    with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
        member = next((n for n in archive.namelist() if n.endswith(".csv")), None)
        if member is None:
            raise RuntimeError(f"BOJ archive {name}.zip contains no CSV.")
        text = archive.read(member).decode("ascii", "replace")
    observations = parse_boj_wide_csv(text, str(spec["series"]))
    start_date = str(spec.get("start_date") or "")
    if start_date:
        observations = [o for o in observations if o["date"] >= start_date]
    if not observations:
        raise RuntimeError(f"BOJ {name} returned no observations for {spec['series']}.")
    return {
        **spec,
        "observations": observations,
        "provider_updated": observations[-1]["date"],
        "api_url": url,
    }


ESTAT_BASE = "https://api.e-stat.go.jp/rest/3.0/app/json/getStatsData"


class EstatCredentialMissing(RuntimeError):
    """Raised when ESTAT_APP_ID is absent so the caller can fall back to a gap."""


def estat_time_to_date(value: str) -> str | None:
    """e-Stat encodes monthly periods as YYYY00MMMM; month is the last two digits."""
    text = str(value or "").strip()
    if len(text) != 10 or not text.isdigit():
        return None
    year, month = text[:4], text[8:10]
    if not ("01" <= month <= "12"):
        return None
    return f"{year}-{month}-01"


def estat_observations(payload: dict[str, Any]) -> list[dict[str, Any]]:
    rows = (
        payload.get("GET_STATS_DATA", {})
        .get("STATISTICAL_DATA", {})
        .get("DATA_INF", {})
        .get("VALUE")
    ) or []
    observations: list[dict[str, Any]] = []
    for row in rows:
        obs_date = estat_time_to_date(row.get("@time"))
        if not obs_date:
            continue
        try:
            observations.append({"date": obs_date, "value": float(row.get("$"))})
        except (TypeError, ValueError):
            continue
    observations.sort(key=lambda item: item["date"])
    return observations


def fetch_estat(session: requests.Session, spec: dict[str, Any]) -> dict[str, Any]:
    app_id = os.environ.get("ESTAT_APP_ID", "").strip()
    if not app_id:
        raise EstatCredentialMissing("ESTAT_APP_ID is not set.")
    params = {
        "appId": app_id,
        "statsDataId": str(spec["stats_data_id"]),
        "cdTab": str(spec["estat_tab"]),
        "cdCat01": str(spec["estat_cat01"]),
        # Nationwide. Omitting this returns the Tokyo ward area, not Japan.
        "cdArea": str(spec.get("estat_area") or "00000"),
    }
    # e-Stat free-text search times out; narrow id lookups still need a long read.
    response = session.get(ESTAT_BASE, params=params, timeout=(10, 240))
    response.raise_for_status()
    payload = response.json()
    status = payload.get("GET_STATS_DATA", {}).get("RESULT", {}).get("STATUS")
    if status != 0:
        raise RuntimeError(f"e-Stat returned STATUS={status} for {spec['stats_data_id']}.")
    observations = estat_observations(payload)
    start_date = str(spec.get("start_date") or "")
    if start_date:
        observations = [o for o in observations if o["date"] >= start_date]
    if not observations:
        raise RuntimeError(f"e-Stat returned no observations for {spec['stats_data_id']}.")
    return {
        **spec,
        "observations": observations,
        "provider_updated": observations[-1]["date"],
        "api_url": ESTAT_BASE,
    }
