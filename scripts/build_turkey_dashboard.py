"""Build the Turkey macro dashboard from the Turkey indicator config.

Turkey is built on official harmonized TurkStat series transmitted directly to
Eurostat (geo=TR), TCMB daily foreign exchange rates XML, IMF SDMX and
DataMapper datasets, BIS and OECD mirrors via FRED, and the Bruegel 178-country
REER database. Indicators requiring an EVDS API key (such as weekly loan flow
rates) are recorded in ``data_gaps`` unless configured.
"""
from __future__ import annotations

import collections
import json
import os
import re
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import requests
import yaml

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from dashboard_summary_utils import (
    apply_quality_assessments,
    build_summary_metadata,
    canonical_frame_metadata,
    load_canonical_data_first_frame,
    retain_last_known_good_series,
    track_revisions_and_vintages,
    write_canonical_data_first_frame,
)
from country_primer.page_renderer import build_country_page, _latest
from country_primer.data_first_pipeline import fetch_all
from country_primer.adapters import (
    USER_AGENT,
    _apply_us_transform as _apply_transform,
    apply_scale,
    fetch_bruegel_reer,
    fetch_dbnomics,
    fetch_eurostat_jsonstat,
    fetch_fred_us,
    fetch_imf_datamapper,
    fetch_imf_sdmx,
    fetch_tcmb_evds,
    fetch_tcmb_xml,
)
from country_primer.cross_checks import evaluate_cross_checks
from country_primer.source_health import SOURCE_HEALTH


CONFIG_PATH = ROOT / "config" / "turkey_indicators.yaml"
OUTPUT = ROOT / "output"
OUT_HTML = OUTPUT / "turkey.html"
SUMMARY_JSON = OUTPUT / "turkey_dashboard_summary.json"
CANONICAL_JSON = OUTPUT / "turkey_canonical_frame.json"
COUNTRY_CODE = "TR"
SUMMARY_KEY_IDS = [
    "real_gdp_growth",
    "real_gdp_yoy",
    "household_consumption",
    "gross_fixed_capital_formation",
    "industrial_production_growth",
    "manufacturing_production_growth",
    "retail_sales_growth",
    "construction_production_growth",
    "economic_sentiment_indicator",
    "capacity_utilization",
    "composite_leading_indicator",
    "unemployment_rate",
    "youth_unemployment_rate",
    "cpi_inflation",
    "cpi_inflation_mom",
    "food_cpi_inflation",
    "core_hicp_inflation",
    "services_hicp_inflation",
    "food_hicp_inflation",
    "energy_hicp_inflation",
    "ppi_inflation",
    "house_price_growth",
    "try_usd",
    "reer",
    "goods_exports",
    "goods_imports",
    "current_account_usd",
    "goods_trade_balance",
    "services_balance",
    "fdi_net_usd",
    "current_account_gdp",
    "fx_reserves",
    "government_debt_gdp",
    "fiscal_balance_gdp",
    "primary_balance_gdp",
    "policy_rate",
    "overnight_interbank_rate",
    "commercial_loan_rate",
    "mortgage_loan_rate",
    "consumer_loan_rate",
    "private_credit_gdp",
    "bank_capital_ratio",
    "bank_npl_ratio",
]


def _load_config() -> dict[str, Any]:
    return yaml.safe_load(CONFIG_PATH.read_text()) or {}


def build(data_mode: str | None = None) -> Path:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    if data_mode is None:
        data_mode = os.environ.get("COUNTRY_PRIMER_DATA_MODE") or ("snapshot" if "--snapshot" in sys.argv else "refresh")
    data_mode = data_mode.strip().lower()
    config = _load_config()

    registry = {
        "eurostat": lambda spec, cache: _apply_transform(apply_scale(fetch_eurostat_jsonstat(requests.Session(), spec))),
        "tcmb_xml": lambda spec, cache: _apply_transform(fetch_tcmb_xml(spec)),
        "tcmb_evds": lambda spec, cache: _apply_transform(apply_scale(fetch_tcmb_evds(spec))),
        "fred": lambda spec, cache: _apply_transform(apply_scale(fetch_fred_us(requests.Session(), spec))),
        "imf_sdmx": lambda spec, cache: _apply_transform(apply_scale(fetch_imf_sdmx(requests.Session(), spec))),
        "imf_datamapper": lambda spec, cache: _apply_transform(fetch_imf_datamapper(requests.Session(), spec)),
        "bruegel_reer": lambda spec, cache: _apply_transform(fetch_bruegel_reer(spec)),
        "dbnomics": lambda spec, cache: _apply_transform(fetch_dbnomics(spec)),
    }

    if data_mode == "snapshot":
        series_list = load_canonical_data_first_frame(CANONICAL_JSON, config)
    else:
        SOURCE_HEALTH.reset()
        series_list, _ = fetch_all(config, registry, max_workers=6)
        series_list = retain_last_known_good_series(series_list, CANONICAL_JSON, config)
        series_list = track_revisions_and_vintages(series_list, CANONICAL_JSON, config)

    charted = [item for item in series_list if item.get("observations")]
    fx_item = next((item for item in charted if item["id"] == "try_usd"), None)
    fx_latest = _latest(fx_item) if fx_item else None
    fx_latest_str = f"{float(fx_latest['value']):.4f} ({fx_latest['date']})" if fx_latest else "n/a"

    summary = build_country_page(
        country_code="TR",
        config=config,
        series_list=series_list,
        out_html=OUT_HTML,
        summary_json=SUMMARY_JSON,
        canonical_json=CANONICAL_JSON,
        data_mode=data_mode,
        summary_key_ids=SUMMARY_KEY_IDS,
        latest_value_key="usd_try_latest",
        latest_value_display=fx_latest_str,
    )

    if not os.environ.get("COUNTRY_PRIMER_SKIP_ARCHIVE"):
        from build_dashboard_archive import build_archive
        build_archive()
    return OUT_HTML


if __name__ == "__main__":
    path = build()
    print(f"Wrote {path} ({path.stat().st_size:,} bytes)")
