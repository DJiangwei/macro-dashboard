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

from datetime import date, timedelta
from email.utils import parsedate_to_datetime
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
    target_month_length = monthrange(year, month)[1]
    # This codebase's quarterly/annual dates are always the *last day* of
    # their period (e.g. Mar 31, Jun 30, Sep 30, Dec 31 for quarter-ends),
    # not a fixed day-of-month. min(value.day, target_month_length) is only
    # correct when value.day exceeds the target month's length; it silently
    # rounds down a valid end-of-period date otherwise (e.g. shifting Jun 30
    # back one quarter must land on Mar 31, not Mar 30 -- min(30, 31) gives
    # the wrong answer because 30 never exceeded March's own length). So an
    # end-of-month source date always maps to the target month's own last
    # day; any other convention (e.g. day=1 for monthly) is preserved via
    # the min() clamp as before.
    if value.day == monthrange(value.year, value.month)[1]:
        day = target_month_length
    else:
        day = min(value.day, target_month_length)
    return date(year, month, day)


def _latest_observation(series: dict[str, Any]) -> dict[str, Any] | None:
    observations = series.get("observations") or []
    if not observations:
        return None
    return observations[-1]


from xml.etree import ElementTree as ET
from calendar import monthrange
from threading import Lock
from zipfile import ZipFile
from csv import DictReader
from io import StringIO
import time

SARB_BASE = "https://custom.resbank.co.za/SarbWebApi/WebIndicators/Shared/GetTimeseriesObservations"
FRED_GRAPH_URL = "https://fred.stlouisfed.org/graph/fredgraph.csv"
FRED_API_URL = "https://api.stlouisfed.org/fred/series/observations"
FRED_SERIES_URL = "https://api.stlouisfed.org/fred/series"
BOE_BANK_RATE_URL = "https://www.bankofengland.co.uk/boeapps/database/Bank-Rate.asp?hl=en-GB"
BOE_IADB_URL = "https://www.bankofengland.co.uk/boeapps/database/_iadb-fromshowcolumns.asp"
ONS_TIMESERIES_BASE = "https://www.ons.gov.uk"
BINARY_DOWNLOAD_CACHE_LOCK = Lock()
DISTRIBUTION_CACHE_LOCK = Lock()

MONTHS = {
    "jan": 1,
    "january": 1,
    "feb": 2,
    "february": 2,
    "mar": 3,
    "march": 3,
    "apr": 4,
    "april": 4,
    "may": 5,
    "jun": 6,
    "june": 6,
    "jul": 7,
    "july": 7,
    "aug": 8,
    "august": 8,
    "sep": 9,
    "september": 9,
    "oct": 10,
    "october": 10,
    "nov": 11,
    "november": 11,
    "dec": 12,
    "december": 12,
}


TREASURY_AUCTIONS_URL = "https://api.fiscaldata.treasury.gov/services/api/fiscal_service/v1/accounting/od/auctions_query"
BLS_API_URL = "https://api.bls.gov/publicAPI/v2/timeseries/data/"
import threading
import pathlib
ROOT = pathlib.Path(__file__).resolve().parents[2]
BLS_BED_CACHE_PATH = ROOT / "data" / "us_bls_bed_cache.json"
BLS_LOCK = threading.Lock()



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
    }
    for key in ["cdTab", "cdCat01", "cdCat02", "cdCat03", "cdArea"]:
        spec_key = "estat_" + key.replace("cd", "").lower()
        if spec_key in spec:
            params[key] = str(spec[spec_key])

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

def fetch_eastmoney(session: requests.Session, spec: dict[str, Any]) -> dict[str, Any]:
    url = "https://datacenter-web.eastmoney.com/api/data/v1/get"
    params = {
        "columns": str(spec["columns"]),
        "pageNumber": "1",
        "pageSize": str(spec.get("page_size", 500)),
        "sortColumns": str(spec.get("sort_columns", "REPORT_DATE")),
        "sortTypes": "-1",
        "source": "WEB",
        "client": "WEB",
        "reportName": str(spec["report_name"]),
    }
    if "filter" in spec:
        params["filter"] = str(spec["filter"])

    response = session.get(url, params=params, headers={"User-Agent": USER_AGENT}, timeout=(5, 45))
    response.raise_for_status()
    payload = response.json()
    if payload.get("code") != 0:
        raise RuntimeError(f"Eastmoney API error: {payload.get('message')}")

    data = payload.get("result", {})
    if data is None:
        data = {}
    rows = data.get("data") or []

    date_column = spec.get("date_column", "REPORT_DATE")
    value_column = spec["value_column"]

    observations = []
    for row in rows:
        raw_date = str(row.get(date_column) or "")
        if len(raw_date) >= 10:
            obs_date = raw_date[:10]
        else:
            continue

        raw_value = row.get(value_column)
        if raw_value is None or raw_value == "":
            continue
        try:
            value = float(raw_value)
        except (TypeError, ValueError):
            continue

        observations.append({"date": obs_date, "value": value})

    observations.sort(key=lambda item: item["date"])

    start_date = str(spec.get("start_date") or "")
    if start_date:
        observations = [o for o in observations if o["date"] >= start_date]

    return {
        **spec,
        "observations": observations,
        "provider_updated": observations[-1]["date"] if observations else "",
        "api_url": url,
    }
import time

SARB_BASE = "https://custom.resbank.co.za/SarbWebApi/WebIndicators/Shared/GetTimeseriesObservations"
FRED_GRAPH_URL = "https://fred.stlouisfed.org/graph/fredgraph.csv"
FRED_API_URL = "https://api.stlouisfed.org/fred/series/observations"
FRED_SERIES_URL = "https://api.stlouisfed.org/fred/series"
BOE_BANK_RATE_URL = "https://www.bankofengland.co.uk/boeapps/database/Bank-Rate.asp?hl=en-GB"
BOE_IADB_URL = "https://www.bankofengland.co.uk/boeapps/database/_iadb-fromshowcolumns.asp"
ONS_TIMESERIES_BASE = "https://www.ons.gov.uk"
BINARY_DOWNLOAD_CACHE_LOCK = Lock()
DISTRIBUTION_CACHE_LOCK = Lock()

MONTHS = {
    "jan": 1,
    "january": 1,
    "feb": 2,
    "february": 2,
    "mar": 3,
    "march": 3,
    "apr": 4,
    "april": 4,
    "may": 5,
    "jun": 6,
    "june": 6,
    "jul": 7,
    "july": 7,
    "aug": 8,
    "august": 8,
    "sep": 9,
    "september": 9,
    "oct": 10,
    "october": 10,
    "nov": 11,
    "november": 11,
    "dec": 12,
    "december": 12,
}


TREASURY_AUCTIONS_URL = "https://api.fiscaldata.treasury.gov/services/api/fiscal_service/v1/accounting/od/auctions_query"
BLS_API_URL = "https://api.bls.gov/publicAPI/v2/timeseries/data/"
import threading
import pathlib
ROOT = pathlib.Path(__file__).resolve().parents[2]
BLS_BED_CACHE_PATH = ROOT / "data" / "us_bls_bed_cache.json"
BLS_LOCK = threading.Lock()

import requests

def fetch_nbs_api(session: requests.Session, spec: dict) -> dict:
    url = "https://data.stats.gov.cn/easyquery.htm"
    # Example spec:
    # dbcode: "hgyd"
    # indicator_id: "A010101"
    # period: "LAST120"
    indicator_id = spec["indicator_id"]
    dbcode = spec.get("dbcode", "hgyd")
    period = spec.get("period", "LAST120")

    # We must provide a user-agent to avoid immediate rejection from basic filters
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "X-Requested-With": "XMLHttpRequest",
    }

    # The NBS API sometimes expects a pre-flight cookie or it will return 403 UrlACL/JS challenge.
    # We first hit the home page to get a JSESSIONID or similar cookies.
    session.get("https://data.stats.gov.cn/", headers=headers, verify=False, timeout=(5, 10))

    k1 = str(int(time.time() * 1000))
    params = {
        "m": "QueryData",
        "dbcode": dbcode,
        "rowcode": "zb",
        "colcode": "sj",
        "wds": "[]",
        "dfwds": f'[{{"wdcode":"zb","valuecode":"{indicator_id}"}},{{"wdcode":"sj","valuecode":"{period}"}}]',
        "k1": k1,
    }

    response = session.get(url, params=params, headers=headers, verify=False, timeout=(5, 30))
    # We don't raise immediately because 403 might happen in CI, we want a clean error message
    if response.status_code == 403:
        raise RuntimeError("NBS API returned 403 Forbidden. This is typically caused by geoblocking (UrlACL) for non-China IP addresses.")
    response.raise_for_status()

    payload = response.json()
    if payload.get("returncode") != 200:
        raise RuntimeError(f"NBS API error: {payload.get('returndata', {}).get('errormsg', 'Unknown error')}")

    datanodes = payload.get("returndata", {}).get("datanodes", [])
    if not datanodes:
        raise RuntimeError(f"NBS API returned no data nodes for indicator {indicator_id}")

    observations = []
    for node in datanodes:
        # node format: {"code": "zb.A020101_sj.202301", "data": {"data": 123.4, "hasdata": True}}
        has_data = node.get("data", {}).get("hasdata", False)
        if not has_data:
            continue

        value = node.get("data", {}).get("data")
        if value is None:
            continue

        # extract period from code, e.g., "zb.A020101_sj.202301" -> "202301"
        code_str = node.get("code", "")
        # The time code is after "sj."
        if "_sj." not in code_str:
            continue
        time_part = code_str.split("_sj.")[-1]

        # parse time_part (YYYYMM or YYYYCQ or YYYY)
        if len(time_part) == 6: # YYYYMM
            year, month = time_part[:4], time_part[4:]
            obs_date = f"{year}-{month}-01"
        elif len(time_part) == 5 and time_part.endswith("A") or time_part.endswith("B") or time_part.endswith("C") or time_part.endswith("D"):
            # Quarters in NBS: A=Q1, B=Q2, C=Q3, D=Q4 (wait, is it? We need to verify).
            # Actually, NBS quarters are usually "2023A", "2023B", "2023C", "2023D".
            year = time_part[:4]
            q_map = {"A": "01", "B": "04", "C": "07", "D": "10"}
            obs_date = f"{year}-{q_map.get(time_part[-1], '01')}-01"
        elif len(time_part) == 4: # YYYY
            obs_date = f"{time_part}-12-01"
        else:
            continue

        observations.append({"date": obs_date, "value": float(value)})

    observations.sort(key=lambda item: item["date"])

    start_date = str(spec.get("start_date") or "")
    if start_date:
        observations = [o for o in observations if o["date"] >= start_date]

    return {
        **spec,
        "observations": observations,
        "provider_updated": observations[-1]["date"] if observations else "",
        "api_url": url,
    }


