"""Whitelisted derived-series operators."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from country_primer.derived import apply_derivations, apply_op, monthly_mean  # noqa: E402


def pts(*pairs):
    return list(pairs)


def test_spread_and_linear_use_only_common_dates():
    a = pts(("2026-01-01", 10.0), ("2026-01-02", 12.0))
    b = pts(("2026-01-02", 2.0), ("2026-01-03", 5.0))
    assert apply_op("spread", [a, b], {}) == [("2026-01-02", 10.0)]
    assert apply_op("linear", [a, b], {"weights": [2, -1]}) == [("2026-01-02", 22.0)]


def test_ratio_skips_zero_denominator():
    assert apply_op("ratio", [pts(("d1", 4.0), ("d2", 1.0)), pts(("d1", 2.0), ("d2", 0.0))], {"factor": 1000}) == [("d1", 2000.0)]


def test_rolling_mean_and_zscore_need_a_full_window():
    series = [(f"2026-01-{i:02d}", float(i)) for i in range(1, 6)]
    assert apply_op("rolling_mean", [series], {"window": 4}) == [("2026-01-04", 2.5), ("2026-01-05", 3.5)]
    z = apply_op("zscore", [series], {"window": 5})
    assert len(z) == 1 and z[0][1] > 1.2
    assert apply_op("zscore", [[(f"d{i}", 1.0) for i in range(5)]], {"window": 5}) == []  # flat: undefined


def test_dev_from_5y_requires_three_prior_years():
    weekly = []
    for year, level in [(2021, 100.0), (2022, 110.0), (2023, 120.0), (2024, 130.0)]:
        weekly.append((f"{year}-03-05", level))
        weekly.append((f"{year}-03-12", level))
    out = dict(apply_op("dev_from_5y_seasonal", [sorted(weekly)], {}))
    assert "2023-03-05" not in out  # only two prior years
    assert out  # 2024 weeks have three prior years
    assert all(abs(v - 20.0) < 1e-9 for d, v in out.items() if d.startswith("2024"))


def test_monthly_mean_drops_current_month(monkeypatch):
    out = monthly_mean([("2020-01-02", 1.0), ("2020-01-03", 3.0), ("2099-01-01", 9.0)])
    assert out == [("2020-01-01", 2.0)]


def test_unlisted_operator_is_refused():
    with pytest.raises(ValueError):
        apply_op("eval", [[]], {})


def test_apply_derivations_chains_and_records_vintages(tmp_path):
    series = [
        {"id": "a", "observations": [{"date": "2026-01-01", "value": 5.0}, {"date": "2026-01-02", "value": 7.0}]},
        {"id": "b", "observations": [{"date": "2026-01-01", "value": 1.0}, {"date": "2026-01-02", "value": 2.0}]},
        {"id": "s", "derivation": "derived", "op": "spread", "inputs": ["a", "b"]},
        {"id": "r", "derivation": "derived", "op": "rolling_mean", "window": 2, "inputs": ["s"]},
    ]
    out = {item["id"]: item for item in apply_derivations(series, tmp_path)}
    assert [o["value"] for o in out["s"]["observations"]] == [4.0, 5.0]
    assert out["r"]["observations"] == [{"date": "2026-01-02", "value": 4.5}]
    assert out["s"]["derivation_inputs"] == {"a": "2026-01-02", "b": "2026-01-02"}
    missing = apply_derivations([{"id": "x", "derivation": "derived", "op": "spread", "inputs": ["a", "zz"]}], tmp_path)
    assert missing[0]["observations"] == [] and missing[0]["quality_status"] == "unavailable"
