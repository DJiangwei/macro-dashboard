"""Data-integrity guards added after the 2026-11-05 audit.

These tests fail the build when code starts hand-typing observations again,
when a build step edits configuration, when a page's policy rate drifts from
the BIS feed, or when a growth concept is mapped to a level series.
"""
from __future__ import annotations

import ast
import json
import re
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
OUTPUT = ROOT / "output"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

DATE = re.compile(r"^\d{4}(-\d{2}(-\d{2})?|-Q[1-4])?$")


def _python_sources() -> list[Path]:
    return sorted([*SCRIPTS.glob("*.py"), *(ROOT / "src").rglob("*.py"), ROOT / "build_v4.py"])


def _is_number(node: ast.AST) -> bool:
    if isinstance(node, ast.UnaryOp):
        node = node.operand
    return isinstance(node, ast.Constant) and isinstance(node.value, (int, float)) and not isinstance(node.value, bool)


def _is_dated_point(node: ast.AST) -> bool:
    if isinstance(node, (ast.List, ast.Tuple)) and len(node.elts) == 2:
        first, second = node.elts
        return (
            isinstance(first, ast.Constant) and isinstance(first.value, str)
            and bool(DATE.match(first.value)) and _is_number(second)
        )
    if isinstance(node, ast.Dict):
        pairs = {k.value: v for k, v in zip(node.keys, node.values) if isinstance(k, ast.Constant)}
        date_node = pairs.get("date")
        return (
            isinstance(date_node, ast.Constant) and isinstance(date_node.value, str)
            and bool(DATE.match(date_node.value))
            and any(_is_number(v) for k, v in pairs.items() if k != "date")
        )
    return False


def test_no_hand_typed_dated_series_in_code():
    """A literal list of >=3 (date, number) points is a hand-typed time series."""
    offenders = []
    for path in _python_sources():
        tree = ast.parse(path.read_text())
        for node in ast.walk(tree):
            if isinstance(node, (ast.List, ast.Tuple)) and len(node.elts) >= 3:
                if sum(bool(_is_dated_point(e)) for e in node.elts) >= 3:
                    offenders.append(f"{path.relative_to(ROOT)}:{node.lineno}")
    assert not offenders, "Hand-typed dated series found (fetch or document as a gap instead): " + ", ".join(offenders)


def test_build_steps_do_not_write_configuration():
    offenders = []
    for path in _python_sources():
        source = path.read_text()
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr in {"write_text", "write_bytes"}:
                target = ast.get_source_segment(source, node.func.value) or ""
                if re.search(r"config|CONFIG|framework_v2|fw_path", target):
                    offenders.append(f"{path.relative_to(ROOT)}:{node.lineno} ({target})")
    assert not offenders, "Build code must not modify configuration: " + ", ".join(offenders)


def test_policy_rates_match_bis_snapshot():
    snapshot_path = OUTPUT / "bis_policy_rates.json"
    if not snapshot_path.exists():
        pytest.skip("BIS snapshot not built yet")
    from build_policy_tracker import POLICY_INPUTS, _date_of, _frame_series, _in_force

    bis = json.loads(snapshot_path.read_text())
    cache: dict = {}
    mismatches = []
    for code, entry in (bis.get("scopes") or {}).items():
        if code not in POLICY_INPUTS:
            continue
        frame_name, policy_ids, _ = POLICY_INPUTS[code]
        series = _frame_series(frame_name, code, cache)
        policy = next((series[i] for i in policy_ids if series.get(i, {}).get("observations")), None)
        assert policy, f"{code}: no policy-rate series on the page"
        on = _date_of(entry["last_observation_date"])
        page_rate = _in_force(policy["observations"], on)
        if code == "US":
            lower = _in_force(series.get("fed_target_lower", {}).get("observations") or [], on)
            page_rate = (page_rate + lower) / 2 if page_rate is not None and lower is not None else page_rate
        if page_rate is None:
            continue
        if abs(page_rate - float(entry["latest_value"])) > 0.051:
            mismatches.append(f"{code}: page {page_rate} vs BIS {entry['latest_value']} on {entry['last_observation_date']}")
    assert not mismatches, "Policy rates differ from BIS WS_CBPOL: " + "; ".join(mismatches)


GROWTH_CONCEPTS = {
    "real_gdp_growth_qoq", "real_gdp_growth_yoy", "nominal_gdp_growth", "consumption_growth", "investment_growth",
    "industrial_production_growth", "retail_sales_growth", "employment_growth", "wage_growth", "real_income_growth",
    "headline_inflation", "core_inflation", "services_inflation", "goods_inflation", "producer_price_inflation",
    "wage_cost_inflation", "house_price_growth", "exports_growth", "imports_growth", "broad_money_growth",
    "private_credit_growth",
}
# Flow changes in employment are an accepted proxy for employment growth.
GROWTH_LEVEL_ALLOWLIST = {("US", "nonfarm_payrolls_change"), ("UK", "paye_payrolled_employees_mom_change")}
SCOPE_FRAMES = {
    "CN": "china", "UK": "uk", "US": "us", "JP": "japan", "ZA": "south_africa", "EA": "euro_area", "TR": "turkey",
    "HK": "hong_kong", "KR": "south_korea", "TW": "taiwan", "KZ": "kazakhstan", "UZ": "uzbekistan",
    "EG": "egypt", "NG": "nigeria",
}


def test_growth_concepts_are_not_mapped_to_level_series():
    framework = yaml.safe_load((ROOT / "config" / "framework_v2.yaml").read_text())
    units: dict[str, dict[str, tuple[str, str]]] = {}
    for scope, slug in SCOPE_FRAMES.items():
        path = OUTPUT / f"{slug}_canonical_frame.json"
        if path.exists():
            payload = json.loads(path.read_text())
            units[scope] = {s["indicator_id"]: (str(s.get("unit") or ""), str(s.get("transform") or "")) for s in payload["series"]}
    offenders = []
    for concept in framework["concepts"]:
        if concept["id"] not in GROWTH_CONCEPTS:
            continue
        for scope, ids in (concept.get("mappings") or {}).items():
            for indicator_id in ids or []:
                unit, transform = units.get(scope, {}).get(indicator_id, ("%", ""))
                is_rate = "%" in unit or "pct" in unit.lower() or transform in {"yoy_pct", "yoy", "pct_change"}
                if not is_rate and (scope, indicator_id) not in GROWTH_LEVEL_ALLOWLIST:
                    offenders.append(f"{concept['id']} <- {scope}:{indicator_id} [{unit}]")
    assert not offenders, "Growth concepts mapped to level series: " + "; ".join(offenders)
