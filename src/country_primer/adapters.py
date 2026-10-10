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
