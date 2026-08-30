"""Build the UK macro dashboard from GS UK-statistics-aligned config.

The UK page follows the logic of the Goldman Sachs UK statistics guide, but it
only renders reproducible public time series. Native ONS JSON and Bank of
England IADB CSV are preferred for release-sensitive UK data; FRED remains the
fallback public backbone for OECD/IMF/BIS mirror series. If FRED_API_KEY is set,
the official FRED API is used; otherwise the script falls back to FRED's public
graph CSV endpoint.
"""
from __future__ import annotations

import csv
import io
import json
import os
import re
import time
from calendar import monthrange
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import UTC, date, datetime
from email.utils import parsedate_to_datetime
from html import escape
from pathlib import Path
from threading import Lock
from typing import Any
from xml.etree import ElementTree as ET
from zipfile import ZipFile

import requests
import yaml

from dashboard_summary_utils import (
    apply_quality_assessments,
    build_summary_metadata,
    canonical_frame_metadata,
    load_canonical_data_first_frame,
    retain_last_known_good_series,
    write_canonical_data_first_frame,
)
from build_china_dashboard import (  # Reuse the data-first page shell.
    CSS,
    _chart_html,
    _format_value,
    _gaps_html,
    _json,
    _latest,
    _section_nav,
    _sections_html,
    _write_clean,
)
from country_primer.source_health import (
    SOURCE_HEALTH,
    failure_series,
    guarded_source_call,
    write_source_health_report,
)


ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "config" / "uk_indicators.yaml"
OUTPUT = ROOT / "output"
OUT_HTML = OUTPUT / "uk.html"
SUMMARY_JSON = OUTPUT / "uk_dashboard_summary.json"
CANONICAL_JSON = OUTPUT / "uk_canonical_frame.json"
SUMMARY_KEY_IDS = [
    "real_gdp_qoq",
    "monthly_gdp_mom",
    "retail_sales_yoy",
    "unemployment_rate",
    "paye_payrolled_employees",
    "cpi_yoy",
    "core_cpi_yoy",
    "bank_rate",
    "sonia_rate",
    "psnb_ex_banks",
    "psnd_ex_banks_gdp",
]

FRED_GRAPH_URL = "https://fred.stlouisfed.org/graph/fredgraph.csv"
FRED_API_URL = "https://api.stlouisfed.org/fred/series/observations"
FRED_SERIES_URL = "https://api.stlouisfed.org/fred/series"
BOE_BANK_RATE_URL = "https://www.bankofengland.co.uk/boeapps/database/Bank-Rate.asp?hl=en-GB"
BOE_IADB_URL = "https://www.bankofengland.co.uk/boeapps/database/_iadb-fromshowcolumns.asp"
ONS_TIMESERIES_BASE = "https://www.ons.gov.uk"
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 Chrome/124.0 Safari/537.36"
)
BINARY_DOWNLOAD_CACHE: dict[str, bytes] = {}
BINARY_DOWNLOAD_CACHE_LOCK = Lock()
DISTRIBUTION_CACHE: dict[tuple[str, str, str], Any] = {}
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
    "sept": 9,
    "september": 9,
    "oct": 10,
    "october": 10,
    "nov": 11,
    "november": 11,
    "dec": 12,
    "december": 12,
}


def _load_config() -> dict[str, Any]:
    return yaml.safe_load(CONFIG_PATH.read_text()) or {}


