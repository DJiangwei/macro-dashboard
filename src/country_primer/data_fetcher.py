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

import csv
from dataclasses import dataclass
from datetime import datetime
import io
import json
import math
from pathlib import Path
from typing import Iterable
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
    "annual": 900,
}


FREQUENCY_GAP_DAYS = {
    "daily": 10,
    "monthly": 70,
    "quarterly": 130,
    "annual": 500,
}


WORLD_BANK_ESG_URL = "https://esgdata.worldbank.org/dist/content/data/download/esgdata_download-2026-01-09.xlsx"
IMF_DATAMAPPER_URL = "https://www.imf.org/external/datamapper/api/v1/{indicator}/{iso3}"
BIS_CREDIT_GAP_URL = "https://data.bis.org/static/bulk/WS_CREDIT_GAP_csv_flat.zip"
_ESG_DATA_CACHE: dict[tuple[str, str], list[tuple[str, float]]] | None = None
_BIS_CREDIT_GAP_CACHE: dict[str, list[tuple[str, float]]] | None = None
_XLSX_NS = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
CONFIG_DIR = Path(__file__).resolve().parents[2] / "config"


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
    IndicatorSpec("markets_valuation", "equity_fwd_pe", "Equity Forward P/E", "x", "Broker/vendor estimates", "monthly", "line", False, "low_confidence", "Forward estimates usually require vendor data."),
    IndicatorSpec("markets_valuation", "equity_div_yield", "Equity Dividend Yield", "%", "Broker/vendor estimates", "monthly", "line", False, "low_confidence", "Trailing/forward methodology must be checked."),
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

    if len(parsed) < 5:
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
            "source": spec.source,
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
            "dataset": "prc_hicp_manr",
            "freq": "M",
            "since": "2018",
            "params": {"coicop": "CP00"},
            "unit": "% YoY",
        },
        "core_cpi_yoy": {
            "dataset": "prc_hicp_manr",
            "freq": "M",
            "since": "2018",
            "params": {"coicop": "TOT_X_NRG_FOOD"},
            "unit": "% YoY",
        },
        "services_cpi_yoy": {
            "dataset": "prc_hicp_manr",
            "freq": "M",
            "since": "2018",
            "params": {"coicop": "SERV"},
            "unit": "% YoY",
        },
        "goods_cpi_yoy": {
            "dataset": "prc_hicp_manr",
            "freq": "M",
            "since": "2018",
            "params": {"coicop": "IGD_NNRG"},
            "unit": "% YoY",
        },
        "energy_cpi_yoy": {
            "dataset": "prc_hicp_manr",
            "freq": "M",
            "since": "2018",
            "params": {"coicop": "NRG"},
            "unit": "% YoY",
        },
        "food_cpi_yoy": {
            "dataset": "prc_hicp_manr",
            "freq": "M",
            "since": "2018",
            "params": {"coicop": "FOOD"},
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
            "params": {"indic": "BS-CU-Q", "s_adj": "NSA"},
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
            "params": {"nace_r2": "B-S", "sizeclas": "TOTAL", "indic_jv": "JOBVAC_RATE", "s_adj": "NSA"},
            "unit": "%",
        },
        "construction_production": {
            "dataset": "sts_copr_m",
            "freq": "M",
            "since": "2018",
            "params": {"nace_r2": "F", "indic_bt": "PRD", "s_adj": "SCA", "unit": "I21"},
            "unit": "% YoY",
            "derive_yoy": True,
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
            "params": {"na_item": "ULC_HW", "unit": "PCH_SM", "s_adj": "SCA"},
            "unit": "% YoY",
        },
        "minimum_wage": {
            "dataset": "earn_mw_cur",
            "freq": "A",
            "since": "2010",
            "params": {"currency": "EUR", "indic_se": "MW_CUR"},
            "unit": "EUR/month",
        },
        "policy_rate": {
            "dataset": "irt_st_m",
            "freq": "M",
            "since": "2018",
            "params": {},
            "unit": "%",
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
            meta["iso2"],
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
        return _series_to_rows(series, spec, unit=cfg["unit"])


class DerivedMacroFetcher(BaseFetcher):
    def fetch(self, country: str, spec: IndicatorSpec) -> list[dict]:
        if spec.indicator_id == "gdp_components":
            return self._gdp_demand_composite(country, spec)
        if spec.indicator_id == "real_wage_yoy":
            return self._real_wage_yoy(country, spec)
        if spec.indicator_id == "real_policy_rate":
            return self._real_policy_rate(country, spec)
        if spec.indicator_id == "sov_spread_vs_bund":
            return self._sov_spread_vs_bund(country, spec)
        if spec.indicator_id == "sov_yield_2y":
            return self._short_rate_market_proxy(country, spec, "2Y sovereign yield proxy")
        if spec.indicator_id == "yield_curve_slope":
            return self._yield_curve_slope(country, spec)
        if spec.indicator_id == "carry_trade_return":
            return self._carry_trade_return(country, spec)
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
            "prc_hicp_manr",
            meta["iso2"],
            "cpi_yoy",
            "Headline CPI/HICP, YoY",
            country,
            freq="M",
            since="2018",
            extra_params={"coicop": "CP00"},
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
            series_id="lc_lci_r2_q:D11 minus prc_hicp_manr:CP00",
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
        nominal_rate = fetch_eurostat(
            "irt_st_m",
            meta["iso2"],
            "policy_rate",
            "Short-Term Interest Rate",
            country,
            freq="M",
            since="2018",
            extra_params={},
            unit_label="%",
        )
        cpi = fetch_eurostat(
            "prc_hicp_manr",
            meta["iso2"],
            "cpi_yoy",
            "Headline CPI/HICP, YoY",
            country,
            freq="M",
            since="2018",
            extra_params={"coicop": "CP00"},
            unit_label="% YoY",
        )
        if not nominal_rate.available or not cpi.available:
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
            source="Derived from Eurostat short-term interest rates and HICP",
            series_id="irt_st_m minus prc_hicp_manr:CP00",
            unit="%",
            frequency="monthly",
            last_update=observations[-1][0] if observations else "",
            source_url="https://ec.europa.eu/eurostat/databrowser/",
            observations=observations,
            available=bool(observations),
            note="Ex-post real policy-stance proxy: Eurostat short-term interest rate minus headline HICP inflation.",
        ))
        return _series_to_rows(series, spec, unit="%", note="Derived from Eurostat short-term interest-rate and HICP adapters.")

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
            extra_params={},
            unit_label="%",
        )
        eur_rate = fetch_eurostat(
            "irt_st_m",
            "DE",
            "eur_short_rate",
            "EUR Short-Term Rate Proxy",
            country,
            freq="M",
            since="2018",
            extra_params={},
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
            series_id=f"irt_st_m:{meta['iso2']}-DE",
            unit="% annualised",
            frequency="monthly",
            last_update=observations[-1][0] if observations else "",
            source_url="https://ec.europa.eu/eurostat/databrowser/view/irt_st_m/default/table?lang=en",
            observations=observations,
            available=bool(observations),
            note="Carry-only proxy: local short-term rate less German/EUR short-term rate, excluding spot FX moves and roll-down.",
        ))
        rows = _series_to_rows(series, spec, unit="% annualised", note="Carry-only proxy; not a realised total-return series.")
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
        if spec.indicator_id != "credit_to_gdp_gap":
            return []
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


