from datetime import date

from country_primer.data_quality import assess_series_quality


def test_current_primary_observation_is_verified() -> None:
    quality = assess_series_quality(
        {
            "frequency": "monthly",
            "source_name": "Office for National Statistics",
            "source_url": "https://www.ons.gov.uk/",
            "observations": [{"date": "2026-06-01", "value": 1.0}],
        },
        today=date(2026, 7, 13),
    )
    assert quality["status"] == "verified"
    assert quality["source_authority"] == "official_primary"
    assert quality["freshness"] == "current"


def test_stale_or_substitute_series_is_not_verified() -> None:
    stale = assess_series_quality(
        {
            "frequency": "monthly",
            "source_name": "FRED",
            "observations": [{"date": "2025-01-01", "value": 1.0}],
        },
        today=date(2026, 7, 13),
    )
    assert stale["status"] == "low_confidence"
    assert stale["freshness"] == "stale"


def test_actual_through_separates_projection_tail() -> None:
    quality = assess_series_quality(
        {
            "frequency": "annual",
            "source_name": "IMF Fiscal Monitor",
            "actual_through": "2024-12-31",
            "observations": [
                {"date": "2024-12-31", "value": -3.0},
                {"date": "2026-12-31", "value": -2.0},
            ],
        },
        today=date(2026, 7, 13),
    )
    assert quality["derivation"] == "projection"
    assert quality["freshness"] == "projection"


def test_negated_substitute_note_does_not_downgrade_official_data() -> None:
    quality = assess_series_quality(
        {
            "frequency": "quarterly",
            "source_name": "Eurostat",
            "quality_notes": ["No employment-ratio substitute is permitted."],
            "observations": [{"date": "2026-01-01", "value": 0.5}],
        },
        today=date(2026, 7, 13),
    )
    assert quality["derivation"] == "observed"
    assert quality["status"] == "verified"


def test_replacing_a_stale_mirror_is_not_a_conceptual_substitute() -> None:
    quality = assess_series_quality(
        {
            "frequency": "monthly",
            "source_name": "ONS",
            "quality_notes": ["Official CPI replaces the lagged mirror."],
            "observations": [{"date": "2026-06-01", "value": 2.0}],
        },
        today=date(2026, 7, 13),
    )
    assert quality["derivation"] == "observed"
    assert quality["status"] == "verified"


def test_announced_administered_rate_is_scheduled_not_unavailable() -> None:
    quality = assess_series_quality(
        {
            "id": "reserve_balance_rate",
            "frequency": "daily",
            "source_name": "FRED / Federal Reserve",
            "observations": [{"date": "2026-07-14", "value": 3.9}],
        },
        today=date(2026, 7, 13),
    )
    assert quality["freshness"] == "scheduled_policy"
    assert quality["status"] == "watch"
