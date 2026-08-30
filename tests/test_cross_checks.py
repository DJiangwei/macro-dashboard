from country_primer.cross_checks import evaluate_cross_checks

CONFIG = {"cross_checks": [{
    "concept": "headline_inflation", "primary": "a", "secondary": "b",
    "tolerance": 0.15, "label_en": "A vs B",
}]}


def _series(sid: str, points: list[tuple[str, float]]) -> dict:
    return {"id": sid, "observations": [{"date": d, "value": v} for d, v in points],
            "frequency": "monthly", "transform": "level"}


def test_agreeing_sources_report_agree() -> None:
    series = [_series("a", [("2026-06-01", 4.3), ("2026-07-01", 5.0)]),
              _series("b", [("2026-06-01", 4.31), ("2026-07-01", 5.02)])]
    result = evaluate_cross_checks(CONFIG, series)[0]
    assert result["n_common"] == 2
    assert result["n_breaches"] == 0
    assert result["status"] == "agree"


def test_breach_beyond_tolerance_reports_diverged() -> None:
    series = [_series("a", [("2026-06-01", 4.3), ("2026-07-01", 5.0)]),
              _series("b", [("2026-06-01", 4.31), ("2026-07-01", 5.9)])]
    result = evaluate_cross_checks(CONFIG, series)[0]
    assert result["n_breaches"] == 1
    assert result["last_breach_date"] == "2026-07-01"
    assert result["status"] == "diverged"
    assert round(result["latest_diff"], 2) == -0.90


def test_no_overlap_reports_insufficient() -> None:
    series = [_series("a", [("2026-06-01", 4.3)]), _series("b", [("2025-01-01", 4.0)])]
    assert evaluate_cross_checks(CONFIG, series)[0]["status"] == "insufficient"


def test_missing_member_is_skipped_not_crashed() -> None:
    assert evaluate_cross_checks(CONFIG, [_series("a", [("2026-06-01", 4.3)])]) == []


def test_breach_outside_default_window_reports_agree_but_keeps_full_history_count() -> None:
    # 2020-01-01 breaches by 4.0, but it's ~78 months before the latest common
    # date (2026-07-01), far outside the default 24-month window. The two
    # in-window points (2025-07-01, 2026-07-01) agree closely.
    series = [_series("a", [("2020-01-01", 1.0), ("2025-07-01", 5.0), ("2026-07-01", 5.0)]),
              _series("b", [("2020-01-01", 5.0), ("2025-07-01", 5.02), ("2026-07-01", 5.01)])]
    result = evaluate_cross_checks(CONFIG, series)[0]
    assert result["status"] == "agree"
    assert result["n_breaches"] == 1
    assert result["last_breach_date"] == "2020-01-01"
    assert result["n_common"] == 3
    assert result["window_n_breaches"] == 0
    assert result["window_n_common"] == 2


def test_breach_inside_default_window_reports_diverged() -> None:
    # The only breach (2026-07-01, diff 1.0) is the most recent point, so it
    # falls inside the default 24-month window regardless of older history.
    series = [_series("a", [("2020-01-01", 5.0), ("2025-07-01", 5.0), ("2026-07-01", 6.0)]),
              _series("b", [("2020-01-01", 5.0), ("2025-07-01", 5.02), ("2026-07-01", 5.0)])]
    result = evaluate_cross_checks(CONFIG, series)[0]
    assert result["status"] == "diverged"
    assert result["window_n_breaches"] == 1
    assert result["window_n_common"] == 2


def test_explicit_since_overrides_default_window() -> None:
    config = {"cross_checks": [{
        "concept": "headline_inflation", "primary": "a", "secondary": "b",
        "tolerance": 0.15, "label_en": "A vs B", "since": "2025-01-01",
    }]}
    # The breach (2024-06-01) is well within the default 24-month window
    # relative to the latest common date (2026-01-01), but the explicit
    # since=2025-01-01 excludes it.
    series = [_series("a", [("2024-06-01", 1.0), ("2025-06-01", 5.0), ("2026-01-01", 5.0)]),
              _series("b", [("2024-06-01", 5.0), ("2025-06-01", 5.02), ("2026-01-01", 5.01)])]
    result = evaluate_cross_checks(config, series)[0]
    assert result["status"] == "agree"
    assert result["window_since"] == "2025-01-01"
    assert result["window_n_common"] == 2
