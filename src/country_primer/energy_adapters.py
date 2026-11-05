"""Keyless energy-market sources for the market_energy scope.

* ``fetch_eia_xls``: EIA "dnav" history spreadsheets (spot prices, weekly
  petroleum status report, natural gas storage). No API key.
* ``fetch_cftc_positions``: CFTC Commitments of Traders (disaggregated futures
  only) via the public Socrata API, queried by contract market code because
  contract names have changed over time.
* ``fetch_energy_charts_price``: day-ahead power prices from Fraunhofer ISE's
  energy-charts API (Bundesnetzagentur / SMARD data, CC BY 4.0), averaged to
  daily values in the bidding zone's local time.
* ``fetch_foreign_futures``: same-day front-month futures closes from Sina
  Finance through AKShare (a public wrapper: quality is capped at "watch").

Keyed sources (the key is read from the environment or ``.env.local``; an
error message names the source and HTTP status only, never the request URL):

* ``fetch_gie_agsi``: GIE AGSI+ gas storage per gas day, EU aggregate or one
  member state (``GIE_AGSI_API_KEY``, sent as the ``x-key`` header).
* ``fetch_eia_steo``: EIA Short-Term Energy Outlook series through API v2
  (``EIA_API_KEY``), history months only: STEO forecasts never reach a page.
* ``fetch_ember_generation``: Ember monthly electricity generation by source
  (``EMBER_API_KEY``).
"""
from __future__ import annotations

import math
import time
from collections import defaultdict
from datetime import UTC, date, datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

import requests

USER_AGENT = "country-primer/0.1 (+https://github.com/DJiangwei/macro-dashboard)"

EIA_XLS_URL = "https://www.eia.gov/dnav/{area}/hist_xls/{code}{suffix}.xls"
EIA_FREQ_SUFFIX = {"daily": "d", "weekly": "w", "monthly": "m", "annual": "a"}

CFTC_DISAGG_URL = "https://publicreporting.cftc.gov/resource/72hh-3qpy.json"
CFTC_FIELDS = {
    "m_money_positions_long_all", "m_money_positions_short_all", "prod_merc_positions_long",
    "prod_merc_positions_short", "swap_positions_long_all", "swap__positions_short_all", "open_interest_all",
}

ENERGY_CHARTS_URL = "https://api.energy-charts.info/price"
ENERGY_CHARTS_TZ = {"DE-LU": "Europe/Berlin", "FR": "Europe/Paris", "IT-North": "Europe/Rome", "ES": "Europe/Madrid", "NL": "Europe/Amsterdam"}

GIE_AGSI_URL = "https://agsi.gie.eu/api"
EIA_STEO_URL = "https://api.eia.gov/v2/steo/data/"
EMBER_MONTHLY_URL = "https://api.ember-energy.org/v1/electricity-generation/monthly"
EMBER_MEASURES = {"share_of_generation_pct", "generation_twh"}


def parse_eia_xls(content: bytes, frequency: str) -> list[dict[str, Any]]:
    """Rows of sheet "Data 1": date in column 0, value in column 1, from row 3."""
    import xlrd

    workbook = xlrd.open_workbook(file_contents=content)
    sheet = workbook.sheet_by_index(1)
    observations: list[dict[str, Any]] = []
    for row in range(3, sheet.nrows):
        raw_date, raw_value = sheet.cell_value(row, 0), sheet.cell_value(row, 1)
        if not isinstance(raw_date, float) or raw_value in ("", None):
            continue
        day = xlrd.xldate_as_datetime(raw_date, workbook.datemode).date()
        if frequency == "monthly":
            day = day.replace(day=1)  # EIA stamps monthly values on the 15th
        try:
            observations.append({"date": day.isoformat(), "value": float(raw_value)})
        except (TypeError, ValueError):
            continue
    return observations


