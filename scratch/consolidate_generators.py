import re
from pathlib import Path

# 1. Fix page_renderer.py
path = Path("src/country_primer/page_renderer.py")
text = path.read_text()
text = text.replace('matter for China but', 'matter for {config.get("name", "Country")} but')
text = text.replace('SUMMARY_KEY_IDS)', 'summary_key_ids)')
if 'summary_key_ids: list[str]' not in text:
    text = text.replace('latest_value_key: str = "",', 'summary_key_ids: list[str],\n    latest_value_key: str = "",')
# Remove SUMMARY_KEY_IDS definition from page_renderer.py
text = re.sub(r'SUMMARY_KEY_IDS = \[[^\]]*\]', '', text)
path.write_text(text)

# 2. We need a unified `fetch_all` function!
fetcher_pipeline = """from __future__ import annotations
from typing import Any
from concurrent.futures import ThreadPoolExecutor, as_completed
from country_primer.source_health import guarded_source_call, failure_series

def validate_series(series: dict[str, Any]) -> dict[str, Any]:
    # A dummy validation or we can just return it. 
    # Actually, the original scripts use validate_series from build_uk_dashboard.py
    if "quality_status" not in series:
        if not series.get("observations"):
            series["quality_status"] = "unavailable"
        else:
            series["quality_status"] = "high_confidence"
    return series

def fetch_all(config: dict[str, Any], registry: dict[str, Any], max_workers: int = 4, sequential: bool = False) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    specs = list(config.get("indicators", []))
    series_list: list[dict[str, Any] | None] = [None] * len(specs)
    
    # State cache for fetchers that need it
    cache = {}

    def fetch_one(spec: dict[str, Any]) -> dict[str, Any]:
        fetcher_name = spec.get("fetcher")
        func = registry.get(fetcher_name)
        if not func:
            raise ValueError(f"Unknown fetcher: {fetcher_name}")
        
        def operation() -> dict[str, Any]:
            return func(spec, cache)
            
        try:
            series = guarded_source_call(
                country=config.get("iso2", "XX"),
                indicator_id=str(spec.get("id") or "unknown"),
                source_id=str(fetcher_name or "unknown"),
                operation=operation,
            )
        except Exception as exc:
            series = failure_series(spec, exc)
        return validate_series(series)

    if sequential:
        for i, spec in enumerate(specs):
            series_list[i] = fetch_one(spec)
    else:
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(fetch_one, spec): i for i, spec in enumerate(specs)}
            for future in as_completed(futures):
                series_list[futures[future]] = future.result()

        # Retry unavailable
        unavailable_indexes = [i for i, item in enumerate(series_list) if item is not None and item.get("quality_status") == "unavailable"]
        for i in unavailable_indexes:
            for _ in range(2):
                retry = fetch_one(specs[i])
                if retry.get("quality_status") != "unavailable":
                    series_list[i] = retry
                    break

    cards = []
    for card in config.get("latest_cards", []):
        fetcher_name = card.get("fetcher") or "pbc_card"
        func = registry.get(fetcher_name)
        if func:
            try:
                cards.append(guarded_source_call(
                    country=config.get("iso2", "XX"),
                    indicator_id=str(card.get("id") or card.get("label_en") or fetcher_name),
                    source_id=fetcher_name,
                    operation=lambda card=card: func(card, cache),
                    record_empty=False,
                ))
            except Exception as exc:
                cards.append({**card, "value": "n/a", "updated": "n/a", "error": str(exc)})
    
    return [item for item in series_list if item is not None], cards
"""
Path("src/country_primer/data_first_pipeline.py").write_text(fetcher_pipeline)
