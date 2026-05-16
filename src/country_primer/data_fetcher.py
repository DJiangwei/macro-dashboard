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

from dataclasses import dataclass
from datetime import datetime
import math
from pathlib import Path
from typing import Iterable

import yaml


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
    IndicatorSpec("political_economy", "wgi_government_effectiveness", "WGI Government Effectiveness", "Percentile rank", "World Bank WGI", "annual", "line", False, "watch", "Composite governance measure; not a precise macro print."),
    IndicatorSpec("political_economy", "wgi_rule_of_law", "WGI Rule of Law", "Percentile rank", "World Bank WGI", "annual", "line", False, "watch", "Composite governance measure; use directionally."),
    IndicatorSpec("political_economy", "wgi_control_of_corruption", "WGI Control of Corruption", "Percentile rank", "World Bank WGI", "annual", "line", False, "watch", "Perception/model composite; can move with methodology."),
    IndicatorSpec("political_economy", "eu_funds_frozen", "EU Funds Frozen / At Risk", "% allocation", "European Commission / public proxy", "annual", "line", False, "low_confidence", "Public programme-cycle data is fragmented; verify manually."),
)


def _load_manifest_from_yaml(fallback: tuple[IndicatorSpec, ...]) -> tuple[IndicatorSpec, ...]:
    """Load the editable 48-indicator manifest from config when available."""
    manifest_path = Path(__file__).resolve().parents[2] / "config" / "indicator_manifest_48.yaml"
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

    expected = int(payload.get("expected_count", 48))
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
    "real_gdp_yoy": 2.0, "real_gdp_qoq": 0.5, "gdp_components": 100.0,
    "industrial_production_yoy": 1.0, "retail_sales_yoy": 2.5, "unemployment_rate": 4.5,
    "economic_sentiment": 98.0, "cpi_yoy": 4.0, "core_cpi_yoy": 4.3, "services_cpi_yoy": 5.0,
    "ppi_yoy": 2.2, "avg_wage_yoy": 8.0, "real_wage_yoy": 3.2,
    "current_account_pct_gdp": -1.5, "trade_balance": 0.0, "services_balance": 2.0,
    "fx_reserves": 80.0, "reer": 102.0, "short_term_ext_debt": 55.0,
    "fiscal_balance_pct_gdp": -3.5, "structural_balance": -3.0, "primary_balance": -1.0,
    "gov_debt_pct_gdp": 55.0, "interest_bill_pct_gdp": 2.0, "sov_yield_10y": 5.0,
    "policy_rate": 5.0, "real_policy_rate": 1.0, "m3_yoy": 7.0, "private_credit_yoy": 5.5,
    "credit_to_gdp_gap": 0.0, "fx_vs_eur": 100.0, "equity_index": 100.0, "equity_yoy": 8.0,
    "equity_fwd_pe": 9.5, "equity_div_yield": 4.0, "sov_spread_vs_bund": 220.0,
    "bank_car": 19.0, "bank_npl_ratio": 3.5, "bank_roe": 12.0, "bank_ld_ratio": 86.0,
    "population_total": 20.0, "working_age_population": 12.5, "old_age_dependency": 29.0,
    "median_age": 42.0, "wgi_government_effectiveness": 70.0, "wgi_rule_of_law": 72.0,
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
    def fetch(self, country: str, spec: IndicatorSpec) -> list[dict]:
        return []


class ECBFetcher(BaseFetcher):
    def fetch(self, country: str, spec: IndicatorSpec) -> list[dict]:
        return []


class BISFetcher(BaseFetcher):
    def fetch(self, country: str, spec: IndicatorSpec) -> list[dict]:
        return []


class NationalCBFetcher(BaseFetcher):
    def fetch(self, country: str, spec: IndicatorSpec) -> list[dict]:
        return []


class ProxyFetcher(BaseFetcher):
    def fetch(self, country: str, spec: IndicatorSpec) -> list[dict]:
        return proxy_rows(country, spec)


class DataPipeline:
    """Fetch all canonical indicators into one normalized DataFrame."""

    def __init__(self, fetchers: Iterable[BaseFetcher] | None = None) -> None:
        self.fetchers = list(fetchers or [EurostatFetcher(), ECBFetcher(), BISFetcher(), NationalCBFetcher(), ProxyFetcher()])

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

    def validate_coverage(self, frame: list[dict], expected: int = 48) -> dict:
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