def _lag_for_frequency(frequency: str) -> int:
    frequency = str(frequency or '').lower()
    if frequency == 'weekly':
        return 52
    if frequency == 'quarterly':
        return 4
    if frequency == 'annual':
        return 1
    return 12

def _parse_obs_date(value: Any) -> date | None:
    try:
        return date.fromisoformat(str(value)[:10])
    except (TypeError, ValueError):
        return None

def _lookup_base(by_date: dict[str, Any], frequency: str, periods: int, item_date: date) -> float | None:
    """Return the value observed exactly `periods` calendar periods before
    `item_date`, or None if that exact date has no observation.

    Looks up the base by its expected calendar date rather than a fixed
    array offset — see shift_calendar_periods for why: one interior gap
    would otherwise misalign every later point permanently, not just the
    one next to the gap.
    """
    expected_date = shift_calendar_periods(item_date, frequency, periods)
    return by_date.get(expected_date.isoformat())

def _apply_us_transform(series: dict[str, Any]) -> dict[str, Any]:
    transform = series.get('transform')
    observations = list(series.get('observations') or [])
    if not transform or not observations:
        return series
    frequency = str(series.get('frequency', ''))
    by_date: dict[str, float] = {}
    for item in observations:
        parsed = _parse_obs_date(item.get('date'))
        if parsed is not None:
            by_date[parsed.isoformat()] = float(item['value'])
    transformed: list[dict[str, Any]] = []
    if transform == 'yoy_pct':
        lag = _lag_for_frequency(frequency)
        for item in observations:
            item_date = _parse_obs_date(item.get('date'))
            if item_date is None:
                continue
            base = _lookup_base(by_date, frequency, lag, item_date)
            if base is None or base == 0:
                continue
            value = float(item['value'])
            transformed.append({'date': item['date'], 'value': (value / base - 1.0) * 100.0})
    elif transform == 'diff':
        for item in observations:
            item_date = _parse_obs_date(item.get('date'))
            if item_date is None:
                continue
            base = _lookup_base(by_date, frequency, 1, item_date)
            if base is None:
                continue
            transformed.append({'date': item['date'], 'value': float(item['value']) - base})
    elif transform == 'pct_change':
        for item in observations:
            item_date = _parse_obs_date(item.get('date'))
            if item_date is None:
                continue
            base = _lookup_base(by_date, frequency, 1, item_date)
            if base is None or base == 0:
                continue
            value = float(item['value'])
            transformed.append({'date': item['date'], 'value': (value / base - 1.0) * 100.0})
    else:
        return {**series, 'observations': [], 'quality_status': 'unavailable', 'quality_notes': [f'Unknown transform: {transform}.']}
    return {**series, 'observations': transformed}

def _fred_graph_observations_us(session: requests.Session, spec: dict[str, Any], read_timeout: int) -> tuple[list[dict[str, Any]], str]:
    params = {'id': spec['series']}
    if spec.get('start_date'):
        params['cosd'] = spec['start_date']
    response = session.get(FRED_GRAPH_URL, params=params, headers={'User-Agent': USER_AGENT, 'Accept': 'text/csv,text/plain,*/*'}, timeout=(5, read_timeout))
    response.raise_for_status()
    rows = csv.DictReader(io.StringIO(response.text))
    observations: list[dict[str, Any]] = []
    for row in rows:
        raw_value = row.get(spec['series'])
        if raw_value in (None, '', '.'):
            continue
        try:
            value = float(raw_value)
        except (TypeError, ValueError):
            continue
        observations.append({'date': str(row.get('observation_date')), 'value': value})
    updated = response.headers.get('Last-Modified', '')
    return (observations, updated)

def fetch_fred_us(session: requests.Session, spec: dict[str, Any]) -> dict[str, Any]:
    if os.environ.get('FRED_API_KEY', '').strip():
        return fetch_fred(session, spec)
    last_error: Exception | None = None
    for read_timeout in (8, 16):
        try:
            observations, provider_updated = _fred_graph_observations_us(session, spec, read_timeout)
            if not observations:
                raise RuntimeError('FRED graph returned no observations.')
            if provider_updated:
                try:
                    provider_updated = parsedate_to_datetime(provider_updated).date().isoformat()
                except (TypeError, ValueError):
                    provider_updated = str(provider_updated)
            return {**spec, 'observations': observations, 'provider_updated': provider_updated or (observations[-1]['date'] if observations else ''), 'api_url': FRED_GRAPH_URL}
        except Exception as exc:
            last_error = exc
    raise last_error or RuntimeError('FRED graph fetch failed.')

def _numeric(value: Any) -> float | None:
    if value in (None, '', 'null', '.'):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None

def _bls_period_to_date(year: str, period: str) -> str | None:
    if not period.startswith('Q'):
        return None
    quarter_month = {'Q01': '01', 'Q02': '04', 'Q03': '07', 'Q04': '10'}.get(period)
    if not quarter_month:
        return None
    return f'{year}-{quarter_month}-01'

def _bls_config_specs() -> list[dict[str, Any]]:
    config = _load_config()
    return [item for item in config.get('indicators', []) if item.get('fetcher') == 'bls_api']

def _load_bls_bed_cache() -> dict[str, Any]:
    if not BLS_BED_CACHE_PATH.exists():
        return {}
    try:
        return json.loads(BLS_BED_CACHE_PATH.read_text())
    except json.JSONDecodeError:
        return {}

def _write_bls_bed_cache(observations_by_series: dict[str, list[dict[str, Any]]]) -> None:
    if not observations_by_series or any((not values for values in observations_by_series.values())):
        return
    BLS_BED_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload = {'generated': datetime.now(UTC).isoformat(), 'source': 'BLS public API last-good cache for Business Employment Dynamics series', 'source_url': BLS_API_URL, 'series': observations_by_series}
    BLS_BED_CACHE_PATH.write_text(json.dumps(payload, indent=2, sort_keys=True))

