"""Build the US macro dashboard from GS US-statistics-aligned config.

The US page follows the chapter logic of Goldman Sachs' Understanding US
Economic Statistics, while modernizing the policy/financial plumbing for 2026.
FRED is the public data backbone. If FRED_API_KEY is set, the official FRED API
is used; otherwise the script falls back to FRED's public graph CSV endpoint.
"""
from __future__ import annotations

import json
import csv
import io
import os
import re
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from html import escape
from pathlib import Path
from typing import Any

import requests
import yaml

from build_china_dashboard import (  # Reuse the data-first page shell.
    CSS,
    _format_value,
    _gaps_html,
    _latest,
    _section_nav,
    _sections_html,
    _write_clean,
)
from build_uk_dashboard import FRED_API_URL, FRED_GRAPH_URL, fetch_fred, validate_series


ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "config" / "us_indicators.yaml"
OUTPUT = ROOT / "output"
OUT_HTML = OUTPUT / "us_2026Q2_v1.html"
SUMMARY_JSON = OUTPUT / "us_dashboard_summary.json"
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 Chrome/124.0 Safari/537.36"
)
TREASURY_AUCTIONS_URL = "https://api.fiscaldata.treasury.gov/services/api/fiscal_service/v1/accounting/od/auctions_query"
BLS_API_URL = "https://api.bls.gov/publicAPI/v2/timeseries/data/"
BLS_BED_CACHE_PATH = ROOT / "data" / "us_bls_bed_cache.json"
BLS_LOCK = threading.Lock()
BLS_CACHE: dict[str, list[dict[str, Any]]] = {}
BLS_BATCH_ERROR: str | None = None


def _load_config() -> dict[str, Any]:
    return yaml.safe_load(CONFIG_PATH.read_text()) or {}


def _lag_for_frequency(frequency: str) -> int:
    frequency = str(frequency or "").lower()
    if frequency == "weekly":
        return 52
    if frequency == "quarterly":
        return 4
    if frequency == "annual":
        return 1
    return 12


def _apply_transform(series: dict[str, Any]) -> dict[str, Any]:
    transform = series.get("transform")
    observations = list(series.get("observations") or [])
    if not transform or not observations:
        return series

    transformed: list[dict[str, Any]] = []
    if transform == "yoy_pct":
        lag = _lag_for_frequency(str(series.get("frequency", "")))
        for index, item in enumerate(observations):
            if index < lag:
                continue
            base = float(observations[index - lag]["value"])
            value = float(item["value"])
            if base == 0:
                continue
            transformed.append({"date": item["date"], "value": ((value / base) - 1.0) * 100.0})
    elif transform == "diff":
        for index, item in enumerate(observations):
            if index == 0:
                continue
            transformed.append({
                "date": item["date"],
                "value": float(item["value"]) - float(observations[index - 1]["value"]),
            })
    elif transform == "pct_change":
        for index, item in enumerate(observations):
            if index == 0:
                continue
            base = float(observations[index - 1]["value"])
            value = float(item["value"])
            if base == 0:
                continue
            transformed.append({"date": item["date"], "value": ((value / base) - 1.0) * 100.0})
    else:
        return {
            **series,
            "observations": [],
            "quality_status": "unavailable",
            "quality_notes": [f"Unknown transform: {transform}."],
        }
    return {**series, "observations": transformed}


def _fred_graph_observations_us(session: requests.Session, spec: dict[str, Any], read_timeout: int) -> tuple[list[dict[str, Any]], str]:
    params = {"id": spec["series"]}
    if spec.get("start_date"):
        params["cosd"] = spec["start_date"]
    response = session.get(
        FRED_GRAPH_URL,
        params=params,
        headers={"User-Agent": USER_AGENT, "Accept": "text/csv,text/plain,*/*"},
        timeout=(5, read_timeout),
    )
    response.raise_for_status()
    rows = csv.DictReader(io.StringIO(response.text))
    observations: list[dict[str, Any]] = []
    for row in rows:
        raw_value = row.get(spec["series"])
        if raw_value in (None, "", "."):
            continue
        try:
            value = float(raw_value)
        except (TypeError, ValueError):
            continue
        observations.append({"date": str(row.get("observation_date")), "value": value})
    updated = response.headers.get("Last-Modified", "")
    return observations, updated


