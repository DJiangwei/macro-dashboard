"""Regression coverage for finding #2 of the whole-branch review: `yoy_pct`
(US) / `yoy` (UK) — and the sibling `qoq_pct`/`mom_pct`/`pct_change`/`diff`
transforms — stepped back a fixed number of *array indices* rather than
checking the base observation is actually that many *calendar* periods
earlier. A single interior gap (e.g. a missing October) silently turned a
"YoY" reading into a 13-month change with no signal that anything was wrong.

The fix (`dashboard_summary_utils.calendar_gap_matches`, wired into both
`build_us_dashboard._apply_transform` and `build_uk_dashboard._apply_transform`)
verifies the base observation's date before using it and skips the point on
a mismatch, per the project rule: never fabricate, interpolate, or
substitute a missing economic reading — a skipped point is an honest gap.

Japan's `build_japan_dashboard.py` imports `_apply_transform` directly from
`build_us_dashboard`, so fixing the shared function also protects Japan's
`producer_price_inflation` (Bank of Japan CGPI) against a silently
suppressed month from `parse_boj_wide_csv`.

These tests must stay offline and deterministic — no live FRED/BOJ calls.
"""
from __future__ import annotations

from datetime import date

from dashboard_summary_utils import calendar_gap_matches


def test_calendar_gap_matches_monthly() -> None:
    assert calendar_gap_matches("monthly", 12, date(2024, 11, 1), date(2025, 11, 1))
    assert not calendar_gap_matches("monthly", 12, date(2024, 10, 1), date(2025, 11, 1))
    assert calendar_gap_matches("monthly", 1, date(2025, 9, 1), date(2025, 10, 1))


def test_calendar_gap_matches_quarterly() -> None:
    assert calendar_gap_matches("quarterly", 4, date(2024, 6, 30), date(2025, 6, 30))
    assert not calendar_gap_matches("quarterly", 4, date(2024, 3, 31), date(2025, 6, 30))
    assert calendar_gap_matches("quarterly", 1, date(2025, 3, 31), date(2025, 6, 30))


def test_calendar_gap_matches_weekly_and_annual() -> None:
    assert calendar_gap_matches("weekly", 52, date(2024, 8, 1), date(2025, 7, 31))
    assert not calendar_gap_matches("weekly", 52, date(2024, 8, 1), date(2025, 8, 8))
    assert calendar_gap_matches("annual", 1, date(2023, 12, 31), date(2024, 12, 31))
    assert not calendar_gap_matches("annual", 1, date(2022, 12, 31), date(2024, 12, 31))


def _monthly_series(transform: str, dates_values: list[tuple[str, float]]) -> dict:
    return {
        "transform": transform,
        "frequency": "monthly",
        "observations": [{"date": d, "value": v} for d, v in dates_values],
    }


def test_us_yoy_pct_skips_a_point_stranded_by_an_interior_gap() -> None:
    from build_us_dashboard import _apply_transform

    values = [(f"2024-{m:02d}-01", 100.0 + m) for m in range(1, 13)]
    values += [("2025-01-01", 120.0), ("2025-02-01", 121.0), ("2025-04-01", 123.0)]  # no 2025-03
    result = _apply_transform(_monthly_series("yoy_pct", values))
    out_dates = [o["date"] for o in result["observations"]]
    assert "2025-04-01" not in out_dates, "13-month change must not be emitted as YoY"
    assert out_dates[-1] == "2025-02-01"


def test_us_pct_change_skips_a_point_stranded_by_an_interior_gap() -> None:
    from build_us_dashboard import _apply_transform

    values = [("2025-08-01", 100.0), ("2025-09-01", 101.0), ("2025-11-01", 103.0)]  # no 2025-10
    result = _apply_transform(_monthly_series("pct_change", values))
    out_dates = [o["date"] for o in result["observations"]]
    assert "2025-11-01" not in out_dates, "2-month change must not be emitted as MoM"
    assert out_dates == ["2025-09-01"]


def test_us_diff_skips_a_point_stranded_by_an_interior_gap() -> None:
    from build_us_dashboard import _apply_transform

    values = [("2025-08-01", 100.0), ("2025-09-01", 101.0), ("2025-11-01", 103.0)]  # no 2025-10
    result = _apply_transform(_monthly_series("diff", values))
    out_dates = [o["date"] for o in result["observations"]]
    assert out_dates == ["2025-09-01"]


