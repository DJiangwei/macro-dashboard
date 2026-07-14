"""Compact, round-trippable snapshots for the long-form CEE canonical frame."""
from __future__ import annotations

from datetime import UTC, datetime
import json
from pathlib import Path
from typing import Any


OBSERVATION_COLUMNS = ["date", "value", "observation_type", "is_projection"]
METADATA_COLUMNS = [
    "country",
    "indicator_id",
    "concept_id",
    "label",
    "section_id",
    "unit",
    "source",
    "series_id",
    "quality_status",
    "quality_note",
    "is_proxy",
    "frequency",
    "source_url",
    "source_authority",
    "derivation",
    "freshness_status",
    "validation_status",
    "comparability",
    "refresh_fallback",
]


def compact_cee_frames(frames: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    series_payload: list[dict[str, Any]] = []
    for country, frame in sorted(frames.items()):
        grouped: dict[str, list[dict[str, Any]]] = {}
        for row in frame:
            indicator_id = str(row.get("indicator_id") or "")
            if indicator_id:
                grouped.setdefault(indicator_id, []).append(row)
        for indicator_id, rows in sorted(grouped.items()):
            rows.sort(key=lambda row: str(row.get("date") or ""))
            first = rows[0]
            series_payload.append({
                "country": country,
                "indicator_id": indicator_id,
                "metadata": {
                    key: first.get(key)
                    for key in METADATA_COLUMNS
                    if key not in {"country", "indicator_id"} and first.get(key) is not None
                },
                "observations": [
                    [
                        str(row.get("date") or ""),
                        float(row["value"]),
                        row.get("observation_type") or "observed",
                        bool(row.get("is_projection")),
                    ]
                    for row in rows
                ],
            })
    return {
        "schema_version": "cee-canonical-v2",
        "generated": datetime.now(UTC).isoformat(),
        "observation_columns": OBSERVATION_COLUMNS,
        "series": series_payload,
    }


def write_cee_canonical_snapshot(path: Path, frames: dict[str, list[dict[str, Any]]]) -> Path:
    payload = compact_cee_frames(frames)
    path.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n")
    return path


def load_cee_canonical_snapshot(path: Path) -> dict[str, list[dict[str, Any]]]:
    payload = json.loads(path.read_text())
    if payload.get("schema_version") != "cee-canonical-v2":
        raise ValueError(f"Unsupported CEE snapshot: {payload.get('schema_version')}")
    frames: dict[str, list[dict[str, Any]]] = {}
    for item in payload.get("series") or []:
        country = str(item.get("country") or "")
        indicator_id = str(item.get("indicator_id") or "")
        if not country or not indicator_id:
            continue
        metadata = dict(item.get("metadata") or {})
        for observation in item.get("observations") or []:
            if not isinstance(observation, list) or len(observation) < 2:
                continue
            frames.setdefault(country, []).append({
                "country": country,
                "indicator_id": indicator_id,
                **metadata,
                "date": str(observation[0]),
                "value": float(observation[1]),
                "observation_type": observation[2] if len(observation) > 2 else "observed",
                "is_projection": bool(observation[3]) if len(observation) > 3 else False,
            })
    for frame in frames.values():
        frame.sort(key=lambda row: (str(row.get("section_id")), str(row.get("indicator_id")), str(row.get("date"))))
    return frames


def retain_last_known_good_cee_rows(
    live_frame: list[dict[str, Any]],
    prior_frame: list[dict[str, Any]],
    expected_indicator_ids: set[str],
) -> list[dict[str, Any]]:
    """Retain prior CEE history only for expected indicators missing live."""
    live_ids = {str(row.get("indicator_id") or "") for row in live_frame}
    missing = expected_indicator_ids - live_ids
    if not missing:
        return live_frame
    retained: list[dict[str, Any]] = []
    for row in prior_frame:
        if row.get("indicator_id") not in missing:
            continue
        note = str(row.get("quality_note") or "").strip()
        suffix = "Live refresh unavailable; retained prior canonical snapshot."
        retained.append({
            **row,
            "quality_status": "watch",
            "validation_status": "watch",
            "quality_note": f"{note} {suffix}".strip(),
            "refresh_fallback": True,
        })
    return sorted(
        [*live_frame, *retained],
        key=lambda row: (str(row.get("section_id")), str(row.get("indicator_id")), str(row.get("date"))),
    )
