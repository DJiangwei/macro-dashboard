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

import csv
import io
import json
import os
import re
import threading
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
    write_canonical_data_first_frame,
)
from build_china_dashboard import (  # Reuse the data-first page shell.
    CSS,
    _format_value,
    _gaps_html,
    _latest,
    _section_nav,
    _sections_html,
    _write_clean,
)
from build_uk_dashboard import validate_series
from build_us_dashboard import _apply_transform, fetch_fred_us
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

IMF_SDMX_BASE = "https://api.imf.org/external/sdmx/2.1/data"
IMF_DATAMAPPER_BASE = "https://www.imf.org/external/datamapper/api/v1"
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 Chrome/124.0 Safari/537.36"
)

# The IMF SDMX endpoint rejects startPeriod on several dataflows and answers the
# unfiltered request instead, so one full pull per dataflow is cached in-process
# and sliced per indicator rather than refetched for every series key.
IMF_SDMX_LOCK = threading.Lock()
IMF_SDMX_CACHE: dict[tuple[str, str], list[dict[str, str]]] = {}


def _load_config() -> dict[str, Any]:
    return yaml.safe_load(CONFIG_PATH.read_text()) or {}


def _sdmx_period_to_date(value: str) -> str | None:
    """Normalise SDMX period notation (2026-M06, 2025-Q3, 2024) to ISO dates."""
    text = str(value or "").strip()
    match = re.match(r"^(\d{4})-M(\d{1,2})$", text)
    if match:
        return f"{int(match.group(1)):04d}-{int(match.group(2)):02d}-01"
    match = re.match(r"^(\d{4})-Q([1-4])$", text)
    if match:
        return f"{int(match.group(1)):04d}-{(int(match.group(2)) - 1) * 3 + 1:02d}-01"
    match = re.match(r"^(\d{4})-(\d{2})$", text)
    if match:
        return f"{match.group(1)}-{match.group(2)}-01"
    match = re.match(r"^(\d{4})-(\d{2})-(\d{2})$", text)
    if match:
        return text
    match = re.match(r"^(\d{4})$", text)
    if match:
        return f"{text}-01-01"
    return None


def _imf_sdmx_rows(session: requests.Session, dataflow: str, series_key: str) -> list[dict[str, str]]:
    cache_key = (dataflow, series_key)
    with IMF_SDMX_LOCK:
        cached = IMF_SDMX_CACHE.get(cache_key)
    if cached is not None:
        return cached

    response = session.get(
        f"{IMF_SDMX_BASE}/{dataflow}/{series_key}",
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "application/vnd.sdmx.data+csv;version=1.0.0",
        },
        timeout=(5, 120),
    )
    response.raise_for_status()
    rows = list(csv.DictReader(io.StringIO(response.text)))
    with IMF_SDMX_LOCK:
        IMF_SDMX_CACHE[cache_key] = rows
    return rows


def fetch_imf_sdmx(session: requests.Session, spec: dict[str, Any]) -> dict[str, Any]:
    """Fetch one fully-qualified IMF SDMX 2.1 series key as observations."""
    dataflow = str(spec["dataflow"])
    series_key = str(spec["series"])
    rows = _imf_sdmx_rows(session, dataflow, series_key)

    observations: list[dict[str, Any]] = []
    for row in rows:
        raw_value = row.get("OBS_VALUE")
        if raw_value in (None, "", "."):
            continue
        obs_date = _sdmx_period_to_date(str(row.get("TIME_PERIOD", "")))
        if not obs_date:
            continue
        try:
            observations.append({"date": obs_date, "value": float(raw_value)})
        except (TypeError, ValueError):
            continue
    observations.sort(key=lambda item: item["date"])

    start_date = str(spec.get("start_date") or "")
    if start_date:
        observations = [item for item in observations if item["date"] >= start_date]
    if not observations:
        raise RuntimeError(f"IMF SDMX returned no observations for {dataflow}/{series_key}.")

    provider_updated = ""
    for row in rows:
        candidate = str(row.get("UPDATE_DATE") or row.get("PUBLICATION_DATE") or "").strip()
        if candidate:
            provider_updated = candidate[:10]
            break
    return {
        **spec,
        "observations": observations,
        "provider_updated": provider_updated or observations[-1]["date"],
        "api_url": f"{IMF_SDMX_BASE}/{dataflow}/{series_key}",
    }


