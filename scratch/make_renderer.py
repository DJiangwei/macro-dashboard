import re
from pathlib import Path

imports = """from __future__ import annotations
import json
import os
import re
from datetime import datetime, UTC
from html import escape
from pathlib import Path
from typing import Any

from dashboard_summary_utils import (
    apply_quality_assessments,
    build_summary_metadata,
    canonical_frame_metadata,
    write_canonical_data_first_frame,
)
from country_primer.source_health import write_source_health_report

"""

body = Path("scratch/extracted_ui.py").read_text()

# We need to adapt the generic inject_index and build_country_page
footer = """
def _key_series_latest(series_list: list[dict[str, Any]], indicator_ids: list[str]) -> list[dict[str, Any]]:
    by_id = {item["id"]: item for item in series_list}
    rows: list[dict[str, Any]] = []
    for indicator_id in indicator_ids:
        series = by_id.get(indicator_id)
        latest = _latest(series) if series else None
        if not series or not latest:
            continue
        unit = str(series.get("unit", ""))
        value = float(latest["value"])
        rows.append({
            "id": indicator_id,
            "label_en": series.get("label_en", indicator_id),
            "label_zh": series.get("label_zh", indicator_id),
            "latest_date": str(latest["date"]),
            "latest_value": value,
            "latest_display": f"{_format_value(value, unit)} {unit}".strip(),
            "frequency": series.get("frequency", ""),
            "source_name": series.get("source_name", ""),
            "series": series.get("series", ""),
            "quality_status": series.get("quality_status", ""),
        })
    return rows

def build_country_page(
    country_code: str,
    config: dict[str, Any],
    series_list: list[dict[str, Any]],
    out_html: Path,
    summary_json: Path,
    canonical_json: Path,
    data_mode: str,
    extra_cards: list[dict[str, Any]] | None = None,
    latest_value_key: str = "",
    latest_value_display: str = ""
) -> Path:
    apply_quality_assessments(series_list)
    html = render_html(config, series_list, extra_cards or [])
    _write_clean(out_html, html)

    charted = [item for item in series_list if item.get("observations")]
    summary = {
        "file": out_html.name,
        "generated": datetime.now(UTC).isoformat(),
        "charts": len(charted),
        "source_groups": len({item.get("source_name") for item in charted}),
        "data_gaps": len(config.get("data_gaps", [])),
        "low_confidence": sum(1 for item in charted if item.get("quality_status") == "low_confidence"),
        "key_series_latest": _key_series_latest(charted, SUMMARY_KEY_IDS),
        "unavailable": [item["id"] for item in series_list if not item.get("observations")],
        "data_mode": data_mode,
        "latest_cards": extra_cards or [],
    }
    if latest_value_key and latest_value_display:
        summary[latest_value_key] = latest_value_display
        
    summary["canonical_frame"] = (
        canonical_frame_metadata(canonical_json)
        if data_mode == "snapshot"
        else write_canonical_data_first_frame(canonical_json, country_code, series_list)
    )
    summary.update(build_summary_metadata(config, series_list, country_code))
    summary_json.write_text(json.dumps(summary, indent=2, ensure_ascii=False))
    
    if data_mode != "snapshot":
        write_source_health_report(out_html.parent / "source_health.json", [country_code])
        
    return out_html
"""

Path("src/country_primer/page_renderer.py").write_text(imports + body + footer)