def fetch_eia_xls(spec: dict[str, Any]) -> dict[str, Any]:
    """``series`` is ``<area>/<code>`` (e.g. ``pet/RBRTE``); frequency picks the file."""
    area, code = str(spec["series"]).split("/", 1)
    frequency = str(spec.get("frequency") or "daily").lower()
    url = EIA_XLS_URL.format(area=area, code=code, suffix=EIA_FREQ_SUFFIX[frequency])
    response = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=(5, 60))
    response.raise_for_status()
    if not response.content.startswith(b"\xd0\xcf"):
        raise RuntimeError(f"EIA returned a non-spreadsheet response for {spec['series']}")
    observations = parse_eia_xls(response.content, frequency)
    start = str(spec.get("start_date") or "")
    if start:
        observations = [o for o in observations if o["date"] >= start[:10]]
    if not observations:
        raise RuntimeError(f"EIA returned no observations for {spec['series']}")
    return {**spec, "observations": observations, "provider_updated": observations[-1]["date"], "api_url": url}


def cftc_measure(row: dict[str, Any], measure: str) -> float | None:
    def num(key: str) -> float | None:
        try:
            return float(row[key])
        except (KeyError, TypeError, ValueError):
            return None

    long_, short = num("m_money_positions_long_all"), num("m_money_positions_short_all")
    if long_ is None or short is None:
        return None
    if measure == "mm_net":
        return long_ - short
    if measure == "mm_net_pct_oi":
        oi = num("open_interest_all")
        return (long_ - short) / oi * 100.0 if oi else None
    raise ValueError(f"Unknown CFTC measure {measure!r}")


def fetch_cftc_positions(spec: dict[str, Any]) -> dict[str, Any]:
    """Managed-money positioning for one contract market code (``series``)."""
    code = str(spec["series"]).strip()
    measure = str(spec.get("measure") or "mm_net")
    start = str(spec.get("start_date") or "2010-01-01")[:10]
    params = {
        "$where": f"cftc_contract_market_code='{code}' AND report_date_as_yyyy_mm_dd >= '{start}T00:00:00'",
        "$order": "report_date_as_yyyy_mm_dd ASC",
        "$limit": "10000",
        "$select": "report_date_as_yyyy_mm_dd,market_and_exchange_names," + ",".join(sorted(CFTC_FIELDS)),
    }
    response = requests.get(CFTC_DISAGG_URL, params=params, headers={"User-Agent": USER_AGENT}, timeout=(5, 60))
    response.raise_for_status()
    rows = response.json()
    by_date: dict[str, float] = {}
    for row in rows:
        value = cftc_measure(row, measure)
        if value is not None:
            by_date[str(row["report_date_as_yyyy_mm_dd"])[:10]] = value
    observations = [{"date": d, "value": v} for d, v in sorted(by_date.items())]
    if not observations:
        raise RuntimeError(f"CFTC returned no rows for contract {code}")
    return {
        **spec,
        "observations": observations,
        "provider_updated": observations[-1]["date"],
        "api_url": f"{CFTC_DISAGG_URL}?cftc_contract_market_code={code}",
        "contract_name": rows[-1].get("market_and_exchange_names", ""),
    }


def daily_means(unix_seconds: list[int], prices: list[float | None], tz_name: str) -> dict[str, float]:
    zone = ZoneInfo(tz_name)
    buckets: dict[str, list[float]] = defaultdict(list)
    for ts, price in zip(unix_seconds, prices):
        if price is None:
            continue
        buckets[datetime.fromtimestamp(ts, zone).date().isoformat()].append(float(price))
    return {day: sum(values) / len(values) for day, values in buckets.items()}


def _energy_charts_get(session: requests.Session, params: dict[str, str], attempts: int = 5) -> dict[str, Any]:
    """GET with pacing: the public API answers bursts with HTTP 429."""
    import time

    delay = 4.0
    for attempt in range(attempts):
        time.sleep(1.5 if attempt == 0 else delay)
        response = session.get(ENERGY_CHARTS_URL, params=params, headers={"User-Agent": USER_AGENT}, timeout=(5, 90))
        if response.status_code == 429 and attempt < attempts - 1:
            retry_after = response.headers.get("Retry-After", "")
            delay = float(retry_after) if retry_after.isdigit() else delay * 2
            continue
        response.raise_for_status()
        return response.json()
    raise RuntimeError("energy-charts kept rate-limiting the request")


