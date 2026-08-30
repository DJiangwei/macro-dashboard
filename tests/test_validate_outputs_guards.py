"""Regression coverage for finding #4 of the whole-branch review: the
existing guards in scripts/validate_outputs.py did not catch findings #1 or
#2 because they never checked (a) a declared frequency against observed
observation spacing, or (b) contiguity of a lag-transformed series at its
declared cadence. Both new assertions read only committed canonical-frame
JSON — offline and deterministic, no network.
"""
from __future__ import annotations

import pytest

from validate_outputs import (
    _assert_frequency_matches_observed_spacing,
    _assert_lag_transform_series_are_contiguous,
    _first_ratio_stat_after,
)


def _series(indicator_id: str, frequency: str, dates: list[str], *, transform: str = "level") -> dict:
    return {
        "indicator_id": indicator_id,
        "frequency": frequency,
        "transform": transform,
        "observations": [[d, 1.0] for d in dates],
    }


def test_frequency_check_passes_for_genuinely_monthly_spacing() -> None:
    dates = [f"2025-{m:02d}-01" for m in range(1, 13)]
    _assert_frequency_matches_observed_spacing("uk", [_series("x", "monthly", dates)])


def test_frequency_check_passes_for_genuinely_quarterly_spacing() -> None:
    dates = ["2024-03-31", "2024-06-30", "2024-09-30", "2024-12-31", "2025-03-31"]
    _assert_frequency_matches_observed_spacing("uk", [_series("x", "quarterly", dates)])


def test_frequency_check_catches_monthly_labelled_quarterly_data() -> None:
    """Regression for finding #1: ONS series YBEZ/PN2 was declared frequency:
    monthly but every observation sat at quarter-ends, three months apart."""
    dates = ["2025-06-30", "2025-09-30", "2025-12-31", "2026-03-31", "2026-06-30"]
    with pytest.raises(AssertionError, match="monthly_gdp_index.*monthly.*3 months"):
        _assert_frequency_matches_observed_spacing(
            "uk", [_series("monthly_gdp_index", "monthly", dates)]
        )


def test_frequency_check_tolerates_one_isolated_gap() -> None:
    """A single honestly-missing month (e.g. BLS never published October
    2025 CPI) must not trip this — only a systematically wrong label should."""
    dates = [f"2025-{m:02d}-01" for m in range(1, 10)] + ["2025-11-01", "2025-12-01"]
    _assert_frequency_matches_observed_spacing("us", [_series("cpi_inflation", "monthly", dates)])


def test_frequency_check_ignores_short_or_unclocked_series() -> None:
    _assert_frequency_matches_observed_spacing("us", [_series("x", "monthly", ["2026-01-01", "2026-02-01"])])
    _assert_frequency_matches_observed_spacing(
        "us", [_series("x", "irregular", ["2020-01-01", "2021-06-15", "2024-09-02", "2025-01-01"])]
    )


def test_contiguity_check_allows_one_missed_period_for_a_yoy_style_transform() -> None:
    dates = [f"2025-{m:02d}-01" for m in range(1, 10)] + ["2025-11-01", "2025-12-01"]
    _assert_lag_transform_series_are_contiguous(
        "us", [_series("cpi_inflation", "monthly", dates, transform="yoy_pct")]
    )


def test_contiguity_check_allows_the_compounded_gap_a_period_1_transform_produces() -> None:
    """A single missing source month costs a period-1 transform (mom_pct/
    qoq_pct/diff) *two* output points, not one: the missing month itself has
    no item to transform, and the immediately following month's own base is
    that missing month, so it is skipped too. This is real, not
    hypothetical: US core_cpi_mom shows exactly this pattern (2025-09 ->
    2025-12, a 3-month gap) because BLS never published October 2025 CPI.
    That must not fail the build."""
    dates = [f"2025-{m:02d}-01" for m in range(1, 10)] + ["2025-12-01"]  # no Oct, no Nov
    _assert_lag_transform_series_are_contiguous(
        "us", [_series("core_cpi_mom", "monthly", dates, transform="pct_change")]
    )


def test_contiguity_check_rejects_a_wider_gap_for_a_lag_transform() -> None:
    """Two or more consecutive missing *source* periods (beyond what a
    single missing observation can honestly produce) or a reintroduced
    index-offset misalignment bug must fail the build rather than ship a
    verified badge on data nobody re-checked."""
    dates = [f"2025-{m:02d}-01" for m in range(1, 6)] + ["2025-10-01"]  # 5-month gap
    with pytest.raises(AssertionError, match="cpi_inflation.*gap"):
        _assert_lag_transform_series_are_contiguous(
            "us", [_series("cpi_inflation", "monthly", dates, transform="yoy_pct")]
        )


def test_contiguity_check_does_not_apply_to_non_transformed_series() -> None:
    dates = [f"2025-{m:02d}-01" for m in range(1, 6)] + ["2025-09-01"]  # same 4-month gap
    _assert_lag_transform_series_are_contiguous("us", [_series("cpi_level", "monthly", dates, transform="level")])


