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


def _series_with_quality(**overrides: object) -> dict:
    series: dict = {
        "id": "cpi_inflation",
        "label_en": "Headline CPI, YoY",
        "label_zh": "总体CPI同比",
        "unit": "% y/y",
        "frequency": "monthly",
        "quality_status": "watch",
        "source_name": "IMF SDMX / CPI",
        "data_quality": {
            "source_authority": "official_mirror",
            "freshness": "current",
            "derivation": "observed",
            "comparability": "national",
            "status": "watch",
        },
        "observations": [
            {"date": "2026-06-01", "value": 3.5},
        ],
    }
    series.update(overrides)
    return series


def test_chart_html_renders_authority_and_freshness_chips_from_data_quality() -> None:
    html = _chart_html(_series_with_quality(), "JP")
    assert 'class="authority-chip"' in html
    assert 'class="freshness-chip"' in html
    assert ">official mirror<" in html
    assert ">current<" in html
    # The coarse pill must still be present alongside the new chips, not replaced.
    assert 'class="quality-pill"' in html
    assert ">watch<" in html


def test_chart_html_handles_missing_data_quality_without_erroring() -> None:
    series = _series_with_quality()
    del series["data_quality"]
    html = _chart_html(series, "JP")
    assert 'class="authority-chip"></span>' in html
    assert 'class="freshness-chip"></span>' in html


def test_chart_html_renders_cross_check_agreement_with_history_context() -> None:
    series = _series_with_quality(cross_check={
        "concept": "headline_inflation",
        "primary": "cpi_inflation_estat",
        "secondary": "cpi_inflation",
        "label_en": "e-Stat vs IMF headline CPI",
        "n_common": 378,
        "latest_diff": -0.10098478066248884,
        "max_abs_diff": 0.4120922946692388,
        "n_breaches": 24,
        "last_breach_date": "2020-10-01",
        "tolerance": 0.15,
        "window_since": "2024-06-01",
        "window_months": 24,
        "window_n_common": 25,
        "window_max_abs_diff": 0.10098478066248884,
        "window_n_breaches": 0,
        "status": "minor",
    })
    html = _chart_html(series, "JP")
    assert 'class="cross-check"' in html
    assert "e-Stat vs IMF headline CPI" in html
    # Windowed verdict (agrees now) is the headline...
    assert "Agrees" in html
    # ...but the full-history breach record must still be visible as context.
    assert "24" in html and "378" in html


def test_chart_html_renders_cross_check_divergence_when_window_breaches() -> None:
    series = _series_with_quality(cross_check={
        "concept": "headline_inflation",
        "primary": "a",
        "secondary": "b",
        "label_en": "A vs B",
        "n_common": 100,
        "latest_diff": 0.9,
        "max_abs_diff": 0.9,
        "n_breaches": 5,
        "last_breach_date": "2026-05-01",
        "tolerance": 0.15,
        "window_since": "2024-06-01",
        "window_months": 24,
        "window_n_common": 25,
        "window_max_abs_diff": 0.9,
        "window_n_breaches": 3,
        "status": "diverged",
    })
    html = _chart_html(series, "JP")
    assert 'class="cross-check diverged"' in html
    assert "Diverges" in html


def test_chart_html_renders_cross_check_insufficient_without_crashing() -> None:
    # `latest_diff` and `last_breach_date` may be None/empty when there are no
    # common observations at all; this must not raise when formatting the line.
    series = _series_with_quality(cross_check={
        "concept": "headline_inflation",
        "primary": "a",
        "secondary": "b",
        "label_en": "A vs B",
        "n_common": 0,
        "latest_diff": None,
        "max_abs_diff": 0.0,
        "n_breaches": 0,
        "last_breach_date": "",
        "tolerance": 0.15,
        "window_since": None,
        "window_months": None,
        "window_n_common": 0,
        "window_max_abs_diff": 0.0,
        "window_n_breaches": 0,
        "status": "insufficient",
    })
    html = _chart_html(series, "JP")
    assert 'class="cross-check"' in html
    assert "cross-check diverged" not in html


def test_chart_html_omits_cross_check_line_when_absent() -> None:
    html = _chart_html(_series_with_quality(), "JP")
    assert "cross-check" not in html.lower()


def test_chart_cards_show_source_authority_and_freshness() -> None:
    html = open("output/japan.html").read()
    assert 'class="authority-chip"' in html
    assert "official primary" in html or "official mirror" in html
    assert 'class="freshness-chip"' in html


def test_page_header_shows_provenance_mix() -> None:
    html = open("output/japan.html").read()
    assert "native official" in html


def test_cross_check_line_renders_on_paired_charts() -> None:
    html = open("output/south_africa.html").read()
    assert 'class="cross-check' in html