def fetch_energy_charts_price(spec: dict[str, Any]) -> dict[str, Any]:
    """Daily mean day-ahead price for a bidding zone (``series``, e.g. ``DE-LU``)."""
    zone = str(spec["series"])
    tz_name = ENERGY_CHARTS_TZ.get(zone, "Europe/Berlin")
    start = date.fromisoformat(str(spec.get("start_date") or "2019-01-01")[:10])
    today = datetime.now(UTC).date()
    session = requests.Session()
    means: dict[str, float] = {}
    chunk_start = start
    while chunk_start <= today:
        chunk_end = min(date(chunk_start.year, 12, 31), today)
        payload = _energy_charts_get(
            session, {"bzn": zone, "start": chunk_start.isoformat(), "end": chunk_end.isoformat()}
        )
        means.update(daily_means(payload.get("unix_seconds") or [], payload.get("price") or [], tz_name))
        chunk_start = chunk_end + timedelta(days=1)
    # Today's delivery day is incomplete until it ends; keep completed days only.
    observations = [{"date": d, "value": round(v, 2)} for d, v in sorted(means.items()) if d < today.isoformat()]
    if not observations:
        raise RuntimeError(f"energy-charts returned no prices for {zone}")
    return {**spec, "observations": observations, "provider_updated": observations[-1]["date"], "api_url": f"{ENERGY_CHARTS_URL}?bzn={zone}"}


def fetch_foreign_futures(spec: dict[str, Any]) -> dict[str, Any]:
    """Front-month futures closes (Sina symbol in ``series``) for completed sessions."""
    import akshare as ak

    frame = ak.futures_foreign_hist(symbol=str(spec["series"]))
    today = datetime.now(UTC).date().isoformat()
    start = str(spec.get("start_date") or "")[:10]
    observations = []
    for row in frame.itertuples(index=False):
        day = str(row.date)[:10]
        if day >= today or (start and day < start):
            continue  # today's row is a session still in progress
        try:
            observations.append({"date": day, "value": float(row.close)})
        except (TypeError, ValueError):
            continue
    if not observations:
        raise RuntimeError(f"No completed futures sessions for {spec['series']}")
    return {**spec, "observations": observations, "provider_updated": observations[-1]["date"], "api_url": "https://finance.sina.com.cn/futuremarket/"}


def fetch_sge_spot(spec: dict[str, Any]) -> dict[str, Any]:
    """Shanghai Gold Exchange daily close (``series`` e.g. ``Au99.99``), CNY per gram.

    ``measure: benchmark_am`` / ``benchmark_pm`` returns the Shanghai Gold
    Benchmark Price fixing instead. Completed sessions only.
    """
    import akshare as ak

    series = str(spec["series"])
    measure = str(spec.get("measure") or "close")
    if measure.startswith("benchmark"):
        frame = ak.spot_golden_benchmark_sge() if series.lower().startswith("au") else ak.spot_silver_benchmark_sge()
        date_col, value_col = "交易时间", ("早盘价" if measure == "benchmark_am" else "晚盘价")
    else:
        frame = ak.spot_hist_sge(symbol=series)
        date_col, value_col = "date", "close"
    today = datetime.now(UTC).date().isoformat()
    start = str(spec.get("start_date") or "")[:10]
    observations = []
    for day, value in zip(frame[date_col], frame[value_col]):
        day = str(day)[:10]
        if day >= today or (start and day < start):
            continue
        try:
            value = float(value)
        except (TypeError, ValueError):
            continue
        if value > 0:
            observations.append({"date": day, "value": value})
    observations.sort(key=lambda o: o["date"])
    if not observations:
        raise RuntimeError(f"SGE returned no completed sessions for {series}")
    return {**spec, "observations": observations, "provider_updated": observations[-1]["date"], "api_url": "https://www.sge.com.cn/sjzx/mrhqsj"}


def fetch_cn_futures_main(spec: dict[str, Any]) -> dict[str, Any]:
    """Chinese exchange main-contract continuous close (Sina symbol, e.g. ``CU0``), completed sessions."""
    import akshare as ak

    frame = ak.futures_main_sina(symbol=str(spec["series"]))
    today = datetime.now(UTC).date().isoformat()
    start = str(spec.get("start_date") or "")[:10]
    observations = []
    for day, close in zip(frame["日期"], frame["收盘价"]):
        day = str(day)[:10]
        if day >= today or (start and day < start):
            continue
        try:
            observations.append({"date": day, "value": float(close)})
        except (TypeError, ValueError):
            continue
    if not observations:
        raise RuntimeError(f"No completed sessions for {spec['series']}")
    return {**spec, "observations": observations, "provider_updated": observations[-1]["date"], "api_url": "https://finance.sina.com.cn/futuremarket/"}


