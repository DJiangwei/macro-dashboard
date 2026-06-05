"""Build the UK macro dashboard from GS UK-statistics-aligned config.

The UK page follows the logic of the Goldman Sachs UK statistics guide, but it
only renders reproducible public time series. FRED is the default public data
backbone. If FRED_API_KEY is set, the official FRED API is used; otherwise the
script falls back to FRED's public graph CSV endpoint.
"""
from __future__ import annotations

import csv
import io
import json
import os
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import UTC, date, datetime
from email.utils import parsedate_to_datetime
from html import escape
from pathlib import Path
from typing import Any

import requests
import yaml

from build_china_dashboard import (  # Reuse the data-first page shell.
    CSS,
    _chart_html,
    _format_value,
    _gaps_html,
    _json,
    _latest,
    _section_nav,
    _sections_html,
    _write_clean,
)


ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "config" / "uk_indicators.yaml"
OUTPUT = ROOT / "output"
OUT_HTML = OUTPUT / "uk_2026Q2_v1.html"
SUMMARY_JSON = OUTPUT / "uk_dashboard_summary.json"

FRED_GRAPH_URL = "https://fred.stlouisfed.org/graph/fredgraph.csv"
FRED_API_URL = "https://api.stlouisfed.org/fred/series/observations"
BOE_BANK_RATE_URL = "https://www.bankofengland.co.uk/boeapps/database/Bank-Rate.asp?hl=en-GB"
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 Chrome/124.0 Safari/537.36"
)


def _load_config() -> dict[str, Any]:
    return yaml.safe_load(CONFIG_PATH.read_text()) or {}


def _clean_text(value: str) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def _parse_date(value: str) -> date | None:
    value = str(value or "")
    for fmt, length in (("%Y-%m-%d", 10), ("%Y-%m", 7), ("%Y", 4)):
        try:
            return datetime.strptime(value[:length], fmt).date()
        except ValueError:
            continue
    return None


def _start_filter(observations: list[dict[str, Any]], start_date: str | None) -> list[dict[str, Any]]:
    if not start_date:
        return observations
    start = _parse_date(start_date)
    if not start:
        return observations
    return [item for item in observations if (_parse_date(str(item["date"])) or date.min) >= start]


def _fred_api_observations(session: requests.Session, spec: dict[str, Any]) -> tuple[list[dict[str, Any]], str]:
    api_key = os.environ.get("FRED_API_KEY", "").strip()
    if not api_key:
        return [], ""
    params = {
        "series_id": spec["series"],
        "api_key": api_key,
        "file_type": "json",
    }
    if spec.get("start_date"):
        params["observation_start"] = spec["start_date"]
    response = session.get(FRED_API_URL, params=params, timeout=(4, 12))
    response.raise_for_status()
    payload = response.json()
    observations: list[dict[str, Any]] = []
    for row in payload.get("observations", []):
        raw_value = row.get("value")
        if raw_value in (None, "", "."):
            continue
        try:
            value = float(raw_value)
        except (TypeError, ValueError):
            continue
        observations.append({"date": str(row.get("date")), "value": value})
    updated = response.headers.get("Last-Modified", "")
    return observations, updated


def _fred_graph_observations(session: requests.Session, spec: dict[str, Any]) -> tuple[list[dict[str, Any]], str]:
    params = {"id": spec["series"]}
    # FRED graph CSV accepts cosd/coed. This is important for very long UK rate
    # histories, where requesting the entire series can be slow.
    if spec.get("start_date"):
        params["cosd"] = spec["start_date"]
    response = session.get(FRED_GRAPH_URL, params=params, timeout=(4, 12))
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


def fetch_fred(session: requests.Session, spec: dict[str, Any]) -> dict[str, Any]:
    observations: list[dict[str, Any]]
    provider_updated: str
    try:
        observations, provider_updated = _fred_api_observations(session, spec)
    except Exception:  # noqa: BLE001 - API key may be absent/invalid; graph CSV is the durable fallback.
        observations, provider_updated = [], ""
    if not observations:
        observations, provider_updated = _fred_graph_observations(session, spec)
    observations = _start_filter(observations, spec.get("start_date"))
    if provider_updated:
        try:
            provider_updated = parsedate_to_datetime(provider_updated).date().isoformat()
        except (TypeError, ValueError):
            provider_updated = str(provider_updated)
    return {
        **spec,
        "observations": observations,
        "provider_updated": provider_updated or (observations[-1]["date"] if observations else ""),
        "api_url": FRED_API_URL if os.environ.get("FRED_API_KEY") else FRED_GRAPH_URL,
    }


def _parse_boe_short_date(value: str) -> str | None:
    try:
        dt = datetime.strptime(value, "%d %b %y").date()
    except ValueError:
        return None
    return dt.isoformat()


