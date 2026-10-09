"""Build the Japan macro dashboard from the Japan indicator config.

Japan is the first page in this repo where the FRED/OECD mirror is not enough on
its own: OECD discontinued its Japan CPI, retail-value, and money-stock mirrors
in 2021-2024, so those series return metadata with no observations. The page
therefore uses three reproducible public backbones side by side:

  * FRED (official API when ``FRED_API_KEY`` is set, public graph CSV otherwise)
    for national accounts, production, labour, trade, rates, and BIS series;
  * the IMF SDMX 2.1 API for national CPI and Financial Soundness Indicators;
  * the IMF WEO DataMapper for fiscal ratios with an explicit forecast split.

Indicators without a validated key-free endpoint are recorded in ``data_gaps``
rather than filled with a proxy.
"""
from __future__ import annotations

import collections
import json
import os
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import UTC, datetime
from html import escape
from pathlib import Path
from typing import Any

import requests
import yaml

from dashboard_summary_utils import (
    apply_quality_assessments,
    build_summary_metadata,
    canonical_frame_metadata,
    load_canonical_data_first_frame,
    retain_last_known_good_series,
    track_revisions_and_vintages,
    write_canonical_data_first_frame,
)
from country_primer.page_renderer import build_country_page
from country_primer.data_first_pipeline import fetch_all
from build_uk_dashboard import validate_series
from build_us_dashboard import _apply_transform, fetch_fred_us
from country_primer.adapters import (
    fetch_imf_datamapper,
    fetch_imf_sdmx,
    USER_AGENT,
    EstatCredentialMissing,
    apply_scale,
    fetch_boj_flatfile,
    fetch_estat,
    fetch_imf_datamapper,
    fetch_imf_sdmx,
)
from country_primer.cross_checks import evaluate_cross_checks
from country_primer.source_health import (
    SOURCE_HEALTH,
    failure_series,
    guarded_source_call,
    write_source_health_report,
)


ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "config" / "japan_indicators.yaml"
OUTPUT = ROOT / "output"
OUT_HTML = OUTPUT / "japan.html"
SUMMARY_JSON = OUTPUT / "japan_dashboard_summary.json"
CANONICAL_JSON = OUTPUT / "japan_canonical_frame.json"
COUNTRY_CODE = "JP"
SUMMARY_KEY_IDS = [
    "real_gdp_growth",
    "real_gdp_yoy",
    "nominal_gdp_growth",
    "industrial_production_growth",
    "retail_sales_growth",
    "unemployment_rate",
    "manufacturing_earnings_growth",
    "cpi_inflation",
    "house_price_growth",
    "goods_trade_balance",
    "usd_jpy",
    "reer",
    "government_debt_gdp",
    "sovereign_yield_10y",
    "policy_rate",
    "broad_money_growth",
    "equity_index",
]


def _load_config() -> dict[str, Any]:
    return yaml.safe_load(CONFIG_PATH.read_text()) or {}



def inject_output_index(summary: dict[str, Any]) -> None:
    index_path = OUTPUT / "index.html"
    if not index_path.exists():
        return
    html = index_path.read_text()
    html = re.sub(r"\n\s*<!-- JP dashboard card -->.*?<!-- /JP dashboard card -->", "", html, flags=re.S)

    card = f'''
  <!-- JP dashboard card -->
  <a href="japan.html" class="card clean">
    <div class="card-kicker">JPY · BOJ · Japan data-first page</div>
    <h2>Japan</h2>
    <div class="stats">
      <div class="stat"><span>Rendered charts</span><strong>{summary['charts']}</strong></div>
      <div class="stat"><span>Proxy fills</span><strong>0</strong></div>
      <div class="stat"><span>Data gaps tracked</span><strong>{summary['data_gaps']}</strong></div>
      <div class="stat"><span>Target Rate</span><strong>{summary.get('boj_rate_latest', 'n/a')}</strong></div>
      <div class="stat"><span>Source groups</span><strong>{summary['source_groups']}</strong></div>
      <div class="stat"><span>Framework</span><strong>GS Japan statistics logic</strong></div>
    </div>
  </a>
  <!-- /JP dashboard card -->'''

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

    registry = {
        "fred": lambda spec, cache: _apply_transform(apply_scale(fetch_fred_us(requests.Session(), spec))),
        "boj_flatfile": lambda spec, cache: _apply_transform(apply_scale(fetch_boj_flatfile(requests.Session(), spec))),
        "estat": lambda spec, cache: _apply_transform(apply_scale(fetch_estat(requests.Session(), spec))),
        "imf_datamapper": lambda spec, cache: _apply_transform(fetch_imf_datamapper(requests.Session(), spec)),
        "imf_sdmx": lambda spec, cache: _apply_transform(fetch_imf_sdmx(requests.Session(), spec)),
    }

    if data_mode == "snapshot":
        series_list = load_canonical_data_first_frame(CANONICAL_JSON, config)
    else:
        from country_primer.source_health import SOURCE_HEALTH
        from country_primer.data_first_pipeline import fetch_all
        SOURCE_HEALTH.reset()
        series_list, _ = fetch_all(config, registry, max_workers=4)
        series_list = retain_last_known_good_series(series_list, CANONICAL_JSON, config)
        series_list = track_revisions_and_vintages(series_list, CANONICAL_JSON, config)

    charted = [item for item in series_list if item.get("observations")]
    boj_rate = next((item for item in charted if item["id"] == "boj_policy_balance_rate"), None)

    from country_primer.page_renderer import _latest, build_country_page
    boj_latest = _latest(boj_rate) if boj_rate else None
    boj_latest_str = f"{float(boj_latest['value']):.2f}% ({boj_latest['date']})" if boj_latest else "n/a"

    summary = build_country_page(
        country_code="JP",
        config=config,
        series_list=series_list,
        out_html=OUT_HTML,
        summary_json=SUMMARY_JSON,
        canonical_json=CANONICAL_JSON,
        data_mode=data_mode,
        summary_key_ids=SUMMARY_KEY_IDS,
        latest_value_key="boj_rate_latest",
        latest_value_display=boj_latest_str
    )

    inject_output_index(summary)

    if not os.environ.get("COUNTRY_PRIMER_SKIP_ARCHIVE"):
        from build_dashboard_archive import build_archive
        build_archive()
    return OUT_HTML

if __name__ == "__main__":
    path = build()
    print(f"Wrote {path} ({path.stat().st_size:,} bytes)")
