#!/usr/bin/env python3
"""Build the seven-country by 48-concept comparable-core coverage matrix."""
from __future__ import annotations

from datetime import UTC, datetime
import json
from pathlib import Path
from typing import Any

from country_primer.framework import load_macro_framework


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "output"
OUT_JSON = OUTPUT / "core_coverage_matrix.json"
OUT_MD = ROOT / "CORE_COVERAGE_MATRIX.md"
COUNTRIES = ("HU", "PL", "CZ", "RO", "CN", "UK", "US")
DATA_FIRST_FILES = {
    "CN": OUTPUT / "china_canonical_frame.json",
    "UK": OUTPUT / "uk_canonical_frame.json",
    "US": OUTPUT / "us_canonical_frame.json",
}
QUALITY_RANK = {"verified": 4, "watch": 3, "low_confidence": 2, "unavailable": 1}


def _cee_records() -> list[dict[str, Any]]:
    payload = json.loads((OUTPUT / "cee_canonical_frame.json").read_text())
    records: list[dict[str, Any]] = []
    for item in payload.get("series") or []:
        metadata = dict(item.get("metadata") or {})
        observations = item.get("observations") or []
        records.append({
            "country": item.get("country"),
            "indicator_id": item.get("indicator_id"),
            "concept_id": metadata.get("concept_id"),
            "quality_status": metadata.get("quality_status") or "watch",
            "derivation": metadata.get("derivation") or "observed",
            "comparability": metadata.get("comparability") or "medium",
            "refresh_fallback": bool(metadata.get("refresh_fallback")),
            "latest_date": str(observations[-1][0]) if observations else "",
        })
    return records


def _data_first_records(country: str, path: Path) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text())
    records: list[dict[str, Any]] = []
    for item in payload.get("series") or []:
        quality = dict(item.get("quality") or {})
        observations = item.get("observations") or []
        records.append({
            "country": country,
            "indicator_id": item.get("indicator_id"),
            "concept_id": item.get("concept_id"),
            "quality_status": quality.get("status") or "watch",
            "derivation": quality.get("derivation") or "observed",
            "comparability": quality.get("comparability") or "medium",
            "refresh_fallback": bool(item.get("refresh_fallback") or quality.get("refresh_fallback")),
            "latest_date": str(observations[-1][0]) if observations else "",
        })
    return records


def _cell(records: list[dict[str, Any]]) -> dict[str, Any]:
    if not records:
        return {
            "state": "missing",
            "quality_status": "unavailable",
            "indicator_ids": [],
            "latest_date": "",
            "refresh_fallback": False,
        }
    best = max(
        records,
        key=lambda item: (
            item.get("derivation") != "substitute",
            item.get("comparability") != "low",
            QUALITY_RANK.get(str(item.get("quality_status")), 0),
            str(item.get("latest_date") or ""),
        ),
    )
    quality = str(best.get("quality_status") or "watch")
    if best.get("derivation") == "substitute" or best.get("comparability") == "low":
        state = "substitute"
    elif quality == "verified":
        state = "verified"
    elif quality == "low_confidence":
        state = "low_confidence"
    else:
        state = "watch"
    return {
        "state": state,
        "quality_status": quality,
        "indicator_ids": sorted({str(item.get("indicator_id")) for item in records}),
        "latest_date": max((str(item.get("latest_date") or "") for item in records), default=""),
        "refresh_fallback": any(bool(item.get("refresh_fallback")) for item in records),
    }


