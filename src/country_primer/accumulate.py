"""Stored history for sources that only return a short recent window.

An indicator flagged ``accumulate: true`` merges every successful fetch into
``data/accumulated/<scope>_<id>.json``: dates the source has dropped are kept,
dates it still returns take the fresh value, and a changed value is logged as a
revision. The directory travels on the ``data`` branch (Pages option C), and
``scripts/data_branch.sh push`` refuses to publish a copy that lost dates.
"""
from __future__ import annotations

import json
import os
import tempfile
from datetime import date
from pathlib import Path
from typing import Any

ACCUMULATED_DIR = Path(__file__).resolve().parents[2] / "data" / "accumulated"
SCHEMA_VERSION = "accumulated-v1"


def accumulated_path(scope: str, indicator_id: str, directory: Path | None = None) -> Path:
    return (directory or ACCUMULATED_DIR) / f"{scope.lower()}_{indicator_id}.json"


def merge_observations(
    stored: list[dict[str, Any]], fresh: list[dict[str, Any]], revised_on: str
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Union by date; a date present in both takes the fresh value and is logged if it changed."""
    merged = {str(item["date"]): item["value"] for item in stored}
    revisions = []
    for item in fresh:
        day, value = str(item["date"]), item["value"]
        if day in merged and merged[day] != value:
            revisions.append({"date": day, "previous": merged[day], "value": value, "revised_on": revised_on})
        merged[day] = value
    return [{"date": day, "value": merged[day]} for day in sorted(merged)], revisions


def _load(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        # Overwriting an unreadable file would replace its history with one window.
        raise RuntimeError(f"Accumulated history {path.name} is unreadable; left untouched") from exc
    if not isinstance(payload, dict) or not isinstance(payload.get("observations"), list):
        raise RuntimeError(f"Accumulated history {path.name} has no observation list; left untouched")
    return payload


def _write(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, tmp = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.", suffix=".tmp")
    try:
        with os.fdopen(handle, "w") as stream:
            json.dump(payload, stream, ensure_ascii=False, indent=1)
        os.replace(tmp, path)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise


def accumulate_series(
    series: dict[str, Any], scope: str, today: date | None = None, directory: Path | None = None
) -> dict[str, Any]:
    """Merge a fetched series into its stored history and return the series with the full history."""
    fresh = list(series.get("observations") or [])
    if not fresh:
        return series
    indicator_id = str(series["id"])
    path = accumulated_path(scope, indicator_id, directory)
    stored = _load(path)
    revised_on = (today or date.today()).isoformat()
    merged, revisions = merge_observations(list(stored.get("observations") or []), fresh, revised_on)
    _write(path, {
        "schema_version": SCHEMA_VERSION,
        "scope": scope,
        "indicator_id": indicator_id,
        "source_name": series.get("source_name") or stored.get("source_name") or "",
        "updated": revised_on,
        "observations": merged,
        "revisions": list(stored.get("revisions") or []) + revisions,
    })
    return {**series, "observations": merged, "accumulated_since": merged[0]["date"]}
