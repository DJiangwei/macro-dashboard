"""Canonical data pipeline for the CEE-4 macro dashboard.

This module is intentionally separate from HTML/chart generation. Fetchers
produce one long-form table with columns:

    country, date, indicator_id, value

The current implementation is cache/API/proxy aware: it first tries the
existing project fetch stack, then emits transparent research proxies for
indicators whose public-source adapter is not yet wired. That keeps every
dashboard section populated while marking data quality clearly.
"""
from __future__ import annotations

import calendar
import csv
from dataclasses import dataclass
from datetime import datetime
import io
import json
import math
import os
from pathlib import Path
import re
import subprocess
from html.parser import HTMLParser
import time
from typing import Iterable
from urllib.parse import urlencode
from xml.etree import ElementTree as ET
import zipfile

import requests
import yaml

from .catalog import load_countries
from .fetch import CACHE_DIR, Series, cache_path, fetch_ecb_fx, fetch_eurostat, fetch_wb, fetch_yahoo, finalize_series


CANONICAL_COLUMNS = [
    "country",
    "date",
    "indicator_id",
    "value",
    "label",
    "section_id",
    "unit",
    "source",
    "series_id",
    "quality_status",
    "quality_note",
    "is_proxy",
]


FREQUENCY_STALE_DAYS = {
    "daily": 14,
    "monthly": 125,
    "quarterly": 220,
    "semiannual": 420,
    "seasonal": 250,
    "annual": 900,
    "event": 420,
}


FREQUENCY_GAP_DAYS = {
    "daily": 10,
    "monthly": 70,
    "quarterly": 130,
    "semiannual": 250,
    "seasonal": 220,
    "annual": 500,
    "event": 900,
}


WORLD_BANK_ESG_URL = "https://esgdata.worldbank.org/dist/content/data/download/esgdata_download-2026-01-09.xlsx"
IMF_DATAMAPPER_URL = "https://www.imf.org/external/datamapper/api/v1/{indicator}/{iso3}"
FRED_OBSERVATIONS_URL = "https://api.stlouisfed.org/fred/series/observations"
FRED_GRAPH_CSV_URL = "https://fred.stlouisfed.org/graph/fredgraph.csv"
BIS_CREDIT_GAP_URL = "https://data.bis.org/static/bulk/WS_CREDIT_GAP_csv_flat.zip"
BIS_CBTA_URL = "https://data.bis.org/static/bulk/WS_CBTA_csv_flat.zip"
DBNOMICS_BIS_LBS_SERIES_URL = "https://api.db.nomics.world/v22/series/BIS/WS_LBS_D_PUB/{series_code}?observations=1"
DBNOMICS_IMF_FSI_SERIES_URL = "https://api.db.nomics.world/v22/series/IMF/FSI/{series_code}?observations=1"
DBNOMICS_ECB_MIR_SERIES_URL = "https://api.db.nomics.world/v22/series/ECB/MIR/{series_code}?observations=1"
ECB_MIR_SERIES_URL = "https://data-api.ecb.europa.eu/service/data/MIR/{series_code}"
ECB_BPS_SERIES_URL = "https://data-api.ecb.europa.eu/service/data/BPS/{series_code}"
COHESION_EU_PAYMENTS_URL = "https://cohesiondata.ec.europa.eu/resource/pbbz-hmfu.json"
CNB_EXTERNAL_DEBT_USD_URLS = (
    "https://www.cnb.cz/en/statistics/bop_stat/external_debt/zz_usd_en.htm",
    "https://www.cnb.cz/en/statistics/bop_stat/external_debt/external-debt-in-usd-quarterly-2024/",
    "https://www.cnb.cz/en/statistics/bop_stat/external_debt/external-debt-in-usd-quarterly-2023/",
    "https://www.cnb.cz/en/statistics/bop_stat/external_debt/external-debt-in-usd-quarterly-2022/",
)
CNB_RESERVES_USD_TXT_URL = (
    "https://www.cnb.cz/export/sites/cnb/en/statistics/bop_stat/"
    "international_reserves/download/drs_rada_en.txt"
)
CZSO_IMPORT_PRICE_CSV_URL = "https://data.csu.gov.cz/opendata/sady/CEN0301/distribuce/csv"
KSH_IMPORT_PRICE_CSV_URL = "https://www.ksh.hu/stadat_files/ara/en/ara0046.csv"
GUS_DBW_VARIABLE_DATA_URL = "https://api-dbw.stat.gov.pl/api/variable/variable-data-section"
PSE_INDEXES_URL = "https://www.pse.cz/api/indexes"
GPW_BENCHMARK_WIG20_URL = "https://gpwbenchmark.pl/ajaxindex.php?action=GPWIndexes&start=ajaxIndicators&format=html&lang=EN&isin=PL9999999987&cmng_id=1011"
BVB_BET_PROFILE_URL = "https://m.bvb.ro/FinancialInstruments/Indices/IndicesProfiles?r=1"
BVB_INDEX_PERFORMANCE_URL = "https://www.bvb.ro/FinancialInstruments/Indices/IndicesPerformance"
EUROSTAT_DATA_URL = "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/{dataset}?{params}"
INSSE_TEMPO_PIVOT_URL = "http://statistici.insse.ro:8077/tempo-ins/pivot"
GIE_AGSI_BASE_URL = "https://agsi.gie.eu/api"
_ESG_DATA_CACHE: dict[tuple[str, str], list[tuple[str, float]]] | None = None
_BIS_CREDIT_GAP_CACHE: dict[str, list[tuple[str, float]]] | None = None
_BIS_CBTA_CACHE: dict[str, list[tuple[str, float]]] | None = None
_XLSX_NS = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
CONFIG_DIR = Path(__file__).resolve().parents[2] / "config"
_POLICY_RATE_CACHE: dict | None = None


FRED_FX_RESERVE_SERIES = {
    "PL": "TRESEGPLM052N",
}


def _cache_is_fresh(path: Path, *, max_age_hours: int) -> bool:
    """Use short-lived caches for live macro builds without hammering public APIs."""
    if os.environ.get("COUNTRY_PRIMER_REFRESH_CACHE") == "1":
        return False
    if not path.exists():
        return False
    age_seconds = datetime.utcnow().timestamp() - path.stat().st_mtime
    return age_seconds <= max_age_hours * 3600


@dataclass(frozen=True)
class IndicatorSpec:
    section_id: str
    indicator_id: str
    label: str
    unit: str
    source: str
    frequency: str
    chart: str = "line"
    peers: bool = False
    quality_status: str = "watch"
    quality_note: str = "Adapter pending; chart uses transparent proxy fill when primary data is unavailable."


INDICATOR_MANIFEST_48: tuple[IndicatorSpec, ...] = (
    IndicatorSpec("real_activity", "real_gdp_yoy", "Real GDP Growth, YoY", "% YoY", "Eurostat / national accounts", "quarterly", "peer_overlay", True, "verified", "Primary national accounts where available; revisions are common."),
    IndicatorSpec("real_activity", "real_gdp_qoq", "Real GDP Growth, QoQ SA", "% QoQ", "Eurostat / national accounts", "quarterly", "line", False, "watch", "Seasonal adjustment differs by source."),
    IndicatorSpec("real_activity", "gdp_components", "GDP Demand Components", "Index", "Eurostat / national accounts", "quarterly", "line", False, "watch", "Component split is a compact proxy until contribution charts are wired."),
    IndicatorSpec("real_activity", "industrial_production_yoy", "Industrial Production, YoY", "% YoY", "Eurostat STS", "monthly", "line", False, "verified", "Industrial-production series may be rebased."),
    IndicatorSpec("real_activity", "retail_sales_yoy", "Retail Sales Volume, YoY", "% YoY", "Eurostat STS", "monthly", "line", False, "watch", "Retail volume excludes some services consumption."),
    IndicatorSpec("real_activity", "unemployment_rate", "Unemployment Rate", "%", "Eurostat LFS", "monthly", "peer_overlay", True, "verified", "ILO/LFS definition preferred."),
    IndicatorSpec("real_activity", "economic_sentiment", "Economic Sentiment Indicator", "Index", "European Commission", "monthly", "peer_overlay", True, "watch", "Survey data is best used as a turning-point signal."),
    IndicatorSpec("prices_wages", "cpi_yoy", "Headline CPI/HICP, YoY", "% YoY", "Eurostat HICP / national CPI", "monthly", "peer_overlay", True, "verified", "Classification changes can affect component inflation."),
    IndicatorSpec("prices_wages", "core_cpi_yoy", "Core CPI, YoY", "% YoY", "Eurostat / national CPI", "monthly", "line", False, "verified", "Core definition should be checked against source metadata."),
    IndicatorSpec("prices_wages", "services_cpi_yoy", "Services CPI, YoY", "% YoY", "Eurostat HICP", "monthly", "line", False, "watch", "Services basket definitions vary across releases."),
    IndicatorSpec("prices_wages", "ppi_yoy", "Producer Prices, YoY", "% YoY", "Eurostat STS", "monthly", "line", False, "verified", "Energy weights can dominate PPI prints."),
    IndicatorSpec("prices_wages", "avg_wage_yoy", "Average Gross Wage, YoY", "% YoY", "Eurostat / national labour data", "quarterly", "line", False, "watch", "Enterprise-survey coverage differs across countries."),
    IndicatorSpec("prices_wages", "real_wage_yoy", "Real Wage, YoY", "% YoY", "Derived from wages and CPI", "quarterly", "line", False, "watch", "Derived indicator; deflator choice matters."),
    IndicatorSpec("external", "current_account_pct_gdp", "Current Account, % GDP", "% GDP", "IMF WEO / Eurostat BoP", "annual", "peer_overlay", True, "verified", "BoP revisions are common."),
    IndicatorSpec("external", "trade_balance", "Trade Balance", "USD bn", "Eurostat / World Bank proxy", "monthly", "bar", False, "watch", "Goods/services perimeter and currency conversion can vary."),
    IndicatorSpec("external", "services_balance", "Services Balance", "USD bn", "Eurostat BoP", "quarterly", "bar", False, "watch", "Adapter pending; use directionally until BoP adapter is wired."),
    IndicatorSpec("external", "fx_reserves", "FX Reserves", "USD bn", "World Bank / central bank", "monthly", "line", False, "verified", "USD valuation effects matter."),
    IndicatorSpec("external", "reer", "Real Effective Exchange Rate", "Index", "BIS / ECB", "monthly", "peer_overlay", True, "verified", "Normalize base year when comparing peers."),
    IndicatorSpec("external", "short_term_ext_debt", "Short-Term External Debt / Reserves", "%", "World Bank / BIS", "annual", "line", False, "watch", "Annual and lagged; structural vulnerability signal."),
    IndicatorSpec("fiscal_sovereign", "fiscal_balance_pct_gdp", "General Government Balance, % GDP", "% GDP", "Eurostat / IMF WEO", "annual", "peer_overlay", True, "verified", "EDP notifications can revise deficit history."),
    IndicatorSpec("fiscal_sovereign", "structural_balance", "Structural Fiscal Balance", "% potential GDP", "IMF / EC AMECO", "annual", "line", False, "watch", "Model-based estimate; output-gap assumptions matter."),
    IndicatorSpec("fiscal_sovereign", "primary_balance", "Primary Balance, % GDP", "% GDP", "IMF / Eurostat", "annual", "line", False, "watch", "Check interest-expenditure classification."),
    IndicatorSpec("fiscal_sovereign", "gov_debt_pct_gdp", "General Government Debt, % GDP", "% GDP", "Eurostat EDP", "annual", "peer_overlay", True, "verified", "Nominal GDP revisions affect the ratio."),
    IndicatorSpec("fiscal_sovereign", "interest_bill_pct_gdp", "Interest Bill, % GDP", "% GDP", "IMF / Eurostat", "annual", "line", False, "watch", "Annual/lagged; combine with current curve."),
    IndicatorSpec("fiscal_sovereign", "sov_yield_10y", "10Y Government Bond Yield", "%", "Eurostat / market data", "monthly", "peer_overlay", True, "verified", "Confirm market data against terminal for trading."),
    IndicatorSpec("monetary_financial", "policy_rate", "Central Bank Policy Rate", "%", "BIS / central bank", "monthly", "peer_overlay", True, "verified", "Corridor systems require definition check."),
    IndicatorSpec("monetary_financial", "real_policy_rate", "Real Policy Rate", "%", "Derived from policy rate and CPI", "monthly", "line", False, "watch", "Ex-post vs ex-ante definition matters."),
    IndicatorSpec("monetary_financial", "m3_yoy", "Broad Money M3, YoY", "% YoY", "World Bank / national central bank", "monthly", "line", False, "watch", "May use broad-money proxy where M3 is unavailable."),
    IndicatorSpec("monetary_financial", "private_credit_yoy", "Private Credit, YoY", "% YoY", "Eurostat / BIS", "monthly", "line", False, "watch", "Credit aggregates differ by sector perimeter."),
    IndicatorSpec("monetary_financial", "credit_to_gdp_gap", "Credit-to-GDP Gap", "pp", "BIS", "quarterly", "line", False, "watch", "Filter-based series can revise with history."),
    IndicatorSpec("monetary_financial", "fx_vs_eur", "FX vs EUR", "LCU per EUR", "ECB", "daily", "line", False, "verified", "ECB reference rate; not executable intraday price."),
    IndicatorSpec("markets_valuation", "equity_index", "Headline Equity Index", "Index", "Yahoo Finance / exchange", "monthly", "line", False, "watch", "Vendor feed; confirm index convention."),
    IndicatorSpec("markets_valuation", "equity_yoy", "Headline Equity Index, YoY", "% YoY", "Derived from equity index", "monthly", "line", False, "watch", "Derived from market index level."),
    IndicatorSpec("markets_valuation", "equity_fwd_pe", "Equity P/E", "x", "Exchange factsheets / vendor estimates", "monthly", "line", False, "low_confidence", "Index-level P/E is sourced from exchange factsheets where available; forward-consensus estimates usually require vendor data."),
    IndicatorSpec("markets_valuation", "equity_div_yield", "Equity Dividend Yield", "%", "Exchange factsheets / vendor estimates", "monthly", "line", False, "low_confidence", "Trailing/forward methodology must be checked."),
    IndicatorSpec("markets_valuation", "sov_spread_vs_bund", "10Y Spread vs Bund", "bp", "Derived from sovereign yields", "monthly", "peer_overlay", True, "watch", "Derived spread; check maturity matching."),
    IndicatorSpec("financial_stability", "bank_car", "Bank Capital Adequacy Ratio", "%", "IMF FSI / national bank", "quarterly", "line", False, "watch", "Regulatory definitions can change."),
    IndicatorSpec("financial_stability", "bank_npl_ratio", "Bank NPL Ratio", "%", "IMF FSI / national bank", "quarterly", "line", False, "watch", "FSI/national-bank data is lagged and definitions vary."),
    IndicatorSpec("financial_stability", "bank_roe", "Bank Return on Equity", "%", "IMF FSI / national bank", "quarterly", "line", False, "watch", "Taxes and one-offs can distort sector ROE."),
    IndicatorSpec("financial_stability", "bank_ld_ratio", "Bank Loan-to-Deposit Ratio", "%", "IMF FSI / national bank", "quarterly", "line", False, "watch", "Deposit perimeter differs by regulator."),
    IndicatorSpec("demographics", "population_total", "Total Population", "mn people", "Eurostat / World Bank", "annual", "line", False, "verified", "Census rebasing can revise history."),
    IndicatorSpec("demographics", "working_age_population", "Working-Age Population", "mn people", "Eurostat / World Bank", "annual", "peer_overlay", True, "verified", "Structural labour-supply signal."),
    IndicatorSpec("demographics", "old_age_dependency", "Old-Age Dependency Ratio", "%", "Eurostat / World Bank", "annual", "peer_overlay", True, "verified", "Slow-moving structural series."),
    IndicatorSpec("demographics", "median_age", "Median Age", "years", "Eurostat / UN WPP", "annual", "line", False, "verified", "Annual structural estimate."),
    IndicatorSpec("political_economy", "wgi_government_effectiveness", "WGI Government Effectiveness", "Estimate score", "World Bank Sovereign ESG / WGI", "annual", "line", False, "watch", "WGI estimate score from the World Bank Sovereign ESG workbook; use directionally and note confidence intervals are not shown."),
    IndicatorSpec("political_economy", "wgi_rule_of_law", "WGI Rule of Law", "Estimate score", "World Bank Sovereign ESG / WGI", "annual", "line", False, "watch", "WGI estimate score from the World Bank Sovereign ESG workbook; use directionally and note confidence intervals are not shown."),
    IndicatorSpec("political_economy", "wgi_control_of_corruption", "WGI Control of Corruption", "Estimate score", "World Bank Sovereign ESG / WGI", "annual", "line", False, "watch", "WGI estimate score from the World Bank Sovereign ESG workbook; perception/model composite can move with methodology."),
    IndicatorSpec("political_economy", "eu_funds_frozen", "EU Funds Frozen / At Risk", "% allocation", "European Commission / public proxy", "annual", "line", False, "low_confidence", "Public programme-cycle data is fragmented; verify manually."),
)


def _load_manifest_from_yaml(fallback: tuple[IndicatorSpec, ...]) -> tuple[IndicatorSpec, ...]:
    """Load the editable canonical indicator manifest from config when available."""
    manifest_path = CONFIG_DIR / "indicator_manifest_48.yaml"
    if not manifest_path.exists():
        return fallback

    payload = yaml.safe_load(manifest_path.read_text()) or {}
    raw_indicators = payload.get("indicators") or []
    specs: list[IndicatorSpec] = []
    seen: set[str] = set()

    for raw in raw_indicators:
        spec = IndicatorSpec(
            section_id=str(raw["section_id"]),
            indicator_id=str(raw["indicator_id"]),
            label=str(raw["label"]),
            unit=str(raw.get("unit", "")),
            source=str(raw.get("source", "")),
            frequency=str(raw.get("frequency", "annual")),
            chart=str(raw.get("chart", "line")),
            peers=bool(raw.get("peers", False)),
            quality_status=str(raw.get("quality_status", "watch")),
            quality_note=str(raw.get("quality_note", "")),
        )
        if spec.indicator_id in seen:
            raise ValueError(f"Duplicate indicator_id in manifest: {spec.indicator_id}")
        seen.add(spec.indicator_id)
        specs.append(spec)

    expected = int(payload.get("expected_count", len(raw_indicators)))
    if len(specs) != expected:
        raise ValueError(f"Expected {expected} indicators in {manifest_path}, found {len(specs)}")
    return tuple(specs)


INDICATOR_MANIFEST_48 = _load_manifest_from_yaml(INDICATOR_MANIFEST_48)


SECTION_INDICATORS_48: dict[str, tuple[IndicatorSpec, ...]] = {}
for _spec in INDICATOR_MANIFEST_48:
    SECTION_INDICATORS_48.setdefault(_spec.section_id, tuple())
    SECTION_INDICATORS_48[_spec.section_id] = (*SECTION_INDICATORS_48[_spec.section_id], _spec)


DROPPED_PROXY_INDICATORS_BY_COUNTRY: dict[str, frozenset[str]] = {
    "HU": frozenset({
        "breakeven_5y5y",
        "equity_fwd_pe",
        "equity_pb",
        "equity_div_yield",
    }),
    "PL": frozenset({
        "breakeven_5y5y",
    }),
    "CZ": frozenset({
        "breakeven_5y5y",
        "equity_fwd_pe",
        "equity_pb",
        "equity_div_yield",
    }),
    "RO": frozenset({
        "breakeven_5y5y",
        "equity_fwd_pe",
        "equity_pb",
        "equity_div_yield",
        "equity_vol_30d",
    }),
}


def is_dropped_proxy_indicator(country: str, indicator_id: str) -> bool:
    """Return true when a country/indicator slot is intentionally hidden.

    These are analytically interesting indicators whose public-source adapter
    still falls back to transparent proxy data. The dashboard now drops those
    country-specific slots instead of publishing low-confidence placeholder
    charts.
    """
    return indicator_id in DROPPED_PROXY_INDICATORS_BY_COUNTRY.get(country.upper(), frozenset())


LEGACY_INDICATOR_KEYS: dict[str, tuple[str, ...]] = {
    "real_gdp_yoy": ("real_gdp_yoy",),
    "industrial_production_yoy": ("industrial_production_yoy",),
    "retail_sales_yoy": ("retail_sales_yoy",),
    "unemployment_rate": ("unemployment_rate",),
    "cpi_yoy": ("cpi_yoy",),
    "core_cpi_yoy": ("core_cpi_yoy",),
    "ppi_yoy": ("ppi_yoy",),
    "avg_wage_yoy": ("avg_wage_yoy",),
    "current_account_pct_gdp": ("current_account_pct_gdp",),
    "trade_balance": ("trade_balance", "goods_trade_balance"),
    "fx_reserves": ("fx_reserves",),
    "reer": ("reer",),
    "fiscal_balance_pct_gdp": ("fiscal_balance_pct_gdp",),
    "gov_debt_pct_gdp": ("gov_debt_pct_gdp",),
    "sov_yield_10y": ("sov_yield_10y",),
    "policy_rate": ("policy_rate",),
    "m3_yoy": ("m3_yoy",),
    "private_credit_yoy": ("private_credit_yoy",),
    "fx_vs_eur": ("fx_vs_eur",),
    "equity_index": ("equity_index",),
    "equity_yoy": ("equity_yoy",),
}


COUNTRY_OFFSETS = {
    "HU": -0.20,
    "PL": 0.35,
    "CZ": 0.10,
    "RO": 0.55,
}


