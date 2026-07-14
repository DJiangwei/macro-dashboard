from types import SimpleNamespace

from build_china_dashboard import _chart_html, _format_period, _latest
from build_v4 import _chart_latest_reading, _format_chart_reading


def test_data_first_latest_reading_stops_at_latest_actual() -> None:
    series = {
        "id": "real_gdp_growth",
        "label_en": "Real GDP Growth",
        "label_zh": "实际GDP增速",
        "unit": "%",
        "frequency": "annual",
        "actual_through": 2024,
        "quality_status": "verified",
        "source_name": "Official statistics",
        "observations": [
            {"date": "2024-12-31", "value": 5.0},
            {"date": "2025-12-31", "value": 4.5},
        ],
    }

    assert _latest(series) == {"date": "2024-12-31", "value": 5.0}
    html = _chart_html(series, "CN")
    assert "data-latest-reading" in html
    assert "<strong>5.00</strong>" in html
    assert 'meta": "cp-latest-marker"' in html


def test_period_labels_are_frequency_aware_and_bilingual() -> None:
    assert _format_period("2026-03-31", "quarterly", "en") == "Q1 2026"
    assert _format_period("2026-03-31", "quarterly", "zh") == "2026年 Q1"
    assert _format_period("2026-06-01", "monthly", "en") == "Jun 2026"


def test_cee_readout_formats_value_unit_and_period() -> None:
    spec = SimpleNamespace(unit="% YoY", frequency="monthly")
    row = {
        "date": "2026-06-01",
        "value": 2.375,
        "unit": "% YoY",
        "frequency": "monthly",
    }

    html = _chart_latest_reading(row, spec, "chart-prices-cpi")
    assert "data-latest-reading" in html
    assert "2.38" in html
    assert "% YoY" in html
    assert "Jun 2026" in html
    assert "2026年6月" in html
    assert _format_chart_reading(125.0, "bp") == "125"