def _fetch_bls_batch(session: requests.Session, specs: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    start_year = min((int(str(item.get('start_date', '1992-01-01'))[:4]) for item in specs))
    end_year = datetime.now(UTC).year
    series_ids = sorted({str(item['series']) for item in specs})
    registration_key = os.environ.get('BLS_API_KEY', '').strip()
    observations_by_series: dict[str, dict[str, float]] = {series_id: {} for series_id in series_ids}
    chunk_years = 20 if registration_key else 10
    for chunk_start in range(start_year, end_year + 1, chunk_years):
        chunk_end = min(chunk_start + chunk_years - 1, end_year)
        payload_body: dict[str, Any] = {'seriesid': series_ids, 'startyear': str(chunk_start), 'endyear': str(chunk_end)}
        if registration_key:
            payload_body['registrationkey'] = registration_key
        last_error: Exception | None = None
        for attempt in range(3):
            try:
                response = session.post(BLS_API_URL, json=payload_body, headers={'User-Agent': USER_AGENT, 'Accept': 'application/json'}, timeout=(5, 30))
                response.raise_for_status()
                payload = response.json()
                if payload.get('status') != 'REQUEST_SUCCEEDED':
                    raise RuntimeError('; '.join(payload.get('message') or ['BLS API request failed.']))
                break
            except Exception as exc:
                last_error = exc
                if attempt < 2:
                    time.sleep(1.0 * 2 ** attempt)
        else:
            raise last_error or RuntimeError('BLS API request failed.')
        for series_payload in payload.get('Results', {}).get('series') or []:
            series_id = str(series_payload.get('seriesID', ''))
            if series_id not in observations_by_series:
                continue
            bucket = observations_by_series[series_id]
            for row in series_payload.get('data') or []:
                obs_date = _bls_period_to_date(str(row.get('year', '')), str(row.get('period', '')))
                value = _numeric(row.get('value'))
                if not obs_date or value is None:
                    continue
                bucket[obs_date] = value
        time.sleep(0.25)
    result = {series_id: [{'date': obs_date, 'value': value} for obs_date, value in sorted(values.items())] for series_id, values in observations_by_series.items()}
    _write_bls_bed_cache(result)
    return result

def fetch_bls_api(session: requests.Session, spec: dict[str, Any]) -> dict[str, Any]:
    global BLS_BATCH_ERROR
    series_id = str(spec['series'])
    with BLS_LOCK:
        if series_id not in BLS_CACHE and (not BLS_BATCH_ERROR):
            try:
                BLS_CACHE.update(_fetch_bls_batch(session, _bls_config_specs()))
            except Exception as exc:
                BLS_BATCH_ERROR = str(exc)
        if BLS_BATCH_ERROR:
            cache_payload = _load_bls_bed_cache()
            observations = list((cache_payload.get('series') or {}).get(series_id) or [])
            if observations:
                cache_date = str(cache_payload.get('generated') or '')[:10]
                caveat_en = (str(spec.get('caveat_en') or '').rstrip() + ' Live BLS API quota was unavailable in this run; rendering the last-good official BED cache.').strip()
                caveat_zh = (str(spec.get('caveat_zh') or '').rstrip() + ' 本次运行BLS实时API额度不可用；当前渲染最近一次验证成功的官方BED缓存。').strip()
                return {**spec, 'observations': observations, 'provider_updated': cache_date or observations[-1]['date'], 'api_url': BLS_API_URL, 'caveat_en': caveat_en, 'caveat_zh': caveat_zh}
            raise RuntimeError(BLS_BATCH_ERROR)
        observations = list(BLS_CACHE.get(series_id) or [])
    start_date = str(spec.get('start_date', ''))
    if start_date:
        observations = [item for item in observations if str(item['date']) >= start_date]
    if not observations:
        raise RuntimeError(f'BLS API returned no observations for {series_id}.')
    return {**spec, 'observations': observations, 'provider_updated': observations[-1]['date'], 'api_url': BLS_API_URL}

def fetch_treasury_auctions(session: requests.Session, spec: dict[str, Any]) -> dict[str, Any]:
    fields = ['auction_date', 'security_type', 'total_accepted', 'total_tendered', 'bid_to_cover_ratio', 'high_yield', 'high_investment_rate']
    filters = [f"auction_date:gte:{spec.get('start_date', '2018-01-01')}", 'total_accepted:gt:0']
    security_types = list(spec.get('security_types') or [])
    if len(security_types) == 1:
        filters.append(f'security_type:eq:{security_types[0]}')
    elif security_types:
        filters.append(f"security_type:in:({','.join(security_types)})")
    rows: list[dict[str, Any]] = []
    page_number = 1
    total_pages = 1
    while page_number <= total_pages:
        response = session.get(TREASURY_AUCTIONS_URL, params={'fields': ','.join(fields), 'filter': ','.join(filters), 'page[size]': int(spec.get('page_size', 5000)), 'page[number]': page_number, 'sort': 'auction_date'}, headers={'User-Agent': USER_AGENT, 'Accept': 'application/json'}, timeout=(5, 30))
        response.raise_for_status()
        payload = response.json()
        rows.extend(payload.get('data') or [])
        total_pages = int(payload.get('meta', {}).get('total-pages') or page_number)
        page_number += 1
    aggregate = str(spec.get('aggregate', 'monthly_sum'))
    metric = str(spec.get('metric', 'total_accepted'))
    scale = float(spec.get('scale', 1))
    buckets: dict[str, dict[str, float]] = {}
    for row in rows:
        auction_date = str(row.get('auction_date') or '')
        if len(auction_date) < 7:
            continue
        month = f'{auction_date[:7]}-01'
        bucket = buckets.setdefault(month, {'value': 0.0, 'count': 0.0, 'numerator': 0.0, 'denominator': 0.0})
        if aggregate == 'monthly_weighted_bid_to_cover':
            numerator = _numeric(row.get('total_tendered'))
            denominator = _numeric(row.get('total_accepted'))
            if numerator is None or denominator in (None, 0):
                continue
            bucket['numerator'] += numerator
            bucket['denominator'] += denominator
        else:
            value = _numeric(row.get(metric))
            if value is None:
                continue
            bucket['value'] += value
            bucket['count'] += 1
    observations: list[dict[str, Any]] = []
    for month, bucket in sorted(buckets.items()):
        if aggregate == 'monthly_weighted_bid_to_cover':
            denominator = bucket['denominator']
            if denominator == 0:
                continue
            value = bucket['numerator'] / denominator
        elif aggregate == 'monthly_average':
            count = bucket['count']
            if count == 0:
                continue
            value = bucket['value'] / count
        else:
            value = bucket['value']
        observations.append({'date': month, 'value': value / scale})
    if not observations:
        raise RuntimeError('Treasury FiscalData returned no completed auction observations.')
    return {**spec, 'observations': observations, 'provider_updated': observations[-1]['date'], 'api_url': TREASURY_AUCTIONS_URL}

def _clean_text(value: str) -> str:
    return re.sub('\\s+', ' ', value or '').strip()

def _parse_date(value: str) -> date | None:
    value = _clean_text(str(value or ''))
    value = re.sub('\\s+\\[[^\\]]+\\]$', '', value).strip()
    quarter_match = re.match('^(\\d{4})\\s+Q([1-4])$', value, flags=re.I)
    if quarter_match:
        year = int(quarter_match.group(1))
        month = int(quarter_match.group(2)) * 3
        return date(year, month, monthrange(year, month)[1])
    quarter_range_match = re.match('^([A-Za-z]{3,9})\\s+to\\s+([A-Za-z]{3,9})\\s+(\\d{4})$', value, flags=re.I)
    if quarter_range_match:
        year = int(quarter_range_match.group(3))
        month = MONTHS.get(quarter_range_match.group(2).lower())
        if month:
            return date(year, month, monthrange(year, month)[1])
    month_match = re.match('^(\\d{4})\\s+([A-Za-z]{3,9})$', value)
    if month_match:
        year = int(month_match.group(1))
        month = MONTHS.get(month_match.group(2).lower())
        if month:
            return date(year, month, 1)
    month_first_match = re.match('^([A-Za-z]{3,9})\\s+(\\d{4})$', value)
    if month_first_match:
        month = MONTHS.get(month_first_match.group(1).lower())
        if month:
            return date(int(month_first_match.group(2)), month, 1)
    for fmt, length in (('%Y-%m-%d', 10), ('%Y-%m', 7), ('%Y', 4)):
        try:
            return datetime.strptime(value[:length], fmt).date()
        except ValueError:
            continue
    for fmt in ('%d %b %Y', '%d %B %Y', '%d %b %y', '%d/%m/%Y', '%b-%y', '%B-%y'):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    return None

def _normalise_date(value: str) -> str | None:
    parsed = _parse_date(value)
    return parsed.isoformat() if parsed else None

def _normalise_obr_period(value: str) -> str | None:
    value = _clean_text(str(value or ''))
    financial_year_match = re.match('^(\\d{4})-(\\d{2})$', value)
    if financial_year_match:
        return date(int(financial_year_match.group(1)) + 1, 3, 31).isoformat()
    quarter_match = re.match('^(\\d{4})\\s*Q([1-4])$', value, flags=re.I)
    if quarter_match:
        year = int(quarter_match.group(1))
        month = int(quarter_match.group(2)) * 3
        return date(year, month, monthrange(year, month)[1]).isoformat()
    return None

def _date_matches_frequency(value: str, frequency: str) -> bool:
    """Avoid treating annual or quarterly rows as monthly data in mixed ONS tables."""
    value = _clean_text(value)
    value = re.sub('\\s+\\[[^\\]]+\\]$', '', value).strip()
    frequency = frequency.lower()
    if frequency == 'monthly':
        return bool(re.match('^[A-Za-z]{3,9}[- ]\\d{2,4}$', value) or re.match('^\\d{4}\\s+[A-Za-z]{3,9}$', value))
    if frequency == 'quarterly':
        return bool(re.match('^\\d{4}\\s+Q[1-4]$', value, flags=re.I) or re.match('^[A-Za-z]{3,9}\\s+to\\s+[A-Za-z]{3,9}\\s+\\d{4}$', value, flags=re.I))
    if frequency == 'annual':
        return bool(re.match('^\\d{4}$', value))
    return True

def _start_filter(observations: list[dict[str, Any]], start_date: str | None) -> list[dict[str, Any]]:
    if not start_date:
        return observations
    start = _parse_date(start_date)
    if not start:
        return observations
    return [item for item in observations if (_parse_date(str(item['date'])) or date.min) >= start]

def _fred_api_observations(session: requests.Session, spec: dict[str, Any]) -> tuple[list[dict[str, Any]], str]:
    api_key = os.environ.get('FRED_API_KEY', '').strip()
    if not api_key:
        return ([], '')
    params = {'series_id': spec['series'], 'api_key': api_key, 'file_type': 'json'}
    if spec.get('start_date'):
        params['observation_start'] = spec['start_date']
    last_error: Exception | None = None
    for attempt in range(5):
        try:
            response = session.get(FRED_API_URL, params=params, timeout=(4, 16))
            response.raise_for_status()
            break
        except Exception as exc:
            last_error = exc
            if attempt < 4:
                time.sleep(0.7 * 2 ** attempt)
    else:
        raise last_error or RuntimeError('FRED API request failed.')
    payload = response.json()
    observations: list[dict[str, Any]] = []
    for row in payload.get('observations', []):
        raw_value = row.get('value')
        if raw_value in (None, '', '.'):
            continue
        try:
            value = float(raw_value)
        except (TypeError, ValueError):
            continue
        observations.append({'date': str(row.get('date')), 'value': value})
    updated = response.headers.get('Last-Modified', '')
    return (observations, updated)

def _fred_api_series_updated(session: requests.Session, series_id: str) -> str:
    api_key = os.environ.get('FRED_API_KEY', '').strip()
    if not api_key:
        return ''
    params = {'series_id': series_id, 'api_key': api_key, 'file_type': 'json'}
    try:
        response = session.get(FRED_SERIES_URL, params=params, timeout=(4, 12))
        response.raise_for_status()
        payload = response.json()
    except Exception:
        return ''
    series = payload.get('seriess') or []
    if not series:
        return ''
    return str(series[0].get('last_updated') or '')

def _fred_graph_observations(session: requests.Session, spec: dict[str, Any]) -> tuple[list[dict[str, Any]], str]:
    params = {'id': spec['series']}
    if spec.get('start_date'):
        params['cosd'] = spec['start_date']
    response = session.get(FRED_GRAPH_URL, params=params, timeout=(4, 12))
    response.raise_for_status()
    rows = csv.DictReader(io.StringIO(response.text))
    observations: list[dict[str, Any]] = []
    for row in rows:
        raw_value = row.get(spec['series'])
        if raw_value in (None, '', '.'):
            continue
        try:
            value = float(raw_value)
        except (TypeError, ValueError):
            continue
        observations.append({'date': str(row.get('observation_date')), 'value': value})
    updated = response.headers.get('Last-Modified', '')
    return (observations, updated)

def _provider_updated_date(value: str) -> str:
    value = str(value or '').strip()
    if not value:
        return ''
    if re.match('^\\d{4}-\\d{2}-\\d{2}', value):
        return value[:10]
    try:
        return parsedate_to_datetime(value).date().isoformat()
    except (TypeError, ValueError):
        return value

def _apply_uk_transform(observations: list[dict[str, Any]], spec: dict[str, Any]) -> list[dict[str, Any]]:
    transform = str(spec.get('transform') or '')
    if transform in {'divide_1k', 'divide_1m', 'divide_1bn', 'decimal_to_pct'}:
        divisor = {'divide_1k': 1000, 'divide_1m': 1000000, 'divide_1bn': 1000000000}.get(transform, 1)
        multiplier = 100 if transform == 'decimal_to_pct' else 1
        return [{**item, 'value': float(item['value']) / divisor * multiplier} for item in observations if item.get('value') is not None]
    if transform not in {'yoy', 'qoq_pct', 'mom_pct'}:
        return observations
    frequency = str(spec.get('frequency', '')).lower()
    periods = 1 if transform in {'qoq_pct', 'mom_pct'} else 12 if frequency == 'monthly' else 4 if frequency == 'quarterly' else 1
    by_date: dict[str, float] = {}
    for item in observations:
        parsed = _parse_date(str(item.get('date', '')))
        if parsed is not None:
            by_date[parsed.isoformat()] = float(item['value'])
    transformed: list[dict[str, Any]] = []
    for item in observations:
        item_date = _parse_date(str(item.get('date', '')))
        if item_date is None:
            continue
        expected_base_date = shift_calendar_periods(item_date, frequency, periods)
        base = by_date.get(expected_base_date.isoformat())
        if base in (0, None):
            continue
        try:
            value = (float(item['value']) / float(base) - 1.0) * 100.0
        except (TypeError, ValueError, ZeroDivisionError):
            continue
        transformed.append({'date': item['date'], 'value': value})
    return transformed

def fetch_fred(session: requests.Session, spec: dict[str, Any]) -> dict[str, Any]:
    observations: list[dict[str, Any]]
    provider_updated: str
    used_api = False
    try:
        observations, provider_updated = _fred_api_observations(session, spec)
        used_api = bool(observations)
    except Exception:
        observations, provider_updated = ([], '')
    if not observations:
        observations, provider_updated = _fred_graph_observations(session, spec)
    elif used_api:
        provider_updated = _fred_api_series_updated(session, str(spec['series'])) or provider_updated
    observations = _apply_uk_transform(_start_filter(observations, spec.get('start_date')), spec)
    provider_updated = _provider_updated_date(provider_updated)
    return {**spec, 'observations': observations, 'provider_updated': provider_updated or (observations[-1]['date'] if observations else ''), 'api_url': FRED_API_URL if os.environ.get('FRED_API_KEY') else FRED_GRAPH_URL}

def _ons_path(spec: dict[str, Any]) -> str:
    path = str(spec.get('ons_path') or '').strip()
    if path:
        return path
    cdid = str(spec['series']).lower()
    dataset = str(spec.get('dataset') or spec.get('dataset_id') or '').lower()
    return f'/timeseries/{cdid}/{dataset}/data'

def fetch_ons_timeseries(session: requests.Session, spec: dict[str, Any]) -> dict[str, Any]:
    path = _ons_path(spec)
    url = f'{ONS_TIMESERIES_BASE}{path}' if path.startswith('/') else path
    response = session.get(url, headers={'User-Agent': USER_AGENT, 'Accept': 'application/json'}, timeout=(4, 20))
    response.raise_for_status()
    payload = response.json()
    frequency = str(spec.get('frequency', '')).lower()
    rows_by_frequency = {'monthly': payload.get('months') or [], 'quarterly': payload.get('quarters') or [], 'annual': payload.get('years') or []}
    if frequency not in rows_by_frequency:
        raise ValueError(f"ONS series {spec.get('series')!r} ({spec.get('id')!r}) declares unsupported frequency {frequency!r}; expected one of {sorted(rows_by_frequency)}.")
    rows = rows_by_frequency[frequency]
    if not rows:
        available = sorted((key for key in ('months', 'quarters', 'years') if payload.get(key)))
        raise ValueError(f"ONS series {spec.get('series')!r} ({spec.get('id')!r}) declares frequency {frequency!r} but the ONS payload has no {frequency!r} observations at {url}; payload only carries {available or ['none']}. Check the declared frequency against the ONS dataset before relabeling or repointing this indicator.")
    observations: list[dict[str, Any]] = []
    provider_updated = ''
    for row in rows:
        raw_value = row.get('value')
        if raw_value in (None, '', '.'):
            continue
        obs_date = _normalise_date(str(row.get('date') or row.get('label') or ''))
        if not obs_date:
            continue
        try:
            value = float(str(raw_value).replace(',', ''))
        except (TypeError, ValueError):
            continue
        provider_updated = str(row.get('updateDate') or provider_updated)
        observations.append({'date': obs_date, 'value': value})
    observations.sort(key=lambda item: item['date'])
    observations = _apply_uk_transform(_start_filter(observations, spec.get('start_date')), spec)
    description = payload.get('description') or {}
    provider_updated = str(description.get('releaseDate') or provider_updated or '')
    if provider_updated:
        provider_updated = provider_updated[:10]
    return {**spec, 'observations': observations, 'provider_updated': provider_updated or (observations[-1]['date'] if observations else ''), 'api_url': url, 'current_value': str(description.get('number') or '')}

def _boe_date_param(start_date: str | None) -> str:
    parsed = _parse_date(start_date or '')
    if not parsed:
        parsed = date(1997, 1, 1)
    return parsed.strftime('%d/%b/%Y')

def fetch_boe_iadb(session: requests.Session, spec: dict[str, Any]) -> dict[str, Any]:
    series_code = str(spec['series']).strip()
    params = {'csv.x': 'yes', 'Datefrom': _boe_date_param(spec.get('start_date')), 'Dateto': 'now', 'SeriesCodes': series_code, 'CSVF': 'TN', 'UsingCodes': 'Y', 'VPD': 'Y', 'VFD': 'N'}
    response = session.get(BOE_IADB_URL, params=params, headers={'User-Agent': USER_AGENT}, timeout=(4, 20))
    response.raise_for_status()
    if '<html' in response.text[:200].lower():
        raise RuntimeError(f'BoE IADB rejected series code {series_code}.')
    rows = csv.DictReader(io.StringIO(response.text))
    observations: list[dict[str, Any]] = []
    for row in rows:
        raw_value = row.get(series_code)
        if raw_value in (None, '', '.'):
            continue
        obs_date = _normalise_date(str(row.get('DATE') or ''))
        if not obs_date:
            continue
        try:
            value = float(str(raw_value).replace(',', ''))
        except (TypeError, ValueError):
            continue
        observations.append({'date': obs_date, 'value': value})
    observations.sort(key=lambda item: item['date'])
    observations = _apply_uk_transform(_start_filter(observations, spec.get('start_date')), spec)
    return {**spec, 'observations': observations, 'provider_updated': observations[-1]['date'] if observations else '', 'api_url': response.url}

def _parse_boe_short_date(value: str) -> str | None:
    try:
        dt = datetime.strptime(value, '%d %b %y').date()
    except ValueError:
        return None
    return dt.isoformat()

def fetch_boe_bank_rate(session: requests.Session, spec: dict[str, Any]) -> dict[str, Any]:
    response = session.get(BOE_BANK_RATE_URL, headers={'User-Agent': USER_AGENT, 'Accept': 'text/html,application/xhtml+xml'}, timeout=(4, 12))
    response.raise_for_status()
    rows = re.findall('<tr[^>]*>(.*?)</tr>', response.text, flags=re.S | re.I)
    observations: list[dict[str, Any]] = []
    for row in rows:
        cells = [_clean_text(re.sub('<[^>]+>', ' ', cell)) for cell in re.findall('<t[dh][^>]*>(.*?)</t[dh]>', row, flags=re.S | re.I)]
        if len(cells) < 2 or cells[0].lower().startswith('date'):
            continue
        obs_date = _parse_boe_short_date(cells[0])
        if not obs_date:
            continue
        try:
            value = float(cells[1].replace('%', ''))
        except ValueError:
            continue
        observations.append({'date': obs_date, 'value': value})
    observations.sort(key=lambda item: item['date'])
    observations = _start_filter(observations, spec.get('start_date'))
    current_match = re.search('<p class="stat-figure">([^<]+)</p>', response.text)
    current_value = _clean_text(current_match.group(1)) if current_match else ''
    return {**spec, 'observations': observations, 'provider_updated': observations[-1]['date'] if observations else '', 'api_url': BOE_BANK_RATE_URL, 'current_value': current_value}

def _govuk_distribution_url(session: requests.Session, spec: dict[str, Any], extension: str) -> tuple[str, str]:
    """Return the current GOV.UK distribution URL from page-level JSON-LD metadata."""
    page_url = str(spec.get('source_url') or '').strip()
    if not page_url:
        raise ValueError('GOV.UK fetcher requires source_url.')
    wanted = str(spec.get('distribution_name_contains') or spec.get('csv_label_contains') or '').lower()
    cache_key = (page_url, extension, wanted)
    with DISTRIBUTION_CACHE_LOCK:
        if cache_key in DISTRIBUTION_CACHE:
            return DISTRIBUTION_CACHE[cache_key]
        response = session.get(page_url, headers={'User-Agent': USER_AGENT}, timeout=(4, 20))
        response.raise_for_status()
        page_text = response.text
    candidates: list[dict[str, Any]] = []
    for match in re.findall('<script[^>]+type=["\\\']application/ld\\+json["\\\'][^>]*>(.*?)</script>', page_text, flags=re.S | re.I):
        try:
            payload = json.loads(match)
        except json.JSONDecodeError:
            continue
        items = payload if isinstance(payload, list) else [payload]
        for item in items:
            if isinstance(item, dict):
                distribution = item.get('distribution') or []
                if isinstance(distribution, dict):
                    distribution = [distribution]
                candidates.extend((row for row in distribution if isinstance(row, dict)))
    for candidate in candidates:
        url = str(candidate.get('contentUrl') or candidate.get('url') or '').strip()
        name = str(candidate.get('name') or '').strip()
        if not url or not url.lower().split('?')[0].endswith(extension):
            continue
        if wanted and wanted not in name.lower() and (wanted not in url.lower()):
            continue
        result = (url, name)
        with DISTRIBUTION_CACHE_LOCK:
            DISTRIBUTION_CACHE[cache_key] = result
        return result
    raise RuntimeError(f'No matching GOV.UK {extension} distribution found for {page_url}.')

def _download_binary(session: requests.Session, url: str, timeout: tuple[int, int]=(4, 24)) -> bytes:
    """Cache workbook downloads reused by several indicators in a single build."""
    with BINARY_DOWNLOAD_CACHE_LOCK:
        if url not in BINARY_DOWNLOAD_CACHE:
            response = session.get(url, headers={'User-Agent': USER_AGENT}, timeout=timeout)
            response.raise_for_status()
            BINARY_DOWNLOAD_CACHE[url] = response.content
        return BINARY_DOWNLOAD_CACHE[url]

def _ons_distribution_candidates(session: requests.Session, spec: dict[str, Any], extension: str) -> list[tuple[str, str]]:
    """Return ONS dataset download candidates from JSON-LD plus visible download links."""
    page_url = str(spec.get('source_url') or '').strip()
    if not page_url:
        raise ValueError('ONS dataset fetcher requires source_url.')
    wanted = str(spec.get('distribution_name_contains') or '').lower()
    cache_key = (page_url, extension, wanted)
    with DISTRIBUTION_CACHE_LOCK:
        if cache_key in DISTRIBUTION_CACHE:
            return list(DISTRIBUTION_CACHE[cache_key])
        response = session.get(page_url, headers={'User-Agent': USER_AGENT}, timeout=(4, 20))
        response.raise_for_status()
        page_text = response.text
        candidates: list[tuple[str, str]] = []
        for match in re.findall('<script[^>]+type=["\\\']application/ld\\+json["\\\'][^>]*>(.*?)</script>', page_text, flags=re.S | re.I):
            try:
                payload = json.loads(match)
            except json.JSONDecodeError:
                continue
            items = payload if isinstance(payload, list) else [payload]
            for item in items:
                if not isinstance(item, dict):
                    continue
                distribution = item.get('distribution') or []
                if isinstance(distribution, dict):
                    distribution = [distribution]
                for row in distribution:
                    if not isinstance(row, dict):
                        continue
                    url = str(row.get('contentUrl') or row.get('url') or '').strip()
                    name = str(row.get('name') or row.get('encodingFormat') or '').strip()
                    if url:
                        candidates.append((url, name))
        for href, label in re.findall('href=["\\\']([^"\\\']+)["\\\'][^>]*>(.*?)</a>', page_text, flags=re.S | re.I):
            url = href.strip()
            if url.startswith('/'):
                url = f'{ONS_TIMESERIES_BASE}{url}'
            name = _clean_text(re.sub('<[^>]+>', ' ', label))
            candidates.append((url, name))
        seen: set[str] = set()
        filtered: list[tuple[str, str]] = []
        for url, name in candidates:
            normalized = url.lower().split('#')[0]
            path_part = normalized.split('?')[0]
            if not (path_part.endswith(extension) or extension in normalized) or url in seen:
                continue
            if wanted and wanted not in name.lower() and (wanted not in url.lower()):
                continue
            seen.add(url)
            filtered.append((url, name))
        if not filtered:
            raise RuntimeError(f'No matching ONS {extension} distribution found for {page_url}.')
        DISTRIBUTION_CACHE[cache_key] = tuple(filtered)
        return filtered

def _table_observations(rows: list[list[str]], spec: dict[str, Any], *, header_index: int, date_index: int, value_index: int) -> list[dict[str, Any]]:
    observations: list[dict[str, Any]] = []
    frequency = str(spec.get('frequency', '')).lower()
    for row in rows[header_index + 1:]:
        if len(row) <= max(date_index, value_index):
            continue
        raw_date = str(row[date_index]).strip()
        if not _date_matches_frequency(raw_date, frequency):
            continue
        obs_date = _normalise_date(raw_date)
        raw_value = row[value_index]
        if not obs_date or raw_value in (None, '', '.', '[x]'):
            continue
        try:
            value = float(str(raw_value).replace(',', ''))
        except (TypeError, ValueError):
            continue
        observations.append({'date': obs_date, 'value': value})
    observations.sort(key=lambda item: item['date'])
    return _apply_uk_transform(_start_filter(observations, spec.get('start_date')), spec)

def fetch_govuk_road_fuel(session: requests.Session, spec: dict[str, Any]) -> dict[str, Any]:
    csv_url = str(spec.get('csv_url') or '').strip()
    distribution_name = ''
    if not csv_url:
        csv_url, distribution_name = _govuk_distribution_url(session, spec, '.csv')
    response = session.get(csv_url, headers={'User-Agent': USER_AGENT}, timeout=(4, 20))
    response.raise_for_status()
    rows = csv.DictReader(io.StringIO(response.content.decode('utf-8-sig', errors='replace')))
    date_column = str(spec.get('date_column') or 'Date')
    value_column = str(spec.get('value_column') or '')
    value_contains = str(spec.get('value_column_contains') or '').lower()
    observations: list[dict[str, Any]] = []
    for row in rows:
        if not value_column:
            value_column = next((name for name in row if value_contains and value_contains in name.lower()), '')
        if not value_column:
            raise ValueError('Road-fuel CSV value column could not be inferred.')
        obs_date = _normalise_date(str(row.get(date_column) or ''))
        raw_value = row.get(value_column)
        if not obs_date or raw_value in (None, '', '.'):
            continue
        try:
            value = float(str(raw_value).replace(',', ''))
        except (TypeError, ValueError):
            continue
        observations.append({'date': obs_date, 'value': value})
    observations.sort(key=lambda item: item['date'])
    observations = _apply_uk_transform(_start_filter(observations, spec.get('start_date')), spec)
    return {**spec, 'observations': observations, 'provider_updated': observations[-1]['date'] if observations else '', 'api_url': csv_url, 'distribution_name': distribution_name}

def _xlsx_col_index(cell_ref: str) -> int:
    letters = re.sub('[^A-Z]', '', cell_ref.upper())
    value = 0
    for letter in letters:
        value = value * 26 + (ord(letter) - ord('A') + 1)
    return value - 1

def _xlsx_sheet_rows(content: bytes, sheet_name: str) -> list[list[str]]:
    ns = {'main': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main', 'rel': 'http://schemas.openxmlformats.org/officeDocument/2006/relationships', 'pkg': 'http://schemas.openxmlformats.org/package/2006/relationships'}
    with ZipFile(io.BytesIO(content)) as workbook:
        shared: list[str] = []
        if 'xl/sharedStrings.xml' in workbook.namelist():
            shared_root = ET.fromstring(workbook.read('xl/sharedStrings.xml'))
            for item in shared_root.findall('main:si', ns):
                shared.append(''.join((node.text or '' for node in item.findall('.//main:t', ns))))
        workbook_root = ET.fromstring(workbook.read('xl/workbook.xml'))
        rel_root = ET.fromstring(workbook.read('xl/_rels/workbook.xml.rels'))
        rel_targets = {rel.attrib['Id']: rel.attrib['Target'] for rel in rel_root.findall('pkg:Relationship', ns) if 'Id' in rel.attrib and 'Target' in rel.attrib}
        sheet_path = ''
        for sheet in workbook_root.findall('.//main:sheet', ns):
            if sheet.attrib.get('name') != sheet_name:
                continue
            rel_id = sheet.attrib.get(f"{{{ns['rel']}}}id")
            target = rel_targets.get(str(rel_id), '')
            sheet_path = f"xl/{target.lstrip('/')}" if not target.startswith('xl/') else target
            break
        if not sheet_path:
            raise ValueError(f'Worksheet {sheet_name!r} not found in XLSX.')
        sheet_root = ET.fromstring(workbook.read(sheet_path))
        rows: list[list[str]] = []
        for row in sheet_root.findall('.//main:sheetData/main:row', ns):
            values: list[str] = []
            for cell in row.findall('main:c', ns):
                cell_ref = cell.attrib.get('r', '')
                column_index = _xlsx_col_index(cell_ref)
                while len(values) <= column_index:
                    values.append('')
                raw = cell.find('main:v', ns)
                value = '' if raw is None else str(raw.text or '')
                if cell.attrib.get('t') == 's' and value:
                    value = shared[int(value)]
                values[column_index] = value
            rows.append(values)
        return rows

def fetch_govuk_xlsx_table(session: requests.Session, spec: dict[str, Any]) -> dict[str, Any]:
    xlsx_url = str(spec.get('xlsx_url') or '').strip()
    distribution_name = ''
    if not xlsx_url:
        xlsx_url, distribution_name = _govuk_distribution_url(session, spec, '.xlsx')
    content = _download_binary(session, xlsx_url)
    rows = _xlsx_sheet_rows(content, str(spec['sheet_name']))
    date_column = str(spec.get('date_column') or 'Period')
    value_column = str(spec['value_column'])
    header_index = -1
    date_index = -1
    value_index = -1
    for index, row in enumerate(rows):
        lowered = [str(item).strip().lower() for item in row]
        if date_column.lower() in lowered and value_column.lower() in lowered:
            header_index = index
            date_index = lowered.index(date_column.lower())
            value_index = lowered.index(value_column.lower())
            break
    if header_index < 0:
        raise ValueError(f'Columns {date_column!r}/{value_column!r} not found in XLSX.')
    observations: list[dict[str, Any]] = []
    for row in rows[header_index + 1:]:
        if len(row) <= max(date_index, value_index):
            continue
        obs_date = _normalise_date(str(row[date_index]))
        raw_value = row[value_index]
        if not obs_date or raw_value in (None, '', '.'):
            continue
        try:
            value = float(str(raw_value).replace(',', ''))
        except (TypeError, ValueError):
            continue
        observations.append({'date': obs_date, 'value': value})
    observations.sort(key=lambda item: item['date'])
    observations = _apply_uk_transform(_start_filter(observations, spec.get('start_date')), spec)
    return {**spec, 'observations': observations, 'provider_updated': observations[-1]['date'] if observations else '', 'api_url': xlsx_url, 'distribution_name': distribution_name}

def _ods_cell_text(cell: ET.Element) -> str:
    ns = {'text': 'urn:oasis:names:tc:opendocument:xmlns:text:1.0', 'office': 'urn:oasis:names:tc:opendocument:xmlns:office:1.0'}
    text_values = [''.join(node.itertext()) for node in cell.findall('.//text:p', ns)]
    text = ' '.join((value for value in text_values if value)).strip()
    if text:
        return text
    return cell.attrib.get(f"{{{ns['office']}}}date-value") or cell.attrib.get(f"{{{ns['office']}}}value") or ''

def _ods_sheet_rows(content: bytes, sheet_name: str) -> list[list[str]]:
    ns = {'table': 'urn:oasis:names:tc:opendocument:xmlns:table:1.0'}
    with ZipFile(io.BytesIO(content)) as workbook:
        root = ET.fromstring(workbook.read('content.xml'))
    table_name_key = f"{{{ns['table']}}}name"
    repeat_rows_key = f"{{{ns['table']}}}number-rows-repeated"
    repeat_cols_key = f"{{{ns['table']}}}number-columns-repeated"
    for table in root.findall('.//table:table', ns):
        if table.attrib.get(table_name_key) != sheet_name:
            continue
        rows: list[list[str]] = []
        for row in table.findall('table:table-row', ns):
            row_repeat = min(int(row.attrib.get(repeat_rows_key, '1')), 20)
            values: list[str] = []
            for cell in row.findall('table:table-cell', ns):
                column_repeat = min(int(cell.attrib.get(repeat_cols_key, '1')), 100)
                values.extend([_ods_cell_text(cell)] * column_repeat)
            for _ in range(row_repeat):
                rows.append(values.copy())
        return rows
    raise ValueError(f'Worksheet {sheet_name!r} not found in ODS.')

def fetch_govuk_ods_table(session: requests.Session, spec: dict[str, Any]) -> dict[str, Any]:
    ods_url = str(spec.get('ods_url') or '').strip()
    distribution_name = ''
    if not ods_url:
        ods_url, distribution_name = _govuk_distribution_url(session, spec, '.ods')
    content = _download_binary(session, ods_url)
    if not content.startswith(b'PK'):
        raise RuntimeError('GOV.UK ODS URL did not return a zipped ODS workbook.')
    rows = _ods_sheet_rows(content, str(spec['sheet_name']))
    date_column = str(spec.get('date_column') or 'Month and year')
    value_column = str(spec['value_column'])
    header_index = -1
    date_index = -1
    value_index = -1
    for index, row in enumerate(rows):
        lowered = [str(item).strip().lower() for item in row]
        if date_column.lower() in lowered and value_column.lower() in lowered:
            header_index = index
            date_index = lowered.index(date_column.lower())
            value_index = lowered.index(value_column.lower())
            break
    if header_index < 0:
        raise ValueError(f'Columns {date_column!r}/{value_column!r} not found in ODS.')
    observations = _table_observations(rows, spec, header_index=header_index, date_index=date_index, value_index=value_index)
    return {**spec, 'observations': observations, 'provider_updated': observations[-1]['date'] if observations else '', 'api_url': ods_url, 'distribution_name': distribution_name}

def fetch_ons_xlsx_table(session: requests.Session, spec: dict[str, Any]) -> dict[str, Any]:
    """Fetch a simple ONS xlsx worksheet with a Time period column and one value column."""
    xlsx_candidates = [(str(spec['xlsx_url']), 'configured')] if spec.get('xlsx_url') else _ons_distribution_candidates(session, spec, '.xlsx')
    last_error: Exception | None = None
    for xlsx_url, distribution_name in xlsx_candidates:
        try:
            content = _download_binary(session, xlsx_url)
            if not content.startswith(b'PK'):
                raise RuntimeError('ONS xlsx candidate did not return an XLSX workbook.')
            rows = _xlsx_sheet_rows(content, str(spec['sheet_name']))
            date_column = str(spec.get('date_column') or 'Time period')
            value_column = str(spec['value_column'])
            header_index = -1
            date_index = -1
            value_index = -1
            for index, row in enumerate(rows):
                lowered = [str(item).strip().lower() for item in row]
                if date_column.lower() in lowered and value_column.lower() in lowered:
                    header_index = index
                    date_index = lowered.index(date_column.lower())
                    value_index = lowered.index(value_column.lower())
                    break
            if header_index < 0:
                raise ValueError(f'Columns {date_column!r}/{value_column!r} not found in ONS XLSX.')
            observations = _table_observations(rows, spec, header_index=header_index, date_index=date_index, value_index=value_index)
            return {**spec, 'observations': observations, 'provider_updated': observations[-1]['date'] if observations else '', 'api_url': xlsx_url, 'distribution_name': distribution_name}
        except Exception as exc:
            last_error = exc
            continue
    raise last_error or RuntimeError('No ONS XLSX candidate could be parsed.')

def fetch_ons_horizontal_csv_table(session: requests.Session, spec: dict[str, Any]) -> dict[str, Any]:
    """Fetch an ONS CSV where multiple tables are laid out horizontally."""
    csv_candidates = [(str(spec['csv_url']), 'configured')] if spec.get('csv_url') else _ons_distribution_candidates(session, spec, '.csv')
    table_title = str(spec['table_title_contains']).lower()
    date_column = str(spec.get('date_column') or 'Time period')
    value_column = str(spec['value_column'])
    last_error: Exception | None = None
    for csv_url, distribution_name in csv_candidates:
        try:
            response = session.get(csv_url, headers={'User-Agent': USER_AGENT}, timeout=(4, 20))
            response.raise_for_status()
            rows = list(csv.reader(io.StringIO(response.content.decode('utf-8-sig', errors='replace'))))
            start_col = -1
            title_row_index = -1
            for row_index, row in enumerate(rows):
                for column_index, cell in enumerate(row):
                    if table_title in str(cell).lower():
                        start_col = column_index
                        title_row_index = row_index
                        break
                if start_col >= 0:
                    break
            if start_col < 0:
                raise ValueError(f'Table title containing {table_title!r} not found in ONS CSV.')
            header_index = -1
            date_index = -1
            value_index = -1
            for index in range(title_row_index + 1, min(title_row_index + 8, len(rows))):
                row = rows[index]
                if len(row) <= start_col:
                    continue
                lowered = [str(item).strip().lower() for item in row]
                if lowered[start_col] != date_column.lower():
                    continue
                for column_index in range(start_col + 1, len(lowered)):
                    if lowered[column_index] == value_column.lower():
                        header_index = index
                        date_index = start_col
                        value_index = column_index
                        break
                if header_index >= 0:
                    break
            if header_index < 0:
                raise ValueError(f'Columns {date_column!r}/{value_column!r} not found in ONS CSV.')
            observations = _table_observations(rows, spec, header_index=header_index, date_index=date_index, value_index=value_index)
            return {**spec, 'observations': observations, 'provider_updated': observations[-1]['date'] if observations else '', 'api_url': csv_url, 'distribution_name': distribution_name}
        except Exception as exc:
            last_error = exc
            continue
    raise last_error or RuntimeError('No ONS horizontal CSV candidate could be parsed.')

def fetch_obr_xlsx_row(session: requests.Session, spec: dict[str, Any]) -> dict[str, Any]:
    """Fetch one horizontal row from an OBR EFO workbook.

    OBR EFO tables often put forecast years across columns and indicator names
    down rows. This adapter keeps those fiscal forecast additions config-driven.
    """
    xlsx_url = str(spec.get('xlsx_url') or '').strip()
    if not xlsx_url:
        raise ValueError('OBR XLSX row fetcher requires xlsx_url.')
    content = _download_binary(session, xlsx_url)
    if not content.startswith(b'PK'):
        raise RuntimeError('OBR xlsx URL did not return an XLSX workbook.')
    rows = _xlsx_sheet_rows(content, str(spec['sheet_name']))
    row_label = _clean_text(str(spec['row_label'])).lower()
    context = _clean_text(str(spec.get('context_above_contains') or '')).lower()
    target_index = -1
    for index, row in enumerate(rows):
        cleaned = [_clean_text(str(cell)).lower() for cell in row]
        if row_label not in cleaned:
            continue
        if context:
            above = ' '.join((' '.join((_clean_text(str(cell)).lower() for cell in rows[above_index])) for above_index in range(max(0, index - 8), index)))
            if context not in above:
                continue
        target_index = index
        break
    if target_index < 0:
        raise ValueError(f"OBR row {spec['row_label']!r} not found in {spec['sheet_name']!r}.")
    header_index = -1
    header_dates: dict[int, str] = {}
    for index in range(target_index - 1, -1, -1):
        candidates = {column_index: _normalise_obr_period(str(cell)) for column_index, cell in enumerate(rows[index]) if _normalise_obr_period(str(cell))}
        if len(candidates) >= 3:
            header_index = index
            header_dates = {column_index: value for column_index, value in candidates.items() if value}
            break
    if header_index < 0 or not header_dates:
        raise ValueError(f"Date header not found above OBR row {spec['row_label']!r}.")
    observations: list[dict[str, Any]] = []
    target_row = rows[target_index]
    for column_index, obs_date in header_dates.items():
        if column_index >= len(target_row):
            continue
        raw_value = target_row[column_index]
        if raw_value in (None, '', '.', '-', ' - '):
            continue
        try:
            value = float(str(raw_value).replace(',', ''))
        except (TypeError, ValueError):
            continue
        observations.append({'date': obs_date, 'value': value})
    observations.sort(key=lambda item: item['date'])
    observations = _apply_uk_transform(_start_filter(observations, spec.get('start_date')), spec)
    return {**spec, 'observations': observations, 'provider_updated': observations[-1]['date'] if observations else '', 'api_url': xlsx_url}

def _clean_text(value: str) -> str:
    return re.sub('\\s+', ' ', value or '').strip()

def _apply_china_transform(value: float, transform: str | None) -> float:
    if transform == 'usd_trn':
        return value / 1000000000000
    if transform == 'usd_mn_to_trn':
        return value / 1000000
    if transform == 'usd_100mn_to_trn':
        return value / 10000
    if transform == 'usd_thousand_to_bn':
        return value / 1000000
    if transform == 'cny_100mn_to_trn':
        return value / 10000
    if transform == 'cny_100mn_to_bn':
        return value / 10
    if transform == 'cny_10k_to_bn':
        return value / 100000
    if transform == 'cny_yuan_to_trn':
        return value / 1000000000000
    if transform == 'index_100_to_yoy':
        return value - 100
    if transform == 'people_billion':
        return value / 1000000000
    return value

def _parse_year(value: str) -> int | None:
    try:
        return int(str(value)[:4])
    except (TypeError, ValueError):
        return None

def _parse_period_date(value: Any) -> str | None:
    if hasattr(value, 'date'):
        value = value.date()
    if hasattr(value, 'isoformat'):
        return value.isoformat()
    text = _clean_text(str(value))
    if not text or text.lower() in {'nan', 'none', 'nat'}:
        return None
    match = re.match('^(\\d{4})-(\\d{1,2})-(\\d{1,2})(?:\\s+\\d{1,2}:\\d{2}:\\d{2})?$', text)
    if match:
        return f'{int(match.group(1)):04d}-{int(match.group(2)):02d}-{int(match.group(3)):02d}'
    match = re.match('^(\\d{4})(\\d{2})$', text)
    if match:
        return f'{int(match.group(1)):04d}-{int(match.group(2)):02d}-01'
    match = re.match('^(\\d{4})年(\\d{1,2})月份$', text)
    if match:
        return f'{int(match.group(1)):04d}-{int(match.group(2)):02d}-01'
    match = re.match('^(\\d{4})-(\\d{1,2})月$', text)
    if match:
        return f'{int(match.group(1)):04d}-{int(match.group(2)):02d}-01'
    match = re.match('^(\\d{4})年(\\d{1,2})月$', text)
    if match:
        return f'{int(match.group(1)):04d}-{int(match.group(2)):02d}-01'
    match = re.match('^(\\d{4})年(\\d{1,2})月(\\d{1,2})日$', text)
    if match:
        return f'{int(match.group(1)):04d}-{int(match.group(2)):02d}-{int(match.group(3)):02d}'
    match = re.match('^(\\d{4})年第(\\d)(?:-(\\d))?季度$', text)
    if match:
        quarter = int(match.group(3) or match.group(2))
        month = quarter * 3
        day = 31 if month in {3, 12} else 30
        return f'{int(match.group(1)):04d}-{month:02d}-{day:02d}'
    match = re.match('^(\\d{4})[.\\-/](\\d{1,2})(?:[.\\-/](\\d{1,2}))?$', text)
    if match:
        day = int(match.group(3) or 1)
        return f'{int(match.group(1)):04d}-{int(match.group(2)):02d}-{day:02d}'
    return None

def fetch_world_bank(spec: dict[str, Any]) -> dict[str, Any]:
    code = spec['series']
    url = f'https://api.worldbank.org/v2/country/CHN/indicator/{code}'
    response = requests.get(url, params={'format': 'json', 'per_page': 20000}, timeout=30)
    response.raise_for_status()
    payload = response.json()
    meta = payload[0] if isinstance(payload, list) and payload else {}
    rows = payload[1] if isinstance(payload, list) and len(payload) > 1 else []
    observations: list[dict[str, Any]] = []
    for row in rows:
        raw_value = row.get('value')
        if raw_value is None:
            continue
        try:
            value = _apply_china_transform(float(raw_value), spec.get('transform'))
        except (TypeError, ValueError):
            continue
        observations.append({'date': str(row.get('date')), 'value': value})
    observations.sort(key=lambda item: item['date'])
    return {**spec, 'observations': observations, 'provider_updated': meta.get('lastupdated', ''), 'api_url': url}

def fetch_imf_datamapper(spec: dict[str, Any]) -> dict[str, Any]:
    code = spec['series']
    url = f'https://www.imf.org/external/datamapper/api/v1/{code}/CHN'
    response = requests.get(url, timeout=45)
    response.raise_for_status()
    payload = response.json()
    country_values = ((payload.get('values') or {}).get(code) or {}).get('CHN') or {}
    observations = [{'date': str(year), 'value': _apply_china_transform(float(value), spec.get('transform'))} for year, value in country_values.items() if value is not None and str(year).isdigit()]
    observations.sort(key=lambda item: int(item['date']))
    return {**spec, 'observations': observations, 'provider_updated': datetime.now(UTC).date().isoformat(), 'api_url': url}

def fetch_fred_graph(spec: dict[str, Any]) -> dict[str, Any]:
    """Fetch a public FRED graph CSV without requiring a runtime API key."""
    code = spec['series']
    url = 'https://fred.stlouisfed.org/graph/fredgraph.csv'
    params = {'id': code}
    if spec.get('start_date'):
        params['cosd'] = str(spec['start_date'])
    response = requests.get(url, params=params, timeout=45)
    response.raise_for_status()
    observations: list[dict[str, Any]] = []
    for row in DictReader(StringIO(response.text)):
        raw_date = row.get('observation_date')
        raw_value = row.get(code)
        if not raw_date or raw_value in (None, '', '.'):
            continue
        try:
            value = _apply_china_transform(float(raw_value), spec.get('transform'))
        except (TypeError, ValueError):
            continue
        observations.append({'date': raw_date, 'value': value})
    observations.sort(key=lambda item: item['date'])
    return {**spec, 'observations': observations, 'provider_updated': observations[-1]['date'] if observations else '', 'api_url': f'{url}?id={code}'}

def _fetch_akshare_frame(spec: dict[str, Any], cache: dict[str, Any] | None=None) -> Any:
    try:
        import akshare as ak
    except ImportError as exc:
        raise RuntimeError('AKShare is not installed in the project environment.') from exc
    function_name = spec['function']
    args = spec.get('args') or []
    kwargs = spec.get('kwargs') or {}
    cache_key = json.dumps({'function': function_name, 'args': args, 'kwargs': kwargs}, ensure_ascii=False, sort_keys=True)
    if cache is not None and cache_key in cache:
        frame = cache[cache_key]
    else:
        fetcher = getattr(ak, function_name)
        timeout_seconds = int(spec.get('timeout_seconds', 45))
        attempts = int(spec.get('retries', 2))
        last_error: Exception | None = None
        for attempt in range(attempts):
            try:
                if timeout_seconds:

                    def _timeout_handler(signum: int, frame: Any) -> None:
                        raise TimeoutError(f'AKShare fetch timed out after {timeout_seconds}s for {function_name}')
                    old_handler = signal.signal(signal.SIGALRM, _timeout_handler)
                    signal.alarm(timeout_seconds)
                    try:
                        frame = fetcher(*args, **kwargs)
                    finally:
                        signal.alarm(0)
                        signal.signal(signal.SIGALRM, old_handler)
                else:
                    frame = fetcher(*args, **kwargs)
                break
            except Exception as exc:
                last_error = exc
                if attempt < attempts - 1:
                    time.sleep(2)
                else:
                    raise last_error
        if cache is not None:
            cache[cache_key] = frame
    return frame

def fetch_akshare_table(spec: dict[str, Any], cache: dict[str, Any] | None=None) -> dict[str, Any]:
    try:
        import pandas as pd
    except ImportError as exc:
        raise RuntimeError('pandas is not installed in the project environment.') from exc
    frame = _fetch_akshare_frame(spec, cache)
    filter_column = spec.get('filter_column')
    if filter_column and spec.get('filter_value') is not None:
        frame = frame[frame[filter_column].astype(str) == str(spec['filter_value'])]
    date_column = spec['date_column']
    value_column = spec.get('value_column')
    value_columns = spec.get('value_columns') or []
    observations: list[dict[str, Any]] = []
    for _, row in frame.iterrows():
        raw_date = row.get(date_column)
        if pd.isna(raw_date):
            continue
        if value_columns:
            raw_values = [row.get(column) for column in value_columns]
            if any((pd.isna(raw_value) for raw_value in raw_values)):
                continue
            try:
                values = [float(raw_value) for raw_value in raw_values]
            except (TypeError, ValueError):
                continue
            operation = spec.get('value_operation', 'sum')
            if operation == 'difference':
                raw_value = values[0] - values[1]
            elif operation == 'ratio':
                raw_value = values[0] / values[1] if values[1] else None
            else:
                raw_value = sum(values)
            if raw_value is None:
                continue
        else:
            raw_value = row.get(value_column)
            if pd.isna(raw_value):
                continue
        parsed_date = _parse_period_date(raw_date)
        if not parsed_date:
            continue
        try:
            value = _apply_china_transform(float(raw_value), spec.get('transform'))
        except (TypeError, ValueError):
            continue
        observations.append({'date': parsed_date, 'value': value})
    observations.sort(key=lambda item: item['date'])
    return {**spec, 'observations': observations, 'provider_updated': observations[-1]['date'] if observations else '', 'api_url': spec.get('source_url', '')}

def fetch_akshare_wide_year_month(spec: dict[str, Any], cache: dict[str, Any] | None=None) -> dict[str, Any]:
    """Parse AKShare tables with month rows and year columns, e.g. CPCA."""
    try:
        import pandas as pd
    except ImportError as exc:
        raise RuntimeError('pandas is not installed in the project environment.') from exc
    frame = _fetch_akshare_frame(spec, cache)
    date_column = spec['date_column']
    observations: list[dict[str, Any]] = []
    for _, row in frame.iterrows():
        month_text = _clean_text(str(row.get(date_column, '')))
        month_match = re.match('^(\\d{1,2})月$', month_text)
        if not month_match:
            continue
        month = int(month_match.group(1))
        for column in frame.columns:
            year_match = re.match('^(\\d{4})年$', str(column))
            if not year_match:
                continue
            raw_value = row.get(column)
            if pd.isna(raw_value):
                continue
            try:
                value = _apply_china_transform(float(raw_value), spec.get('transform'))
            except (TypeError, ValueError):
                continue
            observations.append({'date': f'{int(year_match.group(1)):04d}-{month:02d}-01', 'value': value})
    observations.sort(key=lambda item: item['date'])
    return {**spec, 'observations': observations, 'provider_updated': observations[-1]['date'] if observations else '', 'api_url': spec.get('source_url', '')}

def fetch_eastmoney_industry_indicator(spec: dict[str, Any]) -> dict[str, Any]:
    """Fetch Eastmoney's reusable industry-index API by stable INDICATOR_ID."""
    indicator_id = spec['indicator_id']
    value_column = spec.get('value_column', 'INDICATOR_VALUE')
    url = 'https://datacenter-web.eastmoney.com/api/data/v1/get'
    params = {'sortColumns': 'REPORT_DATE', 'sortTypes': '-1', 'pageSize': str(spec.get('page_size', 1000)), 'pageNumber': '1', 'reportName': 'RPT_INDUSTRY_INDEX', 'columns': 'REPORT_DATE,INDICATOR_ID,INDICATOR_NAME,INDICATOR_VALUE,CHANGE_RATE,CHANGERATE_3M,CHANGERATE_6M,CHANGERATE_1Y,CHANGERATE_2Y,CHANGERATE_3Y', 'filter': f'(INDICATOR_ID="{indicator_id}")', 'source': 'WEB', 'client': 'WEB'}
    response = requests.get(url, params=params, headers={'User-Agent': 'Mozilla/5.0'}, timeout=45)
    response.raise_for_status()
    payload = response.json()
    rows = (payload.get('result') or {}).get('data') or []
    observations: list[dict[str, Any]] = []
    seen: set[tuple[str, float]] = set()
    for row in rows:
        parsed_date = _parse_period_date(row.get('REPORT_DATE'))
        raw_value = row.get(value_column)
        if not parsed_date or raw_value is None:
            continue
        try:
            value = _apply_china_transform(float(raw_value), spec.get('transform'))
        except (TypeError, ValueError):
            continue
        key = (parsed_date, value)
        if key in seen:
            continue
        seen.add(key)
        observations.append({'date': parsed_date, 'value': value})
    observations.sort(key=lambda item: item['date'])
    return {**spec, 'observations': observations, 'provider_updated': observations[-1]['date'] if observations else '', 'api_url': response.url}

def _safe_rows() -> list[list[str]]:
    end = date.today()
    start = end - timedelta(days=365)
    response = requests.post('https://www.safe.gov.cn/AppStructured/hlw/RMBQuery.do', data={'startDate': start.isoformat(), 'endDate': end.isoformat(), 'queryYN': 'true'}, timeout=45)
    response.raise_for_status()
    rows: list[list[str]] = []
    for tr in re.findall('<tr[^>]*class="first"[^>]*>(.*?)</tr>', response.text, flags=re.S):
        cells = [_clean_text(re.sub('<.*?>', '', cell)) for cell in re.findall('<td[^>]*>(.*?)</td>', tr, flags=re.S)]
        cells = [cell for cell in cells if cell]
        if len(cells) >= 3 and re.match('\\d{4}-\\d{2}-\\d{2}', cells[0]):
            rows.append(cells)
    rows.sort(key=lambda item: item[0])
    return rows

def fetch_safe_midpoint(spec: dict[str, Any], rows: list[list[str]]) -> dict[str, Any]:
    column = 1 if spec['id'] == 'usd_cny_midpoint' else 2
    observations: list[dict[str, Any]] = []
    for row in rows:
        try:
            value = float(row[column]) / 100.0
        except (IndexError, TypeError, ValueError):
            continue
        observations.append({'date': row[0], 'value': value})
    return {**spec, 'observations': observations, 'provider_updated': observations[-1]['date'] if observations else '', 'api_url': spec['source_url']}

def fetch_pbc_card(card: dict[str, Any]) -> dict[str, Any]:
    response = requests.get(card['url'], timeout=30)
    response.raise_for_status()
    text = re.sub('<[^>]+>', '\n', response.text)
    lines = [_clean_text(line) for line in text.splitlines()]
    lines = [line for line in lines if line]
    title = card['expected_title']
    title_idx = next((i for i, line in enumerate(lines) if line == title), -1)
    value = 'n/a'
    if title_idx >= 0:
        for line in lines[title_idx + 1:title_idx + 14]:
            if re.match('^-?\\d+(?:\\.\\d+)?(?:%|TN|BN|MN)?$', line, flags=re.I):
                value = line
                break
    update_idx = next((i for i, line in enumerate(lines) if line == 'Latest Update'), -1)
    updated = ''
    if update_idx >= 0:
        for line in lines[update_idx + 1:update_idx + 5]:
            if re.match('\\d{2}/\\d{2}/\\d{4}', line):
                updated = line
                break
    return {**card, 'value': value, 'updated': updated or 'n/a'}

def fetch_sarb(session: requests.Session, spec: dict[str, Any]) -> dict[str, Any]:
    """Fetch one SARB Web Indicators timeseries code.

    The bare ``/{code}`` form of this endpoint returns only the last 25
    observations, which is too short to chart, so the explicit date-range form
    is always used.
    """
    code = str(spec['series'])
    start_date = str(spec.get('start_date') or '1990-01-01')
    end_date = datetime.now(UTC).date().isoformat()
    url = f'{SARB_BASE}/{code}/{start_date}/{end_date}'
    response = session.get(url, headers={'User-Agent': USER_AGENT, 'Accept': 'application/json'}, timeout=(5, 45))
    response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, list):
        raise RuntimeError(f'SARB returned an unexpected payload for {code}.')
    frequency = str(spec.get('frequency') or '').strip().lower()
    observations: list[dict[str, Any]] = []
    for row in payload:
        period = str(row.get('Period') or '')[:10]
        raw_value = row.get('Value')
        if not re.match('^\\d{4}-\\d{2}-\\d{2}$', period) or raw_value is None:
            continue
        if frequency == 'monthly':
            period = f'{period[:7]}-01'
        try:
            observations.append({'date': period, 'value': float(raw_value)})
        except (TypeError, ValueError):
            continue
    observations.sort(key=lambda item: item['date'])
    if not observations:
        raise RuntimeError(f'SARB returned no observations for {code}.')
    return {**spec, 'observations': observations, 'provider_updated': observations[-1]['date'], 'api_url': url}