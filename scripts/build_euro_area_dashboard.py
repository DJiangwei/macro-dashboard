"""Build the Euro Area macro dashboard from the Euro Area indicator config.

The Euro Area page is built directly from official European compiling authorities:
  * ECB Data Portal SDMX 2.1 API for monetary policy rates (DFR), €STR, negotiated
    wages, AAA government yield curves, benchmark sovereign bond yields, TARGET2 balances,
    CISS systemic stress indicator, M3 broad money, adjusted private loan growth,
    NFC cost of borrowing, Eurosystem balance sheet total assets, BLS credit standards,
    and supervisory banking statistics (CET1 and NPL ratios);
  * Eurostat Dissemination JSON-stat 2.0 API for quarterly national accounts (real GDP,
    household consumption, GFCF, government consumption, exports, imports), monthly
    short-term business statistics (industrial production, manufacturing, retail sales,
    construction, PPI, building permits), HICP consumer price inflation components
    (headline, core, services, energy, food via prc_hicp_manr), harmonised unemployment,
    job vacancies, Labour Cost Index, house price index, extra-EA trade balance,
    quarterly BoP current account, and government deficit and debt ratios;
  * Derived sovereign spreads (Italy BTP, France OAT, Spain Bonos, Greece GGB vs German Bund)
    and AAA yield curve slope (10Y minus 2Y) computed via fetch_spread;
  * FRED for BIS-compiled real effective exchange rates and household credit to GDP;
  * IMF WEO DataMapper for cyclically adjusted structural fiscal balance.

Indicators without a validated key-free endpoint are recorded in ``data_gaps`` rather
than filled with a proxy.
"""
from __future__ import annotations

import collections
import json
import os
import re
from datetime import UTC, datetime
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
from country_primer.page_renderer import build_country_page, _latest
from country_primer.data_first_pipeline import fetch_all
from country_primer.adapters import _apply_us_transform as _apply_transform, fetch_fred_us
from country_primer.adapters import (
    USER_AGENT,
    apply_scale,
    fetch_ecb_sdmx,
    fetch_eurostat_jsonstat,
    fetch_spread,
    fetch_imf_datamapper,
)
from country_primer.source_health import (
    SOURCE_HEALTH,
    failure_series,
    guarded_source_call,
    write_source_health_report,
)


ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "config" / "euro_area_indicators.yaml"
OUTPUT = ROOT / "output"
OUT_HTML = OUTPUT / "euro_area.html"
SUMMARY_JSON = OUTPUT / "euro_area_dashboard_summary.json"
CANONICAL_JSON = OUTPUT / "euro_area_canonical_frame.json"
COUNTRY_CODE = "EA"
SUMMARY_KEY_IDS = [
    "real_gdp_growth",
    "real_gdp_yoy",
    "hicp_inflation",
    "hicp_core_inflation",
    "policy_rate",
    "unemployment_rate",
    "m3_growth",
    "goods_trade_balance",
    "it_de_spread_10y",
]


def _load_config() -> dict[str, Any]:
    return yaml.safe_load(CONFIG_PATH.read_text()) or {}


def inject_output_index(summary: dict[str, Any]) -> None:
    index_path = OUTPUT / "index.html"
    if not index_path.exists():
        return
    html = index_path.read_text()
    html = re.sub(r"\n\s*<!-- Euro Area dashboard card -->.*?<!-- /Euro Area dashboard card -->", "", html, flags=re.S)

    card = f'''
  <!-- Euro Area dashboard card -->
  <a href="euro_area.html" class="card clean" data-country="EA">
    <div class="card-kicker">EUR · ECB · EA data-first page</div>
    <h2>Euro Area</h2>
    <div class="stats">
      <div class="stat"><span>Rendered charts</span><strong>{summary['charts']}/{summary['charts']}</strong></div>
      <div class="stat"><span>Proxy fills</span><strong>0</strong></div>
      <div class="stat"><span>Official data gaps</span><strong>{summary['data_gaps']}</strong></div>
      <div class="stat"><span>Deposit Facility Rate</span><strong>{summary.get('policy_rate_latest', 'n/a')}</strong></div>
      <div class="stat"><span>Source groups</span><strong>{summary['source_groups']}</strong></div>
      <div class="stat"><span>Framework</span><strong>Nine-pillar comparable core</strong></div>
    </div>
  </a>
  <!-- /Euro Area dashboard card -->'''

    marker = '  </section>\n  <nav class="links"'
    if marker in html:
        html = html.replace(marker, card + "\n  </section>\n  <nav class=\"links\"", 1)

    from country_primer.page_renderer import _write_clean
    _write_clean(index_path, html)


def _fetch_one(spec: dict[str, Any]) -> dict[str, Any]:
    fetcher = spec.get("fetcher")
    session = requests.Session()
    if fetcher == "ecb_sdmx":
        return _apply_transform(apply_scale(fetch_ecb_sdmx(session, spec)))
    elif fetcher == "eurostat_jsonstat":
        return _apply_transform(apply_scale(fetch_eurostat_jsonstat(session, spec)))
    elif fetcher == "spread":
        return _apply_transform(apply_scale(fetch_spread(session, spec)))
    elif fetcher == "fred":
        return _apply_transform(apply_scale(fetch_fred_us(session, spec)))
    elif fetcher == "imf_datamapper":
        return _apply_transform(fetch_imf_datamapper(session, spec))
    raise ValueError(f"Unknown fetcher {fetcher}")


def build(data_mode: str | None = None) -> Path:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    data_mode = (data_mode or os.environ.get("COUNTRY_PRIMER_DATA_MODE") or "refresh").strip().lower()
    config = _load_config()

    registry = {
        "ecb_sdmx": lambda spec, cache: _apply_transform(apply_scale(fetch_ecb_sdmx(requests.Session(), spec))),
        "eurostat_jsonstat": lambda spec, cache: _apply_transform(apply_scale(fetch_eurostat_jsonstat(requests.Session(), spec))),
        "spread": lambda spec, cache: _apply_transform(apply_scale(fetch_spread(requests.Session(), spec))),
        "fred": lambda spec, cache: _apply_transform(apply_scale(fetch_fred_us(requests.Session(), spec))),
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
    policy_rate = next((item for item in charted if item["id"] == "policy_rate"), None)

    policy_latest = _latest(policy_rate) if policy_rate else None
    policy_latest_str = f"{float(policy_latest['value']):.2f}% ({policy_latest['date']})" if policy_latest else "n/a"

    summary = build_country_page(
        country_code="EA",
        config=config,
        series_list=series_list,
        out_html=OUT_HTML,
        summary_json=SUMMARY_JSON,
        canonical_json=CANONICAL_JSON,
        data_mode=data_mode,
        summary_key_ids=SUMMARY_KEY_IDS,
        latest_value_key="policy_rate_latest",
        latest_value_display=policy_latest_str,
    )

    inject_output_index(summary)

    if not os.environ.get("COUNTRY_PRIMER_SKIP_ARCHIVE"):
        from build_dashboard_archive import build_archive
        build_archive()
    return OUT_HTML


if __name__ == "__main__":
    path = build()
    print(f"Wrote {path} ({path.stat().st_size:,} bytes)")
