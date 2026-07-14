#!/usr/bin/env python3
"""Validate committed dashboard artefacts without refetching live data."""
from __future__ import annotations

import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "output"
COUNTRY_FILES = {
    "HU": "hungary.html",
    "PL": "poland.html",
    "CZ": "czechia.html",
    "RO": "romania.html",
    "CN": "china.html",
    "UK": "uk.html",
    "US": "us.html",
}


def _load_json(path: Path) -> dict:
    if not path.exists():
        raise AssertionError(f"Missing generated artefact: {path}")
    return json.loads(path.read_text())


def validate_output_contract(root: Path = ROOT) -> list[str]:
    output = root / "output"
    messages: list[str] = []

    for code, filename in COUNTRY_FILES.items():
        path = output / filename
        if not path.exists():
            raise AssertionError(f"Missing stable country route: {path}")
        text = path.read_text()
        if 'data-dashboard-view="core"' not in text or "Core 48" not in text:
            raise AssertionError(f"{filename} is missing the core/deep chart view")
        if "cp-dashboard-view" not in text:
            raise AssertionError(f"{filename} does not persist the chart-view preference")
        if text.count(" Dashboard Dashboard"):
            raise AssertionError(f"{filename} contains a duplicated dashboard title")
        messages.append(f"{code}: stable route and view contract ok")

    for name in ("china", "uk", "us"):
        text = (output / f"{name}.html").read_text()
        cards = len(re.findall(r'class="chart-card', text))
        divs = re.findall(r'id="(chart-[^"]+)" class="plotly-chart"', text)
        plots = re.findall(r'Plotly\.newPlot\("(chart-[^"]+)"', text)
        if not cards or cards != len(divs) or set(divs) != set(plots):
            raise AssertionError(f"{name}.html has mismatched chart cards, divs, or Plotly calls")
        canonical = _load_json(output / f"{name}_canonical_frame.json")
        if canonical.get("schema_version") != "data-first-canonical-v2":
            raise AssertionError(f"{name} canonical output is not v2")
        if len(canonical.get("series") or []) != cards:
            raise AssertionError(f"{name} canonical series count does not match rendered charts")
        if not all("quality" in item and "concept_id" in item for item in canonical["series"]):
            raise AssertionError(f"{name} canonical metadata is incomplete")

    snapshot = _load_json(output / "cee_build_snapshot.json")
    if snapshot.get("schema_version") != "cee-build-snapshot-v1":
        raise AssertionError("CEE snapshot schema mismatch")
    if set((snapshot.get("countries") or {})) != {"HU", "PL", "CZ", "RO"}:
        raise AssertionError("CEE snapshot must contain all four countries")
    for code, payload in snapshot["countries"].items():
        indicators = payload.get("indicators") or {}
        if not indicators:
            raise AssertionError(f"CEE snapshot has no indicators for {code}")
        if any(bool(item.get("is_proxy")) for item in indicators.values()):
            raise AssertionError(f"CEE snapshot contains a proxy row for {code}")

    archive = _load_json(output / "dashboard_archive_summary.json")
    cards = archive.get("cards") or []
    if len(cards) != 7:
        raise AssertionError(f"Archive expected seven countries, found {len(cards)}")
    if {card.get("file") for card in cards} != set(COUNTRY_FILES.values()):
        raise AssertionError("Archive country routes do not match stable output routes")
    for index_path in (root / "index.html", output / "index.html"):
        text = index_path.read_text()
        for filename in COUNTRY_FILES.values():
            if filename not in text:
                raise AssertionError(f"{index_path} is missing {filename}")

    return messages


def main() -> int:
    for message in validate_output_contract():
        print(message)
    print("Generated output contract passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
