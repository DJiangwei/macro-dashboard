"""Build the root and output dashboard archive pages from generated data.

The archive is intentionally generated after country pages so the top-level
cards stay in sync with the latest dashboard summaries and the CE4 canonical
pipeline. It also writes a small JSON summary that future agents can inspect
without scraping HTML.
"""
from __future__ import annotations

import json
from datetime import UTC, datetime
from html import escape
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
OUTPUT = ROOT / "output"
ARCHIVE_JSON = OUTPUT / "dashboard_archive_summary.json"

for path in (ROOT, SRC):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from build_v4 import _latest_value, _source_mix, load_cee_build_snapshot  # noqa: E402
from country_primer.data_fetcher import (  # noqa: E402
    INDICATOR_MANIFEST_48,
    is_dropped_proxy_indicator,
)
from macro_workbench import build_workbench  # noqa: E402


CE4_COUNTRIES = [
    {
        "code": "HU",
        "name": "Hungary",
        "file": "hungary.html",
        "currency": "HUF",
        "institution": "MNB",
    },
    {
        "code": "PL",
        "name": "Poland",
        "file": "poland.html",
        "currency": "PLN",
        "institution": "NBP",
    },
    {
        "code": "CZ",
        "name": "Czechia",
        "file": "czechia.html",
        "currency": "CZK",
        "institution": "CNB",
    },
    {
        "code": "RO",
        "name": "Romania",
        "file": "romania.html",
        "currency": "RON",
        "institution": "BNR",
    },
]

DATA_FIRST_COUNTRIES = [
    {
        "code": "CN",
        "name": "China",
        "file": "china.html",
        "currency": "CNY",
        "institution": "PBC",
        "summary": "china_dashboard_summary.json",
        "headline_label": "Latest USD/CNY fixing",
        "headline_key": "usd_cny_latest",
        "framework": "GS China statistics logic",
    },
    {
        "code": "JP",
        "name": "Japan",
        "file": "japan.html",
        "currency": "JPY",
        "institution": "BoJ",
        "summary": "japan_dashboard_summary.json",
        "headline_label": "Overnight call rate",
        "headline_key": "policy_rate_latest",
        "framework": "Nine-pillar comparable core",
    },
    {
        "code": "ZA",
        "name": "South Africa",
        "file": "south_africa.html",
        "currency": "ZAR",
        "institution": "SARB",
        "summary": "south_africa_dashboard_summary.json",
        "headline_label": "SARB repo rate",
        "headline_key": "policy_rate_latest",
        "framework": "Nine-pillar comparable core",
    },
    {
        "code": "UK",
        "name": "United Kingdom",
        "file": "uk.html",
        "currency": "GBP",
        "institution": "BoE",
        "summary": "uk_dashboard_summary.json",
        "headline_label": "Bank Rate",
        "headline_key": "bank_rate_latest",
        "framework": "GS UK statistics logic",
    },
    {
        "code": "US",
        "name": "United States",
        "file": "us.html",
        "currency": "USD",
        "institution": "Fed",
        "summary": "us_dashboard_summary.json",
        "headline_label": "Fed funds",
        "headline_key": "fed_funds_latest",
        "framework": "GS US statistics logic",
    },
]


def _read_json(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text())
    except json.JSONDecodeError:
        return {}


def _latest_row(frame: list[dict], indicator_id: str) -> dict:
    rows = [row for row in frame if row.get("indicator_id") == indicator_id]
    return sorted(rows, key=lambda row: str(row.get("date", "")))[-1] if rows else {}


def _signal(frame: list[dict], indicator_id: str, label: str) -> dict:
    row = _latest_row(frame, indicator_id)
    if not row:
        return {}
    try:
        value = float(row.get("value"))
    except (TypeError, ValueError):
        value = None
    return {
        "id": indicator_id,
        "label": label,
        "value": value,
        "display": f"{value:.2f} {row.get('unit', '')}".strip() if value is not None else "n/a",
        "date": row.get("date", ""),
        "source": row.get("source", ""),
        "quality_status": row.get("quality_status", ""),
    }


