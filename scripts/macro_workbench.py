"""Build macro workbench metadata for the dashboard archive.

This module turns generated country summaries into a portfolio-manager style
control plane: regime scores, data-quality heatmaps, release-monitor queues,
gap backlog, and what-changed deltas versus the previous build.
"""
from __future__ import annotations

import json
import math
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "output"
WORKBENCH_JSON = OUTPUT / "macro_workbench_summary.json"
RELEASE_MONITOR_JSON = OUTPUT / "release_monitor.json"
WHAT_CHANGED_JSON = OUTPUT / "what_changed.json"
DATA_GAP_BACKLOG_JSON = OUTPUT / "data_gap_backlog.json"
FRESHNESS_JSON = OUTPUT / "freshness_audit.json"

DASHBOARD_TO_CODE = {
    "Hungary": "HU",
    "Poland": "PL",
    "Czechia": "CZ",
    "Romania": "RO",
    "China": "CN",
    "Japan": "JP",
    "South Africa": "ZA",
    "United Kingdom": "UK",
    "United States": "US",
}
CODE_TO_DASHBOARD = {code: name for name, code in DASHBOARD_TO_CODE.items()}

DATA_FIRST_SUMMARIES = {
    "CN": "china_dashboard_summary.json",
    "JP": "japan_dashboard_summary.json",
    "ZA": "south_africa_dashboard_summary.json",
    "UK": "uk_dashboard_summary.json",
    "US": "us_dashboard_summary.json",
}

DATA_FIRST_SIGNAL_MAP = {
    "CN": {
        "growth": ("industrial_value_added_yoy_akshare", "Industrial production"),
        "inflation": ("cpi_yoy_akshare", "CPI inflation"),
        "policy": ("m2_yoy_akshare", "Broad-money impulse"),
        "external": ("customs_exports_yoy_akshare", "Exports"),
        "property": ("real_estate_development_investment_ytd_eastmoney", "Property investment"),
    },
    "JP": {
        "growth": ("real_gdp_yoy", "Real GDP"),
        "inflation": ("cpi_inflation", "Headline CPI"),
        "policy": ("policy_rate", "Overnight call rate"),
        "external": ("goods_trade_balance", "Goods trade balance"),
        "fiscal": ("government_debt_gdp", "Government debt/GDP"),
        "financial": ("sovereign_yield_10y", "10Y JGB"),
        "property": ("house_price_growth", "House prices"),
    },
    "ZA": {
        "growth": ("real_gdp_yoy", "Real GDP"),
        "inflation": ("cpi_inflation", "Headline CPI"),
        "policy": ("policy_rate", "SARB repo rate"),
        "external": ("goods_trade_balance", "Goods trade balance"),
        "fiscal": ("government_debt_gdp", "Government debt/GDP"),
        "financial": ("prime_lending_rate", "Prime lending rate"),
        "property": ("house_price_growth", "House prices"),
    },
    "UK": {
        "growth": ("monthly_gdp_mom", "Monthly GDP"),
        "inflation": ("cpi_yoy", "CPI inflation"),
        "policy": ("bank_rate", "Bank Rate"),
        "fiscal": ("psnb_ex_banks", "PSNB"),
        "financial": ("sonia_rate", "SONIA"),
    },
    "US": {
        "growth": ("real_gdp_growth", "Real GDP"),
        "inflation": ("core_cpi_inflation", "Core CPI"),
        "policy": ("daily_fed_funds", "Fed funds"),
        "fiscal": ("federal_debt_gdp", "Federal debt/GDP"),
        "financial": ("mortgage_30y_rate", "Mortgage rate"),
        "property": ("housing_starts", "Housing starts"),
    },
}


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text())
    except json.JSONDecodeError:
        return {}


def _clean(value: object) -> str:
    return " ".join(str(value or "").replace("\xa0", " ").split())


def _number(value: object) -> float | None:
    if value is None:
        return None
    if isinstance(value, (int, float)) and math.isfinite(float(value)):
        return float(value)
    text = _clean(value)
    match = re.search(r"[-+]?\d+(?:,\d{3})*(?:\.\d+)?", text)
    if not match:
        return None
    try:
        return float(match.group(0).replace(",", ""))
    except ValueError:
        return None


