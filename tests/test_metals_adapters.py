"""Base- and precious-metals sources (metals_adapters)."""
import pytest

DAYS = ["2025-12-29", "2025-12-30", "2025-12-31", "2026-01-02", "2026-01-30", "2026-02-02", "2026-02-09"]
# One constant settle per contract, so each spread value names the pair used.
LEVELS = {"2601": 100.0, "2602": 110.0, "2603": 125.0, "2604": 145.0, "2605": 170.0}


def _settles() -> dict[str, dict[str, float]]:
    return {code: {day: level for day in DAYS} for code, level in LEVELS.items()}


def _spread(settles=None) -> dict[str, float]:
    from country_primer.metals_adapters import calendar_spread

    rows = calendar_spread(settles or _settles(), start="2025-12-01", today="2026-02-10")
    return {row["date"]: row["value"] for row in rows}


def test_spread_uses_near_and_third_month() -> None:
    assert _spread()["2025-12-30"] == LEVELS["2601"] - LEVELS["2603"]


def test_spread_rolls_on_last_trading_day_before_delivery_month() -> None:
    spread = _spread()
    assert spread["2025-12-31"] == LEVELS["2602"] - LEVELS["2604"]
    assert spread["2026-01-30"] == LEVELS["2603"] - LEVELS["2605"]


def test_current_month_is_not_rolled_early() -> None:
    assert _spread()["2026-02-09"] == LEVELS["2603"] - LEVELS["2605"]


def test_days_missing_a_leg_are_skipped() -> None:
    settles = _settles()
    del settles["2603"]["2025-12-30"]
    spread = _spread(settles)
    assert "2025-12-30" not in spread
    assert "2025-12-29" in spread


def test_contract_months_span_start_to_three_ahead() -> None:
    from country_primer.metals_adapters import contract_months

    assert contract_months("2025-11-15", "2026-01-20") == ["2511", "2512", "2601", "2602", "2603", "2604"]


def _comex_frame(tonnes_column: str = "COMEX黄金库存量-吨"):
    import pandas as pd

    return pd.DataFrame({
        "序号": [1, 2, 3],
        "日期": ["2026-11-03", "2026-11-04", "2026-11-06"],
        tonnes_column: [719.26, 715.29, 700.0],
        "COMEX黄金库存量-盎司": [23124670.0, 22997130.0, 22505000.0],
    })


def test_comex_observations_reads_tonnes_and_drops_today() -> None:
    from country_primer.metals_adapters import comex_observations

    assert comex_observations(_comex_frame(), today="2026-11-06") == [
        {"date": "2026-11-03", "value": 719.26},
        {"date": "2026-11-04", "value": 715.29},
    ]


def test_comex_observations_require_a_tonnes_column() -> None:
    from country_primer.metals_adapters import comex_observations

    with pytest.raises(ValueError, match="-吨"):
        comex_observations(_comex_frame("COMEX黄金库存量-千克"), today="2026-11-06")


def test_bcch_observations_parses_ok_rows_only() -> None:
    from country_primer.metals_adapters import bcch_observations

    payload = {"Codigo": 0, "Series": {"Obs": [
        {"indexDateString": "01-07-2026", "value": "444.1", "statusCode": "OK"},
        {"indexDateString": "01-08-2026", "value": "NaN", "statusCode": "ND"},
    ]}}
    assert bcch_observations(payload) == [{"date": "2026-07-01", "value": 444.1}]


def test_bcch_error_code_raises_without_details() -> None:
    from country_primer.metals_adapters import bcch_observations

    with pytest.raises(RuntimeError, match="code -5"):
        bcch_observations({"Codigo": -5, "Descripcion": "Invalid username or password"})


def _minem_workbook(copper_header: str = "COBRE\nCopper", unit: str = "TMF\nFTM") -> bytes:
    # Mirrors S01.C01 of MINEM's metallic-production workbook (probed 2026-11-06):
    # labels in column C, and below the months, after a blank row, a
    # year-on-year block whose labels ("Ago. 2025") also start with a month.
    import io

    import openpyxl

    book = openpyxl.Workbook()
    sheet = book.active
    sheet.title = "S01.C01"
    sheet["C3"] = "SECCIÓN N° 01: PRODUCCIÓN MINERA METÁLICA"
    sheet.append([])
    rows = [
        ["PERIODO\nPeriod", copper_header, "ORO*\nGold"],
        [None, unit, "gf\nfg"],
        [2024, 2736237.1, 109624691.9],
        [2025, 2765994.5, 109952906.8],
        ["2026\n(Ene-Ago)\n(Jan-Aug)", 449750.4, 16341614.4],
        ["Ene. / Jan.", 226465.1, 8854678.9],
        ["Feb. / Feb.", 223285.3, 7486935.5],
        [None, None, None],
        ["VARIACIÓN INTERANUAL, AGOSTO 2026", None, None],
        ["Feb. 2025\n(Feb. 2025)", 199999.0, 7000000.0],
        ["Var. %", -0.02, 0.01],
    ]
    for offset, row in enumerate(rows):
        for column, value in enumerate(row, start=3):
            sheet.cell(row=9 + offset, column=column, value=value)
    buffer = io.BytesIO()
    book.save(buffer)
    return buffer.getvalue()


def test_latest_release_picks_highest_prepublication_id() -> None:
    from country_primer.metals_adapters import latest_minem_release

    html = (
        '<a href="/institucion/minem/informes-publicaciones/8604205-cuadros-estadisticos-mineros-prepublicacion-del-bem-julio-2026">'
        '<a href="/institucion/minem/informes-publicaciones/8737012-boletin-estadistico-minero-agosto-2026">'
        '<a href="/institucion/minem/informes-publicaciones/8736267-cuadros-estadisticos-mineros-prepublicacion-del-bem-agosto-2026">'
    )
    assert latest_minem_release(html).endswith("8736267-cuadros-estadisticos-mineros-prepublicacion-del-bem-agosto-2026")


