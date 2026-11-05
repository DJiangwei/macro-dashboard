"""Offline tests for the keyless energy adapters."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from country_primer.energy_adapters import cftc_measure, daily_means, parse_eia_xls  # noqa: E402


def test_parse_eia_monthly_xls_aligns_to_first_of_month():
    obs = parse_eia_xls((ROOT / "tests/fixtures/eia_MCRFPUS2m.xls").read_bytes(), "monthly")
    assert obs[0]["date"].endswith("-01") and obs[-1]["date"].endswith("-01")
    assert obs == sorted(obs, key=lambda o: o["date"])
    assert all(isinstance(o["value"], float) for o in obs)


def test_cftc_managed_money_net_and_share_of_open_interest():
    row = {"m_money_positions_long_all": "150", "m_money_positions_short_all": "50", "open_interest_all": "1000"}
    assert cftc_measure(row, "mm_net") == 100.0
    assert cftc_measure(row, "mm_net_pct_oi") == 10.0
    assert cftc_measure({"m_money_positions_long_all": "1"}, "mm_net") is None


def test_power_daily_means_bucket_by_local_delivery_day():
    # 2026-01-01 23:30 CET is 22:30 UTC on Jan 1; 00:30 CET on Jan 2 is 23:30 UTC on Jan 1.
    jan1_2230_utc = 1767306600
    means = daily_means([jan1_2230_utc, jan1_2230_utc + 3600], [10.0, 30.0], "Europe/Berlin")
    assert means == {"2026-01-01": 10.0, "2026-01-02": 30.0}
    assert daily_means([jan1_2230_utc], [None], "Europe/Berlin") == {}