def _ce4_signals(frame: list[dict]) -> dict[str, dict]:
    return {
        "growth": _signal(frame, "real_gdp_yoy", "Real GDP YoY"),
        "inflation": _signal(frame, "cpi_yoy", "Headline CPI"),
        "policy": _signal(frame, "policy_rate", "Policy rate"),
        "external": _signal(frame, "current_account_pct_gdp", "Current account/GDP"),
        "fiscal": _signal(frame, "fiscal_balance_pct_gdp", "Fiscal balance/GDP"),
        "financial": _signal(frame, "credit_to_gdp_gap", "Credit-to-GDP gap"),
        "property": _signal(frame, "house_price_index", "House price YoY"),
    }


def _ce4_cards() -> list[dict]:
    snapshot = load_cee_build_snapshot()
    cards: list[dict] = []
    for country in CE4_COUNTRIES:
        code = country["code"]
        country_snapshot = (snapshot.get("countries") or {}).get(code) or {}
        frame = list((country_snapshot.get("indicators") or {}).values())
        if not frame:
            raise ValueError(f"CEE snapshot has no indicators for {code}")
        coverage = country_snapshot.get("coverage") or {}
        verified, watch, low = _source_mix(frame)
        dropped = int(country_snapshot.get("dropped_proxy_slots") or len(
            [spec for spec in INDICATOR_MANIFEST_48 if is_dropped_proxy_indicator(code, spec.indicator_id)]
        ))
        rendered = int(coverage.get("indicator_count", 0))
        expected = int(coverage.get("expected", rendered))
        proxy = int(coverage.get("proxy_count", 0))
        cards.append(
            {
                **country,
                "category": "CEE-4 v4 public dashboard",
                "charts": rendered,
                "expected": expected,
                "proxy_fills": proxy,
                "gaps_or_dropped": dropped,
                "gaps_label": "Dropped proxy slots",
                "headline_label": "Policy rate",
                "headline": f"{_latest_value(frame, code, 'policy_rate')}%",
                "secondary_label": "10Y yield",
                "secondary": f"{_latest_value(frame, code, 'sov_yield_10y')}%",
                "quality": f"{verified} verified · {watch} watch · {low} low",
                "status": "watch" if proxy else "clean",
                "signals": _ce4_signals(frame),
            }
        )
    return cards


def _data_first_cards() -> list[dict]:
    cards: list[dict] = []
    for country in DATA_FIRST_COUNTRIES:
        summary = _read_json(OUTPUT / country["summary"])
        charts = int(summary.get("charts") or 0)
        data_gaps = int(summary.get("data_gaps") or 0)
        low_confidence = int(summary.get("low_confidence") or 0)
        source_groups = int(summary.get("source_groups") or 0)
        cards.append(
            {
                **{key: country[key] for key in ("code", "name", "file", "currency", "institution")},
                "category": "data-first country page",
                "charts": charts,
                "expected": charts,
                "proxy_fills": 0,
                "gaps_or_dropped": data_gaps,
                "gaps_label": "Official data gaps",
                "headline_label": country["headline_label"],
                "headline": str(summary.get(country["headline_key"]) or "n/a"),
                "secondary_label": "Source groups",
                "secondary": str(source_groups),
                "quality": f"{source_groups} source groups · {low_confidence} low-confidence charts",
                "framework": country["framework"],
                "status": "clean",
            }
        )
    return cards


