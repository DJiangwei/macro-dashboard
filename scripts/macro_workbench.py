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
BRIEFING_MD = ROOT / "MACRO_WORKBENCH_BRIEFING.md"
BRIEFING_OUTPUT_MD = OUTPUT / "macro_briefing.md"

DASHBOARD_TO_CODE = {
    "Hungary": "HU",
    "Poland": "PL",
    "Czechia": "CZ",
    "Romania": "RO",
    "China": "CN",
    "Euro Area": "EA",
    "Japan": "JP",
    "South Africa": "ZA",
    "United Kingdom": "UK",
    "United States": "US",
}
CODE_TO_DASHBOARD = {code: name for name, code in DASHBOARD_TO_CODE.items()}

DATA_FIRST_SUMMARIES = {
    "CN": "china_dashboard_summary.json",
    "EA": "euro_area_dashboard_summary.json",
    "JP": "japan_dashboard_summary.json",
    "ZA": "south_africa_dashboard_summary.json",
    "UK": "uk_dashboard_summary.json",
    "US": "us_dashboard_summary.json",
}

DATA_FIRST_CANONICAL = {
    "CN": "china_canonical_frame.json",
    "EA": "euro_area_canonical_frame.json",
    "JP": "japan_canonical_frame.json",
    "ZA": "south_africa_canonical_frame.json",
    "UK": "uk_canonical_frame.json",
    "US": "us_canonical_frame.json",
}

