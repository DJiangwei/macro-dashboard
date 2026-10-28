"""Build the Egypt macro dashboard from the Egypt indicator config.

Egypt is built on official data series from DBnomics (IMF International
Financial Statistics policy rate, lending rate, deposit rate, USD/EGP exchange rate,
current account, and goods balance), IMF DataMapper (WEO growth, inflation, external debt,
and Fiscal Monitor), World Bank WDI (growth accounts, unemployment, broad money,
private credit, and workers' remittances % of GDP), FRED (gross FX reserves and Brent crude),
and the Bruegel 178-country REER dataset.
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
    fetch_fred_graph,
    fetch_imf_datamapper,
    fetch_world_bank,
)
from country_primer.cross_checks import evaluate_cross_checks
from country_primer.source_health import SOURCE_HEALTH


CONFIG_PATH = ROOT / "config" / "egypt_indicators.yaml"
OUTPUT = ROOT / "output"
OUT_HTML = OUTPUT / "egypt.html"
SUMMARY_JSON = OUTPUT / "egypt_dashboard_summary.json"
CANONICAL_JSON = OUTPUT / "egypt_canonical_frame.json"
COUNTRY_CODE = "EG"
SUMMARY_KEY_IDS = [
    "real_gdp_growth",
    "real_gdp_growth_wb",
    "consumption_growth",
    "investment_growth",
    "unemployment_rate",
    "cpi_inflation",
    "cpi_index",
    "usd_egp",
    "reer",
    "neer",
    "remittances_gdp",
    "current_account_usd",
    "goods_trade_balance",
    "current_account_gdp",
    "government_debt_gdp",
    "fiscal_balance_gdp",
    "primary_balance_gdp",
    "fx_reserves",
    "policy_rate",
    "lending_rate",
    "deposit_rate",
    "broad_money_growth",
    "private_credit_gdp",
    "brent_crude_oil",
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
        "imf_datamapper": lambda spec, cache: _apply_transform(fetch_imf_datamapper(requests.Session(), spec)),
        "world_bank": lambda spec, cache: _apply_transform(fetch_world_bank(spec)),
        "bruegel_reer": lambda spec, cache: _apply_transform(fetch_bruegel_reer(spec)),
        "dbnomics": lambda spec, cache: _apply_transform(fetch_dbnomics(spec)),
        "fred_graph": lambda spec, cache: _apply_transform(fetch_fred_graph(spec)),
    }

    if data_mode == "snapshot":
        series_list = load_canonical_data_first_frame(CANONICAL_JSON, config)
    else:
        SOURCE_HEALTH.reset()
        series_list, _ = fetch_all(config, registry, max_workers=6)
        series_list = retain_last_known_good_series(series_list, CANONICAL_JSON, config)
        series_list = track_revisions_and_vintages(series_list, CANONICAL_JSON, config)

    charted = [item for item in series_list if item.get("observations")]
    fx_item = next((item for item in charted if item["id"] == "usd_egp"), None)
    fx_latest = _latest(fx_item) if fx_item else None
    fx_latest_str = f"{float(fx_latest['value']):.2f} ({fx_latest['date']})" if fx_latest else "n/a"

    summary = build_country_page(
        country_code="EG",
        config=config,
        series_list=series_list,
        out_html=OUT_HTML,
        summary_json=SUMMARY_JSON,
        canonical_json=CANONICAL_JSON,
        data_mode=data_mode,
        summary_key_ids=SUMMARY_KEY_IDS,
        latest_value_key="usd_egp_latest",
        latest_value_display=fx_latest_str,
    )

    if not os.environ.get("COUNTRY_PRIMER_SKIP_ARCHIVE"):
        from build_dashboard_archive import build_archive
        build_archive()
    return OUT_HTML


if __name__ == "__main__":
    path = build()
    print(f"Wrote {path} ({path.stat().st_size:,} bytes)")