BASELINE = {
    "real_gdp_yoy": 2.0, "real_gdp_qoq": 0.5, "gdp_components": 100.0, "gdp_per_capita": 32000.0,
    "gross_fixed_capital": 23.0, "construction_production": 2.0, "fdi_inflows": 2.5,
    "oecd_cli": 100.0, "ifo_expectations": 88.0, "truck_km_index": 100.0,
    "industrial_production_yoy": 1.0, "retail_sales_yoy": 2.5, "unemployment_rate": 4.5,
    "economic_sentiment": 98.0, "manufacturing_pmi": 50.0, "capacity_utilization": 78.0,
    "consumer_confidence": -12.0, "employment_growth": 1.0, "participation_rate": 58.0,
    "vacancy_rate": 2.0, "cpi_yoy": 4.0, "core_cpi_yoy": 4.3, "services_cpi_yoy": 5.0,
    "goods_cpi_yoy": 3.0, "energy_cpi_yoy": 2.5, "food_cpi_yoy": 4.2,
    "ppi_yoy": 2.2, "import_prices_yoy": 2.0, "avg_wage_yoy": 8.0, "real_wage_yoy": 3.2,
    "inflation_expectations": 4.0, "breakeven_5y5y": 3.0, "house_price_index": 4.0,
    "administered_prices": 15.0,
    "unit_labour_cost": 5.0, "minimum_wage": 700.0, "current_account_pct_gdp": -1.5,
    "trade_balance": 0.0, "services_balance": 2.0, "income_balance": -2.0,
    "fx_reserves": 80.0, "ara_metric": 110.0, "reer": 102.0, "neer": 101.0,
    "fx_implied_vol": 8.0, "iip_position": -35.0, "gross_ext_debt": 60.0, "bis_cross_border": 40.0,
    "energy_import_dependency": 40.0, "gas_storage_level": 65.0,
    "short_term_ext_debt": 55.0,
    "fiscal_balance_pct_gdp": -3.5, "structural_balance": -3.0, "primary_balance": -1.0,
    "gov_debt_pct_gdp": 55.0, "gov_revenue_pct_gdp": 42.0, "gov_expenditure_pct_gdp": 46.0,
    "interest_bill_pct_gdp": 2.0, "debt_fx_share": 25.0, "avg_debt_maturity": 6.0,
    "sov_yield_10y": 5.0, "sov_yield_2y": 4.5, "cds_5y": 120.0, "yield_curve_slope": 50.0,
    "sovereign_rating": 11.0, "eu_funds_absorption": 42.0, "edp_status": 0.0,
    "contingent_liabilities": 8.0,
    "policy_rate": 5.0, "real_policy_rate": 1.0, "m3_yoy": 7.0, "private_credit_yoy": 5.5,
    "credit_to_gdp_gap": 0.0, "interbank_3m": 5.0, "lending_rate_household": 7.0,
    "lending_rate_corp": 6.0, "fx_vs_eur": 100.0, "fx_3m_forward": 0.5,
    "carry_trade_return": 3.0, "cb_balance_sheet_gdp": 35.0, "cb_forward_guidance": 0.0,
    "fx_loan_share": 18.0, "mortgage_rate_new": 6.0,
    "equity_index": 100.0, "equity_yoy": 8.0,
    "equity_fwd_pe": 9.5, "equity_pb": 1.2, "equity_div_yield": 4.0, "equity_vol_30d": 18.0,
    "sov_spread_vs_bund": 220.0, "embi_spread": 180.0, "foreign_ownership_bonds": 25.0,
    "portfolio_flows": 0.0,
    "bank_car": 19.0, "bank_npl_ratio": 3.5, "bank_roe": 12.0, "bank_ld_ratio": 86.0,
    "bank_liquidity_coverage": 180.0, "bank_nim": 3.0, "household_debt_pct_gdp": 25.0, "corp_debt_pct_gdp": 45.0,
    "real_estate_price_gap": 0.0, "foreign_bank_share": 60.0,
    "population_total": 20.0, "working_age_population": 12.5, "old_age_dependency": 29.0,
    "median_age": 42.0, "net_migration": -25000.0, "fertility_rate": 1.5, "pension_spending_pct_gdp": 10.0,
    "wgi_government_effectiveness": 70.0, "wgi_rule_of_law": 72.0,
    "wgi_control_of_corruption": 68.0, "eu_funds_frozen": 8.0,
}


COUNTRY_LEVEL_OVERRIDES = {
    "HU": {"fx_vs_eur": 390.0, "population_total": 9.6, "working_age_population": 6.2, "median_age": 43.6, "gov_debt_pct_gdp": 74.0, "sov_spread_vs_bund": 420.0, "eu_funds_frozen": 35.0},
    "PL": {"fx_vs_eur": 4.3, "population_total": 36.6, "working_age_population": 22.0, "median_age": 42.7, "gov_debt_pct_gdp": 55.0, "sov_spread_vs_bund": 280.0, "eu_funds_frozen": 3.0},
    "CZ": {"fx_vs_eur": 25.0, "population_total": 10.9, "working_age_population": 6.9, "median_age": 43.2, "gov_debt_pct_gdp": 45.0, "sov_spread_vs_bund": 140.0, "eu_funds_frozen": 1.0},
    "RO": {"fx_vs_eur": 5.0, "population_total": 19.0, "working_age_population": 12.0, "median_age": 42.3, "gov_debt_pct_gdp": 52.0, "sov_spread_vs_bund": 520.0, "eu_funds_frozen": 9.0},
}


def _stable_wave(country: str, indicator_id: str, index: int) -> float:
    seed = sum(ord(c) for c in f"{country}:{indicator_id}")
    return math.sin((index + 1) * 0.85 + seed % 11) * 0.55


def _dates_for_frequency(frequency: str) -> list[str]:
    if frequency == "monthly" or frequency == "daily":
        return [f"2025-{m:02d}-01" for m in range(1, 13)] + [f"2026-{m:02d}-01" for m in range(1, 5)]
    if frequency == "quarterly":
        return ["2021-03-31", "2021-06-30", "2021-09-30", "2021-12-31",
                "2022-03-31", "2022-06-30", "2022-09-30", "2022-12-31",
                "2023-03-31", "2023-06-30", "2023-09-30", "2023-12-31",
                "2024-03-31", "2024-06-30", "2024-09-30", "2024-12-31",
                "2025-03-31", "2025-06-30", "2025-09-30", "2025-12-31"]
    if frequency == "seasonal":
        return [
            "2022-04-01", "2022-10-01",
            "2023-04-01", "2023-10-01",
            "2024-04-01", "2024-10-01",
            "2025-04-01", "2025-10-01",
            "2026-04-01",
        ]
    return [f"{year}-12-31" for year in range(2017, 2026)]


def _proxy_values(country: str, spec: IndicatorSpec, n: int) -> list[float]:
    base = COUNTRY_LEVEL_OVERRIDES.get(country, {}).get(spec.indicator_id, BASELINE.get(spec.indicator_id, 1.0))
    offset = COUNTRY_OFFSETS.get(country, 0.0)
    values: list[float] = []
    for i in range(n):
        drift = (i - (n - 1) / 2) * 0.06
        wave = _stable_wave(country, spec.indicator_id, i)
        level = base + offset + drift + wave
        if spec.unit in {"Index", "LCU per EUR", "mn people", "years", "bp"}:
            level = base * (1 + 0.006 * (i - n / 2)) + wave
        if spec.indicator_id in {"trade_balance", "services_balance", "primary_balance", "fiscal_balance_pct_gdp", "structural_balance"}:
            level = base + offset * 1.5 + drift + wave
        values.append(round(float(level), 2))
    return values


def _parse_row_date(row: dict) -> datetime | None:
    try:
        return datetime.fromisoformat(str(row.get("date", ""))[:10])
    except ValueError:
        return None


def _xlsx_column_index(cell_ref: str) -> int:
    letters = "".join(ch for ch in cell_ref if ch.isalpha()).upper()
    index = 0
    for letter in letters:
        index = index * 26 + ord(letter) - ord("A") + 1
    return max(index - 1, 0)


def _xlsx_cell_value(cell: ET.Element, shared_strings: list[str]) -> str:
    cell_type = cell.get("t")
    value = cell.find("m:v", _XLSX_NS)
    if cell_type == "s" and value is not None and value.text:
        return shared_strings[int(value.text)]
    if cell_type == "inlineStr":
        return "".join(node.text or "" for node in cell.findall(".//m:t", _XLSX_NS))
    return "" if value is None or value.text is None else value.text


def _xlsx_row_values(row: ET.Element, shared_strings: list[str]) -> list[str]:
    values: list[str] = []
    for cell in row.findall("m:c", _XLSX_NS):
        index = _xlsx_column_index(cell.get("r", "A1"))
        while len(values) <= index:
            values.append("")
        values[index] = _xlsx_cell_value(cell, shared_strings)
    return values


def _load_world_bank_esg_data() -> dict[tuple[str, str], list[tuple[str, float]]]:
    """Parse the World Bank Sovereign ESG workbook into an in-memory index.

    The standard World Bank Indicators API exposes WGI metadata but does not
    reliably return the latest country-level WGI time series. The ESG workbook
    is the official downloadable data package and includes the WGI estimate
    series needed for the political-economy section.
    """
    global _ESG_DATA_CACHE
    if _ESG_DATA_CACHE is not None:
        return _ESG_DATA_CACHE

    workbook_path = CACHE_DIR / "worldbank_esgdata_2026-01-09.xlsx"
    if workbook_path.exists():
        workbook_bytes = workbook_path.read_bytes()
    else:
        response = requests.get(WORLD_BANK_ESG_URL, timeout=45)
        response.raise_for_status()
        workbook_bytes = response.content
        workbook_path.write_bytes(workbook_bytes)

    with zipfile.ZipFile(io.BytesIO(workbook_bytes)) as archive:
        shared_root = ET.fromstring(archive.read("xl/sharedStrings.xml"))
        shared_strings = [
            "".join(node.text or "" for node in item.findall(".//m:t", _XLSX_NS))
            for item in shared_root.findall("m:si", _XLSX_NS)
        ]
        sheet_root = ET.fromstring(archive.read("xl/worksheets/sheet4.xml"))
        rows = sheet_root.findall(".//m:row", _XLSX_NS)
        header = _xlsx_row_values(rows[0], shared_strings) if rows else []
        year_columns = [
            (idx, value)
            for idx, value in enumerate(header)
            if len(value) == 4 and value.isdigit()
        ]

        data: dict[tuple[str, str], list[tuple[str, float]]] = {}
        for row in rows[1:]:
            values = _xlsx_row_values(row, shared_strings)
            if len(values) < 4:
                continue
            iso3, indicator_code = values[0], values[2]
            if not iso3 or not indicator_code:
                continue
            observations: list[tuple[str, float]] = []
            for idx, year in year_columns:
                if idx >= len(values) or values[idx] == "":
                    continue
                try:
                    observations.append((f"{year}-12-31", float(values[idx])))
                except ValueError:
                    continue
            if observations:
                data[(iso3, indicator_code)] = observations

    _ESG_DATA_CACHE = data
    return data


def _source_validation_notes(rows: list[dict], spec: IndicatorSpec) -> list[str]:
    notes: list[str] = []
    if not rows:
        return ["No observations returned by adapter."]

    parsed = [_parse_row_date(row) for row in rows]
    if any(dt is None for dt in parsed):
        notes.append("Some dates failed ISO parsing.")
        parsed = [dt for dt in parsed if dt is not None]
    if not parsed:
        return notes or ["No parseable dates returned by adapter."]

    latest = max(parsed)
    stale_limit = FREQUENCY_STALE_DAYS.get(spec.frequency, 220)
    age = (datetime.utcnow() - latest).days
    if age > stale_limit:
        notes.append(f"Latest observation is {age} days old for {spec.frequency} data.")

    if spec.frequency != "event" and len(parsed) < 5:
        notes.append("Short history returned by adapter.")

    sorted_dates = sorted(parsed)
    gap_limit = FREQUENCY_GAP_DAYS.get(spec.frequency, 180)
    gaps = [
        (sorted_dates[i] - sorted_dates[i - 1]).days
        for i in range(1, len(sorted_dates))
    ]
    if gaps and max(gaps) > gap_limit:
        notes.append(f"Observed date gap of {max(gaps)} days exceeds expected {spec.frequency} cadence.")

    values: list[float] = []
    for row in rows:
        try:
            value = float(row.get("value"))
        except (TypeError, ValueError):
            notes.append("Non-numeric value returned by adapter.")
            continue
        if not math.isfinite(value):
            notes.append("Non-finite value returned by adapter.")
            continue
        values.append(value)

    if len(values) >= 8:
        diffs = [values[i] - values[i - 1] for i in range(1, len(values))]
        mean = sum(diffs) / len(diffs)
        variance = sum((d - mean) ** 2 for d in diffs) / max(len(diffs) - 1, 1)
        stdev = math.sqrt(variance)
        if stdev > 0 and abs(diffs[-1] - mean) > 6 * stdev:
            notes.append("Latest move is a statistical outlier; verify revision/base effects.")

    return notes[:4]


def _apply_source_validation(rows: list[dict], spec: IndicatorSpec) -> list[dict]:
    if not rows:
        return rows
    notes = _source_validation_notes(rows, spec)
    if notes:
        status = "watch" if len(notes) <= 2 else "low_confidence"
        suffix = " Source validation: " + " ".join(notes)
    else:
        status = "verified" if spec.quality_status == "verified" else "watch"
        suffix = " Source validation passed."

    for row in rows:
        row["quality_status"] = status
        row["quality_note"] = f"{row.get('quality_note') or spec.quality_note} {suffix}".strip()
    return rows


def _series_to_rows(
    series: Series,
    spec: IndicatorSpec,
    *,
    scale: float = 1.0,
    unit: str | None = None,
    note: str = "",
) -> list[dict]:
    if not series.available or not series.observations:
        return []

    rows = []
    quality_note = spec.quality_note
    if note:
        quality_note = f"{quality_note} {note}"
    for date, value in series.observations:
        rows.append({
            "country": series.country,
            "date": str(date)[:10],
            "indicator_id": spec.indicator_id,
            "value": float(value) * scale,
            "label": spec.label,
            "section_id": spec.section_id,
            "unit": unit or spec.unit or series.unit,
            "source": series.source or spec.source,
            "series_id": series.series_id,
            "quality_status": "verified",
            "quality_note": quality_note,
            "is_proxy": False,
        })
    return _apply_source_validation(rows, spec)


def _derive_yoy_series(series: Series, spec: IndicatorSpec, periods: int = 12) -> Series:
    if not series.available or len(series.observations) <= periods:
        return series
    obs = []
    values = series.observations
    for idx in range(periods, len(values)):
        date, value = values[idx]
        _, prior = values[idx - periods]
        if prior == 0:
            continue
        obs.append((date, (float(value) / float(prior) - 1.0) * 100.0))
    return finalize_series(Series(
        key=spec.indicator_id,
        label=spec.label,
        country=series.country,
        source=series.source,
        series_id=f"{series.series_id} (derived YoY)",
        unit="% YoY",
        frequency=series.frequency,
        last_update=obs[-1][0] if obs else "",
        fetched=series.fetched,
        source_url=series.source_url,
        observations=obs,
        available=bool(obs),
        note=f"Derived YoY from {series.series_id}",
    ))


def _parse_jsonstat_observations(payload: dict) -> list[tuple[str, float]]:
    """Parse ECB JSON-data payloads that carry one series plus observations."""
    datasets = payload.get("dataSets") or []
    structure = payload.get("structure") or {}
    if not datasets:
        return []
    series_map = (datasets[0].get("series") or {})
    if not series_map:
        return []
    observation_dims = (structure.get("dimensions") or {}).get("observation") or []
    if not observation_dims:
        return []
    time_values = observation_dims[0].get("values") or []
    times_by_idx = {idx: item.get("id") for idx, item in enumerate(time_values)}
    first_series = next(iter(series_map.values()))
    observations: list[tuple[str, float]] = []
    for idx_str, raw in (first_series.get("observations") or {}).items():
        try:
            value = float(raw[0])
        except (TypeError, ValueError, IndexError):
            continue
        period = times_by_idx.get(int(idx_str))
        if not period:
            continue
        if "-Q" in period:
            year, quarter = period.split("-Q")
            month = (int(quarter) - 1) * 3 + 1
            date = f"{year}-{month:02d}-01"
        elif len(period) == 7 and period[4] == "-":
            date = f"{period}-01"
        elif len(period) == 4:
            date = f"{period}-12-31"
        else:
            date = str(period)[:10]
        observations.append((date, value))
    observations.sort()
    return observations


def _secret_env(name: str) -> str:
    """Read optional source credentials without hard-coding secrets in config."""
    return os.environ.get(name, "").strip()


def _fetch_fred_observations(series_id: str, *, start: str = "2010-01-01") -> list[tuple[str, float]]:
    """Fetch a FRED series using the official API when keyed, graph CSV otherwise."""
    cache_file = CACHE_DIR / f"fred_{series_id}.json"
    if _cache_is_fresh(cache_file, max_age_hours=24):
        payload = json.loads(cache_file.read_text())
        return [(str(item["date"])[:10], float(item["value"])) for item in payload.get("observations", [])]

    api_key = _secret_env("FRED_API_KEY")
    observations: list[tuple[str, float]] = []
    if api_key:
        response = requests.get(
            FRED_OBSERVATIONS_URL,
            params={
                "series_id": series_id,
                "api_key": api_key,
                "file_type": "json",
                "observation_start": start,
            },
            timeout=30,
        )
        response.raise_for_status()
        for item in response.json().get("observations") or []:
            value = item.get("value")
            if value in {None, "", "."}:
                continue
            try:
                observations.append((str(item.get("date", ""))[:10], float(value)))
            except (TypeError, ValueError):
                continue
    else:
        response = requests.get(FRED_GRAPH_CSV_URL, params={"id": series_id}, timeout=30)
        response.raise_for_status()
        reader = csv.DictReader(io.StringIO(response.text))
        for row in reader:
            date = str(row.get("observation_date") or "")[:10]
            value = row.get(series_id)
            if not date or value in {None, "", "."}:
                continue
            try:
                observations.append((date, float(value)))
            except ValueError:
                continue

    observations = [(date, value) for date, value in sorted(observations) if date >= start]
    cache_file.write_text(json.dumps({
        "series_id": series_id,
        "fetched": datetime.utcnow().isoformat() + "Z",
        "observations": [{"date": date, "value": value} for date, value in observations],
    }, indent=2, sort_keys=True))
    return observations


def _parse_ohlc_csv(text: str) -> list[tuple[str, float]]:
    reader = csv.DictReader(io.StringIO(text))
    observations: list[tuple[str, float]] = []
    for row in reader:
        date = str(row.get("Date") or row.get("date") or "").strip()
        close_raw = row.get("Close") or row.get("close")
        if not date or close_raw in {None, ""}:
            continue
        try:
            close = float(str(close_raw).replace(",", ""))
        except ValueError:
            continue
        if math.isfinite(close) and close > 0:
            observations.append((date[:10], close))
    return sorted(observations)


class _HTMLTableParser(HTMLParser):
    """Collect simple HTML tables from official statistics pages."""

    def __init__(self) -> None:
        super().__init__()
        self.tables: list[list[list[str]]] = []
        self._table: list[list[str]] | None = None
        self._row: list[str] | None = None
        self._cell: list[str] | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "table":
            self._table = []
        elif tag == "tr" and self._table is not None:
            self._row = []
        elif tag in {"td", "th"} and self._row is not None:
            self._cell = []

    def handle_data(self, data: str) -> None:
        if self._cell is not None:
            self._cell.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag in {"td", "th"} and self._row is not None and self._cell is not None:
            self._row.append(" ".join(" ".join(self._cell).split()))
            self._cell = None
        elif tag == "tr" and self._table is not None and self._row is not None:
            if self._row:
                self._table.append(self._row)
            self._row = None
        elif tag == "table" and self._table is not None:
            if self._table:
                self.tables.append(self._table)
            self._table = None


def _parse_cnb_number(raw: str) -> float:
    """Parse CNB Czech-formatted numbers such as `178.314,9`."""
    value = str(raw).replace("\xa0", "").replace(" ", "").replace(".", "").replace(",", ".")
    return float(value)


def _cnb_day_month_year_to_iso(raw: str) -> str | None:
    parts = str(raw).strip().strip(".").split(".")
    if len(parts) != 3:
        return None
    day, month, year = parts
    if not (day.isdigit() and month.isdigit() and year.isdigit()):
        return None
    return f"{int(year):04d}-{int(month):02d}-{int(day):02d}"


def proxy_rows(country: str, spec: IndicatorSpec) -> list[dict]:
    dates = _dates_for_frequency(spec.frequency)
    values = _proxy_values(country, spec, len(dates))
    return [
        {
            "country": country,
            "date": date,
            "indicator_id": spec.indicator_id,
            "value": value,
            "label": spec.label,
            "section_id": spec.section_id,
            "unit": spec.unit,
            "source": f"Transparent proxy fill; target source: {spec.source}",
            "series_id": f"proxy:{spec.indicator_id}",
            "quality_status": "low_confidence" if spec.quality_status == "low_confidence" else "watch",
            "quality_note": f"Transparent proxy fill. {spec.quality_note}",
            "is_proxy": True,
        }
        for date, value in zip(dates, values)
    ]


class BaseFetcher:
    """Adapter interface: subclasses return canonical rows for one indicator."""

    def fetch(self, country: str, spec: IndicatorSpec) -> list[dict]:
        raise NotImplementedError


