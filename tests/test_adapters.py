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


def test_scope_builders_are_not_reintroduced() -> None:
    """Pages are built by scripts/build_scope.py from config/scopes.yaml."""
    from pathlib import Path
    per_scope = sorted(p.name for p in Path("scripts").glob("build_*_dashboard.py") if p.name != "build_my_dashboard.py")
    assert per_scope == [], f"per-country builders are back: {per_scope}"


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


# Trimmed from the live PBC English indicator pages (2026-11-05). The DR007 page
# repeats its title in <title> and the nav before the value, and fills "Latest
# Update" in the browser with the viewer's own date, so the HTML carries none.
PBC_DR007_PAGE = """<html><head><title>DR007</title>
<meta  name="createDate" content="2026-09-23 17:51:08" /></head><body>
<div>Old Version</div><div>|</div><div>中文</div><div>About PBC</div><div>Purposes and Functions</div>
<div>Management Team</div><div>Former Governors</div><div>History</div><div>Organizational Structure</div>
<div>News &amp; Events</div><div>Monetary Policy</div><div>Financial Stability</div><div>Financial Markets</div>
<div>Statistics</div><div>Payment System</div><div>Currency</div><div>International Cooperation</div>
<div>Research</div><div>Laws &amp; Rules</div><div>Publications</div>
<ul><li><a>DR007</a></li><li><a>M2</a></li><li><a>USD/CNY Fixing Rate</a></li><li><a>AFRE (Outstanding)</a></li></ul>
<div>Home &gt; Indicators &gt; DR007</div>
<ul><li><p>DR007</p><p>What is DR007?</p><p>DR007 is the interest rate on 7-day repos.</p></li></ul>
<ul class="rateNum clearfix"><li class="li1"> <p class="rateNumName one"><a title="DR007">DR007</a></p>
<p class="two"><a title="1.4935%">1.4935%</a></p> <p class="three">Latest Update</p> <p id="time"></p> </li></ul>
<script>document.getElementById('time').innerHTML=""+day+"/"+month+"/"+year;</script>
</body></html>"""

PBC_M2_PAGE = """<html><head><title>M2</title>
<meta  name="createDate" content="2026-10-19 13:58:39" /></head><body>
<ul><li><a>DR007</a></li><li><a>M2</a></li><li><a>USD/CNY Fixing Rate</a></li></ul>
<ul><li><p>M2</p><p>What is M2?</p><p>The M2 changes year on year reported here is for the end of previous month.</p></li></ul>
<ul class="rateNum clearfix"><li class="li1"> <p class="rateNumName one"><a title="M2 (YoY)">M2 (YoY)</a></p>
<p class="two"><a title="7.2%">7.2%</a></p> <p class="three">Latest Update</p> <p id="time">10/19/2026 </p> </li></ul>
</body></html>"""


class _FakePage:
    def __init__(self, text):
        self.text = text

    def raise_for_status(self):
        return None


@pytest.mark.parametrize(
    ("page", "title", "value", "updated"),
    [(PBC_DR007_PAGE, "DR007", "1.4935%", "09/23/2026"), (PBC_M2_PAGE, "M2", "7.2%", "10/19/2026")],
)
def test_pbc_card_reads_the_value_after_any_title_match_and_dates_it(monkeypatch, page, title, value, updated) -> None:
    from country_primer import adapters
    monkeypatch.setattr(adapters.requests, "get", lambda url, timeout=None: _FakePage(page))
    card = adapters.fetch_pbc_card({"url": "https://www.pbc.gov.cn/en/x/index.html", "expected_title": title})
    assert card["value"] == value
    assert card["updated"] == updated  # never the viewer's date: static text, else the page's createDate


# Rows trimmed from nationalbank.kz's base-rate decision table (2026-11-05):
# a rate split across <span>s by the CMS, a plain row, and a scheduled meeting.
NBK_DECISIONS_PAGE = """<a href="/en/news/grafik-prinyatiya-resheniy-po-bazovoy-stavke/rubrics/2237">2025</a>
<a href="/en/news/grafik-prinyatiya-resheniy-po-bazovoy-stavke/rubrics/2365">2026</a>
<table><tr><td>Decision on the base rate (effective from)</td><td>Base rate, %</td><td>Base rate corridor, %</td></tr>
<tr> <td><span>07.09.2026</span></td> <td width="98"> <p class="MsoNormal" align="center"><span>16</span><span lang="EN-US">.</span><span>25</span></p> </td> <td width="102"> <p class="MsoNormal" align="center"><span>15</span><span lang="EN-US">.</span><span>25 - 17</span><span lang="EN-US">.</span><span>25</span></p> </td> <td><span><a>link</a><br>The base rate reduced to 16.25%</span></td> </tr>
<tr> <td> <p><span>27.10.2026</span></p> </td> <td>15.75</td> <td>14.75 - 16.75</td> <td> <p><span><a>link</a><br>The base rate reduced to 15.75%</span></p> </td> </tr>
<tr> <td><span>04.12.2026*</span></td> <td>&nbsp;</td> <td>&nbsp;</td> <td>&nbsp;</td> </tr>
</table>"""


def test_nbk_base_rate_rows_join_split_numbers_and_skip_scheduled_meetings() -> None:
    from country_primer.adapters import nbk_year_pages, parse_nbk_base_rate_table
    assert parse_nbk_base_rate_table(NBK_DECISIONS_PAGE) == [("2026-09-07", 16.25), ("2026-10-27", 15.75)]
    assert nbk_year_pages(NBK_DECISIONS_PAGE) == [
        "https://nationalbank.kz/en/news/grafik-prinyatiya-resheniy-po-bazovoy-stavke/rubrics/2237",
        "https://nationalbank.kz/en/news/grafik-prinyatiya-resheniy-po-bazovoy-stavke/rubrics/2365",
    ]


def test_nbk_base_rate_events_end_with_an_as_of_row(monkeypatch) -> None:
    from datetime import date

    from country_primer import adapters
    year_2025 = "<table><tr> <td>15.12.2025</td> <td>18.00</td> <td>17.00 - 19.00</td> </tr></table>"
    pages = {adapters.NBK_BASE_RATE_URL: NBK_DECISIONS_PAGE}
    monkeypatch.setattr(adapters, "_nbk_get", lambda url: pages.get(url, year_2025))
    out = adapters.fetch_nbk_base_rate({"id": "policy_rate", "start_date": "2025-01-01"}, today=date(2026, 11, 5))
    assert out["observations"] == [
        {"date": "2025-12-15", "value": 18.0},
        {"date": "2026-09-07", "value": 16.25},
        {"date": "2026-10-27", "value": 15.75},
        {"date": "2026-11-05", "value": 15.75},  # as-of row: the last decision is still in force
    ]
    assert out["provider_updated"] == "2026-10-27"
