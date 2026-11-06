"""Base- and precious-metals sources for the BASE and PRECIOUS market scopes.

* ``fetch_cn_futures_calendar_spread``: SHFE near-month minus third-month
  settlement spread, built from single-contract daily bars (Sina via AKShare,
  a public wrapper).
* ``fetch_comex_inventory``: COMEX gold and silver warehouse stocks in tonnes,
  compiled by AKShare from CME reports (public wrapper).

Keyed source (the key is read from the environment or ``.env.local``; errors
name the source and status only, never the request URL, which holds the key):

* ``fetch_bcch_series``: Banco Central de Chile statistics database through
  SieteRestWS (``BCCH_API_TOKEN``), e.g. Cochilco copper mine output.
"""
from __future__ import annotations

import math
from datetime import UTC, datetime
from typing import Any

SINA_FUTURES_URL = "https://finance.sina.com.cn/futuremarket/"
COMEX_STOCKS_URL = "https://www.cmegroup.com/clearing/operations-and-deliveries/nymex-delivery-notices.html"
BCCH_URL = "https://si3.bcentral.cl/SieteRestWS/SieteRestWS.ashx"


def _shift_month(year_month: str, months: int) -> str:
    index = int(year_month[:4]) * 12 + int(year_month[5:7]) - 1 + months
    return f"{index // 12:04d}-{index % 12 + 1:02d}"


def _contract_code(year_month: str) -> str:
    return year_month[2:4] + year_month[5:7]


def contract_months(start: str, today: str, ahead: int = 3) -> list[str]:
    """Contract codes (``YYMM``) from the month of ``start`` to ``ahead`` months after ``today``."""
    codes, month, last = [], start[:7], _shift_month(today[:7], ahead)
    while month <= last:
        codes.append(_contract_code(month))
        month = _shift_month(month, 1)
    return codes


def calendar_spread(settles: dict[str, dict[str, float]], start: str, today: str) -> list[dict[str, Any]]:
    """Settlement of the near contract minus the contract two months later, per trading day.

    ``settles`` maps contract ``YYMM`` to ``{date: settle}``. The near contract
    on day ``d`` is next month's, or the one after on the last trading day
    before that contract's delivery month (the roll day). The last trading day
    of a month is read from the data, so it is only known for months before
    ``today``'s; the current month never rolls early. A day missing either leg
    is skipped rather than paired with another contract.
    """
    days = sorted({day for series in settles.values() for day in series})
    current = today[:7]
    last_day: dict[str, str] = {}
    for day in days:
        if day[:7] < current:
            last_day[day[:7]] = day  # days are sorted, so the last write is the month's last day
    rows = []
    for day in days:
        if day < start or day >= today:
            continue
        month = day[:7]
        rolled = month in last_day and day >= last_day[month]
        near = _shift_month(month, 2 if rolled else 1)
        near_value = settles.get(_contract_code(near), {}).get(day)
        far_value = settles.get(_contract_code(_shift_month(near, 2)), {}).get(day)
        if near_value is None or far_value is None:
            continue
        rows.append({"date": day, "value": near_value - far_value})
    return rows


def fetch_cn_futures_calendar_spread(spec: dict[str, Any]) -> dict[str, Any]:
    """SHFE near minus third-month spread for the product code in ``series`` (e.g. ``CU``)."""
    import akshare as ak

    from .adapters import _call_with_timeout

    product = str(spec["series"]).upper()
    start = str(spec["start_date"])[:10]
    today = datetime.now(UTC).date().isoformat()
    settles: dict[str, dict[str, float]] = {}
    for code in contract_months(start, today):
        symbol = f"{product}{code}"
        try:
            frame = _call_with_timeout(ak.futures_zh_daily_sina, [], {"symbol": symbol}, 30, f"futures_zh_daily_sina {symbol}")
        except Exception:
            continue  # a contract not yet listed, or a transient miss: its days are skipped
        rows = {}
        for day, settle in zip(frame["date"], frame["settle"]):
            try:
                value = float(settle)
            except (TypeError, ValueError):
                continue
            if math.isfinite(value) and value > 0:
                rows[str(day)[:10]] = value
        if rows:
            settles[code] = rows
    observations = calendar_spread(settles, start, today)
    if not observations:
        raise RuntimeError(f"No SHFE calendar spread could be built for {product}")
    return {**spec, "observations": observations, "provider_updated": observations[-1]["date"], "api_url": SINA_FUTURES_URL}