class EurostatFetcher(BaseFetcher):
    CONFIGS = {
        "real_gdp_yoy": {
            "dataset": "namq_10_gdp",
            "freq": "Q",
            "since": "2018",
            "params": {"na_item": "B1GQ", "unit": "CLV_PCH_SM", "s_adj": "SCA"},
            "unit": "% YoY",
        },
        "real_gdp_qoq": {
            "dataset": "namq_10_gdp",
            "freq": "Q",
            "since": "2018",
            "params": {"na_item": "B1GQ", "unit": "CLV_PCH_PRE", "s_adj": "SCA"},
            "unit": "% QoQ",
        },
        "gdp_per_capita": {
            "dataset": "nama_10_pc",
            "freq": "A",
            "since": "2010",
            "params": {"na_item": "B1GQ", "unit": "CP_EUR_HAB"},
            "unit": "EUR per head",
        },
        "cpi_yoy": {
            "dataset": "prc_hicp_minr",
            "freq": "M",
            "since": "2018",
            "params": {"coicop18": "TOTAL", "unit": "RCH_A"},
            "unit": "% YoY",
        },
        "core_cpi_yoy": {
            "dataset": "prc_hicp_minr",
            "freq": "M",
            "since": "2018",
            "params": {"coicop18": "TOT_X_NRG_FOOD", "unit": "RCH_A"},
            "unit": "% YoY",
        },
        "services_cpi_yoy": {
            "dataset": "prc_hicp_minr",
            "freq": "M",
            "since": "2018",
            "params": {"coicop18": "SERV", "unit": "RCH_A"},
            "unit": "% YoY",
        },
        "goods_cpi_yoy": {
            "dataset": "prc_hicp_minr",
            "freq": "M",
            "since": "2018",
            "params": {"coicop18": "IGD_NNRG", "unit": "RCH_A"},
            "unit": "% YoY",
        },
        "energy_cpi_yoy": {
            "dataset": "prc_hicp_minr",
            "freq": "M",
            "since": "2018",
            "params": {"coicop18": "NRG", "unit": "RCH_A"},
            "unit": "% YoY",
        },
        "food_cpi_yoy": {
            "dataset": "prc_hicp_minr",
            "freq": "M",
            "since": "2018",
            "params": {"coicop18": "FOOD", "unit": "RCH_A"},
            "unit": "% YoY",
        },
        "ppi_yoy": {
            "dataset": "sts_inppd_m",
            "freq": "M",
            "since": "2018",
            "params": {"nace_r2": "B-E36", "indic_bt": "PRC_PRR_DOM", "unit": "I21"},
            "unit": "% YoY",
            "derive_yoy": True,
        },
        "industrial_production_yoy": {
            "dataset": "sts_inpr_m",
            "freq": "M",
            "since": "2018",
            "params": {"nace_r2": "B-D", "indic_bt": "PRD", "s_adj": "SCA", "unit": "I21"},
            "unit": "% YoY",
            "derive_yoy": True,
        },
        "retail_sales_yoy": {
            "dataset": "sts_trtu_m",
            "freq": "M",
            "since": "2018",
            "params": {"nace_r2": "G47", "indic_bt": "VOL_SLS", "s_adj": "SCA", "unit": "I21"},
            "unit": "% YoY",
            "derive_yoy": True,
        },
        "economic_sentiment": {
            "dataset": "ei_bssi_m_r2",
            "freq": "M",
            "since": "2018",
            "params": {"indic": "BS-ESI-I", "s_adj": "SA"},
            "unit": "Index",
        },
        "manufacturing_pmi": {
            "dataset": "ei_bsin_m_r2",
            "freq": "M",
            "since": "2018",
            "params": {"indic": "BS-ICI", "s_adj": "SA", "unit": "BAL"},
            "unit": "Balance",
            "note": "European Commission industry confidence indicator from harmonised business surveys; replaces the vendor PMI placeholder with a public domestic industrial survey signal.",
        },
        "ifo_expectations": {
            "dataset": "ei_bsin_m_r2",
            "geo": "DE",
            "freq": "M",
            "since": "2018",
            "params": {"indic": "BS-ICI", "s_adj": "SA", "unit": "BAL"},
            "unit": "Balance",
            "note": "Germany industrial confidence from the harmonised European Commission business survey; used as a transparent external-demand spillover signal for CEE, not as a domestic country survey.",
        },
        "oecd_cli": {
            "dataset": "ei_bsee_m_r2",
            "freq": "M",
            "since": "2018",
            "params": {"indic": "BS-EEI-I", "s_adj": "SA", "unit": "INX"},
            "unit": "Index",
            "note": "European Commission Employment Expectations Indicator from harmonised business surveys; replaces the unavailable OECD CLI slot with a transparent domestic leading-labour-demand survey signal.",
        },
        "truck_km_index": {
            "dataset": "road_go_tq_tott",
            "freq": "Q",
            "since": "2018",
            "params": {"tra_type": "TOTAL", "tra_oper": "TOTAL", "unit": "MIO_TKM"},
            "unit": "million tonne-km",
            "note": "Eurostat quarterly road freight transport performance by reporting country, total transport and operation, measured in million tonne-kilometres; replaces the unavailable toll-road truck-km alternative-data placeholder.",
        },
        "consumer_confidence": {
            "dataset": "ei_bsco_m",
            "freq": "M",
            "since": "2018",
            "params": {"indic": "BS-CSMCI", "s_adj": "SA"},
            "unit": "Balance",
        },
        "capacity_utilization": {
            "dataset": "ei_bsin_q_r2",
            "freq": "Q",
            "since": "2018",
            "params": {"indic": "BS-ICU-PC", "s_adj": "SA"},
            "unit": "%",
        },
        "employment_growth": {
            "dataset": "namq_10_pe",
            "freq": "Q",
            "since": "2018",
            "params": {"na_item": "EMP_DC", "unit": "PCH_SM", "s_adj": "SCA"},
            "unit": "% YoY",
        },
        "participation_rate": {
            "dataset": "lfsi_emp_q",
            "freq": "Q",
            "since": "2018",
            "params": {"age": "Y15-64", "sex": "T", "indic_em": "ACT_R", "unit": "PC_POP", "s_adj": "SA"},
            "unit": "%",
        },
        "vacancy_rate": {
            "dataset": "jvs_q_nace2",
            "freq": "Q",
            "since": "2018",
            "params": {"nace_r2": "B-S", "sizeclas": "TOTAL", "indic_em": "JVR", "s_adj": "SA"},
            "unit": "%",
        },
        "construction_production": {
            "dataset": "sts_copr_m",
            "freq": "M",
            "since": "2018",
            "params": {"nace_r2": "F", "indic_bt": "PRD", "s_adj": "CA", "unit": "PCH_SM"},
            "unit": "% YoY",
        },
        "inflation_expectations": {
            "dataset": "ei_bsco_m",
            "freq": "M",
            "since": "2018",
            "params": {"indic": "BS-MP-NY", "s_adj": "SA", "unit": "BAL"},
            "unit": "Balance",
        },
        "administered_prices": {
            "dataset": "prc_hicp_iw",
            "freq": "A",
            "since": "2018",
            "params": {"coicop18": "AP"},
            "unit": "% CPI basket",
            "scale": 0.1,
        },
        "house_price_index": {
            "dataset": "prc_hpi_q",
            "freq": "Q",
            "since": "2018",
            "params": {"purchase": "TOTAL", "unit": "RCH_A"},
            "unit": "% YoY",
        },
        "energy_import_dependency": {
            "dataset": "nrg_ind_id",
            "freq": "A",
            "since": "2010",
            "params": {"siec": "TOTAL", "unit": "PC"},
            "unit": "%",
        },
        "iip_position": {
            "dataset": "tipsii40",
            "freq": "Q",
            "since": "2018",
            "params": {"unit": "PC_GDP", "s_adj": "NSA", "bop_item": "FA", "stk_flow": "N_LE", "partner": "WRL_REST"},
            "unit": "% GDP",
        },
        "pension_spending_pct_gdp": {
            "dataset": "spr_exp_pens",
            "freq": "A",
            "since": "2010",
            "params": {"spdepb": "OLD", "spdepm": "TOTAL", "unit": "PC_GDP"},
            "unit": "% GDP",
        },
        "avg_debt_maturity": {
            "dataset": "gov_10dd_rmd",
            "freq": "A",
            "since": "2015",
            "params": {"sector": "S13", "maturity": "TOTAL", "na_item": "GD", "unit": "YR"},
            "unit": "years",
        },
        "contingent_liabilities": {
            "dataset": "gov_cl_guar",
            "freq": "A",
            "since": "2018",
            "params": {"sector": "S13", "na_item": "FGT", "unit": "PC_GDP"},
            "unit": "% GDP",
        },
        "gov_revenue_pct_gdp": {
            "dataset": "gov_10a_main",
            "freq": "A",
            "since": "2010",
            "params": {"sector": "S13", "na_item": "TR", "unit": "PC_GDP"},
            "unit": "% GDP",
            "note": "Eurostat general-government total revenue, ESA 2010, as a share of GDP.",
        },
        "gov_expenditure_pct_gdp": {
            "dataset": "gov_10a_main",
            "freq": "A",
            "since": "2010",
            "params": {"sector": "S13", "na_item": "TE", "unit": "PC_GDP"},
            "unit": "% GDP",
            "note": "Eurostat general-government total expenditure, ESA 2010, as a share of GDP.",
        },
        "avg_wage_yoy": {
            "dataset": "lc_lci_r2_q",
            "freq": "Q",
            "since": "2018",
            "params": {"lcstruct": "D11", "nace_r2": "B-S", "s_adj": "SCA", "unit": "PCH_SM"},
            "unit": "% YoY",
        },
        "unit_labour_cost": {
            "dataset": "namq_10_lp_ulc",
            "freq": "Q",
            "since": "2018",
            "params": {"na_item": "NULC_HW", "unit": "PCH_SM", "s_adj": "NSA"},
            "unit": "% YoY",
        },
        "minimum_wage": {
            "dataset": "earn_mw_cur",
            "freq": "S",
            "since": "2010",
            "params": {"currency": "EUR"},
            "unit": "EUR/month",
        },
        "interbank_3m": {
            "dataset": "irt_st_m",
            "freq": "M",
            "since": "2018",
            "params": {},
            "unit": "%",
        },
        "sov_yield_10y": {
            "dataset": "irt_lt_mcby_m",
            "freq": "M",
            "since": "2018",
            "params": {},
            "unit": "%",
        },
        "median_age": {
            "dataset": "demo_pjanind",
            "freq": "A",
            "since": "2010",
            "params": {"indic_de": "MEDAGEPOP"},
            "unit": "years",
        },
    }

    def fetch(self, country: str, spec: IndicatorSpec) -> list[dict]:
        cfg = self.CONFIGS.get(spec.indicator_id)
        if not cfg:
            return []
        countries = load_countries()
        meta = countries.get(country)
        if not meta:
            return []
        series = fetch_eurostat(
            cfg["dataset"],
            str(cfg.get("geo") or meta["iso2"]),
            spec.indicator_id,
            spec.label,
            country,
            freq=cfg["freq"],
            since=cfg["since"],
            extra_params=cfg.get("params") or {},
            unit_label=cfg["unit"],
            indicator_label=spec.label,
        )
        if cfg.get("derive_yoy"):
            series = _derive_yoy_series(series, spec)
        rows = _series_to_rows(
            series,
            spec,
            scale=float(cfg.get("scale", 1.0)),
            unit=cfg["unit"],
            note=str(cfg.get("note") or ""),
        )
        if cfg.get("geo"):
            for row in rows:
                row["quality_status"] = "watch"
        return rows


def _load_policy_rate_payload() -> dict:
    global _POLICY_RATE_CACHE
    if _POLICY_RATE_CACHE is not None:
        return _POLICY_RATE_CACHE
    path = CONFIG_DIR / "policy_rates.yaml"
    if not path.exists():
        _POLICY_RATE_CACHE = {}
        return _POLICY_RATE_CACHE
    _POLICY_RATE_CACHE = yaml.safe_load(path.read_text()) or {}
    return _POLICY_RATE_CACHE


def _policy_rate_series(country: str, spec: IndicatorSpec) -> Series | None:
    payload = _load_policy_rate_payload()
    raw = (payload.get("policy_rates") or {}).get(country)
    if not raw:
        return None

    observations: list[tuple[str, float]] = []
    for item in raw.get("observations") or []:
        try:
            observations.append((str(item["date"])[:10], float(item["value"])))
        except (KeyError, TypeError, ValueError):
            continue
    observations.sort()
    if not observations:
        return None

    return finalize_series(Series(
        key=spec.indicator_id,
        label=spec.label,
        country=country,
        source=str(raw.get("source") or spec.source),
        series_id=str(raw.get("series_id") or f"policy_rate:{country}"),
        unit="%",
        frequency="event",
        last_update=observations[-1][0],
        source_url=str(raw.get("source_url") or ""),
        observations=observations,
        available=True,
        note=str(raw.get("quality_note") or spec.quality_note),
    ))


def _fetch_eurostat_monthly_fx_end(currency: str, since: str) -> list[tuple[str, float]]:
    """Fetch Eurostat month-end EUR/LCU exchange rates without a geo dimension."""
    params = {
        "freq": "M",
        "statinfo": "END",
        "unit": "NAC",
        "currency": currency,
        "sinceTimePeriod": since,
    }
    query = urlencode(params)
    cache_file = cache_path(f"eurostat::ert_bil_eur_m::{currency}::END::{since}::{query}")
    if _cache_is_fresh(cache_file, max_age_hours=18):
        payload = json.loads(cache_file.read_text())
    else:
        response = requests.get(EUROSTAT_DATA_URL.format(dataset="ert_bil_eur_m", params=query), timeout=30)
        response.raise_for_status()
        payload = response.json()
        cache_file.write_text(json.dumps(payload))

    time_index = payload["dimension"]["time"]["category"]["index"]
    times_by_idx = {int(idx): period for period, idx in time_index.items()}
    observations: list[tuple[str, float]] = []
    for idx_str, raw_value in (payload.get("value") or {}).items():
        period = times_by_idx.get(int(idx_str))
        if not period or raw_value is None:
            continue
        observations.append((f"{period}-01", float(raw_value)))
    observations.sort()
    return observations


class PolicyRateFetcher(BaseFetcher):
    """Official policy-rate definitions maintained in config/policy_rates.yaml."""

    def fetch(self, country: str, spec: IndicatorSpec) -> list[dict]:
        if spec.indicator_id != "policy_rate":
            return []
        series = _policy_rate_series(country, spec)
        if not series:
            return []
        rows = _series_to_rows(
            series,
            spec,
            unit="%",
            note="Official central-bank policy-rate definition; event-dated series is maintained in config/policy_rates.yaml.",
        )
        raw = (_load_policy_rate_payload().get("policy_rates") or {}).get(country) or {}
        for row in rows:
            row["quality_status"] = str(raw.get("quality_status") or "verified")
            row["quality_note"] = (
                f"{row.get('quality_note')} Target policy-rate label: {raw.get('rate_name', 'policy rate')}."
            ).strip()
        return rows