def _card_html(card: dict, *, prefix: str) -> str:
    href = f"{prefix}{card['file']}"
    status_class = "warn" if card.get("status") == "watch" else "clean"
    rendered_label = "Rendered indicators" if card["code"] in {"HU", "PL", "CZ", "RO"} else "Rendered charts"
    return f"""
  <a href="{escape(href)}" class="card {status_class}" data-country="{escape(card['code'])}">
    <div class="card-kicker">{escape(card['currency'])} · {escape(card['institution'])} · {escape(card['category'])}</div>
    <h2>{escape(card['name'])}</h2>
    <div class="stats">
      <div class="stat"><span>{rendered_label}</span><strong>{card['charts']}/{card['expected']}</strong></div>
      <div class="stat"><span>Proxy fills</span><strong>{card['proxy_fills']}</strong></div>
      <div class="stat"><span>{escape(card['gaps_label'])}</span><strong>{card['gaps_or_dropped']}</strong></div>
      <div class="stat"><span>{escape(card['headline_label'])}</span><strong>{escape(card['headline'])}</strong></div>
      <div class="stat"><span>{escape(card['secondary_label'])}</span><strong>{escape(card['secondary'])}</strong></div>
      <div class="stat"><span>Source quality</span><strong>{escape(card['quality'])}</strong></div>
    </div>
  </a>"""


def _status_class(value: object, *, inverse: bool = False) -> str:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return "neutral"
    if inverse:
        if number <= 0:
            return "good"
        if number <= 5:
            return "neutral"
        return "bad"
    if number >= 80:
        return "good"
    if number >= 60:
        return "neutral"
    return "bad"


def _workbench_html(workbench: dict, *, prefix: str) -> str:
    regimes = workbench.get("regimes", {}) or {}
    heatmap = workbench.get("heatmap", []) or []
    monitor = workbench.get("release_monitor", []) or []
    backlog = workbench.get("gap_backlog", []) or []
    changes = workbench.get("what_changed", []) or []

    regime_rows = []
    for card in workbench.get("cards", []) or []:
        code = card.get("code", "")
        regime = regimes.get(code, {})
        dims = regime.get("dimensions", {}) or {}
        regime_rows.append(f"""
      <tr>
        <td><strong>{escape(str(code))}</strong><span>{escape(str(card.get('name', '')))}</span></td>
        <td><span class="score-pill {_status_class(regime.get('composite_score'))}">{escape(str(regime.get('composite_score', 'n/a')))}</span><em>{escape(str(regime.get('composite_label', 'n/a')))}</em></td>
        <td>{escape(str((dims.get('growth') or {}).get('label', 'n/a')))}</td>
        <td>{escape(str((dims.get('inflation') or {}).get('label', 'n/a')))}</td>
        <td>{escape(str((dims.get('policy') or {}).get('label', 'n/a')))}</td>
        <td><span class="score-pill {_status_class((regime.get('quality') or {}).get('score'))}">{escape(str((regime.get('quality') or {}).get('score', 'n/a')))}</span></td>
      </tr>""")

    heatmap_rows = []
    for row in heatmap:
        heatmap_rows.append(f"""
      <tr>
        <td><strong>{escape(str(row.get('code', '')))}</strong></td>
        <td class="{_status_class(row.get('coverage_pct'))}">{escape(str(row.get('coverage_pct', 'n/a')))}%</td>
        <td class="{_status_class(row.get('freshness_pct'))}">{escape(str(row.get('freshness_pct', 'n/a')))}%</td>
        <td class="{_status_class(row.get('proxy_fills'), inverse=True)}">{escape(str(row.get('proxy_fills', 'n/a')))}</td>
        <td class="{_status_class(row.get('gaps'), inverse=True)}">{escape(str(row.get('gaps', 'n/a')))}</td>
        <td class="{_status_class(row.get('regime_score'))}">{escape(str(row.get('regime_score', 'n/a')))}</td>
      </tr>""")

    monitor_items = []
    for item in monitor[:8]:
        monitor_items.append(f"""
      <li>
        <strong>{escape(str(item.get('code', '')))} · {escape(str(item.get('indicator_id', '')))}</strong>
        <span>{escape(str(item.get('status', '')))} · {escape(str(item.get('latest', '')))} · {escape(str(item.get('source', '')))}</span>
      </li>""")
    if not monitor_items:
        monitor_items.append("<li><strong>All clear</strong><span>No freshness-monitor attention items.</span></li>")

    backlog_items = []
    for item in backlog[:8]:
        backlog_items.append(f"""
      <li>
        <strong>{escape(str(item.get('priority', 'watch')).upper())} · {escape(str(item.get('code', '')))} · {escape(str(item.get('section', '')))}</strong>
        <span>{escape(str(item.get('item', '')))}</span>
      </li>""")

    change_items = []
    for item in changes[:8]:
        detail = item.get("detail") or f"{item.get('change', '')}: {item.get('from', '')} -> {item.get('to', '')}"
        change_items.append(f"""
      <li>
        <strong>{escape(str(item.get('scope', 'workbench')))}</strong>
        <span>{escape(str(detail))}</span>
      </li>""")

    return f"""
  <section class="workbench" aria-label="macro workbench">
    <div class="section-head">
      <p class="eyebrow">Macro Workbench</p>
      <h2>Regime, Data Quality, And Maintenance Queue</h2>
      <p>Generated from <code>{escape(prefix)}macro_workbench_summary.json</code>. Scores are directional research aids: they combine public data coverage, freshness, proxy status, and selected macro signals.</p>
    </div>
    <div class="table-wrap">
      <table class="regime-table">
        <thead><tr><th>Country</th><th>Composite</th><th>Growth</th><th>Inflation</th><th>Policy</th><th>Data Quality</th></tr></thead>
        <tbody>{''.join(regime_rows)}</tbody>
      </table>
    </div>
    <div class="workbench-grid">
      <div class="workbench-card">
        <h3>Cross-Country Heatmap</h3>
        <table class="heatmap-table">
          <thead><tr><th>Country</th><th>Coverage</th><th>Fresh</th><th>Proxy</th><th>Gaps</th><th>Regime</th></tr></thead>
          <tbody>{''.join(heatmap_rows)}</tbody>
        </table>
      </div>
      <div class="workbench-card">
        <h3>Release Monitor</h3>
        <ul class="signal-list">{''.join(monitor_items)}</ul>
      </div>
      <div class="workbench-card">
        <h3>Priority Gap Backlog</h3>
        <ul class="signal-list">{''.join(backlog_items)}</ul>
      </div>
      <div class="workbench-card">
        <h3>What Changed</h3>
        <ul class="signal-list">{''.join(change_items)}</ul>
      </div>
    </div>
  </section>"""


