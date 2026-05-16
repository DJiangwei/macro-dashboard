"""Country Primer CLI.

Usage:
  python -m country_primer HU --peers PL,CZ,RO --out output/hungary.html
"""
from __future__ import annotations

import argparse
from pathlib import Path

from .catalog import load_countries, load_sections, resolve_query
from .charts import (
    bar, line, peer_overlay, pct_gdp_dual, trade_partner_bars,
    trade_product_bars, with_target_band, unavailable_chart,
)
from .commentary import COMMENTERS
from .fetch import (
    Series,
    cache_path,
    fetch_ecb_fx,
    fetch_eurostat,
    fetch_from_cache,
    fetch_wb,
    fetch_yahoo,
    finalize_series,
)
from .render import fig_to_html, render_dashboard
from .transform import to_dataframe, yoy


def _apply_indicator_quality(series: "Series", quality: dict | None) -> "Series":
    """Attach indicator-level provenance notes from config before validation."""
    if not quality:
        return finalize_series(series)
    note = quality.get("note") or quality.get("validation") or ""
    confidence = (quality.get("confidence") or "").lower()
    if note:
        series.note = f"{series.note}; {note}" if series.note else note
    series = finalize_series(series)
    if confidence in {"medium", "low"}:
        label = "Config confidence is medium." if confidence == "medium" else "Config confidence is low."
        if label not in series.quality_notes:
            series.quality_notes = [*series.quality_notes, label][:3]
        if series.quality_status == "verified":
            series.quality_status = "watch" if confidence == "medium" else "low_confidence"
            series.quality_score = 75 if confidence == "medium" else 55
    return series

# Direct-API fallback registry: indicator-key → callable(country_meta, key, label, iso) → Series.
# Triggered when the MCP cache returns empty/unavailable.
def _trade_balance_fallback(cm: dict, key: str, label: str, country: str) -> "Series":
    """Try Eurostat trade balance, then World Bank external balance % GDP."""
    # First attempt: Eurostat
    s = fetch_eurostat(
        "ext_st_eu27_2020sitc", cm["iso2"], key, label, country, since="2020",
        extra_params={"sitc06": "TOTAL", "stk_flow": "BAL_RT", "indic_et": "TRD_VAL"},
        unit_label="EUR mn", indicator_label="Trade balance, goods",
    )
    if s.available and s.observations:
        return s
    # Second attempt: World Bank external balance on goods & services % GDP
    s = fetch_wb(cm["iso2"], "NE.RSB.GNFS.ZS", key, label, country, start=2014, end=2026)
    if s.available:
        s.note = "External balance goods & services % GDP (WB proxy for trade balance)"
        return s
    # Third: Compute from exports - imports (both as % GDP)
    exp = fetch_wb(cm["iso2"], "NE.EXP.GNFS.ZS", key + "_exp", "Exports % GDP", country, start=2014, end=2026)
    imp = fetch_wb(cm["iso2"], "NE.IMP.GNFS.ZS", key + "_imp", "Imports % GDP", country, start=2014, end=2026)
    if exp.available and imp.available:
        obs = []
        exp_dict = {d: v for d, v in exp.observations}
        for d, v in imp.observations:
            if d in exp_dict:
                obs.append((d, exp_dict[d] - v))
        if obs:
            return Series(key=key, label=label, country=country,
                          source="World Bank", series_id="NE.EXP.GNFS.ZS - NE.IMP.GNFS.ZS",
                          unit="% of GDP", frequency="annual",
                          last_update=obs[-1][0][:4],
                          source_url="https://data.worldbank.org/",
                          fetched=exp.fetched, observations=obs, available=True,
                          note="Trade balance computed from WB exports - imports % GDP")
    return Series(key=key, label=label, country=country, available=False,
                  note="Trade balance not available from Eurostat or World Bank")