class DerivedMacroFetcher(BaseFetcher):
    def fetch(self, country: str, spec: IndicatorSpec) -> list[dict]:
        if spec.indicator_id == "gdp_components":
            return self._gdp_demand_composite(country, spec)
        if spec.indicator_id == "real_wage_yoy":
            return self._real_wage_yoy(country, spec)
        if spec.indicator_id == "real_policy_rate":
            return self._real_policy_rate(country, spec)
        if spec.indicator_id == "debt_fx_share":
            return self._debt_fx_share(country, spec)
        if spec.indicator_id == "foreign_ownership_bonds":
            return self._foreign_ownership_bonds(country, spec)
        if spec.indicator_id == "sov_spread_vs_bund":
            return self._sov_spread_vs_bund(country, spec)
        if spec.indicator_id == "cds_5y":
            return self._public_sovereign_risk_spread(country, spec, "CDS substitute")
        if spec.indicator_id == "embi_spread":
            return self._public_sovereign_risk_spread(country, spec, "EMBI substitute")
        if spec.indicator_id == "sov_yield_2y":
            return self._short_rate_market_proxy(country, spec, "2Y sovereign yield proxy")
        if spec.indicator_id == "yield_curve_slope":
            return self._yield_curve_slope(country, spec)
        if spec.indicator_id == "fx_3m_forward":
            return self._fx_3m_forward_points(country, spec)
        if spec.indicator_id == "carry_trade_return":
            return self._carry_trade_return(country, spec)
        if spec.indicator_id == "fx_implied_vol":
            return self._fx_realised_volatility(country, spec)
        if spec.indicator_id == "real_estate_price_gap":
            return self._real_estate_price_gap(country, spec)
        return []

    def _gdp_demand_composite(self, country: str, spec: IndicatorSpec) -> list[dict]:
        countries = load_countries()
        meta = countries.get(country)
        if not meta:
            return []
        consumption = fetch_eurostat(
            "namq_10_gdp",
            meta["iso2"],
            "final_consumption_yoy",
            "Final Consumption Expenditure, YoY",
            country,
            freq="Q",
            since="2018",
            extra_params={"na_item": "P3", "unit": "CLV_PCH_SM", "s_adj": "SCA"},
            unit_label="% YoY",
        )
        investment = fetch_eurostat(
            "namq_10_gdp",
            meta["iso2"],
            "gfcf_yoy",
            "Gross Fixed Capital Formation, YoY",
            country,
            freq="Q",
            since="2018",
            extra_params={"na_item": "P51G", "unit": "CLV_PCH_SM", "s_adj": "SCA"},
            unit_label="% YoY",
        )
        if not consumption.available or not investment.available:
            return []
        investment_by_date = {date: value for date, value in investment.observations}
        observations: list[tuple[str, float]] = []
        for date, value in consumption.observations:
            investment_value = investment_by_date.get(date)
            if investment_value is None:
                continue
            observations.append((date, (float(value) + float(investment_value)) / 2.0))
        series = finalize_series(Series(
            key=spec.indicator_id,
            label=spec.label,
            country=country,
            source="Derived from Eurostat national accounts",
            series_id="namq_10_gdp:P3 and P51G",
            unit="% YoY",
            frequency="quarterly",
            last_update=observations[-1][0] if observations else "",
            source_url="https://ec.europa.eu/eurostat/databrowser/view/namq_10_gdp/default/table?lang=en",
            observations=observations,
            available=bool(observations),
            note="Unweighted average of final consumption and gross fixed capital formation YoY; compact domestic-demand proxy.",
        ))
        return _series_to_rows(
            series,
            spec,
            unit="% YoY",
            note="Derived from Eurostat final-consumption and GFCF volume-growth adapters.",
        )

    def _real_wage_yoy(self, country: str, spec: IndicatorSpec) -> list[dict]:
        countries = load_countries()
        meta = countries.get(country)
        if not meta:
            return []
        wages = fetch_eurostat(
            "lc_lci_r2_q",
            meta["iso2"],
            "avg_wage_yoy",
            "Average Gross Wage, YoY",
            country,
            freq="Q",
            since="2018",
            extra_params={"lcstruct": "D11", "nace_r2": "B-S", "s_adj": "SCA", "unit": "PCH_SM"},
            unit_label="% YoY",
        )
        cpi = fetch_eurostat(
            "prc_hicp_minr",
            meta["iso2"],
            "cpi_yoy",
            "Headline CPI/HICP, YoY",
            country,
            freq="M",
            since="2018",
            extra_params={"coicop18": "TOTAL", "unit": "RCH_A"},
            unit_label="% YoY",
        )
        if not wages.available or not cpi.available:
            return []
        cpi_by_month = {date[:7]: value for date, value in cpi.observations}
        observations: list[tuple[str, float]] = []
        for date, wage in wages.observations:
            month_key = date[:7]
            inflation = cpi_by_month.get(month_key)
            if inflation is None:
                continue
            observations.append((date, float(wage) - float(inflation)))
        series = finalize_series(Series(
            key=spec.indicator_id,
            label=spec.label,
            country=country,
            source="Derived from Eurostat labour-cost and HICP series",
            series_id="lc_lci_r2_q:D11 minus prc_hicp_minr:TOTAL:RCH_A",
            unit="% YoY",
            frequency="quarterly",
            last_update=observations[-1][0] if observations else "",
            source_url="https://ec.europa.eu/eurostat/databrowser/",
            observations=observations,
            available=bool(observations),
            note="Ex-post real wage growth: nominal labour-cost growth minus headline HICP inflation.",
        ))
        return _series_to_rows(series, spec, unit="% YoY", note="Derived from Eurostat wage and HICP adapters.")

    def _real_policy_rate(self, country: str, spec: IndicatorSpec) -> list[dict]:
        countries = load_countries()
        meta = countries.get(country)
        if not meta:
            return []
        nominal_rate = _policy_rate_series(country, IndicatorSpec(
            spec.section_id,
            "policy_rate",
            "Central Bank Policy Rate",
            "%",
            "Central bank",
            "event",
            "line",
            False,
            "verified",
            "Official policy-rate definition.",
        ))
        cpi = fetch_eurostat(
            "prc_hicp_minr",
            meta["iso2"],
            "cpi_yoy",
            "Headline CPI/HICP, YoY",
            country,
            freq="M",
            since="2018",
            extra_params={"coicop18": "TOTAL", "unit": "RCH_A"},
            unit_label="% YoY",
        )
        if not nominal_rate or not nominal_rate.available or not cpi.available:
            return []
        cpi_by_month = {date[:7]: value for date, value in cpi.observations}
        observations: list[tuple[str, float]] = []
        for date, rate in nominal_rate.observations:
            inflation = cpi_by_month.get(date[:7])
            if inflation is None:
                continue
            observations.append((date, float(rate) - float(inflation)))
        series = finalize_series(Series(
            key=spec.indicator_id,
            label=spec.label,
            country=country,
            source="Derived from official policy-rate configuration and Eurostat HICP",
            series_id=f"{nominal_rate.series_id} minus prc_hicp_minr:TOTAL:RCH_A",
            unit="%",
            frequency="monthly",
            last_update=observations[-1][0] if observations else "",
            source_url=nominal_rate.source_url or "https://ec.europa.eu/eurostat/databrowser/",
            observations=observations,
            available=bool(observations),
            note="Ex-post real policy rate: official policy rate minus headline HICP inflation.",
        ))
        return _series_to_rows(series, spec, unit="%", note="Derived from official policy-rate configuration and Eurostat HICP.")

    def _real_estate_price_gap(self, country: str, spec: IndicatorSpec) -> list[dict]:
        countries = load_countries()
        meta = countries.get(country)
        if not meta:
            return []
        hpi_yoy = fetch_eurostat(
            "prc_hpi_q",
            meta["iso2"],
            "house_price_index",
            "House Price Index, YoY",
            country,
            freq="Q",
            since="2015",
            extra_params={"purchase": "TOTAL", "unit": "RCH_A"},
            unit_label="% YoY",
        )
        if not hpi_yoy.available or len(hpi_yoy.observations) < 12:
            return []

        observations: list[tuple[str, float]] = []
        for idx, (date, value) in enumerate(hpi_yoy.observations):
            if idx < 11:
                continue
            window = [float(v) for _, v in hpi_yoy.observations[max(0, idx - 19): idx + 1]]
            trend = sum(window) / len(window)
            observations.append((date, float(value) - trend))

        series = finalize_series(Series(
            key=spec.indicator_id,
            label=spec.label,
            country=country,
            source="Derived from Eurostat House Price Index",
            series_id="prc_hpi_q:TOTAL:RCH_A minus trailing trend",
            unit="pp deviation",
            frequency="quarterly",
            last_update=observations[-1][0] if observations else "",
            source_url="https://ec.europa.eu/eurostat/databrowser/view/prc_hpi_q/default/table?lang=en",
            observations=observations,
            available=bool(observations),
            note="Residential HPI YoY growth minus trailing average; official-data valuation-pressure proxy, not an ECB/BIS model gap.",
        ))
        rows = _series_to_rows(
            series,
            spec,
            unit="pp deviation",
            note="Derived from Eurostat HPI growth; use as directional real-estate pressure, not a formal valuation-gap estimate.",
        )
        for row in rows:
            row["quality_status"] = "watch"
        return rows

    def _debt_fx_share(self, country: str, spec: IndicatorSpec) -> list[dict]:
        countries = load_countries()
        meta = countries.get(country)
        if not meta:
            return []
        common_params = {"sector": "S13", "na_item": "GD", "unit": "MIO_NAC"}
        foreign_currency = fetch_eurostat(
            "gov_10dd_dcur",
            meta["iso2"],
            "debt_fx_amount",
            "FX-Denominated General Government Debt",
            country,
            freq="A",
            since="2015",
            extra_params={**common_params, "currency": "FOR"},
            unit_label="million national currency",
        )
        national_currency = fetch_eurostat(
            "gov_10dd_dcur",
            meta["iso2"],
            "debt_national_currency_amount",
            "National-Currency General Government Debt",
            country,
            freq="A",
            since="2015",
            extra_params={**common_params, "currency": "NAC"},
            unit_label="million national currency",
        )
        if not foreign_currency.available or not national_currency.available:
            return []
        national_by_date = {date: value for date, value in national_currency.observations}
        observations: list[tuple[str, float]] = []
        for date, foreign_value in foreign_currency.observations:
            national_value = national_by_date.get(date)
            if national_value is None:
                continue
            total = float(foreign_value) + float(national_value)
            if total <= 0:
                continue
            observations.append((date, float(foreign_value) / total * 100.0))

        series = finalize_series(Series(
            key=spec.indicator_id,
            label=spec.label,
            country=country,
            source="Derived from Eurostat government debt by currency",
            series_id="gov_10dd_dcur:S13:GD:FOR/(FOR+NAC)",
            unit="%",
            frequency="annual",
            last_update=observations[-1][0] if observations else "",
            source_url="https://ec.europa.eu/eurostat/databrowser/view/gov_10dd_dcur/default/table?lang=en",
            observations=observations,
            available=bool(observations),
            note="FX-denominated Maastricht debt share derived from foreign- and national-currency debt amounts.",
        ))
        return _series_to_rows(
            series,
            spec,
            unit="%",
            note="Derived from Eurostat government-debt currency structure, not a national debt-office trading feed.",
        )

    def _foreign_ownership_bonds(self, country: str, spec: IndicatorSpec) -> list[dict]:
        countries = load_countries()
        meta = countries.get(country)
        if not meta:
            return []
        common_params = {
            "sector": "S13",
            "na_item": "GD",
            "maturity": "TOTAL",
            "unit": "MIO_NAC",
        }
        non_resident_debt = fetch_eurostat(
            "gov_10dd_ggd",
            meta["iso2"],
            "non_resident_government_debt",
            "Non-Resident General Government Debt",
            country,
            freq="A",
            since="2015",
            extra_params={**common_params, "sector2": "S2"},
            unit_label="million national currency",
        )
        total_debt = fetch_eurostat(
            "gov_10dd_ggd",
            meta["iso2"],
            "total_government_debt_by_holder",
            "General Government Debt by Holder",
            country,
            freq="A",
            since="2015",
            extra_params={**common_params, "sector2": "S1_S2"},
            unit_label="million national currency",
        )
        if not non_resident_debt.available or not total_debt.available:
            return []

        total_by_date = {date: value for date, value in total_debt.observations}
        observations: list[tuple[str, float]] = []
        for date, non_resident_value in non_resident_debt.observations:
            total_value = total_by_date.get(date)
            if total_value is None or float(total_value) <= 0:
                continue
            observations.append((date, float(non_resident_value) / float(total_value) * 100.0))

        series = finalize_series(Series(
            key=spec.indicator_id,
            label=spec.label,
            country=country,
            source="Derived from Eurostat government debt by holder sector",
            series_id="gov_10dd_ggd:S13:GD:S2/S1_S2",
            unit="%",
            frequency="annual",
            last_update=observations[-1][0] if observations else "",
            source_url="https://ec.europa.eu/eurostat/databrowser/view/gov_10dd_ggd/default/table?lang=en",
            observations=observations,
            available=bool(observations),
            note="Rest-of-world-held Maastricht debt divided by total holder-sector Maastricht debt.",
        ))
        return _series_to_rows(
            series,
            spec,
            unit="%",
            note="Derived from Eurostat holder-sector government debt; harmonized total-debt share, not a local-bond-only ownership feed.",
        )

    def _sov_spread_vs_bund(self, country: str, spec: IndicatorSpec) -> list[dict]:
        countries = load_countries()
        meta = countries.get(country)
        if not meta:
            return []
        local_yield = fetch_eurostat(
            "irt_lt_mcby_m",
            meta["iso2"],
            "sov_yield_10y",
            "10Y Government Bond Yield",
            country,
            freq="M",
            since="2018",
            extra_params={},
            unit_label="%",
        )
        bund_yield = fetch_eurostat(
            "irt_lt_mcby_m",
            "DE",
            "bund_yield_10y",
            "Germany 10Y Government Bond Yield",
            country,
            freq="M",
            since="2018",
            extra_params={},
            unit_label="%",
        )
        if not local_yield.available or not bund_yield.available:
            return []
        bund_by_date = {date: value for date, value in bund_yield.observations}
        observations: list[tuple[str, float]] = []
        for date, value in local_yield.observations:
            bund = bund_by_date.get(date)
            if bund is None:
                continue
            observations.append((date, (float(value) - float(bund)) * 100.0))
        series = finalize_series(Series(
            key=spec.indicator_id,
            label=spec.label,
            country=country,
            source="Derived from Eurostat long-term government bond yields",
            series_id=f"irt_lt_mcby_m:{meta['iso2']}-DE",
            unit="bp",
            frequency="monthly",
            last_update=observations[-1][0] if observations else "",
            source_url="https://ec.europa.eu/eurostat/databrowser/view/irt_lt_mcby_m/default/table?lang=en",
            observations=observations,
            available=bool(observations),
            note="Monthly 10Y local government yield minus German Bund yield, expressed in basis points.",
        ))
        return _series_to_rows(series, spec, unit="bp", note="Derived from Eurostat sovereign-yield adapters.")

    def _public_sovereign_risk_spread(self, country: str, spec: IndicatorSpec, substitute_label: str) -> list[dict]:
        rows = self._sov_spread_vs_bund(country, spec)
        if not rows:
            return []
        for row in rows:
            row["quality_status"] = "watch"
            row["quality_note"] = (
                f"{row.get('quality_note')} Public {substitute_label}: this is the 10Y local "
                "government yield spread versus Germany from Eurostat, not a licensed CDS, EMBI, "
                "or executable credit-risk quote."
            ).strip()
            row["is_proxy"] = False
        return rows

    def _short_rate_market_proxy(self, country: str, spec: IndicatorSpec, label: str) -> list[dict]:
        countries = load_countries()
        meta = countries.get(country)
        if not meta:
            return []
        short_rate = fetch_eurostat(
            "irt_st_m",
            meta["iso2"],
            spec.indicator_id,
            label,
            country,
            freq="M",
            since="2018",
            extra_params={},
            unit_label="%",
        )
        rows = _series_to_rows(
            short_rate,
            spec,
            unit="%",
            note="Uses Eurostat short-term money-market rate as a public proxy until a true 2Y sovereign-yield feed is wired.",
        )
        for row in rows:
            row["quality_status"] = "low_confidence"
            row["quality_note"] = (
                f"{row.get('quality_note')} Proxy mismatch: short-term money-market rate is not a 2Y government bond yield."
            ).strip()
        return rows

    def _yield_curve_slope(self, country: str, spec: IndicatorSpec) -> list[dict]:
        countries = load_countries()
        meta = countries.get(country)
        if not meta:
            return []
        ten_year = fetch_eurostat(
            "irt_lt_mcby_m",
            meta["iso2"],
            "sov_yield_10y",
            "10Y Government Bond Yield",
            country,
            freq="M",
            since="2018",
            extra_params={},
            unit_label="%",
        )
        short_rate = fetch_eurostat(
            "irt_st_m",
            meta["iso2"],
            "short_rate_proxy",
            "Short-Term Interest Rate",
            country,
            freq="M",
            since="2018",
            extra_params={},
            unit_label="%",
        )
        if not ten_year.available or not short_rate.available:
            return []
        short_by_date = {date: value for date, value in short_rate.observations}
        observations: list[tuple[str, float]] = []
        for date, value in ten_year.observations:
            short = short_by_date.get(date)
            if short is None:
                continue
            observations.append((date, (float(value) - float(short)) * 100.0))
        series = finalize_series(Series(
            key=spec.indicator_id,
            label=spec.label,
            country=country,
            source="Derived from Eurostat interest-rate series",
            series_id=f"irt_lt_mcby_m minus irt_st_m:{meta['iso2']}",
            unit="bp",
            frequency="monthly",
            last_update=observations[-1][0] if observations else "",
            source_url="https://ec.europa.eu/eurostat/databrowser/",
            observations=observations,
            available=bool(observations),
            note="Public yield-curve proxy: 10Y government yield minus Eurostat short-term rate.",
        ))
        rows = _series_to_rows(series, spec, unit="bp", note="Uses short-term rate as the 2Y leg until a true 2Y feed is wired.")
        for row in rows:
            row["quality_status"] = "low_confidence"
            row["quality_note"] = f"{row.get('quality_note')} Proxy mismatch: slope is 10Y minus short rate, not exact 10Y-2Y.".strip()
        return rows

    def _carry_trade_return(self, country: str, spec: IndicatorSpec) -> list[dict]:
        countries = load_countries()
        meta = countries.get(country)
        if not meta:
            return []
        local_rate = fetch_eurostat(
            "irt_st_m",
            meta["iso2"],
            "local_short_rate",
            "Local Short-Term Rate",
            country,
            freq="M",
            since="2018",
            extra_params={"int_rt": "IRT_M3"},
            unit_label="%",
        )
        eur_rate = fetch_eurostat(
            "irt_st_m",
            "EA",
            "eur_short_rate",
            "Euro Area 3M Short-Term Rate",
            country,
            freq="M",
            since="2018",
            extra_params={"int_rt": "IRT_M3"},
            unit_label="%",
        )
        if not local_rate.available or not eur_rate.available:
            return []
        eur_by_date = {date: value for date, value in eur_rate.observations}
        observations: list[tuple[str, float]] = []
        for date, value in local_rate.observations:
            eur = eur_by_date.get(date)
            if eur is None:
                continue
            observations.append((date, float(value) - float(eur)))
        series = finalize_series(Series(
            key=spec.indicator_id,
            label=spec.label,
            country=country,
            source="Derived from Eurostat short-term interest rates",
            series_id=f"irt_st_m:IRT_M3:{meta['iso2']}-EA",
            unit="% annualised",
            frequency="monthly",
            last_update=observations[-1][0] if observations else "",
            source_url="https://ec.europa.eu/eurostat/databrowser/view/irt_st_m/default/table?lang=en",
            observations=observations,
            available=bool(observations),
            note="Carry-only proxy: local 3M short-term rate less euro-area 3M short-term rate, excluding spot FX moves and roll-down.",
        ))
        rows = _series_to_rows(series, spec, unit="% annualised", note="Carry-only proxy; not a realised total-return series.")
        for row in rows:
            row["quality_status"] = "watch"
        return rows

    def _fx_realised_volatility(self, country: str, spec: IndicatorSpec) -> list[dict]:
        countries = load_countries()
        meta = countries.get(country)
        if not meta:
            return []
        fx_series = fetch_ecb_fx(meta["currency"], spec.indicator_id, spec.label, country)
        if not fx_series.available or len(fx_series.observations) < 30:
            return []

        returns: list[tuple[str, float]] = []
        values = fx_series.observations
        for idx in range(1, len(values)):
            date, value = values[idx]
            _, prior = values[idx - 1]
            if prior <= 0:
                continue
            returns.append((date, math.log(float(value) / float(prior))))

        observations: list[tuple[str, float]] = []
        for idx in range(20, len(returns)):
            window = [ret for _, ret in returns[idx - 20: idx + 1]]
            mean = sum(window) / len(window)
            variance = sum((ret - mean) ** 2 for ret in window) / max(len(window) - 1, 1)
            observations.append((returns[idx][0], math.sqrt(variance) * math.sqrt(252) * 100.0))
        if not observations:
            return []

        series = finalize_series(Series(
            key=spec.indicator_id,
            label=spec.label,
            country=country,
            source="Derived from ECB FX reference rates",
            series_id=f"EURFXREF/{meta['currency']}:21d-realised-volatility",
            unit="%",
            frequency="daily",
            last_update=observations[-1][0],
            source_url="https://www.ecb.europa.eu/stats/eurofxref/",
            observations=observations,
            available=True,
            note="Annualised realised volatility computed from ECB daily EUR/local-currency reference-rate returns.",
        ))
        rows = _series_to_rows(
            series,
            spec,
            unit="%",
            note="Annualised 21-trading-day realised volatility from daily ECB EUR/local-currency returns.",
        )
        for row in rows:
            row["quality_status"] = "watch"
            row["is_proxy"] = False
        return rows

    def _fx_3m_forward_points(self, country: str, spec: IndicatorSpec) -> list[dict]:
        countries = load_countries()
        meta = countries.get(country)
        if not meta:
            return []

        try:
            spot = _fetch_eurostat_monthly_fx_end(meta["currency"], "2018")
        except (OSError, requests.RequestException, KeyError, TypeError, ValueError, json.JSONDecodeError):
            return []
        local_rate = fetch_eurostat(
            "irt_st_m",
            meta["iso2"],
            "local_short_rate",
            "Local Short-Term Rate",
            country,
            freq="M",
            since="2018",
            extra_params={"int_rt": "IRT_M3"},
            unit_label="%",
        )
        eur_rate = fetch_eurostat(
            "irt_st_m",
            "EA",
            "eur_short_rate",
            "Euro Area 3M Short-Term Rate",
            country,
            freq="M",
            since="2018",
            extra_params={"int_rt": "IRT_M3"},
            unit_label="%",
        )
        if not spot or not local_rate.available or not eur_rate.available:
            return []

        local_by_month = {date[:7]: value for date, value in local_rate.observations}
        eur_by_month = {date[:7]: value for date, value in eur_rate.observations}
        observations: list[tuple[str, float]] = []
        for date, spot_value in spot:
            month = date[:7]
            local_value = local_by_month.get(month)
            eur_value = eur_by_month.get(month)
            if local_value is None or eur_value is None:
                continue
            local_factor = 1.0 + float(local_value) / 100.0 * 0.25
            eur_factor = 1.0 + float(eur_value) / 100.0 * 0.25
            if eur_factor <= 0:
                continue
            forward_points = float(spot_value) * (local_factor / eur_factor - 1.0)
            observations.append((date, forward_points))

        if not observations:
            return []
        series = finalize_series(Series(
            key=spec.indicator_id,
            label=spec.label,
            country=country,
            source="Derived from Eurostat FX and short-term interest rates",
            series_id=f"ert_bil_eur_m:{meta['currency']}:END + irt_st_m:IRT_M3:{meta['iso2']}-EA",
            unit=f"{meta['currency']} per EUR points",
            frequency="monthly",
            last_update=observations[-1][0],
            source_url="https://ec.europa.eu/eurostat/databrowser/view/ert_bil_eur_m/default/table?lang=en",
            observations=observations,
            available=True,
            note=(
                "Covered-interest-parity implied 3M forward points: month-end EUR/LCU spot "
                "times local/euro 3M short-rate differential. This is a public-data estimate, "
                "not executable dealer forward points."
            ),
        ))
        rows = _series_to_rows(
            series,
            spec,
            unit=f"{meta['currency']} per EUR points",
            note="CIP-implied 3M forward points from Eurostat month-end FX and 3M short rates; excludes cross-currency basis and bid/ask.",
        )
        for row in rows:
            row["quality_status"] = "watch"
        return rows


class ECBFetcher(BaseFetcher):
    def fetch(self, country: str, spec: IndicatorSpec) -> list[dict]:
        if spec.indicator_id != "fx_vs_eur":
            return []
        countries = load_countries()
        meta = countries.get(country)
        if not meta:
            return []
        series = fetch_ecb_fx(meta["currency"], spec.indicator_id, spec.label, country)
        return _series_to_rows(series, spec, unit=f'{meta["currency"]} per EUR')


class BISFetcher(BaseFetcher):
    def fetch(self, country: str, spec: IndicatorSpec) -> list[dict]:
        if spec.indicator_id == "credit_to_gdp_gap":
            return self._credit_to_gdp_gap(country, spec)
        if spec.indicator_id == "cb_balance_sheet_gdp":
            return self._central_bank_balance_sheet_gdp(country, spec)
        if spec.indicator_id == "bis_cross_border":
            return self._cross_border_bank_claims(country, spec)
        return []

    def _credit_to_gdp_gap(self, country: str, spec: IndicatorSpec) -> list[dict]:
        countries = load_countries()
        meta = countries.get(country)
        if not meta:
            return []
        try:
            observations = _load_bis_credit_gap_data().get(meta["iso2"], [])
        except (OSError, requests.RequestException, zipfile.BadZipFile, UnicodeDecodeError, csv.Error):
            return []
        observations = [(date, value) for date, value in observations if date >= "2010-01-01"]
        if not observations:
            return []
        series = finalize_series(Series(
            key=spec.indicator_id,
            label=spec.label,
            country=country,
            source="BIS Credit-to-GDP gaps",
            series_id="WS_CREDIT_GAP:C",
            unit="pp",
            frequency="quarterly",
            last_update=observations[-1][0],
            source_url=BIS_CREDIT_GAP_URL,
            observations=observations,
            available=True,
            note="BIS credit-to-GDP gap: private non-financial sector credit ratio minus HP-filter trend.",
        ))
        return _series_to_rows(series, spec, unit="pp", note="BIS bulk CSV data type C: actual minus trend.")

    def _central_bank_balance_sheet_gdp(self, country: str, spec: IndicatorSpec) -> list[dict]:
        countries = load_countries()
        meta = countries.get(country)
        if not meta:
            return []
        try:
            assets = _load_bis_cbta_data().get(meta["iso2"], [])
        except (OSError, requests.RequestException, zipfile.BadZipFile, UnicodeDecodeError, csv.Error):
            return []
        assets = [(date, value) for date, value in assets if date >= "2010-01-01"]
        if not assets:
            return []

        gdp = fetch_wb(meta["iso2"], "NY.GDP.MKTP.CD", "nominal_gdp_usd", "GDP, current US$", country, start=2010, end=2026)
        if not gdp.available:
            gdp = fetch_wb(meta["iso3"], "NY.GDP.MKTP.CD", "nominal_gdp_usd", "GDP, current US$", country, start=2010, end=2026)
        if not gdp.available:
            return []

        gdp_by_year = {date[:4]: float(value) / 1_000_000_000 for date, value in gdp.observations if value}
        observations: list[tuple[str, float]] = []
        for date, assets_usd_bn in assets:
            eligible_years = [year for year in gdp_by_year if year <= date[:4]]
            if not eligible_years:
                continue
            gdp_usd_bn = gdp_by_year[max(eligible_years)]
            if gdp_usd_bn <= 0:
                continue
            observations.append((date, float(assets_usd_bn) / gdp_usd_bn * 100.0))

        if not observations:
            return []
        series = finalize_series(Series(
            key=spec.indicator_id,
            label=spec.label,
            country=country,
            source="BIS CBTA / World Bank WDI",
            series_id="WS_CBTA:USD / NY.GDP.MKTP.CD",
            unit="% GDP",
            frequency="monthly",
            last_update=observations[-1][0],
            source_url=BIS_CBTA_URL,
            observations=observations,
            available=True,
            note="BIS central bank total assets in USD billions divided by World Bank nominal GDP in current USD.",
        ))
        rows = _series_to_rows(
            series,
            spec,
            unit="% GDP",
            note="Derived ratio: BIS CBTA numerator over annual World Bank GDP denominator.",
        )
        for row in rows:
            row["quality_status"] = "watch"
        return rows

    def _cross_border_bank_claims(self, country: str, spec: IndicatorSpec) -> list[dict]:
        countries = load_countries()
        meta = countries.get(country)
        if not meta:
            return []
        series_code = f"Q.S.C.A.TO1.A.5J.A.5A.A.{meta['iso2']}.N"
        try:
            payload = _fetch_dbnomics_bis_series(series_code)
        except (OSError, requests.RequestException, json.JSONDecodeError, KeyError, IndexError):
            return []
        doc = payload.get("series", {}).get("docs", [{}])[0]
        periods = doc.get("period") or []
        values = doc.get("value") or []
        observations: list[tuple[str, float]] = []
        for period, value in zip(periods, values):
            date = _bis_quarter_to_date(str(period))
            if not date or date < "2010-01-01":
                continue
            try:
                numeric = float(value)
            except (TypeError, ValueError):
                continue
            if not math.isfinite(numeric):
                continue
            observations.append((date, numeric / 1_000))
        if not observations:
            return []

        series = finalize_series(Series(
            key=spec.indicator_id,
            label=spec.label,
            country=country,
            source="BIS LBS via DB.nomics",
            series_id=series_code,
            unit="USD bn",
            frequency="quarterly",
            last_update=observations[-1][0],
            source_url="https://data.bis.org/topics/LBS",
            observations=observations,
            available=True,
            note="BIS locational banking statistics: cross-border total claims on residents, all currencies, all reporting countries and sectors. DB.nomics mirror is used for narrow API access.",
        ))
        rows = _series_to_rows(
            series,
            spec,
            unit="USD bn",
            note="Amounts outstanding are converted from USD millions to USD billions.",
        )
        for row in rows:
            row["quality_status"] = "watch"
        return rows


