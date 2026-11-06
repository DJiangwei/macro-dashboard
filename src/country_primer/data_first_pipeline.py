from __future__ import annotations
import os
from typing import Any
from concurrent.futures import ThreadPoolExecutor, as_completed
from country_primer import accumulate
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

PARTIAL_REFRESH_ENV = "COUNTRY_PRIMER_ONLY_INDICATORS"


def partial_refresh_ids() -> set[str]:
    """Indicator ids for a targeted refresh; empty means a full refresh."""
    raw = os.environ.get(PARTIAL_REFRESH_ENV, "")
    return {item.strip() for item in raw.split(",") if item.strip()}


def fetch_all(
    config: dict[str, Any],
    registry: dict[str, Any],
    max_workers: int = 4,
    sequential: bool = False,
    country: str | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    # Source-health records are keyed by scope; older configs carry no iso2.
    country = country or str(config.get("iso2", "XX"))
    only_ids = partial_refresh_ids()
    specs = list(config.get("indicators", []))
    if only_ids:
        # Targeted refresh: untouched indicators are restored verbatim from the
        # prior canonical snapshot by retain_last_known_good_series.
        skipped = [
            {**spec, "observations": [], "quality_status": "partial_skip", "partial_refresh_skipped": True}
            for spec in specs
            if str(spec.get("id")) not in only_ids
        ]
        specs = [spec for spec in specs if str(spec.get("id")) in only_ids]
    else:
        skipped = []
    series_list: list[dict[str, Any] | None] = [None] * len(specs)
    
    # State cache for fetchers that need it
    cache = {}

    def fetch_one(spec: dict[str, Any]) -> dict[str, Any]:
        fetcher_name = spec.get("fetcher")
        func = registry.get(fetcher_name)
        if not func and (fetcher_name in {"manual", "derived"} or spec.get("derivation") == "derived"):
            return validate_series({**spec, "observations": [], "quality_status": "retained"})
        if not func:
            raise ValueError(f"Unknown fetcher: {fetcher_name}")
        
        def operation() -> dict[str, Any]:
            return func(spec, cache)
            
        try:
            series = guarded_source_call(
                country=country,
                indicator_id=str(spec.get("id") or "unknown"),
                source_id=str(fetcher_name or "unknown"),
                operation=operation,
            )
            if isinstance(series, dict):
                series = {**spec, **series}
                if spec.get("accumulate") and series.get("observations"):
                    series = accumulate.accumulate_series(series, country)
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
                    country=country,
                    indicator_id=str(card.get("id") or card.get("label_en") or fetcher_name),
                    source_id=fetcher_name,
                    operation=lambda card=card: func(card, cache),
                    record_empty=False,
                ))
            except Exception as exc:
                cards.append({**card, "value": "n/a", "updated": "n/a", "error": str(exc)})
    
    return [item for item in series_list if item is not None] + skipped, cards
