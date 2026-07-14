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
        chart_count = (
            len(re.findall(r'class="chart-card(?:\s|\")', text))
            if code in {"CN", "UK", "US"}
            else text.count('class="chart-cell chart-shell"')
        )
        if chart_count and text.count("data-latest-reading") != chart_count:
            raise AssertionError(f"{filename} does not show a latest reading for every chart")
        messages.append(f"{code}: stable route and view contract ok")

    for name in ("china", "uk", "us"):
        text = (output / f"{name}.html").read_text()
        cards = len(re.findall(r'class="chart-card', text))
        divs = re.findall(r'id="(chart-[^"]+)" class="plotly-chart"', text)
        plots = re.findall(r'Plotly\.newPlot\("(chart-[^"]+)"', text)
        if not cards or cards != len(divs) or set(divs) != set(plots):
            raise AssertionError(f"{name}.html has mismatched chart cards, divs, or Plotly calls")
        if text.count('meta": "cp-latest-marker"') != cards:
            raise AssertionError(f"{name}.html is missing one endpoint marker per chart")
        canonical = _load_json(output / f"{name}_canonical_frame.json")
        if canonical.get("schema_version") != "data-first-canonical-v2":
            raise AssertionError(f"{name} canonical output is not v2")
        if len(canonical.get("series") or []) != cards:
            raise AssertionError(f"{name} canonical series count does not match rendered charts")
        if not all("quality" in item and "concept_id" in item for item in canonical["series"]):
            raise AssertionError(f"{name} canonical metadata is incomplete")
        summary = _load_json(output / f"{name}_dashboard_summary.json")
        if summary.get("data_mode") not in {"refresh", "snapshot"}:
            raise AssertionError(f"{name} summary is missing its data mode")
        if summary.get("canonical_frame", {}).get("series_count") != cards:
            raise AssertionError(f"{name} summary canonical count does not match rendered charts")

    cee_canonical = _load_json(output / "cee_canonical_frame.json")
    if cee_canonical.get("schema_version") != "cee-canonical-v2":
        raise AssertionError("CEE canonical history schema mismatch")
    if {item.get("country") for item in cee_canonical.get("series") or []} != {"HU", "PL", "CZ", "RO"}:
        raise AssertionError("CEE canonical history must contain all four countries")

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

    source_health = _load_json(output / "source_health.json")
    if source_health.get("schema_version") != "source-health-v1":
        raise AssertionError("Source-health schema mismatch")
    if set((source_health.get("countries") or {})) != set(COUNTRY_FILES):
        raise AssertionError("Source-health report must contain all seven countries")
    if any(payload.get("circuit_open") for payload in source_health["countries"].values()):
        raise AssertionError("Source-health report contains an open source circuit")

    coverage = _load_json(output / "core_coverage_matrix.json")
    if coverage.get("schema_version") != "core-coverage-v1":
        raise AssertionError("Core coverage matrix schema mismatch")
    if coverage.get("concept_count") != 48 or len(coverage.get("concepts") or []) != 48:
        raise AssertionError("Core coverage matrix must contain 48 concepts")
    if coverage.get("countries") != list(COUNTRY_FILES):
        raise AssertionError("Core coverage matrix country order mismatch")

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
