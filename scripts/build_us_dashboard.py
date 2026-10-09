"""Build the US macro dashboard from GS US-statistics-aligned config.

The US page follows the chapter logic of Goldman Sachs' Understanding US
Economic Statistics, while modernizing the policy/financial plumbing for 2026.
FRED is the public data backbone. If FRED_API_KEY is set, the official FRED API
is used; otherwise the script falls back to FRED's public graph CSV endpoint.
"""
from __future__ import annotations

import json
import csv
import io
import os
import re
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import UTC, date, datetime
from email.utils import parsedate_to_datetime
from html import escape
from pathlib import Path
from typing import Any

import requests
import yaml

from dashboard_summary_utils import (
    apply_quality_assessments,
    build_summary_metadata,
    canonical_frame_metadata,
    load_canonical_data_first_frame,
    retain_last_known_good_series,
    track_revisions_and_vintages,
    shift_calendar_periods,
    write_canonical_data_first_frame,
)
from country_primer.page_renderer import build_country_page
from country_primer.data_first_pipeline import fetch_all
from build_uk_dashboard import FRED_API_URL, FRED_GRAPH_URL, fetch_fred, validate_series
from country_primer.source_health import (
    SOURCE_HEALTH,
    failure_series,
    guarded_source_call,
    write_source_health_report,
)


ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "config" / "us_indicators.yaml"
OUTPUT = ROOT / "output"
OUT_HTML = OUTPUT / "us.html"
SUMMARY_JSON = OUTPUT / "us_dashboard_summary.json"
CANONICAL_JSON = OUTPUT / "us_canonical_frame.json"
SUMMARY_KEY_IDS = [
    "real_gdp_growth",
    "retail_sales_mom",
    "retail_sales_growth",
    "real_pce_mom",
    "real_pce_growth",
    "housing_starts",
    "nonfarm_payrolls_change",
    "unemployment_rate",
    "cpi_inflation",
    "core_cpi_mom",
    "core_cpi_inflation",
    "core_pce_inflation",
    "mortgage_30y_rate",
    "daily_fed_funds",
    "fed_target_upper",
    "federal_debt_gdp",
]
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 Chrome/124.0 Safari/537.36"
)
TREASURY_AUCTIONS_URL = "https://api.fiscaldata.treasury.gov/services/api/fiscal_service/v1/accounting/od/auctions_query"
BLS_API_URL = "https://api.bls.gov/publicAPI/v2/timeseries/data/"
BLS_BED_CACHE_PATH = ROOT / "data" / "us_bls_bed_cache.json"
BLS_LOCK = threading.Lock()
BLS_CACHE: dict[str, list[dict[str, Any]]] = {}
BLS_BATCH_ERROR: str | None = None


def _load_config() -> dict[str, Any]:
    return yaml.safe_load(CONFIG_PATH.read_text()) or {}


def _lag_for_frequency(frequency: str) -> int:
    frequency = str(frequency or "").lower()
    if frequency == "weekly":
        return 52
    if frequency == "quarterly":
        return 4
    if frequency == "annual":
        return 1
    return 12


def _parse_obs_date(value: Any) -> date | None:
    try:
        return date.fromisoformat(str(value)[:10])
    except (TypeError, ValueError):
        return None


def _lookup_base(
    by_date: dict[str, Any], frequency: str, periods: int, item_date: date
) -> float | None:
    """Return the value observed exactly `periods` calendar periods before
    `item_date`, or None if that exact date has no observation.

    Looks up the base by its expected calendar date rather than a fixed
    array offset — see shift_calendar_periods for why: one interior gap
    would otherwise misalign every later point permanently, not just the
    one next to the gap.
    """
    expected_date = shift_calendar_periods(item_date, frequency, periods)
    return by_date.get(expected_date.isoformat())


