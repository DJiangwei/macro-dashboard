"""Build the China macro dashboard from PDF-aligned indicator config.

The China page is intentionally data-first. It follows the section logic from
Goldman Sachs' China statistics guide, but only renders charts from sources
that can be fetched reproducibly from public endpoints in this repo.
"""
from __future__ import annotations

import json
import os
import re
import signal
import time
from csv import DictReader
from datetime import UTC, date, datetime, timedelta
from html import escape
from io import StringIO
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
    write_canonical_data_first_frame,
)
from country_primer.framework import concept_id_for
from country_primer.source_health import (
    SOURCE_HEALTH,
    failure_series,
    guarded_source_call,
    write_source_health_report,
)


ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "config" / "china_indicators.yaml"
OUTPUT = ROOT / "output"
OUT_HTML = OUTPUT / "china.html"
SUMMARY_JSON = OUTPUT / "china_dashboard_summary.json"
CANONICAL_JSON = OUTPUT / "china_canonical_frame.json"
SUMMARY_KEY_IDS = [
    "real_gdp_growth",
    "industrial_value_added_yoy_akshare",
    "fixed_asset_investment_yoy_akshare",
    "commercial_housing_sales_value_eastmoney",
    "real_estate_development_investment_ytd_eastmoney",
    "passenger_vehicle_retail_cpca",
    "new_energy_vehicle_share_cpca",
    "customs_exports_yoy_akshare",
    "usd_cny_midpoint",
    "m2_yoy_akshare",
    "financial_institution_deposits_stock_akshare",
    "vegetable_basket_price_index_akshare",
    "pbc_total_assets_akshare",
    "pbc_reserve_money_akshare",
    "cpi_yoy_akshare",
    "ppi_yoy_akshare",
]

ACCENT = "#8a593d"
INK = "#171310"
MUTED = "#63574e"
PAPER = "rgba(255,252,246,0.90)"


def _load_config() -> dict[str, Any]:
    return yaml.safe_load(CONFIG_PATH.read_text()) or {}


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False)


def _clean_text(value: str) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def _write_clean(path: Path, content: str) -> None:
    path.write_text("\n".join(line.rstrip() for line in content.splitlines()) + "\n")


def _apply_transform(value: float, transform: str | None) -> float:
    if transform == "usd_trn":
        return value / 1_000_000_000_000
    if transform == "usd_mn_to_trn":
        return value / 1_000_000
    if transform == "usd_100mn_to_trn":
        return value / 10_000
    if transform == "usd_thousand_to_bn":
        return value / 1_000_000
    if transform == "cny_100mn_to_trn":
        return value / 10_000
    if transform == "cny_100mn_to_bn":
        return value / 10
    if transform == "cny_10k_to_bn":
        return value / 100_000
    if transform == "cny_yuan_to_trn":
        return value / 1_000_000_000_000
    if transform == "index_100_to_yoy":
        return value - 100
    if transform == "people_billion":
        return value / 1_000_000_000
    return value


def _parse_year(value: str) -> int | None:
    try:
        return int(str(value)[:4])
    except (TypeError, ValueError):
        return None


def _parse_period_date(value: Any) -> str | None:
    if hasattr(value, "date"):
        value = value.date()
    if hasattr(value, "isoformat"):
        return value.isoformat()

    text = _clean_text(str(value))
    if not text or text.lower() in {"nan", "none", "nat"}:
        return None

    match = re.match(r"^(\d{4})-(\d{1,2})-(\d{1,2})(?:\s+\d{1,2}:\d{2}:\d{2})?$", text)
    if match:
        return f"{int(match.group(1)):04d}-{int(match.group(2)):02d}-{int(match.group(3)):02d}"

    match = re.match(r"^(\d{4})(\d{2})$", text)
    if match:
        return f"{int(match.group(1)):04d}-{int(match.group(2)):02d}-01"

    match = re.match(r"^(\d{4})年(\d{1,2})月份$", text)
    if match:
        return f"{int(match.group(1)):04d}-{int(match.group(2)):02d}-01"

    match = re.match(r"^(\d{4})-(\d{1,2})月$", text)
    if match:
        return f"{int(match.group(1)):04d}-{int(match.group(2)):02d}-01"

    match = re.match(r"^(\d{4})年(\d{1,2})月$", text)
    if match:
        return f"{int(match.group(1)):04d}-{int(match.group(2)):02d}-01"

    match = re.match(r"^(\d{4})年(\d{1,2})月(\d{1,2})日$", text)
    if match:
        return f"{int(match.group(1)):04d}-{int(match.group(2)):02d}-{int(match.group(3)):02d}"

    match = re.match(r"^(\d{4})年第(\d)(?:-(\d))?季度$", text)
    if match:
        quarter = int(match.group(3) or match.group(2))
        month = quarter * 3
        day = 31 if month in {3, 12} else 30
        return f"{int(match.group(1)):04d}-{month:02d}-{day:02d}"

    match = re.match(r"^(\d{4})[.\-/](\d{1,2})(?:[.\-/](\d{1,2}))?$", text)
    if match:
        day = int(match.group(3) or 1)
        return f"{int(match.group(1)):04d}-{int(match.group(2)):02d}-{day:02d}"

    return None


def fetch_world_bank(spec: dict[str, Any]) -> dict[str, Any]:
    code = spec["series"]
    url = f"https://api.worldbank.org/v2/country/CHN/indicator/{code}"
    response = requests.get(url, params={"format": "json", "per_page": 20000}, timeout=30)
    response.raise_for_status()
    payload = response.json()
    meta = payload[0] if isinstance(payload, list) and payload else {}
    rows = payload[1] if isinstance(payload, list) and len(payload) > 1 else []
    observations: list[dict[str, Any]] = []
    for row in rows:
        raw_value = row.get("value")
        if raw_value is None:
            continue
        try:
            value = _apply_transform(float(raw_value), spec.get("transform"))
        except (TypeError, ValueError):
            continue
        observations.append({"date": str(row.get("date")), "value": value})
    observations.sort(key=lambda item: item["date"])
    return {
        **spec,
        "observations": observations,
        "provider_updated": meta.get("lastupdated", ""),
        "api_url": url,
    }


def fetch_imf_datamapper(spec: dict[str, Any]) -> dict[str, Any]:
    code = spec["series"]
    url = f"https://www.imf.org/external/datamapper/api/v1/{code}/CHN"
    response = requests.get(url, timeout=45)
    response.raise_for_status()
    payload = response.json()
    country_values = ((payload.get("values") or {}).get(code) or {}).get("CHN") or {}
    observations = [
        {"date": str(year), "value": _apply_transform(float(value), spec.get("transform"))}
        for year, value in country_values.items()
        if value is not None and str(year).isdigit()
    ]
    observations.sort(key=lambda item: int(item["date"]))
    return {
        **spec,
        "observations": observations,
        "provider_updated": datetime.now(UTC).date().isoformat(),
        "api_url": url,
    }


