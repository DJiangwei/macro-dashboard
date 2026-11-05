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

from country_primer.scopes import data_first_scopes

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
SCOPE_FRAMES = {scope.id: scope.slug for scope in data_first_scopes()}


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


# Files that compute or display data. Numeric fallbacks here would put an
# invented number on a page whenever a real value is missing.
ANALYTIC_FILES = sorted({
    *SCRIPTS.glob("enrich_*.py"),
    *SCRIPTS.glob("render_*.py"),
    SCRIPTS / "macro_workbench.py",
    SCRIPTS / "real_deepdives.py",
    SCRIPTS / "build_policy_tracker.py",
})
# (file name, source segment) pairs reviewed as non-data defaults.
FALLBACK_ALLOWLIST = {
    ("build_policy_tracker.py", "chg if chg is not None else 0"),  # sort key only; display shows "—"
    ("render_cee_inflation_deepdive.py", "pct if pct is not None else 0"),  # CSS bar width: hidden when missing
    ("render_us_inflation_deepdive.py", "pct if pct is not None else 0"),  # CSS bar width: hidden when missing
}


def _is_none_check(test: ast.AST) -> bool:
    """`x is not None` / `x is None` style guards (also inside `and`/`or`)."""
    nodes = test.values if isinstance(test, ast.BoolOp) else [test]
    return any(
        isinstance(n, ast.Compare)
        and any(isinstance(op, (ast.Is, ast.IsNot)) for op in n.ops)
        and any(isinstance(c, ast.Constant) and c.value is None for c in n.comparators)
        for n in nodes
    )


def _number_value(node: ast.AST) -> float:
    if isinstance(node, ast.UnaryOp):
        return -node.operand.value
    return node.value


def _numeric_fallbacks(path: Path) -> list[str]:
    source = path.read_text()
    tree = ast.parse(source)
    found = []
    for node in ast.walk(tree):
        segment = None
        if isinstance(node, ast.IfExp) and _is_number(node.orelse) and _is_none_check(node.test):
            segment = ast.get_source_segment(source, node)
        elif (
            isinstance(node, ast.BoolOp) and isinstance(node.op, ast.Or) and _is_number(node.values[-1])
            and _number_value(node.values[-1]) not in (0, 1)
        ):
            segment = ast.get_source_segment(source, node)
        elif isinstance(node, ast.BoolOp) and isinstance(node.op, ast.Or):
            last = node.values[-1]
            if isinstance(last, ast.Constant) and isinstance(last.value, str) and DATE.match(last.value):
                segment = ast.get_source_segment(source, node)
        elif isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "get" and len(node.args) == 2:
            default = node.args[1]
            if isinstance(default, ast.Constant) and isinstance(default.value, str) and DATE.match(default.value):
                segment = ast.get_source_segment(source, node)
        if segment and (path.name, segment) not in FALLBACK_ALLOWLIST:
            found.append(f"{path.name}:{node.lineno}: {segment[:90]}")
    return found


def test_no_invented_fallback_values_in_analytics():
    offenders = [hit for path in ANALYTIC_FILES for hit in _numeric_fallbacks(path)]
    assert not offenders, "Missing data must stay missing, not become a number or date: " + "; ".join(offenders)
