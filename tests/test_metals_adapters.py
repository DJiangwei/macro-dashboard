"""Base- and precious-metals sources (metals_adapters)."""
import pytest

DAYS = ["2025-12-29", "2025-12-30", "2025-12-31", "2026-01-02", "2026-01-30", "2026-02-02", "2026-02-09"]
# One constant settle per contract, so each spread value names the pair used.
LEVELS = {"2601": 100.0, "2602": 110.0, "2603": 125.0, "2604": 145.0, "2605": 170.0}


def _settles() -> dict[str, dict[str, float]]:
    return {code: {day: level for day in DAYS} for code, level in LEVELS.items()}


def _spread(settles=None) -> dict[str, float]:
    from country_primer.metals_adapters import calendar_spread

    rows = calendar_spread(settles or _settles(), start="2025-12-01", today="2026-02-10")
    return {row["date"]: row["value"] for row in rows}


def test_spread_uses_near_and_third_month() -> None:
    assert _spread()["2025-12-30"] == LEVELS["2601"] - LEVELS["2603"]


def test_spread_rolls_on_last_trading_day_before_delivery_month() -> None:
    spread = _spread()
    assert spread["2025-12-31"] == LEVELS["2602"] - LEVELS["2604"]
    assert spread["2026-01-30"] == LEVELS["2603"] - LEVELS["2605"]


def test_current_month_is_not_rolled_early() -> None:
    assert _spread()["2026-02-09"] == LEVELS["2603"] - LEVELS["2605"]


def test_days_missing_a_leg_are_skipped() -> None:
    settles = _settles()
    del settles["2603"]["2025-12-30"]
    spread = _spread(settles)
    assert "2025-12-30" not in spread
    assert "2025-12-29" in spread


def test_contract_months_span_start_to_three_ahead() -> None:
    from country_primer.metals_adapters import contract_months

    assert contract_months("2025-11-15", "2026-01-20") == ["2511", "2512", "2601", "2602", "2603", "2604"]


def _comex_frame(tonnes_column: str = "COMEX黄金库存量-吨"):
    import pandas as pd

    return pd.DataFrame({
        "序号": [1, 2, 3],
        "日期": ["2026-11-03", "2026-11-04", "2026-11-06"],
        tonnes_column: [719.26, 715.29, 700.0],
        "COMEX黄金库存量-盎司": [23124670.0, 22997130.0, 22505000.0],
    })


def test_comex_observations_reads_tonnes_and_drops_today() -> None:
    from country_primer.metals_adapters import comex_observations

    assert comex_observations(_comex_frame(), today="2026-11-06") == [
        {"date": "2026-11-03", "value": 719.26},
        {"date": "2026-11-04", "value": 715.29},
    ]


def test_comex_observations_require_a_tonnes_column() -> None:
    from country_primer.metals_adapters import comex_observations

    with pytest.raises(ValueError, match="-吨"):
        comex_observations(_comex_frame("COMEX黄金库存量-千克"), today="2026-11-06")
