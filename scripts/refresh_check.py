#!/usr/bin/env python3
"""Compare a small live headline set with committed snapshots without writing outputs."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import tempfile
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "output"


def _latest_data_first(path: Path, indicator_id: str) -> dict[str, Any]:
    payload = json.loads(path.read_text())
    for item in payload.get("series") or []:
        if item.get("indicator_id") != indicator_id:
            continue
        observations = item.get("observations") or []
        if observations:
            return {"date": str(observations[-1][0]), "value": float(observations[-1][1])}
    return {}


def _latest_cee(country: str, indicator_id: str) -> dict[str, Any]:
    snapshot = json.loads((OUTPUT / "cee_build_snapshot.json").read_text())
    row = (
        snapshot.get("countries", {})
        .get(country, {})
        .get("indicators", {})
        .get(indicator_id, {})
    )
    if not row:
        return {}
    return {"date": str(row.get("date") or ""), "value": float(row["value"])}


def _latest_live(series: dict[str, Any] | list[dict[str, Any]]) -> dict[str, Any]:
    if isinstance(series, dict):
        observations = series.get("observations") or []
        return dict(observations[-1]) if observations else {}
    return dict(series[-1]) if series else {}


def _compare(name: str, baseline: dict[str, Any], live: dict[str, Any]) -> dict[str, Any]:
    if not live:
        status = "live_unavailable"
    elif not baseline:
        status = "snapshot_missing"
    elif str(live["date"]) > str(baseline["date"]):
        status = "new_release"
    elif str(live["date"]) < str(baseline["date"]):
        status = "live_behind_snapshot"
    else:
        tolerance = max(1e-9, abs(float(baseline["value"])) * 1e-6)
        status = "revision" if abs(float(live["value"]) - float(baseline["value"])) > tolerance else "unchanged"
    return {"check": name, "status": status, "snapshot": baseline, "live": live}


def _selected(config: dict[str, Any], indicator_id: str) -> dict[str, Any]:
    return next(item for item in config.get("indicators", []) if item.get("id") == indicator_id)


def run_checks() -> list[dict[str, Any]]:
    # This must be set before importing the CEE fetch stack. Any cache writes
    # from the live probe go to a disposable directory, not the repository.
    os.environ["COUNTRY_PRIMER_CACHE_DIR"] = tempfile.mkdtemp(prefix="country-primer-refresh-check-")

    import build_china_dashboard as china
    import build_japan_dashboard as japan
    import build_south_africa_dashboard as south_africa
    import build_uk_dashboard as uk
    import build_us_dashboard as us
    from country_primer.data_fetcher import DataPipeline, INDICATOR_MANIFEST_48

    results: list[dict[str, Any]] = []
    gdp_spec = next(spec for spec in INDICATOR_MANIFEST_48 if spec.indicator_id == "real_gdp_qoq")
    for country in ("HU", "PL", "CZ", "RO"):
        try:
            live_rows = DataPipeline().fetch_country(country, [gdp_spec])
            live = _latest_live(live_rows)
        except Exception:
            live = {}
        results.append(_compare(
            f"{country}:real_gdp_qoq",
            _latest_cee(country, "real_gdp_qoq"),
            live,
        ))

    china_config = china._load_config()
    china_spec = _selected(china_config, "usd_cny_midpoint")
    try:
        live_china = _latest_live(china.fetch_safe_midpoint(china_spec, china._safe_rows()))
    except Exception:
        live_china = {}
    results.append(_compare(
        "CN:usd_cny_midpoint",
        _latest_data_first(OUTPUT / "china_canonical_frame.json", "usd_cny_midpoint"),
        live_china,
    ))

    uk_spec = _selected(uk._load_config(), "real_gdp_qoq")
    try:
        live_uk = _latest_live(uk._fetch_one(uk_spec))
    except Exception:
        live_uk = {}
    results.append(_compare(
        "UK:real_gdp_qoq",
        _latest_data_first(OUTPUT / "uk_canonical_frame.json", "real_gdp_qoq"),
        live_uk,
    ))

    japan_spec = _selected(japan._load_config(), "policy_rate")
    try:
        live_japan = _latest_live(japan._fetch_one(japan_spec))
    except Exception:
        live_japan = {}
    results.append(_compare(
        "JP:policy_rate",
        _latest_data_first(OUTPUT / "japan_canonical_frame.json", "policy_rate"),
        live_japan,
    ))

    za_spec = _selected(south_africa._load_config(), "policy_rate")
    try:
        live_za = _latest_live(south_africa._fetch_one(za_spec))
    except Exception:
        live_za = {}
    results.append(_compare(
        "ZA:policy_rate",
        _latest_data_first(OUTPUT / "south_africa_canonical_frame.json", "policy_rate"),
        live_za,
    ))

    us_spec = _selected(us._load_config(), "daily_fed_funds")
    try:
        live_us = _latest_live(us._fetch_one(us_spec))
    except Exception:
        live_us = {}
    results.append(_compare(
        "US:daily_fed_funds",
        _latest_data_first(OUTPUT / "us_canonical_frame.json", "daily_fed_funds"),
        live_us,
    ))
    return results


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--strict", action="store_true", help="Fail when a live probe is unavailable or behind.")
    args = parser.parse_args()
    results = run_checks()
    for item in results:
        snapshot = item["snapshot"]
        live = item["live"]
        print(
            f"{item['check']}: {item['status']} | "
            f"snapshot={snapshot.get('date', 'n/a')} {snapshot.get('value', 'n/a')} | "
            f"live={live.get('date', 'n/a')} {live.get('value', 'n/a')}"
        )
    if args.strict and any(item["status"] in {"live_unavailable", "live_behind_snapshot", "snapshot_missing"} for item in results):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
