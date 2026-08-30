"""Regression coverage for the UK Monthly-GDP mislabel found in review.

ONS series YBEZ/PN2 ("Gross domestic product index: CVM: Seasonally
adjusted") is quarterly. `config/uk_indicators.yaml` declared
`frequency: monthly` for it, and `fetch_ons_timeseries` silently fell back
to `payload["quarters"]` whenever the declared frequency's array was empty
— so the chart shipped labelled "Monthly GDP", badged `verified`, while its
observations sat at quarter-ends three months apart.

The fix has two parts: (1) the fetcher now fails loudly instead of
substituting a different frequency's array, and (2) the two Monthly GDP
indicators (`monthly_gdp_index`, `monthly_gdp_mom`) now point at ONS's
genuinely monthly dataset MGDP / CDID ECY2 ("Monthly gross domestic product:
time series"), which backs the official "GDP monthly estimate, UK" bulletin.

These tests must stay offline and deterministic — no live ONS calls.
"""
from __future__ import annotations

import pytest


class _FakeResponse:
    def __init__(self, payload: dict) -> None:
        self._payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict:
        return self._payload


class _FakeSession:
    def __init__(self, payload: dict) -> None:
        self._payload = payload

    def get(self, *args, **kwargs) -> _FakeResponse:
        return _FakeResponse(self._payload)


def test_ons_fetch_fails_loudly_when_declared_frequency_is_absent() -> None:
    """Regression for the UK Monthly-GDP mislabel: ONS series YBEZ/PN2 is
    quarterly, but the config declared frequency: monthly. The fetcher used
    to silently fall back to payload['quarters'] and ship a chart whose
    label ("monthly") contradicted its data, badged verified."""
    from build_uk_dashboard import fetch_ons_timeseries

    payload = {
        "years": [{"date": "2025", "value": "100.0"}],
        "quarters": [{"date": "2025 Q4", "value": "102.5"}],
        "months": [],
    }
    spec = {"series": "YBEZ", "id": "monthly_gdp_index", "frequency": "monthly", "ons_path": "/x"}
    with pytest.raises(ValueError, match="monthly"):
        fetch_ons_timeseries(_FakeSession(payload), spec)


def test_ons_fetch_fails_loudly_on_unsupported_frequency() -> None:
    from build_uk_dashboard import fetch_ons_timeseries

    payload = {"months": [{"date": "2025 JAN", "value": "1.0"}]}
    spec = {"series": "X", "id": "x", "frequency": "weekly", "ons_path": "/x"}
    with pytest.raises(ValueError, match="unsupported"):
        fetch_ons_timeseries(_FakeSession(payload), spec)


def test_ons_fetch_succeeds_when_declared_frequency_matches_payload() -> None:
    """The new MGDP/ECY2 series genuinely carries a `months` array, so the
    fetcher must succeed without falling back to anything."""
    from build_uk_dashboard import fetch_ons_timeseries

    payload = {
        "months": [
            {"date": "2026 MAY", "value": "103.1"},
            {"date": "2026 JUN", "value": "103.4"},
        ],
        "quarters": [],
        "years": [],
        "description": {"releaseDate": "2026-08-12"},
    }
    spec = {"series": "ECY2", "id": "monthly_gdp_index", "frequency": "monthly", "ons_path": "/x"}
    result = fetch_ons_timeseries(_FakeSession(payload), spec)
    assert [o["date"] for o in result["observations"]] == ["2026-05-01", "2026-06-01"]
