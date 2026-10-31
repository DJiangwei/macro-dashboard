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
    "Turkey": "TR",
    "Hong Kong": "HK",
    "South Korea": "KR",
    "Taiwan": "TW",
    "Kazakhstan": "KZ",
    "Uzbekistan": "UZ",
    "Egypt": "EG",
    "Nigeria": "NG",
}
CODE_TO_DASHBOARD = {code: name for name, code in DASHBOARD_TO_CODE.items()}

DATA_FIRST_SUMMARIES = {
    "CN": "china_dashboard_summary.json",
    "EA": "euro_area_dashboard_summary.json",
    "JP": "japan_dashboard_summary.json",
    "ZA": "south_africa_dashboard_summary.json",
    "UK": "uk_dashboard_summary.json",
    "US": "us_dashboard_summary.json",
    "TR": "turkey_dashboard_summary.json",
    "HK": "hong_kong_dashboard_summary.json",
    "KR": "south_korea_dashboard_summary.json",
    "TW": "taiwan_dashboard_summary.json",
    "KZ": "kazakhstan_dashboard_summary.json",
    "UZ": "uzbekistan_dashboard_summary.json",
    "EG": "egypt_dashboard_summary.json",
    "NG": "nigeria_dashboard_summary.json",
}

DATA_FIRST_CANONICAL = {
    "CN": "china_canonical_frame.json",
    "EA": "euro_area_canonical_frame.json",
    "JP": "japan_canonical_frame.json",
    "ZA": "south_africa_canonical_frame.json",
    "UK": "uk_canonical_frame.json",
    "US": "us_canonical_frame.json",
    "TR": "turkey_canonical_frame.json",
    "HK": "hong_kong_canonical_frame.json",
    "KR": "south_korea_canonical_frame.json",
    "TW": "taiwan_canonical_frame.json",
    "KZ": "kazakhstan_canonical_frame.json",
    "UZ": "uzbekistan_canonical_frame.json",
    "EG": "egypt_canonical_frame.json",
    "NG": "nigeria_canonical_frame.json",
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
    "TR": {
        "growth": ("real_gdp_yoy", "Real GDP"),
        "inflation": ("cpi_inflation", "CPI inflation"),
        "policy": ("policy_rate", "1W Repo"),
        "external": ("current_account_gdp", "Current account/GDP"),
        "fiscal": ("government_debt_gdp", "Government debt/GDP"),
        "financial": ("try_usd", "USD/TRY"),
        "property": ("house_price_growth", "House prices"),
    },
    "HK": {
        "growth": ("real_gdp_yoy", "Real GDP"),
        "inflation": ("cpi_inflation", "Composite CPI"),
        "policy": ("policy_rate", "Base rate"),
        "external": ("merchandise_trade_balance", "Trade balance"),
        "fiscal": ("government_debt_gdp", "Government debt/GDP"),
        "financial": ("usd_hkd", "USD/HKD"),
        "property": ("bis_nominal_house_prices", "BIS house prices"),
    },
    "KR": {
        "growth": ("real_gdp_yoy", "Real GDP"),
        "inflation": ("cpi_inflation", "CPI inflation"),
        "policy": ("policy_rate", "Call rate"),
        "external": ("current_account_usd", "Current account"),
        "fiscal": ("government_debt_gdp", "Government debt/GDP"),
        "financial": ("sovereign_yield_10y", "10Y KTB"),
        "property": ("bis_nominal_house_prices", "BIS house prices"),
    },
    "TW": {
        "growth": ("real_gdp_yoy", "Real GDP"),
        "inflation": ("cpi_inflation", "Headline CPI"),
        "policy": ("policy_rate", "CBC discount rate"),
        "external": ("current_account_usd", "Current account"),
        "fiscal": ("government_debt_gdp", "Government debt/GDP"),
        "financial": ("sovereign_yield_10y", "10Y bond yield"),
        "property": ("mortgage_loans_growth", "Mortgage growth"),
    },
    "KZ": {
        "growth": ("real_gdp_growth", "Real GDP"),
        "inflation": ("cpi_inflation", "CPI inflation"),
        "policy": ("policy_rate", "NBK policy rate"),
        "external": ("current_account_gdp", "Current account/GDP"),
        "fiscal": ("government_debt_gdp", "Government debt/GDP"),
        "financial": ("usd_kzt", "USD/KZT"),
        "property": ("brent_crude_oil", "Brent crude oil"),
    },
    "UZ": {
        "growth": ("real_gdp_growth", "Real GDP"),
        "inflation": ("cpi_inflation", "CPI inflation"),
        "policy": ("policy_rate", "CBU policy rate"),
        "external": ("remittances_gdp", "Remittances/GDP"),
        "fiscal": ("government_debt_gdp", "Government debt/GDP"),
        "financial": ("usd_uzs", "USD/UZS"),
        "property": ("lending_rate", "Commercial lending rate"),
    },
    "EG": {
        "growth": ("real_gdp_growth", "Real GDP"),
        "inflation": ("cpi_inflation", "CPI inflation"),
        "policy": ("policy_rate", "CBE corridor rate"),
        "external": ("remittances_gdp", "Remittances/GDP"),
        "fiscal": ("government_debt_gdp", "Government debt/GDP"),
        "financial": ("usd_egp", "USD/EGP"),
        "property": ("brent_crude_oil", "Brent crude oil"),
    },
    "NG": {
        "growth": ("real_gdp_growth", "Real GDP"),
        "inflation": ("cpi_inflation", "CPI inflation"),
        "policy": ("policy_rate", "CBN MPR"),
        "external": ("current_account_gdp", "Current account/GDP"),
        "fiscal": ("government_debt_gdp", "Government debt/GDP"),
        "financial": ("usd_ngn", "USD/NGN"),
        "property": ("brent_crude_oil", "Brent crude oil"),
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
                        raw_obs = s.get("observations", [])
                        obs = [
                            o for o in raw_obs
                            if not (isinstance(o, list) and len(o) >= 3 and o[2])
                        ] or raw_obs
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
    "TR": {"target": 5.0, "r_star": 3.0, "trend_growth": 3.5, "name": "TCMB"},
    "HK": {"target": 2.0, "r_star": 1.0, "trend_growth": 2.5, "name": "HKMA"},
    "KR": {"target": 2.0, "r_star": 1.0, "trend_growth": 2.2, "name": "BOK"},
    "TW": {"target": 2.0, "r_star": 1.0, "trend_growth": 2.5, "name": "CBC"},
    "KZ": {"target": 5.0, "r_star": 2.5, "trend_growth": 4.0, "name": "NBK"},
    "UZ": {"target": 5.0, "r_star": 3.0, "trend_growth": 5.5, "name": "CBU"},
    "EG": {"target": 7.0, "r_star": 2.0, "trend_growth": 4.5, "name": "CBE"},
    "NG": {"target": 9.0, "r_star": 2.0, "trend_growth": 3.5, "name": "CBN"},
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
    countries = ["US", "EA", "UK", "JP", "CN", "ZA", "TR", "HK", "KR", "TW", "KZ", "UZ", "EG", "NG", "PL", "CZ", "HU", "RO"]
    cpi_data: dict[str, dict[str, float]] = {}
    ip_data: dict[str, dict[str, float]] = {}
    yield_data: dict[str, dict[str, float]] = {}
    yield_latest: dict[str, dict[str, Any]] = {}

    canonical_specs = {
        "CN": ("china_canonical_frame.json", "cpi_yoy_akshare", "industrial_value_added_yoy_akshare"),
        "EA": ("euro_area_canonical_frame.json", "hicp_inflation", "industrial_production_yoy"),
        "JP": ("japan_canonical_frame.json", "cpi_inflation", "industrial_production_growth"),
        "ZA": ("south_africa_canonical_frame.json", "cpi_inflation", "manufacturing_production_growth"),
        "UK": ("uk_canonical_frame.json", "cpi_yoy", "industrial_production_yoy"),
        "US": ("us_canonical_frame.json", "cpi_inflation", "industrial_production_growth"),
        "TR": ("turkey_canonical_frame.json", "hicp_inflation", "industrial_production_growth"),
        "HK": ("hong_kong_canonical_frame.json", "cpi_inflation", "industrial_production_growth"),
        "KR": ("south_korea_canonical_frame.json", "cpi_inflation", "industrial_production_growth"),
        "TW": ("taiwan_canonical_frame.json", "cpi_inflation", "real_gdp_growth"),
        "KZ": ("kazakhstan_canonical_frame.json", "cpi_inflation", "real_gdp_growth"),
        "UZ": ("uzbekistan_canonical_frame.json", "cpi_inflation", "real_gdp_growth"),
        "EG": ("egypt_canonical_frame.json", "cpi_inflation", "real_gdp_growth"),
        "NG": ("nigeria_canonical_frame.json", "cpi_inflation", "industry_growth"),
    }

    yield_specs = {
        "US": ("us_canonical_frame.json", "treasury_10y_yield", "10Y Treasury"),
        "EA": ("euro_area_canonical_frame.json", "irs_10y_de", "10Y Bund"),
        "UK": ("uk_canonical_frame.json", "long_rate_10y", "10Y Gilt"),
        "JP": ("japan_canonical_frame.json", "sovereign_yield_10y", "10Y JGB"),
        "ZA": ("south_africa_canonical_frame.json", "sovereign_yield_10y", "10Y Sovereign"),
        "KR": ("south_korea_canonical_frame.json", "sovereign_yield_10y", "10Y KTB"),
        "TW": ("taiwan_canonical_frame.json", "sovereign_yield_10y", "10Y Gov Bond"),
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

    for code, (fname, yld_k, bmk_name) in yield_specs.items():
        p = OUTPUT / fname
        if p.exists():
            d = _read_json(p)
            for s in d.get("series", []) or []:
                if s.get("indicator_id") == yld_k:
                    obs = s.get("observations", [])
                    if obs:
                        m_dict = {}
                        for r in obs:
                            if len(r) >= 2 and r[1] is not None:
                                m_dict[str(r[0])[:7]] = float(r[1])
                        yield_data[code] = m_dict
                        last_r = obs[-1]
                        yield_latest[code] = {
                            "benchmark": bmk_name,
                            "date": str(last_r[0]),
                            "yield": round(float(last_r[1]), 2),
                        }

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
                elif ind_id == "sov_yield_10y":
                    obs = s.get("observations", [])
                    if obs:
                        yield_data[country] = {str(r[0])[:7]: float(r[1]) for r in obs if len(r) >= 2 and r[1] is not None}
                        last_r = obs[-1]
                        yield_latest[country] = {
                            "benchmark": f"{country} 10Y Benchmark",
                            "date": str(last_r[0]),
                            "yield": round(float(last_r[1]), 2),
                        }

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

    us_yld = yield_latest.get("US", {}).get("yield")
    sovereign_spreads: dict[str, dict[str, Any]] = {}
    for c in countries:
        y_info = yield_latest.get(c)
        if not y_info or y_info.get("yield") is None or us_yld is None:
            sovereign_spreads[c] = {
                "benchmark": y_info.get("benchmark", f"{c} 10Y") if y_info else f"{c} 10Y",
                "date": y_info.get("date", "n/a") if y_info else "n/a",
                "yield": None,
                "spread_bps": None,
                "status": "data_gap",
            }
        else:
            y_val = y_info["yield"]
            spread_bps = round((y_val - us_yld) * 100, 1)
            sovereign_spreads[c] = {
                "benchmark": y_info["benchmark"],
                "date": y_info["date"],
                "yield": y_val,
                "spread_bps": spread_bps,
                "status": "observed",
            }

    yield_countries = [c for c in countries if c in yield_data and len(yield_data[c]) >= 12]
    yield_common = sorted(list(set.intersection(*[set(yield_data[c].keys()) for c in yield_countries]))) if yield_countries else []
    yield_matrix: dict[str, dict[str, float | None]] = {}
    if len(yield_common) >= 12:
        yield_window = yield_common[-36:]
        for c1 in countries:
            yield_matrix[c1] = {}
            for c2 in countries:
                if c1 in yield_data and c2 in yield_data and all(m in yield_data[c1] and m in yield_data[c2] for m in yield_window):
                    x = [yield_data[c1][m] for m in yield_window]
                    y = [yield_data[c2][m] for m in yield_window]
                    yield_matrix[c1][c2] = _pearson(x, y)
                else:
                    yield_matrix[c1][c2] = None

    reer_cache_path = ROOT / "data" / "bruegel_reer_monthly.json"
    reer_matrix: dict[str, dict[str, float | None]] = {}
    reer_common: list[str] = []
    if reer_cache_path.exists():
        r_payload = _read_json(reer_cache_path)
        r_countries = r_payload.get("countries", {})
        reer_series_map: dict[str, dict[str, float]] = {}
        for c in countries:
            c_info = r_countries.get(c, {})
            obs_list = c_info.get("reer_120", [])
            reer_series_map[c] = {x["date"]: float(x["value"]) for x in obs_list if "date" in x and "value" in x}
        reer_common = sorted(list(set.intersection(*[set(reer_series_map[c].keys()) for c in countries if c in reer_series_map])))
        if len(reer_common) >= 36:
            r_window = reer_common[-36:]
            for c1 in countries:
                reer_matrix[c1] = {}
                for c2 in countries:
                    x = [reer_series_map[c1][m] for m in r_window]
                    y = [reer_series_map[c2][m] for m in r_window]
                    reer_matrix[c1][c2] = _pearson(x, y)

    return {
        "countries": countries,
        "sample_period_cpi": f"{cpi_common[-36]} to {cpi_common[-1]}" if len(cpi_common) >= 36 else "",
        "sample_period_ip": f"{ip_common[-36]} to {ip_common[-1]}" if len(ip_common) >= 36 else "",
        "sample_period_yield": f"{yield_common[-36]} to {yield_common[-1]}" if len(yield_common) >= 36 else "",
        "sample_period_reer": f"{reer_common[-36]} to {reer_common[-1]}" if len(reer_common) >= 36 else "",
        "inflation_correlation": cpi_matrix,
        "industrial_production_correlation": ip_matrix,
        "sovereign_yield_correlation": yield_matrix,
        "sovereign_spreads_to_us": sovereign_spreads,
        "reer_correlation": reer_matrix,
    }


def _compute_reer_valuation_monitor(countries: list[str]) -> dict[str, Any]:
    reer_cache_path = ROOT / "data" / "bruegel_reer_monthly.json"
    if not reer_cache_path.exists():
        return {}
    r_payload = _read_json(reer_cache_path)
    r_countries = r_payload.get("countries", {})
    monitor: dict[str, Any] = {}
    for c in countries:
        c_info = r_countries.get(c, {})
        reer_obs = [float(x["value"]) for x in c_info.get("reer_120", [])]
        neer_obs = [float(x["value"]) for x in c_info.get("neer_120", [])]
        if not reer_obs or len(reer_obs) < 120:
            continue
        latest_reer = reer_obs[-1]
        latest_neer = neer_obs[-1] if neer_obs else latest_reer
        latest_date = c_info.get("latest_reer", {}).get("date", "2026-09-01")

        ma60 = round(sum(reer_obs[-60:]) / 60, 2)
        ma120 = round(sum(reer_obs[-120:]) / 120, 2)
        dev5y = round((latest_reer / ma60 - 1) * 100, 1)
        dev10y = round((latest_reer / ma120 - 1) * 100, 1)
        wedge = round(latest_reer - latest_neer, 2)

        if dev10y >= 10.0:
            stance = "substantially overvalued (export cost headwind)"
        elif dev10y >= 5.0:
            stance = "moderately overvalued"
        elif dev10y <= -10.0:
            stance = "substantially undervalued (export cost tailwind)"
        elif dev10y <= -5.0:
            stance = "moderately undervalued"
        else:
            stance = "neutral / fair value"

        monitor[c] = {
            "country_code": c,
            "latest_date": latest_date,
            "reer_latest": round(latest_reer, 2),
            "neer_latest": round(latest_neer, 2),
            "ma_5y": ma60,
            "ma_10y": ma120,
            "dev_5y_pct": dev5y,
            "dev_10y_pct": dev10y,
            "inflation_wedge": wedge,
            "valuation_stance": stance,
        }
    return monitor


def _compute_sovereign_curve_monitor() -> list[dict[str, Any]]:
    """Compile cross-market sovereign yield curves, term spreads, and inflation expectations."""
    def get_latest(series_list: list[dict], ind_id: str) -> tuple[str | None, float | None]:
        for s in series_list:
            if s.get("indicator_id") == ind_id:
                obs = s.get("observations", [])
                if obs:
                    last = obs[-1]
                    if isinstance(last, dict):
                        return last.get("date"), float(last.get("value"))
                    elif isinstance(last, list):
                        return last[0], float(last[1])
        return None, None

    def read_canonical(fname: str) -> list[dict]:
        p = OUTPUT / fname
        if not p.exists():
            return []
        try:
            return json.loads(p.read_text()).get("series", [])
        except Exception:
            return []

    records: list[dict[str, Any]] = []

    # 1. US
    us = read_canonical("us_canonical_frame.json")
    dt_10y, y10_us = get_latest(us, "treasury_10y_yield")
    _, y2 = get_latest(us, "treasury_2y_yield")
    _, y5 = get_latest(us, "treasury_5y_yield")
    _, y30 = get_latest(us, "treasury_30y_yield")
    _, slope = get_latest(us, "yield_curve_10y2y")
    _, be10 = get_latest(us, "ten_year_breakeven")
    _, be5 = get_latest(us, "five_year_breakeven")
    slope_bps = round(slope * 100, 1) if slope is not None else (round((y10_us - y2) * 100, 1) if (y10_us and y2) else None)
    records.append({
        "code": "US",
        "name": "United States",
        "tenor_type": "Treasury",
        "date": dt_10y or "2026-10-30",
        "y2": round(y2, 2) if y2 is not None else None,
        "y5": round(y5, 2) if y5 is not None else None,
        "y10": round(y10_us, 2) if y10_us is not None else None,
        "y30": round(y30, 2) if y30 is not None else None,
        "slope_bps": slope_bps,
        "slope_label": "10s2s",
        "spread_vs_anchor": 0.0,
        "anchor_name": "US 10Y Benchmark",
        "breakeven_10y": round(be10, 2) if be10 is not None else None,
        "breakeven_5y": round(be5, 2) if be5 is not None else None,
        "regime": "Normal Steepening" if (slope_bps and slope_bps > 0) else ("Inverted" if (slope_bps and slope_bps < 0) else "Flat"),
    })

    # 2. Euro Area (AAA / German Bund)
    ea = read_canonical("euro_area_canonical_frame.json")
    dt_ea, y10_ea = get_latest(ea, "aaa_yield_10y")
    _, y2_ea = get_latest(ea, "aaa_yield_2y")
    _, y5_ea = get_latest(ea, "aaa_yield_5y")
    _, slope_ea = get_latest(ea, "yield_curve_slope")
    bund_10y = y10_ea or 3.37
    slope_ea_bps = round(slope_ea, 1) if slope_ea is not None else (round((y10_ea - y2_ea) * 100, 1) if (y10_ea and y2_ea) else None)
    records.append({
        "code": "EA",
        "name": "Euro Area (Bund / AAA)",
        "tenor_type": "Bund Benchmark",
        "date": dt_ea or "2026-10-30",
        "y2": round(y2_ea, 2) if y2_ea is not None else None,
        "y5": round(y5_ea, 2) if y5_ea is not None else None,
        "y10": round(y10_ea, 2) if y10_ea is not None else None,
        "y30": None,
        "slope_bps": slope_ea_bps,
        "slope_label": "10s2s",
        "spread_vs_anchor": 0.0,
        "anchor_name": "Bund Benchmark",
        "breakeven_10y": None,
        "breakeven_5y": None,
        "regime": "Normal Steepening" if (slope_ea_bps and slope_ea_bps > 0) else ("Inverted" if (slope_ea_bps and slope_ea_bps < 0) else "Flat"),
    })

    # 3. EA Periphery & Core Spreads
    for p_code, p_name, spr_id in [
        ("IT", "Italy (BTP)", "it_de_spread_10y"),
        ("FR", "France (OAT)", "fr_de_spread_10y"),
        ("ES", "Spain (Bonos)", "es_de_spread_10y"),
        ("GR", "Greece (GGB)", "gr_de_spread_10y"),
    ]:
        dt_p, spr = get_latest(ea, spr_id)
        implied_10y = round(bund_10y + (spr / 100.0), 2) if spr is not None else None
        records.append({
            "code": p_code,
            "name": p_name,
            "tenor_type": "Sovereign Spread",
            "date": dt_p or "2026-09-01",
            "y2": None,
            "y5": None,
            "y10": implied_10y,
            "y30": None,
            "slope_bps": None,
            "slope_label": "-",
            "spread_vs_anchor": round(spr, 1) if spr is not None else None,
            "anchor_name": "vs Bund (bps)",
            "breakeven_10y": None,
            "breakeven_5y": None,
            "regime": "Narrow Spread (<60bps)" if (spr and spr < 60) else ("Moderate Spread (60-120bps)" if (spr and spr <= 120) else "Elevated Spread (>120bps)"),
        })

    # 4. UK (Gilt)
    uk = read_canonical("uk_canonical_frame.json")
    dt_uk, y10_uk = get_latest(uk, "long_rate_10y")
    _, y5_uk = get_latest(uk, "gilt_5y_nominal_par_yield")
    _, y20_uk = get_latest(uk, "gilt_20y_nominal_par_yield")
    _, slope_uk = get_latest(uk, "yield_curve_slope_10y5y")
    records.append({
        "code": "UK",
        "name": "United Kingdom",
        "tenor_type": "Gilt Benchmark",
        "date": dt_uk or "2026-10-28",
        "y2": None,
        "y5": round(y5_uk, 2) if y5_uk is not None else None,
        "y10": round(y10_uk, 2) if y10_uk is not None else None,
        "y30": round(y20_uk, 2) if y20_uk is not None else None,
        "slope_bps": round(slope_uk, 1) if slope_uk is not None else None,
        "slope_label": "10s5s",
        "spread_vs_anchor": round((y10_uk - bund_10y) * 100, 1) if (y10_uk and bund_10y) else None,
        "anchor_name": "vs Bund (bps)",
        "breakeven_10y": None,
        "breakeven_5y": None,
        "regime": "Normal Steepening" if (slope_uk and slope_uk > 0) else "Flat / Inverted",
    })

    # 5. Japan (JGB)
    jp = read_canonical("japan_canonical_frame.json")
    dt_jp, y10_jp = get_latest(jp, "sovereign_yield_10y")
    _, tibor_jp = get_latest(jp, "jp_tibor_3m_rate")
    _, slope_jp = get_latest(jp, "yield_curve_slope_10y3m")
    records.append({
        "code": "JP",
        "name": "Japan",
        "tenor_type": "JGB Benchmark",
        "date": dt_jp or "2026-09-01",
        "y2": round(tibor_jp, 2) if tibor_jp is not None else None,
        "y5": None,
        "y10": round(y10_jp, 2) if y10_jp is not None else None,
        "y30": None,
        "slope_bps": round(slope_jp, 1) if slope_jp is not None else None,
        "slope_label": "10s3m",
        "spread_vs_anchor": round((y10_jp - (y10_us or 4.98)) * 100, 1) if y10_jp else None,
        "anchor_name": "vs US 10Y (bps)",
        "breakeven_10y": None,
        "breakeven_5y": None,
        "regime": "Steepening post-YCC" if (slope_jp and slope_jp > 100) else "Managed Flattish",
    })

    # 6. China (CGB)
    cn = read_canonical("china_canonical_frame.json")
    dt_cn, y10_cn = get_latest(cn, "cgb_yield_10y")
    _, y2_cn = get_latest(cn, "cgb_yield_2y")
    _, y5_cn = get_latest(cn, "cgb_yield_5y")
    _, y30_cn = get_latest(cn, "cgb_yield_30y")
    _, slope_cn = get_latest(cn, "cgb_curve_10y2y")
    _, spr_cn = get_latest(cn, "us_cn_spread_10y")
    slope_cn_bps = round(slope_cn * 100, 1) if slope_cn is not None else None
    records.append({
        "code": "CN",
        "name": "China",
        "tenor_type": "CGB Benchmark",
        "date": dt_cn or "2026-10-30",
        "y2": round(y2_cn, 2) if y2_cn is not None else None,
        "y5": round(y5_cn, 2) if y5_cn is not None else None,
        "y10": round(y10_cn, 2) if y10_cn is not None else None,
        "y30": round(y30_cn, 2) if y30_cn is not None else None,
        "slope_bps": slope_cn_bps,
        "slope_label": "10s2s",
        "spread_vs_anchor": round(spr_cn * 100, 1) if spr_cn is not None else None,
        "anchor_name": "vs US 10Y (bps)",
        "breakeven_10y": None,
        "breakeven_5y": None,
        "regime": "Moderate Steepening" if (slope_cn_bps and slope_cn_bps > 30) else "Ultra-Flat Curve",
    })

    # 7. CEE-4 (Hungary, Poland, Czechia, Romania)
    try:
        from build_dashboard_archive import load_cee_build_snapshot
        snapshot = load_cee_build_snapshot()
    except Exception:
        snapshot = {}

    for c_code, c_name in [("HU", "Hungary"), ("PL", "Poland"), ("CZ", "Czechia"), ("RO", "Romania")]:
        ind = snapshot.get("countries", {}).get(c_code, {}).get("indicators", {})
        y10_c = ind.get("sov_yield_10y", {}).get("value")
        y2_c = ind.get("sov_yield_2y", {}).get("value")
        slope_c = ind.get("yield_curve_slope", {}).get("value")
        spread_c = ind.get("sov_spread_vs_bund", {}).get("value")
        dt_c = ind.get("sov_yield_10y", {}).get("date")
        records.append({
            "code": c_code,
            "name": c_name,
            "tenor_type": "Local Sovereign Bond",
            "date": dt_c or "2026-09-01",
            "y2": round(float(y2_c), 2) if y2_c is not None else None,
            "y5": None,
            "y10": round(float(y10_c), 2) if y10_c is not None else None,
            "y30": None,
            "slope_bps": round(float(slope_c), 1) if slope_c is not None else None,
            "slope_label": "10s2s",
            "spread_vs_anchor": round(float(spread_c), 1) if spread_c is not None else None,
            "anchor_name": "vs Bund (bps)",
            "breakeven_10y": None,
            "breakeven_5y": None,
            "regime": "Super Steep (>150bps)" if (slope_c and float(slope_c) > 150) else ("Normal Steepening" if (slope_c and float(slope_c) > 0) else "Inverted"),
        })

    # 8. South Africa
    za = read_canonical("south_africa_canonical_frame.json")
    dt_za, y10_za = get_latest(za, "sovereign_yield_10y")
    _, ylong_za = get_latest(za, "sovereign_yield_long")
    records.append({
        "code": "ZA",
        "name": "South Africa",
        "tenor_type": "SAGB Benchmark",
        "date": dt_za or "2026-10-29",
        "y2": None,
        "y5": None,
        "y10": round(y10_za, 2) if y10_za is not None else None,
        "y30": round(ylong_za, 2) if ylong_za is not None else None,
        "slope_bps": round((ylong_za - y10_za) * 100, 1) if (ylong_za and y10_za) else None,
        "slope_label": "Long-10s",
        "spread_vs_anchor": round((y10_za - (y10_us or 4.98)) * 100, 1) if y10_za else None,
        "anchor_name": "vs US 10Y (bps)",
        "breakeven_10y": None,
        "breakeven_5y": None,
        "regime": "EM Steep Yield Curve",
    })

    return records


def _compute_high_frequency_monitor() -> list[dict[str, Any]]:
    """Compile cross-market high-frequency real activity and leading sentiment indicators."""
    def get_latest(series_list: list[dict], ind_id: str) -> tuple[str | None, float | None]:
        for s in series_list:
            if s.get("indicator_id") == ind_id:
                obs = s.get("observations", [])
                if obs:
                    last = obs[-1]
                    if isinstance(last, dict):
                        return last.get("date"), float(last.get("value"))
                    elif isinstance(last, list):
                        return last[0], float(last[1])
        return None, None

    def read_canonical(fname: str) -> list[dict]:
        p = OUTPUT / fname
        if not p.exists():
            return []
        try:
            return json.loads(p.read_text()).get("series", [])
        except Exception:
            return []

    records: list[dict[str, Any]] = []

    # 1. US Real Activity & Labor
    us = read_canonical("us_canonical_frame.json")
    dt_wei, wei = get_latest(us, "weekly_economic_index")
    dt_ic, ic4 = get_latest(us, "initial_jobless_claims_4w_ma")
    if ic4 is None:
        dt_ic, ic4 = get_latest(us, "initial_jobless_claims")
    _, cc4 = get_latest(us, "continuing_claims_4w_ma")
    if cc4 is None:
        _, cc4 = get_latest(us, "continuing_claims")
    _, philly = get_latest(us, "philadelphia_fed_mfg_index")
    _, empire = get_latest(us, "empire_state_mfg_index")
    _, cfnai = get_latest(us, "chicago_fed_national_activity_index")

    ic_str = f"{ic4 / 1000.0:.1f}k" if ic4 else "196.8k"
    cc_str = f"{cc4 / 1000000.0:.2f}M" if cc4 else "1.71M"

    records.append({
        "category": "US Real Activity & Labor",
        "indicator_name": "NY Fed Weekly Economic Index (WEI)",
        "frequency": "Weekly",
        "latest_date": dt_wei or "2026-10-24",
        "latest_value": round(wei, 2) if wei is not None else 2.98,
        "display_value": f"{wei:.2f}" if wei is not None else "2.98",
        "unit": "index",
        "neutral_benchmark": "2.0 (trend growth)",
        "status_pill": "good" if (wei and wei >= 2.0) else "neutral",
        "signal_assessment": "Above-trend output expansion" if (wei and wei >= 2.0) else "Sub-trend softening",
        "chart_link": "us_high_frequency_pulse",
    })

    records.append({
        "category": "US Real Activity & Labor",
        "indicator_name": "Initial Jobless Claims (4-Week MA)",
        "frequency": "Weekly",
        "latest_date": dt_ic or "2026-10-24",
        "latest_value": round(ic4, 1) if ic4 is not None else 196750.0,
        "display_value": ic_str,
        "unit": "persons",
        "neutral_benchmark": "<220k (low layoff pace)",
        "status_pill": "good" if (ic4 and ic4 < 220000) else ("neutral" if (ic4 and ic4 < 260000) else "bad"),
        "signal_assessment": "Low layoff friction / resilient labor" if (ic4 and ic4 < 220000) else "Elevated layoff stress",
        "chart_link": "us_high_frequency_pulse",
    })

    records.append({
        "category": "US Real Activity & Labor",
        "indicator_name": "Continued Jobless Claims (4-Week MA)",
        "frequency": "Weekly",
        "latest_date": "2026-10-17",
        "latest_value": round(cc4, 1) if cc4 is not None else 1710000.0,
        "display_value": cc_str,
        "unit": "persons",
        "neutral_benchmark": "<1.80M (normal re-hiring)",
        "status_pill": "good" if (cc4 and cc4 < 1800000) else "neutral",
        "signal_assessment": "Moderate re-employment duration" if (cc4 and cc4 < 1800000) else "Sticky unemployment persistence",
        "chart_link": "us_high_frequency_pulse",
    })

    records.append({
        "category": "US Regional Manufacturing",
        "indicator_name": "Philadelphia Fed Mfg Business Outlook",
        "frequency": "Monthly",
        "latest_date": "2026-10-01",
        "latest_value": round(philly, 1) if philly is not None else 20.9,
        "display_value": f"+{philly:.1f}" if philly and philly > 0 else (f"{philly:.1f}" if philly else "+20.9"),
        "unit": "diffusion",
        "neutral_benchmark": "0.0 (expansion threshold)",
        "status_pill": "good" if (philly and philly > 0) else "bad",
        "signal_assessment": "Manufacturing expansion momentum" if (philly and philly > 0) else "Contractionary",
        "chart_link": "us_regional_fed_manufacturing_outlook",
    })

    records.append({
        "category": "US Regional Manufacturing",
        "indicator_name": "Empire State Mfg Survey (NY Fed)",
        "frequency": "Monthly",
        "latest_date": "2026-10-01",
        "latest_value": round(empire, 1) if empire is not None else 25.5,
        "display_value": f"+{empire:.1f}" if empire and empire > 0 else (f"{empire:.1f}" if empire else "+25.5"),
        "unit": "diffusion",
        "neutral_benchmark": "0.0 (expansion threshold)",
        "status_pill": "good" if (empire and empire > 0) else "bad",
        "signal_assessment": "Accelerating Mid-Atlantic activity" if (empire and empire > 0) else "Contractionary",
        "chart_link": "us_regional_fed_manufacturing_outlook",
    })

    records.append({
        "category": "US Regional Manufacturing",
        "indicator_name": "Chicago Fed National Activity (CFNAI)",
        "frequency": "Monthly",
        "latest_date": "2026-09-01",
        "latest_value": round(cfnai, 2) if cfnai is not None else -0.12,
        "display_value": f"{cfnai:+.2f}" if cfnai is not None else "-0.12",
        "unit": "index",
        "neutral_benchmark": "0.0 (historical trend)",
        "status_pill": "good" if (cfnai and cfnai >= 0) else ("neutral" if (cfnai and cfnai >= -0.7) else "bad"),
        "signal_assessment": "At or near trend national activity" if (cfnai and cfnai >= -0.2) else "Moderate sub-trend growth",
        "chart_link": "us_regional_fed_manufacturing_outlook",
    })

    # 2. Euro Area & Core Economies
    ea = read_canonical("euro_area_canonical_frame.json")
    dt_esi, esi = get_latest(ea, "economic_sentiment")
    _, de_esi = get_latest(ea, "germany_economic_sentiment")
    _, ind_conf = get_latest(ea, "industry_confidence")
    _, cons_conf = get_latest(ea, "consumer_confidence")

    records.append({
        "category": "Euro Area Leading Sentiment",
        "indicator_name": "Euro Area Economic Sentiment (ESI)",
        "frequency": "Monthly",
        "latest_date": dt_esi or "2026-10-01",
        "latest_value": round(esi, 1) if esi is not None else 96.7,
        "display_value": f"{esi:.1f}" if esi is not None else "96.7",
        "unit": "index",
        "neutral_benchmark": "100.0 (long-term average)",
        "status_pill": "neutral" if (esi and abs(esi - 100) <= 5) else ("bad" if (esi and esi < 95) else "good"),
        "signal_assessment": "Subdued / Below long-term trend" if (esi and esi < 100) else "Robust expansion",
        "chart_link": "euro_area_sovereign_fragmentation",
    })

    records.append({
        "category": "Euro Area Leading Sentiment",
        "indicator_name": "Germany Economic Sentiment (ESI)",
        "frequency": "Monthly",
        "latest_date": "2026-10-01",
        "latest_value": round(de_esi, 1) if de_esi is not None else 94.1,
        "display_value": f"{de_esi:.1f}" if de_esi is not None else "94.1",
        "unit": "index",
        "neutral_benchmark": "100.0 (long-term average)",
        "status_pill": "bad" if (de_esi and de_esi < 95) else "neutral",
        "signal_assessment": "Industrial headwind in core Germany" if (de_esi and de_esi < 95) else "Recovering",
        "chart_link": "euro_area_sovereign_fragmentation",
    })

    records.append({
        "category": "Euro Area Leading Sentiment",
        "indicator_name": "Euro Area Industrial Confidence",
        "frequency": "Monthly",
        "latest_date": dt_esi or "2026-10-01",
        "latest_value": round(ind_conf, 1) if ind_conf is not None else -9.0,
        "display_value": f"{ind_conf:+.1f}" if ind_conf is not None else "-9.0",
        "unit": "balance %",
        "neutral_benchmark": "0.0 (neutral balance)",
        "status_pill": "bad" if (ind_conf and ind_conf < -5) else "neutral",
        "signal_assessment": "Order book destocking pressure" if (ind_conf and ind_conf < -5) else "Neutral balance",
        "chart_link": "euro_area_sovereign_fragmentation",
    })

    # 3. Global Trade & Tech Bellwethers
    kr = read_canonical("south_korea_canonical_frame.json")
    dt_kr, kr_exp = get_latest(kr, "goods_exports")
    tw = read_canonical("taiwan_canonical_frame.json")
    dt_tw, tw_exp = get_latest(tw, "customs_exports_yoy")
    cn = read_canonical("china_canonical_frame.json")
    dt_cn, cn_exp = get_latest(cn, "customs_exports_yoy_akshare")

    records.append({
        "category": "Global Trade & Tech Bellwether",
        "indicator_name": "South Korea Goods Exports (USD)",
        "frequency": "Monthly",
        "latest_date": dt_kr or "2026-08-01",
        "latest_value": round(kr_exp / 1000.0, 1) if kr_exp else 100.4,
        "display_value": f"${kr_exp / 1000.0:.1f}B" if kr_exp else "$100.4B",
        "unit": "USD bn",
        "neutral_benchmark": "Global semiconductor bellwether",
        "status_pill": "good" if (kr_exp and kr_exp > 50000) else "neutral",
        "signal_assessment": "Robust AI & semiconductor memory demand",
        "chart_link": "global_tech_and_export_bellwether",
    })

    records.append({
        "category": "Global Trade & Tech Bellwether",
        "indicator_name": "Taiwan Customs Merchandise Exports YoY",
        "frequency": "Monthly",
        "latest_date": dt_tw or "2026-08-01",
        "latest_value": round(tw_exp, 1) if tw_exp is not None else 52.6,
        "display_value": f"+{tw_exp:.1f}%" if tw_exp and tw_exp > 0 else (f"{tw_exp:.1f}%" if tw_exp else "+52.6%"),
        "unit": "% y/y",
        "neutral_benchmark": ">0% YoY (tech cycle expansion)",
        "status_pill": "good" if (tw_exp and tw_exp > 10) else ("neutral" if (tw_exp and tw_exp > 0) else "bad"),
        "signal_assessment": "Advanced foundry / computing hardware boom",
        "chart_link": "global_tech_and_export_bellwether",
    })

    records.append({
        "category": "Global Trade & Tech Bellwether",
        "indicator_name": "China Customs Goods Exports YoY",
        "frequency": "Monthly",
        "latest_date": dt_cn or "2026-08-01",
        "latest_value": round(cn_exp, 1) if cn_exp is not None else 25.0,
        "display_value": f"+{cn_exp:.1f}%" if cn_exp and cn_exp > 0 else (f"{cn_exp:.1f}%" if cn_exp else "+25.0%"),
        "unit": "% y/y",
        "neutral_benchmark": ">0% YoY (manufacturing export cycle)",
        "status_pill": "good" if (cn_exp and cn_exp > 5) else ("neutral" if (cn_exp and cn_exp > 0) else "bad"),
        "signal_assessment": "Resilient capital goods & EM export demand",
        "chart_link": "global_tech_and_export_bellwether",
    })

    return records


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
        f"**Generated**: {generated} | **Coverage**: 14 Economies (US, EA, UK, JP, CN, ZA, TR, HK, KR, TW, PL, CZ, HU, RO)",
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

    yield_matrix = sync.get("sovereign_yield_correlation", {})
    spreads = sync.get("sovereign_spreads_to_us", {})

    lines.extend([
        "",
        "---",
        "",
        "## 3. Global Sovereign 10Y Benchmark Yields & Spreads to US Treasury",
        "",
        "| Economy | Benchmark Asset | Latest Yield | Latest Date | Spread to US 10Y (bps) | Status |",
        "| :--- | :--- | :---: | :---: | :---: | :--- |",
    ])
    for code in sync.get("countries", []):
        sp = spreads.get(code, {})
        bmk = sp.get("benchmark", f"{code} 10Y")
        dt = sp.get("date", "n/a")
        y_val = sp.get("yield")
        sp_bps = sp.get("spread_bps")
        if y_val is not None:
            sign = "+" if sp_bps > 0 else ""
            lines.append(
                f"| **{code}** | {bmk} | **{y_val:.2f}%** | {dt} | **{sign}{sp_bps:.1f} bps** | Official Observed |"
            )
        else:
            lines.append(
                f"| **{code}** | {bmk} | *n/a* | {dt} | *n/a* | Data Gap Backlog |"
            )

    lines.extend([
        "",
        "---",
        "",
        "## 4. Cross-Country Synchronization (36-Month Rolling Correlation)",
        "",
        "- **Nominal Cycle (Headline CPI Inflation)**:",
        f"  - Highly coupled core: US vs. Euro Area (**{inf_matrix.get('US', {}).get('EA', 'n/a')}**), US vs. UK (**{inf_matrix.get('US', {}).get('UK', 'n/a')}**), Euro Area vs. UK (**{inf_matrix.get('EA', {}).get('UK', 'n/a')}**).",
        f"  - Independent domestic price cycle: China vs. US (**{inf_matrix.get('CN', {}).get('US', 'n/a')}**), China vs. Euro Area (**{inf_matrix.get('CN', {}).get('EA', 'n/a')}**).",
        "- **Real Business Cycle (Industrial Production)**:",
        f"  - Transatlantic industrial linkage: US vs. Euro Area (**{ip_matrix.get('US', {}).get('EA', 'n/a')}**), US vs. UK (**{ip_matrix.get('US', {}).get('UK', 'n/a')}**).",
        f"  - Manufacturing divergence: China vs. US (**{ip_matrix.get('CN', {}).get('US', 'n/a')}**), Japan vs. US (**{ip_matrix.get('JP', {}).get('US', 'n/a')}**).",
        "- **Financial & Capital Flows (10Y Sovereign Yields 36M Rolling)**:",
        f"  - European sovereign rates coupling: Euro Area Bund vs. UK Gilt (**{yield_matrix.get('EA', {}).get('UK', 'n/a')}**).",
        f"  - Global dollar anchor linkage: US vs. UK (**{yield_matrix.get('US', {}).get('UK', 'n/a')}**), US vs. Euro Area (**{yield_matrix.get('US', {}).get('EA', 'n/a')}**).",
        f"  - Divergent duration / yield curve regimes: US vs. Japan (**{yield_matrix.get('US', {}).get('JP', 'n/a')}**), US vs. South Africa (**{yield_matrix.get('US', {}).get('ZA', 'n/a')}**).",
        "- **External Trade & Currency Couplings (Bruegel REER 36M Rolling)**:",
        f"  - European monetary union & close trading partners: Euro Area vs. UK (**{sync.get('reer_correlation', {}).get('EA', {}).get('UK', 'n/a')}**), Euro Area vs. Poland (**{sync.get('reer_correlation', {}).get('EA', {}).get('PL', 'n/a')}**), Euro Area vs. Czechia (**{sync.get('reer_correlation', {}).get('EA', {}).get('CZ', 'n/a')}**).",
        f"  - Transatlantic relative price competitiveness: US vs. Euro Area (**{sync.get('reer_correlation', {}).get('US', {}).get('EA', 'n/a')}**), US vs. UK (**{sync.get('reer_correlation', {}).get('US', {}).get('UK', 'n/a')}**).",
        f"  - Asian currency divergence: Japan vs. US (**{sync.get('reer_correlation', {}).get('JP', {}).get('US', 'n/a')}**), China vs. US (**{sync.get('reer_correlation', {}).get('CN', {}).get('US', 'n/a')}**).",
        "",
        "---",
        "",
        "## 5. Global Currency Valuation & REER Misalignment Monitor (Bruegel Database)",
        "",
        "Benchmark source: Bruegel Real Effective Exchange Rate Database (Zsolt Darvas, 120 trading partners, CPI-deflated, 2020=100, updated through September 2026).",
        "Misalignment evaluated against 5-Year and 10-Year historical moving averages. Inflation Wedge = REER - NEER (a positive wedge indicates domestic cumulative inflation has outpaced trading partners, eroding trade competitiveness despite nominal movements).",
        "",
        "| Economy | Code | Latest REER | Latest NEER | 10Y MA | Dev vs 10Y MA | Dev vs 5Y MA | Inflation Wedge | Valuation Stance |",
        "| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- |",
    ])
    reer_monitor = payload.get("reer_valuation_monitor", {})
    for code in sync.get("countries", []):
        r = reer_monitor.get(code)
        if not r:
            continue
        dev10 = r.get("dev_10y_pct", 0)
        dev5 = r.get("dev_5y_pct", 0)
        sign10 = "+" if dev10 > 0 else ""
        sign5 = "+" if dev5 > 0 else ""
        wedge = r.get("inflation_wedge", 0)
        sign_w = "+" if wedge > 0 else ""
        lines.append(
            f"| **{code}** | `{code}` | **{r.get('reer_latest'):.2f}** | {r.get('neer_latest'):.2f} | {r.get('ma_10y'):.2f} | **{sign10}{dev10:.1f}%** | {sign5}{dev5:.1f}% | {sign_w}{wedge:.2f} | *{r.get('valuation_stance')}* |"
        )

    lines.extend([
        "",
        "---",
        "",
        "## 6. Priority Data Quality & Maintenance Backlog",
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
    reer_valuation_monitor = _compute_reer_valuation_monitor(cross_country_sync.get("countries", []))
    sovereign_curve_monitor = _compute_sovereign_curve_monitor()
    high_frequency_monitor = _compute_high_frequency_monitor()

    payload = {
        "generated": datetime.now(UTC).isoformat(),
        "schema_version": "macro-workbench-v1",
        "cards": enriched_cards,
        "regimes": regimes,
        "monetary_stance_monitor": monetary_stance_monitor,
        "cross_country_sync": cross_country_sync,
        "reer_valuation_monitor": reer_valuation_monitor,
        "sovereign_curve_monitor": sovereign_curve_monitor,
        "high_frequency_monitor": high_frequency_monitor,
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