def fetch_fred_graph(spec: dict[str, Any]) -> dict[str, Any]:
    """Fetch a public FRED graph CSV without requiring a runtime API key."""
    code = spec["series"]
    url = "https://fred.stlouisfed.org/graph/fredgraph.csv"
    params = {"id": code}
    if spec.get("start_date"):
        params["cosd"] = str(spec["start_date"])
    response = requests.get(url, params=params, timeout=45)
    response.raise_for_status()
    observations: list[dict[str, Any]] = []
    for row in DictReader(StringIO(response.text)):
        raw_date = row.get("observation_date")
        raw_value = row.get(code)
        if not raw_date or raw_value in (None, "", "."):
            continue
        try:
            value = _apply_transform(float(raw_value), spec.get("transform"))
        except (TypeError, ValueError):
            continue
        observations.append({"date": raw_date, "value": value})
    observations.sort(key=lambda item: item["date"])
    return {
        **spec,
        "observations": observations,
        "provider_updated": observations[-1]["date"] if observations else "",
        "api_url": f"{url}?id={code}",
    }


def _fetch_akshare_frame(spec: dict[str, Any], cache: dict[str, Any] | None = None) -> Any:
    try:
        import akshare as ak  # type: ignore[import-not-found]
    except ImportError as exc:
        raise RuntimeError("AKShare is not installed in the project environment.") from exc

    function_name = spec["function"]
    args = spec.get("args") or []
    kwargs = spec.get("kwargs") or {}
    cache_key = json.dumps({"function": function_name, "args": args, "kwargs": kwargs}, ensure_ascii=False, sort_keys=True)
    if cache is not None and cache_key in cache:
        frame = cache[cache_key]
    else:
        fetcher = getattr(ak, function_name)
        timeout_seconds = int(spec.get("timeout_seconds", 45))
        attempts = int(spec.get("retries", 2))
        last_error: Exception | None = None
        for attempt in range(attempts):
            try:
                if timeout_seconds:
                    def _timeout_handler(signum: int, frame: Any) -> None:  # noqa: ARG001
                        raise TimeoutError(f"AKShare fetch timed out after {timeout_seconds}s for {function_name}")

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
            except Exception as exc:  # noqa: BLE001 - retry flaky upstream wrappers once before degrading.
                last_error = exc
                if attempt < attempts - 1:
                    time.sleep(2)
                else:
                    raise last_error
        if cache is not None:
            cache[cache_key] = frame
    return frame


def fetch_akshare_table(spec: dict[str, Any], cache: dict[str, Any] | None = None) -> dict[str, Any]:
    try:
        import pandas as pd
    except ImportError as exc:
        raise RuntimeError("pandas is not installed in the project environment.") from exc

    frame = _fetch_akshare_frame(spec, cache)
    filter_column = spec.get("filter_column")
    if filter_column and spec.get("filter_value") is not None:
        frame = frame[frame[filter_column].astype(str) == str(spec["filter_value"])]
    date_column = spec["date_column"]
    value_column = spec.get("value_column")
    value_columns = spec.get("value_columns") or []
    observations: list[dict[str, Any]] = []

    for _, row in frame.iterrows():
        raw_date = row.get(date_column)
        if pd.isna(raw_date):
            continue
        if value_columns:
            raw_values = [row.get(column) for column in value_columns]
            if any(pd.isna(raw_value) for raw_value in raw_values):
                continue
            try:
                values = [float(raw_value) for raw_value in raw_values]
            except (TypeError, ValueError):
                continue
            operation = spec.get("value_operation", "sum")
            if operation == "difference":
                raw_value = values[0] - values[1]
            elif operation == "ratio":
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
            value = _apply_transform(float(raw_value), spec.get("transform"))
        except (TypeError, ValueError):
            continue
        observations.append({"date": parsed_date, "value": value})

    observations.sort(key=lambda item: item["date"])
    return {
        **spec,
        "observations": observations,
        "provider_updated": observations[-1]["date"] if observations else "",
        "api_url": spec.get("source_url", ""),
    }


def fetch_akshare_wide_year_month(spec: dict[str, Any], cache: dict[str, Any] | None = None) -> dict[str, Any]:
    """Parse AKShare tables with month rows and year columns, e.g. CPCA."""
    try:
        import pandas as pd
    except ImportError as exc:
        raise RuntimeError("pandas is not installed in the project environment.") from exc

    frame = _fetch_akshare_frame(spec, cache)
    date_column = spec["date_column"]
    observations: list[dict[str, Any]] = []
    for _, row in frame.iterrows():
        month_text = _clean_text(str(row.get(date_column, "")))
        month_match = re.match(r"^(\d{1,2})月$", month_text)
        if not month_match:
            continue
        month = int(month_match.group(1))
        for column in frame.columns:
            year_match = re.match(r"^(\d{4})年$", str(column))
            if not year_match:
                continue
            raw_value = row.get(column)
            if pd.isna(raw_value):
                continue
            try:
                value = _apply_transform(float(raw_value), spec.get("transform"))
            except (TypeError, ValueError):
                continue
            observations.append({"date": f"{int(year_match.group(1)):04d}-{month:02d}-01", "value": value})

    observations.sort(key=lambda item: item["date"])
    return {
        **spec,
        "observations": observations,
        "provider_updated": observations[-1]["date"] if observations else "",
        "api_url": spec.get("source_url", ""),
    }


def fetch_eastmoney_industry_indicator(spec: dict[str, Any]) -> dict[str, Any]:
    """Fetch Eastmoney's reusable industry-index API by stable INDICATOR_ID."""
    indicator_id = spec["indicator_id"]
    value_column = spec.get("value_column", "INDICATOR_VALUE")
    url = "https://datacenter-web.eastmoney.com/api/data/v1/get"
    params = {
        "sortColumns": "REPORT_DATE",
        "sortTypes": "-1",
        "pageSize": str(spec.get("page_size", 1000)),
        "pageNumber": "1",
        "reportName": "RPT_INDUSTRY_INDEX",
        "columns": "REPORT_DATE,INDICATOR_ID,INDICATOR_NAME,INDICATOR_VALUE,CHANGE_RATE,CHANGERATE_3M,CHANGERATE_6M,CHANGERATE_1Y,CHANGERATE_2Y,CHANGERATE_3Y",
        "filter": f'(INDICATOR_ID="{indicator_id}")',
        "source": "WEB",
        "client": "WEB",
    }
    response = requests.get(url, params=params, headers={"User-Agent": "Mozilla/5.0"}, timeout=45)
    response.raise_for_status()
    payload = response.json()
    rows = ((payload.get("result") or {}).get("data") or [])
    observations: list[dict[str, Any]] = []
    seen: set[tuple[str, float]] = set()
    for row in rows:
        parsed_date = _parse_period_date(row.get("REPORT_DATE"))
        raw_value = row.get(value_column)
        if not parsed_date or raw_value is None:
            continue
        try:
            value = _apply_transform(float(raw_value), spec.get("transform"))
        except (TypeError, ValueError):
            continue
        key = (parsed_date, value)
        if key in seen:
            continue
        seen.add(key)
        observations.append({"date": parsed_date, "value": value})
    observations.sort(key=lambda item: item["date"])
    return {
        **spec,
        "observations": observations,
        "provider_updated": observations[-1]["date"] if observations else "",
        "api_url": response.url,
    }


