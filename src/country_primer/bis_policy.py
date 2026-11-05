"""BIS WS_CBPOL central-bank policy rates, shared by every pipeline.

The BIS collects official policy rates directly from member central banks and
publishes them daily. It is the automated backbone for policy-rate tracking:
CEE pages use it as their primary source, while the Policy Tracker and the
validation contract use it to cross-check every scope that BIS covers.

Daily observations are converted into an event path (one row per confirmed
level change plus a final "as of" row). A level that appears for fewer than
``min_persistence`` consecutive observations and then reverts is treated as a
source glitch: it is excluded from the event path and reported separately so
the page can disclose it rather than silently smoothing it.
"""
from __future__ import annotations

import csv
import io
import math
from dataclasses import dataclass, field

import requests

BIS_CBPOL_CSV_URL = (
    "https://stats.bis.org/api/v2/data/dataflow/BIS/WS_CBPOL/1.0/D.{ref_area}"
    "?startPeriod={start}&format=csv"
)
BIS_CBPOL_PAGE_URL = "https://data.bis.org/topics/CBPOL"
BIS_SERIES_PREFIX = "WS_CBPOL:D"

# Scope code -> BIS reference area. Scopes BIS does not cover (TW, KZ, UZ, EG,
# NG) are deliberately absent so callers fall back to their native sources.
BIS_REF_AREA = {
    "HU": "HU", "PL": "PL", "CZ": "CZ", "RO": "RO",
    "EA": "XM", "US": "US", "UK": "GB", "JP": "JP", "CN": "CN",
    "ZA": "ZA", "TR": "TR", "KR": "KR", "HK": "HK", "IN": "IN",
}


@dataclass
class PolicyRatePath:
    ref_area: str
    events: list[tuple[str, float]]
    last_observation_date: str
    glitches: list[tuple[str, float]] = field(default_factory=list)
    compilation: str = ""
    source_ref: str = ""

    @property
    def latest_value(self) -> float | None:
        return self.events[-1][1] if self.events else None

    @property
    def series_id(self) -> str:
        return f"{BIS_SERIES_PREFIX}.{self.ref_area}"

    @property
    def change_events(self) -> list[tuple[str, float]]:
        """Level changes only (drops the trailing as-of row if it repeats)."""
        out: list[tuple[str, float]] = []
        for date, value in self.events:
            if not out or not math.isclose(out[-1][1], value, abs_tol=1e-9):
                out.append((date, value))
        return out


def fetch_bis_cbpol_daily(
    ref_area: str,
    start: str = "2000-01-01",
    session: requests.Session | None = None,
    timeout: int = 60,
) -> tuple[list[tuple[str, float]], dict[str, str]]:
    """Return (daily observations, series metadata) for one BIS reference area."""
    http = session or requests
    url = BIS_CBPOL_CSV_URL.format(ref_area=ref_area, start=start)
    response = http.get(url, timeout=timeout)
    response.raise_for_status()
    observations: list[tuple[str, float]] = []
    meta: dict[str, str] = {}
    for row in csv.DictReader(io.StringIO(response.text)):
        if not meta:
            meta = {
                "compilation": " ".join(str(row.get("COMPILATION") or "").split()),
                "source_ref": " ".join(str(row.get("SOURCE_REF") or "").split()),
                "title": " ".join(str(row.get("TITLE") or "").split()),
            }
        raw = str(row.get("OBS_VALUE") or "").strip()
        if not raw or raw.lower() == "nan":
            continue
        try:
            value = float(raw)
        except ValueError:
            continue
        observations.append((str(row["TIME_PERIOD"])[:10], value))
    observations.sort()
    return observations, meta


def to_event_path(
    daily: list[tuple[str, float]],
    min_persistence: int = 2,
) -> tuple[list[tuple[str, float]], list[tuple[str, float]]]:
    """Collapse daily observations to confirmed level changes.

    Returns ``(events, glitches)``. ``events`` contains the first observation,
    every confirmed change, and a final as-of row carrying the last
    observation date. A new level is confirmed when it persists for at least
    ``min_persistence`` consecutive observations, or when it is the most
    recent level in the sample (nothing contradicts it yet).
    """
    if not daily:
        return [], []
    events: list[tuple[str, float]] = [daily[0]]
    glitches: list[tuple[str, float]] = []
    current = daily[0][1]
    i = 1
    n = len(daily)
    while i < n:
        date, value = daily[i]
        if math.isclose(value, current, abs_tol=1e-9):
            i += 1
            continue
        run = 1
        while i + run < n and math.isclose(daily[i + run][1], value, abs_tol=1e-9):
            run += 1
        reaches_end = i + run >= n
        if run >= min_persistence or reaches_end:
            events.append((date, value))
            current = value
        else:
            glitches.extend(daily[i:i + run])
        i += run
    last_date = daily[-1][0]
    if events[-1][0] != last_date:
        events.append((last_date, current))
    return events, glitches


def fetch_bis_policy_rate_path(
    scope_code: str,
    start: str = "2000-01-01",
    session: requests.Session | None = None,
    min_persistence: int = 2,
) -> PolicyRatePath | None:
    """Fetch and normalise the BIS policy-rate path for a dashboard scope code."""
    ref_area = BIS_REF_AREA.get(scope_code.upper())
    if not ref_area:
        return None
    daily, meta = fetch_bis_cbpol_daily(ref_area, start=start, session=session)
    if not daily:
        return None
    events, glitches = to_event_path(daily, min_persistence=min_persistence)
    return PolicyRatePath(
        ref_area=ref_area,
        events=events,
        last_observation_date=daily[-1][0],
        glitches=glitches,
        compilation=meta.get("compilation", ""),
        source_ref=meta.get("source_ref", ""),
    )


def glitch_note(glitches: list[tuple[str, float]], limit: int = 3) -> str:
    """Human-readable disclosure of excluded single-observation reversals."""
    if not glitches:
        return ""
    shown = ", ".join(f"{d} ({v:g}%)" for d, v in glitches[-limit:])
    more = f" and {len(glitches) - limit} earlier" if len(glitches) > limit else ""
    return (
        f" Excluded {len(glitches)} single-observation reversal(s) in the BIS daily feed "
        f"as source glitches: {shown}{more}."
    )