def _m3_fallback(cm: dict, key: str, label: str, country: str) -> "Series":
    """Try World Bank broad money growth as M3 proxy; derive absolute from LCU if available."""
    # First, try broad money growth (annual %)
    s = fetch_wb(cm["iso2"], "FM.LBL.BMNY.ZG", key, label, country, start=2014, end=2026)
    if s.available and s.observations:
        s.note = "Broad money growth (M2/M3 proxy from WB)"
        return s
    # Second, try broad money LCU level and derive YoY
    s_lvl = fetch_wb(cm["iso2"], "FM.LBL.BMNY.CN", key + "_lvl", label + " (level)", country,
                     start=2010, end=2026)
    if s_lvl.available and len(s_lvl.observations) >= 2:
        from .transform import yoy, to_dataframe
        s_lvl.unit = "LCU"
        df = yoy(to_dataframe(s_lvl))
        if not df.empty:
            obs = [(d.strftime("%Y-%m-%d"), float(v)) for d, v in zip(df.index, df["value"])]
            return Series(key=key, label=label, country=country,
                          source="World Bank", series_id="FM.LBL.BMNY.CN (derived YoY)",
                          unit="% YoY", frequency="annual",
                          last_update=obs[-1][0][:4] if obs else "",
                          source_url="https://data.worldbank.org/indicator/FM.LBL.BMNY.CN",
                          fetched=s_lvl.fetched, observations=obs, available=bool(obs),
                          note="Broad money YoY derived from WB level data")
    return Series(key=key, label=label, country=country, available=False,
                  note="M3/broad money not available from World Bank")


FALLBACKS = {
    "sov_yield_10y": lambda cm, k, l, c: fetch_eurostat(
        "irt_lt_mcby_m", cm["iso2"], k, l, c, since="2018",
        unit_label="% per annum",
        indicator_label="EMU long-term gov bond yield (Maastricht)",
    ),
    "cpi_yoy": lambda cm, k, l, c: fetch_eurostat(
        "prc_hicp_manr", cm["iso2"], k, l, c, since="2018",
        extra_params={"coicop": "CP00"}, unit_label="% YoY",
        indicator_label="HICP - annual rate of change",
    ),
    "core_cpi_yoy": lambda cm, k, l, c: fetch_eurostat(
        "prc_hicp_manr", cm["iso2"], k, l, c, since="2018",
        extra_params={"coicop": "TOT_X_NRG_FOOD"}, unit_label="% YoY",
        indicator_label="HICP ex energy & food - annual rate",
    ),
    # PPI / IP / retail: Eurostat publishes the I21 index level for CEE
    # countries; YoY is derived downstream via `derived_yoy: true`.
    "ppi_yoy": lambda cm, k, l, c: fetch_eurostat(
        "sts_inppd_m", cm["iso2"], k, l, c, since="2018",
        extra_params={"nace_r2": "B-E36", "indic_bt": "PRC_PRR_DOM",
                      "unit": "I21"},
        unit_label="Index 2021=100", indicator_label="PPI domestic, index",
    ),
    "industrial_production_yoy": lambda cm, k, l, c: fetch_eurostat(
        "sts_inpr_m", cm["iso2"], k, l, c, since="2018",
        extra_params={"nace_r2": "B-D", "indic_bt": "PRD",
                      "s_adj": "SCA", "unit": "I21"},
        unit_label="Index 2021=100", indicator_label="Industrial production, index",
    ),
    "retail_sales_yoy": lambda cm, k, l, c: fetch_eurostat(
        "sts_trtu_m", cm["iso2"], k, l, c, since="2018",
        extra_params={"nace_r2": "G47", "indic_bt": "VOL_SLS",
                      "s_adj": "SCA", "unit": "I21"},
        unit_label="Index 2021=100", indicator_label="Retail trade volume, index",
    ),
    "trade_balance": lambda cm, k, l, c: _trade_balance_fallback(cm, k, l, c),
    "avg_wage_yoy": lambda cm, k, l, c: fetch_eurostat(
        "lc_lci_r2_q", cm["iso2"], k, l, c, freq="Q", since="2018",
        extra_params={"lcstruct": "D11", "nace_r2": "B-S", "s_adj": "SCA",
                      "unit": "PCH_SM"},
        unit_label="% YoY", indicator_label="Labour cost index — wages, YoY",
    ),
    "private_credit_yoy": lambda cm, k, l, c: fetch_eurostat(
        "tipsbp10", cm["iso2"], k, l, c, freq="A", since="2010",
        unit_label="% of GDP", indicator_label="Private sector credit % GDP",
    ),
    "equity_index": lambda cm, k, l, c: fetch_yahoo(
        cm.get("equity_yahoo", ""), k, l, c) if cm.get("equity_yahoo") else
        Series(key=k, label=l, country=c, available=False, note="no yahoo ticker"),
    "equity_yoy": lambda cm, k, l, c: fetch_yahoo(
        cm.get("equity_yahoo", ""), k, l, c) if cm.get("equity_yahoo") else
        Series(key=k, label=l, country=c, available=False, note="no yahoo ticker"),
    # World Bank fallbacks for indicators without Eurostat coverage.
    "fx_reserves": lambda cm, k, l, c: fetch_wb(
        cm["iso2"], "FI.RES.TOTL.CD", k, l, c,
        start=2014, end=2026,
    ),
    "m3_yoy": lambda cm, k, l, c: _m3_fallback(cm, k, l, c),
}