def _apply_transform(series: dict[str, Any]) -> dict[str, Any]:
    transform = series.get("transform")
    observations = list(series.get("observations") or [])
    if not transform or not observations:
        return series

    frequency = str(series.get("frequency", ""))
    by_date: dict[str, float] = {}
    for item in observations:
        parsed = _parse_obs_date(item.get("date"))
        if parsed is not None:
            by_date[parsed.isoformat()] = float(item["value"])

    transformed: list[dict[str, Any]] = []
    if transform == "yoy_pct":
        lag = _lag_for_frequency(frequency)
        for item in observations:
            item_date = _parse_obs_date(item.get("date"))
            if item_date is None:
                continue
            base = _lookup_base(by_date, frequency, lag, item_date)
            if base is None or base == 0:
                continue
            value = float(item["value"])
            transformed.append({"date": item["date"], "value": ((value / base) - 1.0) * 100.0})
    elif transform == "diff":
        for item in observations:
            item_date = _parse_obs_date(item.get("date"))
            if item_date is None:
                continue
            base = _lookup_base(by_date, frequency, 1, item_date)
            if base is None:
                continue
            transformed.append({"date": item["date"], "value": float(item["value"]) - base})
    elif transform == "pct_change":
        for item in observations:
            item_date = _parse_obs_date(item.get("date"))
            if item_date is None:
                continue
            base = _lookup_base(by_date, frequency, 1, item_date)
            if base is None or base == 0:
                continue
            value = float(item["value"])
            transformed.append({"date": item["date"], "value": ((value / base) - 1.0) * 100.0})
    else:
        return {
            **series,
            "observations": [],
            "quality_status": "unavailable",
            "quality_notes": [f"Unknown transform: {transform}."],
        }
    return {**series, "observations": transformed}


def _fred_graph_observations_us(session: requests.Session, spec: dict[str, Any], read_timeout: int) -> tuple[list[dict[str, Any]], str]:
    params = {"id": spec["series"]}
    if spec.get("start_date"):
        params["cosd"] = spec["start_date"]
    response = session.get(
        FRED_GRAPH_URL,
        params=params,
        headers={"User-Agent": USER_AGENT, "Accept": "text/csv,text/plain,*/*"},
        timeout=(5, read_timeout),
    )
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


def fetch_fred_us(session: requests.Session, spec: dict[str, Any]) -> dict[str, Any]:
    if os.environ.get("FRED_API_KEY", "").strip():
        return fetch_fred(session, spec)

    last_error: Exception | None = None
    for read_timeout in (8, 16):
        try:
            observations, provider_updated = _fred_graph_observations_us(session, spec, read_timeout)
            if not observations:
                raise RuntimeError("FRED graph returned no observations.")
            if provider_updated:
                try:
                    provider_updated = parsedate_to_datetime(provider_updated).date().isoformat()
                except (TypeError, ValueError):
                    provider_updated = str(provider_updated)
            return {
                **spec,
                "observations": observations,
                "provider_updated": provider_updated or (observations[-1]["date"] if observations else ""),
                "api_url": FRED_GRAPH_URL,
            }
        except Exception as exc:  # noqa: BLE001 - retry with a larger read timeout.
            last_error = exc
    raise last_error or RuntimeError("FRED graph fetch failed.")


def _numeric(value: Any) -> float | None:
    if value in (None, "", "null", "."):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _bls_period_to_date(year: str, period: str) -> str | None:
    if not period.startswith("Q"):
        return None
    quarter_month = {
        "Q01": "01",
        "Q02": "04",
        "Q03": "07",
        "Q04": "10",
    }.get(period)
    if not quarter_month:
        return None
    return f"{year}-{quarter_month}-01"


def _bls_config_specs() -> list[dict[str, Any]]:
    config = _load_config()
    return [item for item in config.get("indicators", []) if item.get("fetcher") == "bls_api"]


def _load_bls_bed_cache() -> dict[str, Any]:
    if not BLS_BED_CACHE_PATH.exists():
        return {}
    try:
        return json.loads(BLS_BED_CACHE_PATH.read_text())
    except json.JSONDecodeError:
        return {}


def _write_bls_bed_cache(observations_by_series: dict[str, list[dict[str, Any]]]) -> None:
    if not observations_by_series or any(not values for values in observations_by_series.values()):
        return
    BLS_BED_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "generated": datetime.now(UTC).isoformat(),
        "source": "BLS public API last-good cache for Business Employment Dynamics series",
        "source_url": BLS_API_URL,
        "series": observations_by_series,
    }
    BLS_BED_CACHE_PATH.write_text(json.dumps(payload, indent=2, sort_keys=True))