def _html(cards: list[dict], workbench: dict, *, prefix: str, docs_prefix: str) -> str:
    total_charts = sum(int(card["charts"]) for card in cards)
    total_proxy = sum(int(card["proxy_fills"]) for card in cards)
    total_gaps = sum(int(card["gaps_or_dropped"]) for card in cards)
    generated = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")
    card_markup = "".join(_card_html(card, prefix=prefix) for card in cards)
    archive_json_href = f"{prefix}dashboard_archive_summary.json" if prefix else "dashboard_archive_summary.json"
    workbench_markup = _workbench_html(workbench, prefix=prefix)
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Country Primer — Macro Dashboard Archive</title>
<style>
:root {{
  --bg: #f4efe7;
  --fg: #171310;
  --muted: #63574e;
  --accent: #8a593d;
  --border: rgba(23, 19, 16, 0.14);
  --card: rgba(255, 252, 246, 0.76);
  --success: #3f6f50;
  --warn: #9d3d2e;
  --font-display: "Iowan Old Style", "Songti SC", "Noto Serif SC", Georgia, serif;
  --font-body: "Avenir Next", "PingFang SC", "Noto Sans SC", "Segoe UI", sans-serif;
}}
* {{ box-sizing: border-box; }}
html {{ scroll-behavior: smooth; }}
body {{
  margin: 0;
  background:
    radial-gradient(circle at top left, rgba(138, 89, 61, 0.15), transparent 24%),
    radial-gradient(circle at top right, rgba(54, 75, 97, 0.12), transparent 22%),
    linear-gradient(180deg, #f8f4ed 0%, #f4efe7 48%, #efe7db 100%);
  color: var(--fg);
  font-family: var(--font-body);
  font-size: 14px;
  line-height: 1.6;
}}
body::before {{
  content: "";
  position: fixed;
  inset: 0;
  pointer-events: none;
  background:
    linear-gradient(to right, rgba(23, 19, 16, 0.025) 1px, transparent 1px),
    linear-gradient(to bottom, rgba(23, 19, 16, 0.02) 1px, transparent 1px);
  background-size: 48px 48px;
  mask-image: linear-gradient(180deg, rgba(0, 0, 0, 0.45), transparent 85%);
}}
.topbar {{
  position: sticky;
  top: 0;
  z-index: 20;
  display: flex;
  justify-content: space-between;
  gap: 16px;
  padding: 12px 32px;
  border-bottom: 1px solid var(--border);
  background: rgba(244, 239, 231, 0.86);
  backdrop-filter: blur(14px);
  font-size: 11px;
  letter-spacing: 0.12em;
  text-transform: uppercase;
}}
.brand {{ font-family: var(--font-display); font-size: 15px; letter-spacing: 0.16em; }}
.brand span {{ color: var(--accent); }}
.container {{ position: relative; max-width: 1180px; margin: 0 auto; padding: 48px 24px; }}
header {{ border-bottom: 1px solid var(--border); padding-bottom: 32px; margin-bottom: 24px; }}
h1 {{
  margin: 0;
  max-width: 980px;
  font-family: var(--font-display);
  font-size: clamp(34px, 6vw, 72px);
  line-height: 0.92;
  letter-spacing: -0.06em;
  font-weight: 500;
}}
.subtitle {{ max-width: 880px; color: var(--muted); font-size: 17px; line-height: 1.7; }}
code {{ overflow-wrap: anywhere; word-break: break-word; }}
.meta-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 10px; margin: 24px 0; }}
.meta-chip {{
  background: var(--card);
  border: 1px solid var(--border);
  padding: 14px 16px;
}}
.meta-chip strong {{ display: block; font-family: var(--font-display); font-size: 28px; font-weight: 500; }}
.meta-chip span {{ color: var(--muted); font-size: 11px; letter-spacing: 0.08em; text-transform: uppercase; }}
.section-head {{ margin: 42px 0 18px; max-width: 900px; }}
.section-head .eyebrow {{ color: var(--accent); font-size: 11px; letter-spacing: 0.16em; text-transform: uppercase; margin: 0 0 8px; }}
.section-head h2 {{ margin: 0; font-family: var(--font-display); font-size: clamp(28px, 4vw, 48px); font-weight: 500; letter-spacing: -0.04em; }}
.section-head p {{ color: var(--muted); }}
.table-wrap, .workbench-card {{
  background: var(--card);
  border: 1px solid var(--border);
  overflow-x: auto;
}}
table {{ width: 100%; border-collapse: collapse; min-width: 720px; }}
th {{ text-align: left; color: var(--accent); font-size: 11px; letter-spacing: 0.1em; text-transform: uppercase; font-weight: 600; }}
th, td {{ border-bottom: 1px solid var(--border); padding: 12px 14px; vertical-align: top; }}
td span, td em {{ display: block; color: var(--muted); font-style: normal; font-size: 12px; }}
.score-pill {{ display: inline-block; min-width: 46px; text-align: center; padding: 3px 8px; border-radius: 999px; border: 1px solid var(--border); font-family: var(--font-display); }}
.good {{ background: rgba(63, 111, 80, 0.12); color: #315b40; }}
.neutral {{ background: rgba(138, 89, 61, 0.10); color: var(--accent); }}
.bad {{ background: rgba(157, 61, 46, 0.12); color: var(--warn); }}
.workbench-grid {{ display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 14px; margin-top: 14px; }}
.workbench-card {{ padding: 18px; }}
.workbench-card h3 {{ margin: 0 0 12px; font-family: var(--font-display); font-weight: 500; font-size: 24px; }}
.workbench-card table {{ min-width: 520px; }}
.signal-list {{ list-style: none; margin: 0; padding: 0; display: grid; gap: 10px; }}
.signal-list li {{ border-top: 1px solid var(--border); padding-top: 10px; }}
.signal-list strong {{ display: block; font-size: 12px; letter-spacing: 0.04em; text-transform: uppercase; }}
.signal-list span {{ display: block; color: var(--muted); font-size: 12px; margin-top: 3px; }}
.controls {{ display: flex; gap: 10px; flex-wrap: wrap; align-items: center; margin: 24px 0 14px; }}
.controls button, .controls input {{
  border: 1px solid var(--border);
  background: var(--card);
  color: var(--fg);
  padding: 9px 12px;
  border-radius: 999px;
  font: inherit;
}}
.controls button.active {{ border-color: rgba(138, 89, 61, 0.55); background: rgba(138, 89, 61, 0.12); }}
.controls input {{ min-width: min(280px, 100%); border-radius: 14px; }}
.grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 14px; }}
.card {{
  display: block;
  color: inherit;
  text-decoration: none;
  background: var(--card);
  border: 1px solid var(--border);
  border-top: 3px solid var(--success);
  padding: 24px;
  transition: transform 0.18s ease, border-color 0.18s ease, background 0.18s ease;
}}
.card.warn {{ border-top-color: var(--warn); }}
.card:hover {{ transform: translateY(-2px); background: rgba(255, 252, 246, 0.95); border-color: rgba(23, 19, 16, 0.28); }}
.card-kicker {{ color: var(--accent); font-size: 11px; letter-spacing: 0.1em; text-transform: uppercase; }}
.card h2 {{ margin: 8px 0 16px; font-family: var(--font-display); font-weight: 500; font-size: 34px; }}
.stats {{ display: grid; gap: 7px; }}
.stat {{ display: flex; justify-content: space-between; gap: 16px; border-bottom: 1px solid var(--border); padding: 7px 0; }}
.stat span {{ color: var(--muted); }}
.stat strong {{ text-align: right; font-family: var(--font-display); font-weight: 500; }}
.links {{ margin-top: 24px; display: flex; gap: 10px; flex-wrap: wrap; }}
.links a {{
  color: var(--accent);
  border: 1px solid var(--border);
  background: var(--card);
  padding: 8px 13px;
  text-decoration: none;
  border-radius: 999px;
}}
footer {{ margin-top: 36px; padding-top: 24px; border-top: 1px solid var(--border); color: var(--muted); font-size: 12px; }}
@media (max-width: 720px) {{
  .topbar {{ align-items: flex-start; flex-direction: column; padding: 12px 20px; }}
  .container {{ padding: 34px 18px; }}
  .workbench-grid {{ grid-template-columns: 1fr; }}
}}
</style>
</head>
<body>
<div class="topbar">
  <div class="brand">East Meridian <span>/ Country Primer</span></div>
  <div>Macro Dashboard Archive · CEE-4 v4 + China + Japan + South Africa + UK + US</div>