DATA_FIRST_SIGNAL_MAP = {
    "CN": {
        "growth": ("industrial_value_added_yoy_akshare", "Industrial production"),
        "inflation": ("cpi_yoy_akshare", "CPI inflation"),
        "policy": ("lpr_1y_akshare", "1Y LPR"),
        "external": ("customs_exports_yoy_akshare", "Exports"),
        "fiscal": ("general_gov_debt", "Government debt/GDP"),
        "financial": ("shibor_3m_akshare", "3M Shibor"),
        "property": ("commercial_housing_sales_value_yoy_eastmoney", "Housing sales YoY"),
    },
    "EA": {
        "growth": ("real_gdp_yoy", "Real GDP"),
        "inflation": ("hicp_inflation", "HICP headline"),
        "policy": ("policy_rate", "ECB DFR"),
        "external": ("current_account_gdp", "Current account/GDP"),
        "fiscal": ("government_debt_gdp", "Government debt/GDP"),
        "financial": ("it_de_spread_10y", "BTP-Bund 10Y spread"),
        "property": ("house_price_yoy", "House prices"),
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
        "external": ("current_account_gdp", "Current account/GDP"),
        "fiscal": ("psnd_ex_banks_gdp", "PSND/GDP"),
        "financial": ("sonia_rate", "SONIA"),
        "property": ("uk_hpi_annual_change", "UK HPI"),
    },
    "US": {
        "growth": ("real_gdp_growth", "Real GDP"),
        "inflation": ("core_pce_inflation", "Core PCE"),
        "policy": ("daily_fed_funds", "Fed funds"),
        "external": ("goods_trade_balance", "Goods trade balance"),
        "fiscal": ("federal_debt_gdp", "Federal debt/GDP"),
        "financial": ("mortgage_30y_rate", "Mortgage rate"),
        "property": ("case_shiller_20_city_growth", "Case-Shiller 20-City"),
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


def _key_series(code: str, summary: dict[str, Any]) -> dict[str, dict[str, Any]]:
    series_map: dict[str, dict[str, Any]] = {
        str(item.get("id")): item
        for item in summary.get("key_series_latest", []) or []
        if item.get("id")
    }
    canonical_file = DATA_FIRST_CANONICAL.get(code)
    if canonical_file:
        c_path = OUTPUT / canonical_file
        if c_path.exists():
            try:
                frame_data = json.loads(c_path.read_text())
                for s in frame_data.get("series", []):
                    ind_id = s.get("indicator_id")
                    if ind_id and ind_id not in series_map:
                        obs = s.get("observations", [])
                        if obs:
                            latest_obs = obs[-1]
                            val = float(latest_obs[1])
                            dt = str(latest_obs[0])
                            unit = s.get("unit", "")
                            series_map[ind_id] = {
                                "id": ind_id,
                                "latest_value": val,
                                "latest_display": f"{val:.2f} {unit}".strip(),
                                "latest_date": dt,
                                "source_name": s.get("source", {}).get("name", ""),
                                "quality_status": s.get("quality", {}).get("status", ""),
                                "unit": unit,
                                "label": s.get("label_en", ind_id),
                            }
            except Exception:
                pass
    return series_map


def _data_first_signals(code: str, summary: dict[str, Any]) -> dict[str, dict[str, Any]]:
    key_series = _key_series(code, summary)
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


def _regime_label(dimension: str, value: float | None, display: str, signal_id: str) -> tuple[str, float, float]:
    if value is None:
        return "insufficient data", 50.0, 0.0

    display_l = str(display).lower()
    sid_l = str(signal_id).lower()
    if "y/y" in display_l or "yoy" in sid_l:
        transform = "yoy"
    elif "m/m" in display_l or "mom" in sid_l:
        transform = "mom"
    elif "q/q" in display_l or "qoq" in sid_l:
        transform = "qoq"
    else:
        transform = "level"

    confidence = 1.0
    if transform in {"mom", "qoq"}:
        confidence = 0.8  # Fast frequency

    if dimension == "growth":
        if transform == "mom":
            if value >= 0.4: return "above-trend expansion", 80.0, confidence
            if value >= 0.1: return "moderate expansion", 65.0, confidence
            if value >= 0.0: return "stall-speed growth", 45.0, confidence
            return "contraction", 25.0, confidence
        elif transform == "qoq":
            if value >= 0.8: return "above-trend expansion", 80.0, confidence
            if value >= 0.3: return "moderate expansion", 65.0, confidence
            if value >= 0.0: return "stall-speed growth", 45.0, confidence
            return "contraction", 25.0, confidence
        elif transform == "level" and value > 30.0:
            # e.g., PMI level
            if value >= 52.0: return "above-trend expansion", 80.0, confidence
            if value >= 50.0: return "moderate expansion", 65.0, confidence
            return "contraction", 25.0, confidence
        else:
            # YoY or annualized rate
            if value >= 3.0: return "above-trend expansion", 80.0, confidence
            if value >= 1.5: return "moderate expansion", 65.0, confidence
            if value >= 0.0: return "stall-speed growth", 45.0, confidence
            return "contraction", 25.0, confidence

    if dimension == "inflation":
        if transform == "mom":
            if value >= 0.4: return "inflation pressure", 25.0, confidence
            if value >= 0.2: return "above-target inflation", 45.0, confidence
            if value >= 0.1: return "near-target inflation", 70.0, confidence
            return "disinflation risk", 55.0, confidence
        else:
            if value >= 4.5: return "inflation pressure", 25.0, confidence
            if value >= 2.8: return "above-target inflation", 45.0, confidence
            if value >= 1.5: return "near-target inflation", 75.0, confidence
            if value >= 0.0: return "disinflation risk", 55.0, confidence
            return "deflation risk", 30.0, confidence

    if dimension == "policy":
        if value >= 5.0: return "restrictive stance", 35.0, confidence
        if value >= 2.5: return "neutral-moderate stance", 60.0, confidence
        return "accommodative stance", 70.0, confidence

    if dimension == "external":
        if "balance" in sid_l:
            if value >= 0.0: return "external strength", 75.0, confidence
            return "external drag", 35.0, confidence
        else:
            if value >= 3.0: return "external strength", 75.0, confidence
            if value <= -3.0: return "external drag", 35.0, confidence
            return "balanced external impulse", 60.0, confidence

    if dimension == "fiscal":
        if "debt" in sid_l or (value > 20.0 and "balance" not in sid_l):
            if value >= 120.0: return "heavy debt overhang", 30.0, confidence
            if value >= 80.0: return "elevated debt", 45.0, confidence
            if value >= 60.0: return "moderate debt", 60.0, confidence
            return "debt contained", 75.0, confidence
        else:
            if value <= -6.0: return "fiscal stress", 30.0, confidence
            if value <= -3.0: return "watch fiscal slippage", 45.0, confidence
            return "fiscal contained", 65.0, confidence

    if dimension == "financial":
        if "spread" in sid_l or "bps" in display_l:
            if value <= 100.0: return "loose / minimal fragmentation", 75.0, confidence
            if value <= 175.0: return "moderate spread / stable", 60.0, confidence
            if value <= 250.0: return "elevated sovereign spread", 40.0, confidence
            return "severe fragmentation stress", 25.0, confidence
        elif "gap" in sid_l or "pp" in display_l:
            if value >= 10.0: return "credit bubble risk", 35.0, confidence
            if value <= -5.0: return "credit deleveraging", 40.0, confidence
            return "financial conditions stable", 65.0, confidence
        else:
            if value >= 7.0: return "tight financial conditions", 35.0, confidence
            if value >= 3.5: return "neutral financial conditions", 60.0, confidence
            return "easy financial conditions", 75.0, confidence

    if dimension == "property":
        if "yoy" in sid_l or "growth" in sid_l or "change" in sid_l or "%" in display_l:
            if value >= 7.0: return "property hot", 45.0, confidence
            if value >= 2.0: return "healthy property expansion", 65.0, confidence
            if value >= -1.0: return "property stable", 55.0, confidence
            return "property drag", 35.0, confidence
        return "property tracked", 55.0, confidence

    return "tracked", 50.0, confidence


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


TAYLOR_PARAMETERS = {
    "US": {"target": 2.0, "r_star": 1.0, "trend_growth": 2.0, "name": "Federal Reserve"},
    "EA": {"target": 2.0, "r_star": 0.5, "trend_growth": 1.2, "name": "ECB"},
    "UK": {"target": 2.0, "r_star": 1.25, "trend_growth": 1.2, "name": "Bank of England"},
    "JP": {"target": 2.0, "r_star": 0.0, "trend_growth": 0.8, "name": "Bank of Japan"},
    "CN": {"target": 3.0, "r_star": 1.5, "trend_growth": 4.5, "name": "PBC"},
    "ZA": {"target": 4.5, "r_star": 2.5, "trend_growth": 1.5, "name": "SARB"},
    "PL": {"target": 2.5, "r_star": 1.5, "trend_growth": 3.0, "name": "NBP"},
    "CZ": {"target": 2.0, "r_star": 1.2, "trend_growth": 2.0, "name": "CNB"},
    "HU": {"target": 3.0, "r_star": 1.8, "trend_growth": 2.2, "name": "MNB"},
    "RO": {"target": 2.5, "r_star": 2.0, "trend_growth": 2.5, "name": "BNR"},
}


def _compute_taylor_stance(code: str, signals: dict[str, Any]) -> dict[str, Any] | None:
    param = TAYLOR_PARAMETERS.get(code)
    if not param:
        return None
    policy_sig = signals.get("policy") or {}
    infl_sig = signals.get("inflation") or {}
    growth_sig = signals.get("growth") or {}

    policy_val = _number(policy_sig.get("value"))
    infl_val = _number(infl_sig.get("value"))
    growth_val = _number(growth_sig.get("value"))

    if policy_val is None or infl_val is None:
        return None

    target = param["target"]
    r_star = param["r_star"]
    trend_growth = param["trend_growth"]

    g_val = growth_val if growth_val is not None else trend_growth
    output_gap = max(-3.0, min(3.0, g_val - trend_growth))
    infl_gap = infl_val - target

    taylor_rate = r_star + infl_val + 0.5 * infl_gap + 0.5 * output_gap
    deviation = policy_val - taylor_rate
    real_rate = policy_val - infl_val

    taylor_low = round(taylor_rate - 0.5, 2)
    taylor_high = round(taylor_rate + 0.5, 2)
    dev_low = round(deviation - 0.5, 2)
    dev_high = round(deviation + 0.5, 2)

    if deviation >= 1.5:
        stance_label = "substantially restrictive"
    elif deviation >= 0.5:
        stance_label = "moderately restrictive"
    elif deviation >= -0.5:
        stance_label = "calibrated / neutral"
    elif deviation >= -1.5:
        stance_label = "moderately accommodative"
    else:
        stance_label = "substantially accommodative"

    return {
        "institution": param["name"],
        "policy_rate": round(policy_val, 2),
        "inflation_rate": round(infl_val, 2),
        "inflation_target": target,
        "neutral_real_rate_r_star": r_star,
        "taylor_implied_rate": round(taylor_rate, 2),
        "taylor_rate_range": [taylor_low, taylor_high],
        "policy_gap_deviation": round(deviation, 2),
        "policy_gap_range": [dev_low, dev_high],
        "real_policy_rate": round(real_rate, 2),
        "stance_label": stance_label,
    }


def _regime_for_card(card: dict[str, Any]) -> dict[str, Any]:
    code = str(card.get("code") or "")
    signals = card.get("signals") or {}
    dimensions: dict[str, dict[str, Any]] = {}

    cyc_scores, cyc_weights = [], []
    str_scores, str_weights = [], []

    cyclical_dims = {"growth", "inflation", "policy", "external"}
    structural_dims = {"fiscal", "financial", "property"}

    for dimension in ("growth", "inflation", "policy", "external", "fiscal", "financial", "property"):
        signal = signals.get(dimension, {})
        value = _number(signal.get("value") if signal else None)
        display = signal.get("display") or ""
        sig_id = signal.get("id") or ""

        label, score, weight = _regime_label(dimension, value, display, sig_id)
        dimensions[dimension] = {
            "label": label,
            "score": round(score, 1),
            "confidence_weight": weight,
            "value": value,
            "display": display or (f"{value:.2f}" if value is not None else "n/a"),
            "source_signal": sig_id,
        }
        if value is not None and weight > 0:
            if dimension in cyclical_dims:
                cyc_scores.append(score * weight)
                cyc_weights.append(weight)
            elif dimension in structural_dims:
                str_scores.append(score * weight)
                str_weights.append(weight)

    quality = _country_quality_score(card)

    cyc_total_weight = sum(cyc_weights) if cyc_weights else 0
    str_total_weight = sum(str_weights) if str_weights else 0

    cyclical_score = sum(cyc_scores) / cyc_total_weight if cyc_total_weight > 0 else 50.0
    structural_score = sum(str_scores) / str_total_weight if str_total_weight > 0 else 50.0

    composite = _score((cyclical_score + structural_score) / 2)

    if composite >= 70:
        composite_label = "constructive"
    elif composite >= 50:
        composite_label = "mixed"
    else:
        composite_label = "defensive"

    taylor_stance = _compute_taylor_stance(code, signals)

    return {
        "composite_score": round(composite, 1),
        "cyclical_score": round(cyclical_score, 1),
        "structural_score": round(structural_score, 1),
        "composite_label": composite_label,
        "quality": quality,
        "dimensions": dimensions,
        "taylor_stance": taylor_stance,
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


def _pearson(x: list[float], y: list[float]) -> float:
    n = len(x)
    if n < 3:
        return 0.0
    mx, my = sum(x) / n, sum(y) / n
    vx = sum((xi - mx) ** 2 for xi in x)
    vy = sum((yi - my) ** 2 for yi in y)
    if vx <= 1e-9 or vy <= 1e-9:
        return 0.0
    cov = sum((xi - mx) * (yi - my) for xi, yi in zip(x, y))
    return round(cov / math.sqrt(vx * vy), 2)


def _compute_cross_country_sync() -> dict[str, Any]:
    countries = ["US", "EA", "UK", "JP", "CN", "ZA", "PL", "CZ", "HU", "RO"]
    cpi_data: dict[str, dict[str, float]] = {}
    ip_data: dict[str, dict[str, float]] = {}

    canonical_specs = {
        "CN": ("china_canonical_frame.json", "cpi_yoy_akshare", "industrial_value_added_yoy_akshare"),
        "EA": ("euro_area_canonical_frame.json", "hicp_inflation", "industrial_production_yoy"),
        "JP": ("japan_canonical_frame.json", "cpi_inflation", "industrial_production_growth"),
        "ZA": ("south_africa_canonical_frame.json", "cpi_inflation", "manufacturing_production_growth"),
        "UK": ("uk_canonical_frame.json", "cpi_yoy", "industrial_production_yoy"),
        "US": ("us_canonical_frame.json", "cpi_inflation", "industrial_production_growth"),
    }

    for code, (fname, cpi_k, ip_k) in canonical_specs.items():
        p = OUTPUT / fname
        if p.exists():
            d = _read_json(p)
            for s in d.get("series", []) or []:
                ind_id = s.get("indicator_id")
                if ind_id == cpi_k:
                    cpi_data[code] = {str(r[0])[:7]: float(r[1]) for r in s.get("observations", []) if len(r) >= 2 and r[1] is not None}
                elif ind_id == ip_k:
                    ip_data[code] = {str(r[0])[:7]: float(r[1]) for r in s.get("observations", []) if len(r) >= 2 and r[1] is not None}

    cee_path = OUTPUT / "cee_canonical_frame.json"
    if cee_path.exists():
        cee = _read_json(cee_path)
        for s in cee.get("series", []) or []:
            ind_id = s.get("indicator_id")
            country = str(s.get("country") or "").upper()
            if country in countries:
                if ind_id == "cpi_yoy":
                    cpi_data[country] = {str(r[0])[:7]: float(r[1]) for r in s.get("observations", []) if len(r) >= 2 and r[1] is not None}
                elif ind_id == "industrial_production_yoy":
                    ip_data[country] = {str(r[0])[:7]: float(r[1]) for r in s.get("observations", []) if len(r) >= 2 and r[1] is not None}

    cpi_common = sorted(list(set.intersection(*[set(cpi_data[c].keys()) for c in countries if c in cpi_data]))) if len(cpi_data) >= len(countries) else []
    ip_common = sorted(list(set.intersection(*[set(ip_data[c].keys()) for c in countries if c in ip_data]))) if len(ip_data) >= len(countries) else []

    cpi_matrix: dict[str, dict[str, float]] = {}
    if len(cpi_common) >= 12:
        cpi_window = cpi_common[-36:]
        for c1 in countries:
            cpi_matrix[c1] = {}
            for c2 in countries:
                x = [cpi_data[c1][m] for m in cpi_window]
                y = [cpi_data[c2][m] for m in cpi_window]
                cpi_matrix[c1][c2] = _pearson(x, y)

    ip_matrix: dict[str, dict[str, float]] = {}
    if len(ip_common) >= 12:
        ip_window = ip_common[-36:]
        for c1 in countries:
            ip_matrix[c1] = {}
            for c2 in countries:
                x = [ip_data[c1][m] for m in ip_window]
                y = [ip_data[c2][m] for m in ip_window]
                ip_matrix[c1][c2] = _pearson(x, y)

    return {
        "countries": countries,
        "sample_period_cpi": f"{cpi_common[-36]} to {cpi_common[-1]}" if len(cpi_common) >= 36 else "",
        "sample_period_ip": f"{ip_common[-36]} to {ip_common[-1]}" if len(ip_common) >= 36 else "",
        "inflation_correlation": cpi_matrix,
        "industrial_production_correlation": ip_matrix,
    }


def _generate_briefing(payload: dict[str, Any]) -> str:
    generated = payload.get("generated", "")[:10]
    cards = payload.get("cards", [])
    regimes = payload.get("regimes", {})
    monetary = payload.get("monetary_stance_monitor", {})
    sync = payload.get("cross_country_sync", {})
    inf_matrix = sync.get("inflation_correlation", {})
    ip_matrix = sync.get("industrial_production_correlation", {})

    lines = [
        "# Global Macro Workbench Intelligence Briefing",
        "",
        f"**Generated**: {generated} | **Coverage**: 10 Economies (US, EA, UK, JP, CN, ZA, PL, CZ, HU, RO)",
        "",
        "---",
        "",
        "## 1. Global Macro Regime Board",
        "",
        "| Country | Cyclical | Structural | Composite | Growth Assessment | Inflation Assessment | Policy Stance | Data Quality |",
        "| :--- | :---: | :---: | :---: | :--- | :--- | :--- | :---: |",
    ]
    for c in cards:
        code = str(c.get("code"))
        name = c.get("name")
        r = regimes.get(code, {})
        dims = r.get("dimensions", {})
        q = r.get("quality", {})
        g_lbl = dims.get("growth", {}).get("label", "n/a")
        i_lbl = dims.get("inflation", {}).get("label", "n/a")
        p_lbl = dims.get("policy", {}).get("label", "n/a")
        lines.append(
            f"| **{name} ({code})** | {r.get('cyclical_score', 0):.1f} | {r.get('structural_score', 0):.1f} | **{r.get('composite_label', 'mixed')}** | {g_lbl} | {i_lbl} | {p_lbl} | {q.get('score', 0):.1f} ({q.get('label', 'n/a')}) |"
        )

    lines.extend([
        "",
        "---",
        "",
        "## 2. Central Bank Policy Stance & Taylor Rule Monitor",
        "",
        "Theoretical rate benchmark calculated as $i^* = r^* + \\pi + 0.5(\\pi - \\pi^*) + 0.5(y - y^*)$ with $r^* \\pm 50\\text{ bps}$ sensitivity band.",
        "",
        "| Economy / Institution | Policy Rate | Inflation (Target) | Neutral $r^*$ | Taylor Benchmark (Range) | Policy Gap | Stance Label |",
        "| :--- | :---: | :---: | :---: | :---: | :---: | :--- |",
    ])
    for code, m in monetary.items():
        if not m:
            continue
        inst = m.get("institution", code)
        pr = m.get("policy_rate")
        inf = m.get("inflation_rate")
        tgt = m.get("inflation_target")
        r_star = m.get("neutral_real_rate_r_star")
        tb = m.get("taylor_implied_rate")
        tb_rng = m.get("taylor_rate_range", [tb, tb])
        gap = m.get("policy_gap_deviation")
        sign = "+" if gap > 0 else ""
        lines.append(
            f"| **{code}** ({inst}) | **{pr:.2f}%** | {inf:.2f}% ({tgt:.1f}%) | {r_star:.2f}% | **{tb:.2f}%** ({tb_rng[0]:.2f}% ~ {tb_rng[1]:.2f}%) | **{sign}{gap:.2f}%** | *{m.get('stance_label', 'n/a')}* |"
        )

    lines.extend([
        "",
        "---",
        "",
        "## 3. Cross-Country Synchronization (36-Month Rolling Correlation)",
        "",
        "- **Nominal Cycle (Headline CPI Inflation)**:",
        f"  - Highly coupled core: US vs. Euro Area (**{inf_matrix.get('US', {}).get('EA', 'n/a')}**), US vs. UK (**{inf_matrix.get('US', {}).get('UK', 'n/a')}**), Euro Area vs. UK (**{inf_matrix.get('EA', {}).get('UK', 'n/a')}**).",
        f"  - Independent domestic price cycle: China vs. US (**{inf_matrix.get('CN', {}).get('US', 'n/a')}**), China vs. Euro Area (**{inf_matrix.get('CN', {}).get('EA', 'n/a')}**).",
        "- **Real Business Cycle (Industrial Production)**:",
        f"  - Transatlantic industrial linkage: US vs. Euro Area (**{ip_matrix.get('US', {}).get('EA', 'n/a')}**), US vs. UK (**{ip_matrix.get('US', {}).get('UK', 'n/a')}**).",
        f"  - Manufacturing divergence: China vs. US (**{ip_matrix.get('CN', {}).get('US', 'n/a')}**), Japan vs. US (**{ip_matrix.get('JP', {}).get('US', 'n/a')}**).",
        "",
        "---",
        "",
        "## 4. Priority Data Quality & Maintenance Backlog",
        "",
        "| Code | Section | Item | Priority | Action Hint |",
        "| :---: | :--- | :--- | :---: | :--- |",
    ])
    backlog = payload.get("gap_backlog", [])
    for b in backlog[:10]:
        lines.append(
            f"| **{b.get('code')}** | `{b.get('section')}` | {b.get('item')} | **{str(b.get('priority')).upper()}** | {b.get('source_hint')} |"
        )

    lines.append("")
    return "\n".join(lines)


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
    monetary_stance_monitor = {
        code: r.get("taylor_stance")
        for code, r in regimes.items()
        if r.get("taylor_stance")
    }
    cross_country_sync = _compute_cross_country_sync()

    payload = {
        "generated": datetime.now(UTC).isoformat(),
        "schema_version": "macro-workbench-v1",
        "cards": enriched_cards,
        "regimes": regimes,
        "monetary_stance_monitor": monetary_stance_monitor,
        "cross_country_sync": cross_country_sync,
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
    briefing_text = _generate_briefing(payload)
    BRIEFING_MD.write_text(briefing_text, encoding="utf-8")
    BRIEFING_OUTPUT_MD.write_text(briefing_text, encoding="utf-8")
    return payload


if __name__ == "__main__":
    archive = _read_json(OUTPUT / "dashboard_archive_summary.json")
    payload = build_workbench(archive.get("cards", []) or [])
    print(f"Wrote {WORKBENCH_JSON} ({len(payload.get('cards', []))} countries)")
    print(f"Wrote {RELEASE_MONITOR_JSON}")
    print(f"Wrote {WHAT_CHANGED_JSON}")
    print(f"Wrote {DATA_GAP_BACKLOG_JSON}")
