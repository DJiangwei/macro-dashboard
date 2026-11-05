#!/usr/bin/env python3
"""Cross-series derivations over the data-first canonical frames.

Only *derivations from series already in a canonical frame* belong here. This
script never writes observations that were not computed from fetched data,
never edits configuration, and never overrides a quality assessment.

History: an earlier version of this file injected hand-typed observations
(KZ/NG policy rates, HK reserves, China "September/October 2026" prints, TR/HK
10Y yields, ECB CISS, BIS credit gaps, S&P 500/Euro Stoxx returns) and appended
coverage mappings to config/framework_v2.yaml at build time. All of that was
removed on 2026-11-05; the affected series now come from real fetchers or are
documented as gaps.

Derivations:
1. Real policy rate (monthly, ex post): policy rate in force at the end of each
   CPI month minus that month's headline CPI YoY. Months after the policy
   series' last observation are not filled.
2. Sovereign term-structure slopes for South Korea (10Y-3Y) and Taiwan (10Y-5Y),
   computed only on dates where both legs are observed.
"""
from __future__ import annotations

import calendar
import json
import sys
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "output"
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from country_primer.data_quality import assess_series_quality  # noqa: E402
from country_primer.scopes import data_first_scopes  # noqa: E402

# Section of the derived real-rate chart; scopes not listed use monetary_financial.
REAL_RATE_SECTION = {"CN": "money_credit"}

# (scope, canonical frame, policy-rate candidates, CPI YoY candidates, section),
# from the roles in config/scopes.yaml. The market rate is used where a scope
# declares one (US: EFFR rather than the target range).
REAL_RATE_INPUTS: list[tuple[str, str, list[str], list[str], str]] = [
    (
        scope.id,
        scope.canonical_file,
        list(scope.market_policy_rate),
        list(scope.role("cpi_yoy")),
        REAL_RATE_SECTION.get(scope.id, "monetary_financial"),
    )
    for scope in data_first_scopes()
]


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())


def _write(path: Path, payload: dict[str, Any]) -> None:
    payload["generated"] = datetime.now(UTC).isoformat()
    path.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n")