def _load_bis_credit_gap_data() -> dict[str, list[tuple[str, float]]]:
    """Load BIS credit-to-GDP gaps from the public bulk-download ZIP."""
    global _BIS_CREDIT_GAP_CACHE
    if _BIS_CREDIT_GAP_CACHE is not None:
        return _BIS_CREDIT_GAP_CACHE

    zip_path = CACHE_DIR / "bis_ws_credit_gap_csv_flat.zip"
    if _cache_is_fresh(zip_path, max_age_hours=168):
        zip_bytes = zip_path.read_bytes()
    else:
        response = requests.get(BIS_CREDIT_GAP_URL, timeout=45)
        response.raise_for_status()
        zip_bytes = response.content
        zip_path.write_bytes(zip_bytes)

    def quarter_to_date(period: str) -> str | None:
        if "-Q" not in period:
            return None
        year, quarter = period.split("-Q", 1)
        month_day = {"1": "03-31", "2": "06-30", "3": "09-30", "4": "12-31"}.get(quarter)
        if not month_day or not year.isdigit():
            return None
        return f"{year}-{month_day}"

    data: dict[str, list[tuple[str, float]]] = {}
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as archive:
        csv_name = archive.namelist()[0]
        text = archive.read(csv_name).decode("utf-8")
        reader = csv.DictReader(text.splitlines())
        for row in reader:
            country_value = row.get("BORROWERS_CTY:Borrowers' country", "")
            country_code = country_value.split(":", 1)[0]
            dtype = row.get("CG_DTYPE:Credit gap data type", "").split(":", 1)[0]
            if dtype != "C":
                continue
            date = quarter_to_date(row.get("TIME_PERIOD:Time period or range", ""))
            if not date:
                continue
            try:
                value = float(row.get("OBS_VALUE:Observation Value", ""))
            except ValueError:
                continue
            data.setdefault(country_code, []).append((date, value))

    for country_code, observations in data.items():
        observations.sort()
    _BIS_CREDIT_GAP_CACHE = data
    return data


def _bis_quarter_to_date(period: str) -> str | None:
    if "-Q" not in period:
        return None
    year, quarter = period.split("-Q", 1)
    month_day = {"1": "03-31", "2": "06-30", "3": "09-30", "4": "12-31"}.get(quarter)
    if not month_day or not year.isdigit():
        return None
    return f"{year}-{month_day}"


def _fetch_dbnomics_bis_series(series_code: str) -> dict:
    cache_file = CACHE_DIR / f"dbnomics_bis_lbs_{series_code.replace('.', '_')}.json"
    if _cache_is_fresh(cache_file, max_age_hours=72):
        return json.loads(cache_file.read_text())
    response = requests.get(DBNOMICS_BIS_LBS_SERIES_URL.format(series_code=series_code), timeout=30)
    response.raise_for_status()
    payload = response.json()
    cache_file.write_text(json.dumps(payload))
    return payload


def _fetch_dbnomics_imf_fsi_series(series_code: str) -> dict:
    cache_file = CACHE_DIR / f"dbnomics_imf_fsi_{series_code.replace('.', '_')}.json"
    if _cache_is_fresh(cache_file, max_age_hours=72):
        return json.loads(cache_file.read_text())
    response = requests.get(DBNOMICS_IMF_FSI_SERIES_URL.format(series_code=series_code), timeout=30)
    response.raise_for_status()
    payload = response.json()
    cache_file.write_text(json.dumps(payload))
    return payload


def _fetch_dbnomics_ecb_mir_series(series_code: str) -> dict:
    cache_file = CACHE_DIR / f"dbnomics_ecb_mir_{series_code.replace('.', '_')}.json"
    if _cache_is_fresh(cache_file, max_age_hours=72):
        return json.loads(cache_file.read_text())
    response = requests.get(DBNOMICS_ECB_MIR_SERIES_URL.format(series_code=series_code), timeout=30)
    response.raise_for_status()
    payload = response.json()
    cache_file.write_text(json.dumps(payload))
    return payload


def _fetch_ecb_mir_series(series_code: str) -> list[tuple[str, float]]:
    """Fetch ECB MIR directly before falling back to mirrors."""
    cache_file = CACHE_DIR / f"ecb_mir_{series_code.replace('.', '_')}.json"
    if _cache_is_fresh(cache_file, max_age_hours=24):
        payload = json.loads(cache_file.read_text())
    else:
        response = requests.get(
            ECB_MIR_SERIES_URL.format(series_code=series_code),
            params={"startPeriod": "2018-01", "format": "jsondata"},
            timeout=30,
        )
        if response.status_code == 404:
            return []
        response.raise_for_status()
        payload = response.json()
        cache_file.write_text(json.dumps(payload, indent=2, sort_keys=True))
    return _parse_jsonstat_observations(payload)


def _load_bis_cbta_data() -> dict[str, list[tuple[str, float]]]:
    """Load central-bank total assets from the BIS CBTA public bulk ZIP."""
    global _BIS_CBTA_CACHE
    if _BIS_CBTA_CACHE is not None:
        return _BIS_CBTA_CACHE

    zip_path = CACHE_DIR / "bis_ws_cbta_csv_flat.zip"
    if _cache_is_fresh(zip_path, max_age_hours=168):
        zip_bytes = zip_path.read_bytes()
    else:
        response = requests.get(BIS_CBTA_URL, timeout=45)
        response.raise_for_status()
        zip_bytes = response.content
        zip_path.write_bytes(zip_bytes)

    def period_to_date(period: str) -> str | None:
        if "-Q" in period:
            year, quarter = period.split("-Q", 1)
            month_day = {"1": "03-31", "2": "06-30", "3": "09-30", "4": "12-31"}.get(quarter)
            if month_day and year.isdigit():
                return f"{year}-{month_day}"
        if len(period) == 7 and period[4] == "-" and period[:4].isdigit() and period[5:7].isdigit():
            return f"{period}-01"
        if len(period) == 4 and period.isdigit():
            return f"{period}-12-31"
        return None

    rows_by_country_date: dict[tuple[str, str], tuple[int, float]] = {}
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as archive:
        csv_name = archive.namelist()[0]
        text = archive.read(csv_name).decode("utf-8")
        reader = csv.DictReader(text.splitlines())
        for row in reader:
            country_code = row.get("REF_AREA:Reference area", "").split(":", 1)[0]
            unit_code = row.get("UNIT_MEASURE:Unit of measure", "").split(":", 1)[0]
            if not country_code or unit_code != "USD":
                continue
            date = period_to_date(row.get("TIME_PERIOD:Time period or range", ""))
            if not date:
                continue
            try:
                value = float(row.get("OBS_VALUE:Observation Value", ""))
            except ValueError:
                continue

            method_code = row.get("COMP_METHOD:Compilation methodology", "").split(":", 1)[0]
            transformation_code = row.get("TRANSFORMATION:Transformation", "").split(":", 1)[0]
            frequency_code = row.get("FREQ:Frequency", "").split(":", 1)[0]
            score = 0
            if method_code == "B":
                score += 4
            if transformation_code == "B":
                score += 2
            if frequency_code == "M":
                score += 2
            elif frequency_code == "Q":
                score += 1

            key = (country_code, date)
            if key not in rows_by_country_date or score > rows_by_country_date[key][0]:
                rows_by_country_date[key] = (score, value)

    data: dict[str, list[tuple[str, float]]] = {}
    for (country_code, date), (_, value) in rows_by_country_date.items():
        data.setdefault(country_code, []).append((date, value))
    for observations in data.values():
        observations.sort()
    _BIS_CBTA_CACHE = data
    return data


class NationalCBFetcher(BaseFetcher):
    def fetch(self, country: str, spec: IndicatorSpec) -> list[dict]:
        if country == "CZ" and spec.indicator_id == "short_term_ext_debt":
            return self._czech_short_term_external_debt_reserves(country, spec)
        if country == "CZ" and spec.indicator_id == "fx_reserves":
            return self._czech_fx_reserves(country, spec)
        return []

    def _czech_fx_reserves(self, country: str, spec: IndicatorSpec) -> list[dict]:
        try:
            reserves = self._cnb_reserves_usd()
        except (OSError, requests.RequestException, ValueError):
            return []
        observations = [(date, value / 1_000.0) for date, value in sorted(reserves.items()) if date >= "2022-01-01"]
        if not observations:
            return []

        series = finalize_series(Series(
            key=spec.indicator_id,
            label=spec.label,
            country=country,
            source="Czech National Bank",
            series_id="CNB international reserves, USD",
            unit="USD bn",
            frequency="monthly",
            last_update=observations[-1][0],
            source_url=CNB_RESERVES_USD_TXT_URL,
            observations=observations,
            available=True,
            note="CNB official international reserves in USD, converted from USD millions to USD billions.",
        ))
        return _series_to_rows(
            series,
            spec,
            unit="USD bn",
            note="Official CNB reserves series; USD valuation effects remain material.",
        )

    def _czech_short_term_external_debt_reserves(self, country: str, spec: IndicatorSpec) -> list[dict]:
        try:
            debt = self._cnb_short_term_external_debt_usd()
            reserves = self._cnb_reserves_usd()
        except (OSError, requests.RequestException, ValueError):
            return []
        observations = []
        for date, debt_usd_mn in debt:
            reserves_usd_mn = reserves.get(date)
            if not reserves_usd_mn or reserves_usd_mn <= 0:
                continue
            observations.append((date, debt_usd_mn / reserves_usd_mn * 100.0))
        observations.sort()
        if not observations:
            return []

        series = finalize_series(Series(
            key=spec.indicator_id,
            label=spec.label,
            country=country,
            source="CNB external debt / CNB international reserves",
            series_id="CNB USD short-term external debt / CNB USD reserves",
            unit="%",
            frequency="quarterly",
            last_update=observations[-1][0],
            source_url=CNB_EXTERNAL_DEBT_USD_URLS[0],
            observations=observations,
            available=True,
            note=(
                "Czech National Bank USD short-term external debt position divided by "
                "CNB end-period international reserves in USD."
            ),
        ))
        rows = _series_to_rows(
            series,
            spec,
            unit="%",
            note=(
                "National-CB override for Czechia where IMF ARA ratio coverage is missing; "
                "external debt is quarterly while reserve denominator is matched to quarter-end."
            ),
        )
        for row in rows:
            row["quality_status"] = "watch"
        return rows

    def _cnb_short_term_external_debt_usd(self) -> list[tuple[str, float]]:
        observations: dict[str, float] = {}
        for url in CNB_EXTERNAL_DEBT_USD_URLS:
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            parser = _HTMLTableParser()
            parser.feed(response.text)
            for table in parser.tables:
                if len(table) < 2:
                    continue
                header = table[0]
                short_term = next(
                    (row for row in table[1:] if row and row[0].strip().lower() == "short-term"),
                    None,
                )
                if not short_term:
                    continue
                for raw_date, raw_value in zip(header[1:], short_term[1:]):
                    date = _cnb_day_month_year_to_iso(raw_date)
                    if not date or date < "2022-01-01":
                        continue
                    observations[date] = _parse_cnb_number(raw_value)
        return sorted(observations.items())

    def _cnb_reserves_usd(self) -> dict[str, float]:
        response = requests.get(CNB_RESERVES_USD_TXT_URL, timeout=30)
        response.raise_for_status()
        observations: dict[str, float] = {}
        for line in response.text.splitlines()[1:]:
            cells = line.split("|")
            if len(cells) < 2:
                continue
            date = _cnb_day_month_year_to_iso(cells[0])
            if not date or date < "2022-01-01":
                continue
            observations[date] = _parse_cnb_number(cells[1])
        return observations


class CZSOFetcher(BaseFetcher):
    """Czech Statistical Office open-data adapters."""

    def fetch(self, country: str, spec: IndicatorSpec) -> list[dict]:
        if country == "CZ" and spec.indicator_id == "import_prices_yoy":
            return self._import_prices_yoy(country, spec)
        return []

    def _import_prices_yoy(self, country: str, spec: IndicatorSpec) -> list[dict]:
        try:
            response = requests.get(CZSO_IMPORT_PRICE_CSV_URL, timeout=45)
            response.raise_for_status()
            observations = self._parse_import_price_csv(response.text)
        except (OSError, requests.RequestException, csv.Error, TypeError, ValueError):
            return []
        if not observations:
            return []

        series = finalize_series(Series(
            key=spec.indicator_id,
            label=spec.label,
            country=country,
            source="Czech Statistical Office open data",
            series_id="CEN0301:614703:ABCDEJ:IR",
            unit="% YoY",
            frequency="monthly",
            last_update=observations[-1][0],
            source_url=CZSO_IMPORT_PRICE_CSV_URL,
            observations=observations,
            available=True,
            note=(
                "CZSO import price index for total CPA aggregate, monthly year-on-year "
                "index converted from index form to percent change."
            ),
        ))
        rows = _series_to_rows(
            series,
            spec,
            unit="% YoY",
            note="Czechia national-statistics override where Eurostat import-price coverage is incomplete.",
        )
        for row in rows:
            row["quality_status"] = "watch"
        return rows

    def _parse_import_price_csv(self, text: str) -> list[tuple[str, float]]:
        observations: list[tuple[str, float]] = []
        for row in csv.DictReader(text.splitlines()):
            period = str(row.get("CASMKMQRM12") or "")
            if (
                row.get("IndicatorType") != "614703"
                or row.get("CZCPAVAD.CZCPA1") != "ABCDEJ"
                or row.get("TYPUDAJE5B") != "IR"
                or len(period) != 7
                or period[4] != "-"
                or not period[:4].isdigit()
                or not period[5:7].isdigit()
                or not 1 <= int(period[5:7]) <= 12
            ):
                continue
            value = float(str(row.get("Hodnota") or "").replace(",", "."))
            observations.append((f"{period}-01", value - 100.0))
        return sorted(observations)


class KSHFetcher(BaseFetcher):
    """Hungarian Central Statistical Office STADAT adapters."""

    def fetch(self, country: str, spec: IndicatorSpec) -> list[dict]:
        if country == "HU" and spec.indicator_id == "import_prices_yoy":
            return self._import_prices_yoy(country, spec)
        return []

    def _import_prices_yoy(self, country: str, spec: IndicatorSpec) -> list[dict]:
        try:
            response = requests.get(KSH_IMPORT_PRICE_CSV_URL, timeout=45)
            response.raise_for_status()
            observations = self._parse_import_price_csv(response.text)
        except (OSError, requests.RequestException, csv.Error, TypeError, ValueError):
            return []
        if not observations:
            return []

        series = finalize_series(Series(
            key=spec.indicator_id,
            label=spec.label,
            country=country,
            source="Hungarian Central Statistical Office STADAT",
            series_id="STADAT:ara0046:import-monthly-total",
            unit="% YoY",
            frequency="monthly",
            last_update=observations[-1][0],
            source_url=KSH_IMPORT_PRICE_CSV_URL,
            observations=observations,
            available=True,
            note=(
                "KSH external-trade import price index, total monthly series with "
                "corresponding period of previous year = 100 converted to percent."
            ),
        ))
        rows = _series_to_rows(
            series,
            spec,
            unit="% YoY",
            note=(
                "Hungary national-statistics override; latest KSH methodology column "
                "is preferred and older-method values fill only missing early history."
            ),
        )
        for row in rows:
            row["quality_status"] = "watch"
        return rows

    def _parse_import_price_csv(self, text: str) -> list[tuple[str, float]]:
        observations: list[tuple[str, float]] = []
        current_year = ""
        in_import_monthly = False
        for row in csv.reader(io.StringIO(text), delimiter=";"):
            if not row:
                continue
            section = str(row[0]).strip()
            if section == "Import, monthly":
                in_import_monthly = True
                continue
            if in_import_monthly and section.startswith(("Import,", "Export,")):
                break
            if not in_import_monthly or len(row) < 8:
                continue
            year = section or current_year
            period = str(row[1]).strip()
            if section.isdigit():
                current_year = section
                year = section
            if not year.isdigit():
                continue
            try:
                month = datetime.strptime(period, "%B").month
            except ValueError:
                continue

            value = _parse_ksh_number(row[7])
            if value is None:
                value = _parse_ksh_number(row[6])
            if value is None:
                continue
            observations.append((f"{year}-{month:02d}-01", value - 100.0))
        return sorted(observations)


def _parse_ksh_number(raw: str) -> float | None:
    value = str(raw).strip()
    if not value or value == "..":
        return None
    try:
        return float(value.replace(",", "."))
    except ValueError:
        return None


class GUSDBWFetcher(BaseFetcher):
    """Statistics Poland DBW API adapters."""

    IMPORT_PRICE_VARIABLE_ID = 329
    IMPORT_PRICE_SECTION_ID = 772
    IMPORT_POSITION_ID = 4768413
    INDUSTRIAL_PRODUCTS_TOTAL_POSITION_ID = 7124459
    YOY_PRESENTATION_ID = 5

    def fetch(self, country: str, spec: IndicatorSpec) -> list[dict]:
        if country == "PL" and spec.indicator_id == "import_prices_yoy":
            return self._import_prices_yoy(country, spec)
        return []

    def _import_prices_yoy(self, country: str, spec: IndicatorSpec) -> list[dict]:
        cached = self._load_cached_observations()
        observations: list[tuple[str, float]] = list(cached)
        session = requests.Session()
        current_year = datetime.utcnow().year
        current_month = datetime.utcnow().month
        latest_cached = max((date for date, _ in observations), default="")
        failed_requests = 0

        for year in range(2022, current_year + 1):
            for month in range(1, 13):
                if year == current_year and month > current_month:
                    break
                date = f"{year}-{month:02d}-01"
                if date <= latest_cached:
                    continue
                try:
                    payload = self._fetch_month_payload(session, year, month)
                    value = self._find_import_total_yoy(payload)
                except (OSError, requests.RequestException, TypeError, ValueError, json.JSONDecodeError):
                    # DBW returns 404 for unavailable months and can rate-limit anonymous clients.
                    failed_requests += 1
                    if failed_requests >= 6 and observations:
                        break
                    continue
                finally:
                    # Anonymous DBW clients are capped; keep live refresh gentle.
                    time.sleep(0.22)
                if value is None:
                    continue
                observations.append((date, value - 100.0))
            if failed_requests >= 6 and observations:
                break
        if not observations:
            return []
        observations = sorted(dict(observations).items())
        self._write_cached_observations(observations)

        series = finalize_series(Series(
            key=spec.indicator_id,
            label=spec.label,
            country=country,
            source="Statistics Poland DBW API",
            series_id="DBW:variable-329:section-772:import:industrial-products-total:yoy",
            unit="% YoY",
            frequency="monthly",
            last_update=observations[-1][0],
            source_url=GUS_DBW_VARIABLE_DATA_URL,
            observations=sorted(observations),
            available=True,
            note=(
                "Statistics Poland import price index for industrial products total, "
                "monthly corresponding period of previous year = 100 converted to percent."
            ),
        ))
        rows = _series_to_rows(
            series,
            spec,
            unit="% YoY",
            note=(
                "Poland DBW national-statistics override uses variable 329 and the "
                "industrial-products-total CPA B-D position."
            ),
        )
        for row in rows:
            row["quality_status"] = "watch"
        return rows

    def _cache_file(self) -> Path:
        return cache_path("gus_dbw::import_prices_yoy::pl::variable_329_section_772")

    def _load_cached_observations(self) -> list[tuple[str, float]]:
        path = self._cache_file()
        if not path.exists():
            return []
        try:
            payload = json.loads(path.read_text())
        except (OSError, json.JSONDecodeError):
            return []
        observations = []
        for item in payload.get("observations") or []:
            try:
                observations.append((str(item["date"])[:10], float(item["value"])))
            except (KeyError, TypeError, ValueError):
                continue
        return sorted(observations)

    def _write_cached_observations(self, observations: list[tuple[str, float]]) -> None:
        payload = {
            "source": "Statistics Poland DBW API",
            "series_id": "DBW:variable-329:section-772:import:industrial-products-total:yoy",
            "fetched": datetime.utcnow().isoformat() + "Z",
            "observations": [
                {"date": date, "value": value}
                for date, value in observations
            ],
        }
        try:
            self._cache_file().write_text(json.dumps(payload, indent=2, sort_keys=True))
        except OSError:
            return

    def _fetch_month_payload(self, session: requests.Session, year: int, month: int) -> dict:
        query = (
            f"gus_dbw::variable_data_section::{self.IMPORT_PRICE_VARIABLE_ID}::"
            f"{self.IMPORT_PRICE_SECTION_ID}::{year}::{month}"
        )
        path = cache_path(query)
        if _cache_is_fresh(path, max_age_hours=72):
            return json.loads(path.read_text())
        response = session.get(
            GUS_DBW_VARIABLE_DATA_URL,
            params={
                "id-zmienna": self.IMPORT_PRICE_VARIABLE_ID,
                "id-przekroj": self.IMPORT_PRICE_SECTION_ID,
                "id-rok": year,
                "id-okres": 246 + month,
                "ile-na-stronie": 5000,
                "numer-strony": 0,
                "lang": "en",
            },
            timeout=30,
        )
        response.raise_for_status()
        payload = response.json()
        path.write_text(json.dumps(payload))
        return payload

    def _find_import_total_yoy(self, payload: dict) -> float | None:
        for row in payload.get("data") or []:
            if (
                row.get("id-pozycja-2") == self.IMPORT_POSITION_ID
                and row.get("id-pozycja-3") == self.INDUSTRIAL_PRODUCTS_TOTAL_POSITION_ID
                and row.get("id-sposob-prezentacji-miara") == self.YOY_PRESENTATION_ID
                and row.get("id-brak-wartosci") == 253
            ):
                return float(row["wartosc"])
        return None


