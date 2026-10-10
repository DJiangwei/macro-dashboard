"""Build the China macro dashboard from PDF-aligned indicator config."""
from __future__ import annotations

import json
import os
import re
from datetime import UTC, datetime
from html import escape
from pathlib import Path
from typing import Any

import requests
import yaml

from dashboard_summary_utils import (
    load_canonical_data_first_frame,
    retain_last_known_good_series,
    track_revisions_and_vintages,
)
from country_primer.page_renderer import build_country_page, _write_clean
from country_primer.data_first_pipeline import fetch_all

from country_primer.adapters import (
    _apply_china_transform,
    fetch_world_bank,
    fetch_imf_datamapper,
    fetch_fred_graph,
    fetch_akshare_table,
    fetch_akshare_wide_year_month,
    fetch_eastmoney_industry_indicator,
    fetch_safe_midpoint,
    fetch_pbc_card,
)

ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "config" / "china_indicators.yaml"
OUTPUT = ROOT / "output"
OUT_HTML = OUTPUT / "china.html"
SUMMARY_JSON = OUTPUT / "china_dashboard_summary.json"
CANONICAL_JSON = OUTPUT / "china_canonical_frame.json"
SUMMARY_KEY_IDS = [
    "real_gdp_growth",
    "industrial_value_added_yoy_akshare",
    "fixed_asset_investment_yoy_akshare",
    "commercial_housing_sales_value_eastmoney",
    "real_estate_development_investment_ytd_eastmoney",
    "passenger_vehicle_retail_cpca",
    "new_energy_vehicle_share_cpca",
    "customs_exports_yoy_akshare",
    "usd_cny_midpoint",
    "m2_yoy_akshare",
    "financial_institution_deposits_stock_akshare",
    "vegetable_basket_price_index_akshare",
    "pbc_total_assets_akshare",
    "pbc_reserve_money_akshare",
    "cpi_yoy_akshare",
    "ppi_yoy_akshare",
]

def _load_config() -> dict[str, Any]:
    return yaml.safe_load(CONFIG_PATH.read_text()) or {}

def _index_card(summary: dict[str, Any]) -> str:
    return f"""
  <!-- China dashboard card -->
  <a href="china.html" class="card clean">
    <div class="card-kicker">CNY · PBC · China data-first page</div>
    <h2>China</h2>
    <div class="stats">
      <div class="stat"><span>Rendered charts</span><strong>{summary['charts']}</strong></div>
      <div class="stat"><span>Proxy fills</span><strong>0</strong></div>
      <div class="stat"><span>Official gaps tracked</span><strong>{summary['data_gaps']}</strong></div>
      <div class="stat"><span>Latest USD/CNY fixing</span><strong>{escape(summary.get('usd_cny_latest', 'n/a'))}</strong></div>
      <div class="stat"><span>Source groups</span><strong>{summary['source_groups']}</strong></div>
      <div class="stat"><span>Framework</span><strong>GS China statistics logic</strong></div>
    </div>
  </a>
  <!-- /China dashboard card -->"""

def inject_index(summary: dict[str, Any]) -> None:
    index_path = OUTPUT / "index.html"
    if not index_path.exists():
        return
    html = index_path.read_text()
    html = re.sub(r"\n\s*<!-- China dashboard card -->.*?<!-- /China dashboard card -->", "", html, flags=re.S)
    marker = '  </section>\n  <nav class="links"'
    if marker in html:
        html = html.replace(marker, _index_card(summary) + "\n  </section>\n  <nav class=\"links\"", 1)
    html = html.replace("<title>Country Primer — CEE-4 Macro Dashboard</title>", "<title>Country Primer — Macro Dashboard Archive</title>")
    html = html.replace("CEE-4 Macro Dashboard · v4 · Proxy-free public pages", "Macro Dashboard Archive · CEE-4 v4 + China")
    html = html.replace("<h1>CEE-4 Macro Dashboard</h1>", "<h1>Macro Dashboard Archive</h1>")
    html = html.replace(
        "Generated archive entry for the four country dashboards. This page is rebuilt by <code>build_v4.py ALL</code>, so its links, indicator counts, proxy status, and quality summary stay synchronized with the individual country pages.",
        "Generated archive entry for the proxy-free CEE-4 dashboards plus the China data-first page. This page is rebuilt by <code>make build-v4</code>, so links, indicator counts, proxy status, and quality summary stay synchronized with generated pages.",
    )
    html = html.replace("<span>rendered country-indicator slots</span>", "<span>CEE-4 rendered indicator slots</span>")
    html = html.replace("<strong>4</strong><span>country dashboards</span>", "<strong>5</strong><span>country dashboards</span>")
    _write_clean(index_path, html)

