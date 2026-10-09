import re
from pathlib import Path

# We will read from build_china_dashboard.py and extract the UI parts
china_code = Path("scripts/build_china_dashboard.py").read_text()

# We need everything from CSS definition down to inject_index
match = re.search(r'(CSS = """.*?)\ndef build\(', china_code, re.DOTALL)
if not match:
    print("Could not find CSS block")
    exit(1)

extracted = match.group(1)

# Now we construct page_renderer.py
renderer = f"""from __future__ import annotations
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

{extracted}

def build_country_page(
    country_code: str,
    config: dict[str, Any],
    series_list: list[dict[str, Any]],
    out_html: Path,
    summary_json: Path,
    canonical_json: Path,
    data_mode: str,
    summary_key_ids: list[str],
    extra_cards: list[dict[str, Any]] | None = None,
    index_kicker: str = "",
    index_framework: str = "",
    latest_value_key: str = "",
    latest_value_display: str = ""
) -> Path:
    apply_quality_assessments(series_list)
    html = render_html(config, series_list, extra_cards or [])
    _write_clean(out_html, html)

    charted = [item for item in series_list if item.get("observations")]
    summary = {{
        "file": out_html.name,
        "generated": datetime.now(UTC).isoformat(),
        "charts": len(charted),
        "source_groups": len({{item.get("source_name") for item in charted}}),
        "data_gaps": len(config.get("data_gaps", [])),
        "low_confidence": sum(1 for item in charted if item.get("quality_status") == "low_confidence"),
        "key_series_latest": _key_series_latest(charted, summary_key_ids),
        "unavailable": [item["id"] for item in series_list if not item.get("observations")],
        "data_mode": data_mode,
        "latest_cards": extra_cards or [],
    }}
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
        
    # We will let the caller handle inject_index if needed, or we adapt inject_index here.
    return out_html
"""

Path("src/country_primer/page_renderer.py").write_text(renderer)
print("Created page_renderer.py")
