"""Regression coverage for finding #2 of the whole-branch review: `yoy_pct`
(US) / `yoy` (UK) — and the sibling `qoq_pct`/`mom_pct`/`pct_change`/`diff`
transforms — stepped back a fixed number of *array indices* rather than
looking up the base observation by calendar date. A single interior gap
(e.g. BLS never publishing October 2025 CPI during the government shutdown)
silently turned every later "YoY" reading into a 13-month change with no
signal that anything was wrong — and because the misalignment was an array
*offset*, it did not just affect the point next to the gap: every later
point inherited the same one-slot drift, forever.

The fix (`dashboard_summary_utils.shift_calendar_periods`, wired into both
`build_us_dashboard._apply_transform` and `build_uk_dashboard._apply_transform`)
looks up the base observation by its exact expected calendar date instead of
a fixed array offset. This makes the series self-healing: only the specific
point whose own calendar-aligned base is itself missing gets skipped (an
honest gap); every other point — including everything after the gap —
computes correctly once its own base date exists. Per the project rule,
never fabricate, interpolate, or substitute a missing reading: a skipped
point is the honest outcome exactly where no aligned base exists at all.

Japan's `build_japan_dashboard.py` imports `_apply_transform` directly from
`build_us_dashboard`, so fixing the shared function also protects Japan's
`producer_price_inflation` (Bank of Japan CGPI) against a silently
suppressed month from `parse_boj_wide_csv`.

These tests must stay offline and deterministic — no live FRED/BOJ calls.
"""
from __future__ import annotations

from datetime import date

from dashboard_summary_utils import calendar_gap_matches, shift_calendar_periods


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


def test_shift_calendar_periods_monthly_and_quarterly() -> None:
    assert shift_calendar_periods(date(2025, 11, 1), "monthly", 12) == date(2024, 11, 1)
    assert shift_calendar_periods(date(2026, 2, 1), "monthly", 1) == date(2026, 1, 1)
    assert shift_calendar_periods(date(2025, 6, 30), "quarterly", 4) == date(2024, 6, 30)
    assert shift_calendar_periods(date(2025, 6, 30), "quarterly", 1) == date(2025, 3, 30)


def test_shift_calendar_periods_weekly_and_annual() -> None:
    assert shift_calendar_periods(date(2025, 8, 8), "weekly", 52) == date(2024, 8, 9)
    assert shift_calendar_periods(date(2024, 12, 31), "annual", 1) == date(2023, 12, 31)


def _monthly_series(transform: str, dates_values: list[tuple[str, float]]) -> dict:
    return {
        "transform": transform,
        "frequency": "monthly",
        "observations": [{"date": d, "value": v} for d, v in dates_values],
    }


def test_us_yoy_pct_skips_only_the_point_whose_own_base_is_missing() -> None:
    """2024-04 is missing from the raw series. Only 2025-04's YoY (which
    needs exactly 2024-04 as its base) must be skipped; 2025-03 and 2025-05
    — whose own bases (2024-03, 2024-05) are present — must compute
    normally. This is the key behavioural difference from a naive
    array-offset fix: a single missing month must not take out every later
    reading, only the one reading that genuinely has no year-ago comparator.
    """
    from build_us_dashboard import _apply_transform

    values = [(f"2024-{m:02d}-01", 100.0 + m) for m in range(1, 13) if m != 4]  # no 2024-04
    values += [(f"2025-{m:02d}-01", 120.0 + m) for m in range(1, 6)]  # 2025-01..2025-05
    result = _apply_transform(_monthly_series("yoy_pct", values))
    out = {o["date"]: o["value"] for o in result["observations"]}
    assert "2025-04-01" not in out, "2024-04 base is missing; 2025-04 YoY has no valid comparator"
    assert out["2025-03-01"] == ((123.0 / 103.0) - 1.0) * 100.0
    assert out["2025-05-01"] == ((125.0 / 105.0) - 1.0) * 100.0


def test_us_yoy_pct_self_heals_after_an_interior_gap_instead_of_drifting_forever() -> None:
    """A naive array-offset fix (skip whenever observations[index-12] is not
    exactly 12 calendar months back) would permanently misalign — and thus
    permanently skip — every point after a single missing month, because
    the missing month removes one array slot forever. The correct fix looks
    up the base by calendar date, so only the specific 13-month-later point
    that needs the missing month as its base is skipped; every subsequent
    month keeps computing normally against its own real base."""
    from build_us_dashboard import _apply_transform

    values = [(f"2024-{m:02d}-01", 100.0 + m) for m in range(1, 13)]
    values += [(f"2025-{m:02d}-01", 120.0 + m) for m in range(1, 13) if m != 3]  # no 2025-03
    values += [(f"2026-{m:02d}-01", 140.0 + m) for m in range(1, 4)]  # 2026-01..2026-03
    result = _apply_transform(_monthly_series("yoy_pct", values))
    out_dates = [o["date"] for o in result["observations"]]
    # Only 2026-03 needs the missing 2025-03 as its base; everything else,
    # including every 2026 point whose 2025 base exists, must be present.
    assert "2026-03-01" not in out_dates
    assert "2026-01-01" in out_dates and "2026-02-01" in out_dates
    assert "2025-04-01" in out_dates  # unaffected — its own base (2024-04) exists