def comex_observations(frame: Any, today: str) -> list[dict[str, Any]]:
    """Daily stocks in tonnes from AKShare's COMEX inventory frame, completed days only."""
    tonnes = [column for column in frame.columns if str(column).endswith("-吨")]
    if len(tonnes) != 1:
        raise ValueError(f"Expected one '-吨' column in the COMEX inventory frame, got {list(frame.columns)}")
    observations = []
    for day, raw in zip(frame["日期"], frame[tonnes[0]]):
        day = str(day)[:10]
        try:
            value = float(raw)
        except (TypeError, ValueError):
            continue
        if day < today and math.isfinite(value) and value > 0:
            observations.append({"date": day, "value": value})
    observations.sort(key=lambda item: item["date"])
    return observations


def fetch_comex_inventory(spec: dict[str, Any]) -> dict[str, Any]:
    """COMEX warehouse stocks for the AKShare symbol in ``series`` (黄金 or 白银)."""
    import akshare as ak

    from .adapters import _call_with_timeout

    symbol = str(spec["series"])
    frame = _call_with_timeout(ak.futures_comex_inventory, [], {"symbol": symbol}, 60, f"futures_comex_inventory {symbol}")
    observations = comex_observations(frame, datetime.now(UTC).date().isoformat())
    start = str(spec.get("start_date") or "")[:10]
    if start:
        observations = [item for item in observations if item["date"] >= start]
    if not observations:
        raise RuntimeError(f"No COMEX inventory rows for {symbol}")
    return {**spec, "observations": observations, "provider_updated": observations[-1]["date"], "api_url": COMEX_STOCKS_URL}


def bcch_observations(payload: dict[str, Any]) -> list[dict[str, Any]]:
    """Observations from a SieteRestWS GetSeries payload; rows not marked OK are skipped.

    A bad token still answers HTTP 200, with ``Codigo`` -5, so the code is checked here.
    """
    code = payload.get("Codigo")
    if code != 0:
        raise RuntimeError(f"BCCh returned code {code}: {payload.get('Descripcion') or 'no description'}")
    observations = []
    for row in (payload.get("Series") or {}).get("Obs") or []:
        if row.get("statusCode") != "OK":
            continue
        try:
            value = float(row.get("value"))
            day, month, year = str(row.get("indexDateString")).split("-")
        except (TypeError, ValueError):
            continue
        if math.isfinite(value):
            observations.append({"date": f"{year}-{month}-{day}", "value": value})
    observations.sort(key=lambda item: item["date"])
    return observations


def fetch_bcch_series(spec: dict[str, Any]) -> dict[str, Any]:
    """One BCCh series (``series`` is the series id) from ``start_date`` on."""
    import requests

    from .energy_adapters import _get_json, _require_key

    params = {
        "token": _require_key("BCCH_API_TOKEN"),
        "function": "GetSeries",
        "timeseries": str(spec["series"]),
        "firstdate": str(spec["start_date"])[:10],
    }
    with requests.Session() as session:
        payload = _get_json(session, BCCH_URL, params, None, "BCCh")
    observations = bcch_observations(payload)
    if not observations:
        raise RuntimeError(f"BCCh returned no observations for {spec['series']}")
    return {**spec, "observations": observations, "provider_updated": observations[-1]["date"], "api_url": "https://si3.bcentral.cl/siete"}