def test_first_ratio_stat_after_extracts_the_stat_following_a_heading() -> None:
    html = (
        '<a href="south_africa.html" class="card"><h2>South Africa</h2>'
        '<div class="stats"><div class="stat"><span>Rendered charts</span>'
        '<strong>64/64</strong></div></div></a>'
    )
    assert _first_ratio_stat_after(html, "South Africa") == (64, 64)


def test_first_ratio_stat_after_returns_none_when_heading_is_absent() -> None:
    assert _first_ratio_stat_after("<h2>Japan</h2><strong>52/52</strong>", "South Africa") is None


def test_frequency_check_judges_cadence_by_recent_history_not_full_history() -> None:
    """China's 1Y LPR (lpr_1y_akshare) was reported near-daily before the
    August 2019 LPR reform and monthly afterward. That is an honest
    methodology change in the underlying source, not a mislabel, and must
    not trip this check just because the full history's modal gap is
    dominated by the old daily-ish era."""
    daily_era = [f"2013-{m:02d}-{d:02d}" for m in range(10, 13) for d in (1, 8, 15, 22)]
    monthly_era = [f"2019-{m:02d}-20" for m in range(9, 13)] + [f"2020-{m:02d}-20" for m in range(1, 9)]
    dates = daily_era + monthly_era
    _assert_frequency_matches_observed_spacing("china", [_series("lpr_1y_akshare", "monthly", dates)])


def test_frequency_check_accepts_semi_annual_reporting_declared_as_quarterly() -> None:
    """Japan's IMF Financial Soundness Indicators series (bank_capital_ratio,
    bank_npl_ratio) are dimensioned quarterly in IMF SDMX but Japan has only
    ever submitted them twice a year — a genuine cross-country reporting
    cadence, not a mislabel. Real committed data for both series is exactly
    this pattern (verified against output/japan_canonical_frame.json)."""
    dates = [f"{y}-{m:02d}-01" for y in range(2020, 2026) for m in (1, 7)]
    _assert_frequency_matches_observed_spacing("japan", [_series("bank_capital_ratio", "quarterly", dates)])


def test_frequency_check_still_rejects_monthly_labelled_as_quarterly_data_even_with_the_quarterly_allowance() -> None:
    """The quarterly-tolerates-6-months allowance must not leak into the
    monthly check: a monthly label still requires monthly data."""
    dates = ["2025-06-30", "2025-09-30", "2025-12-31", "2026-03-31", "2026-06-30"]
    with pytest.raises(AssertionError):
        _assert_frequency_matches_observed_spacing("uk", [_series("monthly_gdp_index", "monthly", dates)])


def test_frequency_check_still_rejects_quarterly_labelled_as_annual_data() -> None:
    """The 3-or-6-month allowance for "quarterly" must not become "anything
    goes" — a genuinely annual cadence must still fail."""
    dates = [f"{y}-12-31" for y in range(2018, 2026)]
    with pytest.raises(AssertionError, match="quarterly.*12 months"):
        _assert_frequency_matches_observed_spacing("japan", [_series("x", "quarterly", dates)])


# --- Ruling 10: parity rule for period-1 lag transforms ----------------------
# A period-1 transform (mom_pct/qoq_pct/pct_change/diff) loses exactly TWO
# adjacent output points per missing source observation -- the missing period
# itself, and the next period whose own base is that missing period. So its
# honest gaps are exactly 1x (contiguous) or 3x (one missing source period).
# A 2x gap cannot arise from missing source data: it would mean one output
# point vanished while its neighbour survived, which the base lookup makes
# impossible. It is instead the fingerprint of a systematic every-other-point
# drop -- exactly what the end-of-month day-rollover bug produced, dropping
# every Q2 point from every quarterly QoQ series.


def test_contiguity_rejects_a_2x_gap_for_a_period_1_transform() -> None:
    # Quarter-end dates with every Q2 dropped: the rollover-bug fingerprint.
    dates = ["2024-03-31", "2024-09-30", "2024-12-31", "2025-03-31", "2025-09-30"]
    with pytest.raises(AssertionError, match="every-other-period|2x|parity|neither"):
        _assert_lag_transform_series_are_contiguous(
            "uk", [_series("gfcf_qoq", "quarterly", dates, transform="qoq_pct")]
        )


def test_contiguity_still_allows_1x_and_3x_for_a_period_1_transform() -> None:
    # 1x throughout, then a single 3x gap from one missing source month.
    dates = ["2025-06-01", "2025-07-01", "2025-08-01", "2025-09-01", "2025-12-01"]
    _assert_lag_transform_series_are_contiguous(
        "us", [_series("core_cpi_mom", "monthly", dates, transform="pct_change")]
    )


def test_contiguity_still_allows_a_2x_gap_for_a_period_n_transform() -> None:
    # yoy loses one isolated output point per missing source month, so 2x is
    # honest here and must not be rejected by the period-1 parity rule.
    dates = ["2025-06-01", "2025-07-01", "2025-09-01", "2025-10-01"]
    _assert_lag_transform_series_are_contiguous(
        "us", [_series("cpi_inflation", "monthly", dates, transform="yoy_pct")]
    )