class INSSETempoFetcher(BaseFetcher):
    """Romanian National Institute of Statistics TEMPO adapters."""

    IMPORT_UNIT_VALUE_MATRIX = "EXP105A"
    IMPORT_NOM_ITEM_ID = 7100
    PERCENTAGE_UNIT_ID = 10225

    def fetch(self, country: str, spec: IndicatorSpec) -> list[dict]:
        if country == "RO" and spec.indicator_id == "import_prices_yoy":
            return self._import_unit_value_yoy(country, spec)
        return []

    def _import_unit_value_yoy(self, country: str, spec: IndicatorSpec) -> list[dict]:
        try:
            observations = self._fetch_import_unit_value_observations()
        except (OSError, requests.RequestException, TypeError, ValueError, json.JSONDecodeError):
            return []
        if not observations:
            return []

        series = finalize_series(Series(
            key=spec.indicator_id,
            label=spec.label,
            country=country,
            source="INSSE TEMPO",
            series_id="EXP105A:import-unit-value-index",
            unit="% YoY",
            frequency="annual",
            last_update=observations[-1][0],
            source_url="http://statistici.insse.ro:8077/tempo-ins/matrix/EXP105A/",
            observations=observations,
            available=True,
            note=(
                "Official annual import unit-value index from Romania's TEMPO database, "
                "converted from previous-year=100 index to percent change."
            ),
        ))
        annual_spec = IndicatorSpec(
            spec.section_id,
            spec.indicator_id,
            spec.label,
            spec.unit,
            spec.source,
            "annual",
            spec.chart,
            spec.peers,
            spec.quality_status,
            spec.quality_note,
        )
        rows = _series_to_rows(
            series,
            annual_spec,
            unit="% YoY",
            note=(
                "Romania substitute uses annual import unit-value indices, not a monthly "
                "transaction import-price index; use as a broad external-price signal."
            ),
        )
        for row in rows:
            row["quality_status"] = "watch"
        return rows

    def _fetch_import_unit_value_observations(self) -> list[tuple[str, float]]:
        start_year = 2018
        current_year = datetime.utcnow().year
        year_ids = [
            str(4437 + 19 * (year - 2000))
            for year in range(start_year, current_year + 1)
        ]
        body = {
            "language": "en",
            "encQuery": (
                f"{self.IMPORT_NOM_ITEM_ID}:"
                f"{','.join(year_ids)}:"
                f"{self.PERCENTAGE_UNIT_ID}"
            ),
            "matCode": self.IMPORT_UNIT_VALUE_MATRIX,
            "nomJud": 0,
            "nomLoc": 0,
            "matMaxDim": 3,
            "matUMSpec": 0,
            "matSiruta": 0,
            "matCaen1": 0,
            "matCaen2": 0,
            "matRegJ": 0,
            "matCharge": 0,
            "matViews": 0,
            "matDownloads": 0,
            "matActive": 1,
            "matTime": 2,
        }
        path = cache_path(
            f"insse_tempo::{self.IMPORT_UNIT_VALUE_MATRIX}::import::{start_year}-{current_year}"
        )
        if path.exists():
            text = path.read_text()
        else:
            response = requests.post(
                INSSE_TEMPO_PIVOT_URL,
                params={"lang": "en"},
                json=body,
                timeout=30,
            )
            response.raise_for_status()
            text = response.text
            path.write_text(text)

        observations: list[tuple[str, float]] = []
        for idx, line in enumerate(text.splitlines()):
            if idx == 0:
                continue
            cells = [cell.strip() for cell in line.split(", ")]
            if len(cells) < 4 or cells[0] != "Import":
                continue
            year_text = cells[1].replace("Year", "").strip()
            if not year_text.isdigit():
                continue
            value = float(cells[-1]) - 100.0
            observations.append((f"{year_text}-12-31", value))
        return sorted(observations)


class WorldBankFallbackFetcher(BaseFetcher):
    """Fallback adapters for indicators with partial official-source coverage."""

    def fetch(self, country: str, spec: IndicatorSpec) -> list[dict]:
        if spec.indicator_id == "credit_to_gdp_gap":
            return self._credit_to_gdp_gap(country, spec)
        return []

    def _credit_to_gdp_gap(self, country: str, spec: IndicatorSpec) -> list[dict]:
        countries = load_countries()
        meta = countries.get(country)
        if not meta:
            return []
        credit = fetch_wb(
            meta["iso2"],
            "FS.AST.PRVT.GD.ZS",
            "private_credit_to_gdp",
            "Domestic Credit to Private Sector by Banks, % GDP",
            country,
            start=1995,
            end=2026,
        )
        if not credit.available or len(credit.observations) < 12:
            return []
        observations: list[tuple[str, float]] = []
        for idx, (date, value) in enumerate(credit.observations):
            if idx < 9:
                continue
            window = [float(v) for _, v in credit.observations[idx - 9: idx + 1]]
            trend = sum(window) / len(window)
            observations.append((date, float(value) - trend))
        series = finalize_series(Series(
            key=spec.indicator_id,
            label=spec.label,
            country=country,
            source="World Bank WDI fallback",
            series_id="FS.AST.PRVT.GD.ZS minus 10Y trailing average",
            unit="pp",
            frequency="annual",
            last_update=observations[-1][0] if observations else "",
            source_url="https://data.worldbank.org/indicator/FS.AST.PRVT.GD.ZS",
            observations=observations,
            available=bool(observations),
            note="Fallback credit-gap proxy using domestic credit to private sector by banks, % GDP, minus a 10-year trailing average.",
        ))
        rows = _series_to_rows(
            series,
            spec,
            unit="pp",
            note="Used only when BIS credit-gap data is unavailable; annual and not methodologically identical to BIS HP-filter gap.",
        )
        for row in rows:
            row["quality_status"] = "low_confidence"
            row["quality_note"] = (
                f"{row.get('quality_note')} Methodology fallback: World Bank annual credit/GDP "
                "minus trailing average, not BIS HP-filter credit gap."
            ).strip()
        return rows


class IMFFinancialSoundnessFetcher(BaseFetcher):
    """IMF FSI adapter through DB.nomics narrow series API."""

    CONFIGS = {
        "bank_car": {
            "indicator": "FSKRC_PT",
            "unit": "%",
            "note": "IMF Financial Soundness Indicator: deposit-taker regulatory capital to risk-weighted assets, percent.",
        },
        "bank_npl_ratio": {
            "indicator": "FSANL_PT",
            "unit": "%",
            "note": "IMF Financial Soundness Indicator: deposit-taker non-performing loans to total gross loans, percent.",
        },
        "bank_roe": {
            "indicator": "FSERE_PT",
            "unit": "%",
            "note": "IMF Financial Soundness Indicator: deposit-taker return on equity, percent.",
        },
        "bank_ld_ratio": {
            "indicator": "FSCD_PT",
            "unit": "%",
            "transform": "invert_percent_ratio",
            "note": "IMF Financial Soundness Indicator reports customer deposits to total non-interbank loans; the dashboard inverts it to approximate loans to customer deposits.",
        },
        "bank_liquidity_coverage": {
            "indicator": "FSLCR_PT",
            "unit": "%",
            "note": "IMF Financial Soundness Indicator: deposit-taker liquidity coverage ratio, percent.",
        },
        "fx_loan_share": {
            "indicator": "FSFC_PT",
            "unit": "%",
            "min_latest": "2020-01-01",
            "note": "IMF Financial Soundness Indicator: deposit-taker foreign-currency-denominated loans to total loans, percent.",
        },
    }

    def fetch(self, country: str, spec: IndicatorSpec) -> list[dict]:
        cfg = self.CONFIGS.get(spec.indicator_id)
        if not cfg:
            return []
        countries = load_countries()
        meta = countries.get(country)
        if not meta:
            return []
        series_code = f"Q.{meta['iso2']}.{cfg['indicator']}"
        try:
            payload = _fetch_dbnomics_imf_fsi_series(series_code)
        except (OSError, requests.RequestException, json.JSONDecodeError, KeyError, IndexError):
            return []
        doc = payload.get("series", {}).get("docs", [{}])[0]
        observations: list[tuple[str, float]] = []
        for period, value in zip(doc.get("period") or [], doc.get("value") or []):
            date = _bis_quarter_to_date(str(period))
            if not date or date < "2010-01-01":
                continue
            try:
                numeric = float(value)
            except (TypeError, ValueError):
                continue
            if cfg.get("transform") == "invert_percent_ratio":
                if numeric == 0:
                    continue
                numeric = 10000.0 / numeric
            if math.isfinite(numeric):
                observations.append((date, numeric))
        if not observations:
            return []
        if observations[-1][0] < str(cfg.get("min_latest") or ""):
            return []

        series = finalize_series(Series(
            key=spec.indicator_id,
            label=spec.label,
            country=country,
            source="IMF FSI via DB.nomics",
            series_id=series_code,
            unit=cfg["unit"],
            frequency="quarterly",
            last_update=observations[-1][0],
            source_url="https://data.imf.org/en/Datasets/FSIC",
            observations=observations,
            available=True,
            note=cfg["note"],
        ))
        rows = _series_to_rows(series, spec, unit=cfg["unit"], note="DB.nomics mirror is used for narrow API access.")
        for row in rows:
            row["quality_status"] = "watch"
            if cfg.get("transform") == "invert_percent_ratio":
                row["quality_note"] = (
                    f"{row.get('quality_note') or ''} "
                    "Series transformed from IMF deposits-to-loans into loans-to-deposits; "
                    "compare levels with national supervisory definitions."
                ).strip()
        return rows


class ECBMIRFetcher(BaseFetcher):
    """ECB MFI interest-rate statistics adapter through DB.nomics."""

    CONFIGS = {
        "mortgage_rate_new": {
            "bs_item": "A2C",
            "sector": "2250",
            "note": "New-business household loans for house purchase, excluding revolving loans and overdrafts.",
        },
        "lending_rate_household": {
            "bs_item": "A2B",
            "sector": "2250",
            "note": "New-business household consumption loans, excluding revolving loans and overdrafts.",
        },
        "lending_rate_corp": {
            "bs_item": "A2A",
            "sector": "2240",
            "note": "New-business loans to non-financial corporations, excluding revolving loans and overdrafts.",
        },
    }

    def fetch(self, country: str, spec: IndicatorSpec) -> list[dict]:
        cfg = self.CONFIGS.get(spec.indicator_id)
        if not cfg:
            return []
        countries = load_countries()
        meta = countries.get(country)
        if not meta:
            return []
        series_code = f"M.{meta['iso2']}.B.{cfg['bs_item']}.A.R.A.{cfg['sector']}.{meta['currency']}.N"
        try:
            observations = _fetch_ecb_mir_series(series_code)
        except (OSError, requests.RequestException, json.JSONDecodeError, KeyError, IndexError):
            observations = []
        source = "ECB MIR"
        source_note = "ECB Data API is used directly."
        if observations:
            observations = [(date, value) for date, value in observations if date >= "2018-01-01"]
        if not observations:
            source = "ECB MIR via DB.nomics"
            source_note = "DB.nomics mirror is used as fallback because the direct ECB Data API returned no observations."
            try:
                payload = _fetch_dbnomics_ecb_mir_series(series_code)
            except (OSError, requests.RequestException, json.JSONDecodeError, KeyError, IndexError):
                return []
            doc = payload.get("series", {}).get("docs", [{}])[0]
            observations = []
            for period, value in zip(doc.get("period") or [], doc.get("value") or []):
                if len(str(period)) != 7:
                    continue
                date = f"{period}-01"
                if date < "2018-01-01":
                    continue
                try:
                    numeric = float(value)
                except (TypeError, ValueError):
                    continue
                if math.isfinite(numeric):
                    observations.append((date, numeric))
        if not observations:
            return []
        observations.sort()

        series = finalize_series(Series(
            key=spec.indicator_id,
            label=spec.label,
            country=country,
            source=source,
            series_id=series_code,
            unit="%",
            frequency="monthly",
            last_update=observations[-1][0],
            source_url="https://data.ecb.europa.eu/data/datasets/MIR",
            observations=observations,
            available=True,
            note=f"ECB MFI interest-rate statistics: {cfg['note']} Annualised agreed rate / narrowly defined effective rate in local currency.",
        ))
        rows = _series_to_rows(series, spec, unit="%", note=source_note)
        if source != "ECB MIR":
            for row in rows:
                row["quality_status"] = "watch"
        return rows


class ECBExternalDebtFetcher(BaseFetcher):
    """ECB BPS external-debt component adapter with Eurostat GDP denominator."""

    COMPONENT_KEYS = (
        ("portfolio_debt", "P", "F3", "M"),
        ("other_investment_currency_deposits", "O", "F2", "N"),
        ("other_investment_loans", "O", "F4", "N"),
        ("other_investment_trade_credits", "O", "F81", "_X"),
        ("other_investment_other_debt", "O", "FY", "_X"),
    )

    def fetch(self, country: str, spec: IndicatorSpec) -> list[dict]:
        if spec.indicator_id != "gross_ext_debt":
            return []
        countries = load_countries()
        meta = countries.get(country)
        if not meta:
            return []

        component_observations: list[dict[str, float]] = []
        component_names: list[str] = []
        for name, functional_category, instrument, valuation in self.COMPONENT_KEYS:
            series_code = (
                f"Q.N.{meta['iso2']}.W1.S1.S1.LE.L.FA."
                f"{functional_category}.{instrument}.T.EUR._T.{valuation}.N.ALL"
            )
            observations = self._fetch_bps_component(series_code)
            if not observations:
                continue
            component_names.append(name)
            component_observations.append({date: value for date, value in observations})

        if len(component_observations) < 3:
            return []

        gdp_series = fetch_eurostat(
            "namq_10_gdp",
            meta["iso2"],
            "nominal_gdp_quarterly",
            "Nominal GDP",
            country,
            freq="Q",
            since="2018",
            extra_params={"na_item": "B1GQ", "unit": "CP_MEUR", "s_adj": "NSA"},
            unit_label="EUR mn",
            indicator_label="Nominal GDP",
        )
        if not gdp_series.available or len(gdp_series.observations) < 4:
            return []
        gdp_by_date = {date: value for date, value in gdp_series.observations}
        gdp_dates = [date for date, _ in gdp_series.observations]

        observations: list[tuple[str, float]] = []
        common_dates = sorted(set.intersection(*(set(item) for item in component_observations)))
        for date in common_dates:
            if date not in gdp_by_date:
                continue
            try:
                idx = gdp_dates.index(date)
            except ValueError:
                continue
            if idx < 3:
                continue
            trailing_gdp = sum(float(gdp_by_date[gdp_dates[i]]) for i in range(idx - 3, idx + 1))
            if trailing_gdp <= 0:
                continue
            external_debt = sum(float(component[date]) for component in component_observations)
            observations.append((date, external_debt / trailing_gdp * 100.0))

        if not observations:
            return []

        series = finalize_series(Series(
            key=spec.indicator_id,
            label=spec.label,
            country=country,
            source="ECB BPS / Eurostat GDP",
            series_id="BPS external-debt liability components / rolling 4Q GDP",
            unit="% GDP",
            frequency="quarterly",
            last_update=observations[-1][0],
            source_url="https://data.ecb.europa.eu/main-figures/external-sector/external-debt",
            observations=observations,
            available=True,
            note=(
                "Component-based gross external debt estimate from ECB BPS liabilities: "
                f"{', '.join(component_names)}; scaled by Eurostat rolling four-quarter nominal GDP."
            ),
        ))
        rows = _series_to_rows(
            series,
            spec,
            unit="% GDP",
            note=(
                "Official ECB BPS component stack; direct-investment intercompany debt is not included "
                "unless reported through the selected debt-instrument components, so compare with national external-debt releases."
            ),
        )
        for row in rows:
            row["quality_status"] = "watch"
        return rows

    def _fetch_bps_component(self, series_code: str) -> list[tuple[str, float]]:
        query = f"ecb_bps::{series_code}::2018-2026"
        path = cache_path(query)
        if _cache_is_fresh(path, max_age_hours=72):
            payload = json.loads(path.read_text())
        else:
            response = requests.get(
                ECB_BPS_SERIES_URL.format(series_code=series_code),
                params={"startPeriod": "2018-Q1", "format": "jsondata"},
                timeout=30,
            )
            if response.status_code == 404:
                return []
            response.raise_for_status()
            payload = response.json()
            path.write_text(json.dumps(payload, indent=2, sort_keys=True))
        return _parse_jsonstat_observations(payload)


class ECBPortfolioFlowsFetcher(BaseFetcher):
    """ECB BPS adapter for non-resident portfolio-liability transactions."""

    def fetch(self, country: str, spec: IndicatorSpec) -> list[dict]:
        if spec.indicator_id != "portfolio_flows":
            return []
        countries = load_countries()
        meta = countries.get(country)
        if not meta:
            return []

        series_code = f"M.N.{meta['iso2']}.W1.S1.S1.T.L.FA.P.F._Z.EUR._T.M.N.ALL"
        observations = self._fetch_bps_series(series_code)
        if not observations:
            return []

        series = finalize_series(Series(
            key=spec.indicator_id,
            label=spec.label,
            country=country,
            source="ECB BPS",
            series_id=series_code,
            unit="EUR mn",
            frequency="monthly",
            last_update=observations[-1][0],
            source_url="https://data.ecb.europa.eu/data/datasets/BPS",
            observations=observations,
            available=True,
            note=(
                "ECB BPS portfolio-investment liabilities, transactions, total financial "
                "assets/liabilities, vis-a-vis rest of world."
            ),
        ))
        rows = _series_to_rows(
            series,
            spec,
            unit="EUR mn",
            note=(
                "Positive values are net incurrence of portfolio-investment liabilities "
                "to non-residents; negative values are net liability reductions."
            ),
        )
        for row in rows:
            row["quality_status"] = "watch"
        return rows

    def _fetch_bps_series(self, series_code: str) -> list[tuple[str, float]]:
        query = f"ecb_bps::{series_code}::2018-2026"
        path = cache_path(query)
        if _cache_is_fresh(path, max_age_hours=72):
            payload = json.loads(path.read_text())
        else:
            response = requests.get(
                ECB_BPS_SERIES_URL.format(series_code=series_code),
                params={"startPeriod": "2018-01", "format": "jsondata"},
                timeout=30,
            )
            if response.status_code == 404:
                return []
            response.raise_for_status()
            payload = response.json()
            path.write_text(json.dumps(payload, indent=2, sort_keys=True))
        return _parse_jsonstat_observations(payload)


class ManualIndicatorFetcher(BaseFetcher):
    """User-maintained research series for non-statistical political-risk inputs."""

    def fetch(self, country: str, spec: IndicatorSpec) -> list[dict]:
        payload = self._load_payload()
        raw_indicator = (payload.get("manual_indicators") or {}).get(spec.indicator_id)
        if not raw_indicator:
            return []
        raw_observations = (raw_indicator.get("observations") or {}).get(country) or []
        observations: list[tuple[str, float]] = []
        for item in raw_observations:
            try:
                observations.append((str(item["date"])[:10], float(item["value"])))
            except (KeyError, TypeError, ValueError):
                continue
        if not observations:
            return []
        observations.sort()
        references = raw_indicator.get("references") or []
        reference_note = " References: " + "; ".join(str(url) for url in references[:3]) if references else ""
        series = finalize_series(Series(
            key=spec.indicator_id,
            label=spec.label,
            country=country,
            source=str(raw_indicator.get("source") or "Manual research series"),
            series_id=f"manual:{spec.indicator_id}",
            unit=str(raw_indicator.get("unit") or spec.unit),
            frequency=spec.frequency,
            last_update=observations[-1][0],
            source_url=str(references[0]) if references else "",
            observations=observations,
            available=True,
            note=f"{raw_indicator.get('quality_note') or spec.quality_note}{reference_note}",
        ))
        rows = _series_to_rows(
            series,
            spec,
            unit=str(raw_indicator.get("unit") or spec.unit),
            note="Maintained in config/manual_indicators.yaml; revise manually when source values change.",
        )
        for row in rows:
            row["quality_status"] = str(raw_indicator.get("quality_status") or "low_confidence")
            row["is_proxy"] = False
            postscript = str(raw_indicator.get("postscript") or (
                "Manual input, not a statistical API series; "
                "treat as a policy-risk marker rather than measured macro data."
            ))
            row["quality_note"] = f"{row.get('quality_note')} {postscript}".strip()
        return rows

    def _load_payload(self) -> dict:
        path = CONFIG_DIR / "manual_indicators.yaml"
        if not path.exists():
            return {}
        return yaml.safe_load(path.read_text()) or {}


