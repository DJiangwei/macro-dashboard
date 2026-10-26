import pytest


def test_adapters_module_exposes_the_shared_fetchers() -> None:
    from country_primer import adapters
    for name in ("fetch_imf_sdmx", "fetch_imf_datamapper", "apply_scale", "sdmx_period_to_date"):
        assert hasattr(adapters, name), name


def test_sdmx_period_parsing() -> None:
    from country_primer.adapters import sdmx_period_to_date
    assert sdmx_period_to_date("2026-M06") == "2026-06-01"
    assert sdmx_period_to_date("2025-Q3") == "2025-07-01"
    assert sdmx_period_to_date("2024") == "2024-01-01"
    assert sdmx_period_to_date("garbage") is None


def test_apply_scale_divides_and_is_a_noop_without_scale() -> None:
    from country_primer.adapters import apply_scale
    scaled = apply_scale({"scale": 1_000_000_000, "observations": [{"date": "2026-06-01", "value": 5e9}]})
    assert scaled["observations"][0]["value"] == 5.0
    same = {"observations": [{"date": "2026-06-01", "value": 42.0}]}
    assert apply_scale(same)["observations"][0]["value"] == 42.0


def test_builders_no_longer_import_fetchers_from_each_other() -> None:
    source = open("scripts/build_south_africa_dashboard.py").read()
    assert "from build_japan_dashboard import" not in source


def test_parse_boj_wide_csv_reads_periods_from_the_header() -> None:
    from country_primer.adapters import parse_boj_wide_csv
    text = open("tests/fixtures/boj_cgpi_sample.csv").read()
    obs = parse_boj_wide_csv(text, "PRCG20_2200000000")
    assert obs, "expected observations for the all-commodities series"
    assert obs[0]["date"] == "2020-01-01"
    assert isinstance(obs[0]["value"], float)
    assert obs == sorted(obs, key=lambda o: o["date"])


def test_parse_boj_wide_csv_unknown_code_returns_empty() -> None:
    from country_primer.adapters import parse_boj_wide_csv
    text = open("tests/fixtures/boj_cgpi_sample.csv").read()
    assert parse_boj_wide_csv(text, "NOT_A_CODE") == []


def test_estat_time_parsing() -> None:
    from country_primer.adapters import estat_time_to_date
    assert estat_time_to_date("2026000808") == "2026-08-01"
    assert estat_time_to_date("2026000707") == "2026-07-01"
    assert estat_time_to_date("1970000000") is None


def test_estat_value_rows_parse_into_observations() -> None:
    import json
    from country_primer.adapters import estat_observations
    payload = json.load(open("tests/fixtures/estat_cpi_sample.json"))
    obs = estat_observations(payload)
    assert obs
    assert all(o["date"][4] == "-" and isinstance(o["value"], float) for o in obs)
    assert obs == sorted(obs, key=lambda o: o["date"])


def test_estat_without_credential_raises_a_typed_error(monkeypatch: pytest.MonkeyPatch) -> None:
    from country_primer.adapters import EstatCredentialMissing, fetch_estat
    monkeypatch.delenv("ESTAT_APP_ID", raising=False)
    with pytest.raises(EstatCredentialMissing):
        fetch_estat(None, {"stats_data_id": "0004052037", "estat_tab": "3", "estat_cat01": "0161"})


def test_fetch_bruegel_reer_returns_sorted_observations() -> None:
    import requests
    from country_primer.adapters import fetch_bruegel_reer
    res = fetch_bruegel_reer(requests.Session(), {"id": "reer_us", "country": "US"})
    assert "observations" in res
    obs = res["observations"]
    assert len(obs) >= 300
    assert obs[-1]["date"] >= "2026-08-01"
    assert all("date" in o and "value" in o for o in obs)
    assert obs == sorted(obs, key=lambda x: x["date"])
    assert res.get("provider_updated") == obs[-1]["date"]


def test_fred_api_observations_caches_duplicate_series_and_redacts_keys(monkeypatch: pytest.MonkeyPatch) -> None:
    from country_primer import adapters

    monkeypatch.setenv("FRED_API_KEY", "supersecretkey123")
    adapters.FRED_OBS_CACHE.clear()
    calls = []

    class DummyResp:
        headers = {"Last-Modified": "Mon, 26 Oct 2026 12:00:00 GMT"}

        def raise_for_status(self) -> None:
            pass

        def json(self) -> dict:
            return {
                "realtime_end": "2026-10-26",
                "observations": [
                    {"date": "2026-08-01", "value": "100.0"},
                    {"date": "2026-09-01", "value": "101.5"},
                ],
            }

    class DummySession:
        def get(self, url: str, params: dict | None = None, timeout: tuple | int | None = None) -> DummyResp:
            calls.append((url, dict(params or {})))
            return DummyResp()

    sess = DummySession()
    obs1, upd1 = adapters._fred_api_observations(sess, {"series": "CPIAUCSL", "start_date": "1990-01-01"})
    obs2, upd2 = adapters._fred_api_observations(sess, {"series": "CPIAUCSL", "start_date": "1990-01-01"})
    assert len(calls) == 1
    assert obs1 == obs2
    assert upd1 == upd2
    assert adapters._redact_fred_key("url?series_id=GDP&api_key=supersecretkey123&file_type=json") == (
        "url?series_id=GDP&api_key=REDACTED&file_type=json"
    )
    adapters.FRED_OBS_CACHE.clear()