def _fetch_bls_batch(session: requests.Session, specs: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    start_year = min(int(str(item.get("start_date", "1992-01-01"))[:4]) for item in specs)
    end_year = datetime.now(UTC).year
    series_ids = sorted({str(item["series"]) for item in specs})
    registration_key = os.environ.get("BLS_API_KEY", "").strip()
    observations_by_series: dict[str, dict[str, float]] = {series_id: {} for series_id in series_ids}

    # BLS public API range limits are tighter without a registration key. Keep
    # the unregistered path conservative so automated refreshes do not drop BED.
    chunk_years = 20 if registration_key else 10
    for chunk_start in range(start_year, end_year + 1, chunk_years):
        chunk_end = min(chunk_start + chunk_years - 1, end_year)
        payload_body: dict[str, Any] = {
            "seriesid": series_ids,
            "startyear": str(chunk_start),
            "endyear": str(chunk_end),
        }
        if registration_key:
            payload_body["registrationkey"] = registration_key

        last_error: Exception | None = None
        for attempt in range(3):
            try:
                response = session.post(
                    BLS_API_URL,
                    json=payload_body,
                    headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
                    timeout=(5, 30),
                )
                response.raise_for_status()
                payload = response.json()
                if payload.get("status") != "REQUEST_SUCCEEDED":
                    raise RuntimeError("; ".join(payload.get("message") or ["BLS API request failed."]))
                break
            except Exception as exc:  # noqa: BLE001 - retry transient BLS throttling/transport failures.
                last_error = exc
                if attempt < 2:
                    time.sleep(1.0 * (2 ** attempt))
        else:
            raise last_error or RuntimeError("BLS API request failed.")

        for series_payload in payload.get("Results", {}).get("series") or []:
            series_id = str(series_payload.get("seriesID", ""))
            if series_id not in observations_by_series:
                continue
            bucket = observations_by_series[series_id]
            for row in series_payload.get("data") or []:
                obs_date = _bls_period_to_date(str(row.get("year", "")), str(row.get("period", "")))
                value = _numeric(row.get("value"))
                if not obs_date or value is None:
                    continue
                bucket[obs_date] = value
        time.sleep(0.25)

    result = {
        series_id: [
            {"date": obs_date, "value": value}
            for obs_date, value in sorted(values.items())
        ]
        for series_id, values in observations_by_series.items()
    }
    _write_bls_bed_cache(result)
    return result


def fetch_bls_api(session: requests.Session, spec: dict[str, Any]) -> dict[str, Any]:
    global BLS_BATCH_ERROR

    series_id = str(spec["series"])
    with BLS_LOCK:
        if series_id not in BLS_CACHE and not BLS_BATCH_ERROR:
            try:
                BLS_CACHE.update(_fetch_bls_batch(session, _bls_config_specs()))
            except Exception as exc:  # noqa: BLE001 - preserve one failure for all BLS specs in this run.
                BLS_BATCH_ERROR = str(exc)
        if BLS_BATCH_ERROR:
            cache_payload = _load_bls_bed_cache()
            observations = list((cache_payload.get("series") or {}).get(series_id) or [])
            if observations:
                cache_date = str(cache_payload.get("generated") or "")[:10]
                caveat_en = (
                    str(spec.get("caveat_en") or "").rstrip()
                    + " Live BLS API quota was unavailable in this run; rendering the last-good official BED cache."
                ).strip()
                caveat_zh = (
                    str(spec.get("caveat_zh") or "").rstrip()
                    + " 本次运行BLS实时API额度不可用；当前渲染最近一次验证成功的官方BED缓存。"
                ).strip()
                return {
                    **spec,
                    "observations": observations,
                    "provider_updated": cache_date or observations[-1]["date"],
                    "api_url": BLS_API_URL,
                    "caveat_en": caveat_en,
                    "caveat_zh": caveat_zh,
                }
            raise RuntimeError(BLS_BATCH_ERROR)
        observations = list(BLS_CACHE.get(series_id) or [])

    start_date = str(spec.get("start_date", ""))
    if start_date:
        observations = [item for item in observations if str(item["date"]) >= start_date]

    if not observations:
        raise RuntimeError(f"BLS API returned no observations for {series_id}.")
    return {
        **spec,
        "observations": observations,
        "provider_updated": observations[-1]["date"],
        "api_url": BLS_API_URL,
    }


def fetch_treasury_auctions(session: requests.Session, spec: dict[str, Any]) -> dict[str, Any]:
    fields = [
        "auction_date",
        "security_type",
        "total_accepted",
        "total_tendered",
        "bid_to_cover_ratio",
        "high_yield",
        "high_investment_rate",
    ]
    filters = [f"auction_date:gte:{spec.get('start_date', '2018-01-01')}", "total_accepted:gt:0"]
    security_types = list(spec.get("security_types") or [])
    if len(security_types) == 1:
        filters.append(f"security_type:eq:{security_types[0]}")
    elif security_types:
        filters.append(f"security_type:in:({','.join(security_types)})")

    rows: list[dict[str, Any]] = []
    page_number = 1
    total_pages = 1
    while page_number <= total_pages:
        response = session.get(
            TREASURY_AUCTIONS_URL,
            params={
                "fields": ",".join(fields),
                "filter": ",".join(filters),
                "page[size]": int(spec.get("page_size", 5000)),
                "page[number]": page_number,
                "sort": "auction_date",
            },
            headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
            timeout=(5, 30),
        )
        response.raise_for_status()
        payload = response.json()
        rows.extend(payload.get("data") or [])
        total_pages = int(payload.get("meta", {}).get("total-pages") or page_number)
        page_number += 1

    aggregate = str(spec.get("aggregate", "monthly_sum"))
    metric = str(spec.get("metric", "total_accepted"))
    scale = float(spec.get("scale", 1))
    buckets: dict[str, dict[str, float]] = {}
    for row in rows:
        auction_date = str(row.get("auction_date") or "")
        if len(auction_date) < 7:
            continue
        month = f"{auction_date[:7]}-01"
        bucket = buckets.setdefault(month, {"value": 0.0, "count": 0.0, "numerator": 0.0, "denominator": 0.0})
        if aggregate == "monthly_weighted_bid_to_cover":
            numerator = _numeric(row.get("total_tendered"))
            denominator = _numeric(row.get("total_accepted"))
            if numerator is None or denominator in (None, 0):
                continue
            bucket["numerator"] += numerator
            bucket["denominator"] += denominator
        else:
            value = _numeric(row.get(metric))
            if value is None:
                continue
            bucket["value"] += value
            bucket["count"] += 1

    observations: list[dict[str, Any]] = []
    for month, bucket in sorted(buckets.items()):
        if aggregate == "monthly_weighted_bid_to_cover":
            denominator = bucket["denominator"]
            if denominator == 0:
                continue
            value = bucket["numerator"] / denominator
        elif aggregate == "monthly_average":
            count = bucket["count"]
            if count == 0:
                continue
            value = bucket["value"] / count
        else:
            value = bucket["value"]
        observations.append({"date": month, "value": value / scale})

    if not observations:
        raise RuntimeError("Treasury FiscalData returned no completed auction observations.")
    return {
        **spec,
        "observations": observations,
        "provider_updated": observations[-1]["date"],
        "api_url": TREASURY_AUCTIONS_URL,
    }



def inject_output_index(summary: dict[str, Any]) -> None:
    index_path = OUTPUT / "index.html"
    if not index_path.exists():
        return
    html = index_path.read_text()
    html = re.sub(r"\n\s*<!-- US dashboard card -->.*?<!-- /US dashboard card -->", "", html, flags=re.S)
    card = f'''
  <!-- US dashboard card -->
  <a href="us.html" class="card clean">
    <div class="card-kicker">USD · FED · US data-first page</div>
    <h2>United States</h2>
    <div class="stats">
      <div class="stat"><span>Rendered charts</span><strong>{summary['charts']}</strong></div>
      <div class="stat"><span>Proxy fills</span><strong>0</strong></div>
      <div class="stat"><span>Official gaps tracked</span><strong>{summary['data_gaps']}</strong></div>
      <div class="stat"><span>Fed Funds Rate</span><strong>{summary.get('fed_funds_latest', 'n/a')}</strong></div>
      <div class="stat"><span>Source groups</span><strong>{summary['source_groups']}</strong></div>
      <div class="stat"><span>Framework</span><strong>GS US statistics logic</strong></div>
    </div>
  </a>
  <!-- /US dashboard card -->'''
    marker = '  </section>\n  <nav class="links"'
    if marker in html:
        html = html.replace(marker, card + "\n  </section>\n  <nav class=\"links\"", 1)

    # ensure it says 6 country dashboards
    html = re.sub(r"Macro Dashboard Archive · CEE-4 v4 \+ China[^<]*", "Macro Dashboard Archive · CEE-4 v4 + China + Japan + South Africa + UK + US", html)
    html = re.sub(
        r"Generated archive entry for the proxy-free CEE-4 dashboards plus the [^.]*\.",
        "Generated archive entry for the proxy-free CEE-4 dashboards plus the China, Japan, South Africa, UK, and US data-first pages.",
        html,
    )
    html = html.replace("<strong>5</strong><span>country dashboards</span>", "<strong>6</strong><span>country dashboards</span>")

    from country_primer.page_renderer import _write_clean
    _write_clean(index_path, html)

def inject_root_index(summary: dict[str, Any]) -> None:
    index_path = ROOT / "index.html"
    if not index_path.exists():
        return
    html = index_path.read_text()
    html = re.sub(
        r'(<a href="output/us.html" class="card">.*?<span class="label">Charts</span><span class="value">)\d+(</span>)',
        rf"\g<1>{summary['charts']}\2",
        html,
        count=1,
        flags=re.S,
    )
    from country_primer.page_renderer import _write_clean
    _write_clean(index_path, html)

def build(data_mode: str | None = None) -> Path:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    data_mode = (data_mode or os.environ.get("COUNTRY_PRIMER_DATA_MODE") or "refresh").strip().lower()
    config = _load_config()

    registry = {
        "fred": lambda spec, cache: _apply_transform(fetch_fred_us(requests.Session(), spec)),
        "bls_api": lambda spec, cache: fetch_bls_api(requests.Session(), spec),
        "treasury_auctions": lambda spec, cache: fetch_treasury_auctions(requests.Session(), spec)
    }

    if data_mode == "snapshot":
        series_list = load_canonical_data_first_frame(CANONICAL_JSON, config)
        cards = []
    else:
        from country_primer.source_health import SOURCE_HEALTH
        SOURCE_HEALTH.reset()
        series_list, cards = fetch_all(config, registry, max_workers=4)
        series_list = retain_last_known_good_series(series_list, CANONICAL_JSON, config)
        series_list = track_revisions_and_vintages(series_list, CANONICAL_JSON, config)

    charted = [item for item in series_list if item.get("observations")]
    min_chart_count = int(config.get("min_chart_count", 55))
    if len(charted) < min_chart_count:
        unavailable = [item["id"] for item in series_list if not item.get("observations")]
        raise RuntimeError(
            f"US dashboard fetched only {len(charted)} charts, below minimum {min_chart_count}. "
            "Set FRED_API_KEY for the official API path or retry later. "
            f"Unavailable indicators: {', '.join(unavailable[:12])}{'...' if len(unavailable) > 12 else ''}"
        )

    fed_funds = next((item for item in charted if item["id"] == "daily_fed_funds"), None)
    if fed_funds is None:
        fed_funds = next((item for item in charted if item["id"] == "effective_fed_funds"), None)

    from country_primer.page_renderer import _latest
    fed_latest = _latest(fed_funds) if fed_funds else None
    fed_latest_str = f"{float(fed_latest['value']):.2f}% ({fed_latest['date']})" if fed_latest else "n/a"

    summary = build_country_page(
        country_code="US",
        config=config,
        series_list=series_list,
        out_html=OUT_HTML,
        summary_json=SUMMARY_JSON,
        canonical_json=CANONICAL_JSON,
        data_mode=data_mode,
        summary_key_ids=["real_gdp_growth", "core_pce_inflation", "unemployment_rate", "nonfarm_payrolls_change", "effective_fed_funds"],
        extra_cards=cards,
        latest_value_key="fed_funds_latest",
        latest_value_display=fed_latest_str
    )

    inject_output_index(summary)
    inject_root_index(summary)

    if not os.environ.get("COUNTRY_PRIMER_SKIP_ARCHIVE"):
        from build_dashboard_archive import build_archive
        build_archive()
    return OUT_HTML

if __name__ == "__main__":
    path = build()
    print(f"Wrote {path} ({path.stat().st_size:,} bytes)")