def _clean_text(value: str) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def _parse_date(value: str) -> date | None:
    value = _clean_text(str(value or ""))
    value = re.sub(r"\s+\[[^\]]+\]$", "", value).strip()
    quarter_match = re.match(r"^(\d{4})\s+Q([1-4])$", value, flags=re.I)
    if quarter_match:
        year = int(quarter_match.group(1))
        month = int(quarter_match.group(2)) * 3
        return date(year, month, monthrange(year, month)[1])
    quarter_range_match = re.match(
        r"^([A-Za-z]{3,9})\s+to\s+([A-Za-z]{3,9})\s+(\d{4})$",
        value,
        flags=re.I,
    )
    if quarter_range_match:
        year = int(quarter_range_match.group(3))
        month = MONTHS.get(quarter_range_match.group(2).lower())
        if month:
            return date(year, month, monthrange(year, month)[1])
    month_match = re.match(r"^(\d{4})\s+([A-Za-z]{3,9})$", value)
    if month_match:
        year = int(month_match.group(1))
        month = MONTHS.get(month_match.group(2).lower())
        if month:
            return date(year, month, 1)
    month_first_match = re.match(r"^([A-Za-z]{3,9})\s+(\d{4})$", value)
    if month_first_match:
        month = MONTHS.get(month_first_match.group(1).lower())
        if month:
            return date(int(month_first_match.group(2)), month, 1)
    for fmt, length in (("%Y-%m-%d", 10), ("%Y-%m", 7), ("%Y", 4)):
        try:
            return datetime.strptime(value[:length], fmt).date()
        except ValueError:
            continue
    for fmt in ("%d %b %Y", "%d %B %Y", "%d %b %y", "%d/%m/%Y", "%b-%y", "%B-%y"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    return None


def _normalise_date(value: str) -> str | None:
    parsed = _parse_date(value)
    return parsed.isoformat() if parsed else None


def _normalise_obr_period(value: str) -> str | None:
    value = _clean_text(str(value or ""))
    financial_year_match = re.match(r"^(\d{4})-(\d{2})$", value)
    if financial_year_match:
        # OBR fiscal-year tables are UK financial years ending in March.
        return date(int(financial_year_match.group(1)) + 1, 3, 31).isoformat()
    quarter_match = re.match(r"^(\d{4})\s*Q([1-4])$", value, flags=re.I)
    if quarter_match:
        year = int(quarter_match.group(1))
        month = int(quarter_match.group(2)) * 3
        return date(year, month, monthrange(year, month)[1]).isoformat()
    return None


def _date_matches_frequency(value: str, frequency: str) -> bool:
    """Avoid treating annual or quarterly rows as monthly data in mixed ONS tables."""
    value = _clean_text(value)
    value = re.sub(r"\s+\[[^\]]+\]$", "", value).strip()
    frequency = frequency.lower()
    if frequency == "monthly":
        return bool(
            re.match(r"^[A-Za-z]{3,9}[- ]\d{2,4}$", value)
            or re.match(r"^\d{4}\s+[A-Za-z]{3,9}$", value)
        )
    if frequency == "quarterly":
        return bool(
            re.match(r"^\d{4}\s+Q[1-4]$", value, flags=re.I)
            or re.match(r"^[A-Za-z]{3,9}\s+to\s+[A-Za-z]{3,9}\s+\d{4}$", value, flags=re.I)
        )
    if frequency == "annual":
        return bool(re.match(r"^\d{4}$", value))
    return True


def _start_filter(observations: list[dict[str, Any]], start_date: str | None) -> list[dict[str, Any]]:
    if not start_date:
        return observations
    start = _parse_date(start_date)
    if not start:
        return observations
    return [item for item in observations if (_parse_date(str(item["date"])) or date.min) >= start]


def _fred_api_observations(session: requests.Session, spec: dict[str, Any]) -> tuple[list[dict[str, Any]], str]:
    api_key = os.environ.get("FRED_API_KEY", "").strip()
    if not api_key:
        return [], ""
    params = {
        "series_id": spec["series"],
        "api_key": api_key,
        "file_type": "json",
    }
    if spec.get("start_date"):
        params["observation_start"] = spec["start_date"]
    last_error: Exception | None = None
    for attempt in range(5):
        try:
            response = session.get(FRED_API_URL, params=params, timeout=(4, 16))
            response.raise_for_status()
            break
        except Exception as exc:  # noqa: BLE001 - retry transient FRED/API transport failures.
            last_error = exc
            if attempt < 4:
                time.sleep(0.7 * (2 ** attempt))
    else:
        raise last_error or RuntimeError("FRED API request failed.")
    payload = response.json()
    observations: list[dict[str, Any]] = []
    for row in payload.get("observations", []):
        raw_value = row.get("value")
        if raw_value in (None, "", "."):
            continue
        try:
            value = float(raw_value)
        except (TypeError, ValueError):
            continue
        observations.append({"date": str(row.get("date")), "value": value})
    updated = response.headers.get("Last-Modified", "")
    return observations, updated


def _fred_api_series_updated(session: requests.Session, series_id: str) -> str:
    api_key = os.environ.get("FRED_API_KEY", "").strip()
    if not api_key:
        return ""
    params = {
        "series_id": series_id,
        "api_key": api_key,
        "file_type": "json",
    }
    try:
        response = session.get(FRED_SERIES_URL, params=params, timeout=(4, 12))
        response.raise_for_status()
        payload = response.json()
    except Exception:  # noqa: BLE001 - provider metadata is useful but not critical.
        return ""
    series = payload.get("seriess") or []
    if not series:
        return ""
    return str(series[0].get("last_updated") or "")


def _fred_graph_observations(session: requests.Session, spec: dict[str, Any]) -> tuple[list[dict[str, Any]], str]:
    params = {"id": spec["series"]}
    # FRED graph CSV accepts cosd/coed. This is important for very long UK rate
    # histories, where requesting the entire series can be slow.
    if spec.get("start_date"):
        params["cosd"] = spec["start_date"]
    response = session.get(FRED_GRAPH_URL, params=params, timeout=(4, 12))
    response.raise_for_status()
    rows = csv.DictReader(io.StringIO(response.text))
    observations: list[dict[str, Any]] = []
    for row in rows:
        raw_value = row.get(spec["series"])
        if raw_value in (None, "", "."):
            continue
        try:
            value = float(raw_value)
        except (TypeError, ValueError):
            continue
        observations.append({"date": str(row.get("observation_date")), "value": value})
    updated = response.headers.get("Last-Modified", "")
    return observations, updated


def _provider_updated_date(value: str) -> str:
    value = str(value or "").strip()
    if not value:
        return ""
    if re.match(r"^\d{4}-\d{2}-\d{2}", value):
        return value[:10]
    try:
        return parsedate_to_datetime(value).date().isoformat()
    except (TypeError, ValueError):
        return value


def _apply_transform(observations: list[dict[str, Any]], spec: dict[str, Any]) -> list[dict[str, Any]]:
    transform = str(spec.get("transform") or "")
    if transform in {"divide_1k", "divide_1m", "divide_1bn", "decimal_to_pct"}:
        divisor = {"divide_1k": 1_000, "divide_1m": 1_000_000, "divide_1bn": 1_000_000_000}.get(transform, 1)
        multiplier = 100 if transform == "decimal_to_pct" else 1
        return [
            {**item, "value": float(item["value"]) / divisor * multiplier}
            for item in observations
            if item.get("value") is not None
        ]
    if transform not in {"yoy", "qoq_pct", "mom_pct"}:
        return observations
    frequency = str(spec.get("frequency", "")).lower()
    periods = 1 if transform in {"qoq_pct", "mom_pct"} else 12 if frequency == "monthly" else 4 if frequency == "quarterly" else 1
    transformed: list[dict[str, Any]] = []
    for index, item in enumerate(observations):
        if index < periods:
            continue
        base = observations[index - periods]["value"]
        if base in (0, None):
            continue
        try:
            value = (float(item["value"]) / float(base) - 1.0) * 100.0
        except (TypeError, ValueError, ZeroDivisionError):
            continue
        transformed.append({"date": item["date"], "value": value})
    return transformed


def fetch_fred(session: requests.Session, spec: dict[str, Any]) -> dict[str, Any]:
    observations: list[dict[str, Any]]
    provider_updated: str
    used_api = False
    try:
        observations, provider_updated = _fred_api_observations(session, spec)
        used_api = bool(observations)
    except Exception:  # noqa: BLE001 - API key may be absent/invalid; graph CSV is the durable fallback.
        observations, provider_updated = [], ""
    if not observations:
        observations, provider_updated = _fred_graph_observations(session, spec)
    elif used_api:
        provider_updated = _fred_api_series_updated(session, str(spec["series"])) or provider_updated
    observations = _apply_transform(_start_filter(observations, spec.get("start_date")), spec)
    provider_updated = _provider_updated_date(provider_updated)
    return {
        **spec,
        "observations": observations,
        "provider_updated": provider_updated or (observations[-1]["date"] if observations else ""),
        "api_url": FRED_API_URL if os.environ.get("FRED_API_KEY") else FRED_GRAPH_URL,
    }


def _ons_path(spec: dict[str, Any]) -> str:
    path = str(spec.get("ons_path") or "").strip()
    if path:
        return path
    cdid = str(spec["series"]).lower()
    dataset = str(spec.get("dataset") or spec.get("dataset_id") or "").lower()
    return f"/timeseries/{cdid}/{dataset}/data"


def fetch_ons_timeseries(session: requests.Session, spec: dict[str, Any]) -> dict[str, Any]:
    path = _ons_path(spec)
    url = f"{ONS_TIMESERIES_BASE}{path}" if path.startswith("/") else path
    response = session.get(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"}, timeout=(4, 20))
    response.raise_for_status()
    payload = response.json()
    frequency = str(spec.get("frequency", "")).lower()
    rows_by_frequency = {
        "monthly": payload.get("months") or [],
        "quarterly": payload.get("quarters") or [],
        "annual": payload.get("years") or [],
    }
    if frequency not in rows_by_frequency:
        raise ValueError(
            f"ONS series {spec.get('series')!r} ({spec.get('id')!r}) declares unsupported "
            f"frequency {frequency!r}; expected one of {sorted(rows_by_frequency)}."
        )
    rows = rows_by_frequency[frequency]
    if not rows:
        # Do NOT silently fall back to whatever array the payload happens to
        # carry (e.g. "months" for a series that is actually quarterly) — that
        # produces a chart whose label ("monthly") contradicts its data. Fail
        # loudly so a mislabeled config gets caught at build time, not shipped
        # with a confident "verified" badge.
        available = sorted(key for key in ("months", "quarters", "years") if payload.get(key))
        raise ValueError(
            f"ONS series {spec.get('series')!r} ({spec.get('id')!r}) declares frequency "
            f"{frequency!r} but the ONS payload has no {frequency!r} observations at {url}; "
            f"payload only carries {available or ['none']}. Check the declared frequency "
            f"against the ONS dataset before relabeling or repointing this indicator."
        )
    observations: list[dict[str, Any]] = []
    provider_updated = ""
    for row in rows:
        raw_value = row.get("value")
        if raw_value in (None, "", "."):
            continue
        obs_date = _normalise_date(str(row.get("date") or row.get("label") or ""))
        if not obs_date:
            continue
        try:
            value = float(str(raw_value).replace(",", ""))
        except (TypeError, ValueError):
            continue
        provider_updated = str(row.get("updateDate") or provider_updated)
        observations.append({"date": obs_date, "value": value})
    observations.sort(key=lambda item: item["date"])
    observations = _apply_transform(_start_filter(observations, spec.get("start_date")), spec)
    description = payload.get("description") or {}
    provider_updated = str(description.get("releaseDate") or provider_updated or "")
    if provider_updated:
        provider_updated = provider_updated[:10]
    return {
        **spec,
        "observations": observations,
        "provider_updated": provider_updated or (observations[-1]["date"] if observations else ""),
        "api_url": url,
        "current_value": str(description.get("number") or ""),
    }


def _boe_date_param(start_date: str | None) -> str:
    parsed = _parse_date(start_date or "")
    if not parsed:
        parsed = date(1997, 1, 1)
    return parsed.strftime("%d/%b/%Y")


def fetch_boe_iadb(session: requests.Session, spec: dict[str, Any]) -> dict[str, Any]:
    series_code = str(spec["series"]).strip()
    params = {
        "csv.x": "yes",
        "Datefrom": _boe_date_param(spec.get("start_date")),
        "Dateto": "now",
        "SeriesCodes": series_code,
        "CSVF": "TN",
        "UsingCodes": "Y",
        "VPD": "Y",
        "VFD": "N",
    }
    response = session.get(BOE_IADB_URL, params=params, headers={"User-Agent": USER_AGENT}, timeout=(4, 20))
    response.raise_for_status()
    if "<html" in response.text[:200].lower():
        raise RuntimeError(f"BoE IADB rejected series code {series_code}.")
    rows = csv.DictReader(io.StringIO(response.text))
    observations: list[dict[str, Any]] = []
    for row in rows:
        raw_value = row.get(series_code)
        if raw_value in (None, "", "."):
            continue
        obs_date = _normalise_date(str(row.get("DATE") or ""))
        if not obs_date:
            continue
        try:
            value = float(str(raw_value).replace(",", ""))
        except (TypeError, ValueError):
            continue
        observations.append({"date": obs_date, "value": value})
    observations.sort(key=lambda item: item["date"])
    observations = _apply_transform(_start_filter(observations, spec.get("start_date")), spec)
    return {
        **spec,
        "observations": observations,
        "provider_updated": observations[-1]["date"] if observations else "",
        "api_url": response.url,
    }


def _parse_boe_short_date(value: str) -> str | None:
    try:
        dt = datetime.strptime(value, "%d %b %y").date()
    except ValueError:
        return None
    return dt.isoformat()


def fetch_boe_bank_rate(session: requests.Session, spec: dict[str, Any]) -> dict[str, Any]:
    response = session.get(
        BOE_BANK_RATE_URL,
        headers={"User-Agent": USER_AGENT, "Accept": "text/html,application/xhtml+xml"},
        timeout=(4, 12),
    )
    response.raise_for_status()
    rows = re.findall(r"<tr[^>]*>(.*?)</tr>", response.text, flags=re.S | re.I)
    observations: list[dict[str, Any]] = []
    for row in rows:
        cells = [
            _clean_text(re.sub(r"<[^>]+>", " ", cell))
            for cell in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", row, flags=re.S | re.I)
        ]
        if len(cells) < 2 or cells[0].lower().startswith("date"):
            continue
        obs_date = _parse_boe_short_date(cells[0])
        if not obs_date:
            continue
        try:
            value = float(cells[1].replace("%", ""))
        except ValueError:
            continue
        observations.append({"date": obs_date, "value": value})
    observations.sort(key=lambda item: item["date"])
    observations = _start_filter(observations, spec.get("start_date"))
    current_match = re.search(r'<p class="stat-figure">([^<]+)</p>', response.text)
    current_value = _clean_text(current_match.group(1)) if current_match else ""
    return {
        **spec,
        "observations": observations,
        "provider_updated": observations[-1]["date"] if observations else "",
        "api_url": BOE_BANK_RATE_URL,
        "current_value": current_value,
    }


def _govuk_distribution_url(session: requests.Session, spec: dict[str, Any], extension: str) -> tuple[str, str]:
    """Return the current GOV.UK distribution URL from page-level JSON-LD metadata."""
    page_url = str(spec.get("source_url") or "").strip()
    if not page_url:
        raise ValueError("GOV.UK fetcher requires source_url.")
    wanted = str(spec.get("distribution_name_contains") or spec.get("csv_label_contains") or "").lower()
    cache_key = (page_url, extension, wanted)
    with DISTRIBUTION_CACHE_LOCK:
        if cache_key in DISTRIBUTION_CACHE:
            return DISTRIBUTION_CACHE[cache_key]
        response = session.get(page_url, headers={"User-Agent": USER_AGENT}, timeout=(4, 20))
        response.raise_for_status()
        page_text = response.text
    candidates: list[dict[str, Any]] = []
    for match in re.findall(
        r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
        page_text,
        flags=re.S | re.I,
    ):
        try:
            payload = json.loads(match)
        except json.JSONDecodeError:
            continue
        items = payload if isinstance(payload, list) else [payload]
        for item in items:
            if isinstance(item, dict):
                distribution = item.get("distribution") or []
                if isinstance(distribution, dict):
                    distribution = [distribution]
                candidates.extend(row for row in distribution if isinstance(row, dict))
    for candidate in candidates:
        url = str(candidate.get("contentUrl") or candidate.get("url") or "").strip()
        name = str(candidate.get("name") or "").strip()
        if not url or not url.lower().split("?")[0].endswith(extension):
            continue
        if wanted and wanted not in name.lower() and wanted not in url.lower():
            continue
        result = (url, name)
        with DISTRIBUTION_CACHE_LOCK:
            DISTRIBUTION_CACHE[cache_key] = result
        return result
    raise RuntimeError(f"No matching GOV.UK {extension} distribution found for {page_url}.")


def _download_binary(session: requests.Session, url: str, timeout: tuple[int, int] = (4, 24)) -> bytes:
    """Cache workbook downloads reused by several indicators in a single build."""
    with BINARY_DOWNLOAD_CACHE_LOCK:
        if url not in BINARY_DOWNLOAD_CACHE:
            response = session.get(url, headers={"User-Agent": USER_AGENT}, timeout=timeout)
            response.raise_for_status()
            BINARY_DOWNLOAD_CACHE[url] = response.content
        return BINARY_DOWNLOAD_CACHE[url]


def _ons_distribution_candidates(
    session: requests.Session,
    spec: dict[str, Any],
    extension: str,
) -> list[tuple[str, str]]:
    """Return ONS dataset download candidates from JSON-LD plus visible download links."""
    page_url = str(spec.get("source_url") or "").strip()
    if not page_url:
        raise ValueError("ONS dataset fetcher requires source_url.")
    wanted = str(spec.get("distribution_name_contains") or "").lower()
    cache_key = (page_url, extension, wanted)
    with DISTRIBUTION_CACHE_LOCK:
        if cache_key in DISTRIBUTION_CACHE:
            return list(DISTRIBUTION_CACHE[cache_key])
        response = session.get(page_url, headers={"User-Agent": USER_AGENT}, timeout=(4, 20))
        response.raise_for_status()
        page_text = response.text
        candidates: list[tuple[str, str]] = []

        for match in re.findall(
            r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
            page_text,
            flags=re.S | re.I,
        ):
            try:
                payload = json.loads(match)
            except json.JSONDecodeError:
                continue
            items = payload if isinstance(payload, list) else [payload]
            for item in items:
                if not isinstance(item, dict):
                    continue
                distribution = item.get("distribution") or []
                if isinstance(distribution, dict):
                    distribution = [distribution]
                for row in distribution:
                    if not isinstance(row, dict):
                        continue
                    url = str(row.get("contentUrl") or row.get("url") or "").strip()
                    name = str(row.get("name") or row.get("encodingFormat") or "").strip()
                    if url:
                        candidates.append((url, name))

        for href, label in re.findall(r'href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', page_text, flags=re.S | re.I):
            url = href.strip()
            if url.startswith("/"):
                url = f"{ONS_TIMESERIES_BASE}{url}"
            name = _clean_text(re.sub(r"<[^>]+>", " ", label))
            candidates.append((url, name))

        seen: set[str] = set()
        filtered: list[tuple[str, str]] = []
        for url, name in candidates:
            normalized = url.lower().split("#")[0]
            path_part = normalized.split("?")[0]
            if not (path_part.endswith(extension) or extension in normalized) or url in seen:
                continue
            if wanted and wanted not in name.lower() and wanted not in url.lower():
                continue
            seen.add(url)
            filtered.append((url, name))
        if not filtered:
            raise RuntimeError(f"No matching ONS {extension} distribution found for {page_url}.")
        DISTRIBUTION_CACHE[cache_key] = tuple(filtered)
        return filtered


def _table_observations(
    rows: list[list[str]],
    spec: dict[str, Any],
    *,
    header_index: int,
    date_index: int,
    value_index: int,
) -> list[dict[str, Any]]:
    observations: list[dict[str, Any]] = []
    frequency = str(spec.get("frequency", "")).lower()
    for row in rows[header_index + 1 :]:
        if len(row) <= max(date_index, value_index):
            continue
        raw_date = str(row[date_index]).strip()
        if not _date_matches_frequency(raw_date, frequency):
            continue
        obs_date = _normalise_date(raw_date)
        raw_value = row[value_index]
        if not obs_date or raw_value in (None, "", ".", "[x]"):
            continue
        try:
            value = float(str(raw_value).replace(",", ""))
        except (TypeError, ValueError):
            continue
        observations.append({"date": obs_date, "value": value})
    observations.sort(key=lambda item: item["date"])
    return _apply_transform(_start_filter(observations, spec.get("start_date")), spec)


def fetch_govuk_road_fuel(session: requests.Session, spec: dict[str, Any]) -> dict[str, Any]:
    csv_url = str(spec.get("csv_url") or "").strip()
    distribution_name = ""
    if not csv_url:
        csv_url, distribution_name = _govuk_distribution_url(session, spec, ".csv")
    response = session.get(csv_url, headers={"User-Agent": USER_AGENT}, timeout=(4, 20))
    response.raise_for_status()
    rows = csv.DictReader(io.StringIO(response.content.decode("utf-8-sig", errors="replace")))
    date_column = str(spec.get("date_column") or "Date")
    value_column = str(spec.get("value_column") or "")
    value_contains = str(spec.get("value_column_contains") or "").lower()
    observations: list[dict[str, Any]] = []
    for row in rows:
        if not value_column:
            value_column = next((name for name in row if value_contains and value_contains in name.lower()), "")
        if not value_column:
            raise ValueError("Road-fuel CSV value column could not be inferred.")
        obs_date = _normalise_date(str(row.get(date_column) or ""))
        raw_value = row.get(value_column)
        if not obs_date or raw_value in (None, "", "."):
            continue
        try:
            value = float(str(raw_value).replace(",", ""))
        except (TypeError, ValueError):
            continue
        observations.append({"date": obs_date, "value": value})
    observations.sort(key=lambda item: item["date"])
    observations = _apply_transform(_start_filter(observations, spec.get("start_date")), spec)
    return {
        **spec,
        "observations": observations,
        "provider_updated": observations[-1]["date"] if observations else "",
        "api_url": csv_url,
        "distribution_name": distribution_name,
    }


def _xlsx_col_index(cell_ref: str) -> int:
    letters = re.sub(r"[^A-Z]", "", cell_ref.upper())
    value = 0
    for letter in letters:
        value = value * 26 + (ord(letter) - ord("A") + 1)
    return value - 1


def _xlsx_sheet_rows(content: bytes, sheet_name: str) -> list[list[str]]:
    ns = {
        "main": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
        "rel": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
        "pkg": "http://schemas.openxmlformats.org/package/2006/relationships",
    }
    with ZipFile(io.BytesIO(content)) as workbook:
        shared: list[str] = []
        if "xl/sharedStrings.xml" in workbook.namelist():
            shared_root = ET.fromstring(workbook.read("xl/sharedStrings.xml"))
            for item in shared_root.findall("main:si", ns):
                shared.append("".join(node.text or "" for node in item.findall(".//main:t", ns)))

        workbook_root = ET.fromstring(workbook.read("xl/workbook.xml"))
        rel_root = ET.fromstring(workbook.read("xl/_rels/workbook.xml.rels"))
        rel_targets = {
            rel.attrib["Id"]: rel.attrib["Target"]
            for rel in rel_root.findall("pkg:Relationship", ns)
            if "Id" in rel.attrib and "Target" in rel.attrib
        }
        sheet_path = ""
        for sheet in workbook_root.findall(".//main:sheet", ns):
            if sheet.attrib.get("name") != sheet_name:
                continue
            rel_id = sheet.attrib.get(f"{{{ns['rel']}}}id")
            target = rel_targets.get(str(rel_id), "")
            sheet_path = f"xl/{target.lstrip('/')}" if not target.startswith("xl/") else target
            break
        if not sheet_path:
            raise ValueError(f"Worksheet {sheet_name!r} not found in XLSX.")

        sheet_root = ET.fromstring(workbook.read(sheet_path))
        rows: list[list[str]] = []
        for row in sheet_root.findall(".//main:sheetData/main:row", ns):
            values: list[str] = []
            for cell in row.findall("main:c", ns):
                cell_ref = cell.attrib.get("r", "")
                column_index = _xlsx_col_index(cell_ref)
                while len(values) <= column_index:
                    values.append("")
                raw = cell.find("main:v", ns)
                value = "" if raw is None else str(raw.text or "")
                if cell.attrib.get("t") == "s" and value:
                    value = shared[int(value)]
                values[column_index] = value
            rows.append(values)
        return rows


def fetch_govuk_xlsx_table(session: requests.Session, spec: dict[str, Any]) -> dict[str, Any]:
    xlsx_url = str(spec.get("xlsx_url") or "").strip()
    distribution_name = ""
    if not xlsx_url:
        xlsx_url, distribution_name = _govuk_distribution_url(session, spec, ".xlsx")
    content = _download_binary(session, xlsx_url)
    rows = _xlsx_sheet_rows(content, str(spec["sheet_name"]))
    date_column = str(spec.get("date_column") or "Period")
    value_column = str(spec["value_column"])
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
        raise ValueError(f"Columns {date_column!r}/{value_column!r} not found in XLSX.")

    observations: list[dict[str, Any]] = []
    for row in rows[header_index + 1 :]:
        if len(row) <= max(date_index, value_index):
            continue
        obs_date = _normalise_date(str(row[date_index]))
        raw_value = row[value_index]
        if not obs_date or raw_value in (None, "", "."):
            continue
        try:
            value = float(str(raw_value).replace(",", ""))
        except (TypeError, ValueError):
            continue
        observations.append({"date": obs_date, "value": value})
    observations.sort(key=lambda item: item["date"])
    observations = _apply_transform(_start_filter(observations, spec.get("start_date")), spec)
    return {
        **spec,
        "observations": observations,
        "provider_updated": observations[-1]["date"] if observations else "",
        "api_url": xlsx_url,
        "distribution_name": distribution_name,
    }


def _ods_cell_text(cell: ET.Element) -> str:
    ns = {
        "text": "urn:oasis:names:tc:opendocument:xmlns:text:1.0",
        "office": "urn:oasis:names:tc:opendocument:xmlns:office:1.0",
    }
    text_values = ["".join(node.itertext()) for node in cell.findall(".//text:p", ns)]
    text = " ".join(value for value in text_values if value).strip()
    if text:
        return text
    return (
        cell.attrib.get(f"{{{ns['office']}}}date-value")
        or cell.attrib.get(f"{{{ns['office']}}}value")
        or ""
    )


def _ods_sheet_rows(content: bytes, sheet_name: str) -> list[list[str]]:
    ns = {"table": "urn:oasis:names:tc:opendocument:xmlns:table:1.0"}
    with ZipFile(io.BytesIO(content)) as workbook:
        root = ET.fromstring(workbook.read("content.xml"))
    table_name_key = f"{{{ns['table']}}}name"
    repeat_rows_key = f"{{{ns['table']}}}number-rows-repeated"
    repeat_cols_key = f"{{{ns['table']}}}number-columns-repeated"
    for table in root.findall(".//table:table", ns):
        if table.attrib.get(table_name_key) != sheet_name:
            continue
        rows: list[list[str]] = []
        for row in table.findall("table:table-row", ns):
            row_repeat = min(int(row.attrib.get(repeat_rows_key, "1")), 20)
            values: list[str] = []
            for cell in row.findall("table:table-cell", ns):
                column_repeat = min(int(cell.attrib.get(repeat_cols_key, "1")), 100)
                values.extend([_ods_cell_text(cell)] * column_repeat)
            for _ in range(row_repeat):
                rows.append(values.copy())
        return rows
    raise ValueError(f"Worksheet {sheet_name!r} not found in ODS.")


def fetch_govuk_ods_table(session: requests.Session, spec: dict[str, Any]) -> dict[str, Any]:
    ods_url = str(spec.get("ods_url") or "").strip()
    distribution_name = ""
    if not ods_url:
        ods_url, distribution_name = _govuk_distribution_url(session, spec, ".ods")
    content = _download_binary(session, ods_url)
    if not content.startswith(b"PK"):
        raise RuntimeError("GOV.UK ODS URL did not return a zipped ODS workbook.")
    rows = _ods_sheet_rows(content, str(spec["sheet_name"]))
    date_column = str(spec.get("date_column") or "Month and year")
    value_column = str(spec["value_column"])
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
        raise ValueError(f"Columns {date_column!r}/{value_column!r} not found in ODS.")
    observations = _table_observations(
        rows,
        spec,
        header_index=header_index,
        date_index=date_index,
        value_index=value_index,
    )
    return {
        **spec,
        "observations": observations,
        "provider_updated": observations[-1]["date"] if observations else "",
        "api_url": ods_url,
        "distribution_name": distribution_name,
    }


def fetch_ons_xlsx_table(session: requests.Session, spec: dict[str, Any]) -> dict[str, Any]:
    """Fetch a simple ONS xlsx worksheet with a Time period column and one value column."""
    xlsx_candidates = [(str(spec["xlsx_url"]), "configured")] if spec.get("xlsx_url") else _ons_distribution_candidates(
        session,
        spec,
        ".xlsx",
    )
    last_error: Exception | None = None
    for xlsx_url, distribution_name in xlsx_candidates:
        try:
            content = _download_binary(session, xlsx_url)
            if not content.startswith(b"PK"):
                raise RuntimeError("ONS xlsx candidate did not return an XLSX workbook.")
            rows = _xlsx_sheet_rows(content, str(spec["sheet_name"]))
            date_column = str(spec.get("date_column") or "Time period")
            value_column = str(spec["value_column"])
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
                raise ValueError(f"Columns {date_column!r}/{value_column!r} not found in ONS XLSX.")
            observations = _table_observations(
                rows,
                spec,
                header_index=header_index,
                date_index=date_index,
                value_index=value_index,
            )
            return {
                **spec,
                "observations": observations,
                "provider_updated": observations[-1]["date"] if observations else "",
                "api_url": xlsx_url,
                "distribution_name": distribution_name,
            }
        except Exception as exc:  # noqa: BLE001 - try visible dated ONS links if the current link is stale.
            last_error = exc
            continue
    raise last_error or RuntimeError("No ONS XLSX candidate could be parsed.")


def fetch_ons_horizontal_csv_table(session: requests.Session, spec: dict[str, Any]) -> dict[str, Any]:
    """Fetch an ONS CSV where multiple tables are laid out horizontally."""
    csv_candidates = [(str(spec["csv_url"]), "configured")] if spec.get("csv_url") else _ons_distribution_candidates(
        session,
        spec,
        ".csv",
    )
    table_title = str(spec["table_title_contains"]).lower()
    date_column = str(spec.get("date_column") or "Time period")
    value_column = str(spec["value_column"])
    last_error: Exception | None = None
    for csv_url, distribution_name in csv_candidates:
        try:
            response = session.get(csv_url, headers={"User-Agent": USER_AGENT}, timeout=(4, 20))
            response.raise_for_status()
            rows = list(csv.reader(io.StringIO(response.content.decode("utf-8-sig", errors="replace"))))
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
                raise ValueError(f"Table title containing {table_title!r} not found in ONS CSV.")

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
                raise ValueError(f"Columns {date_column!r}/{value_column!r} not found in ONS CSV.")
            observations = _table_observations(
                rows,
                spec,
                header_index=header_index,
                date_index=date_index,
                value_index=value_index,
            )
            return {
                **spec,
                "observations": observations,
                "provider_updated": observations[-1]["date"] if observations else "",
                "api_url": csv_url,
                "distribution_name": distribution_name,
            }
        except Exception as exc:  # noqa: BLE001 - try the next official ONS download candidate.
            last_error = exc
            continue
    raise last_error or RuntimeError("No ONS horizontal CSV candidate could be parsed.")


def fetch_obr_xlsx_row(session: requests.Session, spec: dict[str, Any]) -> dict[str, Any]:
    """Fetch one horizontal row from an OBR EFO workbook.

    OBR EFO tables often put forecast years across columns and indicator names
    down rows. This adapter keeps those fiscal forecast additions config-driven.
    """
    xlsx_url = str(spec.get("xlsx_url") or "").strip()
    if not xlsx_url:
        raise ValueError("OBR XLSX row fetcher requires xlsx_url.")
    content = _download_binary(session, xlsx_url)
    if not content.startswith(b"PK"):
        raise RuntimeError("OBR xlsx URL did not return an XLSX workbook.")
    rows = _xlsx_sheet_rows(content, str(spec["sheet_name"]))
    row_label = _clean_text(str(spec["row_label"])).lower()
    context = _clean_text(str(spec.get("context_above_contains") or "")).lower()
    target_index = -1
    for index, row in enumerate(rows):
        cleaned = [_clean_text(str(cell)).lower() for cell in row]
        if row_label not in cleaned:
            continue
        if context:
            above = " ".join(
                " ".join(_clean_text(str(cell)).lower() for cell in rows[above_index])
                for above_index in range(max(0, index - 8), index)
            )
            if context not in above:
                continue
        target_index = index
        break
    if target_index < 0:
        raise ValueError(f"OBR row {spec['row_label']!r} not found in {spec['sheet_name']!r}.")

    header_index = -1
    header_dates: dict[int, str] = {}
    for index in range(target_index - 1, -1, -1):
        candidates = {
            column_index: _normalise_obr_period(str(cell))
            for column_index, cell in enumerate(rows[index])
            if _normalise_obr_period(str(cell))
        }
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
        if raw_value in (None, "", ".", "-", " - "):
            continue
        try:
            value = float(str(raw_value).replace(",", ""))
        except (TypeError, ValueError):
            continue
        observations.append({"date": obs_date, "value": value})
    observations.sort(key=lambda item: item["date"])
    observations = _apply_transform(_start_filter(observations, spec.get("start_date")), spec)
    return {
        **spec,
        "observations": observations,
        "provider_updated": observations[-1]["date"] if observations else "",
        "api_url": xlsx_url,
    }


def validate_series(series: dict[str, Any]) -> dict[str, Any]:
    observations = series.get("observations") or []
    notes: list[str] = []
    if not observations:
        return {**series, "quality_status": "unavailable", "quality_notes": ["No observations returned."]}
    if len(observations) < 12:
        notes.append("Short history.")

    latest_date = _parse_date(str(observations[-1]["date"]))
    frequency = str(series.get("frequency", "")).lower()
    if latest_date:
        age_days = (date.today() - latest_date).days
        max_age_days = series.get("max_age_days")
        if max_age_days is not None:
            try:
                if age_days > int(max_age_days):
                    notes.append(
                        f"Series exceeds configured freshness limit ({max_age_days} days); latest observation is {observations[-1]['date']}."
                    )
            except (TypeError, ValueError):
                pass
        if frequency == "monthly" and age_days > 150:
            notes.append(f"Monthly series looks stale; latest observation is {observations[-1]['date']}.")
        elif frequency == "weekly" and age_days > 45:
            notes.append(f"Weekly series looks stale; latest observation is {observations[-1]['date']}.")
        elif frequency == "quarterly" and age_days > 330:
            notes.append(f"Quarterly series looks stale; latest observation is {observations[-1]['date']}.")
        elif frequency == "annual" and latest_date.year < date.today().year - 2:
            notes.append(f"Lagged annual series; latest observation is {latest_date.year}.")
    else:
        notes.append("Latest date could not be parsed.")

    source_name = str(series.get("source_name", ""))
    if "FRED" in source_name:
        notes.append("FRED is used as a reproducible mirror; release-day work should check the native source.")
    if series.get("caveat_en"):
        notes.append(series["caveat_en"])

    quality_floor = str(series.get("quality_floor", ""))
    if quality_floor == "low_confidence":
        status = "low_confidence"
    elif not notes:
        status = "verified"
    elif len(notes) <= 2:
        status = "watch"
    else:
        status = "low_confidence"
    return {**series, "quality_status": status, "quality_notes": notes[:3]}


def _fetch_one(spec: dict[str, Any]) -> dict[str, Any]:
    session = requests.Session()

    def operation() -> dict[str, Any]:
        fetcher = spec.get("fetcher")
        if fetcher == "fred":
            return fetch_fred(session, spec)
        if fetcher == "ons_timeseries":
            return fetch_ons_timeseries(session, spec)
        if fetcher == "boe_iadb":
            return fetch_boe_iadb(session, spec)
        if fetcher == "boe_bank_rate":
            return fetch_boe_bank_rate(session, spec)
        if fetcher == "govuk_road_fuel":
            return fetch_govuk_road_fuel(session, spec)
        if fetcher == "govuk_xlsx_table":
            return fetch_govuk_xlsx_table(session, spec)
        if fetcher == "govuk_ods_table":
            return fetch_govuk_ods_table(session, spec)
        if fetcher == "ons_xlsx_table":
            return fetch_ons_xlsx_table(session, spec)
        if fetcher == "ons_horizontal_csv_table":
            return fetch_ons_horizontal_csv_table(session, spec)
        if fetcher == "obr_xlsx_row":
            return fetch_obr_xlsx_row(session, spec)
        raise ValueError(f"Unknown fetcher: {fetcher}")

    try:
        series = guarded_source_call(
            country="UK",
            indicator_id=str(spec.get("id") or "unknown"),
            source_id=str(spec.get("fetcher") or "unknown"),
            operation=operation,
        )
    except Exception as exc:  # noqa: BLE001 - structured degradation is intentional.
        series = failure_series(spec, exc)
    return validate_series(series)


def fetch_all(config: dict[str, Any]) -> list[dict[str, Any]]:
    specs = list(config.get("indicators", []))
    series_list: list[dict[str, Any] | None] = [None] * len(specs)
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = {executor.submit(_fetch_one, spec): index for index, spec in enumerate(specs)}
        for future in as_completed(futures):
            index = futures[future]
            spec = specs[index]
            try:
                series_list[index] = future.result()
            except Exception as exc:  # noqa: BLE001 - data page should degrade instead of crashing.
                series_list[index] = validate_series({
                    **spec,
                    "observations": [],
                    "quality_status": "unavailable",
                    "quality_notes": [f"Fetch failed: {exc}"],
                })
    unavailable_indexes = [
        index
        for index, item in enumerate(series_list)
        if item is not None and item.get("quality_status") == "unavailable"
    ]
    for index in unavailable_indexes:
        for _ in range(2):
            retry = _fetch_one(specs[index])
            if retry.get("quality_status") != "unavailable":
                series_list[index] = retry
                break
    return [item for item in series_list if item is not None]


def _render_cards(series_list: list[dict[str, Any]]) -> str:
    headline_ids = [
        "real_gdp_qoq",
        "cpi_yoy",
        "unemployment_rate",
        "bank_rate",
        "psnd_ex_banks_gdp",
        "gbp_reer",
    ]
    by_id = {item["id"]: item for item in series_list}
    cards: list[str] = []
    for indicator_id in headline_ids:
        series = by_id.get(indicator_id)
        latest = _latest(series) if series else None
        if not series or not latest:
            continue
        cards.append(f"""
<div class="data-card">
  <span><span data-lang="en">{escape(series['label_en'])}</span><span data-lang="zh">{escape(series['label_zh'])}</span></span>
  <strong>{_format_value(float(latest['value']), series.get('unit', ''))}</strong>
  <small>{escape(str(latest['date']))} · {escape(series.get('source_name', ''))}</small>
</div>""")
    return "\n".join(cards)


def _key_series_latest(series_list: list[dict[str, Any]], indicator_ids: list[str]) -> list[dict[str, Any]]:
    by_id = {item["id"]: item for item in series_list}
    rows: list[dict[str, Any]] = []
    for indicator_id in indicator_ids:
        series = by_id.get(indicator_id)
        latest = _latest(series) if series else None
        if not series or not latest:
            continue
        unit = str(series.get("unit", ""))
        value = float(latest["value"])
        rows.append({
            "id": indicator_id,
            "label_en": series.get("label_en", indicator_id),
            "label_zh": series.get("label_zh", indicator_id),
            "latest_date": str(latest["date"]),
            "latest_value": value,
            "latest_display": f"{_format_value(value, unit)} {unit}".strip(),
            "frequency": series.get("frequency", ""),
            "source_name": series.get("source_name", ""),
            "series": series.get("series", ""),
            "quality_status": series.get("quality_status", ""),
        })
    return rows


def render_html(config: dict[str, Any], series_list: list[dict[str, Any]]) -> str:
    chart_count = sum(1 for item in series_list if item.get("observations"))
    source_count = len({item.get("source_name") for item in series_list if item.get("observations")})
    gap_count = len(config.get("data_gaps", []))
    low_count = sum(1 for item in series_list if item.get("quality_status") == "low_confidence" and item.get("observations"))
    generated_date = datetime.now(UTC).date().isoformat()
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>UK Dashboard</title>
<script src="https://cdn.plot.ly/plotly-2.32.0.min.js"></script>
<style>{CSS}</style>
</head>
<body data-dashboard-view="core">
<div class="topbar">
  <a href="../index.html" style="text-decoration:none;color:inherit;"><div class="brand">East Meridian <span>/ Macro Dashboard</span></div></a>
  <nav class="country-nav" aria-label="country dashboards">
    <a href="hungary.html">HU</a>
    <a href="poland.html">PL</a>
    <a href="czechia.html">CZ</a>
    <a href="romania.html">RO</a>
    <a href="china.html">CN</a>
    <a href="japan.html">JP</a>
    <a href="south_africa.html">ZA</a>
    <a href="uk.html" class="active">UK</a>
    <a href="us.html">US</a>
  </nav>
  <button class="lang-toggle" onclick="toggleLang()" id="lang-btn">中文</button>
</div>

<main class="container">
  <header>
    <h1><span data-lang="en">UK Dashboard</span><span data-lang="zh">英国 Dashboard</span></h1>
    <p class="subtitle"><span data-lang="en">A chart-and-data-first UK macro page aligned to the GS <em>Understanding UK Economic Statistics</em> framework. The page prioritises reproducible public series from native ONS and Bank of England endpoints, while keeping FRED/OECD/BIS/IMF mirrors for broader public-data coverage and preserving vendor-controlled GS/PMI/CBI/RICS items as explicit data gaps.</span><span data-lang="zh">一个以图表和数据为核心的英国宏观页面，结构对齐GS <em>Understanding UK Economic Statistics</em> 框架。页面优先使用ONS与Bank of England原生可复跑公开接口，同时保留FRED/OECD/BIS/IMF镜像作为更广覆盖的公开数据骨架；GS、PMI、CBI、RICS等供应商控制指标则明确列为数据缺口。</span></p>
    <div class="meta-row">
      <span class="meta-chip">{chart_count} <span data-lang="en">charts</span><span data-lang="zh">张图</span></span>
      <span class="meta-chip">{source_count} <span data-lang="en">public source groups</span><span data-lang="zh">组公开来源</span></span>
      <span class="meta-chip">{gap_count} <span data-lang="en">official/vendor gaps tracked</span><span data-lang="zh">个官方/供应商缺口</span></span>
      <span class="meta-chip">{low_count} <span data-lang="en">low-confidence charts</span><span data-lang="zh">张低置信图</span></span>
    </div>
  </header>

  <section class="data-grid" aria-label="latest data cards">
    {_render_cards(series_list)}
  </section>

  <nav class="toc" aria-label="section navigation">
    {_section_nav(config)}
  </nav>

  <div class="view-switch" role="group" aria-label="chart density">
    <span><span data-lang="en">Chart view</span><span data-lang="zh">图表视图</span></span>
    <button type="button" data-view-option="core" aria-pressed="true" onclick="setDashboardView('core')"><span data-lang="en">Core 48</span><span data-lang="zh">核心 48</span></button>
    <button type="button" data-view-option="deep" aria-pressed="false" onclick="setDashboardView('deep')"><span data-lang="en">All deep-dive charts</span><span data-lang="zh">全部深度指标</span></button>
  </div>

  <div class="data-note">
    <span data-lang="en">Data policy: no fabricated proxies. FRED remains the durable public backbone, while release-sensitive UK series prefer native ONS time-series JSON and Bank of England IADB CSV endpoints when validated.</span>
    <span data-lang="zh">数据原则：不制造假proxy。FRED继续作为稳定公开骨架；对发布时效更敏感的英国序列，在验证后优先使用ONS time-series JSON与Bank of England IADB CSV原生接口。</span>
  </div>

  {_sections_html(config, series_list, "UK")}

  <section class="panel" id="data-gaps">
    <div class="section-title">
      <p>Pipeline</p>
      <h2><span data-lang="en">Official Data Gaps</span><span data-lang="zh">官方数据缺口</span></h2>
      <div class="logic"><span data-lang="en">These are GS-framework indicators that matter for UK macro trading but are not yet rendered because a reproducible public adapter or license-safe source has not been validated.</span><span data-lang="zh">这些是GS框架中对英国宏观交易重要的指标，但由于尚未验证可复跑公开adapter或授权安全数据源，当前暂不渲染为图。</span></div>
    </div>
    <table class="gaps-table">
      <thead><tr><th>Section</th><th>Indicator family</th><th>Status</th></tr></thead>
      <tbody>{_gaps_html(config)}</tbody>
    </table>
  </section>

  <footer class="page-footer">
    <span data-lang="en">Research artefact only, not investment advice. Generated {generated_date} from <code>config/uk_indicators.yaml</code>.</span>
    <span data-lang="zh">仅为研究工具，不构成投资建议。生成日期 {generated_date}，配置来源 <code>config/uk_indicators.yaml</code>。</span>
  </footer>
</main>

<script>
function resizeCharts() {{
  if (!window.Plotly) return;
  document.querySelectorAll('.plotly-chart').forEach(function(el) {{
    Plotly.Plots.resize(el);
  }});
}}
function setDashboardView(view) {{
  var normalized = view === 'deep' ? 'deep' : 'core';
  document.body.dataset.dashboardView = normalized;
  localStorage.setItem('cp-dashboard-view', normalized);
  document.querySelectorAll('[data-view-option]').forEach(function(btn) {{
    btn.setAttribute('aria-pressed', String(btn.dataset.viewOption === normalized));
  }});
  requestAnimationFrame(resizeCharts);
}}
(function() {{
  var saved = localStorage.getItem('cp-lang');
  if (saved === 'zh') {{
    document.documentElement.lang = 'zh';
    document.getElementById('lang-btn').textContent = 'English';
  }}
  setDashboardView(localStorage.getItem('cp-dashboard-view') || 'core');
  requestAnimationFrame(resizeCharts);
}})();
function toggleLang() {{
  var html = document.documentElement;
  var btn = document.getElementById('lang-btn');
  if (html.lang === 'en') {{
    html.lang = 'zh';
    btn.textContent = 'English';
    localStorage.setItem('cp-lang', 'zh');
  }} else {{
    html.lang = 'en';
    btn.textContent = '中文';
    localStorage.setItem('cp-lang', 'en');
  }}
  requestAnimationFrame(resizeCharts);
}}
window.addEventListener('resize', resizeCharts);
</script>
</body>
</html>
"""


def _index_card(summary: dict[str, Any]) -> str:
    return f"""
  <!-- UK dashboard card -->
  <a href="uk.html" class="card clean">
    <div class="card-kicker">GBP · BoE · UK GS-statistics page</div>
    <h2>United Kingdom</h2>
    <div class="stats">
      <div class="stat"><span>Rendered charts</span><strong>{summary['charts']}</strong></div>
      <div class="stat"><span>Proxy fills</span><strong>0</strong></div>
      <div class="stat"><span>Data gaps tracked</span><strong>{summary['data_gaps']}</strong></div>
      <div class="stat"><span>Bank Rate</span><strong>{escape(summary.get('bank_rate_latest', 'n/a'))}</strong></div>
      <div class="stat"><span>Source groups</span><strong>{summary['source_groups']}</strong></div>
      <div class="stat"><span>Framework</span><strong>GS UK statistics logic</strong></div>
    </div>
  </a>
  <!-- /UK dashboard card -->"""


def inject_output_index(summary: dict[str, Any]) -> None:
    index_path = OUTPUT / "index.html"
    if not index_path.exists():
        return
    html = index_path.read_text()
    html = re.sub(r"\n\s*<!-- UK dashboard card -->.*?<!-- /UK dashboard card -->", "", html, flags=re.S)
    marker = '  </section>\n  <nav class="links"'
    if marker in html:
        html = html.replace(marker, _index_card(summary) + "\n  </section>\n  <nav class=\"links\"", 1)
    html = re.sub(r"Macro Dashboard Archive · CEE-4 v4 \+ China[^<]*", "Macro Dashboard Archive · CEE-4 v4 + China + Japan + South Africa + UK + US", html)
    html = re.sub(
        r"Generated archive entry for the proxy-free CEE-4 dashboards plus the [^.]*\.",
        "Generated archive entry for the proxy-free CEE-4 dashboards plus the China, Japan, South Africa, UK, and US data-first pages.",
        html,
    )
    html = html.replace("<strong>5</strong><span>country dashboards</span>", "<strong>6</strong><span>country dashboards</span>")
    _write_clean(index_path, html)


def build(data_mode: str | None = None) -> Path:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    data_mode = (data_mode or os.environ.get("COUNTRY_PRIMER_DATA_MODE") or "refresh").strip().lower()
    config = _load_config()
    if data_mode == "snapshot":
        series_list = load_canonical_data_first_frame(CANONICAL_JSON, config)
    else:
        SOURCE_HEALTH.reset()
        series_list = fetch_all(config)
        series_list = retain_last_known_good_series(series_list, CANONICAL_JSON, config)
    apply_quality_assessments(series_list)
    _write_clean(OUT_HTML, render_html(config, series_list))

    charted = [item for item in series_list if item.get("observations")]
    bank_rate = next((item for item in charted if item["id"] == "bank_rate"), None)
    bank_latest = _latest(bank_rate) if bank_rate else None
    summary = {
        "file": OUT_HTML.name,
        "generated": datetime.now(UTC).isoformat(),
        "charts": len(charted),
        "source_groups": len({item.get("source_name") for item in charted}),
        "data_gaps": len(config.get("data_gaps", [])),
        "low_confidence": sum(1 for item in charted if item.get("quality_status") == "low_confidence"),
        "bank_rate_latest": (
            f"{float(bank_latest['value']):.2f}% ({bank_latest['date']})" if bank_latest else "n/a"
        ),
        "key_series_latest": _key_series_latest(charted, SUMMARY_KEY_IDS),
        "unavailable": [item["id"] for item in series_list if not item.get("observations")],
        "data_mode": data_mode,
    }
    summary["canonical_frame"] = (
        canonical_frame_metadata(CANONICAL_JSON)
        if data_mode == "snapshot"
        else write_canonical_data_first_frame(CANONICAL_JSON, "UK", series_list)
    )
    summary.update(build_summary_metadata(config, series_list, "UK"))
    SUMMARY_JSON.write_text(json.dumps(summary, indent=2, ensure_ascii=False))
    if data_mode != "snapshot":
        write_source_health_report(OUTPUT / "source_health.json", ["UK"])
    inject_output_index(summary)
    if not os.environ.get("COUNTRY_PRIMER_SKIP_ARCHIVE"):
        from build_dashboard_archive import build_archive
        build_archive()
    return OUT_HTML


if __name__ == "__main__":
    path = build()
    print(f"Wrote {path} ({path.stat().st_size:,} bytes)")