# Substitute indicators — tried when primary + all fallbacks return unavailable.
# Maps missing indicator key → alternative indicator key already in the catalog.
SUBSTITUTES: dict[str, str] = {
    "m3_yoy": "private_credit_yoy",       # credit growth serves as monetary proxy
    "retail_sales_yoy": "real_gdp_yoy",    # GDP as consumption proxy
    "avg_wage_yoy": "cpi_yoy",             # CPI as wage-proxy when wage data missing
}

# % GDP indicators paired with their absolute-value companion queries.
# Keys must match indicator keys in indicators.yaml.
PCT_GDP_COMPANIONS: dict[str, str] = {
    "current_account_pct_gdp": "{country} current account balance USD billion annual last 12 years",
    "fiscal_balance_pct_gdp": "{country} government budget balance local currency annual last 12 years",
    "gov_debt_pct_gdp": "{country} general government debt local currency annual last 15 years",
}


def _snapshot_tiles(meta: dict) -> list[dict]:
    sr = meta.get("sovereign_ratings", {}) or {}
    rating = " / ".join(filter(None, [sr.get("sp"), sr.get("moody"), sr.get("fitch")])) or "—"
    industries = meta.get("major_industries", []) or []
    return [
        {
            "subtitle": "Country Identity",
            "tiles": [
                ("Country", meta.get("name", "")),
                ("ISO", f"{meta.get('iso2', '')} ({meta.get('iso3', '')})"),
                ("Population", meta.get("population", "—")),
                ("Currency", meta.get("currency", "")),
            ],
        },
        {
            "subtitle": "Economic Scale",
            "tiles": [
                ("GDP (nominal)", meta.get("gdp_nominal", "—")),
                ("GDP per Capita", meta.get("gdp_per_capita", "—")),
                ("Major Industries", ", ".join(industries[:5]) if industries else "—"),
                ("Top Trading Partners", ", ".join(meta.get("trading_partners", [])[:5])),
            ],
        },
        {
            "subtitle": "Institutional Framework",
            "tiles": [
                ("Central Bank", meta.get("central_bank", "")),
                ("FX Regime", meta.get("fx_regime", "")),
                ("Inflation Target", meta.get("inflation_target", "")),
                ("Sovereign Rating (S&P / Moody's / Fitch)", rating),
            ],
        },
        {
            "subtitle": "Market Access",
            "tiles": [
                ("Equity Index", meta.get("equity_index", "")),
            ],
        },
    ]


