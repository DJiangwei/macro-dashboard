"""Data fetcher: cache-first, with HTTP fallbacks for ECB XML and World Bank.

Design: in v1 the openecon-data MCP is only callable from inside Claude Code.
For each indicator we resolve a cache key from the MCP query string; the cached
JSON is what was fetched in-session. If a cache file is missing, we try a
public HTTP fallback (only ECB-XML and World Bank are wired); otherwise we
return an empty Series with a flag so the chart renders a "data unavailable"
note instead of crashing.
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional
from xml.etree import ElementTree as ET

import requests

CACHE_DIR = Path(__file__).resolve().parents[2] / "cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)


@dataclass
class Series:
    key: str
    label: str
    country: str
    source: str = "unknown"
    series_id: str = ""
    unit: str = ""
    frequency: str = ""
    last_update: str = ""
    fetched: str = ""
    source_url: str = ""
    observations: list[tuple[str, float]] = field(default_factory=list)
    available: bool = True
    note: str = ""

    @property
    def latest(self) -> Optional[tuple[str, float]]:
        return self.observations[-1] if self.observations else None

    def to_dict(self) -> dict:
        return {
            "key": self.key,
            "label": self.label,
            "country": self.country,
            "source": self.source,
            "series_id": self.series_id,
            "unit": self.unit,
            "frequency": self.frequency,
            "last_update": self.last_update,
            "fetched": self.fetched,
            "source_url": self.source_url,
            "observations": self.observations,
            "available": self.available,
            "note": self.note,
        }


def cache_key(query: str) -> str:
    return hashlib.sha1(query.strip().lower().encode()).hexdigest()[:16]


def cache_path(query: str) -> Path:
    return CACHE_DIR / f"{cache_key(query)}.json"


def save_mcp_response(query: str, response: dict) -> Path:
    """Called from the MCP-prefetch step to persist a raw MCP response."""
    p = cache_path(query)
    payload = {"query": query, "response": response, "fetched": datetime.utcnow().isoformat() + "Z"}
    p.write_text(json.dumps(payload, indent=2))
    return p


def _parse_mcp_response(query: str, payload: dict, key: str, label: str, country: str) -> Series:
    """Convert a cached MCP response into a Series."""
    response = payload.get("response", {})
    fetched = payload.get("fetched", "")
    data_block = response.get("data") or []
    if not data_block:
        return Series(key=key, label=label, country=country, available=False,
                      note="MCP returned no data", fetched=fetched)
    entry = data_block[0]
    meta = entry.get("metadata", {}) or {}
    obs = entry.get("data") or []
    cleaned: list[tuple[str, float]] = []
    for o in obs:
        d = (o.get("date") or "").strip()
        v = o.get("value")
        if d and v is not None:
            # Eurostat sometimes returns "2026-03-01-01" — normalize.
            d_norm = re.sub(r"-(\d{2})-\d{2}$", r"-\1-01", d) if d.count("-") >= 3 else d
            try:
                cleaned.append((d_norm, float(v)))
            except (TypeError, ValueError):
                continue
    return Series(
        key=key,
        label=label,
        country=country,
        source=meta.get("source", "MCP"),
        series_id=meta.get("seriesId", ""),
        unit=meta.get("unit", ""),
        frequency=meta.get("frequency", ""),
        last_update=str(meta.get("lastUpdated", ""))[:10],
        source_url=meta.get("sourceUrl", ""),
        fetched=fetched[:10],
        observations=cleaned,
        available=bool(cleaned),
    )


def fetch_from_cache(query: str, key: str, label: str, country: str) -> Series:
    p = cache_path(query)
    if not p.exists():
        return Series(key=key, label=label, country=country, available=False,
                      note=f"No cached data for query: {query!r}")
    payload = json.loads(p.read_text())
    return _parse_mcp_response(query, payload, key, label, country)


# ---------- HTTP fallbacks (no API key needed) ----------

ECB_XML_URL = "https://www.ecb.europa.eu/stats/eurofxref/eurofxref-hist-90d.xml"
WB_URL = "https://api.worldbank.org/v2/country/{iso2}/indicator/{code}?format=json&per_page=200&date={start}:{end}"


def fetch_ecb_fx(currency: str, key: str, label: str, country: str) -> Series:
    """ECB daily reference rates (last 90 days). Returns EUR/<currency> per the source."""
    today = datetime.utcnow().strftime("%Y-%m-%d")
    cache_q = f"ecb_xml::{currency}::90d"
    cp = cache_path(cache_q)
    if cp.exists():
        body = cp.read_text()
    else:
        try:
            r = requests.get(ECB_XML_URL, timeout=15)
            r.raise_for_status()
            body = r.text
            cp.write_text(body)
        except Exception as e:
            return Series(key=key, label=label, country=country, available=False,
                          note=f"ECB fetch failed: {e}")
    obs: list[tuple[str, float]] = []
    try:
        root = ET.fromstring(body)
        ns = {"g": "http://www.gesmes.org/xml/2002-08-01",
              "e": "http://www.ecb.int/vocabulary/2002-08-01/eurofxref"}
        for cube in root.findall(".//e:Cube[@time]", ns):
            d = cube.attrib["time"]
            for c in cube.findall("e:Cube", ns):
                if c.attrib.get("currency") == currency:
                    obs.append((d, float(c.attrib["rate"])))
        obs.sort()
    except Exception as e:
        return Series(key=key, label=label, country=country, available=False,
                      note=f"ECB parse failed: {e}")
    return Series(
        key=key, label=label, country=country,
        source="ECB", series_id=f"EURFXREF/{currency}",
        unit=f"{currency} per EUR", frequency="daily",
        last_update=obs[-1][0] if obs else "",
        source_url="https://www.ecb.europa.eu/stats/eurofxref/",
        fetched=today, observations=obs, available=bool(obs),
    )


EUROSTAT_URL = "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/{dataset}?{params}"


def fetch_eurostat(dataset: str, geo: str, key: str, label: str, country: str,
                   freq: str = "M", since: str = "2018",
                   extra_params: dict | None = None,
                   unit_label: str = "", indicator_label: str = "") -> Series:
    """Generic Eurostat JSON-stat fetcher. Returns a sorted monthly time series."""
    today = datetime.utcnow().strftime("%Y-%m-%d")
    params = {"geo": geo, "freq": freq, "sinceTimePeriod": since}
    if extra_params:
        params.update(extra_params)
    qs = "&".join(f"{k}={v}" for k, v in params.items())
    cache_q = f"eurostat::{dataset}::{geo}::{freq}::{since}::{qs}"
    cp = cache_path(cache_q)
    if cp.exists():
        data = json.loads(cp.read_text())
    else:
        try:
            r = requests.get(EUROSTAT_URL.format(dataset=dataset, params=qs), timeout=20)
            r.raise_for_status()
            data = r.json()
            cp.write_text(json.dumps(data))
        except Exception as e:
            return Series(key=key, label=label, country=country, available=False,
                          note=f"Eurostat fetch failed: {e}")
    try:
        time_cat = data["dimension"]["time"]["category"]["index"]
        # time_cat: {"2024-01": 0, "2024-02": 1, ...}
        times_by_idx = {v: k for k, v in time_cat.items()}
        values = data.get("value", {})
        unit = unit_label or data.get("dimension", {}).get("unit", {}).get("category", {}).get("label", {})
        if isinstance(unit, dict):
            unit = next(iter(unit.values()), "")
        obs: list[tuple[str, float]] = []
        for idx_str, val in values.items():
            idx = int(idx_str)
            t = times_by_idx.get(idx)
            if t is None or val is None:
                continue
            # Normalize Eurostat time codes to ISO YYYY-MM-DD.
            if len(t) == 4:                     # annual: "2025"
                d = f"{t}-12-31"
            elif "-Q" in t:                     # quarterly: "2025-Q4" → "2025-10-01"
                yr, q = t.split("-Q")
                month = (int(q) - 1) * 3 + 1
                d = f"{yr}-{month:02d}-01"
            elif len(t) == 7:                   # monthly: "2025-12"
                d = f"{t}-01"
            else:
                d = t
            obs.append((d, float(val)))
        obs.sort()
    except Exception as e:
        return Series(key=key, label=label, country=country, available=False,
                      note=f"Eurostat parse failed: {e}")
    return Series(
        key=key, label=label, country=country,
        source="Eurostat",
        series_id=dataset,
        unit=unit if isinstance(unit, str) else "",
        frequency={"M": "monthly", "Q": "quarterly", "A": "annual"}.get(freq, freq),
        last_update=obs[-1][0] if obs else "",
        source_url=f"https://ec.europa.eu/eurostat/databrowser/view/{dataset}/default/table?lang=en",
        fetched=today, observations=obs, available=bool(obs),
    )


YAHOO_CHART_URL = "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?range={range_}&interval={interval}"


def fetch_yahoo(symbol: str, key: str, label: str, country: str,
                range_: str = "5y", interval: str = "1mo") -> Series:
    """Yahoo Finance chart endpoint — equity indexes, FX crosses."""
    today = datetime.utcnow().strftime("%Y-%m-%d")
    cache_q = f"yahoo::{symbol}::{range_}::{interval}"
    cp = cache_path(cache_q)
    headers = {"User-Agent": "Mozilla/5.0"}
    if cp.exists():
        data = json.loads(cp.read_text())
    else:
        try:
            url = YAHOO_CHART_URL.format(
                symbol=symbol.replace("^", "%5E"), range_=range_, interval=interval)
            r = requests.get(url, headers=headers, timeout=20)
            r.raise_for_status()
            data = r.json()
            cp.write_text(json.dumps(data))
        except Exception as e:
            return Series(key=key, label=label, country=country, available=False,
                          note=f"Yahoo fetch failed: {e}")
    try:
        result = data["chart"]["result"][0]
        ts = result["timestamp"]
        close = result["indicators"]["quote"][0]["close"]
        currency = result["meta"].get("currency", "")
        obs: list[tuple[str, float]] = []
        for t, v in zip(ts, close):
            if v is None:
                continue
            d = datetime.utcfromtimestamp(t).strftime("%Y-%m-01")
            obs.append((d, float(v)))
        obs.sort()
    except Exception as e:
        return Series(key=key, label=label, country=country, available=False,
                      note=f"Yahoo parse failed: {e}")
    return Series(
        key=key, label=label, country=country,
        source="Yahoo Finance", series_id=symbol,
        unit=currency, frequency=interval,
        last_update=obs[-1][0] if obs else "",
        source_url=f"https://finance.yahoo.com/quote/{symbol}",
        fetched=today, observations=obs, available=bool(obs),
    )


OEC_API_BASE = "https://api-v2.oec.world/tesseract/data.jsonrecords"
OEC_TOKEN = ""  # Set via env var OEC_TOKEN for authenticated access


def fetch_oec_trade(iso3: str, key: str, label: str, country: str,
                    year: int = 2024) -> Series:
    """Fetch trade data from OEC API. Requires OEC_TOKEN env var for v2 API.
    Falls back to a note if unavailable."""
    today = datetime.utcnow().strftime("%Y-%m-%d")
    cache_q = f"oec::{iso3}::{year}"
    cp = cache_path(cache_q)
    if cp.exists():
        data = json.loads(cp.read_text())
    else:
        import os
        token = os.environ.get("OEC_TOKEN", OEC_TOKEN)
        if not token:
            return Series(key=key, label=label, country=country, available=False,
                          note="OEC API requires OEC_TOKEN env var. Get a free token at https://oec.world/en/resources/api")
        params = {
            "cube": "trade_i_baci_a_22",
            "drilldowns": "Partner+Country,Year",
            "measures": "Trade+Value",
            "include": f"Reporter+Country:{iso3.lower()};Year:{year}",
            "limit": "50,0",
            "token": token,
        }
        qs = "&".join(f"{k}={v}" for k, v in params.items())
        try:
            r = requests.get(f"{OEC_API_BASE}?{qs}", timeout=20)
            r.raise_for_status()
            data = r.json()
            cp.write_text(json.dumps(data))
        except Exception as e:
            return Series(key=key, label=label, country=country, available=False,
                          note=f"OEC fetch failed: {e}")
    try:
        rows = data.get("data", [])
        obs: list[tuple[str, float]] = []
        partner_totals: dict[str, float] = {}
        for row in rows:
            partner = row.get("Partner Country", "")
            val = row.get("Trade Value", 0)
            yr = row.get("Year", year)
            partner_totals[partner] = partner_totals.get(partner, 0) + float(val)
        # Store as observations sorted by value
        for partner, val in sorted(partner_totals.items(), key=lambda x: -x[1]):
            obs.append((partner, val))
    except Exception as e:
        return Series(key=key, label=label, country=country, available=False,
                      note=f"OEC parse failed: {e}")
    return Series(
        key=key, label=label, country=country,
        source="OEC", series_id=f"trade_i_baci_a_22/{iso3}",
        unit="USD", frequency="annual",
        last_update=str(year),
        source_url=f"https://oec.world/en/profile/country/{iso3.lower()}",
        fetched=today, observations=obs if obs else [(f"total_{year}", 0.0)],
        available=bool(obs),
    )


def fetch_wb(iso2: str, code: str, key: str, label: str, country: str,
             start: int = 2010, end: int = 2026) -> Series:
    today = datetime.utcnow().strftime("%Y-%m-%d")
    cache_q = f"wb::{iso2}::{code}::{start}-{end}"
    cp = cache_path(cache_q)
    if cp.exists():
        data = json.loads(cp.read_text())
    else:
        url = WB_URL.format(iso2=iso2, code=code, start=start, end=end)
        try:
            r = requests.get(url, timeout=20)
            r.raise_for_status()
            data = r.json()
            cp.write_text(json.dumps(data))
        except Exception as e:
            return Series(key=key, label=label, country=country, available=False,
                          note=f"World Bank fetch failed: {e}")
    if not isinstance(data, list) or len(data) < 2 or not data[1]:
        return Series(key=key, label=label, country=country, available=False,
                      note="World Bank returned no data")
    rows = data[1]
    obs: list[tuple[str, float]] = []
    for row in rows:
        v = row.get("value")
        d = row.get("date")
        if v is not None and d:
            obs.append((f"{d}-12-31", float(v)))
    obs.sort()
    return Series(
        key=key, label=label, country=country,
        source="World Bank", series_id=code, unit="",
        frequency="annual",
        last_update=obs[-1][0][:4] if obs else "",
        source_url=f"https://data.worldbank.org/indicator/{code}",
        fetched=today, observations=obs, available=bool(obs),
    )
