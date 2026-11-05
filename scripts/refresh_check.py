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


def run_checks() -> list[dict[str, Any]]:
    # This must be set before importing the CEE fetch stack. Any cache writes
    # from the live probe go to a disposable directory, not the repository.
    os.environ["COUNTRY_PRIMER_CACHE_DIR"] = tempfile.mkdtemp(prefix="country-primer-refresh-check-")

    import sys
    sys.path.insert(0, str(ROOT / "src"))
    from country_primer.data_fetcher import DataPipeline, INDICATOR_MANIFEST_48
    from country_primer.indicator_templates import load_indicator_config
    from country_primer.fetchers import fetch_series
    from country_primer.scopes import cee_scopes, data_first_scopes

    results: list[dict[str, Any]] = []
    gdp_spec = next(spec for spec in INDICATOR_MANIFEST_48 if spec.indicator_id == "real_gdp_qoq")
    for scope in cee_scopes():
        try:
            live_rows = DataPipeline().fetch_country(scope.id, [gdp_spec])
            live = _latest_live(live_rows)
        except Exception:
            live = {}
        results.append(_compare(f"{scope.id}:real_gdp_qoq", _latest_cee(scope.id, "real_gdp_qoq"), live))

    # Each data-first scope: its registry headline series, fetched live through
    # the same global fetcher registry the builders use.
    for scope in data_first_scopes():
        assert scope.indicators_path is not None and scope.headline is not None
        config = load_indicator_config(scope.indicators_path)
        specs = {str(item.get("id")): item for item in config.get("indicators", [])}
        indicator_id = next((i for i in scope.headline.indicators if i in specs), None)
        if indicator_id is None:
            continue
        try:
            live = _latest_live(fetch_series(specs[indicator_id]["fetcher"], specs[indicator_id], {}))
        except Exception:
            live = {}
        results.append(_compare(
            f"{scope.id}:{indicator_id}",
            _latest_data_first(scope.canonical_path, indicator_id),
            live,
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
