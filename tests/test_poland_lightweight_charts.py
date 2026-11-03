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
