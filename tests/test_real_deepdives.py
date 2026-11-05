"""Real-data deepdive views: transforms, provenance and rendering."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import real_deepdives as rd  # noqa: E402


def test_annualised_from_index_uses_actual_three_month_change():
    obs = [("2026-01-01", 100.0), ("2026-02-01", 100.5), ("2026-03-01", 101.0), ("2026-04-01", 101.5)]
    value, latest, base = rd.annualised_from_index(obs, 3)
    assert (latest, base) == ("2026-04-01", "2026-01-01")
    assert value == pytest.approx(((101.5 / 100.0) ** 4 - 1) * 100, abs=0.01)


def test_annualised_from_mom_compounds_consecutive_months_only():
    obs = [("2026-01-01", 0.2), ("2026-02-01", 0.3), ("2026-03-01", 0.4)]
    value, _, _ = rd.annualised_from_mom(obs, 3)
    assert value == pytest.approx(((1.002 * 1.003 * 1.004) ** 4 - 1) * 100, abs=0.01)
    assert rd.annualised_from_mom([("2026-01-01", 0.2), ("2026-03-01", 0.4)], 3) is None


def test_sahm_indicator_and_gap_handling():
    flat = [(f"2025-{m:02d}-01", 4.0) for m in range(1, 13)] + [(f"2026-{m:02d}-01", 4.0) for m in range(1, 4)]
    assert rd.sahm_indicator(flat)["value"] == 0.0
    rising = flat[:-3] + [("2026-01-01", 4.6), ("2026-02-01", 4.7), ("2026-03-01", 4.8)]
    result = rd.sahm_indicator(rising)
    assert result["value"] == pytest.approx(0.7, abs=0.01) and result["triggered"]
    assert rd.sahm_indicator([o for o in flat if o[0] != "2025-10-01"]) is None


def test_real_wage_only_on_matching_months():
    wage = [("2026-01-01", 5.0), ("2026-02-01", 4.0)]
    cpi = [("2026-02-01", 3.0)]
    assert rd.real_wage(wage, cpi) == [("2026-02-01", 1.0)]


def _views():
    return sorted((ROOT / "output").glob("*_deepdive_views.json"))


@pytest.mark.parametrize("path", _views(), ids=lambda p: p.stem)
def test_view_values_trace_to_canonical_frames(path: Path):
    view = json.loads(path.read_text())
    config = rd.load_config()
    series = rd._load_scope_series(view["scope"], config, {})
    for kind in ("inflation", "labour"):
        for row in (view.get(kind) or {}).get("rows", []):
            if row["derivation"] != "observed":
                continue
            canonical = dict(series[row["id"]]["observations"])
            assert canonical[row["latest"]["date"]] == pytest.approx(row["latest"]["value"]), row["id"]


def test_render_returns_nothing_without_real_rows():
    assert rd.render_labour_view("TW") == ""


def test_old_synthetic_outputs_are_gone():
    leftovers = [p.name for p in (ROOT / "output").glob("*_labour_deepdive.json")]
    assert not leftovers, leftovers