def fetch_boe_bank_rate(session: requests.Session, spec: dict[str, Any]) -> dict[str, Any]:
    response = session.get(
        BOE_BANK_RATE_URL,
        headers={"User-Agent": USER_AGENT, "Accept": "text/html,application/xhtml+xml"},
        timeout=(4, 12),
    )
    response.raise_for_status()
    rows = re.findall(r"<tr[^>]*>(.*?)</tr>", response.text, flags=re.S | re.I)
    observations: list[dict[str, Any]] = []
    for row in rows:
        cells = [
            _clean_text(re.sub(r"<[^>]+>", " ", cell))
            for cell in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", row, flags=re.S | re.I)
        ]
        if len(cells) < 2 or cells[0].lower().startswith("date"):
            continue
        obs_date = _parse_boe_short_date(cells[0])
        if not obs_date:
            continue
        try:
            value = float(cells[1].replace("%", ""))
        except ValueError:
            continue
        observations.append({"date": obs_date, "value": value})
    observations.sort(key=lambda item: item["date"])
    observations = _start_filter(observations, spec.get("start_date"))
    current_match = re.search(r'<p class="stat-figure">([^<]+)</p>', response.text)
    current_value = _clean_text(current_match.group(1)) if current_match else ""
    return {
        **spec,
        "observations": observations,
        "provider_updated": observations[-1]["date"] if observations else "",
        "api_url": BOE_BANK_RATE_URL,
        "current_value": current_value,
    }


def validate_series(series: dict[str, Any]) -> dict[str, Any]:
    observations = series.get("observations") or []
    notes: list[str] = []
    if not observations:
        return {**series, "quality_status": "unavailable", "quality_notes": ["No observations returned."]}
    if len(observations) < 12:
        notes.append("Short history.")

    latest_date = _parse_date(str(observations[-1]["date"]))
    frequency = str(series.get("frequency", "")).lower()
    if latest_date:
        age_days = (date.today() - latest_date).days
        if frequency == "monthly" and age_days > 150:
            notes.append(f"Monthly series looks stale; latest observation is {observations[-1]['date']}.")
        elif frequency == "quarterly" and age_days > 330:
            notes.append(f"Quarterly series looks stale; latest observation is {observations[-1]['date']}.")
        elif frequency == "annual" and latest_date.year < date.today().year - 2:
            notes.append(f"Lagged annual series; latest observation is {latest_date.year}.")
    else:
        notes.append("Latest date could not be parsed.")

    source_name = str(series.get("source_name", ""))
    if "FRED" in source_name:
        notes.append("FRED is used as a reproducible mirror; release-day work should check the native source.")
    if series.get("caveat_en"):
        notes.append(series["caveat_en"])

    quality_floor = str(series.get("quality_floor", ""))
    if quality_floor == "low_confidence":
        status = "low_confidence"
    elif not notes:
        status = "verified"
    elif len(notes) <= 2:
        status = "watch"
    else:
        status = "low_confidence"
    return {**series, "quality_status": status, "quality_notes": notes[:3]}


def _fetch_one(spec: dict[str, Any]) -> dict[str, Any]:
    session = requests.Session()
    try:
        fetcher = spec.get("fetcher")
        if fetcher == "fred":
            series = fetch_fred(session, spec)
        elif fetcher == "boe_bank_rate":
            series = fetch_boe_bank_rate(session, spec)
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
    with ThreadPoolExecutor(max_workers=6) as executor:
        futures = {executor.submit(_fetch_one, spec): index for index, spec in enumerate(specs)}
        for future in as_completed(futures):
            index = futures[future]
            spec = specs[index]
            try:
                series_list[index] = future.result()
            except Exception as exc:  # noqa: BLE001 - data page should degrade instead of crashing.
                series_list[index] = validate_series({
                    **spec,
                    "observations": [],
                    "quality_status": "unavailable",
                    "quality_notes": [f"Fetch failed: {exc}"],
                })
    return [item for item in series_list if item is not None]