def fetch_imf_datamapper(session: requests.Session, spec: dict[str, Any]) -> dict[str, Any]:
    """Fetch one IMF WEO DataMapper indicator for a single ISO3 country."""
    code = str(spec["series"])
    iso3 = str(spec.get("country_iso3") or "JPN")
    url = f"{IMF_DATAMAPPER_BASE}/{code}/{iso3}"
    # imf.org answers 403 to the browser User-Agent the other endpoints require,
    # so this call deliberately sends the default requests headers.
    response = session.get(url, timeout=(5, 45))
    response.raise_for_status()
    payload = response.json()
    country_values = ((payload.get("values") or {}).get(code) or {}).get(iso3) or {}
    observations = [
        {"date": str(year), "value": float(value)}
        for year, value in country_values.items()
        if value is not None and str(year).isdigit()
    ]
    observations.sort(key=lambda item: int(item["date"]))
    if not observations:
        raise RuntimeError(f"IMF DataMapper returned no observations for {code}/{iso3}.")
    return {
        **spec,
        "observations": observations,
        "provider_updated": datetime.now(UTC).date().isoformat(),
        "api_url": url,
    }


def apply_scale(series: dict[str, Any]) -> dict[str, Any]:
    """Divide observations by ``spec['scale']`` so units read as bn/mn, not raw."""
    try:
        scale = float(series.get("scale") or 0)
    except (TypeError, ValueError):
        return series
    observations = series.get("observations") or []
    if scale in (0.0, 1.0) or not observations:
        return series
    return {
        **series,
        "observations": [
            {**item, "value": float(item["value"]) / scale} for item in observations
        ],
    }


def _fetch_one(spec: dict[str, Any]) -> dict[str, Any]:
    session = requests.Session()

    def operation() -> dict[str, Any]:
        fetcher = spec.get("fetcher")
        if fetcher == "fred":
            return _apply_transform(apply_scale(fetch_fred_us(session, spec)))
        if fetcher == "imf_sdmx":
            return _apply_transform(fetch_imf_sdmx(session, spec))
        if fetcher == "imf_datamapper":
            return _apply_transform(fetch_imf_datamapper(session, spec))
        raise ValueError(f"Unknown fetcher: {fetcher}")

    try:
        series = guarded_source_call(
            country=COUNTRY_CODE,
            indicator_id=str(spec.get("id") or "unknown"),
            source_id=str(spec.get("fetcher") or "unknown"),
            operation=operation,
        )
    except Exception as exc:  # noqa: BLE001 - structured degradation is intentional.
        series = failure_series(spec, exc)
    return validate_series(series)


def fetch_all(config: dict[str, Any]) -> list[dict[str, Any]]:
    specs = list(config.get("indicators", []))
    series_list: list[dict[str, Any] | None] = [None] * len(specs)
    # A small pool keeps FRED and the IMF SDMX gateway from throttling during a
    # full-site build while still being much faster than serial IO.
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = {executor.submit(_fetch_one, spec): index for index, spec in enumerate(specs)}
        for future in as_completed(futures):
            index = futures[future]
            spec = specs[index]
            try:
                series_list[index] = future.result()
            except Exception as exc:  # noqa: BLE001
                series_list[index] = validate_series({
                    **spec,
                    "observations": [],
                    "quality_status": "unavailable",
                    "quality_notes": [f"Fetch failed: {exc}"],
                })
    unavailable_indexes = [
        index
        for index, item in enumerate(series_list)
        if item is not None and item.get("quality_status") == "unavailable"
    ]
    for index in unavailable_indexes:
        # Retry tail failures sequentially so transient provider issues do not
        # get recorded as genuine missing-series gaps.
        for _ in range(2):
            retry = _fetch_one(specs[index])
            if retry.get("quality_status") != "unavailable":
                series_list[index] = retry
                break
    return [item for item in series_list if item is not None]


def _render_cards(series_list: list[dict[str, Any]]) -> str:
    headline_ids = [
        "real_gdp_yoy",
        "cpi_inflation",
        "unemployment_rate",
        "policy_rate",
        "usd_jpy",
        "government_debt_gdp",
    ]
    by_id = {item["id"]: item for item in series_list}
    cards: list[str] = []
    for indicator_id in headline_ids:
        series = by_id.get(indicator_id)
        latest = _latest(series) if series else None
        if not series or not latest:
            continue
        cards.append(f"""
<div class="data-card">
  <span><span data-lang="en">{escape(series['label_en'])}</span><span data-lang="zh">{escape(series['label_zh'])}</span></span>
  <strong>{_format_value(float(latest['value']), series.get('unit', ''))}</strong>
  <small>{escape(str(latest['date']))} · {escape(series.get('source_name', ''))}</small>
</div>""")
    return "\n".join(cards)


