import re

with open("scripts/dashboard_summary_utils.py", "r") as f:
    content = f.read()

# 1. Update canonical_data_first_series to output the new fields
output_block = """            "refresh_fallback": bool(item.get("refresh_fallback")),
            "fetch_timestamp": _clean(item.get("fetch_timestamp")),
            "has_revisions": bool(item.get("has_revisions")),
            "prior_vintage": item.get("prior_vintage"),"""
content = re.sub(
    r'"refresh_fallback": bool\(item\.get\("refresh_fallback"\)\),',
    output_block,
    content,
    count=1
)

# 2. Update load_canonical_data_first_frame to restore the new fields
restore_block = """            "refresh_fallback": bool(item.get("refresh_fallback")),
            "fetch_timestamp": _clean(item.get("fetch_timestamp")),
            "has_revisions": bool(item.get("has_revisions")),
            "prior_vintage": item.get("prior_vintage"),"""
content = re.sub(
    r'"refresh_fallback": bool\(item\.get\("refresh_fallback"\)\),',
    restore_block,
    content,
    count=1
)

# 3. Add track_revisions_and_vintages function
new_func = """
def track_revisions_and_vintages(
    series_list: list[dict[str, Any]],
    canonical_path: Any,
    config: dict[str, Any],
) -> list[dict[str, Any]]:
    \"\"\"Track release vintages, fetch timestamps, and flag high-value revisions.\"\"\"
    from pathlib import Path
    from datetime import datetime, UTC

    now_iso = datetime.now(UTC).isoformat()
    path = Path(canonical_path)
    if not path.exists():
        for item in series_list:
            item["fetch_timestamp"] = now_iso
        return series_list

    previous_frame = load_canonical_data_first_frame(path, config)
    previous_by_id = {
        item["id"]: item for item in previous_frame if item.get("observations")
    }

    # High-value concepts where revisions are tracked
    HIGH_VALUE_PILLARS = {"growth_demand", "labour_wages", "prices_costs", "fiscal_sovereign", "external_fx"}

    for item in series_list:
        item["fetch_timestamp"] = now_iso
        indicator_id = item.get("id")
        if not indicator_id or indicator_id not in previous_by_id:
            continue
        
        prior = previous_by_id[indicator_id]
        
        # If this was a refresh fallback, don't treat it as a new vintage
        if item.get("refresh_fallback"):
            item["fetch_timestamp"] = prior.get("fetch_timestamp") or now_iso
            item["prior_vintage"] = prior.get("prior_vintage")
            item["has_revisions"] = prior.get("has_revisions", False)
            continue

        current_obs = {obs["date"]: obs["value"] for obs in (item.get("observations") or [])}
        prior_obs = {obs["date"]: obs["value"] for obs in (prior.get("observations") or [])}
        
        is_new_vintage = False
        has_revisions = False
        
        if item.get("provider_updated") and prior.get("provider_updated"):
            if item["provider_updated"] != prior["provider_updated"]:
                is_new_vintage = True
        elif len(current_obs) != len(prior_obs) or set(current_obs.keys()) != set(prior_obs.keys()):
            is_new_vintage = True

        for date, val in current_obs.items():
            if date in prior_obs:
                if abs(val - prior_obs[date]) > 1e-6:
                    has_revisions = True
                    break

        section = item.get("section") or prior.get("section")
        
        # We also need to map section to pillar if possible, or just use broad checks.
        # Framework v2 uses section_id in config which maps to pillars in framework_v2.yaml
        # For simplicity, if section matches the substring of high value pillars...
        is_high_value = any(term in (section or "") for term in ("growth", "labour", "price", "fiscal", "external"))
        
        if is_new_vintage and is_high_value:
            # Retain prior vintage
            item["prior_vintage"] = {
                "provider_updated": prior.get("provider_updated"),
                "fetch_timestamp": prior.get("fetch_timestamp"),
                "observations": [[d, v] for d, v in sorted(prior_obs.items())]
            }
            if has_revisions:
                item["has_revisions"] = True
                _append_quality_note(item, f"Revisions detected vs prior vintage ({prior.get('provider_updated') or 'unknown'})")
        else:
            # Propagate existing prior vintage
            item["prior_vintage"] = prior.get("prior_vintage")
            item["has_revisions"] = prior.get("has_revisions", False)

    return series_list

def _append_quality_note(item: dict[str, Any], note: str) -> None:
    notes = item.get("quality_notes") or []
    if note not in notes:
        notes.append(note)
    item["quality_notes"] = notes

"""

content = content + new_func

with open("scripts/dashboard_summary_utils.py", "w") as f:
    f.write(content)
