"""Freshness-audit classification for CE4 forecast tails."""
from __future__ import annotations

import json

import freshness_audit as fa


def test_projection_flag_overrides_future_date() -> None:
    record = fa._record(
        dashboard="Hungary",
        indicator_id="gov_debt_pct_gdp",
        label="General Government Debt, % GDP",
        frequency="annual",
        latest_observation="2099-12-31",
        quality_status="watch",
        source="IMF Fiscal Monitor",
        projection=True,
    )
    assert record.freshness_status == "projection"


def test_ce4_projection_tails_read_canonical_flags(tmp_path, monkeypatch) -> None:
    frame = {
        "observation_columns": ["date", "value", "observation_type", "is_projection"],
        "series": [
            {
                "country": "HU",
                "indicator_id": "gov_debt_pct_gdp",
                "observations": [
                    ["2024-12-31", 73.5, "historical", False],
                    ["2026-12-31", 77.9, "projection", True],
                ],
            },
            {
                "country": "HU",
                "indicator_id": "administered_prices",
                "observations": [["2026-12-31", 20.5, "historical", False]],
            },
        ],
    }
    path = tmp_path / "cee_canonical_frame.json"
    path.write_text(json.dumps(frame))
    monkeypatch.setattr(fa, "CEE_CANONICAL", path)
    assert fa._ce4_projection_tails() == {("Hungary", "gov_debt_pct_gdp")}
