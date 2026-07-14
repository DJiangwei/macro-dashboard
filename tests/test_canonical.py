import json

from dashboard_summary_utils import (
    load_canonical_data_first_frame,
    retain_last_known_good_series,
    write_canonical_data_first_frame,
)
from country_primer.snapshots import (
    load_cee_canonical_snapshot,
    retain_last_known_good_cee_rows,
    write_cee_canonical_snapshot,
)


def test_canonical_v2_deduplicates_metadata(tmp_path) -> None:
    path = tmp_path / "frame.json"
    metadata = write_canonical_data_first_frame(
        path,
        "UK",
        [{
            "id": "cpi_yoy",
            "section": "prices",
            "label_en": "CPI",
            "label_zh": "CPI",
            "unit": "% YoY",
            "frequency": "monthly",
            "source_name": "ONS",
            "series": "D7G7",
            "source_url": "https://www.ons.gov.uk/",
            "provider_updated": "2026-07-10",
            "observations": [
                {"date": "2026-05-01", "value": 2.1},
                {"date": "2026-06-01", "value": 2.0},
            ],
        }],
    )
    payload = json.loads(path.read_text())
    assert payload["schema_version"] == "data-first-canonical-v2"
    assert payload["series"][0]["concept_id"] == "headline_inflation"
    assert payload["series"][0]["observations"] == [["2026-05-01", 2.1], ["2026-06-01", 2.0]]
    assert payload["series"][0]["provider_updated"] == "2026-07-10"
    assert metadata["series_count"] == 1
    assert metadata["observation_count"] == 2

    restored = load_canonical_data_first_frame(
        path,
        {"indicators": [{"id": "cpi_yoy", "caveat_en": "Official release."}]},
    )
    assert restored[0]["source_name"] == "ONS"
    assert restored[0]["caveat_en"] == "Official release."
    assert restored[0]["provider_updated"] == "2026-07-10"
    assert restored[0]["observations"][-1] == {"date": "2026-06-01", "value": 2.0}


def test_cee_canonical_snapshot_round_trip(tmp_path) -> None:
    path = tmp_path / "cee.json"
    rows = [{
        "country": "PL",
        "date": "2026-05-01",
        "indicator_id": "cpi_yoy",
        "concept_id": "headline_inflation",
        "value": 2.4,
        "label": "CPI",
        "section_id": "prices_wages",
        "unit": "% YoY",
        "source": "Eurostat",
        "series_id": "prc_hicp_manr",
        "quality_status": "verified",
        "quality_note": "",
        "is_proxy": False,
        "frequency": "monthly",
        "source_url": "https://ec.europa.eu/eurostat/",
        "source_authority": "official_primary",
        "derivation": "observed",
        "freshness_status": "current",
        "validation_status": "passed",
        "comparability": "high",
        "observation_type": "observed",
        "is_projection": False,
    }]
    write_cee_canonical_snapshot(path, {"PL": rows})
    restored = load_cee_canonical_snapshot(path)
    assert restored["PL"] == rows


def test_failed_refresh_retains_prior_canonical_observations(tmp_path) -> None:
    path = tmp_path / "frame.json"
    config = {"indicators": [{"id": "cpi_yoy", "label_en": "CPI"}]}
    write_canonical_data_first_frame(
        path,
        "UK",
        [{
            "id": "cpi_yoy",
            "label_en": "CPI",
            "frequency": "monthly",
            "source_name": "ONS",
            "observations": [{"date": "2026-06-01", "value": 2.0}],
        }],
    )
    merged = retain_last_known_good_series(
        [{"id": "cpi_yoy", "observations": [], "failure_reason": "timeout"}],
        path,
        config,
    )
    assert merged[0]["observations"] == [{"date": "2026-06-01", "value": 2.0}]
    assert merged[0]["refresh_fallback"] is True
    assert merged[0]["quality_status"] == "watch"
    assert "timeout" in merged[0]["quality_notes"][-1]


def test_cee_refresh_retains_only_expected_missing_indicator() -> None:
    prior = [
        {"country": "PL", "indicator_id": "cpi_yoy", "date": "2026-05-01", "value": 2.4},
        {"country": "PL", "indicator_id": "retired_series", "date": "2020-01-01", "value": 1.0},
    ]
    merged = retain_last_known_good_cee_rows([], prior, {"cpi_yoy"})
    assert [row["indicator_id"] for row in merged] == ["cpi_yoy"]
    assert merged[0]["refresh_fallback"] is True
    assert merged[0]["quality_status"] == "watch"