def _series_map(payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {s["indicator_id"]: s for s in payload.get("series", [])}


def _pick(series_map: dict[str, dict[str, Any]], candidates: list[str]) -> dict[str, Any] | None:
    for candidate in candidates:
        item = series_map.get(candidate)
        if item and item.get("observations"):
            return item
    return None


def _derived_entry(
    *,
    indicator_id: str,
    concept_id: str,
    section: str,
    label_en: str,
    label_zh: str,
    unit: str,
    frequency: str,
    inputs: list[dict[str, Any]],
    formula: str,
    observations: list[list[Any]],
) -> dict[str, Any]:
    primary = inputs[0]
    source = dict(primary.get("source") or {})
    input_ids = [item["indicator_id"] for item in inputs]
    note = f"Derived: {formula}. Inputs: {', '.join(input_ids)}."
    assessable = {
        "id": indicator_id,
        "frequency": frequency,
        "source_name": source.get("name", ""),
        "source_url": source.get("url", ""),
        "derivation": "derived",
        "observations": [{"date": d, "value": v} for d, v in observations],
        "quality_notes": [note],
    }
    quality = assess_series_quality(assessable)
    # A derivation is never more trustworthy than its weakest input.
    order = {"verified": 0, "watch": 1, "low_confidence": 2, "unavailable": 3}
    worst_input = max(
        (str((item.get("quality") or {}).get("status") or "watch") for item in inputs),
        key=lambda status: order.get(status, 1),
    )
    if order.get(worst_input, 1) > order.get(quality["status"], 1):
        quality["status"] = worst_input
    latest = observations[-1][0] if observations else ""
    return {
        "indicator_id": indicator_id,
        "concept_id": concept_id,
        "section": section,
        "label_en": label_en,
        "label_zh": label_zh,
        "unit": unit,
        "frequency": frequency,
        "transform": "level",
        "source": {"name": f"{source.get('name', '')} / Derived".strip(" /"), "series": formula, "url": source.get("url", "")},
        "quality": quality,
        "quality_notes": [note],
        "actual_through": latest,
        "provider_updated": latest,
        "refresh_fallback": False,
        "fetch_timestamp": datetime.now(UTC).isoformat(),
        "has_revisions": False,
        "prior_vintage": None,
        "observations": observations,
    }


def _month_end(year: int, month: int) -> str:
    return f"{year:04d}-{month:02d}-{calendar.monthrange(year, month)[1]:02d}"


def real_policy_rate_observations(
    policy_obs: list[list[Any]],
    cpi_obs: list[list[Any]],
) -> list[list[Any]]:
    """Monthly ex-post real rate without filling beyond the policy series."""
    policy = sorted((str(d)[:10], float(v)) for d, v in policy_obs)
    if not policy:
        return []
    first_policy, last_policy = policy[0][0], policy[-1][0]
    out: list[list[Any]] = []
    for raw_date, raw_value in sorted(cpi_obs):
        cpi_date = str(raw_date)[:10]
        year, month = int(cpi_date[:4]), int(cpi_date[5:7])
        month_start = f"{year:04d}-{month:02d}-01"
        month_end = _month_end(year, month)
        if month_end < first_policy or month_start > last_policy:
            continue
        in_force = [value for d, value in policy if d <= month_end]
        if not in_force:
            continue
        out.append([month_start, round(in_force[-1] - float(raw_value), 2)])
    return out


def enrich_all_real_policy_rates() -> None:
    print("--- Real policy rates (policy rate in force at month end minus CPI YoY) ---")
    for scope, frame_name, policy_ids, cpi_ids, section in REAL_RATE_INPUTS:
        path = OUTPUT / frame_name
        if not path.exists():
            continue
        payload = _load(path)
        series_map = _series_map(payload)
        policy = _pick(series_map, policy_ids)
        cpi = _pick(series_map, cpi_ids)
        if not policy or not cpi:
            print(f"{scope}: skipped (policy={bool(policy)}, cpi={bool(cpi)})")
            series_map.pop("real_policy_rate", None)
            payload["series"] = [series_map[k] for k in sorted(series_map)]
            _write(path, payload)
            continue
        observations = real_policy_rate_observations(policy["observations"], cpi["observations"])
        if not observations:
            print(f"{scope}: no overlapping months")
            continue
        series_map["real_policy_rate"] = _derived_entry(
            indicator_id="real_policy_rate",
            concept_id="real_policy_rate",
            section=section,
            label_en=f"{scope} Real Policy Rate (Policy Rate − CPI YoY)",
            label_zh=f"{scope} 实际政策利率 (政策利率 − CPI同比)",
            unit="%",
            frequency="monthly",
            inputs=[policy, cpi],
            formula=f"{policy['indicator_id']} in force at month end − {cpi['indicator_id']}",
            observations=observations,
        )
        payload["series"] = [series_map[k] for k in sorted(series_map)]
        _write(path, payload)
        print(f"{scope}: {len(observations)} months, latest {observations[-1]}")


def _slope(
    frame_name: str,
    long_id: str,
    short_id: str,
    indicator_id: str,
    label_en: str,
    label_zh: str,
) -> None:
    path = OUTPUT / frame_name
    if not path.exists():
        return
    payload = _load(path)
    series_map = _series_map(payload)
    long_leg, short_leg = series_map.get(long_id), series_map.get(short_id)
    if not long_leg or not short_leg:
        print(f"{frame_name}: slope skipped (missing {long_id} or {short_id})")
        return
    short_by_date = {str(d)[:10]: float(v) for d, v in short_leg.get("observations", [])}
    observations = [
        [str(d)[:10], round((float(v) - short_by_date[str(d)[:10]]) * 100, 1)]
        for d, v in long_leg.get("observations", [])
        if str(d)[:10] in short_by_date
    ]
    if not observations:
        return
    series_map[indicator_id] = _derived_entry(
        indicator_id=indicator_id,
        concept_id="yield_curve_slope",
        section=str(long_leg.get("section") or "monetary_financial"),
        label_en=label_en,
        label_zh=label_zh,
        unit="bps",
        # Legs on different calendars (e.g. TW bimonthly 10Y vs 5Y auction dates)
        # only coincide occasionally, so the slope is honestly irregular.
        frequency=(
            str(long_leg.get("frequency") or "monthly")
            if long_leg.get("frequency") == short_leg.get("frequency")
            else "irregular"
        ),
        inputs=[long_leg, short_leg],
        formula=f"({long_id} − {short_id}) × 100 on dates where both are observed",
        observations=observations,
    )
    payload["series"] = [series_map[k] for k in sorted(series_map)]
    _write(path, payload)
    print(f"{frame_name}: {indicator_id} {len(observations)} obs")


def enrich_yield_curve_slopes() -> None:
    print("--- Sovereign term-structure slopes ---")
    _slope(
        "south_korea_canonical_frame.json", "sovereign_yield_10y", "ktb_3y_yield",
        "yield_curve_slope_10y3y", "South Korea KTB 10Y-3Y Slope", "韩国国债 10Y-3Y 期限利差",
    )
    _slope(
        "taiwan_canonical_frame.json", "sovereign_yield_10y", "sovereign_yield_5y",
        "yield_curve_slope_10y5y", "Taiwan Government Bond 10Y-5Y Slope", "台湾公债 10Y-5Y 期限利差",
    )


def main() -> None:
    enrich_all_real_policy_rates()
    enrich_yield_curve_slopes()


if __name__ == "__main__":
    main()