</div>
<main class="container">
  <header>
    <h1>Macro Dashboard Archive</h1>
    <p class="subtitle">Generated archive for the CEE-4 public dashboards and the China, UK, and US data-first pages. Cards are rebuilt from the latest country summaries and the CE4 canonical pipeline, then exported to <code>{escape(archive_json_href)}</code> so homepage data stays linked to dashboard builds.</p>
  </header>
  <section class="meta-grid" aria-label="coverage summary">
    <div class="meta-chip"><strong>{total_charts}</strong><span>rendered chart slots</span></div>
    <div class="meta-chip"><strong>{total_proxy}</strong><span>remaining proxy fills</span></div>
    <div class="meta-chip"><strong>{total_gaps}</strong><span>gaps or dropped slots</span></div>
    <div class="meta-chip"><strong>{len(cards)}</strong><span>country dashboards</span></div>
  </section>
{workbench_markup}
  <div class="controls" aria-label="country filters">
    <button type="button" class="active" data-filter="all">All</button>
    <button type="button" data-filter="clean">Clean</button>
    <button type="button" data-filter="watch">Watch</button>
    <input id="countrySearch" type="search" placeholder="Filter countries, currencies, institutions..." aria-label="Filter country cards">
  </div>
  <section class="grid" aria-label="country dashboards">
{card_markup}
  </section>
  <nav class="links" aria-label="documentation links">
    <a href="{docs_prefix}CORE_COVERAGE_MATRIX.md">Core 48 Coverage</a>
    <a href="{docs_prefix}DATA_SOURCE_CATALOG.md">Data Source Catalog</a>
    <a href="{docs_prefix}DATA_FRESHNESS_AUDIT.md">Freshness Audit</a>
    <a href="{docs_prefix}PROXY_REVIEW.md">Proxy Review</a>
    <a href="{prefix}macro_framework_proposal.html">Framework Proposal</a>
    <a href="{escape(archive_json_href)}">Archive JSON</a>
    <a href="{prefix}macro_workbench_summary.json">Workbench JSON</a>
    <a href="{prefix}release_monitor.json">Release Monitor</a>
    <a href="{prefix}what_changed.json">What Changed</a>
  </nav>
  <footer>
    Generated {generated} from country dashboard summaries and canonical CE4 data. Research artefact only, not investment advice.
  </footer>
