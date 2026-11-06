"""Base- and precious-metals sources for the BASE and PRECIOUS market scopes.

* ``fetch_cn_futures_calendar_spread``: SHFE near-month minus third-month
  settlement spread, built from single-contract daily bars (Sina via AKShare,
  a public wrapper).
"""
from __future__ import annotations

import math
from datetime import UTC, datetime
from typing import Any

SINA_FUTURES_URL = "https://finance.sina.com.cn/futuremarket/"


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
