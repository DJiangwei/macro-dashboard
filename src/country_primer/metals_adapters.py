"""Base- and precious-metals sources for the BASE and PRECIOUS market scopes.

* ``fetch_cn_futures_calendar_spread``: SHFE near-month minus third-month
  settlement spread, built from single-contract daily bars (Sina via AKShare,
  a public wrapper).
* ``fetch_comex_inventory``: COMEX gold and silver warehouse stocks in tonnes,
  compiled by AKShare from CME reports (public wrapper).
* ``fetch_minem_copper``: Peruvian copper output from the Ministry of Energy and
  Mines' statistical tables (sheet S01.C01 of the latest pre-publication
  release on gob.pe). The parser locates the copper column by its header and
  checks the unit, so a layout change raises instead of reading another metal.

Keyed source (the key is read from the environment or ``.env.local``; errors
name the source and status only, never the request URL, which holds the key):

* ``fetch_bcch_series``: Banco Central de Chile statistics database through
  SieteRestWS (``BCCH_API_TOKEN``), e.g. Cochilco copper mine output.
"""
from __future__ import annotations

import io
import math
import re
import threading
from datetime import UTC, date, datetime, timedelta
from typing import Any

SINA_FUTURES_URL = "https://finance.sina.com.cn/futuremarket/"
MAX_CONSECUTIVE_CONTRACT_FAILURES = 3
COMEX_STOCKS_URL = "https://www.cmegroup.com/clearing/operations-and-deliveries/nymex-delivery-notices.html"
BCCH_URL = "https://si3.bcentral.cl/SieteRestWS/SieteRestWS.ashx"
GOB_PE = "https://www.gob.pe"
MINEM_COLLECTION_URL = f"{GOB_PE}/institucion/minem/colecciones/6-boletin-estadistico-minero"
MINEM_MONTHS = {"ene": 1, "feb": 2, "mar": 3, "abr": 4, "may": 5, "jun": 6, "jul": 7, "ago": 8, "set": 9, "sep": 9, "oct": 10, "nov": 11, "dic": 12}
_MINEM_LOCK = threading.Lock()


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


def _sessions_left_in_month(today: str) -> bool:
    """True while a weekday remains in today's month, today included (holidays are not known)."""
    day = date.fromisoformat(today)
    while day.month == date.fromisoformat(today).month:
        if day.weekday() < 5:
            return True
        day += timedelta(days=1)
    return False


def calendar_spread(settles: dict[str, dict[str, float]], start: str, today: str) -> list[dict[str, Any]]:
    """Settlement of the near contract minus the contract two months later, per trading day.

    ``settles`` maps contract ``YYMM`` to ``{date: settle}``. The near contract
    on day ``d`` is next month's, or the one after on the last trading day
    before that contract's delivery month (the roll day). The last trading day
    of a month is read from the data, so it is known once the month has no
    weekday left (``today``'s month counts as finished from its last weekend
    on); the current month never rolls early. An exchange holiday at month end
    is not known, so that month's last session shows the pre-roll pair until
    trading resumes. A day missing either leg is skipped rather than paired
    with another contract.
    """
    days = sorted({day for series in settles.values() for day in series})
    current = today[:7]
    finished = {day[:7] for day in days if day[:7] < current}
    if not _sessions_left_in_month(today):
        finished.add(current)
    last_day: dict[str, str] = {}
    for day in days:
        if day[:7] in finished:
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
    skipped: list[str] = []
    consecutive = 0
    for code in contract_months(start, today):
        symbol = f"{product}{code}"
        try:
            frame = _call_with_timeout(ak.futures_zh_daily_sina, [], {"symbol": symbol}, 30, f"futures_zh_daily_sina {symbol}")
        except Exception:
            # A transient miss leaves that contract's days out; a run of misses
            # means the source is down, and waiting out every timeout (38
            # contracts × 30 s, three attempts) would outlast the refresh job.
            skipped.append(symbol)
            consecutive += 1
            if consecutive >= MAX_CONSECUTIVE_CONTRACT_FAILURES:
                raise RuntimeError(
                    f"Sina contract bars failed for {consecutive} consecutive contracts ({', '.join(skipped[-consecutive:])}); source treated as unreachable"
                )
            continue
        consecutive = 0
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
    result = {**spec, "observations": observations, "provider_updated": observations[-1]["date"], "api_url": SINA_FUTURES_URL}
    if skipped:
        result["quality_notes"] = [f"Contracts not fetched in this refresh: {', '.join(skipped)}; days that need them are left out."]
    return result


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


def latest_minem_release(collection_html: str) -> str:
    """Path of the newest "cuadros estadísticos mineros (prepublicación)" release."""
    releases = re.findall(r"/institucion/minem/informes-publicaciones/(\d+)-cuadros-estadisticos-mineros-prepublicacion-del-bem-[a-z0-9-]+", collection_html)
    paths = re.findall(r"/institucion/minem/informes-publicaciones/\d+-cuadros-estadisticos-mineros-prepublicacion-del-bem-[a-z0-9-]+", collection_html)
    if not paths:
        raise ValueError("MINEM collection page lists no pre-publication release")
    return max(zip(map(int, releases), paths))[1]


def minem_workbook_url(publication_html: str) -> str:
    """The metallic-production workbook (``s01-produccion-minera-metalica``) attached to a release."""
    links = re.findall(r"https://cdn\.www\.gob\.pe/[^\"'\s<>]+?\.xlsx(?:\?[^\"'\s<>]*)?", publication_html)
    matches = [link for link in links if "s01-produccion-minera-metalica" in link]
    if not matches:
        raise ValueError("MINEM release has no s01-produccion-minera-metalica workbook")
    return matches[0]