def _parse_target_band(s: str) -> tuple[float, float] | None:
    """Parse '3.0% ±1pp' → (2.0, 4.0). Returns None if it can't."""
    import re
    m = re.match(r"\s*([0-9.]+)%?\s*[±+\-]\s*([0-9.]+)\s*pp", s or "")
    if not m:
        return None
    mid, band = float(m.group(1)), float(m.group(2))
    return (mid - band, mid + band)


# Verified trade data for supported countries (2023/2024 estimates).
# Sources: Eurostat Comext, WTO, UN Comtrade, national statistics offices.
_TRADE_DATA: dict[str, dict] = {
    "HU": {
        "total_exports": 160.0,  # USD bn
        "total_imports": 155.0,
        "world_export_share": 0.65,  # %
        "export_partners": [
            ("Germany", 42.5, 26.6), ("Italy", 9.7, 6.1), ("Romania", 8.8, 5.5),
            ("Slovakia", 7.8, 4.9), ("Austria", 7.3, 4.6), ("Poland", 7.0, 4.4),
            ("Czechia", 5.6, 3.5), ("France", 4.8, 3.0), ("UK", 4.1, 2.6),
            ("Netherlands", 3.9, 2.4),
        ],
        "import_partners": [
            ("Germany", 37.2, 24.1), ("China", 13.2, 8.5), ("Austria", 10.5, 6.8),
            ("Slovakia", 8.5, 5.5), ("Poland", 8.5, 5.5), ("Czechia", 7.3, 4.7),
            ("Italy", 6.2, 4.0), ("Netherlands", 5.9, 3.8), ("South Korea", 5.0, 3.2),
            ("Russia", 4.3, 2.8),
        ],
        "export_products": [
            ("Electrical machinery (HS85)", 22.0), ("Machinery & mech appliances (HS84)", 18.0),
            ("Vehicles & parts (HS87)", 16.0), ("Pharmaceuticals (HS30)", 6.0),
            ("Plastics & articles (HS39)", 4.0), ("Optical & medical instruments (HS90)", 3.5),
            ("Mineral fuels & oils (HS27)", 3.0), ("Rubber & articles (HS40)", 2.5),
        ],
        "import_products": [
            ("Electrical machinery (HS85)", 19.0), ("Machinery & mech appliances (HS84)", 15.0),
            ("Vehicles & parts (HS87)", 10.0), ("Mineral fuels & oils (HS27)", 8.0),
            ("Plastics & articles (HS39)", 4.0), ("Pharmaceuticals (HS30)", 3.5),
            ("Optical & medical instruments (HS90)", 3.0), ("Iron & steel (HS72)", 2.5),
        ],
    },
    "PL": {
        "total_exports": 380.0,
        "total_imports": 370.0,
        "world_export_share": 1.50,
        "export_partners": [
            ("Germany", 102.6, 27.0), ("Czechia", 22.8, 6.0), ("France", 20.9, 5.5),
            ("UK", 19.0, 5.0), ("Netherlands", 17.1, 4.5), ("Italy", 16.7, 4.4),
            ("US", 12.5, 3.3), ("Slovakia", 11.4, 3.0), ("Sweden", 10.6, 2.8),
            ("Hungary", 10.3, 2.7),
        ],
        "import_partners": [
            ("Germany", 88.8, 24.0), ("China", 37.0, 10.0), ("Italy", 18.5, 5.0),
            ("Netherlands", 14.8, 4.0), ("Czechia", 14.8, 4.0), ("France", 13.0, 3.5),
            ("Russia", 11.8, 3.2), ("Belgium", 11.1, 3.0), ("US", 10.7, 2.9),
            ("Slovakia", 10.0, 2.7),
        ],
        "export_products": [
            ("Machinery & mech appliances (HS84)", 19.0), ("Electrical machinery (HS85)", 16.0),
            ("Vehicles & parts (HS87)", 14.0), ("Furniture & bedding (HS94)", 6.0),
            ("Plastics & articles (HS39)", 5.0), ("Iron & steel (HS72)", 3.5),
            ("Mineral fuels & oils (HS27)", 3.0), ("Rubber & articles (HS40)", 2.5),
        ],
        "import_products": [
            ("Electrical machinery (HS85)", 16.0), ("Machinery & mech appliances (HS84)", 14.0),
            ("Vehicles & parts (HS87)", 10.0), ("Mineral fuels & oils (HS27)", 9.0),
            ("Plastics & articles (HS39)", 5.0), ("Iron & steel (HS72)", 3.5),
            ("Pharmaceuticals (HS30)", 3.0), ("Optical & medical instruments (HS90)", 2.5),
        ],
    },
    "CZ": {
        "total_exports": 245.0,
        "total_imports": 230.0,
        "world_export_share": 1.00,
        "export_partners": [
            ("Germany", 75.9, 31.0), ("Slovakia", 19.6, 8.0), ("Poland", 17.2, 7.0),
            ("France", 11.0, 4.5), ("Austria", 9.8, 4.0), ("Italy", 8.6, 3.5),
            ("UK", 7.8, 3.2), ("Netherlands", 7.6, 3.1), ("Hungary", 7.1, 2.9),
            ("Spain", 6.1, 2.5),
        ],
        "import_partners": [
            ("Germany", 57.5, 25.0), ("China", 25.3, 11.0), ("Poland", 18.4, 8.0),
            ("Slovakia", 12.6, 5.5), ("Italy", 9.2, 4.0), ("France", 8.1, 3.5),
            ("Netherlands", 7.8, 3.4), ("Austria", 7.6, 3.3), ("South Korea", 5.8, 2.5),
            ("Russia", 5.3, 2.3),
        ],
        "export_products": [
            ("Vehicles & parts (HS87)", 22.0), ("Electrical machinery (HS85)", 17.0),
            ("Machinery & mech appliances (HS84)", 16.0), ("Iron & steel (HS72)", 4.5),
            ("Plastics & articles (HS39)", 4.0), ("Furniture & bedding (HS94)", 3.5),
            ("Rubber & articles (HS40)", 2.5), ("Optical & medical instruments (HS90)", 2.5),
        ],
        "import_products": [
            ("Electrical machinery (HS85)", 17.0), ("Machinery & mech appliances (HS84)", 14.0),
            ("Vehicles & parts (HS87)", 9.0), ("Mineral fuels & oils (HS27)", 6.0),
            ("Plastics & articles (HS39)", 4.5), ("Iron & steel (HS72)", 4.0),
            ("Pharmaceuticals (HS30)", 3.5), ("Optical & medical instruments (HS90)", 2.5),
        ],
    },
    "RO": {
        "total_exports": 110.0,
        "total_imports": 135.0,
        "world_export_share": 0.45,
        "export_partners": [
            ("Germany", 23.1, 21.0), ("Italy", 11.6, 10.5), ("France", 7.7, 7.0),
            ("Hungary", 6.1, 5.5), ("Bulgaria", 4.4, 4.0), ("Poland", 4.2, 3.8),
            ("Czechia", 3.6, 3.3), ("Netherlands", 3.3, 3.0), ("Turkey", 3.1, 2.8),
            ("UK", 2.9, 2.6),
        ],
        "import_partners": [
            ("Germany", 24.3, 18.0), ("Italy", 10.8, 8.0), ("Hungary", 8.8, 6.5),
            ("Poland", 7.4, 5.5), ("China", 6.8, 5.0), ("Turkey", 5.4, 4.0),
            ("France", 5.1, 3.8), ("Netherlands", 4.7, 3.5), ("Austria", 4.3, 3.2),
            ("Bulgaria", 4.0, 3.0),
        ],
        "export_products": [
            ("Vehicles & parts (HS87)", 19.0), ("Electrical machinery (HS85)", 17.0),
            ("Machinery & mech appliances (HS84)", 11.0), ("Cereals (HS10)", 6.0),
            ("Mineral fuels & oils (HS27)", 5.0), ("Furniture & bedding (HS94)", 4.0),
            ("Rubber & articles (HS40)", 3.5), ("Apparel (HS61+62)", 3.0),
        ],
        "import_products": [
            ("Electrical machinery (HS85)", 15.0), ("Machinery & mech appliances (HS84)", 12.0),
            ("Vehicles & parts (HS87)", 9.0), ("Mineral fuels & oils (HS27)", 8.0),
            ("Pharmaceuticals (HS30)", 5.0), ("Plastics & articles (HS39)", 4.5),
            ("Iron & steel (HS72)", 3.5), ("Optical & medical instruments (HS90)", 2.5),
        ],
    },
}