def test_us_yoy_pct_is_unaffected_when_the_series_is_contiguous() -> None:
    from build_us_dashboard import _apply_transform

    values = [(f"2024-{m:02d}-01", 100.0 + m) for m in range(1, 13)]
    values += [(f"2025-{m:02d}-01", 120.0 + m) for m in range(1, 4)]
    result = _apply_transform(_monthly_series("yoy_pct", values))
    out_dates = [o["date"] for o in result["observations"]]
    assert out_dates == ["2025-01-01", "2025-02-01", "2025-03-01"]


def test_uk_yoy_skips_a_point_stranded_by_an_interior_gap() -> None:
    """build_uk_dashboard.py has its own `_apply_transform` (different
    vocabulary: "yoy"/"qoq_pct"/"mom_pct") with the identical index-lag
    defect as the US version — it must get the same calendar-gap guard."""
    from build_uk_dashboard import _apply_transform as uk_apply_transform

    observations = [{"date": f"2024-{m:02d}-01", "value": 100.0 + m} for m in range(1, 13)]
    observations += [
        {"date": "2025-01-01", "value": 120.0},
        {"date": "2025-02-01", "value": 121.0},
        {"date": "2025-04-01", "value": 123.0},  # no 2025-03
    ]
    result = uk_apply_transform(observations, {"transform": "yoy", "frequency": "monthly"})
    out_dates = [o["date"] for o in result]
    assert "2025-04-01" not in out_dates
    assert out_dates[-1] == "2025-02-01"


def test_uk_mom_pct_matches_ons_monthly_gdp_growth_on_a_contiguous_series() -> None:
    """Confirms the MGDP/ECY2 repoint (finding #1) produces sane MoM growth
    once fed through the shared UK transform, and that the calendar-gap
    guard is a no-op on a genuinely contiguous monthly series."""
    from build_uk_dashboard import _apply_transform as uk_apply_transform

    observations = [
        {"date": "2026-01-01", "value": 102.3},
        {"date": "2026-02-01", "value": 102.8},
        {"date": "2026-03-01", "value": 103.2},
        {"date": "2026-04-01", "value": 103.1},
        {"date": "2026-05-01", "value": 103.1},
        {"date": "2026-06-01", "value": 103.4},
    ]
    result = uk_apply_transform(observations, {"transform": "mom_pct", "frequency": "monthly"})
    out = {o["date"]: round(o["value"], 1) for o in result}
    assert out["2026-06-01"] == 0.3  # matches the ONS-published "Monthly GDP grew by 0.3% in June 2026"


def test_japan_cgpi_yoy_survives_a_boj_suppressed_month() -> None:
    """Japan's producer_price_inflation reuses build_us_dashboard._apply_transform
    (imported directly by build_japan_dashboard.py). A BOJ flat file that
    silently drops one non-numeric month (see parse_boj_wide_csv) must not
    misalign the YoY reading it feeds."""
    from build_us_dashboard import _apply_transform
    from country_primer.adapters import parse_boj_wide_csv

    header = "202301,202302,202303,202304,202305,202306,202307,202308,202309,202310,202311,202312"
    # 202401 (13th column) is deliberately non-numeric -> parse_boj_wide_csv
    # drops it, leaving a gap between 2023-12 and 2024-02.
    values_2023 = ",".join(f"{100 + i}" for i in range(12))
    text = (
        f",,,{header},202401,202402\n"
        f"CODE,\"CGPI\",\"All commodities\",{values_2023},NA,113.0\n"
    )
    obs = parse_boj_wide_csv(text, "CODE")
    assert [o["date"] for o in obs[-3:]] == ["2023-11-01", "2023-12-01", "2024-02-01"]

    series = {"transform": "yoy_pct", "frequency": "monthly", "observations": obs}
    result = _apply_transform(series)
    out_dates = [o["date"] for o in result["observations"]]
    # A YoY point for 2024-02 would need a 2023-02 base 12 months back; the
    # gap means index-12 no longer lands on a calendar-aligned base, so it
    # must be skipped rather than silently computed from the wrong month.
    assert "2024-02-01" not in out_dates