def parse_minem_copper(content: bytes) -> dict[str, list[dict[str, Any]]]:
    """Copper output (kt) from sheet S01.C01: annual totals and the current year's months.

    Layout checks, each raising ValueError: the sheet exists, a header cell
    starts with PERIODO (its column holds the row labels), exactly one header
    starts with COBRE, and its unit cell below starts with TMF (fine metric
    tonnes). The year-to-date row ("2026 (Ene-Ago)") names the year of the
    month rows after it and is not itself an annual total. The month block
    ends at the first blank label: below it a year-on-year block has labels
    such as "Ago. 2025" that must not be read as this year's months.
    """
    import openpyxl

    book = openpyxl.load_workbook(io.BytesIO(content), read_only=True, data_only=True)
    if "S01.C01" not in book.sheetnames:
        raise ValueError(f"MINEM workbook has no sheet S01.C01 (sheets: {book.sheetnames})")
    rows = [list(row) for row in book["S01.C01"].iter_rows(values_only=True)]
    header = next(
        ((i, j) for i, row in enumerate(rows) for j, cell in enumerate(row) if str(cell or "").strip().upper().startswith("PERIODO")),
        None,
    )
    if header is None:
        raise ValueError("MINEM S01.C01 has no PERIODO header row")
    header_at, label_column = header
    copper = [j for j, cell in enumerate(rows[header_at]) if str(cell or "").strip().upper().startswith("COBRE")]
    if len(copper) != 1:
        raise ValueError(f"MINEM S01.C01: expected one COBRE column, found {len(copper)}")
    column = copper[0]
    unit_row = rows[header_at + 1] if header_at + 1 < len(rows) else []
    unit = str(unit_row[column] if column < len(unit_row) else "").strip()
    if not unit.upper().startswith("TMF"):
        raise ValueError(f"MINEM S01.C01: copper unit is {unit!r}, expected TMF")

    annual: list[dict[str, Any]] = []
    monthly: list[dict[str, Any]] = []
    year: int | None = None
    for row in rows[header_at + 2:]:
        label = str(row[label_column] if label_column < len(row) and row[label_column] is not None else "").strip()
        if not label:
            if monthly:
                break  # end of the month block
            continue
        if column >= len(row):
            continue
        try:
            value = float(row[column]) / 1000.0
        except (TypeError, ValueError):
            continue  # "N/D", "-" or a note
        if not math.isfinite(value):
            continue
        if re.fullmatch(r"\d{4}(\.0)?", label):
            annual.append({"date": f"{label[:4]}-01-01", "value": value})
        elif re.match(r"\d{4}\s*\(", label):
            year = int(label[:4])
        elif (month := re.fullmatch(r"([A-Za-z]{3})\.?\s*/\s*[A-Za-z]{3}\.?", label)) and month.group(1).lower() in MINEM_MONTHS:
            if year is None:
                raise ValueError("MINEM S01.C01: month row before the year-to-date row")
            monthly.append({"date": f"{year}-{MINEM_MONTHS[month.group(1).lower()]:02d}-01", "value": value})
    if not annual or not monthly:
        raise ValueError(f"MINEM S01.C01: {len(annual)} annual and {len(monthly)} monthly copper rows")
    return {"annual": annual, "monthly": monthly}


def fetch_minem_copper(spec: dict[str, Any], cache: dict[str, Any]) -> dict[str, Any]:
    """Peruvian copper output; ``measure`` is ``annual`` or ``monthly``. One download per build."""
    import requests

    from .energy_adapters import USER_AGENT

    with _MINEM_LOCK:
        parsed = cache.get("minem_copper")
        if parsed is None:
            # Both Peru indicators and their retries share one download per build:
            # after a failure they raise a plain error that cannot trip the circuit
            # (four 403s or timeouts would open it and block the whole publish).
            if cache.get("minem_copper_error"):
                raise RuntimeError(f"MINEM download failed earlier in this build ({cache['minem_copper_error']}); not retried")
            headers = {"User-Agent": USER_AGENT}
            try:
                with requests.Session() as session:
                    collection = session.get(MINEM_COLLECTION_URL, headers=headers, timeout=(5, 60))
                    collection.raise_for_status()
                    release = GOB_PE + latest_minem_release(collection.text)
                    page = session.get(release, headers=headers, timeout=(5, 60))
                    page.raise_for_status()
                    workbook = session.get(minem_workbook_url(page.text), headers=headers, timeout=(5, 60))
                    workbook.raise_for_status()
                parsed = {**parse_minem_copper(workbook.content), "release": release}
            except Exception as exc:
                cache["minem_copper_error"] = f"{type(exc).__name__}: {exc}"[:200]
                raise
            cache["minem_copper"] = parsed
    measure = str(spec["measure"])
    if measure not in ("annual", "monthly"):
        raise ValueError(f"minem_copper measure must be annual or monthly, got {measure!r}")
    observations = list(parsed[measure])
    start = str(spec.get("start_date") or "")[:10]
    if start:
        observations = [item for item in observations if item["date"] >= start]
    if not observations:
        raise RuntimeError(f"MINEM returned no {measure} copper observations")
    return {**spec, "observations": observations, "provider_updated": observations[-1]["date"], "api_url": parsed["release"]}
