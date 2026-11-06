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


# Rows trimmed from CBN's money-market indicators API (2026-11-05).
CBN_MONEY_MARKET_ROWS = [
    {"tyear": 2026, "tmonth": 9, "period": "September 2026", "mpr": "23.00", "interBankCallRate": "22.00"},
    {"tyear": 2026, "tmonth": 8, "period": "August 2026", "mpr": "26.50", "interBankCallRate": "22.00"},
    {"tyear": 2006, "tmonth": 11, "period": "November 2006", "mpr": "0.00", "interBankCallRate": "9.10"},
    {"tyear": 2006, "tmonth": 10, "period": "October 2006", "mpr": "", "interBankCallRate": "8.20"},
]


def test_cbn_money_market_reads_one_field_monthly_and_drops_placeholder_zeros(monkeypatch) -> None:
    from country_primer import adapters

    class Response:
        def raise_for_status(self):
            return None

        def json(self):
            return CBN_MONEY_MARKET_ROWS

    monkeypatch.setattr(adapters.requests, "get", lambda url, headers=None, timeout=None: Response())
    out = adapters.fetch_cbn_money_market({"id": "policy_rate", "measure": "mpr", "start_date": "2006-01-01"})
    # Before December 2006 the field is "0.00" or blank: the MPR did not exist yet.
    assert out["observations"] == [{"date": "2026-08-01", "value": 26.5}, {"date": "2026-09-01", "value": 23.0}]
    assert out["provider_updated"] == "2026-09-01"
    call = adapters.fetch_cbn_money_market({"id": "x", "measure": "interBankCallRate"})
    assert [o["value"] for o in call["observations"]] == [8.2, 9.1, 22.0, 22.0]


def test_bls_api_batches_every_us_config_series_once(monkeypatch) -> None:
    # The module-level BLS cache and the US config loader were lost when the
    # fetchers moved into adapters.py, so every live BLS call raised NameError.
    from country_primer import adapters
    batches: list[list[str]] = []

    def fake_batch(session, specs):
        batches.append(sorted(str(item["series"]) for item in specs))
        return {series: [{"date": "2026-04-01", "value": 7000.0}] for series in batches[-1]}

    monkeypatch.setattr(adapters, "_fetch_bls_batch", fake_batch)
    series = "BDS0000000000000000110001LQ5"
    first = adapters.fetch_bls_api(None, {"series": series, "start_date": "2015-01-01"})
    assert first["observations"] == [{"date": "2026-04-01", "value": 7000.0}]
    assert len(batches) == 1 and series in batches[0] and len(batches[0]) > 1
    adapters.fetch_bls_api(None, {"series": batches[0][-1]})
    assert len(batches) == 1, "the batch result should serve the other BLS series"


class _CountingSession:
    def __init__(self, text: str = "", content: bytes = b"") -> None:
        self.calls = 0
        self.text, self.content = text, content

    def get(self, url, headers=None, timeout=None):
        self.calls += 1
        session = self

        class Response:
            text, content = session.text, session.content

            def raise_for_status(self) -> None:
                return None

        return Response()


def test_govuk_distribution_and_workbook_downloads_are_cached_per_build() -> None:
    # UK fetchers share one distribution lookup and one workbook download per
    # build; the caches backing that were undefined, failing 63 UK series live.
    from country_primer import adapters
    page = _CountingSession(text=(
        '<script type="application/ld+json">{"distribution": '
        '[{"name": "Monthly fuel prices", "contentUrl": "https://assets.example/fuel-test.csv"}]}</script>'
    ))
    spec = {"source_url": "https://www.gov.uk/test-cache-page", "distribution_name_contains": "fuel"}
    expected = ("https://assets.example/fuel-test.csv", "Monthly fuel prices")
    assert adapters._govuk_distribution_url(page, spec, ".csv") == expected
    assert adapters._govuk_distribution_url(page, spec, ".csv") == expected
    assert page.calls == 1

    workbook = _CountingSession(content=b"xlsx-bytes")
    url = "https://assets.example/test-cache-workbook.xlsx"
    assert adapters._download_binary(workbook, url) == b"xlsx-bytes"
    assert adapters._download_binary(workbook, url) == b"xlsx-bytes"
    assert workbook.calls == 1


def _imf_sdmx_specs(node):
    if isinstance(node, dict):
        if node.get("fetcher") == "imf_sdmx":
            yield node
        for value in node.values():
            yield from _imf_sdmx_specs(value)
    elif isinstance(node, list):
        for value in node:
            yield from _imf_sdmx_specs(value)


def test_fsic_specs_use_the_agency_qualified_dataflow() -> None:
    # api.imf.org answers 403 to the bare FSIC flow (every key, 2026-11-06) and
    # 200 to IMF.STA,FSIC; four 403s open the imf_sdmx circuit for the scope.
    from pathlib import Path
    import yaml
    paths = sorted(Path("config").glob("*.yaml")) + sorted(Path("config/countries").glob("*.yaml"))
    fsic = [
        (path.name, spec.get("id"), spec["dataflow"])
        for path in paths
        for spec in _imf_sdmx_specs(yaml.safe_load(path.read_text()))
        if str(spec.get("dataflow", "")).endswith("FSIC")
    ]
    assert fsic, "expected the Japan and South Africa FSIC series"
    assert [item for item in fsic if item[2] != "IMF.STA,FSIC"] == []


def test_akshare_timeout_does_not_keep_the_process_alive() -> None:
    # A timed-out AKShare call used to leave a non-daemon pool thread behind,
    # and interpreter exit waits for such threads: on 2026-11-06 slow AKShare
    # pages kept build_scope alive after every page was written, until the
    # refresh job hit its 25-minute limit.
    import os
    import subprocess
    import sys
    import time
    code = (
        "import time\n"
        "from country_primer.adapters import _call_with_timeout\n"
        "try:\n"
        "    _call_with_timeout(time.sleep, [20], {}, 1, 'slow_source')\n"
        "except TimeoutError as exc:\n"
        "    print(exc)\n"
    )
    env = {**os.environ, "PYTHONPATH": "src"}
    started = time.monotonic()
    result = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, timeout=15, env=env)
    elapsed = time.monotonic() - started
    assert "timed out after 1s for slow_source" in result.stdout, result.stderr
    assert elapsed < 10, f"process lingered {elapsed:.1f}s after the timeout"


def test_akshare_timeout_wrapper_returns_values_and_reraises_errors() -> None:
    from country_primer.adapters import _call_with_timeout

    assert _call_with_timeout(lambda x, y=0: x * 2 + y, [3], {"y": 1}, 5, "ok") == 7

    def broken() -> None:
        raise ValueError("source changed its schema")

    with pytest.raises(ValueError, match="source changed its schema"):
        _call_with_timeout(broken, [], {}, 5, "broken")