def _load_bis_credit_gap_data() -> dict[str, list[tuple[str, float]]]:
    """Load BIS credit-to-GDP gaps from the public bulk-download ZIP."""
    global _BIS_CREDIT_GAP_CACHE
    if _BIS_CREDIT_GAP_CACHE is not None:
        return _BIS_CREDIT_GAP_CACHE

    zip_path = CACHE_DIR / "bis_ws_credit_gap_csv_flat.zip"
    if zip_path.exists():
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


class NationalCBFetcher(BaseFetcher):
    def fetch(self, country: str, spec: IndicatorSpec) -> list[dict]:
        return []


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
            note="Maintained in config/manual_indicators.yaml; revise manually when policy status changes.",
        )
        for row in rows:
            row["quality_status"] = str(raw_indicator.get("quality_status") or "low_confidence")
            row["is_proxy"] = False
            row["quality_note"] = (
                f"{row.get('quality_note')} Manual input, not a statistical API series; "
                "treat as a policy-risk marker rather than measured macro data."
            ).strip()
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
        if path.exists():
            return json.loads(path.read_text())

        url = IMF_DATAMAPPER_URL.format(indicator=indicator, iso3=iso3)
        params = {"periods": ",".join(str(year) for year in range(2010, 2027))}
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        payload = response.json()
        path.write_text(json.dumps(payload, indent=2, sort_keys=True))
        return payload


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
            EurostatFetcher(),
            DerivedMacroFetcher(),
            IMFDataMapperFetcher(),
            WorldBankESGFetcher(),
            WorldBankFetcher(),
            YahooMarketFetcher(),
            BISFetcher(),
            WorldBankFallbackFetcher(),
            ManualIndicatorFetcher(),
            NationalCBFetcher(),
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
        expected = expected or len(INDICATOR_MANIFEST_48)
        indicators = sorted({row["indicator_id"] for row in frame}) if frame else []
        unique_rows = {}
        for row in frame:
            unique_rows.setdefault(row["indicator_id"], row)
        return {
            "indicator_count": len(indicators),
            "expected": expected,
            "missing": sorted({s.indicator_id for s in INDICATOR_MANIFEST_48} - set(indicators)),
            "proxy_count": sum(1 for row in unique_rows.values() if row.get("is_proxy")),
            "generated_at": datetime.utcnow().strftime("%Y-%m-%d"),
        }


def fetch_canonical_macro_frame(country: str) -> list[dict]:
    return DataPipeline().fetch_country(country)