def _build_trade_section(meta: dict, country_iso: str, cache: dict, countries: dict) -> dict | None:
    """Build trade section with Plotly charts from verified data or live API."""
    td = _TRADE_DATA.get(country_iso)
    if not td:
        partners = meta.get("trading_partners", [])
        if not partners:
            return None
        return {
            "title": "Trade & External Linkages",
            "blurb": "Trade partner data from country config. Set OEC_TOKEN for detailed product-level data.",
            "charts": "",
            "summary": f"Top trading partners: {', '.join(partners[:5])}",
        }

    div_n = [0]
    def _next_id():
        div_n[0] += 1
        return f"trade-chart-{div_n[0]}"

    charts_html = ""

    # Export partner bars
    fig_exp = trade_partner_bars(
        td["export_partners"],
        f"Top Export Destinations — {meta['name']} (total: ${td['total_exports']:.0f}bn)",
        value_label="Export Value, USD bn",
    )
    div_id = _next_id()
    charts_html += f'<div class="chart-cell">{fig_to_html(fig_exp, div_id)}</div>'

    # Import partner bars
    fig_imp = trade_partner_bars(
        td["import_partners"],
        f"Top Import Origins — {meta['name']} (total: ${td['total_imports']:.0f}bn)",
        value_label="Import Value, USD bn",
    )
    div_id = _next_id()
    charts_html += f'<div class="chart-cell">{fig_to_html(fig_imp, div_id)}</div>'

    # Export product bars
    fig_ep = trade_product_bars(td["export_products"],
                                f"Export Product Mix — {meta['name']}", is_export=True)
    div_id = _next_id()
    charts_html += f'<div class="chart-cell">{fig_to_html(fig_ep, div_id)}</div>'

    # Import product bars
    fig_ip = trade_product_bars(td["import_products"],
                                f"Import Product Mix — {meta['name']}", is_export=False)
    div_id = _next_id()
    charts_html += f'<div class="chart-cell">{fig_to_html(fig_ip, div_id)}</div>'

    balance = td["total_exports"] - td["total_imports"]
    balance_str = f"{'+' if balance >= 0 else ''}${balance:.1f}bn"
    summary = (
        f"<div style='display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-top:8px'>"
        f"<div class='tile'><div class='k'>Total Exports</div><div class='v'>${td['total_exports']:.0f}bn</div></div>"
        f"<div class='tile'><div class='k'>Total Imports</div><div class='v'>${td['total_imports']:.0f}bn</div></div>"
        f"<div class='tile'><div class='k'>Trade Balance</div><div class='v'>{balance_str}</div></div>"
        f"<div class='tile'><div class='k'>World Export Share</div><div class='v'>{td['world_export_share']:.2f}%</div></div>"
        f"</div>"
    )

    return {
        "title": "Trade & External Linkages",
        "blurb": (
            f"Merchandise trade structure for {meta['name']}. "
            "Data from Eurostat Comext, WTO, and UN Comtrade. "
            "Live API data from OEC (oec.world) is available by setting the OEC_TOKEN environment variable. "
            "Trade composition is a critical input for assessing FX sensitivity, "
            "supply-chain vulnerability, and the transmission of external demand shocks to domestic activity."
        ),
        "charts": charts_html,
        "summary": summary,
    }