def _key_series_latest(series_list: list[dict[str, Any]], indicator_ids: list[str]) -> list[dict[str, Any]]:
    by_id = {item["id"]: item for item in series_list}
    rows: list[dict[str, Any]] = []
    for indicator_id in indicator_ids:
        series = by_id.get(indicator_id)
        latest = _latest(series) if series else None
        if not series or not latest:
            continue
        unit = str(series.get("unit", ""))
        value = float(latest["value"])
        rows.append({
            "id": indicator_id,
            "label_en": series.get("label_en", indicator_id),
            "label_zh": series.get("label_zh", indicator_id),
            "latest_date": str(latest["date"]),
            "latest_value": value,
            "latest_display": f"{_format_value(value, unit)} {unit}".strip(),
            "frequency": series.get("frequency", ""),
            "source_name": series.get("source_name", ""),
            "series": series.get("series", ""),
            "quality_status": series.get("quality_status", ""),
        })
    return rows


def render_html(config: dict[str, Any], series_list: list[dict[str, Any]]) -> str:
    chart_count = sum(1 for item in series_list if item.get("observations"))
    source_count = len({item.get("source_name") for item in series_list if item.get("observations")})
    gap_count = len(config.get("data_gaps", []))
    low_count = sum(1 for item in series_list if item.get("quality_status") == "low_confidence" and item.get("observations"))
    generated_date = datetime.now(UTC).date().isoformat()
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Japan Dashboard</title>
<script src="https://cdn.plot.ly/plotly-2.32.0.min.js"></script>
<style>{CSS}</style>
</head>
<body data-dashboard-view="core">
<div class="topbar">
  <a href="../index.html" style="text-decoration:none;color:inherit;"><div class="brand">East Meridian <span>/ Macro Dashboard</span></div></a>
  <nav class="country-nav" aria-label="country dashboards">
    <a href="hungary.html">HU</a>
    <a href="poland.html">PL</a>
    <a href="czechia.html">CZ</a>
    <a href="romania.html">RO</a>
    <a href="china.html">CN</a>
    <a href="japan.html" class="active">JP</a>
    <a href="south_africa.html">ZA</a>
    <a href="uk.html">UK</a>
    <a href="us.html">US</a>
  </nav>
  <button class="lang-toggle" onclick="toggleLang()" id="lang-btn">中文</button>
</div>