def _render_cards(series_list: list[dict[str, Any]]) -> str:
    headline_ids = [
        "real_gdp_qoq",
        "cpi_yoy",
        "unemployment_rate",
        "bank_rate",
        "government_debt_gdp",
        "gbp_reer",
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
<title>UK Dashboard</title>
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
    <a href="uk_2026Q2_v1.html" class="active">UK</a>
  </nav>
  <button class="lang-toggle" onclick="toggleLang()" id="lang-btn">中文</button>
</div>

<main class="container">
  <header>
    <h1><span data-lang="en">UK Dashboard</span><span data-lang="zh">英国 Dashboard</span></h1>
    <p class="subtitle"><span data-lang="en">A chart-and-data-first UK macro page aligned to the GS <em>Understanding UK Economic Statistics</em> framework. The page prioritises reproducible public series from FRED/OECD/BIS/IMF and the Bank of England, while preserving vendor-controlled GS/PMI/CBI/RICS items as explicit data gaps.</span><span data-lang="zh">一个以图表和数据为核心的英国宏观页面，结构对齐GS <em>Understanding UK Economic Statistics</em> 框架。页面优先使用FRED/OECD/BIS/IMF与Bank of England的可复跑公开序列；GS、PMI、CBI、RICS等供应商控制指标则明确列为数据缺口。</span></p>
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
    <span data-lang="en">Data policy: no fabricated proxies. FRED is used as the durable, no-key public backbone; if <code>FRED_API_KEY</code> is available, the official FRED API is used automatically. BoE Bank Rate is fetched from the official Bank of England history table.</span>
    <span data-lang="zh">数据原则：不制造假proxy。FRED作为无需key的稳定公开骨架；如果运行环境提供 <code>FRED_API_KEY</code>，脚本会自动使用FRED官方API。BoE Bank Rate来自Bank of England官方历史表。</span>
  </div>

  {_sections_html(config, series_list)}

  <section class="panel" id="data-gaps">
    <div class="section-title">
      <p>Pipeline</p>
      <h2><span data-lang="en">Official Data Gaps</span><span data-lang="zh">官方数据缺口</span></h2>
      <div class="logic"><span data-lang="en">These are GS-framework indicators that matter for UK macro trading but are not yet rendered because a reproducible public adapter or license-safe source has not been validated.</span><span data-lang="zh">这些是GS框架中对英国宏观交易重要的指标，但由于尚未验证可复跑公开adapter或授权安全数据源，当前暂不渲染为图。</span></div>
    </div>
    <table class="gaps-table">
      <thead><tr><th>Section</th><th>Indicator family</th><th>Status</th></tr></thead>
      <tbody>{_gaps_html(config)}</tbody>
    </table>
  </section>

  <footer class="page-footer">
    <span data-lang="en">Research artefact only, not investment advice. Generated {generated_date} from <code>config/uk_indicators.yaml</code>.</span>
    <span data-lang="zh">仅为研究工具，不构成投资建议。生成日期 {generated_date}，配置来源 <code>config/uk_indicators.yaml</code>。</span>
  </footer>
</main>

<script>
(function() {{
  var saved = localStorage.getItem('cp-lang');
  if (saved === 'zh') {{
    document.documentElement.lang = 'zh';
    document.getElementById('lang-btn').textContent = 'English';
  }}
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
}}
</script>
</body>
</html>
"""


def _index_card(summary: dict[str, Any]) -> str:
    return f"""
  <!-- UK dashboard card -->
  <a href="uk_2026Q2_v1.html" class="card clean">
    <div class="card-kicker">GBP · BoE · UK GS-statistics page</div>
    <h2>United Kingdom</h2>
    <div class="stats">
      <div class="stat"><span>Rendered charts</span><strong>{summary['charts']}</strong></div>
      <div class="stat"><span>Proxy fills</span><strong>0</strong></div>
      <div class="stat"><span>Data gaps tracked</span><strong>{summary['data_gaps']}</strong></div>
      <div class="stat"><span>Bank Rate</span><strong>{escape(summary.get('bank_rate_latest', 'n/a'))}</strong></div>
      <div class="stat"><span>Source groups</span><strong>{summary['source_groups']}</strong></div>
      <div class="stat"><span>Framework</span><strong>GS UK statistics logic</strong></div>
    </div>
  </a>
  <!-- /UK dashboard card -->"""


def inject_output_index(summary: dict[str, Any]) -> None:
    index_path = OUTPUT / "index.html"
    if not index_path.exists():
        return
    html = index_path.read_text()
    html = re.sub(r"\n\s*<!-- UK dashboard card -->.*?<!-- /UK dashboard card -->", "", html, flags=re.S)
    marker = '  </section>\n  <nav class="links"'
    if marker in html:
        html = html.replace(marker, _index_card(summary) + "\n  </section>\n  <nav class=\"links\"", 1)
    html = re.sub(
        r"Macro Dashboard Archive · CEE-4 v4 \+ China(?: \+ UK)*",
        "Macro Dashboard Archive · CEE-4 v4 + China + UK",
        html,
    )
    html = html.replace(
        "Generated archive entry for the proxy-free CEE-4 dashboards plus the China data-first page.",
        "Generated archive entry for the proxy-free CEE-4 dashboards plus the China and UK data-first pages.",
    )
    html = html.replace("<strong>5</strong><span>country dashboards</span>", "<strong>6</strong><span>country dashboards</span>")
    _write_clean(index_path, html)


def build() -> Path:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    config = _load_config()
    series_list = fetch_all(config)
    _write_clean(OUT_HTML, render_html(config, series_list))

    charted = [item for item in series_list if item.get("observations")]
    bank_rate = next((item for item in charted if item["id"] == "bank_rate"), None)
    bank_latest = _latest(bank_rate) if bank_rate else None
    summary = {
        "file": OUT_HTML.name,
        "generated": datetime.now(UTC).isoformat(),
        "charts": len(charted),
        "source_groups": len({item.get("source_name") for item in charted}),
        "data_gaps": len(config.get("data_gaps", [])),
        "low_confidence": sum(1 for item in charted if item.get("quality_status") == "low_confidence"),
        "bank_rate_latest": (
            f"{float(bank_latest['value']):.2f}% ({bank_latest['date']})" if bank_latest else "n/a"
        ),
        "unavailable": [item["id"] for item in series_list if not item.get("observations")],
    }
    SUMMARY_JSON.write_text(json.dumps(summary, indent=2, ensure_ascii=False))
    inject_output_index(summary)
    return OUT_HTML


if __name__ == "__main__":
    path = build()
    print(f"Wrote {path} ({path.stat().st_size:,} bytes)")
