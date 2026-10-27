"""Build the Taiwan macro dashboard from the Taiwan indicator config.

Taiwan is built on official endpoints: Central Bank of the Republic of China (CBC)
DataAPI for monetary, credit, and balance of payments statistics, Directorate-General
of Budget, Accounting and Statistics (DGBAS) for chained GDP accounts and CPI price
indices, Federal Reserve Board (H.10) for daily USD/TWD spot rates, BIS real effective
exchange rates via FRED, Bruegel 178-country REER database, and IMF WEO DataMapper.
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
    fetch_fred_us,
    fetch_imf_datamapper,
    fetch_tw_cbc,
    fetch_tw_dgbas,
)
from country_primer.cross_checks import evaluate_cross_checks
from country_primer.source_health import SOURCE_HEALTH


CONFIG_PATH = ROOT / "config" / "taiwan_indicators.yaml"
OUTPUT = ROOT / "output"
OUT_HTML = OUTPUT / "taiwan.html"
SUMMARY_JSON = OUTPUT / "taiwan_dashboard_summary.json"
CANONICAL_JSON = OUTPUT / "taiwan_canonical_frame.json"
COUNTRY_CODE = "TW"
SUMMARY_KEY_IDS = [
    "real_gdp_yoy",
    "real_gdp_growth",
    "gross_fixed_capital_formation",
    "private_consumption",
    "government_consumption",
    "domestic_demand",
    "cpi_inflation",
    "core_cpi_inflation",
    "ppi_inflation",
    "rent_inflation",
    "policy_rate",
    "collateral_rate",
    "interbank_call_rate",
    "prime_lending_rate",
    "deposit_rate_1y",
    "m1b_growth",
    "m2_growth",
    "reserve_money_growth",
    "consumer_loans_growth",
    "mortgage_loans_growth",
    "commercial_paper_growth",
    "bond_market_growth",
    "usd_twd",
    "reer",
    "neer",
    "bis_reer",
    "current_account_usd",
    "goods_trade_balance",
    "goods_exports",
    "goods_imports",
    "services_balance",
    "current_account_gdp",
    "sovereign_yield_10y",
    "sovereign_yield_5y",
    "government_debt_gdp",
    "fiscal_balance_gdp",
    "unemployment_rate_weo",
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
        "tw_dgbas": lambda spec, cache: _apply_transform(apply_scale(fetch_tw_dgbas(spec))),
        "tw_cbc": lambda spec, cache: _apply_transform(apply_scale(fetch_tw_cbc(spec))),
        "fred": lambda spec, cache: _apply_transform(apply_scale(fetch_fred_us(requests.Session(), spec))),
        "bruegel_reer": lambda spec, cache: _apply_transform(fetch_bruegel_reer(requests.Session(), spec)),
        "imf_datamapper": lambda spec, cache: _apply_transform(fetch_imf_datamapper(requests.Session(), spec)),
    }

    if data_mode == "snapshot":
        series_list = load_canonical_data_first_frame(CANONICAL_JSON, config)
    else:
        SOURCE_HEALTH.reset()
        series_list, _ = fetch_all(config, registry, max_workers=6)
        series_list = retain_last_known_good_series(series_list, CANONICAL_JSON, config)
        series_list = track_revisions_and_vintages(series_list, CANONICAL_JSON, config)

    charted = [item for item in series_list if item.get("observations")]
    fx_item = next((item for item in charted if item["id"] == "usd_twd"), None)
    fx_latest = _latest(fx_item) if fx_item else None
    fx_latest_str = f"{float(fx_latest['value']):.2f} ({fx_latest['date']})" if fx_latest else "n/a"

    summary = build_country_page(
        country_code="TW",
        config=config,
        series_list=series_list,
        out_html=OUT_HTML,
        summary_json=SUMMARY_JSON,
        canonical_json=CANONICAL_JSON,
        data_mode=data_mode,
        summary_key_ids=SUMMARY_KEY_IDS,
        latest_value_key="usd_twd_latest",
        latest_value_display=fx_latest_str,
    )

    if not os.environ.get("COUNTRY_PRIMER_SKIP_ARCHIVE"):
        from build_dashboard_archive import build_archive
        build_archive()
    return OUT_HTML


if __name__ == "__main__":
    path = build()
    print(f"Wrote {path} ({path.stat().st_size:,} bytes)")
