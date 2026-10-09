"""Build the South Africa macro dashboard from the South Africa indicator config.

South Africa is the first page in this repo where the national central bank
exposes a usable public JSON API, so the SARB Web Indicators service is the
preferred path for rates, prices, and the rand crosses: SARB is the compiling
authority for those series and publishes them same-day. FRED (OECD/Stats SA/BIS
mirrors) carries national accounts, production, labour, trade, and credit; the
IMF SDMX API carries the CPI cross-check and Financial Soundness Indicators; and
the IMF WEO DataMapper carries fiscal ratios with an explicit forecast split.

Indicators without a validated key-free endpoint - notably Eskom load-shedding
and the vendor-controlled BER/PMI surveys - are recorded in ``data_gaps`` rather
than filled with a proxy.
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
    USER_AGENT,
    apply_scale,
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
CONFIG_PATH = ROOT / "config" / "south_africa_indicators.yaml"
OUTPUT = ROOT / "output"
OUT_HTML = OUTPUT / "south_africa.html"
SUMMARY_JSON = OUTPUT / "south_africa_dashboard_summary.json"
CANONICAL_JSON = OUTPUT / "south_africa_canonical_frame.json"
COUNTRY_CODE = "ZA"
SUMMARY_KEY_IDS = [
    "real_gdp_growth",
    "real_gdp_yoy",
    "nominal_gdp_growth",
    "manufacturing_production_growth",
    "retail_sales_growth",
    "unemployment_rate",
    "youth_unemployment_rate",
    "cpi_inflation",
    "ppi_inflation",
    "house_price_growth",
    "goods_trade_balance",
    "zar_usd",
    "reer",
    "government_debt_gdp",
    "sovereign_yield_10y",
    "policy_rate",
    "prime_lending_rate",
    "broad_money_growth",
]

SARB_BASE = "https://custom.resbank.co.za/SarbWebApi/WebIndicators/Shared/GetTimeseriesObservations"


def _load_config() -> dict[str, Any]:
    return yaml.safe_load(CONFIG_PATH.read_text()) or {}


def fetch_sarb(session: requests.Session, spec: dict[str, Any]) -> dict[str, Any]:
    """Fetch one SARB Web Indicators timeseries code.

    The bare ``/{code}`` form of this endpoint returns only the last 25
    observations, which is too short to chart, so the explicit date-range form
    is always used.
    """
    code = str(spec["series"])
    start_date = str(spec.get("start_date") or "1990-01-01")
    end_date = datetime.now(UTC).date().isoformat()
    url = f"{SARB_BASE}/{code}/{start_date}/{end_date}"
    response = session.get(
        url,
        headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
        timeout=(5, 45),
    )
    response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, list):
        raise RuntimeError(f"SARB returned an unexpected payload for {code}.")

    frequency = str(spec.get("frequency") or "").strip().lower()
    observations: list[dict[str, Any]] = []
    for row in payload:
        period = str(row.get("Period") or "")[:10]
        raw_value = row.get("Value")
        if not re.match(r"^\d{4}-\d{2}-\d{2}$", period) or raw_value is None:
            continue
        if frequency == "monthly":
            # SARB stamps monthly readings with the last calendar day of the
            # reference month (e.g. "2026-07-31"); every other source in this
            # repo (FRED, IMF SDMX, e-Stat) stamps the first day instead. Align
            # to that convention so same-period observations from independent
            # sources share a date key for cross-source comparison.
            period = f"{period[:7]}-01"
        try:
            observations.append({"date": period, "value": float(raw_value)})
        except (TypeError, ValueError):
            continue
    observations.sort(key=lambda item: item["date"])
    if not observations:
        raise RuntimeError(f"SARB returned no observations for {code}.")
    return {
        **spec,
        "observations": observations,
        "provider_updated": observations[-1]["date"],
        "api_url": url,
    }



def inject_output_index(summary: dict[str, Any]) -> None:
    index_path = OUTPUT / "index.html"
    if not index_path.exists():
        return
    html = index_path.read_text()
    html = re.sub(r"\n\s*<!-- South Africa dashboard card -->.*?<!-- /South Africa dashboard card -->", "", html, flags=re.S)

    card = f'''
  <!-- South Africa dashboard card -->
  <a href="south_africa.html" class="card clean">
    <div class="card-kicker">ZAR · SARB · ZA data-first page</div>
    <h2>South Africa</h2>
    <div class="stats">
      <div class="stat"><span>Rendered charts</span><strong>{summary['charts']}</strong></div>
      <div class="stat"><span>Proxy fills</span><strong>0</strong></div>
      <div class="stat"><span>Data gaps tracked</span><strong>{summary['data_gaps']}</strong></div>
      <div class="stat"><span>Target Rate</span><strong>{summary.get('repo_rate_latest', 'n/a')}</strong></div>
      <div class="stat"><span>Source groups</span><strong>{summary['source_groups']}</strong></div>
      <div class="stat"><span>Framework</span><strong>GS CEEMEA statistics logic</strong></div>
    </div>
  </a>
  <!-- /South Africa dashboard card -->'''

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
        "sarb": lambda spec, cache: _apply_transform(fetch_sarb(requests.Session(), spec)),
        "imf_datamapper": lambda spec, cache: _apply_transform(fetch_imf_datamapper(requests.Session(), spec)),
        "imf_sdmx": lambda spec, cache: _apply_transform(apply_scale(fetch_imf_sdmx(requests.Session(), spec))),
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
    repo_rate = next((item for item in charted if item["id"] == "policy_repo_rate"), None)

    from country_primer.page_renderer import _latest, build_country_page
    repo_latest = _latest(repo_rate) if repo_rate else None
    repo_latest_str = f"{float(repo_latest['value']):.2f}% ({repo_latest['date']})" if repo_latest else "n/a"

    summary = build_country_page(
        country_code="ZA",
        config=config,
        series_list=series_list,
        out_html=OUT_HTML,
        summary_json=SUMMARY_JSON,
        canonical_json=CANONICAL_JSON,
        data_mode=data_mode,
        summary_key_ids=SUMMARY_KEY_IDS,
        latest_value_key="repo_rate_latest",
        latest_value_display=repo_latest_str
    )

    inject_output_index(summary)

    if not os.environ.get("COUNTRY_PRIMER_SKIP_ARCHIVE"):
        from build_dashboard_archive import build_archive
        build_archive()
    return OUT_HTML

if __name__ == "__main__":
    path = build()
    print(f"Wrote {path} ({path.stat().st_size:,} bytes)")
