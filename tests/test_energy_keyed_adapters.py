"""Offline tests for the keyed energy sources: GIE AGSI+, EIA STEO and Ember.

Fixtures are trimmed live responses (data rows only, no request echo, no key).
"""
from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from country_primer.energy_adapters import (  # noqa: E402
    agsi_points,
    ember_observations,
    fetch_agsi_points,
    steo_last_history_month,
    steo_observations,
)

FIXTURES = ROOT / "tests/fixtures"


class FakeResponse:
    status_code = 200
    ok = True

    def __init__(self, payload):
        self._payload = payload

    def json(self):
        return self._payload

    def raise_for_status(self):
        return None


class FakeSession:
    """Serves the recorded AGSI+ pages by the ``page`` query parameter."""

    def __init__(self, pages):
        self.pages = pages
        self.calls = []

    def get(self, url, params=None, headers=None, timeout=None):
        self.calls.append({"params": dict(params or {}), "headers": dict(headers or {})})
        return FakeResponse(self.pages[int(params["page"]) - 1])


def agsi_pages():
    return json.loads((FIXTURES / "gie_agsi_eu_pages.json").read_text())


def test_agsi_points_sorted_ascending_and_skip_blank_values():
    rows = agsi_pages()[0]["data"] + [
        {"gasDayStart": "2026-10-06", "full": "-"},
        {"gasDayStart": "2026-10-07", "full": "0"},
    ]
    points = agsi_points(rows)
    assert points[:3] == [("2026-10-03", 72.41), ("2026-10-04", 72.68), ("2026-10-05", 72.84)]
    assert ("2026-10-07", 0.0) in points  # an empty store is data, not a gap
    assert all(day != "2026-10-06" for day, _ in points)


def test_fetch_agsi_points_walks_every_page_and_sends_the_key_as_a_header():
    session = FakeSession(agsi_pages())
    points = fetch_agsi_points("eu", "2026-10-01", api_key="k", session=session, today=date(2026, 10, 6))
    assert [day for day, _ in points] == ["2026-10-01", "2026-10-02", "2026-10-03", "2026-10-04", "2026-10-05"]
    assert [call["params"]["page"] for call in session.calls] == [1, 2]
    first = session.calls[0]
    assert first["params"]["type"] == "eu" and "country" not in first["params"]
    assert first["params"]["from"] == "2026-10-01" and first["params"]["to"] == "2026-10-06"
    assert first["headers"]["x-key"] == "k"
    assert "k" not in first["params"].values()


def test_fetch_agsi_points_uses_country_parameter_for_member_states():
    session = FakeSession(agsi_pages())
    fetch_agsi_points("HU", "2026-10-01", api_key="k", session=session, today=date(2026, 10, 6))
    assert session.calls[0]["params"]["country"] == "HU" and "type" not in session.calls[0]["params"]


def test_steo_history_month_stays_behind_the_forecast_start():
    # STEO is released early in the month and forecasts from the release month,
    # so two months back is always history whichever vintage is live.
    assert steo_last_history_month(date(2026, 11, 5)) == "2026-09"
    assert steo_last_history_month(date(2027, 1, 3)) == "2026-11"
    assert steo_last_history_month(date(2027, 2, 28)) == "2026-12"


def test_steo_observations_drop_forecast_months():
    rows = json.loads((FIXTURES / "eia_steo_cops_opec.json").read_text())["response"]["data"]
    obs = steo_observations(rows, today=date(2026, 11, 5))
    assert obs[0] == {"date": "2026-01-01", "value": 2.955}
    assert obs[-1]["date"] == "2026-09-01"
    assert [o["date"] for o in obs] == sorted(o["date"] for o in obs)


def test_ember_selects_one_series_and_measure():
    rows = json.loads((FIXTURES / "ember_eu_monthly.json").read_text())["data"]
    gas = ember_observations(rows, "Gas", "share_of_generation_pct")
    assert [o["date"] for o in gas] == ["2026-01-01", "2026-02-01"]
    assert all(0.0 < o["value"] < 100.0 for o in gas)
    wind_solar = ember_observations(rows, "Wind and solar", "share_of_generation_pct")
    wind = {o["date"]: o["value"] for o in ember_observations(rows, "Wind", "share_of_generation_pct")}
    solar = {o["date"]: o["value"] for o in ember_observations(rows, "Solar", "share_of_generation_pct")}
    for o in wind_solar:
        assert o["value"] == pytest.approx(wind[o["date"]] + solar[o["date"]], abs=0.05)
    with pytest.raises(ValueError):
        ember_observations(rows, "Gas", "price")


def test_cee_gas_storage_uses_the_shared_client_with_a_daily_cache(monkeypatch, tmp_path):
    from datetime import datetime

    from country_primer import data_fetcher, energy_adapters

    calls = []

    def fake_points(code, start, api_key, **kwargs):
        calls.append((code, start))
        return [("2026-10-01", 70.0)]

    monkeypatch.setattr(energy_adapters, "fetch_agsi_points", fake_points)
    monkeypatch.setattr(data_fetcher, "cache_path", lambda key: tmp_path / key.replace(":", "_"))
    fetcher = data_fetcher.GIEAGSIFetcher()
    assert fetcher._fetch_country("HU", "k") == [("2026-10-01", 70.0)]
    assert fetcher._fetch_country("HU", "k") == [("2026-10-01", 70.0)]  # today's cache
    assert calls == [("HU", "2015-01-01")]
    assert [p.name for p in tmp_path.iterdir()] == [f"gie_agsi__HU__{datetime.now().date().isoformat()}"]