class IMFDataMapperFetcher(BaseFetcher):
    """IMF DataMapper adapter for fiscal, labour-market, and reserve-risk series."""

    CONFIGS = {
        "fiscal_balance_pct_gdp": {
            "indicator": "GGXCNL_G01_GDP_PT",
            "unit": "% GDP",
            "source": "IMF Fiscal Monitor",
            "note": "General government net lending/borrowing from IMF Fiscal Monitor; latest years may include IMF forecasts.",
        },
        "primary_balance": {
            "indicator": "GGXONLB_G01_GDP_PT",
            "unit": "% GDP",
            "source": "IMF Fiscal Monitor",
            "note": "General government primary net lending/borrowing from IMF Fiscal Monitor; latest years may include IMF forecasts.",
        },
        "structural_balance": {
            "indicator": "GGCB_G01_PGDP_PT",
            "unit": "% potential GDP",
            "source": "IMF Fiscal Monitor",
            "note": "Cyclically adjusted balance used as the structural-balance estimate; output-gap assumptions matter.",
        },
        "gov_debt_pct_gdp": {
            "indicator": "G_XWDG_G01_GDP_PT",
            "unit": "% GDP",
            "source": "IMF Fiscal Monitor",
            "note": "General government gross debt position from IMF Fiscal Monitor; nominal GDP revisions affect the ratio.",
        },
        "interest_bill_pct_gdp": {
            "indicator": "ie",
            "unit": "% GDP",
            "source": "IMF Public Finances in Modern History",
            "note": "Interest paid on public debt as a share of GDP; annual history is lagged and revision-prone.",
        },
        "unemployment_rate": {
            "indicator": "LUR",
            "unit": "%",
            "source": "IMF WEO",
            "note": "Annual unemployment rate from IMF WEO; use Eurostat for higher-frequency labour-market timing.",
        },
        "short_term_ext_debt": {
            "indicator": "Reserves_STD",
            "unit": "%",
            "source": "IMF Assessing Reserve Adequacy",
            "note": "Derived as 100 divided by IMF reserves-to-short-term-debt ratio; directional external-liquidity risk gauge.",
            "invert_ratio": True,
        },
        "ara_metric": {
            "indicator": "Reserves_ARA",
            "unit": "%",
            "source": "IMF Assessing Reserve Adequacy",
            "note": "Reserve holdings divided by the IMF ARA metric; 100-150% is typically read as an adequate range, subject to country judgment.",
            "scale": 100.0,
        },
        "household_debt_pct_gdp": {
            "indicator": "HH_ALL",
            "unit": "% GDP",
            "source": "IMF Global Debt Database",
            "note": "Household debt, all instruments, as a share of GDP from the IMF Global Debt Database.",
        },
        "corp_debt_pct_gdp": {
            "indicator": "NFC_ALL",
            "unit": "% GDP",
            "source": "IMF Global Debt Database",
            "note": "Nonfinancial corporate debt, all instruments, as a share of GDP from the IMF Global Debt Database.",
        },
    }

    def fetch(self, country: str, spec: IndicatorSpec) -> list[dict]:
        cfg = self.CONFIGS.get(spec.indicator_id)
        if not cfg:
            return []
        countries = load_countries()
        meta = countries.get(country)
        if not meta:
            return []

        indicator = cfg["indicator"]
        try:
            payload = self._fetch_payload(meta["iso3"], indicator)
        except (OSError, requests.RequestException, json.JSONDecodeError, KeyError, TypeError, ValueError):
            return []

        raw_values = (
            payload.get("values", {})
            .get(indicator, {})
            .get(meta["iso3"], {})
        )
        observations: list[tuple[str, float]] = []
        for year, raw_value in sorted(raw_values.items()):
            if not str(year).isdigit():
                continue
            year_int = int(year)
            if year_int < 2010 or year_int > 2026 or raw_value is None:
                continue
            try:
                value = float(raw_value)
            except (TypeError, ValueError):
                continue
            if cfg.get("invert_ratio"):
                if value == 0:
                    continue
                value = 100.0 / value
            value *= float(cfg.get("scale", 1.0))
            observations.append((f"{year_int}-12-31", value))

        if not observations:
            return []

        url = IMF_DATAMAPPER_URL.format(indicator=indicator, iso3=meta["iso3"])
        series = finalize_series(Series(
            key=spec.indicator_id,
            label=spec.label,
            country=country,
            source=cfg["source"],
            series_id=indicator,
            unit=cfg["unit"],
            frequency="annual",
            last_update=observations[-1][0],
            source_url=url,
            observations=observations,
            available=True,
            note=cfg["note"],
        ))
        return _series_to_rows(
            series,
            spec,
            unit=cfg["unit"],
            note=f"{cfg['note']} IMF DataMapper indicator {indicator}.",
        )

    def _fetch_payload(self, iso3: str, indicator: str) -> dict:
        query = f"imf_datamapper::{iso3}::{indicator}::2010-2026"
        path = cache_path(query)
        if _cache_is_fresh(path, max_age_hours=168):
            return json.loads(path.read_text())

        url = IMF_DATAMAPPER_URL.format(indicator=indicator, iso3=iso3)
        params = {"periods": ",".join(str(year) for year in range(2010, 2027))}
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        payload = response.json()
        path.write_text(json.dumps(payload, indent=2, sort_keys=True))
        return payload


class PragueExchangeFetcher(BaseFetcher):
    """Official Prague Stock Exchange PX adapters."""

    def __init__(self) -> None:
        self._monthly_px: list[tuple[str, float]] | None = None
        self._daily_px: list[tuple[str, float]] | None = None

    def fetch(self, country: str, spec: IndicatorSpec) -> list[dict]:
        if country != "CZ" or spec.indicator_id not in {"equity_index", "equity_yoy", "equity_vol_30d"}:
            return []
        if spec.indicator_id == "equity_vol_30d":
            return self._equity_vol_30d(country, spec)

        observations = self._monthly_observations()
        if not observations:
            return []
        series = finalize_series(Series(
            key=spec.indicator_id,
            label=spec.label,
            country=country,
            source="Prague Stock Exchange",
            series_id="PSE:PX:monthly-close",
            unit="Index",
            frequency="monthly",
            last_update=observations[-1][0],
            source_url=PSE_INDEXES_URL,
            observations=observations,
            available=True,
            note="Official PX close sampled from the last Prague Stock Exchange day returned for each month.",
        ))
        if spec.indicator_id == "equity_yoy":
            series = _derive_yoy_series(series, spec, periods=12)
        unit = "% YoY" if spec.indicator_id == "equity_yoy" else "Index"
        return _series_to_rows(
            series,
            spec,
            unit=unit,
            note="Official Czech exchange PX feed; monthly samples use the final available exchange-day close.",
        )

    def _monthly_observations(self) -> list[tuple[str, float]]:
        if self._monthly_px is not None:
            return self._monthly_px
        now = datetime.utcnow()
        observations: list[tuple[str, float]] = []
        for year in range(now.year - 5, now.year + 1):
            start_month = 1
            end_month = now.month if year == now.year else 12
            for month in range(start_month, end_month + 1):
                last_day = calendar.monthrange(year, month)[1]
                values = self._fetch_index_page(
                    1,
                    f"{year}-{month:02d}-01",
                    f"{year}-{month:02d}-{last_day:02d}",
                )
                if not values:
                    continue
                latest = values[0]
                try:
                    observations.append((str(latest["stockExchangeDay"])[:10], float(latest["closingValue"])))
                except (KeyError, TypeError, ValueError):
                    continue
        self._monthly_px = sorted(observations)
        return self._monthly_px

    def _daily_observations(self) -> list[tuple[str, float]]:
        if self._daily_px is not None:
            return self._daily_px
        now = datetime.utcnow()
        first_page = self._fetch_index_page(
            1,
            f"{now.year - 1}-01-01",
            now.strftime("%Y-%m-%d"),
            include_meta=True,
        )
        if not first_page:
            self._daily_px = []
            return self._daily_px
        values, total = first_page
        pages = max(1, math.ceil(total / 10))
        for page in range(2, pages + 1):
            values.extend(self._fetch_index_page(page, f"{now.year - 1}-01-01", now.strftime("%Y-%m-%d")))
        observations: list[tuple[str, float]] = []
        for item in values:
            try:
                observations.append((str(item["stockExchangeDay"])[:10], float(item["closingValue"])))
            except (KeyError, TypeError, ValueError):
                continue
        self._daily_px = sorted(observations)
        return self._daily_px

    def _fetch_index_page(
        self,
        page: int,
        date_from: str,
        date_to: str,
        *,
        include_meta: bool = False,
    ):
        query = f"pse_px::{page}::{date_from}::{date_to}"
        path = cache_path(query)
        try:
            if path.exists():
                payload = json.loads(path.read_text())
            else:
                response = requests.get(
                    PSE_INDEXES_URL,
                    params={"page": page, "indexName": "PX", "dateFrom": date_from, "dateTo": date_to},
                    headers={"X-API-Key": "PSE"},
                    timeout=30,
                )
                response.raise_for_status()
                payload = response.json()
                path.write_text(json.dumps(payload, indent=2, sort_keys=True))
        except (OSError, requests.RequestException, TypeError, ValueError, json.JSONDecodeError):
            return ([], 0) if include_meta else []
        values = list(((payload.get("data") or {}).get("values") or []))
        if include_meta:
            return values, int((payload.get("meta") or {}).get("total") or 0)
        return values

    def _equity_vol_30d(self, country: str, spec: IndicatorSpec) -> list[dict]:
        values = self._daily_observations()
        if len(values) < 35:
            return []
        returns: list[tuple[str, float]] = []
        for idx in range(1, len(values)):
            date, value = values[idx]
            _, prior = values[idx - 1]
            if prior <= 0:
                continue
            returns.append((date, math.log(value / prior)))
        observations: list[tuple[str, float]] = []
        for idx in range(20, len(returns)):
            window = [ret for _, ret in returns[idx - 20: idx + 1]]
            mean = sum(window) / len(window)
            variance = sum((ret - mean) ** 2 for ret in window) / max(len(window) - 1, 1)
            observations.append((returns[idx][0], math.sqrt(variance) * math.sqrt(252) * 100.0))
        series = finalize_series(Series(
            key=spec.indicator_id,
            label=spec.label,
            country=country,
            source="Prague Stock Exchange derived",
            series_id="PSE:PX:21d-realised-volatility",
            unit="%",
            frequency="daily",
            last_update=observations[-1][0] if observations else "",
            source_url=PSE_INDEXES_URL,
            observations=observations,
            available=bool(observations),
            note="Annualised realised volatility computed from official daily PX exchange closes.",
        ))
        return _series_to_rows(
            series,
            spec,
            unit="%",
            note="Derived 21-trading-day realised volatility from the official Czech PX close.",
        )


