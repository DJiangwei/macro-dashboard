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


def _fetch_one(spec: dict[str, Any]) -> dict[str, Any]:
    session = requests.Session()
    try:
        if spec.get("fetcher") == "fred":
            series = _apply_transform(fetch_fred_us(session, spec))
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
    # Keep public fallback bounded: slow FRED graph requests should become
    # explicit unavailable items, not stall the whole publishing pipeline.
    with ThreadPoolExecutor(max_workers=8) as executor:
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
    return OUT_HTML


if __name__ == "__main__":
    path = build()
    print(f"Wrote {path} ({path.stat().st_size:,} bytes)")