def fetch_cn_futures_inventory(spec: dict[str, Any]) -> dict[str, Any]:
    """Exchange warehouse stocks from Eastmoney via AKShare (``series`` is the AKShare symbol, e.g. 沪铜)."""
    import akshare as ak

    frame = ak.futures_inventory_em(symbol=str(spec["series"]))
    observations = []
    for day, stock in zip(frame["日期"], frame["库存"]):
        try:
            observations.append({"date": str(day)[:10], "value": float(stock)})
        except (TypeError, ValueError):
            continue
    observations.sort(key=lambda o: o["date"])
    if not observations:
        raise RuntimeError(f"No inventory rows for {spec['series']}")
    return {**spec, "observations": observations, "provider_updated": observations[-1]["date"], "api_url": "https://data.eastmoney.com/ifdata/kcsj.html"}


def _require_key(name: str) -> str:
    from .adapters import _get_env_key

    key = _get_env_key(name)
    if not key:
        raise RuntimeError(f"{name} is not configured")
    return key


def _get_json(session: Any, url: str, params: dict[str, Any], headers: dict[str, str] | None, source: str, attempts: int = 4) -> Any:
    """GET JSON, backing off on HTTP 429. Errors carry the status, not the URL (it can hold a key)."""
    delay = 10.0
    for attempt in range(attempts):
        response = session.get(url, params=params, headers={"User-Agent": USER_AGENT, **(headers or {})}, timeout=(5, 90))
        if response.status_code == 429 and attempt < attempts - 1:
            retry_after = response.headers.get("Retry-After", "")
            time.sleep(float(retry_after) if retry_after.isdigit() else delay)
            delay *= 2
            continue
        if response.status_code != 200:
            raise RuntimeError(f"{source} returned HTTP {response.status_code}")
        return response.json()
    raise RuntimeError(f"{source} kept rate-limiting the request")


def agsi_points(rows: list[dict[str, Any]], field: str = "full") -> list[tuple[str, float]]:
    """(gas day, value) pairs, oldest first; blank and non-numeric values are skipped."""
    points: dict[str, float] = {}
    for row in rows or []:
        day = str(row.get("gasDayStart") or "")[:10]
        raw = row.get(field)
        if not day or raw in (None, "", "-"):
            continue
        try:
            value = float(raw)
        except (TypeError, ValueError):
            continue
        if math.isfinite(value):
            points[day] = value
    return sorted(points.items())


def fetch_agsi_points(
    code: str, start: str, api_key: str, session: Any = None, today: date | None = None, field: str = "full"
) -> list[tuple[str, float]]:
    """Every gas day since ``start`` for ``eu`` (EU aggregate) or an ISO2 member state.

    Also used by the CEE pipeline (``data_fetcher.GIEAGSIFetcher``), so there is
    one AGSI+ client. Pages hold at most 300 gas days; ``last_page`` drives the loop.
    """
    session = session or requests.Session()
    today = today or datetime.now(UTC).date()
    scope = {"type": "eu"} if code.lower() == "eu" else {"country": code.upper()}
    rows: list[dict[str, Any]] = []
    page, last_page = 1, 1
    while page <= last_page:
        params = {**scope, "from": start[:10], "to": today.isoformat(), "size": 300, "page": page}
        payload = _get_json(session, GIE_AGSI_URL, params, {"x-key": api_key}, "GIE AGSI+")
        rows.extend(payload.get("data") or [])
        last_page = int(payload.get("last_page") or 1)
        page += 1
    return agsi_points(rows, field)


def fetch_gie_agsi(spec: dict[str, Any]) -> dict[str, Any]:
    """Gas storage per gas day; ``series`` is ``eu`` or an ISO2 code, ``measure`` an AGSI+ field (default ``full``)."""
    code = str(spec["series"])
    points = fetch_agsi_points(
        code, str(spec.get("start_date") or "2015-01-01"), _require_key("GIE_AGSI_API_KEY"), field=str(spec.get("measure") or "full")
    )
    if not points:
        raise RuntimeError(f"GIE AGSI+ returned no gas days for {code}")
    observations = [{"date": day, "value": value} for day, value in points]
    query = "type=eu" if code.lower() == "eu" else f"country={code.upper()}"
    return {**spec, "observations": observations, "provider_updated": observations[-1]["date"], "api_url": f"{GIE_AGSI_URL}?{query}"}