def _safe_rows() -> list[list[str]]:
    end = date.today()
    start = end - timedelta(days=365)
    response = requests.post(
        "https://www.safe.gov.cn/AppStructured/hlw/RMBQuery.do",
        data={"startDate": start.isoformat(), "endDate": end.isoformat(), "queryYN": "true"},
        timeout=45,
    )
    response.raise_for_status()
    rows: list[list[str]] = []
    for tr in re.findall(r'<tr[^>]*class="first"[^>]*>(.*?)</tr>', response.text, flags=re.S):
        cells = [
            _clean_text(re.sub(r"<.*?>", "", cell))
            for cell in re.findall(r"<td[^>]*>(.*?)</td>", tr, flags=re.S)
        ]
        cells = [cell for cell in cells if cell]
        if len(cells) >= 3 and re.match(r"\d{4}-\d{2}-\d{2}", cells[0]):
            rows.append(cells)
    rows.sort(key=lambda item: item[0])
    return rows


def fetch_safe_midpoint(spec: dict[str, Any], rows: list[list[str]]) -> dict[str, Any]:
    column = 1 if spec["id"] == "usd_cny_midpoint" else 2
    observations: list[dict[str, Any]] = []
    for row in rows:
        try:
            value = float(row[column]) / 100.0
        except (IndexError, TypeError, ValueError):
            continue
        observations.append({"date": row[0], "value": value})
    return {
        **spec,
        "observations": observations,
        "provider_updated": observations[-1]["date"] if observations else "",
        "api_url": spec["source_url"],
    }


def fetch_pbc_card(card: dict[str, Any]) -> dict[str, Any]:
    response = requests.get(card["url"], timeout=30)
    response.raise_for_status()
    text = re.sub(r"<[^>]+>", "\n", response.text)
    lines = [_clean_text(line) for line in text.splitlines()]
    lines = [line for line in lines if line]
    title = card["expected_title"]
    title_idx = next((i for i, line in enumerate(lines) if line == title), -1)
    value = "n/a"
    if title_idx >= 0:
        for line in lines[title_idx + 1 : title_idx + 14]:
            if re.match(r"^-?\d+(?:\.\d+)?(?:%|TN|BN|MN)?$", line, flags=re.I):
                value = line
                break
    update_idx = next((i for i, line in enumerate(lines) if line == "Latest Update"), -1)
    updated = ""
    if update_idx >= 0:
        for line in lines[update_idx + 1 : update_idx + 5]:
            if re.match(r"\d{2}/\d{2}/\d{4}", line):
                updated = line
                break
    return {**card, "value": value, "updated": updated or "n/a"}


def validate_series(series: dict[str, Any]) -> dict[str, Any]:
    observations = series.get("observations") or []
    notes: list[str] = []
    if not observations:
        return {**series, "quality_status": "unavailable", "quality_notes": ["No observations returned."]}
    if len(observations) < 10:
        notes.append("Short history.")

    frequency = str(series.get("frequency", "")).lower()
    latest_date = str(observations[-1]["date"])
    if frequency == "annual":
        latest_year = _parse_year(latest_date)
        if latest_year and latest_year < date.today().year - 2:
            notes.append(f"Lagged annual series; latest observation is {latest_year}.")
    elif frequency in {"monthly", "quarterly"}:
        try:
            latest_dt = datetime.strptime(latest_date, "%Y-%m-%d").date()
            stale_days = 120 if frequency == "monthly" else 285
            if (date.today() - latest_dt).days > stale_days:
                notes.append(f"{frequency.title()} series looks stale; latest observation is {latest_date}.")
        except ValueError:
            notes.append(f"{frequency.title()} date could not be parsed.")
    elif frequency == "daily":
        try:
            latest_dt = datetime.strptime(latest_date, "%Y-%m-%d").date()
            if (date.today() - latest_dt).days > 14:
                notes.append(f"Daily series looks stale; latest observation is {latest_date}.")
        except ValueError:
            notes.append("Daily date could not be parsed.")

    source_name = str(series.get("source_name", ""))
    if "World Bank" in source_name:
        notes.append("Annual WDI data is lagged and revision-prone.")
    if "IMF WEO" in source_name:
        notes.append("IMF WEO includes estimates/projections; dashed segment marks forecast years.")
    if "FRED" in source_name:
        notes.append("FRED is used as a reproducible public mirror; verify native-source definitions before trading use.")
    if "AKShare" in source_name:
        notes.append("AKShare wraps upstream web data; monitor schema drift and upstream availability.")
    if series.get("caveat_en"):
        notes.append(series["caveat_en"])

    if not notes:
        status = "verified"
    elif len(notes) <= 2:
        status = "watch"
    else:
        status = "low_confidence"
    return {**series, "quality_status": status, "quality_notes": notes[:3]}