def _score(value: float, *, lower: float = 0.0, upper: float = 100.0) -> float:
    return max(lower, min(upper, value))


def _freshness_by_code() -> dict[str, dict[str, Any]]:
    payload = _read_json(FRESHNESS_JSON)
    output: dict[str, dict[str, Any]] = {}
    for row in payload.get("summary", []) or []:
        code = DASHBOARD_TO_CODE.get(str(row.get("dashboard") or ""))
        if code:
            output[code] = row
    return output


def _key_series(summary: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        str(item.get("id")): item
        for item in summary.get("key_series_latest", []) or []
        if item.get("id")
    }


def _data_first_signals(code: str, summary: dict[str, Any]) -> dict[str, dict[str, Any]]:
    key_series = _key_series(summary)
    signals: dict[str, dict[str, Any]] = {}
    for dimension, (series_id, label) in DATA_FIRST_SIGNAL_MAP.get(code, {}).items():
        item = key_series.get(series_id)
        if not item:
            continue
        signals[dimension] = {
            "id": series_id,
            "label": label,
            "value": item.get("latest_value"),
            "display": item.get("latest_display"),
            "date": item.get("latest_date"),
            "source": item.get("source_name"),
            "quality_status": item.get("quality_status"),
        }
    return signals


def enrich_cards(cards: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Attach data-first signals and summary health to archive cards."""
    enriched: list[dict[str, Any]] = []
    freshness = _freshness_by_code()
    for card in cards:
        item = dict(card)
        code = str(item.get("code") or "")
        summary = _read_json(OUTPUT / DATA_FIRST_SUMMARIES[code]) if code in DATA_FIRST_SUMMARIES else {}
        if summary:
            item["signals"] = _data_first_signals(code, summary)
            item["source_health"] = summary.get("source_health", {})
            item["freshness"] = summary.get("freshness", {})
            item["canonical_frame"] = summary.get("canonical_frame", {})
        item["freshness_summary"] = freshness.get(code, {})
        enriched.append(item)
    return enriched


def _regime_label(dimension: str, value: float | None) -> tuple[str, float]:
    if value is None:
        return "insufficient data", 50.0
    if dimension == "growth":
        if value >= 3:
            return "above-trend expansion", 80.0
        if value >= 1:
            return "moderate expansion", 65.0
        if value >= 0:
            return "stall-speed growth", 45.0
        return "contraction", 25.0
    if dimension == "inflation":
        if value >= 5:
            return "inflation pressure", 25.0
        if value >= 3:
            return "above-target inflation", 45.0
        if value >= 1:
            return "near-target inflation", 70.0
        return "disinflation risk", 55.0
    if dimension == "policy":
        if value >= 5:
            return "restrictive stance", 35.0
        if value >= 3:
            return "neutral-tight stance", 55.0
        return "easy stance", 65.0
    if dimension == "external":
        if value >= 3:
            return "external strength", 75.0
        if value <= -3:
            return "external drag", 35.0
        return "balanced external impulse", 60.0
    if dimension == "fiscal":
        if value <= -6:
            return "fiscal stress", 30.0
        if value <= -3:
            return "watch fiscal slippage", 45.0
        return "fiscal contained", 65.0
    if dimension == "financial":
        if value >= 8:
            return "tight financial conditions", 35.0
        if value <= -5:
            return "credit deleveraging", 40.0
        return "financial conditions stable", 60.0
    if dimension == "property":
        if value >= 5:
            return "property hot", 65.0
        if value < 0:
            return "property drag", 35.0
        return "property stable", 58.0
    return "tracked", 50.0


def _country_quality_score(card: dict[str, Any]) -> dict[str, Any]:
    charts = float(card.get("charts") or 0)
    expected = float(card.get("expected") or charts or 1)
    coverage = _score(charts / expected * 100.0 if expected else 0.0)
    proxy_penalty = min(float(card.get("proxy_fills") or 0) * 20.0, 60.0)
    gap_penalty = min(float(card.get("gaps_or_dropped") or 0) * 2.5, 30.0)
    freshness = card.get("freshness_summary") or {}
    current = float(freshness.get("current") or 0)
    freshness_charts = float(freshness.get("charts") or charts or 1)
    freshness_score = _score(current / freshness_charts * 100.0 if freshness_charts else 0.0)
    low_confidence = float(freshness.get("low_confidence") or 0)
    low_penalty = min(low_confidence * 2.0, 20.0)
    score = _score(coverage * 0.35 + freshness_score * 0.35 + 30.0 - proxy_penalty - gap_penalty - low_penalty)
    if score >= 80:
        label = "high-confidence dashboard"
    elif score >= 60:
        label = "usable with watch-list"
    else:
        label = "needs data review"
    return {
        "score": round(score, 1),
        "label": label,
        "coverage_score": round(coverage, 1),
        "freshness_score": round(freshness_score, 1),
        "proxy_penalty": round(proxy_penalty, 1),
        "gap_penalty": round(gap_penalty, 1),
    }


def _regime_for_card(card: dict[str, Any]) -> dict[str, Any]:
    signals = card.get("signals") or {}
    dimensions: dict[str, dict[str, Any]] = {}
    dimension_scores: list[float] = []
    for dimension in ("growth", "inflation", "policy", "external", "fiscal", "financial", "property"):
        signal = signals.get(dimension, {})
        value = _number(signal.get("value") if signal else None)
        label, score = _regime_label(dimension, value)
        dimensions[dimension] = {
            "label": label,
            "score": round(score, 1),
            "value": value,
            "display": signal.get("display") or (f"{value:.2f}" if value is not None else "n/a"),
            "source_signal": signal.get("id", ""),
        }
        if value is not None:
            dimension_scores.append(score)
    quality = _country_quality_score(card)
    base_score = sum(dimension_scores) / len(dimension_scores) if dimension_scores else 50.0
    composite = _score(base_score * 0.65 + quality["score"] * 0.35)
    if composite >= 70:
        composite_label = "constructive"
    elif composite >= 50:
        composite_label = "mixed"
    else:
        composite_label = "defensive"
    return {
        "composite_score": round(composite, 1),
        "composite_label": composite_label,
        "quality": quality,
        "dimensions": dimensions,
    }


def _heatmap(cards: list[dict[str, Any]], regimes: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for card in cards:
        code = str(card.get("code"))
        freshness = card.get("freshness_summary") or {}
        charts = float(card.get("charts") or 0)
        expected = float(card.get("expected") or charts or 1)
        current = float(freshness.get("current") or 0)
        freshness_charts = float(freshness.get("charts") or charts or 1)
        rows.append({
            "code": code,
            "name": card.get("name"),
            "coverage_pct": round(charts / expected * 100.0 if expected else 0.0, 1),
            "freshness_pct": round(current / freshness_charts * 100.0 if freshness_charts else 0.0, 1),
            "proxy_fills": int(card.get("proxy_fills") or 0),
            "gaps": int(card.get("gaps_or_dropped") or 0),
            "regime_score": regimes.get(code, {}).get("composite_score"),
            "quality_score": regimes.get(code, {}).get("quality", {}).get("score"),
        })
    return rows


def _release_monitor() -> list[dict[str, Any]]:
    payload = _read_json(FRESHNESS_JSON)
    output: list[dict[str, Any]] = []
    for item in payload.get("attention", []) or []:
        code = DASHBOARD_TO_CODE.get(str(item.get("dashboard") or ""))
        if not code:
            continue
        status = str(item.get("freshness_status") or "")
        age = item.get("age_days")
        severity = "high" if status in {"stale", "needs_review"} and (age or 0) > 330 else "medium"
        if status in {"missing_date", "future_date"}:
            severity = "high"
        output.append({
            "code": code,
            "dashboard": item.get("dashboard"),
            "indicator_id": item.get("indicator_id"),
            "label": item.get("label"),
            "latest": item.get("latest_observation"),
            "frequency": item.get("frequency"),
            "status": status,
            "age_days": age,
            "severity": severity,
            "source": item.get("source"),
            "note": item.get("note"),
        })
    return output[:80]


def _gap_priority(text: str) -> tuple[str, str]:
    haystack = text.lower()
    if any(token in haystack for token in ("pmi", "credit conditions", "housing", "real estate", "nbs", "fomc", "tic")):
        priority = "high"
    elif any(token in haystack for token in ("survey", "expectations", "fiscal", "debt", "safe", "pbc")):
        priority = "medium"
    else:
        priority = "watch"
    if "china" in haystack or "nbs" in haystack or "pbc" in haystack:
        source_hint = "Prefer native official APIs or AKShare-wrapped structured endpoints; avoid manual proxy fills."
    elif "uk" in haystack or "ons" in haystack or "boe" in haystack:
        source_hint = "Prefer ONS, BoE IADB, HMRC/GOV.UK, OBR, or DESNZ endpoints before mirrors."
    elif "ism" in haystack or "fomc" in haystack or "treasury" in haystack or "tic" in haystack:
        source_hint = "Prefer FRED, Federal Reserve, BLS/Census/BEA, FiscalData, or Treasury source APIs."
    elif "pmi" in haystack or "survey" in haystack:
        source_hint = "Check licensing before rendering; vendor surveys should stay as official gaps unless source-safe."
    else:
        source_hint = "Wire only a reproducible source with definition and freshness validation."
    return priority, source_hint


def _gap_backlog(cards: list[dict[str, Any]]) -> list[dict[str, Any]]:
    backlog: list[dict[str, Any]] = []
    for card in cards:
        code = str(card.get("code"))
        if code in DATA_FIRST_SUMMARIES:
            summary = _read_json(OUTPUT / DATA_FIRST_SUMMARIES[code])
            for gap in summary.get("data_gaps_detail", []) or []:
                text = " ".join([gap.get("section", ""), gap.get("item_en", ""), gap.get("status_en", "")])
                priority, source_hint = _gap_priority(f"{code} {text}")
                backlog.append({
                    "code": code,
                    "country": card.get("name"),
                    "section": gap.get("section"),
                    "item": gap.get("item_en"),
                    "status": gap.get("status_en"),
                    "priority": priority,
                    "source_hint": source_hint,
                })
        else:
            dropped = int(card.get("gaps_or_dropped") or 0)
            if dropped:
                backlog.append({
                    "code": code,
                    "country": card.get("name"),
                    "section": "dropped_proxy_slots",
                    "item": f"{dropped} dropped proxy-only slots",
                    "status": "Restore only with reusable public or licensed non-proxy sources.",
                    "priority": "watch",
                    "source_hint": "Review PROXY_REVIEW.md and DATA_SOURCE_CATALOG.md before restoring.",
                })
    priority_order = {"high": 0, "medium": 1, "watch": 2}
    backlog.sort(key=lambda item: (priority_order.get(str(item["priority"]), 9), str(item["code"]), str(item["section"])))
    return backlog


def _what_changed(previous: dict[str, Any], current_cards: list[dict[str, Any]], regimes: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    if not previous:
        return [{
            "scope": "workbench",
            "change": "initial_snapshot",
            "detail": "No previous macro_workbench_summary.json was available for comparison.",
        }]
    previous_cards = {card.get("code"): card for card in previous.get("cards", []) or []}
    previous_regimes = previous.get("regimes", {}) or {}
    changes: list[dict[str, Any]] = []
    for card in current_cards:
        code = card.get("code")
        old = previous_cards.get(code, {})
        for field in ("charts", "proxy_fills", "gaps_or_dropped", "headline"):
            if old and old.get(field) != card.get(field):
                changes.append({
                    "scope": code,
                    "change": field,
                    "from": old.get(field),
                    "to": card.get(field),
                })
        old_score = (previous_regimes.get(code) or {}).get("composite_score")
        new_score = regimes.get(code, {}).get("composite_score")
        if old_score is not None and new_score is not None and abs(float(new_score) - float(old_score)) >= 3:
            changes.append({
                "scope": code,
                "change": "regime_score",
                "from": old_score,
                "to": new_score,
            })
    return changes[:80] or [{
        "scope": "workbench",
        "change": "no_material_change",
        "detail": "Coverage, proxy, headline, and regime metrics are unchanged versus the previous workbench build.",
    }]


def _degradation_alerts(previous: dict[str, Any], current_cards: list[dict[str, Any]], heatmap: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not previous:
        return []
    previous_cards = {card.get("code"): card for card in previous.get("cards", []) or []}
    previous_heatmap = {row.get("code"): row for row in previous.get("heatmap", []) or []}
    current_heatmap = {row.get("code"): row for row in heatmap}
    alerts: list[dict[str, Any]] = []
    for card in current_cards:
        code = card.get("code")
        old = previous_cards.get(code, {})
        if not old:
            continue
        if int(card.get("charts") or 0) < int(old.get("charts") or 0):
            alerts.append({
                "code": code,
                "severity": "high",
                "metric": "charts",
                "from": old.get("charts"),
                "to": card.get("charts"),
                "message": "Rendered chart count declined versus previous workbench build.",
            })
        if int(card.get("proxy_fills") or 0) > int(old.get("proxy_fills") or 0):
            alerts.append({
                "code": code,
                "severity": "high",
                "metric": "proxy_fills",
                "from": old.get("proxy_fills"),
                "to": card.get("proxy_fills"),
                "message": "Proxy fills increased versus previous workbench build.",
            })
        old_freshness = _number((previous_heatmap.get(code) or {}).get("freshness_pct"))
        new_freshness = _number((current_heatmap.get(code) or {}).get("freshness_pct"))
        if old_freshness is not None and new_freshness is not None and new_freshness < old_freshness - 10:
            alerts.append({
                "code": code,
                "severity": "medium",
                "metric": "freshness_pct",
                "from": old_freshness,
                "to": new_freshness,
                "message": "Freshness share fell by more than 10 percentage points.",
            })
    return alerts


def build_workbench(cards: list[dict[str, Any]]) -> dict[str, Any]:
    """Build and write macro workbench JSON artifacts."""
    OUTPUT.mkdir(parents=True, exist_ok=True)
    previous = _read_json(WORKBENCH_JSON)
    enriched_cards = enrich_cards(cards)
    regimes = {
        str(card.get("code")): _regime_for_card(card)
        for card in enriched_cards
    }
    heatmap = _heatmap(enriched_cards, regimes)
    release_monitor = _release_monitor()
    gap_backlog = _gap_backlog(enriched_cards)
    what_changed = _what_changed(previous, enriched_cards, regimes)
    degradation_alerts = _degradation_alerts(previous, enriched_cards, heatmap)

    payload = {
        "generated": datetime.now(UTC).isoformat(),
        "schema_version": "macro-workbench-v1",
        "cards": enriched_cards,
        "regimes": regimes,
        "heatmap": heatmap,
        "release_monitor": release_monitor,
        "gap_backlog": gap_backlog,
        "what_changed": what_changed,
        "degradation_alerts": degradation_alerts,
        "phase_coverage": {
            "phase_2_unified_data": "data-first canonical frame JSONs and shared summary metadata are generated for CN/UK/US; CE4 remains canonical DataPipeline-backed.",
            "phase_3_quality": "freshness, source health, transform audit, proxy-free checks, and degradation deltas are machine-readable.",
            "phase_4_deepening": "gap backlog prioritizes remaining source work without rendering unverified proxies.",
            "phase_5_workbench": "regime board, heatmap, release monitor, and what-changed are generated.",
            "phase_6_ui": "archive page consumes this workbench layer for country comparison and monitoring.",
        },
    }
    WORKBENCH_JSON.write_text(json.dumps(payload, indent=2, ensure_ascii=False))
    RELEASE_MONITOR_JSON.write_text(json.dumps({
        "generated": payload["generated"],
        "items": release_monitor,
    }, indent=2, ensure_ascii=False))
    WHAT_CHANGED_JSON.write_text(json.dumps({
        "generated": payload["generated"],
        "items": what_changed,
    }, indent=2, ensure_ascii=False))
    DATA_GAP_BACKLOG_JSON.write_text(json.dumps({
        "generated": payload["generated"],
        "items": gap_backlog,
    }, indent=2, ensure_ascii=False))
    return payload


if __name__ == "__main__":
    archive = _read_json(OUTPUT / "dashboard_archive_summary.json")
    payload = build_workbench(archive.get("cards", []) or [])
    print(f"Wrote {WORKBENCH_JSON} ({len(payload.get('cards', []))} countries)")
    print(f"Wrote {RELEASE_MONITOR_JSON}")
    print(f"Wrote {WHAT_CHANGED_JSON}")
    print(f"Wrote {DATA_GAP_BACKLOG_JSON}")