def steo_last_history_month(today: date) -> str:
    """Latest month shown from STEO.

    STEO is released in the first half of each month and forecasts from the
    release month onward, so two months back is history under any live vintage.
    """
    index = today.year * 12 + (today.month - 1) - 2
    return f"{index // 12:04d}-{index % 12 + 1:02d}"


def steo_observations(rows: list[dict[str, Any]], today: date | None = None) -> list[dict[str, Any]]:
    last = steo_last_history_month(today or datetime.now(UTC).date())
    values: dict[str, float] = {}
    for row in rows or []:
        period = str(row.get("period") or "")[:7]
        if len(period) != 7 or period > last:
            continue
        try:
            values[f"{period}-01"] = float(row.get("value"))
        except (TypeError, ValueError):
            continue
    return [{"date": day, "value": value} for day, value in sorted(values.items())]


def fetch_eia_steo(spec: dict[str, Any]) -> dict[str, Any]:
    """One monthly STEO series (``series`` is the STEO seriesId, e.g. ``COPS_OPEC``).

    ``steo_unit`` in the spec, when given, must match the unit EIA reports, so a
    unit change at the source empties the chart instead of mislabelling it.
    """
    series = str(spec["series"])
    params = {
        "api_key": _require_key("EIA_API_KEY"),
        "frequency": "monthly",
        "data[0]": "value",
        "facets[seriesId][]": series,
        "start": str(spec.get("start_date") or "2010-01")[:7],
        "sort[0][column]": "period",
        "sort[0][direction]": "asc",
        "length": 5000,
    }
    payload = _get_json(requests.Session(), EIA_STEO_URL, params, None, "EIA STEO")
    rows = (payload.get("response") or {}).get("data") or []
    expected_unit = spec.get("steo_unit")
    reported_units = {str(row.get("unit")) for row in rows}
    if expected_unit and reported_units != {expected_unit}:
        raise RuntimeError(f"EIA STEO {series} reports units {sorted(reported_units)}, expected {expected_unit!r}")
    observations = steo_observations(rows)
    if not observations:
        raise RuntimeError(f"EIA STEO returned no history months for {series}")
    return {
        **spec,
        "observations": observations,
        "provider_updated": observations[-1]["date"],
        "api_url": f"{EIA_STEO_URL}?facets[seriesId][]={series}",
    }


def ember_observations(rows: list[dict[str, Any]], series: str, measure: str) -> list[dict[str, Any]]:
    """One Ember generation series (e.g. ``Gas``, ``Wind and solar``) as monthly observations."""
    if measure not in EMBER_MEASURES:
        raise ValueError(f"Unknown Ember measure {measure!r}")
    values: dict[str, float] = {}
    for row in rows or []:
        if row.get("series") != series or row.get(measure) is None:
            continue
        try:
            values[str(row["date"])[:10]] = float(row[measure])
        except (KeyError, TypeError, ValueError):
            continue
    return [{"date": day, "value": value} for day, value in sorted(values.items())]


def fetch_ember_generation(spec: dict[str, Any]) -> dict[str, Any]:
    """Monthly generation for ``series`` (``EU`` or an ISO3 code) and source ``ember_series``."""
    entity = str(spec["series"])
    source_series = str(spec["ember_series"])
    measure = str(spec.get("measure") or "share_of_generation_pct")
    scope = {"entity_code": entity} if len(entity) == 3 else {"entity": entity}
    params = {**scope, "series": source_series, "start_date": str(spec.get("start_date") or "2015-01")[:7], "api_key": _require_key("EMBER_API_KEY")}
    payload = _get_json(requests.Session(), EMBER_MONTHLY_URL, params, None, "Ember")
    observations = ember_observations(payload.get("data") or [], source_series, measure)
    if not observations:
        raise RuntimeError(f"Ember returned no {source_series} rows for {entity}")
    return {**spec, "observations": observations, "provider_updated": observations[-1]["date"], "api_url": f"{EMBER_MONTHLY_URL}?{next(iter(scope))}={entity}"}