def build(data_mode: str | None = None) -> Path:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    data_mode = (data_mode or os.environ.get("COUNTRY_PRIMER_DATA_MODE") or "refresh").strip().lower()
    config = _load_config()

    import requests
    from country_primer.adapters import fetch_eastmoney, fetch_nbs_api
    registry = {
        "world_bank": lambda spec, cache: fetch_world_bank(spec),
        "imf_datamapper": lambda spec, cache: fetch_imf_datamapper(spec),
        "fred_graph_csv": lambda spec, cache: fetch_fred_graph(spec),
        "akshare_table": lambda spec, cache: fetch_akshare_table(spec, cache),
        "akshare_wide_year_month": lambda spec, cache: fetch_akshare_wide_year_month(spec, cache),
        "eastmoney_industry_indicator": lambda spec, cache: fetch_eastmoney_industry_indicator(spec),
        "safe_rmb_midpoint": lambda spec, cache: fetch_safe_midpoint(spec, cache.setdefault("safe_rows", [])),
        "pbc_card": lambda spec, cache: fetch_pbc_card(spec),
        "eastmoney_api": lambda spec, cache: fetch_eastmoney(requests.Session(), spec),
        "nbs_api": lambda spec, cache: fetch_nbs_api(requests.Session(), spec),
    }

    if data_mode == "snapshot":
        series_list = load_canonical_data_first_frame(CANONICAL_JSON, config)
        previous_summary = json.loads(SUMMARY_JSON.read_text()) if SUMMARY_JSON.exists() else {}
        cards = list(previous_summary.get("latest_cards") or [
            {**card, "value": "n/a", "updated": "n/a"}
            for card in config.get("latest_cards", [])
        ])
    else:
        from country_primer.source_health import SOURCE_HEALTH
        SOURCE_HEALTH.reset()
        series_list, cards = fetch_all(config, registry, max_workers=4)
        series_list = retain_last_known_good_series(series_list, CANONICAL_JSON, config)
        series_list = track_revisions_and_vintages(series_list, CANONICAL_JSON, config)

    charted = [item for item in series_list if item.get("observations")]
    usd_cny = next((item for item in charted if item["id"] == "usd_cny_midpoint"), None)

    from country_primer.page_renderer import _latest
    usd_latest = _latest(usd_cny) if usd_cny else None
    usd_latest_str = f"{float(usd_latest['value']):.4f} ({usd_latest['date']})" if usd_latest else "n/a"

    summary = build_country_page(
        country_code="CN",
        config=config,
        series_list=series_list,
        out_html=OUT_HTML,
        summary_json=SUMMARY_JSON,
        canonical_json=CANONICAL_JSON,
        data_mode=data_mode,
        summary_key_ids=SUMMARY_KEY_IDS,
        extra_cards=cards,
        latest_value_key="usd_cny_latest",
        latest_value_display=usd_latest_str
    )

    inject_index(summary)

    if not os.environ.get("COUNTRY_PRIMER_SKIP_ARCHIVE"):
        from build_dashboard_archive import build_archive
        build_archive()
    return OUT_HTML

if __name__ == "__main__":
    path = build()
    print(f"Wrote {path} ({path.stat().st_size:,} bytes)")