def fetch_fred_us(session: requests.Session, spec: dict[str, Any]) -> dict[str, Any]:
    if os.environ.get("FRED_API_KEY", "").strip():
        return fetch_fred(session, spec)

    last_error: Exception | None = None
    for read_timeout in (8, 16):
        try:
            observations, provider_updated = _fred_graph_observations_us(session, spec, read_timeout)
            if not observations:
                raise RuntimeError("FRED graph returned no observations.")
            if provider_updated:
                try:
                    provider_updated = parsedate_to_datetime(provider_updated).date().isoformat()
                except (TypeError, ValueError):
                    provider_updated = str(provider_updated)
            return {
                **spec,
                "observations": observations,
                "provider_updated": provider_updated or (observations[-1]["date"] if observations else ""),
                "api_url": FRED_GRAPH_URL,
            }
        except Exception as exc:  # noqa: BLE001 - retry with a larger read timeout.
            last_error = exc
    raise last_error or RuntimeError("FRED graph fetch failed.")


def _numeric(value: Any) -> float | None:
    if value in (None, "", "null", "."):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _bls_period_to_date(year: str, period: str) -> str | None:
    if not period.startswith("Q"):
        return None
    quarter_month = {
        "Q01": "01",
        "Q02": "04",
        "Q03": "07",
        "Q04": "10",
    }.get(period)
    if not quarter_month:
        return None
    return f"{year}-{quarter_month}-01"


def _bls_config_specs() -> list[dict[str, Any]]:
    config = _load_config()
    return [item for item in config.get("indicators", []) if item.get("fetcher") == "bls_api"]


def _load_bls_bed_cache() -> dict[str, Any]:
    if not BLS_BED_CACHE_PATH.exists():
        return {}
    try:
        return json.loads(BLS_BED_CACHE_PATH.read_text())
    except json.JSONDecodeError:
        return {}


def _write_bls_bed_cache(observations_by_series: dict[str, list[dict[str, Any]]]) -> None:
    if not observations_by_series or any(not values for values in observations_by_series.values()):
        return
    BLS_BED_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "generated": datetime.now(UTC).isoformat(),
        "source": "BLS public API last-good cache for Business Employment Dynamics series",
        "source_url": BLS_API_URL,
        "series": observations_by_series,
    }
    BLS_BED_CACHE_PATH.write_text(json.dumps(payload, indent=2, sort_keys=True))