def test_workbook_url_picks_metallic_production() -> None:
    from country_primer.metals_adapters import minem_workbook_url

    html = (
        '<a href="https://cdn.www.gob.pe/uploads/document/file/1/8736267-s04-exportaciones-mineras-ed-8-2026.xlsx?v=1">'
        '<a href="https://cdn.www.gob.pe/uploads/document/file/2/8736267-s01-produccion-minera-metalica-ed-8-2026.xlsx?v=1">'
    )
    assert minem_workbook_url(html) == "https://cdn.www.gob.pe/uploads/document/file/2/8736267-s01-produccion-minera-metalica-ed-8-2026.xlsx?v=1"


def test_parse_reads_copper_column_by_header() -> None:
    from country_primer.metals_adapters import parse_minem_copper

    parsed = parse_minem_copper(_minem_workbook())
    assert [row["date"] for row in parsed["annual"]] == ["2024-01-01", "2025-01-01"]
    assert [row["value"] for row in parsed["annual"]] == pytest.approx([2736.2371, 2765.9945])
    assert [row["date"] for row in parsed["monthly"]] == ["2026-01-01", "2026-02-01"]
    assert [row["value"] for row in parsed["monthly"]] == pytest.approx([226.4651, 223.2853])


def test_parse_rejects_a_moved_copper_column() -> None:
    from country_primer.metals_adapters import parse_minem_copper

    with pytest.raises(ValueError, match="COBRE"):
        parse_minem_copper(_minem_workbook(copper_header="ZINC\nZinc"))


def test_parse_rejects_a_non_tonne_unit() -> None:
    from country_primer.metals_adapters import parse_minem_copper

    with pytest.raises(ValueError, match="TMF"):
        parse_minem_copper(_minem_workbook(unit="kgf\nfkg"))


def test_minem_failure_is_reported_once_per_build(monkeypatch) -> None:
    # Review fix: both Peru indicators and their retries used to hit gob.pe
    # again; six 403s/timeouts open the circuit, which blocks the publish.
    import requests

    from country_primer import metals_adapters
    from country_primer.source_health import classify_failure

    calls = []

    def blocked(self, url, **kwargs):
        calls.append(url)
        response = requests.Response()
        response.status_code = 403
        raise requests.HTTPError("403 Client Error: Forbidden", response=response)

    monkeypatch.setattr(requests.Session, "get", blocked)
    cache: dict = {}
    with pytest.raises(requests.HTTPError) as first:
        metals_adapters.fetch_minem_copper({"measure": "monthly"}, cache)
    assert classify_failure(first.value) == "authentication"
    with pytest.raises(RuntimeError, match="earlier in this build") as again:
        metals_adapters.fetch_minem_copper({"measure": "annual"}, cache)
    assert classify_failure(again.value) == "unexpected_error"
    assert len(calls) == 1


def test_spread_rolls_on_a_saturday_after_a_friday_month_end() -> None:
    # Review fix: on Saturday 2026-01-31 no January session remains, so Friday
    # 01-30 is January's last trading day and already uses the next pair.
    from country_primer.metals_adapters import calendar_spread

    days = ["2025-12-31", "2026-01-29", "2026-01-30"]
    settles = {code: {day: level for day in days} for code, level in LEVELS.items()}
    spread = {row["date"]: row["value"] for row in calendar_spread(settles, start="2025-12-01", today="2026-01-31")}
    assert spread["2026-01-29"] == LEVELS["2602"] - LEVELS["2604"]
    assert spread["2026-01-30"] == LEVELS["2603"] - LEVELS["2605"]


def _patch_contract_fetch(monkeypatch, failing: set[str]):
    from country_primer import adapters, metals_adapters

    calls = []

    def fake(fn, args, kwargs, timeout_seconds, label):
        symbol = kwargs["symbol"]
        calls.append(symbol)
        if symbol in failing or "*" in failing:
            raise TimeoutError(f"AKShare fetch timed out after {timeout_seconds}s for {label}")
        level = LEVELS[symbol[2:]]
        return {"date": DAYS, "settle": [level] * len(DAYS)}

    monkeypatch.setattr(adapters, "_call_with_timeout", fake)
    monkeypatch.setattr(metals_adapters, "contract_months", lambda start, today: list(LEVELS))
    return calls


def test_spread_gives_up_after_consecutive_contract_failures(monkeypatch) -> None:
    # Review fix: with Sina unreachable, 38 contracts × 30 s × 3 attempts
    # outlasted the 25-minute refresh job.
    from country_primer.metals_adapters import fetch_cn_futures_calendar_spread

    calls = _patch_contract_fetch(monkeypatch, {"*"})
    with pytest.raises(RuntimeError, match="consecutive"):
        fetch_cn_futures_calendar_spread({"series": "CU", "start_date": "2025-12-01"})
    assert len(calls) == 3


def test_spread_notes_skipped_contracts(monkeypatch) -> None:
    from country_primer.metals_adapters import fetch_cn_futures_calendar_spread

    _patch_contract_fetch(monkeypatch, {"CU2603"})
    result = fetch_cn_futures_calendar_spread({"series": "CU", "start_date": "2025-12-01"})
    assert "CU2603" in " ".join(result["quality_notes"])
    assert "2025-12-30" not in {row["date"] for row in result["observations"]}  # 2601−2603 needs the skipped leg