def test_us_pct_change_skips_only_the_point_whose_own_base_is_missing() -> None:
    from build_us_dashboard import _apply_transform

    values = [("2025-08-01", 100.0), ("2025-09-01", 101.0), ("2025-11-01", 103.0), ("2025-12-01", 104.0)]
    result = _apply_transform(_monthly_series("pct_change", values))
    out = {o["date"]: o["value"] for o in result["observations"]}
    assert "2025-11-01" not in out, "2025-10 base is missing; 2025-11 MoM has no valid comparator"
    assert out["2025-12-01"] == ((104.0 / 103.0) - 1.0) * 100.0  # base 2025-11 is present


def test_us_diff_skips_only_the_point_whose_own_base_is_missing() -> None:
    from build_us_dashboard import _apply_transform

    values = [("2025-08-01", 100.0), ("2025-09-01", 101.0), ("2025-11-01", 103.0), ("2025-12-01", 104.0)]
    result = _apply_transform(_monthly_series("diff", values))
    out = {o["date"]: o["value"] for o in result["observations"]}
    assert "2025-11-01" not in out
    assert out["2025-12-01"] == 1.0


def test_us_yoy_pct_is_unaffected_when_the_series_is_contiguous() -> None:
    from build_us_dashboard import _apply_transform

    values = [(f"2024-{m:02d}-01", 100.0 + m) for m in range(1, 13)]
    values += [(f"2025-{m:02d}-01", 120.0 + m) for m in range(1, 4)]
    result = _apply_transform(_monthly_series("yoy_pct", values))
    out_dates = [o["date"] for o in result["observations"]]
    assert out_dates == ["2025-01-01", "2025-02-01", "2025-03-01"]


def test_uk_yoy_skips_only_the_point_whose_own_base_is_missing() -> None:
    """build_uk_dashboard.py has its own `_apply_transform` (different
    vocabulary: "yoy"/"qoq_pct"/"mom_pct") with the identical defect as the
    US version — it must get the same calendar-date-lookup fix."""
    from build_uk_dashboard import _apply_transform as uk_apply_transform

    observations = [{"date": f"2024-{m:02d}-01", "value": 100.0 + m} for m in range(1, 13) if m != 4]
    observations += [{"date": f"2025-{m:02d}-01", "value": 120.0 + m} for m in range(1, 6)]
    result = uk_apply_transform(observations, {"transform": "yoy", "frequency": "monthly"})
    out = {o["date"]: o["value"] for o in result}
    assert "2025-04-01" not in out
    assert "2025-03-01" in out and "2025-05-01" in out


def test_uk_mom_pct_matches_ons_monthly_gdp_growth_on_a_contiguous_series() -> None:
    """Confirms the MGDP/ECY2 repoint (finding #1) produces sane MoM growth
    once fed through the shared UK transform, and that the calendar-lookup
    fix is a no-op on a genuinely contiguous monthly series."""
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


def test_japan_cgpi_yoy_skips_only_the_point_that_needs_the_suppressed_month() -> None:
    """Japan's producer_price_inflation reuses build_us_dashboard._apply_transform
    (imported directly by build_japan_dashboard.py). A BOJ flat file that
    silently drops one non-numeric month (see parse_boj_wide_csv) must
    misalign only the one future reading whose year-ago base is that exact
    suppressed month — not every reading after it (self-healing: 2025-02's
    base, 2024-02, is present, so it must compute normally)."""
    from build_us_dashboard import _apply_transform
    from country_primer.adapters import parse_boj_wide_csv

    periods = ",".join(f"2023{m:02d}" for m in range(1, 13))
    periods += ",202401,202402,202501,202502"
    values_2023 = ",".join(f"{100 + i}" for i in range(12))
    # 202401 is deliberately non-numeric ("NA") -> parse_boj_wide_csv drops it.
    text = (
        f",,,{periods}\n"
        f"CODE,\"CGPI\",\"All commodities\",{values_2023},NA,112.0,120.0,121.0\n"
    )
    obs = parse_boj_wide_csv(text, "CODE")
    assert [o["date"] for o in obs][-3:] == ["2024-02-01", "2025-01-01", "2025-02-01"]
    assert "2024-01-01" not in [o["date"] for o in obs]

    series = {"transform": "yoy_pct", "frequency": "monthly", "observations": obs}
    result = _apply_transform(series)
    out = {o["date"]: o["value"] for o in result["observations"]}
    # 2025-01's base would be 2024-01 — suppressed, so it must be skipped.
    assert "2025-01-01" not in out
    # 2025-02's base is 2024-02, which IS present, so it must self-heal and
    # compute normally rather than staying misaligned forever.
    assert out["2025-02-01"] == ((121.0 / 112.0) - 1.0) * 100.0