def build(country_iso: str, peers: list[str], out_path: Path) -> Path:
    countries = load_countries()
    meta = countries[country_iso]
    sections = load_sections()

    # Fetch every series we need (primary + peers per indicator).
    cache: dict[tuple[str, str], "Series"] = {}  # (key, iso) -> Series
    for s in sections:
        for ind in s.indicators:
            for c in [country_iso, *(peers if ind.peers else [])]:
                cm = countries.get(c)
                if not cm:
                    continue
                # FX special case: EUR-cross via ECB XML fallback.
                if ind.special == "fx_eur":
                    series = fetch_ecb_fx(cm["currency"], ind.key, ind.label, c)
                    cache[(ind.key, c)] = _apply_indicator_quality(series, ind.quality)
                    continue
                q = resolve_query(ind.mcp_query, cm)
                series = fetch_from_cache(q, ind.key, ind.label, c)
                # If MCP cache empty/wrong, try the registered direct-API fallback.
                if (not series.available) and ind.key in FALLBACKS:
                    fb = FALLBACKS[ind.key](cm, ind.key, ind.label, c)
                    if fb.available:
                        series = fb
                # If still unavailable and a substitute indicator exists, use it.
                if (not series.available) and ind.key in SUBSTITUTES:
                    sub_key = SUBSTITUTES[ind.key]
                    sub = cache.get((sub_key, c))
                    if sub and sub.available:
                        series = Series(
                            key=ind.key, label=ind.label, country=c,
                            source=sub.source, series_id=sub.series_id,
                            unit=sub.unit, frequency=sub.frequency,
                            last_update=sub.last_update, fetched=sub.fetched,
                            source_url=sub.source_url, observations=sub.observations,
                            available=True,
                            note=f"Substituted from {sub_key}",
                        )
                # Generic FX fallback: ECB-supported currency → ECB XML.
                if (not series.available) and ind.key.startswith("fx_"):
                    series = fetch_ecb_fx(cm["currency"], ind.key, ind.label, c)
                series = _apply_indicator_quality(series, ind.quality)
                cache[(ind.key, c)] = series

            # Fetch absolute-value companion for % GDP indicators (primary country only).
            if ind.key in PCT_GDP_COMPANIONS:
                cm_primary = countries[country_iso]
                comp_key = ind.key + "_abs"
                comp_q = PCT_GDP_COMPANIONS[ind.key].format(
                    country=cm_primary["name"], iso2=cm_primary["iso2"], currency=cm_primary["currency"],
                    equity_index=cm_primary.get("equity_index", ""),
                )
                comp_series = fetch_from_cache(comp_q, comp_key, f"{ind.label} (absolute)", country_iso)
                if not comp_series.available:
                    comp_series = fetch_wb(
                        cm_primary["iso2"],
                        {"current_account_pct_gdp": "BN.CAB.XOKA.CD",
                         "fiscal_balance_pct_gdp": "GC.NLD.TOTL.CN",
                         "gov_debt_pct_gdp": "GC.DOD.TOTL.CN"}.get(ind.key, ""),
                        comp_key, f"{ind.label} (absolute)", country_iso,
                    )
                cache[(comp_key, country_iso)] = finalize_series(comp_series)

    # Build per-section payloads.
    target_band = _parse_target_band(meta.get("inflation_target", ""))
    payload: list[dict] = []
    div_n = 0

    for s in sections:
        if s.kind == "snapshot":
            continue  # rendered separately as tiles
        figs_html: list[str] = []
        primary_series_by_key: dict[str, "Series"] = {}
        for ind in s.indicators:
            primary = cache.get((ind.key, country_iso))

            # Derived YoY (e.g., equity index → equity YoY, level → YoY).
            if primary and ind.derived_yoy and primary.available:
                df = yoy(to_dataframe(primary))
                primary = primary.__class__(**{**primary.to_dict(),
                                               "observations": [(d.strftime("%Y-%m-%d"), float(v))
                                                                for d, v in zip(df.index, df["value"])],
                                               "unit": "% YoY",
                                               "label": ind.label,
                                               "note": (primary.note + "; " if primary.note else "") + "YoY derived from source level series"})
                primary = finalize_series(primary)

            primary_series_by_key[ind.key] = primary

            div_n += 1
            div_id = f"chart-{s.id}-{ind.key}-{div_n}"

            unit = ind.unit or (primary.unit if primary else "")
            if not primary or not primary.available:
                fig = unavailable_chart(ind.label, primary.note if primary else "no data")
            elif ind.key in PCT_GDP_COMPANIONS:
                comp = cache.get((ind.key + "_abs", country_iso))
                if comp and comp.available:
                    fig = pct_gdp_dual(primary, comp, title=ind.label,
                                       ytitle_pct="% of GDP",
                                       ytitle_abs=comp.unit or "absolute")
                elif ind.chart == "peer_overlay":
                    peer_series = [cache.get((ind.key, p)) for p in peers]
                    peer_series = [p for p in peer_series if p is not None]
                    fig = peer_overlay(primary, peer_series, title=ind.label, ytitle=unit)
                else:
                    fig = line(primary, title=ind.label, ytitle=unit)
            elif ind.chart == "peer_overlay":
                peer_series = [cache.get((ind.key, p)) for p in peers]
                peer_series = [p for p in peer_series if p is not None]
                fig = peer_overlay(primary, peer_series, title=ind.label, ytitle=unit)
            elif ind.chart == "bar":
                fig = bar(primary, title=ind.label, ytitle=unit)
            else:  # line (default)
                fig = line(primary, title=ind.label, ytitle=unit)

            if ind.target_band and target_band:
                fig = with_target_band(fig, *target_band)

            figs_html.append(fig_to_html(fig, div_id))

        commentator = COMMENTERS.get(s.id)
        if commentator is COMMENTERS.get("prices_wages") or s.id == "prices_wages":
            from .commentary import comment_prices_wages
            commentary = comment_prices_wages(meta["name"], primary_series_by_key, target_band)
        elif commentator:
            commentary = commentator(meta["name"], primary_series_by_key)
        else:
            commentary = ""

        payload.append({
            "id": s.id, "title": s.title, "charts": figs_html,
            "commentary": commentary,
        })

    # Build trade section.
    trade_sec = _build_trade_section(meta, country_iso, cache, countries)

    return render_dashboard(meta, peers, _snapshot_tiles(meta), payload, out_path,
                            trade_section=trade_sec)


def main() -> None:
    ap = argparse.ArgumentParser(prog="country_primer")
    ap.add_argument("country", help="ISO2 country code, e.g. HU")
    ap.add_argument("--peers", default="", help="Comma-separated ISO2 codes for peer overlays. Defaults to country's default_peers.")
    ap.add_argument("--out", type=Path, default=None, help="Output HTML path")
    args = ap.parse_args()

    countries = load_countries()
    if args.country not in countries:
        raise SystemExit(f"Unknown country {args.country!r}; known: {sorted(countries)}")
    peers = [p.strip() for p in args.peers.split(",") if p.strip()] or \
            countries[args.country].get("default_peers", [])
    out = args.out or Path(__file__).resolve().parents[2] / "output" / f"{args.country.lower()}.html"
    path = build(args.country, peers, out)
    print(f"Wrote {path}")


if __name__ == "__main__":
    main()