def _fetch_bls_batch(session: requests.Session, specs: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    start_year = min(int(str(item.get("start_date", "1992-01-01"))[:4]) for item in specs)
    end_year = datetime.now(UTC).year
    series_ids = sorted({str(item["series"]) for item in specs})
    registration_key = os.environ.get("BLS_API_KEY", "").strip()
    observations_by_series: dict[str, dict[str, float]] = {series_id: {} for series_id in series_ids}

    # BLS public API range limits are tighter without a registration key. Keep
    # the unregistered path conservative so automated refreshes do not drop BED.
    chunk_years = 20 if registration_key else 10
    for chunk_start in range(start_year, end_year + 1, chunk_years):
        chunk_end = min(chunk_start + chunk_years - 1, end_year)
        payload_body: dict[str, Any] = {
            "seriesid": series_ids,
            "startyear": str(chunk_start),
            "endyear": str(chunk_end),
        }
        if registration_key:
            payload_body["registrationkey"] = registration_key

        last_error: Exception | None = None
        for attempt in range(3):
            try:
                response = session.post(
                    BLS_API_URL,
                    json=payload_body,
                    headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
                    timeout=(5, 30),
                )
                response.raise_for_status()
                payload = response.json()
                if payload.get("status") != "REQUEST_SUCCEEDED":
                    raise RuntimeError("; ".join(payload.get("message") or ["BLS API request failed."]))
                break
            except Exception as exc:  # noqa: BLE001 - retry transient BLS throttling/transport failures.
                last_error = exc
                if attempt < 2:
                    time.sleep(1.0 * (2 ** attempt))
        else:
            raise last_error or RuntimeError("BLS API request failed.")

        for series_payload in payload.get("Results", {}).get("series") or []:
            series_id = str(series_payload.get("seriesID", ""))
            if series_id not in observations_by_series:
                continue
            bucket = observations_by_series[series_id]
            for row in series_payload.get("data") or []:
                obs_date = _bls_period_to_date(str(row.get("year", "")), str(row.get("period", "")))
                value = _numeric(row.get("value"))
                if not obs_date or value is None:
                    continue
                bucket[obs_date] = value
        time.sleep(0.25)

    result = {
        series_id: [
            {"date": obs_date, "value": value}
            for obs_date, value in sorted(values.items())
        ]
        for series_id, values in observations_by_series.items()
    }
    _write_bls_bed_cache(result)
    return result


def fetch_bls_api(session: requests.Session, spec: dict[str, Any]) -> dict[str, Any]:
    global BLS_BATCH_ERROR

    series_id = str(spec["series"])
    with BLS_LOCK:
        if series_id not in BLS_CACHE and not BLS_BATCH_ERROR:
            try:
                BLS_CACHE.update(_fetch_bls_batch(session, _bls_config_specs()))
            except Exception as exc:  # noqa: BLE001 - preserve one failure for all BLS specs in this run.
                BLS_BATCH_ERROR = str(exc)
        if BLS_BATCH_ERROR:
            cache_payload = _load_bls_bed_cache()
            observations = list((cache_payload.get("series") or {}).get(series_id) or [])
            if observations:
                cache_date = str(cache_payload.get("generated") or "")[:10]
                caveat_en = (
                    str(spec.get("caveat_en") or "").rstrip()
                    + " Live BLS API quota was unavailable in this run; rendering the last-good official BED cache."
                ).strip()
                caveat_zh = (
                    str(spec.get("caveat_zh") or "").rstrip()
                    + " 本次运行BLS实时API额度不可用；当前渲染最近一次验证成功的官方BED缓存。"
                ).strip()
                return {
                    **spec,
                    "observations": observations,
                    "provider_updated": cache_date or observations[-1]["date"],
                    "api_url": BLS_API_URL,
                    "caveat_en": caveat_en,
                    "caveat_zh": caveat_zh,
                }
            raise RuntimeError(BLS_BATCH_ERROR)
        observations = list(BLS_CACHE.get(series_id) or [])

    start_date = str(spec.get("start_date", ""))
    if start_date:
        observations = [item for item in observations if str(item["date"]) >= start_date]

    if not observations:
        raise RuntimeError(f"BLS API returned no observations for {series_id}.")
    return {
        **spec,
        "observations": observations,
        "provider_updated": observations[-1]["date"],
        "api_url": BLS_API_URL,
    }


def fetch_treasury_auctions(session: requests.Session, spec: dict[str, Any]) -> dict[str, Any]:
    fields = [
        "auction_date",
        "security_type",
        "total_accepted",
        "total_tendered",
        "bid_to_cover_ratio",
        "high_yield",
        "high_investment_rate",
    ]
    filters = [f"auction_date:gte:{spec.get('start_date', '2018-01-01')}", "total_accepted:gt:0"]
    security_types = list(spec.get("security_types") or [])
    if len(security_types) == 1:
        filters.append(f"security_type:eq:{security_types[0]}")
    elif security_types:
        filters.append(f"security_type:in:({','.join(security_types)})")

    rows: list[dict[str, Any]] = []
    page_number = 1
    total_pages = 1
    while page_number <= total_pages:
        response = session.get(
            TREASURY_AUCTIONS_URL,
            params={
                "fields": ",".join(fields),
                "filter": ",".join(filters),
                "page[size]": int(spec.get("page_size", 5000)),
                "page[number]": page_number,
                "sort": "auction_date",
            },
            headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
            timeout=(5, 30),
        )
        response.raise_for_status()
        payload = response.json()
        rows.extend(payload.get("data") or [])
        total_pages = int(payload.get("meta", {}).get("total-pages") or page_number)
        page_number += 1

    aggregate = str(spec.get("aggregate", "monthly_sum"))
    metric = str(spec.get("metric", "total_accepted"))
    scale = float(spec.get("scale", 1))
    buckets: dict[str, dict[str, float]] = {}
    for row in rows:
        auction_date = str(row.get("auction_date") or "")
        if len(auction_date) < 7:
            continue
        month = f"{auction_date[:7]}-01"
        bucket = buckets.setdefault(month, {"value": 0.0, "count": 0.0, "numerator": 0.0, "denominator": 0.0})
        if aggregate == "monthly_weighted_bid_to_cover":
            numerator = _numeric(row.get("total_tendered"))
            denominator = _numeric(row.get("total_accepted"))
            if numerator is None or denominator in (None, 0):
                continue
            bucket["numerator"] += numerator
            bucket["denominator"] += denominator
        else:
            value = _numeric(row.get(metric))
            if value is None:
                continue
            bucket["value"] += value
            bucket["count"] += 1

    observations: list[dict[str, Any]] = []
    for month, bucket in sorted(buckets.items()):
        if aggregate == "monthly_weighted_bid_to_cover":
            denominator = bucket["denominator"]
            if denominator == 0:
                continue
            value = bucket["numerator"] / denominator
        elif aggregate == "monthly_average":
            count = bucket["count"]
            if count == 0:
                continue
            value = bucket["value"] / count
        else:
            value = bucket["value"]
        observations.append({"date": month, "value": value / scale})

    if not observations:
        raise RuntimeError("Treasury FiscalData returned no completed auction observations.")
    return {
        **spec,
        "observations": observations,
        "provider_updated": observations[-1]["date"],
        "api_url": TREASURY_AUCTIONS_URL,
    }


def _fetch_one(spec: dict[str, Any]) -> dict[str, Any]:
    session = requests.Session()
    try:
        if spec.get("fetcher") == "fred":
            series = _apply_transform(fetch_fred_us(session, spec))
        elif spec.get("fetcher") == "bls_api":
            series = fetch_bls_api(session, spec)
        elif spec.get("fetcher") == "treasury_auctions":
            series = fetch_treasury_auctions(session, spec)
        else:
            series = {**spec, "observations": [], "quality_status": "unavailable", "quality_notes": ["Unknown fetcher."]}
    except Exception as exc:  # noqa: BLE001 - data page should degrade instead of crashing.
        series = {
            **spec,
            "observations": [],
            "quality_status": "unavailable",
            "quality_notes": [f"Fetch failed: {exc}"],
        }
    return validate_series(series)


def fetch_all(config: dict[str, Any]) -> list[dict[str, Any]]:
    specs = list(config.get("indicators", []))
    series_list: list[dict[str, Any] | None] = [None] * len(specs)
    # FRED can throttle or drop bursts during full-site builds; a smaller pool
    # keeps automated refreshes reproducible while still much faster than serial IO.
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
        # Retry tail failures sequentially. This catches transient FRED/API
        # issues without hiding genuine missing-series gaps.
        for _ in range(2):
            retry = _fetch_one(specs[index])
            if retry.get("quality_status") != "unavailable":
                series_list[index] = retry
                break
    return [item for item in series_list if item is not None]


def _render_cards(series_list: list[dict[str, Any]]) -> str:
    headline_ids = [
        "real_gdp_growth",
        "nonfarm_payrolls_change",
        "unemployment_rate",
        "core_pce_inflation",
        "effective_fed_funds",
        "federal_debt_gdp",
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
<title>US Dashboard</title>
<script src="https://cdn.plot.ly/plotly-2.32.0.min.js"></script>
<style>{CSS}</style>
</head>
<body>
<div class="topbar">
  <a href="../index.html" style="text-decoration:none;color:inherit;"><div class="brand">East Meridian <span>/ Macro Dashboard</span></div></a>
  <nav class="country-nav" aria-label="country dashboards">
    <a href="hungary_2026Q2_v4.html">HU</a>
    <a href="poland_2026Q2_v4.html">PL</a>
    <a href="czechia_2026Q2_v4.html">CZ</a>
    <a href="romania_2026Q2_v4.html">RO</a>
    <a href="china_2026Q2_v1.html">CN</a>
    <a href="uk_2026Q2_v1.html">UK</a>
    <a href="us_2026Q2_v1.html" class="active">US</a>
  </nav>
  <button class="lang-toggle" onclick="toggleLang()" id="lang-btn">中文</button>
</div>

<main class="container">
  <header>
    <h1><span data-lang="en">US Dashboard</span><span data-lang="zh">美国 Dashboard</span></h1>
    <p class="subtitle"><span data-lang="en">A chart-and-data-first US macro page aligned to the GS <em>Understanding US Economic Statistics</em> framework, modernized for 2026 with FRED-backed public data, Fed policy plumbing, and explicit gaps for GS or vendor-controlled releases.</span><span data-lang="zh">一个以图表和数据为核心的美国宏观页面，结构对齐GS <em>Understanding US Economic Statistics</em> 框架，并面向2026年更新：使用FRED公开数据、现代美联储政策管道，并明确列出GS或供应商控制的数据缺口。</span></p>
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

  <div class="data-note">
    <span data-lang="en">Data policy: no fabricated proxies. FRED is the durable public backbone; if <code>FRED_API_KEY</code> is available, the official FRED API is used automatically. Derived charts such as year-over-year inflation or payroll change are computed directly from the cited FRED source series.</span>
    <span data-lang="zh">数据原则：不制造假proxy。FRED是稳定公开骨架；如果运行环境提供 <code>FRED_API_KEY</code>，脚本会自动使用FRED官方API。同比通胀、非农月度变化等派生图直接由标注的FRED原始序列计算。</span>
  </div>

  {_sections_html(config, series_list)}

  <section class="panel" id="data-gaps">
    <div class="section-title">
      <p>Pipeline</p>
      <h2><span data-lang="en">Official Data Gaps</span><span data-lang="zh">官方数据缺口</span></h2>
      <div class="logic"><span data-lang="en">These are GS-framework indicators that matter for US macro trading but are not yet rendered because a reproducible public adapter or license-safe source has not been validated.</span><span data-lang="zh">这些是GS框架中对美国宏观交易重要的指标，但由于尚未验证可复跑公开adapter或授权安全数据源，当前暂不渲染为图。</span></div>
    </div>
    <table class="gaps-table">
      <thead><tr><th>Section</th><th>Indicator family</th><th>Status</th></tr></thead>
      <tbody>{_gaps_html(config)}</tbody>
    </table>
  </section>

  <footer class="page-footer">
    <span data-lang="en">Research artefact only, not investment advice. Generated {generated_date} from <code>config/us_indicators.yaml</code>.</span>
    <span data-lang="zh">仅为研究工具，不构成投资建议。生成日期 {generated_date}，配置来源 <code>config/us_indicators.yaml</code>。</span>
  </footer>
</main>

<script>
function resizeCharts() {{
  if (!window.Plotly) return;
  document.querySelectorAll('.plotly-chart').forEach(function(el) {{
    Plotly.Plots.resize(el);
  }});
}}
(function() {{
  var saved = localStorage.getItem('cp-lang');
  if (saved === 'zh') {{
    document.documentElement.lang = 'zh';
    document.getElementById('lang-btn').textContent = 'English';
  }}
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
  <!-- US dashboard card -->
  <a href="us_2026Q2_v1.html" class="card clean">
    <div class="card-kicker">USD · Fed · US GS-statistics page</div>
    <h2>United States</h2>
    <div class="stats">
      <div class="stat"><span>Rendered charts</span><strong>{summary['charts']}</strong></div>
      <div class="stat"><span>Proxy fills</span><strong>0</strong></div>
      <div class="stat"><span>Data gaps tracked</span><strong>{summary['data_gaps']}</strong></div>
      <div class="stat"><span>Fed funds</span><strong>{escape(summary.get('fed_funds_latest', 'n/a'))}</strong></div>
      <div class="stat"><span>Source groups</span><strong>{summary['source_groups']}</strong></div>
      <div class="stat"><span>Framework</span><strong>GS US statistics logic</strong></div>
    </div>
  </a>
  <!-- /US dashboard card -->"""


def inject_output_index(summary: dict[str, Any]) -> None:
    index_path = OUTPUT / "index.html"
    if not index_path.exists():
        return
    html = index_path.read_text()
    html = re.sub(r"\n\s*<!-- US dashboard card -->.*?<!-- /US dashboard card -->", "", html, flags=re.S)
    marker = '  </section>\n  <nav class="links"'
    if marker in html:
        html = html.replace(marker, _index_card(summary) + "\n  </section>\n  <nav class=\"links\"", 1)
    html = re.sub(
        r"Macro Dashboard Archive · CEE-4 v4 \+ China(?: \+ UK)?(?: \+ US)*",
        "Macro Dashboard Archive · CEE-4 v4 + China + UK + US",
        html,
    )
    html = html.replace(
        "Generated archive entry for the proxy-free CEE-4 dashboards plus the China and UK data-first pages.",
        "Generated archive entry for the proxy-free CEE-4 dashboards plus the China, UK, and US data-first pages.",
    )
    html = html.replace("<strong>6</strong><span>country dashboards</span>", "<strong>7</strong><span>country dashboards</span>")
    _write_clean(index_path, html)


def inject_root_index(summary: dict[str, Any]) -> None:
    index_path = ROOT / "index.html"
    if not index_path.exists():
        return
    html = index_path.read_text()
    html = re.sub(
        r'(<a href="output/us_2026Q2_v1.html" class="card">.*?<span class="label">Charts</span><span class="value">)\d+(</span>)',
        rf"\g<1>{summary['charts']}\2",
        html,
        count=1,
        flags=re.S,
    )
    _write_clean(index_path, html)


def build() -> Path:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    config = _load_config()
    series_list = fetch_all(config)
    charted = [item for item in series_list if item.get("observations")]
    min_chart_count = int(config.get("min_chart_count", 55))
    if len(charted) < min_chart_count:
        unavailable = [item["id"] for item in series_list if not item.get("observations")]
        raise RuntimeError(
            f"US dashboard fetched only {len(charted)} charts, below minimum {min_chart_count}. "
            "Set FRED_API_KEY for the official API path or retry later. "
            f"Unavailable indicators: {', '.join(unavailable[:12])}"
            f"{'...' if len(unavailable) > 12 else ''}"
        )
    _write_clean(OUT_HTML, render_html(config, series_list))

    fed_funds = next((item for item in charted if item["id"] == "effective_fed_funds"), None)
    fed_latest = _latest(fed_funds) if fed_funds else None
    summary = {
        "file": OUT_HTML.name,
        "generated": datetime.now(UTC).isoformat(),
        "charts": len(charted),
        "source_groups": len({item.get("source_name") for item in charted}),
        "data_gaps": len(config.get("data_gaps", [])),
        "low_confidence": sum(1 for item in charted if item.get("quality_status") == "low_confidence"),
        "fed_funds_latest": (
            f"{float(fed_latest['value']):.2f}% ({fed_latest['date']})" if fed_latest else "n/a"
        ),
        "unavailable": [item["id"] for item in series_list if not item.get("observations")],
    }
    SUMMARY_JSON.write_text(json.dumps(summary, indent=2, ensure_ascii=False))
    inject_output_index(summary)
    inject_root_index(summary)
    if not os.environ.get("COUNTRY_PRIMER_SKIP_ARCHIVE"):
        from build_dashboard_archive import build_archive
        build_archive()
    return OUT_HTML


if __name__ == "__main__":
    path = build()
    print(f"Wrote {path} ({path.stat().st_size:,} bytes)")
