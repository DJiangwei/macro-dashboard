"""Build the UK macro dashboard from PDF-aligned indicator config."""
from __future__ import annotations

import json
import os
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import requests
import yaml

from dashboard_summary_utils import (
    load_canonical_data_first_frame,
    retain_last_known_good_series,
    track_revisions_and_vintages,
)
from country_primer.page_renderer import build_country_page
from country_primer.data_first_pipeline import fetch_all

from country_primer.adapters import (
    _apply_uk_transform,
    fetch_fred,
    fetch_ons_timeseries,
    fetch_boe_iadb,
    fetch_boe_bank_rate,
    fetch_govuk_road_fuel,
    fetch_govuk_xlsx_table,
    fetch_govuk_ods_table,
    fetch_ons_xlsx_table,
    fetch_ons_horizontal_csv_table,
    fetch_obr_xlsx_row,
)

ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "config" / "uk_indicators.yaml"
OUTPUT = ROOT / "output"
OUT_HTML = OUTPUT / "uk.html"
SUMMARY_JSON = OUTPUT / "uk_dashboard_summary.json"
CANONICAL_JSON = OUTPUT / "uk_canonical_frame.json"
SUMMARY_KEY_IDS = [
    "real_gdp_growth",
    "real_gdp_yoy",
    "services_output_growth",
    "manufacturing_output_growth",
    "unemployment_rate",
    "employment_growth",
    "regular_pay_growth",
    "cpi_inflation",
    "core_cpi_inflation",
    "services_cpi_inflation",
    "retail_sales_growth",
    "house_price_growth",
    "consumer_confidence",
    "gbp_usd",
    "government_borrowing_ytd",
    "government_debt_gdp",
    "sovereign_yield_10y",
    "bank_rate",
]

def _load_config() -> dict[str, Any]:
    return yaml.safe_load(CONFIG_PATH.read_text()) or {}

def inject_output_index(summary: dict[str, Any]) -> None:
    index_path = OUTPUT / "index.html"
    if not index_path.exists():
        return
    html = index_path.read_text()
    html = re.sub(r"\n\s*<!-- UK dashboard card -->.*?<!-- /UK dashboard card -->", "", html, flags=re.S)
    card = f'''
  <!-- UK dashboard card -->
  <a href="uk.html" class="card clean">
    <div class="card-kicker">GBP · BOE · UK data-first page</div>
    <h2>United Kingdom</h2>
    <div class="stats">
      <div class="stat"><span>Rendered charts</span><strong>{summary['charts']}</strong></div>
      <div class="stat"><span>Proxy fills</span><strong>0</strong></div>
      <div class="stat"><span>Data gaps tracked</span><strong>{summary['data_gaps']}</strong></div>
      <div class="stat"><span>Bank Rate</span><strong>{summary.get('bank_rate_latest', 'n/a')}</strong></div>
      <div class="stat"><span>Source groups</span><strong>{summary['source_groups']}</strong></div>
      <div class="stat"><span>Framework</span><strong>GS UK statistics logic</strong></div>
    </div>
  </a>
  <!-- /UK dashboard card -->'''
    marker = '  </section>\n  <nav class="links"'
    if marker in html:
        html = html.replace(marker, card + "\n  </section>\n  <nav class=\"links\"", 1)

    html = re.sub(r"Macro Dashboard Archive · CEE-4 v4 \+ China[^<]*", "Macro Dashboard Archive · CEE-4 v4 + China + Japan + South Africa + UK + US", html)
    html = re.sub(
        r"Generated archive entry for the proxy-free CEE-4 dashboards plus the [^.]*\.",
        "Generated archive entry for the proxy-free CEE-4 dashboards plus the China, Japan, South Africa, UK, and US data-first pages.",
        html,
    )
    html = html.replace("<strong>5</strong><span>country dashboards</span>", "<strong>6</strong><span>country dashboards</span>")

    from country_primer.page_renderer import _write_clean
    _write_clean(index_path, html)

def build(data_mode: str | None = None) -> Path:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    data_mode = (data_mode or os.environ.get("COUNTRY_PRIMER_DATA_MODE") or "refresh").strip().lower()
    config = _load_config()

    import requests
    from country_primer.adapters import (
        fetch_fred, fetch_ons_timeseries, fetch_boe_iadb, fetch_boe_bank_rate,
        fetch_govuk_road_fuel, fetch_govuk_xlsx_table, fetch_govuk_ods_table,
        fetch_ons_xlsx_table, fetch_ons_horizontal_csv_table, fetch_obr_xlsx_row
    )
    registry = {
        "fred": lambda spec, cache: fetch_fred(requests.Session(), spec),
        "ons_timeseries": lambda spec, cache: fetch_ons_timeseries(requests.Session(), spec),
        "boe_iadb": lambda spec, cache: fetch_boe_iadb(requests.Session(), spec),
        "boe_bank_rate": lambda spec, cache: fetch_boe_bank_rate(requests.Session(), spec),
        "govuk_road_fuel": lambda spec, cache: fetch_govuk_road_fuel(requests.Session(), spec),
        "govuk_xlsx_table": lambda spec, cache: fetch_govuk_xlsx_table(requests.Session(), spec),
        "govuk_ods_table": lambda spec, cache: fetch_govuk_ods_table(requests.Session(), spec),
        "ons_xlsx_table": lambda spec, cache: fetch_ons_xlsx_table(requests.Session(), spec),
        "ons_horizontal_csv_table": lambda spec, cache: fetch_ons_horizontal_csv_table(requests.Session(), spec),
        "obr_xlsx_row": lambda spec, cache: fetch_obr_xlsx_row(requests.Session(), spec),
    }

    if data_mode == "snapshot":
        series_list = load_canonical_data_first_frame(CANONICAL_JSON, config)
    else:
        from country_primer.source_health import SOURCE_HEALTH
        SOURCE_HEALTH.reset()
        series_list, _ = fetch_all(config, registry, max_workers=4)
        series_list = retain_last_known_good_series(series_list, CANONICAL_JSON, config)
        series_list = track_revisions_and_vintages(series_list, CANONICAL_JSON, config)

    charted = [item for item in series_list if item.get("observations")]
    bank_rate = next((item for item in charted if item["id"] == "bank_rate"), None)

    from country_primer.page_renderer import _latest
    br_latest = _latest(bank_rate) if bank_rate else None
    br_latest_str = f"{float(br_latest['value']):.2f}% ({br_latest['date']})" if br_latest else "n/a"

    summary = build_country_page(
        country_code="UK",
        config=config,
        series_list=series_list,
        out_html=OUT_HTML,
        summary_json=SUMMARY_JSON,
        canonical_json=CANONICAL_JSON,
        data_mode=data_mode,
        summary_key_ids=SUMMARY_KEY_IDS,
        latest_value_key="bank_rate_latest",
        latest_value_display=br_latest_str
    )

    inject_output_index(summary)

    if not os.environ.get("COUNTRY_PRIMER_SKIP_ARCHIVE"):
        from build_dashboard_archive import build_archive
        build_archive()
    return OUT_HTML

if __name__ == "__main__":
    path = build()
    print(f"Wrote {path} ({path.stat().st_size:,} bytes)")