def fetch_all(config: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    safe_rows: list[list[str]] | None = None
    akshare_cache: dict[str, Any] = {}
    series_list: list[dict[str, Any]] = []
    for spec in config.get("indicators", []):
        fetcher = spec.get("fetcher")

        def operation() -> dict[str, Any]:
            nonlocal safe_rows
            if fetcher == "world_bank":
                return fetch_world_bank(spec)
            if fetcher == "imf_datamapper":
                return fetch_imf_datamapper(spec)
            if fetcher == "fred_graph_csv":
                return fetch_fred_graph(spec)
            if fetcher == "akshare_table":
                return fetch_akshare_table(spec, akshare_cache)
            if fetcher == "akshare_wide_year_month":
                return fetch_akshare_wide_year_month(spec, akshare_cache)
            if fetcher == "eastmoney_industry_indicator":
                return fetch_eastmoney_industry_indicator(spec)
            if fetcher == "safe_rmb_midpoint":
                if safe_rows is None:
                    safe_rows = _safe_rows()
                return fetch_safe_midpoint(spec, safe_rows)
            raise ValueError(f"Unknown fetcher: {fetcher}")

        try:
            series = guarded_source_call(
                country="CN",
                indicator_id=str(spec.get("id") or "unknown"),
                source_id=str(fetcher or "unknown"),
                operation=operation,
            )
        except Exception as exc:  # noqa: BLE001 - structured degradation is intentional.
            series = failure_series(spec, exc)
        series_list.append(validate_series(series))

    cards: list[dict[str, Any]] = []
    for card in config.get("latest_cards", []):
        try:
            cards.append(guarded_source_call(
                country="CN",
                indicator_id=str(card.get("id") or card.get("label_en") or "pbc_card"),
                source_id="pbc_card",
                operation=lambda card=card: fetch_pbc_card(card),
                record_empty=False,
            ))
        except Exception as exc:  # noqa: BLE001
            cards.append({**card, "value": "n/a", "updated": "n/a", "error": str(exc)})
    return series_list, cards


def _latest(series: dict[str, Any]) -> dict[str, Any] | None:
    observations = series.get("observations") or []
    if not observations:
        return None

    actual_through = series.get("actual_through")
    if actual_through not in (None, ""):
        try:
            cutoff_year = int(actual_through)
        except (TypeError, ValueError):
            cutoff_year = None
        if cutoff_year is not None:
            actual = [
                item for item in observations
                if (_parse_year(str(item.get("date", ""))) or 9999) <= cutoff_year
            ]
            if actual:
                return actual[-1]

    observed = [
        item for item in observations
        if not bool(item.get("is_projection"))
        and str(item.get("observation_type") or "").lower() not in {"forecast", "projection"}
    ]
    return observed[-1] if observed else observations[-1]


def _format_period(date_text: str, frequency: str, locale: str) -> str:
    text = str(date_text or "")
    try:
        parsed = datetime.strptime(text[:10], "%Y-%m-%d")
    except ValueError:
        year = _parse_year(text)
        return f"{year}年" if year and locale == "zh" else str(year or text)

    frequency = str(frequency or "").lower()
    if frequency == "annual":
        return f"{parsed.year}年" if locale == "zh" else str(parsed.year)
    if frequency == "quarterly":
        quarter = ((parsed.month - 1) // 3) + 1
        return f"{parsed.year}年 Q{quarter}" if locale == "zh" else f"Q{quarter} {parsed.year}"
    if frequency == "monthly":
        return f"{parsed.year}年{parsed.month}月" if locale == "zh" else parsed.strftime("%b %Y")
    if locale == "zh":
        return f"{parsed.year}年{parsed.month}月{parsed.day}日"
    return f"{parsed.day} {parsed.strftime('%b %Y')}"


def _format_value(value: float, unit: str) -> str:
    if unit == "USD":
        return f"${value:,.2f}tn"
    if unit == "people":
        return f"{value:,.2f}bn"
    if abs(value) >= 100:
        return f"{value:,.0f}"
    if abs(value) >= 10:
        return f"{value:,.1f}"
    return f"{value:,.2f}"


def _chart_html(series: dict[str, Any], country_code: str) -> str:
    observations = series.get("observations") or []
    if not observations:
        return ""
    chart_id = f"chart-{series['id']}"
    actual_through = series.get("actual_through")
    traces: list[dict[str, Any]] = []
    if actual_through:
        actual = [item for item in observations if (_parse_year(item["date"]) or 9999) <= int(actual_through)]
        forecast = [item for item in observations if (_parse_year(item["date"]) or 0) >= int(actual_through)]
        if actual:
            traces.append({
                "name": "Actual / history",
                "x": [item["date"] for item in actual],
                "y": [item["value"] for item in actual],
                "mode": "lines",
                "line": {"color": ACCENT, "width": 2.4},
                "type": "scatter",
            })
        if forecast:
            traces.append({
                "name": "IMF WEO estimate / forecast",
                "x": [item["date"] for item in forecast],
                "y": [item["value"] for item in forecast],
                "mode": "lines",
                "line": {"color": "#364b61", "width": 2.2, "dash": "dash"},
                "type": "scatter",
            })
    else:
        traces.append({
            "name": series["label_en"],
            "x": [item["date"] for item in observations],
            "y": [item["value"] for item in observations],
            "mode": "lines",
            "line": {"color": ACCENT, "width": 2.4},
            "type": "scatter",
        })

    latest = _latest(series)
    if latest:
        traces.append({
            "name": "Latest observation",
            "meta": "cp-latest-marker",
            "x": [latest["date"]],
            "y": [latest["value"]],
            "mode": "markers",
            "marker": {
                "size": 9,
                "color": ACCENT,
                "line": {"width": 2, "color": "#fffdf8"},
            },
            "showlegend": False,
            "hovertemplate": "Latest: %{y}<extra></extra>",
            "cliponaxis": False,
            "type": "scatter",
        })

    layout = {
        "height": 360,
        "margin": {"l": 52, "r": 26, "t": 20, "b": 46},
        "paper_bgcolor": PAPER,
        "plot_bgcolor": PAPER,
        "font": {
            "family": "Avenir Next, PingFang SC, Hiragino Sans GB, Noto Sans SC, Segoe UI, sans-serif",
            "size": 12,
            "color": INK,
        },
        "xaxis": {"gridcolor": "rgba(23,19,16,0.08)", "autorange": True, "automargin": True},
        "yaxis": {
            "title": series.get("unit", ""),
            "gridcolor": "rgba(23,19,16,0.08)",
            "autorange": True,
            "automargin": True,
        },
        "legend": {"orientation": "h", "y": -0.24},
        "hovermode": "x unified",
        "autosize": True,
    }
    latest_reading = ""
    if latest:
        value = _format_value(float(latest["value"]), series.get("unit", ""))
        unit = escape(series.get("unit", ""))
        date_text = escape(str(latest["date"]))
        period_en = escape(_format_period(str(latest["date"]), series.get("frequency", ""), "en"))
        period_zh = escape(_format_period(str(latest["date"]), series.get("frequency", ""), "zh"))
        latest_reading = f"""
      <div class="latest-reading" data-latest-reading data-latest-date="{date_text}">
        <span class="latest-label"><span data-lang="en">Latest observation</span><span data-lang="zh">最新读数</span></span>
        <span class="latest-value"><strong>{value}</strong><em>{unit}</em></span>
        <time datetime="{date_text}"><span data-lang="en">{period_en}</span><span data-lang="zh">{period_zh}</span></time>
      </div>"""
    quality_data = series.get("data_quality") or {}
    authority = escape(str(quality_data.get("source_authority", "")).replace("_", " "))
    freshness = escape(str(quality_data.get("freshness", "")).replace("_", " "))
    quality = escape(series.get("quality_status", "unchecked").replace("_", " "))
    chips = (
        f'<span class="quality-pill">{quality}</span>'
        f'<span class="authority-chip">{authority}</span>'
        f'<span class="freshness-chip">{freshness}</span>'
    )
    caveat_en = escape(series.get("caveat_en", ""))
    caveat_zh = escape(series.get("caveat_zh", ""))
    source_url = escape(series.get("source_url") or series.get("api_url") or "#")
    concept_id = concept_id_for(country_code, str(series["id"]))
    view = "deep" if ":" in concept_id else "core"
    cross = series.get("cross_check") or {}
    cross_html = ""
    if cross:
        status = cross["status"]
        window_months = cross.get("window_months")
        window_label = f"last {window_months} months" if window_months else "recent window"
        if status == "insufficient":
            # No overlapping observations in the recent window (and possibly none
            # at all) — nothing to agree or diverge on, so say so plainly rather
            # than formatting fields (e.g. `latest_diff`) that may be None here.
            mark = "— No recent overlap for"
            headline = f"{window_label}: no common periods to compare"
            cls = "cross-check"
        elif status in {"agree", "minor"}:
            mark = "✓ Agrees with"
            headline = (
                f"{window_label}: {cross['window_n_common']} common periods, "
                f"max gap {cross['window_max_abs_diff']:.2f} (tolerance {cross['tolerance']:.2f})"
            )
            cls = "cross-check"
        else:
            mark = "⚠ Diverges from"
            headline = (
                f"{window_label}: {cross['window_n_breaches']} of {cross['window_n_common']} periods "
                f"beyond tolerance {cross['tolerance']:.2f}, latest gap {cross['latest_diff']:.2f} "
                f"({cross['last_breach_date']})"
            )
            cls = "cross-check diverged"
        if cross["n_breaches"]:
            history = (
                f"Full history: {cross['n_breaches']} of {cross['n_common']} periods beyond tolerance "
                f"(most recently {cross['last_breach_date']}; max gap {cross['max_abs_diff']:.2f})."
            )
        else:
            history = f"Full history: no breaches across {cross['n_common']} common periods."
        cross_html = (
            f'\n  <p class="{cls}">{mark} <strong>{escape(cross["label_en"])}</strong> · {escape(headline)}'
            f'<br><span class="cross-check-history">{escape(history)}</span></p>'
        )
    return f"""
<article class="chart-card chart-quality-{escape(series.get('quality_status', 'unchecked'))}" data-dashboard-view="{view}" data-concept-id="{escape(concept_id)}">
  <div class="chart-head">
    <div class="chart-title">
      <h3><span data-lang="en">{escape(series['label_en'])}</span><span data-lang="zh">{escape(series['label_zh'])}</span></h3>
    </div>
    <div class="chart-status">
      {latest_reading}
      {chips}
    </div>
  </div>
  <div id="{chart_id}" class="plotly-chart"></div>
  <script>
    Plotly.newPlot("{chart_id}", {_json(traces)}, {_json(layout)}, {{displayModeBar:"hover", displaylogo:false, responsive:true}});
  </script>
  <footer>
    <span>Source: <a href="{source_url}" target="_blank" rel="noreferrer">{escape(series.get('source_name', 'unknown'))}</a></span>
    <span>Series: {escape(series.get('series', ''))}</span>
    <span>Frequency: {escape(series.get('frequency', ''))}</span>
    <span>Provider update: {escape(series.get('provider_updated', '') or 'n/a')}</span>
  </footer>{cross_html}
  <p class="caveat"><span data-lang="en">{caveat_en}</span><span data-lang="zh">{caveat_zh}</span></p>
</article>
"""


def _render_cards(series_list: list[dict[str, Any]], pbc_cards: list[dict[str, Any]]) -> str:
    headline_ids = ["real_gdp_growth", "cpi_inflation", "usd_cny_midpoint", "general_gov_debt"]
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
    for card in pbc_cards:
        cards.append(f"""
<div class="data-card">
  <span><span data-lang="en">{escape(card['label_en'])}</span><span data-lang="zh">{escape(card['label_zh'])}</span></span>
  <strong>{escape(str(card.get('value', 'n/a')))}</strong>
  <small>{escape(str(card.get('updated', 'n/a')))} · PBC</small>
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


def _section_nav(config: dict[str, Any]) -> str:
    links = []
    for section_id, section in config.get("sections", {}).items():
        links.append(
            f'<a href="#{escape(section_id)}"><span data-lang="en">{escape(section["title_en"])}</span>'
            f'<span data-lang="zh">{escape(section["title_zh"])}</span></a>'
        )
    links.append('<a href="#data-gaps"><span data-lang="en">Data Gaps</span><span data-lang="zh">数据缺口</span></a>')
    return "\n".join(links)


def _sections_html(config: dict[str, Any], series_list: list[dict[str, Any]], country_code: str) -> str:
    by_section: dict[str, list[dict[str, Any]]] = {}
    for item in series_list:
        if item.get("observations"):
            by_section.setdefault(item["section"], []).append(item)
    html_parts: list[str] = []
    for section_id, section in config.get("sections", {}).items():
        charts = "\n".join(_chart_html(item, country_code) for item in by_section.get(section_id, []))
        empty = ""
        if not charts:
            empty = '<div class="empty-note"><span data-lang="en">No reproducible public chart wired yet for this section.</span><span data-lang="zh">本节暂未接入可复跑的公开图表数据。</span></div>'
        html_parts.append(f"""
<section class="panel" id="{escape(section_id)}">
  <div class="section-title">
    <p>PDF logic</p>
    <h2><span data-lang="en">{escape(section['title_en'])}</span><span data-lang="zh">{escape(section['title_zh'])}</span></h2>
    <div class="logic"><span data-lang="en">{escape(section['report_logic_en'])}</span><span data-lang="zh">{escape(section['report_logic_zh'])}</span></div>
  </div>
  <div class="charts-grid">
    {charts}
    {empty}
  </div>
</section>""")
    return "\n".join(html_parts)


def _gaps_html(config: dict[str, Any]) -> str:
    sections = config.get("sections", {})
    rows = []
    for gap in config.get("data_gaps", []):
        section = sections.get(gap["section"], {})
        rows.append(f"""
<tr>
  <td><span data-lang="en">{escape(section.get('title_en', gap['section']))}</span><span data-lang="zh">{escape(section.get('title_zh', gap['section']))}</span></td>
  <td><span data-lang="en">{escape(gap['item_en'])}</span><span data-lang="zh">{escape(gap['item_zh'])}</span></td>
  <td><span data-lang="en">{escape(gap['status_en'])}</span><span data-lang="zh">{escape(gap['status_zh'])}</span></td>
</tr>""")
    return "\n".join(rows)


CSS = """
:root {
  --bg: #f4efe7;
  --fg: #171310;
  --muted: #63574e;
  --accent: #8a593d;
  --accent-soft: rgba(138, 89, 61, 0.12);
  --border: rgba(23, 19, 16, 0.14);
  --card: rgba(255, 252, 246, 0.76);
  --blue: #364b61;
  --warn: #9d6a2e;
  --low: #9d3d2e;
  --font-display: "Iowan Old Style", "Songti SC", "Noto Serif SC", Georgia, serif;
  --font-body: "Avenir Next", "PingFang SC", "Hiragino Sans GB", "Noto Sans SC", "Segoe UI", sans-serif;
}
* { box-sizing: border-box; }
html { scroll-behavior: smooth; }
html[lang="en"] [data-lang="zh"] { display: none !important; }
html[lang="zh"] [data-lang="en"] { display: none !important; }
html:not([lang="zh"]) [data-lang="zh"] { display: none !important; }
body {
  margin: 0;
  background:
    radial-gradient(circle at top left, rgba(138, 89, 61, 0.15), transparent 24%),
    radial-gradient(circle at top right, rgba(54, 75, 97, 0.12), transparent 22%),
    linear-gradient(180deg, #f8f4ed 0%, #f4efe7 48%, #efe7db 100%);
  color: var(--fg);
  font-family: var(--font-body);
  line-height: 1.6;
}
body::before {
  content: "";
  position: fixed;
  inset: 0;
  pointer-events: none;
  background:
    linear-gradient(to right, rgba(23, 19, 16, 0.025) 1px, transparent 1px),
    linear-gradient(to bottom, rgba(23, 19, 16, 0.02) 1px, transparent 1px);
  background-size: 48px 48px;
  mask-image: linear-gradient(180deg, rgba(0, 0, 0, 0.45), transparent 85%);
}
a { color: inherit; }
.topbar {
  position: sticky;
  top: 0;
  z-index: 20;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 12px 32px;
  background: rgba(244, 239, 231, 0.86);
  border-bottom: 1px solid var(--border);
  backdrop-filter: blur(14px);
  font-size: 11px;
  letter-spacing: 0.12em;
  text-transform: uppercase;
}
.brand { font-family: var(--font-display); font-size: 15px; letter-spacing: 0.16em; white-space: nowrap; }
.brand span { color: var(--accent); }
.country-nav { display: flex; gap: 5px; flex-wrap: wrap; align-items: center; }
.country-nav a {
  text-decoration: none;
  color: var(--muted);
  border: 1px solid var(--border);
  border-radius: 999px;
  padding: 5px 12px;
}
.country-nav a.active { background: var(--fg); color: var(--bg); border-color: var(--fg); }
.lang-toggle {
  border: 1px solid var(--border);
  background: rgba(255,252,246,0.7);
  color: var(--fg);
  border-radius: 999px;
  padding: 6px 12px;
  cursor: pointer;
  font: inherit;
}
.container { position: relative; max-width: 1320px; margin: 0 auto; padding: 38px 24px 56px; }
header { border-bottom: 1px solid var(--border); padding: 36px 0 30px; margin-bottom: 24px; }
h1 {
  margin: 0;
  max-width: 980px;
  font-family: var(--font-display);
  font-size: clamp(36px, 6vw, 76px);
  font-weight: 500;
  letter-spacing: -0.06em;
  line-height: 0.92;
}
.subtitle { max-width: 880px; color: var(--muted); font-size: 16px; margin-top: 16px; }
.meta-row { display: flex; gap: 10px; flex-wrap: wrap; margin-top: 18px; }
.meta-chip {
  border: 1px solid var(--border);
  background: rgba(255,252,246,0.48);
  border-radius: 999px;
  padding: 5px 13px;
  color: var(--muted);
  font-size: 12px;
}
.toc {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  margin: 20px 0 28px;
}
.toc a {
  text-decoration: none;
  border: 1px solid var(--border);
  border-radius: 999px;
  padding: 7px 12px;
  background: var(--card);
  color: var(--muted);
  font-size: 12px;
}
.view-switch {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  margin: -12px 0 26px;
}
.view-switch > span { color: var(--muted); font-size: 12px; margin-right: 3px; }
.view-switch button {
  border: 1px solid var(--border);
  border-radius: 999px;
  padding: 7px 13px;
  background: var(--card);
  color: var(--muted);
  cursor: pointer;
  font: inherit;
  font-size: 12px;
}
.view-switch button[aria-pressed="true"] { background: var(--fg); color: var(--bg); border-color: var(--fg); }
body[data-dashboard-view="core"] .chart-card[data-dashboard-view="deep"] { display: none; }
.data-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(170px, 1fr));
  gap: 10px;
  margin-bottom: 24px;
}
.data-card, .chart-card, .panel, .data-note, .gaps-table {
  background: var(--card);
  border: 1px solid var(--border);
}
.data-card { padding: 16px; min-height: 118px; }
.data-card span {
  display: block;
  color: var(--muted);
  font-size: 11px;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}
.data-card strong {
  display: block;
  font-family: var(--font-display);
  font-size: 30px;
  font-weight: 500;
  line-height: 1.05;
  margin: 12px 0 8px;
}
.data-card small { color: var(--muted); }
.panel { padding: 26px; margin-bottom: 26px; }
.section-title { display: grid; grid-template-columns: 180px 1fr; gap: 18px; align-items: baseline; border-bottom: 1px solid var(--border); padding-bottom: 16px; margin-bottom: 18px; }
.section-title p {
  margin: 0;
  color: var(--accent);
  font-size: 11px;
  letter-spacing: 0.12em;
  text-transform: uppercase;
}
.section-title h2 {
  margin: 0;
  font-family: var(--font-display);
  font-size: clamp(26px, 3.2vw, 44px);
  font-weight: 500;
  letter-spacing: -0.04em;
}
.logic { grid-column: 2; color: var(--muted); max-width: 860px; }
.charts-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(min(520px, 100%), 1fr)); gap: 16px; margin-bottom: 20px; }
.chart-card { padding: 16px; min-width: 0; overflow: hidden; transition: transform 0.16s ease, border-color 0.16s ease; }
.chart-card:hover { transform: translateY(-2px); border-color: rgba(23,19,16,0.26); }
.chart-head { display: flex; justify-content: space-between; gap: 18px; align-items: stretch; border-bottom: 1px solid var(--border); padding-bottom: 12px; margin-bottom: 8px; }
.chart-title { min-width: 0; flex: 1 1 auto; padding-top: 2px; }
.chart-head h3 { margin: 0; font-family: var(--font-display); font-size: 22px; font-weight: 500; letter-spacing: -0.02em; }
.chart-status { display: flex; align-items: flex-start; gap: 10px; flex: 0 0 auto; }
.latest-reading {
  display: grid;
  grid-template-columns: auto auto;
  column-gap: 9px;
  align-items: baseline;
  min-width: 160px;
  padding-left: 14px;
  border-left: 1px solid var(--border);
  font-variant-numeric: tabular-nums;
}
.latest-label {
  grid-column: 1 / -1;
  color: var(--accent);
  font-size: 9px;
  font-weight: 700;
  letter-spacing: 0.1em;
  line-height: 1.2;
  text-transform: uppercase;
}
.latest-value { display: inline-flex; align-items: baseline; gap: 5px; min-width: 0; }
.latest-value strong {
  font-family: var(--font-display);
  font-size: 24px;
  font-weight: 600;
  line-height: 1;
  letter-spacing: -0.035em;
  color: var(--fg);
  white-space: nowrap;
}
.latest-value em { color: var(--muted); font-size: 9px; font-style: normal; white-space: nowrap; }
.latest-reading time { color: var(--muted); font-size: 10px; white-space: nowrap; }
.quality-pill {
  border: 1px solid var(--border);
  border-radius: 999px;
  padding: 4px 9px;
  color: var(--muted);
  font-size: 11px;
  white-space: nowrap;
}
.chart-quality-verified .quality-pill { color: #3f6f50; border-color: rgba(63,111,80,0.35); }
.chart-quality-watch .quality-pill { color: var(--warn); border-color: rgba(157,106,46,0.35); }
.chart-quality-low_confidence .quality-pill { color: var(--low); border-color: rgba(157,61,46,0.35); }
.authority-chip, .freshness-chip {
  font-size: 11px; letter-spacing: .02em; padding: 2px 7px; border-radius: 999px;
  border: 1px solid rgba(23,19,16,0.16); color: var(--muted, #63574e); margin-left: 6px;
}
.authority-chip { background: rgba(63,111,80,0.10); }
.freshness-chip { background: rgba(54,75,97,0.10); }
.cross-check { font-size: 12px; color: #63574e; margin-top: 4px; }
.cross-check.diverged { color: #9d3d2e; }
.cross-check-history { color: var(--muted); }
.plotly-chart { width: 100%; min-width: 0; height: 360px; }
.plot-container, .svg-container { max-width: 100% !important; }
#js-plotly-tester { width: 1px !important; max-width: 1px !important; overflow: hidden !important; }
.chart-card footer {
  display: grid;
  gap: 3px;
  color: var(--muted);
  font-size: 11px;
  border-top: 1px solid var(--border);
  padding-top: 10px;
}
.chart-card footer a { color: var(--accent); }
.caveat { color: var(--muted); font-size: 12px; margin: 10px 0 0; }
.empty-note { padding: 20px; color: var(--muted); border: 1px dashed var(--border); }
.data-note { padding: 18px; margin-bottom: 26px; color: var(--muted); }
.gaps-table { width: 100%; border-collapse: collapse; font-size: 13px; }
.gaps-table th, .gaps-table td { padding: 12px; border-bottom: 1px solid var(--border); vertical-align: top; text-align: left; }
.gaps-table th { color: var(--muted); font-size: 11px; letter-spacing: 0.08em; text-transform: uppercase; }
footer.page-footer { color: var(--muted); border-top: 1px solid var(--border); padding-top: 20px; font-size: 12px; }
@media (max-width: 760px) {
  .topbar { align-items: flex-start; flex-direction: column; padding: 12px 18px; }
  .container { padding: 28px 16px 42px; }
  .section-title { grid-template-columns: 1fr; }
  .logic { grid-column: 1; }
  .charts-grid { grid-template-columns: 1fr; }
  .panel { overflow-x: auto; }
  .chart-card { padding: 13px; }
  .chart-head { flex-direction: column; gap: 8px; }
  .chart-head h3 { font-size: 19px; }
  .chart-status { width: 100%; justify-content: space-between; align-items: center; }
  .latest-reading { flex: 1 1 auto; min-width: 0; border-left: 0; border-top: 1px solid var(--border); padding: 8px 0 0; }
  .latest-value strong { font-size: 22px; }
  .plotly-chart { height: 320px; }
}
"""


def render_html(config: dict[str, Any], series_list: list[dict[str, Any]], cards: list[dict[str, Any]]) -> str:
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
<title>China Dashboard</title>
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
    <a href="china.html" class="active">CN</a>
    <a href="japan.html">JP</a>
    <a href="south_africa.html">ZA</a>
    <a href="uk.html">UK</a>
    <a href="us.html">US</a>
  </nav>
  <button class="lang-toggle" onclick="toggleLang()" id="lang-btn">中文</button>
</div>

<main class="container">
  <header>
    <h1><span data-lang="en">China Dashboard</span><span data-lang="zh">中国 Dashboard</span></h1>
    <p class="subtitle"><span data-lang="en">A chart-and-data-only China macro page aligned to the report logic in <em>Understanding China's Economic Statistics</em>. It uses reproducible public sources only; missing China-native monthly indicators are called out rather than proxied.</span><span data-lang="zh">一个仅聚焦图表和数据的中国宏观页面，结构对齐 <em>Understanding China's Economic Statistics</em> 的报告逻辑。页面仅使用可复跑公开来源；尚未稳定接入的中国本土月度指标会明确列为缺口，不用 proxy 替代。</span></p>
    <div class="meta-row">
      <span class="meta-chip">{chart_count} <span data-lang="en">charts</span><span data-lang="zh">张图</span></span>
      <span class="meta-chip">{source_count} <span data-lang="en">public source groups</span><span data-lang="zh">组公开来源</span></span>
      <span class="meta-chip">{gap_count} <span data-lang="en">official-data gaps tracked</span><span data-lang="zh">个官方数据缺口</span></span>
      <span class="meta-chip">{low_count} <span data-lang="en">low-confidence charts</span><span data-lang="zh">张低置信图</span></span>
    </div>
  </header>

  <section class="data-grid" aria-label="latest data cards">
    {_render_cards(series_list, cards)}
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
    <span data-lang="en">Data policy: no fabricated proxies. World Bank and IMF annual series provide the durable public skeleton; SAFE provides official daily RMB fixing data; PBC cards show latest official monetary prints where history is not yet wired.</span>
    <span data-lang="zh">数据原则：不制造 proxy。World Bank 与 IMF 年度序列提供可维护的公开骨架；SAFE 提供官方人民币日度中间价；PBC 卡片展示暂未接入历史序列的最新官方货币数据。</span>
  </div>

  {_sections_html(config, series_list, "CN")}

  <section class="panel" id="data-gaps">
    <div class="section-title">
      <p>Pipeline</p>
      <h2><span data-lang="en">Official Data Gaps</span><span data-lang="zh">官方数据缺口</span></h2>
      <div class="logic"><span data-lang="en">These are PDF-native indicators that matter for China but are not yet rendered because a reproducible public adapter has not been validated.</span><span data-lang="zh">这些是报告逻辑中的中国本土核心指标，但由于尚未验证可复跑的公开 adapter，当前暂不渲染为图。</span></div>
    </div>
    <table class="gaps-table">
      <thead><tr><th>Section</th><th>Indicator family</th><th>Status</th></tr></thead>
      <tbody>{_gaps_html(config)}</tbody>
    </table>
  </section>

  <footer class="page-footer">
    <span data-lang="en">Research artefact only, not investment advice. Generated {generated_date} from <code>config/china_indicators.yaml</code>.</span>
    <span data-lang="zh">仅为研究工具，不构成投资建议。生成日期 {generated_date}，配置来源 <code>config/china_indicators.yaml</code>。</span>
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
  <!-- China dashboard card -->
  <a href="china.html" class="card clean">
    <div class="card-kicker">CNY · PBC · China data-first page</div>
    <h2>China</h2>
    <div class="stats">
      <div class="stat"><span>Rendered charts</span><strong>{summary['charts']}</strong></div>
      <div class="stat"><span>Proxy fills</span><strong>0</strong></div>
      <div class="stat"><span>Official gaps tracked</span><strong>{summary['data_gaps']}</strong></div>
      <div class="stat"><span>Latest USD/CNY fixing</span><strong>{escape(summary.get('usd_cny_latest', 'n/a'))}</strong></div>
      <div class="stat"><span>Source groups</span><strong>{summary['source_groups']}</strong></div>
      <div class="stat"><span>Framework</span><strong>GS China statistics logic</strong></div>
    </div>
  </a>
  <!-- /China dashboard card -->"""


def inject_index(summary: dict[str, Any]) -> None:
    index_path = OUTPUT / "index.html"
    if not index_path.exists():
        return
    html = index_path.read_text()
    html = re.sub(r"\n\s*<!-- China dashboard card -->.*?<!-- /China dashboard card -->", "", html, flags=re.S)
    marker = '  </section>\n  <nav class="links"'
    if marker in html:
        html = html.replace(marker, _index_card(summary) + "\n  </section>\n  <nav class=\"links\"", 1)
    html = html.replace("<title>Country Primer — CEE-4 Macro Dashboard</title>", "<title>Country Primer — Macro Dashboard Archive</title>")
    html = html.replace("CEE-4 Macro Dashboard · v4 · Proxy-free public pages", "Macro Dashboard Archive · CEE-4 v4 + China")
    html = html.replace("<h1>CEE-4 Macro Dashboard</h1>", "<h1>Macro Dashboard Archive</h1>")
    html = html.replace(
        "Generated archive entry for the four country dashboards. This page is rebuilt by <code>build_v4.py ALL</code>, so its links, indicator counts, proxy status, and quality summary stay synchronized with the individual country pages.",
        "Generated archive entry for the proxy-free CEE-4 dashboards plus the China data-first page. This page is rebuilt by <code>make build-v4</code>, so links, indicator counts, proxy status, and quality summary stay synchronized with generated pages.",
    )
    html = html.replace("<span>rendered country-indicator slots</span>", "<span>CEE-4 rendered indicator slots</span>")
    html = html.replace("<strong>4</strong><span>country dashboards</span>", "<strong>5</strong><span>country dashboards</span>")
    _write_clean(index_path, html)


def build(data_mode: str | None = None) -> Path:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    data_mode = (data_mode or os.environ.get("COUNTRY_PRIMER_DATA_MODE") or "refresh").strip().lower()
    config = _load_config()
    if data_mode == "snapshot":
        series_list = load_canonical_data_first_frame(CANONICAL_JSON, config)
        previous_summary = json.loads(SUMMARY_JSON.read_text()) if SUMMARY_JSON.exists() else {}
        cards = list(previous_summary.get("latest_cards") or [
            {**card, "value": "n/a", "updated": "n/a"}
            for card in config.get("latest_cards", [])
        ])
    else:
        SOURCE_HEALTH.reset()
        series_list, cards = fetch_all(config)
        series_list = retain_last_known_good_series(series_list, CANONICAL_JSON, config)
    apply_quality_assessments(series_list)
    _write_clean(OUT_HTML, render_html(config, series_list, cards))

    charted = [item for item in series_list if item.get("observations")]
    usd_cny = next((item for item in charted if item["id"] == "usd_cny_midpoint"), None)
    usd_latest = _latest(usd_cny) if usd_cny else None
    summary = {
        "file": OUT_HTML.name,
        "generated": datetime.now(UTC).isoformat(),
        "charts": len(charted),
        "source_groups": len({item.get("source_name") for item in charted}),
        "data_gaps": len(config.get("data_gaps", [])),
        "low_confidence": sum(1 for item in charted if item.get("quality_status") == "low_confidence"),
        "usd_cny_latest": (
            f"{float(usd_latest['value']):.4f} ({usd_latest['date']})" if usd_latest else "n/a"
        ),
        "key_series_latest": _key_series_latest(charted, SUMMARY_KEY_IDS),
        "unavailable": [item["id"] for item in series_list if not item.get("observations")],
        "data_mode": data_mode,
        "latest_cards": cards,
    }
    summary["canonical_frame"] = (
        canonical_frame_metadata(CANONICAL_JSON)
        if data_mode == "snapshot"
        else write_canonical_data_first_frame(CANONICAL_JSON, "CN", series_list)
    )
    summary.update(build_summary_metadata(config, series_list, "CN"))
    SUMMARY_JSON.write_text(json.dumps(summary, indent=2, ensure_ascii=False))
    if data_mode != "snapshot":
        write_source_health_report(OUTPUT / "source_health.json", ["CN"])
    inject_index(summary)
    if not os.environ.get("COUNTRY_PRIMER_SKIP_ARCHIVE"):
        from build_dashboard_archive import build_archive
        build_archive()
    return OUT_HTML


if __name__ == "__main__":
    path = build()
    print(f"Wrote {path} ({path.stat().st_size:,} bytes)")
