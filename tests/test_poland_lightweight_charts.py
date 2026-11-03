from pathlib import Path
import json
import re


ROOT = Path(__file__).resolve().parents[1]
POLAND_HTML = ROOT / "output" / "poland.html"


def test_poland_uses_lightweight_charts_without_plotly():
    html = POLAND_HTML.read_text(encoding="utf-8")
    assert "lightweight-charts@4.2.1/dist/lightweight-charts.standalone.production.js" in html
    assert "plotly-2.32.0.min.js" not in html
    assert "Plotly.newPlot(" not in html


def test_poland_chart_containers_and_lazy_observer_contract():
    html = POLAND_HTML.read_text(encoding="utf-8")
    # 108 macro indicator shells + 4 inflation deep-dive canvases = 112 lightweight-charts plots
    lw_plots = re.findall(r'data-lw-chart="([^"]+)"', html)
    assert len(lw_plots) == 112
    assert len(set(lw_plots)) == 112
    assert html.count('class="chart-cell chart-shell"') == 108
    assert html.count('class="ft-hbar-card"') == 4
    assert "IntersectionObserver" in html
    assert "window.CPChart" in html


def test_poland_compact_date_pool_and_specs_valid():
    html = POLAND_HTML.read_text(encoding="utf-8")
    m_dates = re.search(r"window\.CP_LW_DATES\s*=\s*(\[\[\[.*?\]\]|\[\[.*?\]\]);", html, re.S)
    assert m_dates is not None
    dates = json.loads(m_dates.group(1))
    assert len(dates) > 0
    for date_vec in dates:
        assert date_vec == sorted(date_vec)
        assert len(date_vec) == len(set(date_vec))
        for d in date_vec:
            assert re.match(r"^\d{4}-\d{2}-\d{2}$", d)


def test_poland_cpi_band_bounds_unit_scaling_and_thousands_formatter():
    html = POLAND_HTML.read_text(encoding="utf-8")
    # Thousands formatter registered on LightweightCharts localization
    assert "priceFormatter: formatVal" in html
    assert "toLocaleString('en-US'" in html

    # Extract main 108 chart specs
    matches = list(
        re.finditer(
            r"window\.CP_LW_CHARTS\s*=\s*Object\.assign\(window\.CP_LW_CHARTS\s*\|\|\s*\{\},\s*(\{.*?\})\);",
            html,
            re.S,
        )
    )
    assert len(matches) >= 2
    specs = json.loads(matches[-1].group(1))

    # 1. CPI band explicitly labels Upper 3.5%, Target 2.5%, Lower 1.5% with axisLabel=False (no duplicate 2.5/2.5%)
    cpi_spec = specs["chart-prices_wages-cpi_yoy-01"]
    pl_titles = [pl["title"] for pl in cpi_spec["priceLines"]]
    assert "Upper 3.5%" in pl_titles
    assert "Target 2.5%" in pl_titles
    assert "Lower 1.5%" in pl_titles
    assert all(pl.get("axisLabel") is False for pl in cpi_spec["priceLines"])

    # 2. Large-number series are scaled to thousands / billions without raw 11-zero (abs) traces
    assert specs["chart-demographics-net_migration-05"]["unit"] == "thousands"
    assert specs["chart-real_activity-road_freight_activity-20"]["unit"] == "bn tonne-km"
    assert specs["chart-markets_valuation-portfolio_flows-09"]["unit"] == "EUR bn"
    for cid, sp in specs.items():
        for ser in sp.get("series") or []:
            assert "(abs)" not in ser.get("name", "")
            for val in ser.get("y") or []:
                assert abs(float(val)) < 100_000, f"Unscaled large value {val} in {cid}"
