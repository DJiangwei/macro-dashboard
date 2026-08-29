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
