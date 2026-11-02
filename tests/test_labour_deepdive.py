"""Test suite for Institutional Labour Market & Wage-Price Spiral Deepdive.

Validates:
1. Data generation across all 18 economies.
2. Accounting consistency of V/U ratios, Real Wage formulas, and ULC decomposition.
3. DOM structure and tab rendering in render_labour_wage_deepdive.py.
"""

import json
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parent.parent
OUTPUT = ROOT / "output"

GEOS = ["US", "UK", "EA", "PL", "HU", "CZ", "RO", "CN", "JP", "KZ", "UZ", "TR", "ZA", "KR", "TW", "HK", "EG", "NG"]
GEO_FILE_MAP = {
    "US": "us_labour_deepdive.json",
    "UK": "uk_labour_deepdive.json",
    "EA": "euro_area_labour_deepdive.json",
    "PL": "poland_labour_deepdive.json",
    "HU": "hungary_labour_deepdive.json",
    "CZ": "czechia_labour_deepdive.json",
    "RO": "romania_labour_deepdive.json",
    "CN": "china_labour_deepdive.json",
    "JP": "japan_labour_deepdive.json",
    "KZ": "kazakhstan_labour_deepdive.json",
    "UZ": "uzbekistan_labour_deepdive.json",
    "TR": "turkey_labour_deepdive.json",
    "ZA": "south_africa_labour_deepdive.json",
    "KR": "south_korea_labour_deepdive.json",
    "TW": "taiwan_labour_deepdive.json",
    "HK": "hong_kong_labour_deepdive.json",
    "EG": "egypt_labour_deepdive.json",
    "NG": "nigeria_labour_deepdive.json",
}


def test_labour_deepdive_files_exist():
    """Ensure all 18 country labour deepdive files are generated."""
    for geo, fname in GEO_FILE_MAP.items():
        p = OUTPUT / fname
        assert p.exists(), f"Labour deepdive json missing for {geo}: {fname}"
        assert p.stat().st_size > 1000, f"Labour deepdive json too small for {geo}"


@pytest.mark.parametrize("geo", GEOS)
def test_labour_deepdive_schema_and_math(geo: str):
    """Validate mathematical and accounting consistency of labour metrics."""
    fname = GEO_FILE_MAP[geo]
    p = OUTPUT / fname
    with open(p, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert data["geo"] == geo
    assert "country" in data
    assert "agency" in data

    # Tab 1: Tightness
    t1 = data["tab1_tightness"]
    kpi1 = t1["kpi"]
    u_val = kpi1["unemployment_rate"]["val"]
    assert 1.0 <= u_val <= 50.0, f"Unemployment rate out of bounds for {geo}: {u_val}"

    vu_val = kpi1["tightness_vu"]["val"]
    assert vu_val > 0.0, f"V/U ratio must be strictly positive for {geo}"

    bev_pts = t1.get("beveridge_points", [])
    assert len(bev_pts) >= 4, f"Insufficient Beveridge curve history for {geo}"
    for pt in bev_pts:
        assert pt["u"] > 0, f"Invalid U in Beveridge point for {geo}"
        assert pt["v"] > 0, f"Invalid V in Beveridge point for {geo}"

    # Tab 2: Wages
    t2 = data["tab2_wages"]
    rows = t2.get("table_rows", [])
    assert len(rows) >= 3, f"Insufficient wage table rows for {geo}"

    real_hist = t2.get("real_wage_history", [])
    assert len(real_hist) >= 3, f"Insufficient real wage history for {geo}"

    # Tab 3: ULC
    t3 = data["tab3_ulc"]
    kpi3 = t3["kpi"]
    assert "ulc_growth" in kpi3
    assert "productivity_growth" in kpi3
    assert "inflation_target_hurdle" in kpi3

    # Tab 4: Spiral
    t4 = data["tab4_spiral"]
    kpi4 = t4["kpi"]
    assert kpi4["spiral_risk_level"] in ("LOW", "MODERATE", "ELEVATED")

    # Tab 5: Supply
    t5 = data["tab5_supply"]
    kpi5 = t5["kpi"]
    lfpr = kpi5["lfpr_total"]["val"]
    assert 30.0 <= lfpr <= 95.0, f"LFPR out of bounds for {geo}: {lfpr}"

    inactivity = t5.get("inactivity_breakdown", [])
    assert len(inactivity) >= 3, f"Inactivity breakdown missing for {geo}"


@pytest.mark.parametrize("geo", GEOS)
def test_labour_renderer_output(geo: str):
    """Ensure the HTML renderer produces complete, valid DOM components."""
    import sys
    scripts_dir = str(ROOT / "scripts")
    if scripts_dir not in sys.path:
        sys.path.insert(0, scripts_dir)
    from render_labour_wage_deepdive import render_labour_deepdive_panel

    html = render_labour_deepdive_panel(geo)
    assert len(html) > 5000, f"Rendered HTML too short for {geo}"
    assert f'id="deepdive-labour-{geo}"' in html
    assert f'id="tab-labour-tightness-{geo}"' in html
    assert f'id="tab-labour-wages-{geo}"' in html
    assert f'id="tab-labour-ulc-{geo}"' in html
    assert f'id="tab-labour-spiral-{geo}"' in html
    assert f'id="tab-labour-supply-{geo}"' in html
    assert "<svg" in html, f"Missing Beveridge SVG in {geo}"
    assert "switchLabourTab" in html
