"""Snapshot BIS WS_CBPOL policy-rate paths for every covered scope.

Runs during ``make refresh-data`` (network). The resulting
``output/bis_policy_rates.json`` lets offline steps — the Policy Tracker's BIS
reference column and the validation cross-check — compare each page's policy
rate with the BIS feed without calling the network.
"""
from __future__ import annotations

import json
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

import requests  # noqa: E402

from country_primer.bis_policy import (  # noqa: E402
    BIS_CBPOL_PAGE_URL,
    BIS_REF_AREA,
    fetch_bis_policy_rate_path,
)

OUT = ROOT / "output" / "bis_policy_rates.json"


def build(start: str = "2015-01-01") -> Path:
    previous = json.loads(OUT.read_text()).get("scopes", {}) if OUT.exists() else {}
    session = requests.Session()
    scopes: dict[str, dict] = {}
    for scope in sorted(BIS_REF_AREA):
        try:
            path = fetch_bis_policy_rate_path(scope, start=start, session=session)
        except (requests.RequestException, ValueError, KeyError) as exc:
            path = None
            print(f"{scope}: BIS fetch failed ({type(exc).__name__}); keeping previous snapshot")
        if path is None:
            if scope in previous:
                scopes[scope] = {**previous[scope], "stale_snapshot": True}
            continue
        scopes[scope] = {
            "ref_area": path.ref_area,
            "series_id": path.series_id,
            "latest_value": path.latest_value,
            "last_observation_date": path.last_observation_date,
            "change_events": [[d, v] for d, v in path.change_events],
            "glitches": [[d, v] for d, v in path.glitches],
            "source_ref": path.source_ref,
            "compilation": path.compilation,
        }
        print(f"{scope}: {path.latest_value}% as of {path.last_observation_date}")
    payload = {
        "schema_version": "bis-policy-snapshot-v1",
        "generated": datetime.now(UTC).isoformat(),
        "source_url": BIS_CBPOL_PAGE_URL,
        "scopes": scopes,
    }
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=1) + "\n")
    return OUT


if __name__ == "__main__":
    print(f"Wrote {build()}")
