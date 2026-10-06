from datetime import date

from country_primer.data_quality import assess_series_quality, expected_next_release, source_authority


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


def test_ons_fast_monthly_uses_expected_next_release_window() -> None:
    series = {
        "id": "cpi_yoy",
        "frequency": "monthly",
        "source_name": "Office for National Statistics",
        "source_url": "https://www.ons.gov.uk/",
        "observations": [{"date": "2026-05-01", "value": 2.0}],
    }
    window = expected_next_release(series, date(2026, 5, 1))
    assert window is not None
    assert window["calendar_id"] == "ons_fast_monthly"
    assert window["expected_release_date"] == "2026-07-20"
    quality = assess_series_quality(series, today=date(2026, 7, 14))
    assert quality["freshness"] == "due"
    assert quality["due_date"] == "2026-07-27"


def test_eurostat_quarterly_becomes_stale_after_calendar_grace() -> None:
    quality = assess_series_quality(
        {
            "id": "employment_growth",
            "frequency": "quarterly",
            "source_name": "Eurostat",
            "source_url": "https://ec.europa.eu/eurostat/",
            "observations": [{"date": "2025-10-01", "value": 0.5}],
        },
        today=date(2026, 7, 14),
    )
    assert quality["release_calendar_id"] == "eurostat_quarterly"
    assert quality["freshness"] == "stale"


def test_explicit_max_age_days_overrides_release_calendar() -> None:
    quality = assess_series_quality(
        {
            "id": "cpi_yoy",
            "frequency": "monthly",
            "source_name": "ONS",
            "max_age_days": 10,
            "observations": [{"date": "2026-06-01", "value": 2.0}],
        },
        today=date(2026, 7, 14),
    )
    assert quality["freshness"] == "stale"
    assert quality["max_age_days"] == 10


def test_wrappers_and_mirrors_take_precedence_over_embedded_agency_names() -> None:
    assert source_authority("AKShare / National Bureau of Statistics") == "public_wrapper"
    assert source_authority("FRED / Bureau of Economic Analysis") == "official_mirror"
    assert source_authority("Bureau of Economic Analysis", "https://www.bea.gov/") == "official_primary"


def test_declared_authority_overrides_name_matching():
    assert source_authority("SARB Web API", "", "official_primary") == "official_primary"


def test_declared_authority_ignored_when_invalid():
    assert source_authority("FRED / OECD", "", "not_a_tier") == "official_mirror"


def test_native_sources_match_as_primary_without_declaration():
    for name in ("Bank of Japan flat file", "e-Stat API", "SARB Web API"):
        assert source_authority(name) == "official_primary", name


def test_declared_authority_flows_through_assessment():
    series = {
        "id": "cpi_inflation", "frequency": "monthly", "transform": "level",
        "source_name": "SARB Web API", "source_authority": "official_primary",
        "observations": [{"date": "2026-07-01", "value": 4.3}],
    }
    assert assess_series_quality(series)["source_authority"] == "official_primary"


def _series(**overrides):
    base = {
        "id": "core_cpi_inflation", "frequency": "monthly",
        "source_name": "e-Stat API", "source_authority": "official_primary",
        "observations": [{"date": "2026-07-01", "value": 1.7}],
    }
    base.update(overrides)
    return base


def test_declared_transform_can_still_be_verified(monkeypatch):
    import country_primer.data_quality as dq
    monkeypatch.setattr(dq, "DEFAULT_MAX_AGE_DAYS", {**dq.DEFAULT_MAX_AGE_DAYS, "monthly": 3650})
    result = dq.assess_series_quality(_series(transform="yoy_pct"), today=__import__("datetime").date(2026, 8, 1))
    assert result["derivation"] == "derived"
    assert result["status"] == "verified"


def test_substitute_is_still_not_verified(monkeypatch):
    import country_primer.data_quality as dq
    monkeypatch.setattr(dq, "DEFAULT_MAX_AGE_DAYS", {**dq.DEFAULT_MAX_AGE_DAYS, "monthly": 3650})
    result = dq.assess_series_quality(
        _series(transform="level", derivation="substitute"),
        today=__import__("datetime").date(2026, 8, 1),
    )
    assert result["status"] != "verified"