</main>
<script>
const buttons = Array.from(document.querySelectorAll('[data-filter]'));
const cards = Array.from(document.querySelectorAll('.card[data-country]'));
const search = document.getElementById('countrySearch');
let activeFilter = 'all';
function applyFilters() {{
  const query = (search.value || '').trim().toLowerCase();
  cards.forEach(card => {{
    const statusOk = activeFilter === 'all' || card.classList.contains(activeFilter);
    const textOk = !query || card.textContent.toLowerCase().includes(query);
    card.style.display = statusOk && textOk ? '' : 'none';
  }});
}}
buttons.forEach(button => {{
  button.addEventListener('click', () => {{
    activeFilter = button.dataset.filter || 'all';
    buttons.forEach(item => item.classList.toggle('active', item === button));
    applyFilters();
  }});
}});
if (search) search.addEventListener('input', applyFilters);
</script>
</body>
</html>
"""


def _write(path: Path, content: str) -> None:
    path.write_text("\n".join(line.rstrip() for line in content.splitlines()) + "\n")


def build_archive() -> tuple[Path, Path, Path]:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    cards = _ce4_cards() + _data_first_cards()
    workbench = build_workbench(cards)
    payload = {
        "generated": datetime.now(UTC).isoformat(),
        "source": "Generated from one CEE build snapshot plus output/*_dashboard_summary.json files.",
        "cards": cards,
        "workbench": {
            "file": "macro_workbench_summary.json",
            "release_monitor": "release_monitor.json",
            "what_changed": "what_changed.json",
            "data_gap_backlog": "data_gap_backlog.json",
            "schema_version": workbench.get("schema_version"),
        },
    }
    ARCHIVE_JSON.write_text(json.dumps(payload, indent=2, ensure_ascii=False))
    output_index = OUTPUT / "index.html"
    root_index = ROOT / "index.html"
    _write(output_index, _html(cards, workbench, prefix="", docs_prefix="../"))
    _write(root_index, _html(cards, workbench, prefix="output/", docs_prefix=""))
    return root_index, output_index, ARCHIVE_JSON


if __name__ == "__main__":
    for path in build_archive():
        print(f"Wrote {path} ({path.stat().st_size:,} bytes)")