def build_matrix() -> dict[str, Any]:
    framework = load_macro_framework()
    records = _cee_records()
    for country, path in DATA_FIRST_FILES.items():
        records.extend(_data_first_records(country, path))

    by_concept_country: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for item in records:
        concept_id = str(item.get("concept_id") or "")
        country = str(item.get("country") or "")
        if concept_id in framework.concept_ids and country in COUNTRIES:
            by_concept_country.setdefault((concept_id, country), []).append(item)

    concepts: list[dict[str, Any]] = []
    country_counts = {
        country: {"verified": 0, "watch": 0, "low_confidence": 0, "substitute": 0, "missing": 0}
        for country in COUNTRIES
    }
    for order, concept in enumerate(framework.concepts, start=1):
        cells = {
            country: _cell(by_concept_country.get((concept.concept_id, country), []))
            for country in COUNTRIES
        }
        for country, cell in cells.items():
            country_counts[country][cell["state"]] += 1
        missing = sum(cell["state"] == "missing" for cell in cells.values())
        weak = sum(cell["state"] in {"substitute", "low_confidence"} for cell in cells.values())
        priority_weight = int(framework.pillars[concept.pillar].get("priority_weight") or 1)
        concepts.append({
            "order": order,
            "concept_id": concept.concept_id,
            "pillar": concept.pillar,
            "label_en": concept.label_en,
            "label_zh": concept.label_zh,
            "unit": concept.unit,
            "priority_weight": priority_weight,
            "missing_countries": missing,
            "weak_countries": weak,
            "priority_score": priority_weight * 10 + missing * 5 + weak * 2,
            "countries": cells,
        })

    priorities = sorted(
        [item for item in concepts if item["missing_countries"] or item["weak_countries"]],
        key=lambda item: (-item["priority_score"], item["order"]),
    )
    return {
        "schema_version": "core-coverage-v1",
        "generated": datetime.now(UTC).isoformat(),
        "framework_version": framework.version,
        "countries": list(COUNTRIES),
        "concept_count": len(concepts),
        "legend": {
            "verified": "Official-primary, observed, current, validation passed",
            "watch": "Usable with a mirror, derivation, cadence, or validation caveat",
            "low_confidence": "Stale or otherwise low-confidence public series",
            "substitute": "Conceptual substitute or low-comparability implementation",
            "missing": "No mapped canonical series",
        },
        "country_summary": country_counts,
        "concepts": concepts,
        "priorities": [
            {
                "concept_id": item["concept_id"],
                "pillar": item["pillar"],
                "label_en": item["label_en"],
                "priority_score": item["priority_score"],
                "missing_countries": [
                    country for country, cell in item["countries"].items()
                    if cell["state"] == "missing"
                ],
                "weak_countries": [
                    country for country, cell in item["countries"].items()
                    if cell["state"] in {"substitute", "low_confidence"}
                ],
            }
            for item in priorities
        ],
    }


def _markdown(payload: dict[str, Any]) -> str:
    token = {
        "verified": "V",
        "watch": "W",
        "low_confidence": "L",
        "substitute": "S",
        "missing": "-",
    }
    lines = [
        "# Core 48 Coverage Matrix",
        "",
        f"Generated: {payload['generated']}",
        "",
        "Legend: `V` verified, `W` watch, `L` low confidence, `S` substitute/low comparability, `-` missing.",
        "",
        "| # | Pillar | Concept | " + " | ".join(payload["countries"]) + " |",
        "|---:|---|---|" + "---:|" * len(payload["countries"]),
    ]
    for item in payload["concepts"]:
        cells = " | ".join(token[item["countries"][country]["state"]] for country in payload["countries"])
        lines.append(f"| {item['order']} | `{item['pillar']}` | `{item['concept_id']}` {item['label_en']} | {cells} |")

    lines.extend(["", "## Country Summary", "", "| Country | Covered | Verified | Watch | Low | Substitute | Missing |", "|---|---:|---:|---:|---:|---:|---:|"])
    for country in payload["countries"]:
        counts = payload["country_summary"][country]
        covered = payload["concept_count"] - counts["missing"]
        lines.append(
            f"| {country} | {covered}/{payload['concept_count']} | {counts['verified']} | "
            f"{counts['watch']} | {counts['low_confidence']} | {counts['substitute']} | {counts['missing']} |"
        )

    lines.extend(["", "## Priority Gaps", "", "Priority is explicit and reproducible: pillar macro-value weight x10, plus 5 points per missing country and 2 per weak implementation.", "", "| Rank | Concept | Pillar | Score | Missing | Weak |", "|---:|---|---|---:|---|---|"])
    for rank, item in enumerate(payload["priorities"][:24], start=1):
        lines.append(
            f"| {rank} | `{item['concept_id']}` {item['label_en']} | `{item['pillar']}` | "
            f"{item['priority_score']} | {', '.join(item['missing_countries']) or '-'} | "
            f"{', '.join(item['weak_countries']) or '-'} |"
        )
    lines.extend([
        "",
        "This matrix measures comparable concept coverage, not raw chart count. Country-specific deep-dive charts do not fill a Core 48 slot unless the framework mapping is explicit.",
        "",
    ])
    return "\n".join(lines)


def main() -> int:
    payload = build_matrix()
    OUT_JSON.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")
    OUT_MD.write_text(_markdown(payload))
    print(f"Wrote {OUT_JSON}")
    print(f"Wrote {OUT_MD}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