class GPWBenchmarkFetcher(BaseFetcher):
    """Official GPW Benchmark WIG20 snapshot adapters."""

    METRIC_MAP = {
        "equity_index": ("closing", "Index", "Official WIG20 closing level from GPW Benchmark."),
        "equity_vol_30d": (
            "index volatility",
            "%",
            "Official GPW Benchmark index volatility snapshot based on the last 20 sessions; this is a close substitute for the dashboard's 30D realised-volatility slot.",
        ),
        "equity_fwd_pe": (
            "P/E",
            "x",
            "Official GPW Benchmark index P/E snapshot; this is not a forward-consensus multiple.",
        ),
        "equity_pb": ("P/BV", "x", "Official GPW Benchmark index price-to-book-value snapshot."),
        "equity_div_yield": ("Dividend yield (%)", "%", "Official GPW Benchmark index dividend-yield snapshot."),
    }

    def __init__(self) -> None:
        self._snapshot: dict[str, float | str] | None = None

    def fetch(self, country: str, spec: IndicatorSpec) -> list[dict]:
        if country != "PL" or spec.indicator_id not in self.METRIC_MAP:
            return []
        snapshot = self._fetch_snapshot()
        if not snapshot:
            return []
        metric, unit, note = self.METRIC_MAP[spec.indicator_id]
        value = snapshot.get(metric)
        date = str(snapshot.get("date") or "")
        if value is None or not date:
            return []
        observations = [(date, float(value))]
        series = finalize_series(Series(
            key=spec.indicator_id,
            label=spec.label,
            country=country,
            source="GPW Benchmark",
            series_id=f"WIG20:{metric}",
            unit=unit,
            frequency="event",
            last_update=date,
            source_url="https://gpwbenchmark.pl/en-karta-indeksu?isin=PL9999999987",
            observations=observations,
            available=True,
            note=note,
        ))
        rows = _series_to_rows(series, spec, unit=unit, note=note)
        for row in rows:
            row["quality_status"] = "watch"
        return rows

    def _fetch_snapshot(self) -> dict[str, float | str]:
        if self._snapshot is not None:
            return self._snapshot
        path = cache_path("gpw_benchmark::wig20::indicators")
        try:
            if path.exists():
                html = path.read_text()
            else:
                html = self._fetch_html()
                path.write_text(html)
        except (OSError, requests.RequestException, subprocess.SubprocessError):
            self._snapshot = {}
            return self._snapshot

        date_match = re.search(r"As of\s+(\d{1,2}\s+[A-Za-z]+\s+\d{4})", html)
        if not date_match:
            self._snapshot = {}
            return self._snapshot
        try:
            date = datetime.strptime(date_match.group(1), "%d %B %Y").strftime("%Y-%m-%d")
        except ValueError:
            self._snapshot = {}
            return self._snapshot

        snapshot: dict[str, float | str] = {"date": date}
        for label in ["closing", "index volatility", "P/E", "P/BV", "Dividend yield (%)"]:
            pattern = rf"<th>\s*{re.escape(label)}\s*(?:<sup>.*?</sup>)?\s*</th>\s*<td[^>]*>\s*([\d,.\s-]+)\s*</td>"
            match = re.search(pattern, html, flags=re.IGNORECASE | re.DOTALL)
            if not match:
                continue
            try:
                snapshot[label] = float(match.group(1).replace(",", "").strip())
            except ValueError:
                continue
        self._snapshot = snapshot
        return self._snapshot

    def _fetch_html(self) -> str:
        try:
            response = requests.post(
                GPW_BENCHMARK_WIG20_URL,
                headers={"User-Agent": "Mozilla/5.0"},
                timeout=30,
            )
            response.raise_for_status()
            if response.text.strip():
                return response.text
        except requests.RequestException:
            pass

        completed = subprocess.run(
            [
                "curl",
                "--max-time",
                "30",
                "-Ls",
                "-X",
                "POST",
                GPW_BENCHMARK_WIG20_URL,
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        return completed.stdout


class BVBIndexProfileFetcher(BaseFetcher):
    """Official Bucharest Stock Exchange BET snapshot adapters."""

    def __init__(self) -> None:
        self._snapshot: dict[str, float | str] | None = None
        self._performance: dict[str, float] | None = None

    def fetch(self, country: str, spec: IndicatorSpec) -> list[dict]:
        if country != "RO" or spec.indicator_id not in {"equity_index", "equity_yoy"}:
            return []
        snapshot = self._fetch_snapshot()
        if not snapshot:
            return []
        date = str(snapshot.get("date") or "")
        if not date:
            return []

        if spec.indicator_id == "equity_yoy":
            performance = self._fetch_performance()
            value = performance.get("1y") if performance else None
            if value is None:
                return []
            return self._snapshot_rows(
                country,
                spec,
                date,
                float(value),
                "% YoY",
                "BVB:BET:performance-1y",
                BVB_INDEX_PERFORMANCE_URL,
                "Official BVB index-performance table, `1 an (%)` column for BET.",
                "Official BVB BET 1-year performance snapshot; not recomputed from a full historical close feed.",
            )

        value = snapshot.get("value")
        if value is None:
            return []
        return self._snapshot_rows(
            country,
            spec,
            date,
            float(value),
            "Index",
            "BVB:BET:profile-current-value",
            BVB_BET_PROFILE_URL,
            "Official BVB mobile index profile snapshot for the BET price-return index.",
            "Official BVB BET profile snapshot; current-value observation, not a full historical close feed.",
        )

    def _snapshot_rows(
        self,
        country: str,
        spec: IndicatorSpec,
        date: str,
        value: float,
        unit: str,
        series_id: str,
        source_url: str,
        series_note: str,
        row_note: str,
    ) -> list[dict]:
        series = finalize_series(Series(
            key=spec.indicator_id,
            label=spec.label,
            country=country,
            source="Bucharest Stock Exchange",
            series_id=series_id,
            unit=unit,
            frequency="event",
            last_update=date,
            source_url=source_url,
            observations=[(date, value)],
            available=True,
            note=series_note,
        ))
        rows = _series_to_rows(
            series,
            spec,
            unit=unit,
            note=row_note,
        )
        for row in rows:
            row["quality_status"] = "watch"
        return rows

    def _fetch_snapshot(self) -> dict[str, float | str]:
        if self._snapshot is not None:
            return self._snapshot
        path = cache_path("bvb::bet::index_profile")
        try:
            if path.exists():
                html = path.read_text()
            else:
                response = requests.get(
                    BVB_BET_PROFILE_URL,
                    headers={"User-Agent": "Mozilla/5.0"},
                    timeout=30,
                )
                response.raise_for_status()
                html = response.text
                path.write_text(html)
        except (OSError, requests.RequestException):
            self._snapshot = {}
            return self._snapshot

        value_match = re.search(r'<div class="value pBot10">\s*<b>([\d.,]+)</b>', html)
        date_match = re.search(r'<div class="date small">(\d{2}\.\d{2}\.\d{4})\s+\d{2}:\d{2}:\d{2}</div>', html)
        if not value_match or not date_match:
            self._snapshot = {}
            return self._snapshot
        try:
            value = float(value_match.group(1).replace(".", "").replace(",", "."))
            date = datetime.strptime(date_match.group(1), "%d.%m.%Y").strftime("%Y-%m-%d")
        except ValueError:
            self._snapshot = {}
            return self._snapshot

        self._snapshot = {"date": date, "value": value}
        return self._snapshot

    def _fetch_performance(self) -> dict[str, float]:
        if self._performance is not None:
            return self._performance
        path = cache_path("bvb::bet::index_performance")
        try:
            if path.exists():
                html = path.read_text()
            else:
                response = requests.get(
                    BVB_INDEX_PERFORMANCE_URL,
                    headers={"User-Agent": "Mozilla/5.0"},
                    timeout=30,
                )
                response.raise_for_status()
                html = response.text
                path.write_text(html)
        except (OSError, requests.RequestException):
            self._performance = {}
            return self._performance

        row_match = re.search(
            r"<tr>\s*<td[^>]*>\s*BET\s*</td>(.*?)</tr>",
            html,
            flags=re.IGNORECASE | re.DOTALL,
        )
        if not row_match:
            self._performance = {}
            return self._performance
        cells = re.findall(r'<td[^>]*class="numericspvar"[^>]*>\s*([^<]+)\s*</td>', row_match.group(1), flags=re.IGNORECASE)
        if len(cells) < 5:
            self._performance = {}
            return self._performance
        try:
            one_year = float(cells[4].replace(".", "").replace(",", ".").strip())
        except ValueError:
            self._performance = {}
            return self._performance

        self._performance = {"1y": one_year}
        return self._performance


class CredentialedStooqFetcher(BaseFetcher):
    """Optional Stooq CSV adapter for market indexes that need user credentials.

    Stooq's unattended CSV endpoint currently requires an API key/captcha flow.
    The safest reusable path is to let the user paste the exact CSV URL from
    Stooq into an environment variable, or provide a key if the default URL
    template works for their account.
    """

    CONFIGS = {
        "PL": {
            "symbol": "wig20",
            "env_url": "STOOQ_WIG20_CSV_URL",
            "label": "WIG20",
        },
        "RO": {
            "symbol": "bet",
            "env_url": "STOOQ_BET_CSV_URL",
            "label": "BET",
        },
    }

    def __init__(self) -> None:
        self._daily_cache: dict[str, list[tuple[str, float]]] = {}

    def fetch(self, country: str, spec: IndicatorSpec) -> list[dict]:
        if spec.indicator_id not in {"equity_index", "equity_yoy", "equity_vol_30d"}:
            return []
        cfg = self.CONFIGS.get(country)
        if not cfg:
            return []
        observations = self._daily_observations(country, cfg)
        if not observations:
            return []
        if spec.indicator_id == "equity_vol_30d":
            return self._equity_vol_30d(country, cfg, spec, observations)

        monthly: dict[str, tuple[str, float]] = {}
        for date, value in observations:
            monthly[date[:7]] = (date, value)
        monthly_observations = sorted(monthly.values())
        series = finalize_series(Series(
            key=spec.indicator_id,
            label=spec.label,
            country=country,
            source="Stooq CSV user-configured feed",
            series_id=f"stooq:{cfg['symbol']}:daily-close",
            unit="Index",
            frequency="daily",
            last_update=monthly_observations[-1][0],
            source_url=f"https://stooq.com/q/?s={cfg['symbol']}",
            observations=monthly_observations,
            available=True,
            note=f"{cfg['label']} close sampled from the last available Stooq trading day in each month.",
        ))
        if spec.indicator_id == "equity_yoy":
            series = _derive_yoy_series(series, spec, periods=12)
        return _series_to_rows(
            series,
            spec,
            unit="% YoY" if spec.indicator_id == "equity_yoy" else "Index",
            note="Requires STOOQ_*_CSV_URL or STOOQ_API_KEY; verify index convention against the local exchange before trading.",
        )

    def _daily_observations(self, country: str, cfg: dict) -> list[tuple[str, float]]:
        if country in self._daily_cache:
            return self._daily_cache[country]
        url = _secret_env(str(cfg["env_url"]))
        api_key = _secret_env("STOOQ_API_KEY")
        if not url and api_key:
            url = f"https://stooq.com/q/d/l/?s={cfg['symbol']}&i=d&apikey={api_key}"
        if not url:
            self._daily_cache[country] = []
            return []
        cache_key = f"stooq::{country}::{cfg['symbol']}::{url.split('apikey=')[0]}"
        path = cache_path(cache_key)
        try:
            if path.exists():
                text = path.read_text()
            else:
                response = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=30)
                response.raise_for_status()
                text = response.text
                if "Get your apikey" in text or "captcha" in text.lower():
                    self._daily_cache[country] = []
                    return []
                path.write_text(text)
        except (OSError, requests.RequestException):
            self._daily_cache[country] = []
            return []
        observations = _parse_ohlc_csv(text)
        self._daily_cache[country] = observations
        return observations

    def _equity_vol_30d(
        self,
        country: str,
        cfg: dict,
        spec: IndicatorSpec,
        values: list[tuple[str, float]],
    ) -> list[dict]:
        if len(values) < 35:
            return []
        returns: list[tuple[str, float]] = []
        for idx in range(1, len(values)):
            date, value = values[idx]
            _, prior = values[idx - 1]
            if prior <= 0:
                continue
            returns.append((date, math.log(value / prior)))
        observations: list[tuple[str, float]] = []
        for idx in range(20, len(returns)):
            window = [ret for _, ret in returns[idx - 20: idx + 1]]
            mean = sum(window) / len(window)
            variance = sum((ret - mean) ** 2 for ret in window) / max(len(window) - 1, 1)
            observations.append((returns[idx][0], math.sqrt(variance) * math.sqrt(252) * 100.0))
        series = finalize_series(Series(
            key=spec.indicator_id,
            label=spec.label,
            country=country,
            source="Stooq CSV user-configured feed, derived",
            series_id=f"stooq:{cfg['symbol']}:21d-realised-volatility",
            unit="%",
            frequency="daily",
            last_update=observations[-1][0] if observations else "",
            source_url=f"https://stooq.com/q/?s={cfg['symbol']}",
            observations=observations,
            available=bool(observations),
            note=f"Annualised realised volatility computed from daily {cfg['label']} closes.",
        ))
        return _series_to_rows(
            series,
            spec,
            unit="%",
            note="Requires STOOQ_*_CSV_URL or STOOQ_API_KEY; derived from 21 trading days of daily closes.",
        )


class YahooMarketFetcher(BaseFetcher):
    """Vendor market-data adapter for local headline equity indexes."""

    def fetch(self, country: str, spec: IndicatorSpec) -> list[dict]:
        if spec.indicator_id not in {"equity_index", "equity_yoy", "equity_vol_30d"}:
            return []
        countries = load_countries()
        meta = countries.get(country)
        symbol = meta.get("equity_yahoo") if meta else ""
        if not symbol:
            return []

        if spec.indicator_id == "equity_vol_30d":
            return self._equity_vol_30d(symbol, country, spec)

        series = fetch_yahoo(symbol, spec.indicator_id, spec.label, country, range_="5y", interval="1mo")
        if spec.indicator_id == "equity_yoy":
            series = _derive_yoy_series(series, spec, periods=12)
        unit = "% YoY" if spec.indicator_id == "equity_yoy" else "Index"
        return _series_to_rows(
            series,
            spec,
            unit=unit,
            note="Yahoo Finance vendor feed; confirm index convention and live levels against the local exchange or terminal.",
        )

    def _equity_vol_30d(self, symbol: str, country: str, spec: IndicatorSpec) -> list[dict]:
        series = fetch_yahoo(symbol, spec.indicator_id, spec.label, country, range_="1y", interval="1d")
        if not series.available or len(series.observations) < 35:
            return []
        observations: list[tuple[str, float]] = []
        values = series.observations
        returns: list[tuple[str, float]] = []
        for idx in range(1, len(values)):
            date, value = values[idx]
            _, prior = values[idx - 1]
            if prior <= 0:
                continue
            returns.append((date, math.log(float(value) / float(prior))))
        for idx in range(20, len(returns)):
            window = [ret for _, ret in returns[idx - 20: idx + 1]]
            mean = sum(window) / len(window)
            variance = sum((ret - mean) ** 2 for ret in window) / max(len(window) - 1, 1)
            observations.append((returns[idx][0], math.sqrt(variance) * math.sqrt(252) * 100.0))
        vol_series = finalize_series(Series(
            key=spec.indicator_id,
            label=spec.label,
            country=country,
            source="Yahoo Finance derived",
            series_id=f"{symbol}:21d realised volatility",
            unit="%",
            frequency="daily",
            last_update=observations[-1][0] if observations else "",
            source_url=f"https://finance.yahoo.com/quote/{symbol}",
            observations=observations,
            available=bool(observations),
            note="Annualised realised volatility computed from daily Yahoo Finance close-to-close returns.",
        ))
        return _series_to_rows(
            vol_series,
            spec,
            unit="%",
            note="Derived 21-trading-day realised volatility; vendor daily close data should be verified for trading use.",
        )


class GIEAGSIFetcher(BaseFetcher):
    """Optional GIE AGSI+ gas-storage adapter.

    GIE requires API access, so this fetcher is intentionally inert until
    GIE_AGSI_API_KEY is present. Without credentials the transparent proxy
    remains, rather than silently substituting a fragile scraped value.
    """

    COUNTRIES = {"HU", "PL", "CZ", "RO"}

    def fetch(self, country: str, spec: IndicatorSpec) -> list[dict]:
        if spec.indicator_id != "gas_storage_level" or country not in self.COUNTRIES:
            return []
        api_key = _secret_env("GIE_AGSI_API_KEY")
        if not api_key:
            return []
        observations = self._fetch_country(country, api_key)
        if not observations:
            return []
        series = finalize_series(Series(
            key=spec.indicator_id,
            label=spec.label,
            country=country,
            source="GIE AGSI+",
            series_id=f"AGSI:{country}:gasFull",
            unit="%",
            frequency="daily",
            last_update=observations[-1][0],
            source_url="https://agsi.gie.eu/",
            observations=observations,
            available=True,
            note="GIE AGSI+ country-level storage filling percentage, daily end-of-gas-day data.",
        ))
        rows = _series_to_rows(
            series,
            spec,
            unit="%",
            note="Requires GIE_AGSI_API_KEY; country-level AGSI+ gasFull/fill percentage.",
        )
        for row in rows:
            row["quality_status"] = "watch"
        return rows

    def _fetch_country(self, country: str, api_key: str) -> list[tuple[str, float]]:
        base = _secret_env("GIE_AGSI_BASE_URL") or GIE_AGSI_BASE_URL
        candidates = [
            f"{base.rstrip('/')}/data/{country}/",
            f"{base.rstrip('/')}/data/{country}",
            f"{base.rstrip('/')}?country={country}",
        ]
        headers = {
            "User-Agent": "Mozilla/5.0",
            "x-key": api_key,
            "X-KEY": api_key,
            "Authorization": f"Bearer {api_key}",
        }
        for url in candidates:
            cache_key = f"gie_agsi::{country}::{url.split('?')[0]}"
            path = cache_path(cache_key)
            try:
                if path.exists():
                    payload = json.loads(path.read_text())
                else:
                    response = requests.get(url, headers=headers, timeout=30)
                    if response.status_code in {401, 403, 404}:
                        continue
                    response.raise_for_status()
                    payload = response.json()
                    path.write_text(json.dumps(payload, indent=2, sort_keys=True))
            except (OSError, requests.RequestException, json.JSONDecodeError):
                continue
            observations = self._parse_payload(payload)
            if observations:
                return observations
        return []

    def _parse_payload(self, payload: dict | list) -> list[tuple[str, float]]:
        raw_rows = payload
        if isinstance(payload, dict):
            raw_rows = payload.get("data") or payload.get("rows") or payload.get("result") or []
        if not isinstance(raw_rows, list):
            return []
        observations: list[tuple[str, float]] = []
        for item in raw_rows:
            if not isinstance(item, dict):
                continue
            date = str(item.get("gasDayStart") or item.get("gasDay") or item.get("date") or item.get("period") or "")[:10]
            value = (
                item.get("gasFull")
                or item.get("full")
                or item.get("fillingLevel")
                or item.get("fill")
                or item.get("percentageFull")
            )
            if not date or value in {None, ""}:
                continue
            try:
                numeric = float(str(value).replace("%", "").replace(",", "."))
            except ValueError:
                continue
            if math.isfinite(numeric):
                observations.append((date, numeric))
        return sorted({date: value for date, value in observations}.items())


class ProxyFetcher(BaseFetcher):
    def fetch(self, country: str, spec: IndicatorSpec) -> list[dict]:
        return proxy_rows(country, spec)


class WorldBankESGFetcher(BaseFetcher):
    CONFIGS = {
        "wgi_government_effectiveness": "GE.EST",
        "wgi_rule_of_law": "RL.EST",
        "wgi_control_of_corruption": "CC.EST",
    }

    def fetch(self, country: str, spec: IndicatorSpec) -> list[dict]:
        code = self.CONFIGS.get(spec.indicator_id)
        if not code:
            return []
        countries = load_countries()
        meta = countries.get(country)
        if not meta:
            return []
        try:
            observations = _load_world_bank_esg_data().get((meta["iso3"], code), [])
        except (OSError, requests.RequestException, zipfile.BadZipFile, ET.ParseError):
            return []
        observations = [(date, value) for date, value in observations if date >= "2010-01-01"]
        if not observations:
            return []
        series = finalize_series(Series(
            key=spec.indicator_id,
            label=spec.label,
            country=country,
            source="World Bank Sovereign ESG Data Portal / WGI",
            series_id=code,
            unit="Estimate score",
            frequency="annual",
            last_update=observations[-1][0][:4],
            source_url=WORLD_BANK_ESG_URL,
            observations=observations,
            available=True,
            note="Downloaded from the official Sovereign ESG workbook; WGI estimate score, not percentile rank.",
        ))
        return _series_to_rows(
            series,
            spec,
            unit="Estimate score",
            note=f"World Bank Sovereign ESG workbook indicator {code}.",
        )


class EUFundsAbsorptionFetcher(BaseFetcher):
    """European Commission Cohesion Open Data payment-absorption adapter."""

    FUNDS = ("CF", "EMFAF", "ERDF", "ESF+", "JTF")

    def fetch(self, country: str, spec: IndicatorSpec) -> list[dict]:
        if spec.indicator_id != "eu_funds_absorption":
            return []
        countries = load_countries()
        meta = countries.get(country)
        if not meta:
            return []
        try:
            observations = self._fetch_country_absorption(meta["iso2"])
        except (OSError, requests.RequestException, json.JSONDecodeError, KeyError, TypeError, ValueError):
            return []
        if not observations:
            return []

        series = finalize_series(Series(
            key=spec.indicator_id,
            label=spec.label,
            country=country,
            source="European Commission Cohesion Open Data",
            series_id="pbbz-hmfu total_net_payments / actual_plan_eu_amt_latest_adop",
            unit="% allocation",
            frequency="annual",
            last_update=observations[-1][0],
            source_url="https://cohesiondata.ec.europa.eu/d/pbbz-hmfu",
            observations=observations,
            available=True,
            note="Cumulative 2021-2027 EU payments as a share of latest adopted EU planned amount.",
        ))
        return _series_to_rows(
            series,
            spec,
            unit="% allocation",
            note=(
                "Official payment ratio across CF, EMFAF, ERDF, ESF+, and JTF; "
                "payment absorption is narrower than contracting or claims submitted by national authorities."
            ),
        )

    def _fetch_country_absorption(self, iso2: str) -> list[tuple[str, float]]:
        query = f"cohesion_absorption::{iso2}::2021_2027"
        path = cache_path(query)
        if path.exists():
            payload = json.loads(path.read_text())
        else:
            fund_filter = ",".join(f"'{fund}'" for fund in self.FUNDS)
            response = requests.get(
                COHESION_EU_PAYMENTS_URL,
                params={
                    "$select": (
                        "year, sum(actual_plan_eu_amt_latest_adop) as planned, "
                        "sum(total_net_payments) as paid"
                    ),
                    "$where": f"ms='{iso2}' AND fund in ({fund_filter})",
                    "$group": "year",
                    "$order": "year",
                    "$limit": "20",
                },
                timeout=30,
            )
            response.raise_for_status()
            payload = response.json()
            path.write_text(json.dumps(payload, indent=2, sort_keys=True))

        observations: list[tuple[str, float]] = []
        for item in payload:
            year = int(item["year"])
            planned = float(item["planned"])
            paid = float(item["paid"])
            if planned > 0:
                observations.append((f"{year}-12-31", paid / planned * 100.0))
        observations.sort()
        return observations


class FREDInternationalFetcher(BaseFetcher):
    """Selected FRED international series where IDs have been explicitly verified."""

    def fetch(self, country: str, spec: IndicatorSpec) -> list[dict]:
        if spec.indicator_id != "fx_reserves":
            return []
        series_id = FRED_FX_RESERVE_SERIES.get(country)
        if not series_id:
            return []
        try:
            raw_observations = _fetch_fred_observations(series_id, start="2010-01-01")
        except (OSError, requests.RequestException, json.JSONDecodeError, csv.Error):
            return []
        observations = [(date, value / 1_000.0) for date, value in raw_observations if date >= "2010-01-01"]
        if not observations:
            return []
        series = finalize_series(Series(
            key=spec.indicator_id,
            label=spec.label,
            country=country,
            source="FRED / IMF International Financial Statistics",
            series_id=series_id,
            unit="USD bn",
            frequency="monthly",
            last_update=observations[-1][0],
            source_url=f"https://fred.stlouisfed.org/series/{series_id}",
            observations=observations,
            available=True,
            note="FRED monthly total reserves excluding gold, sourced from IMF International Financial Statistics; converted from USD millions to USD billions.",
        ))
        rows = _series_to_rows(
            series,
            spec,
            unit="USD bn",
            note="Monthly FRED/IMF IFS series is used where the country-specific ID has been explicitly verified.",
        )
        for row in rows:
            row["quality_status"] = "watch"
        return rows


class WorldBankFetcher(BaseFetcher):
    CONFIGS = {
        "gdp_per_capita": ("NY.GDP.PCAP.PP.KD", 1.0, "constant intl $"),
        "gross_fixed_capital": ("NE.GDI.FTOT.ZS", 1.0, "% GDP"),
        "fdi_inflows": ("BX.KLT.DINV.WD.GD.ZS", 1.0, "% GDP"),
        "participation_rate": ("SL.TLF.CACT.ZS", 1.0, "%"),
        "employment_growth": ("SL.EMP.TOTL.SP.ZS", 1.0, "% population"),
        "population_total": ("SP.POP.TOTL", 1 / 1_000_000, "mn people"),
        "working_age_population": ("SP.POP.1564.TO", 1 / 1_000_000, "mn people"),
        "old_age_dependency": ("SP.POP.DPND.OL", 1.0, "%"),
        "fx_reserves": ("FI.RES.TOTL.CD", 1 / 1_000_000_000, "USD bn"),
        "current_account_pct_gdp": ("BN.CAB.XOKA.GD.ZS", 1.0, "% GDP"),
        "income_balance": ("BN.GSR.FCTY.CD", 1 / 1_000_000_000, "USD bn"),
        "gross_ext_debt": ("DT.DOD.DECT.GN.ZS", 1.0, "% GNI"),
        "reer": ("REER", 1.0, "Index"),
        "neer": ("NEER", 1.0, "Index"),
        "m3_yoy": ("FM.LBL.BMNY.ZG", 1.0, "% YoY"),
        "private_credit_yoy": ("FM.AST.PRVT.ZG.M3", 1.0, "% YoY"),
        "gov_revenue_pct_gdp": ("GC.REV.XGRT.GD.ZS", 1.0, "% GDP"),
        "gov_expenditure_pct_gdp": ("GC.XPN.TOTL.GD.ZS", 1.0, "% GDP"),
        "bank_car": ("FB.BNK.CAPA.ZS", 1.0, "%"),
        "bank_npl_ratio": ("FB.AST.NPER.ZS", 1.0, "%"),
        "bank_roe": ("GFDD.EI.06", 1.0, "%"),
        "bank_ld_ratio": ("GFDD.SI.04", 1.0, "%"),
        "bank_nim": ("GFDD.EI.01", 1.0, "%"),
        "household_debt_pct_gdp": ("FS.AST.PRVT.GD.ZS", 0.45, "% GDP"),
        "corp_debt_pct_gdp": ("FS.AST.PRVT.GD.ZS", 0.55, "% GDP"),
        "foreign_bank_share": ("GFDD.OI.16", 1.0, "%"),
        "net_migration": ("SM.POP.NETM", 1.0, "people"),
        "fertility_rate": ("SP.DYN.TFRT.IN", 1.0, "children per woman"),
    }

    def fetch(self, country: str, spec: IndicatorSpec) -> list[dict]:
        if spec.indicator_id == "services_balance":
            return self._services_balance(country, spec)
        if spec.indicator_id == "trade_balance":
            return self._trade_balance(country, spec)
        cfg = self.CONFIGS.get(spec.indicator_id)
        if not cfg:
            return []
        countries = load_countries()
        meta = countries.get(country)
        if not meta:
            return []
        code, scale, unit = cfg
        series = fetch_wb(meta["iso2"], code, spec.indicator_id, spec.label, country, start=2010, end=2026)
        return _series_to_rows(series, spec, scale=scale, unit=unit, note=f"World Bank indicator {code}.")

    def _services_balance(self, country: str, spec: IndicatorSpec) -> list[dict]:
        countries = load_countries()
        meta = countries.get(country)
        if not meta:
            return []
        exports = fetch_wb(meta["iso2"], "BX.GSR.NFSV.CD", "services_exports", "Services exports", country, start=2010, end=2026)
        imports = fetch_wb(meta["iso2"], "BM.GSR.NFSV.CD", "services_imports", "Services imports", country, start=2010, end=2026)
        if not exports.available or not imports.available:
            return []
        imports_by_date = {date: value for date, value in imports.observations}
        observations: list[tuple[str, float]] = []
        for date, value in exports.observations:
            import_value = imports_by_date.get(date)
            if import_value is None:
                continue
            observations.append((date, (float(value) - float(import_value)) / 1_000_000_000))
        series = finalize_series(Series(
            key=spec.indicator_id,
            label=spec.label,
            country=country,
            source="World Bank WDI",
            series_id="BX.GSR.NFSV.CD minus BM.GSR.NFSV.CD",
            unit="USD bn",
            frequency="annual",
            last_update=observations[-1][0] if observations else "",
            source_url="https://data.worldbank.org/",
            observations=observations,
            available=bool(observations),
            note="Annual services exports minus services imports from World Bank WDI.",
        ))
        return _series_to_rows(series, spec, unit="USD bn", note="Derived from World Bank service export/import indicators.")

    def _trade_balance(self, country: str, spec: IndicatorSpec) -> list[dict]:
        countries = load_countries()
        meta = countries.get(country)
        if not meta:
            return []
        exports = fetch_wb(meta["iso2"], "NE.EXP.GNFS.CD", "goods_services_exports", "Goods and services exports", country, start=2010, end=2026)
        imports = fetch_wb(meta["iso2"], "NE.IMP.GNFS.CD", "goods_services_imports", "Goods and services imports", country, start=2010, end=2026)
        if not exports.available or not imports.available:
            return []
        imports_by_date = {date: value for date, value in imports.observations}
        observations: list[tuple[str, float]] = []
        for date, value in exports.observations:
            import_value = imports_by_date.get(date)
            if import_value is None:
                continue
            observations.append((date, (float(value) - float(import_value)) / 1_000_000_000))
        series = finalize_series(Series(
            key=spec.indicator_id,
            label=spec.label,
            country=country,
            source="World Bank WDI",
            series_id="NE.EXP.GNFS.CD minus NE.IMP.GNFS.CD",
            unit="USD bn",
            frequency="annual",
            last_update=observations[-1][0] if observations else "",
            source_url="https://data.worldbank.org/",
            observations=observations,
            available=bool(observations),
            note="Annual exports of goods and services minus imports of goods and services from World Bank WDI.",
        ))
        return _series_to_rows(series, spec, unit="USD bn", note="Derived from World Bank national-accounts export/import indicators.")


class DataPipeline:
    """Fetch all canonical indicators into one normalized DataFrame."""

    def __init__(self, fetchers: Iterable[BaseFetcher] | None = None) -> None:
        self.fetchers = list(fetchers or [
            ECBFetcher(),
            PolicyRateFetcher(),
            EurostatFetcher(),
            DerivedMacroFetcher(),
            IMFDataMapperFetcher(),
            WorldBankESGFetcher(),
            EUFundsAbsorptionFetcher(),
            ECBExternalDebtFetcher(),
            ECBPortfolioFlowsFetcher(),
            NationalCBFetcher(),
            FREDInternationalFetcher(),
            IMFFinancialSoundnessFetcher(),
            WorldBankFetcher(),
            PragueExchangeFetcher(),
            GPWBenchmarkFetcher(),
            BVBIndexProfileFetcher(),
            CredentialedStooqFetcher(),
            YahooMarketFetcher(),
            BISFetcher(),
            WorldBankFallbackFetcher(),
            ECBMIRFetcher(),
            GIEAGSIFetcher(),
            ManualIndicatorFetcher(),
            CZSOFetcher(),
            KSHFetcher(),
            GUSDBWFetcher(),
            INSSETempoFetcher(),
            ProxyFetcher(),
        ])

    def fetch_indicator(self, country: str, spec: IndicatorSpec) -> list[dict]:
        for fetcher in self.fetchers:
            rows = fetcher.fetch(country, spec)
            if rows:
                return rows
        return proxy_rows(country, spec)

    def fetch_country(self, country: str, specs: Iterable[IndicatorSpec] = INDICATOR_MANIFEST_48) -> list[dict]:
        rows: list[dict] = []
        for spec in specs:
            if is_dropped_proxy_indicator(country, spec.indicator_id):
                continue
            rows.extend(self.fetch_indicator(country, spec))
        clean_rows: list[dict] = []
        for row in rows:
            try:
                datetime.fromisoformat(str(row["date"])[:10])
                row["value"] = float(row["value"])
            except (KeyError, TypeError, ValueError):
                continue
            clean_rows.append({column: row.get(column) for column in CANONICAL_COLUMNS})
        return sorted(clean_rows, key=lambda r: (r["section_id"], r["indicator_id"], str(r["date"])))

    def validate_coverage(self, frame: list[dict], expected: int | None = None) -> dict:
        country = str(frame[0].get("country", "")).upper() if frame else ""
        expected_specs = [
            spec for spec in INDICATOR_MANIFEST_48
            if not is_dropped_proxy_indicator(country, spec.indicator_id)
        ]
        expected = expected or len(expected_specs)
        indicators = sorted({row["indicator_id"] for row in frame}) if frame else []
        unique_rows = {}
        for row in frame:
            unique_rows.setdefault(row["indicator_id"], row)
        return {
            "indicator_count": len(indicators),
            "expected": expected,
            "missing": sorted({s.indicator_id for s in expected_specs} - set(indicators)),
            "proxy_count": sum(1 for row in unique_rows.values() if row.get("is_proxy")),
            "generated_at": datetime.utcnow().strftime("%Y-%m-%d"),
        }


def fetch_canonical_macro_frame(country: str) -> list[dict]:
    return DataPipeline().fetch_country(country)