<main class="container">
  <header>
    <h1><span data-lang="en">Japan Dashboard</span><span data-lang="zh">日本 Dashboard</span></h1>
    <p class="subtitle"><span data-lang="en">A chart-and-data-first Japan macro page built on the same nine-pillar comparable core as the other country dashboards. Because OECD discontinued several of its Japan mirrors, national CPI and bank soundness come from the IMF SDMX API rather than FRED, and Japan-native releases that need e-Stat credentials are recorded as explicit gaps.</span><span data-lang="zh">一个以图表和数据为核心的日本宏观页面，采用与其他国家看板一致的九支柱可比核心框架。由于OECD停更了部分日本镜像序列，全国CPI与银行稳健指标改用IMF SDMX接口而非FRED；需要e-Stat凭证的日本本土数据则明确列为缺口。</span></p>
    <div class="meta-row">
      <span class="meta-chip">{chart_count} <span data-lang="en">charts</span><span data-lang="zh">张图</span></span>
      <span class="meta-chip">{source_count} <span data-lang="en">public source groups</span><span data-lang="zh">组公开来源</span></span>
      <span class="meta-chip">{gap_count} <span data-lang="en">official/vendor gaps tracked</span><span data-lang="zh">个官方/供应商缺口</span></span>
      <span class="meta-chip">{low_count} <span data-lang="en">low-confidence charts</span><span data-lang="zh">张低置信图</span></span>
    </div>
  </header>

  <section class="data-grid" aria-label="latest data cards">
    {_render_cards(series_list)}
  </section>

  <nav class="toc" aria-label="section navigation">
    {_section_nav(config)}
  </nav>

  <div class="view-switch" role="group" aria-label="chart density">
    <span><span data-lang="en">Chart view</span><span data-lang="zh">图表视图</span></span>
    <button type="button" data-view-option="core" aria-pressed="true" onclick="setDashboardView('core')"><span data-lang="en">Core 48</span><span data-lang="zh">核心 48</span></button>
    <button type="button" data-view-option="deep" aria-pressed="false" onclick="setDashboardView('deep')"><span data-lang="en">All deep-dive charts</span><span data-lang="zh">全部深度指标</span></button>
  </div>

  <div class="data-note">
    <span data-lang="en">Data policy: no fabricated proxies. FRED is the durable public backbone for national accounts, production, labour, trade, rates, and BIS series; the IMF SDMX API supplies national CPI and Financial Soundness Indicators where the OECD mirror was discontinued. Derived charts such as year-over-year growth are computed directly from the cited source series.</span>
    <span data-lang="zh">数据原则：不制造假proxy。国民账户、生产、劳动力、贸易、利率与BIS序列以FRED为稳定公开骨架；在OECD镜像停更之处，由IMF SDMX接口提供全国CPI与金融稳健指标。同比等派生图直接由标注的原始序列计算。</span>
  </div>

  {_sections_html(config, series_list, COUNTRY_CODE)}

  <section class="panel" id="data-gaps">
    <div class="section-title">
      <p>Pipeline</p>
      <h2><span data-lang="en">Official Data Gaps</span><span data-lang="zh">官方数据缺口</span></h2>
      <div class="logic"><span data-lang="en">These are framework indicators that matter for Japan macro work but are not yet rendered because a reproducible public adapter or license-safe source has not been validated.</span><span data-lang="zh">这些是框架中对日本宏观研究重要的指标，但由于尚未验证可复跑公开adapter或授权安全数据源，当前暂不渲染为图。</span></div>
    </div>
    <table class="gaps-table">
      <thead><tr><th>Section</th><th>Indicator family</th><th>Status</th></tr></thead>
      <tbody>{_gaps_html(config)}</tbody>
    </table>
  </section>

  <footer class="page-footer">
    <span data-lang="en">Research artefact only, not investment advice. Generated {generated_date} from <code>config/japan_indicators.yaml</code>.</span>
    <span data-lang="zh">仅为研究工具，不构成投资建议。生成日期 {generated_date}，配置来源 <code>config/japan_indicators.yaml</code>。</span>
  </footer>
</main>

<script>
function resizeCharts() {{
  if (!window.Plotly) return;
  document.querySelectorAll('.plotly-chart').forEach(function(el) {{
    Plotly.Plots.resize(el);
  }});
}}
function setDashboardView(view) {{
  var normalized = view === 'deep' ? 'deep' : 'core';
  document.body.dataset.dashboardView = normalized;
  localStorage.setItem('cp-dashboard-view', normalized);
  document.querySelectorAll('[data-view-option]').forEach(function(btn) {{
    btn.setAttribute('aria-pressed', String(btn.dataset.viewOption === normalized));
  }});
  requestAnimationFrame(resizeCharts);
}}
(function() {{
  var saved = localStorage.getItem('cp-lang');
  if (saved === 'zh') {{
    document.documentElement.lang = 'zh';
    document.getElementById('lang-btn').textContent = 'English';
  }}
  setDashboardView(localStorage.getItem('cp-dashboard-view') || 'core');
  requestAnimationFrame(resizeCharts);
}})();
function toggleLang() {{
  var html = document.documentElement;
  var btn = document.getElementById('lang-btn');
  if (html.lang === 'en') {{
    html.lang = 'zh';
    btn.textContent = 'English';
    localStorage.setItem('cp-lang', 'zh');
  }} else {{
    html.lang = 'en';
    btn.textContent = '中文';
    localStorage.setItem('cp-lang', 'en');
  }}
  requestAnimationFrame(resizeCharts);
}}
window.addEventListener('resize', resizeCharts);
</script>
</body>
</html>
"""


def _index_card(summary: dict[str, Any]) -> str:
    return f"""
  <!-- JP dashboard card -->
  <a href="japan.html" class="card clean">
    <div class="card-kicker">JPY · BoJ · Japan comparable-core page</div>
    <h2>Japan</h2>
    <div class="stats">
      <div class="stat"><span>Rendered charts</span><strong>{summary['charts']}</strong></div>
      <div class="stat"><span>Proxy fills</span><strong>0</strong></div>
      <div class="stat"><span>Data gaps tracked</span><strong>{summary['data_gaps']}</strong></div>
      <div class="stat"><span>Call rate</span><strong>{escape(summary.get('policy_rate_latest', 'n/a'))}</strong></div>
      <div class="stat"><span>Source groups</span><strong>{summary['source_groups']}</strong></div>
      <div class="stat"><span>Framework</span><strong>Nine-pillar comparable core</strong></div>
    </div>
  </a>
  <!-- /JP dashboard card -->"""


def inject_output_index(summary: dict[str, Any]) -> None:
    index_path = OUTPUT / "index.html"
    if not index_path.exists():
        return
    html = index_path.read_text()
    html = re.sub(r"\n\s*<!-- JP dashboard card -->.*?<!-- /JP dashboard card -->", "", html, flags=re.S)
    marker = '  </section>\n  <nav class="links"'
    if marker in html:
        html = html.replace(marker, _index_card(summary) + "\n  </section>\n  <nav class=\"links\"", 1)
    html = re.sub(r"Macro Dashboard Archive · CEE-4 v4 \+ China[^<]*", "Macro Dashboard Archive · CEE-4 v4 + China + Japan + South Africa + UK + US", html)
    html = re.sub(
        r"Generated archive entry for the proxy-free CEE-4 dashboards plus the [^.]*\.",
        "Generated archive entry for the proxy-free CEE-4 dashboards plus the China, Japan, South Africa, UK, and US data-first pages.",
        html,
    )
    html = html.replace("<strong>7</strong><span>country dashboards</span>", "<strong>8</strong><span>country dashboards</span>")
    _write_clean(index_path, html)



def build(data_mode: str | None = None) -> Path:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    data_mode = (data_mode or os.environ.get("COUNTRY_PRIMER_DATA_MODE") or "refresh").strip().lower()
    config = _load_config()
    if data_mode == "snapshot":
        series_list = load_canonical_data_first_frame(CANONICAL_JSON, config)
    else:
        SOURCE_HEALTH.reset()
        series_list = fetch_all(config)
        series_list = retain_last_known_good_series(series_list, CANONICAL_JSON, config)
    apply_quality_assessments(series_list)
    charted = [item for item in series_list if item.get("observations")]
    min_chart_count = int(config.get("min_chart_count", 34))
    if len(charted) < min_chart_count:
        unavailable = [item["id"] for item in series_list if not item.get("observations")]
        raise RuntimeError(
            f"Japan dashboard fetched only {len(charted)} charts, below minimum {min_chart_count}. "
            "Set FRED_API_KEY for the official API path or retry later. "
            f"Unavailable indicators: {', '.join(unavailable[:12])}"
            f"{'...' if len(unavailable) > 12 else ''}"
        )
    _write_clean(OUT_HTML, render_html(config, series_list))

    policy_rate = next((item for item in charted if item["id"] == "policy_rate"), None)
    policy_latest = _latest(policy_rate) if policy_rate else None
    summary = {
        "file": OUT_HTML.name,
        "generated": datetime.now(UTC).isoformat(),
        "charts": len(charted),
        "source_groups": len({item.get("source_name") for item in charted}),
        "data_gaps": len(config.get("data_gaps", [])),
        "low_confidence": sum(1 for item in charted if item.get("quality_status") == "low_confidence"),
        "policy_rate_latest": (
            f"{float(policy_latest['value']):.2f}% ({policy_latest['date']})" if policy_latest else "n/a"
        ),
        "key_series_latest": _key_series_latest(charted, SUMMARY_KEY_IDS),
        "unavailable": [item["id"] for item in series_list if not item.get("observations")],
        "data_mode": data_mode,
    }
    summary["canonical_frame"] = (
        canonical_frame_metadata(CANONICAL_JSON)
        if data_mode == "snapshot"
        else write_canonical_data_first_frame(CANONICAL_JSON, COUNTRY_CODE, series_list)
    )
    summary.update(build_summary_metadata(config, series_list, COUNTRY_CODE))
    SUMMARY_JSON.write_text(json.dumps(summary, indent=2, ensure_ascii=False))
    if data_mode != "snapshot":
        write_source_health_report(OUTPUT / "source_health.json", [COUNTRY_CODE])
    inject_output_index(summary)
    if not os.environ.get("COUNTRY_PRIMER_SKIP_ARCHIVE"):
        from build_dashboard_archive import build_archive
        build_archive()
    return OUT_HTML


if __name__ == "__main__":
    path = build()
    print(f"Wrote {path} ({path.stat().st_size:,} bytes)")
