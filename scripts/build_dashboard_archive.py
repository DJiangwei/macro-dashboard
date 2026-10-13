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
        "code": "EA",
        "name": "Euro Area",
        "file": "euro_area.html",
        "currency": "EUR",
        "institution": "ECB",
        "summary": "euro_area_dashboard_summary.json",
        "headline_label": "Deposit Facility Rate",
        "headline_key": "policy_rate_latest",
        "framework": "Nine-pillar comparable core",
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
        <td><span class="score-pill {_status_class(regime.get('cyclical_score'))}">{escape(str(regime.get('cyclical_score', 'n/a')))}</span><em>{escape(str(regime.get('composite_label', 'n/a')))}</em></td>
        <td><span class="score-pill {_status_class(regime.get('structural_score'))}">{escape(str(regime.get('structural_score', 'n/a')))}</span></td>
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

    monetary_rows = []
    monetary_stance = workbench.get("monetary_stance_monitor", {}) or {}
    for code, stance in monetary_stance.items():
        if not stance:
            continue
        dev = float(stance.get("policy_gap_deviation") or 0.0)
        if dev >= 0.5:
            pill_cls = "bad"
        elif dev <= -0.5:
            pill_cls = "good"
        else:
            pill_cls = "neutral"

        sign = "+" if dev > 0 else ""
        dev_str = f"{sign}{dev:.2f}%"

        real_val = float(stance.get("real_policy_rate") or 0.0)
        real_sign = "+" if real_val > 0 else ""
        real_str = f"{real_sign}{real_val:.2f}%"

        monetary_rows.append(f"""
      <tr>
        <td><strong>{escape(str(code))}</strong><span>{escape(str(stance.get('institution', '')))}</span></td>
        <td><strong>{escape(str(stance.get('policy_rate', 'n/a')))}%</strong></td>
        <td>{escape(str(stance.get('inflation_rate', 'n/a')))}% <em>tgt {escape(str(stance.get('inflation_target', 'n/a')))}%</em></td>
        <td>{escape(str(stance.get('taylor_implied_rate', 'n/a')))}%</td>
        <td><span class="score-pill {pill_cls}">{escape(dev_str)}</span></td>
        <td><strong>{escape(real_str)}</strong></td>
        <td><em>{escape(str(stance.get('stance_label', 'n/a')))}</em></td>
      </tr>""")

    sync_data = workbench.get("cross_country_sync", {}) or {}
    cpi_matrix = sync_data.get("inflation_correlation", {}) or {}
    ip_matrix = sync_data.get("industrial_production_correlation", {}) or {}
    sync_countries = sync_data.get("countries", []) or []

    sync_th = "".join(f"<th style='text-align: center; padding: 6px 4px; font-size: 11px;'>{c}</th>" for c in sync_countries)
    sync_rows = []
    sync_ip_rows = []
    for c1 in sync_countries:
        cells = [f"<td style='padding: 6px 8px;'><strong>{c1}</strong></td>"]
        cells_ip = [f"<td style='padding: 6px 8px;'><strong>{c1}</strong></td>"]
        for c2 in sync_countries:
            val = cpi_matrix.get(c1, {}).get(c2)
            if val is None:
                cells.append("<td style='text-align: center; padding: 6px 4px;'>-</td>")
            else:
                if val >= 0.8:
                    style = "background: rgba(13, 118, 128, 0.14); color: #0d7680; font-weight: 600;"
                elif val >= 0.5:
                    style = "background: rgba(13, 118, 128, 0.06); color: #0d7680;"
                elif val <= -0.2:
                    style = "background: rgba(153, 15, 61, 0.08); color: #990f3d;"
                else:
                    style = "color: #737c8c;"
                cells.append(f"<td style='text-align: center; padding: 6px 4px; font-size: 11px; {style}'>{val:.2f}</td>")

            val_ip = ip_matrix.get(c1, {}).get(c2)
            if val_ip is None:
                cells_ip.append("<td style='text-align: center; padding: 6px 4px;'>-</td>")
            else:
                if val_ip >= 0.8:
                    style_ip = "background: rgba(13, 118, 128, 0.14); color: #0d7680; font-weight: 600;"
                elif val_ip >= 0.5:
                    style_ip = "background: rgba(13, 118, 128, 0.06); color: #0d7680;"
                elif val_ip <= -0.2:
                    style_ip = "background: rgba(153, 15, 61, 0.08); color: #990f3d;"
                else:
                    style_ip = "color: #737c8c;"
                cells_ip.append(f"<td style='text-align: center; padding: 6px 4px; font-size: 11px; {style_ip}'>{val_ip:.2f}</td>")

        sync_rows.append(f"<tr>{''.join(cells)}</tr>")
        sync_ip_rows.append(f"<tr>{''.join(cells_ip)}</tr>")

    return f"""
  <section class="workbench" aria-label="macro workbench">
    <div class="section-head">
      <p class="eyebrow">Macro Workbench</p>
      <h2>Regime, Data Quality, And Maintenance Queue</h2>
      <p>Generated from <code>{escape(prefix)}macro_workbench_summary.json</code>. Scores are directional research aids: they combine public data coverage, freshness, proxy status, and selected macro signals.</p>
    </div>
    <div class="table-wrap">
      <table class="regime-table">
        <thead><tr><th>Country</th><th>Cyclical</th><th>Structural</th><th>Growth</th><th>Inflation</th><th>Policy</th><th>Data Quality</th></tr></thead>
        <tbody>{''.join(regime_rows)}</tbody>
      </table>
    </div>
    <div class="table-wrap" style="margin-top: 16px;">
      <div style="padding: 12px 14px; border-bottom: 1px solid var(--border); background: #fcfaf7;">
        <strong style="font-size: 13px; color: var(--fg);">Taylor Rule & Monetary Stance Monitor</strong>
        <span style="display: block; color: var(--text-secondary); font-size: 11px; margin-top: 2px;">Theoretical policy rate benchmark based on core inflation target, neutral real rate (r*), and output gap. Policy gap = Actual rate − Taylor benchmark.</span>
      </div>
      <table class="regime-table">
        <thead><tr><th>Central Bank</th><th>Policy Rate</th><th>Inflation (Target)</th><th>Taylor Benchmark</th><th>Policy Gap</th><th>Real Rate</th><th>Stance Assessment</th></tr></thead>
        <tbody>{''.join(monetary_rows)}</tbody>
      </table>
    </div>
    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(480px, 1fr)); gap: 16px; margin-top: 16px;">
      <div class="table-wrap">
        <div style="padding: 12px 14px; border-bottom: 1px solid var(--border); background: #fcfaf7;">
          <strong style="font-size: 13px; color: var(--fg);">Cross-Country Inflation Synchronization Matrix</strong>
          <span style="display: block; color: var(--text-secondary); font-size: 11px; margin-top: 2px;">Pairwise Pearson correlation on monthly headline CPI ({escape(str(sync_data.get('sample_period_cpi', '')))}). Teal denotes strong co-movement.</span>
        </div>
        <table class="regime-table" style="min-width: 480px;">
          <thead><tr><th style="padding: 6px 8px;">Country</th>{sync_th}</tr></thead>
          <tbody>{''.join(sync_rows)}</tbody>
        </table>
      </div>
      <div class="table-wrap">
        <div style="padding: 12px 14px; border-bottom: 1px solid var(--border); background: #fcfaf7;">
          <strong style="font-size: 13px; color: var(--fg);">Cross-Country Industrial Production Synchronization Matrix</strong>
          <span style="display: block; color: var(--text-secondary); font-size: 11px; margin-top: 2px;">Pairwise Pearson correlation on monthly Industrial Production ({escape(str(sync_data.get('sample_period_ip', '')))}). Teal denotes real-cycle co-movement.</span>
        </div>
        <table class="regime-table" style="min-width: 480px;">
          <thead><tr><th style="padding: 6px 8px;">Country</th>{sync_th}</tr></thead>
          <tbody>{''.join(sync_ip_rows)}</tbody>
        </table>
      </div>
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
  --bg-canvas: #fcfaf7;
  --bg-surface: #ffffff;
  --bg-deep: #f7f5f0;
  --fg: #12151a;
  --text-secondary: #4b525f;
  --muted: #737c8c;
  --accent: #990f3d;
  --border: rgba(18, 21, 26, 0.08);
  --border-strong: rgba(18, 21, 26, 0.16);
  --card: #ffffff;
  --success: #0d7680;
  --warn: #b86200;
  --font-display: "Newsreader", "Iowan Old Style", "Songti SC", "Noto Serif SC", Georgia, serif;
  --font-body: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", "Noto Sans SC", Helvetica, Arial, sans-serif;
}}
* {{ box-sizing: border-box; }}
html {{ scroll-behavior: smooth; }}
body {{
  margin: 0;
  background: var(--bg-canvas);
  color: var(--fg);
  font-family: var(--font-body);
  font-size: 14px;
  line-height: 1.6;
  -webkit-font-smoothing: antialiased;
}}
body::before {{ display: none !important; }}
.topbar {{
  position: sticky;
  top: 0;
  z-index: 20;
  display: flex;
  justify-content: space-between;
  gap: 16px;
  padding: 10px 32px;
  border-bottom: 1px solid var(--border);
  background: rgba(252, 250, 247, 0.94);
  backdrop-filter: blur(12px);
  font-size: 12px;
  letter-spacing: normal;
}}
.brand {{ font-family: var(--font-display); font-size: 16px; font-weight: 600; letter-spacing: -0.01em; }}
.brand span {{ color: var(--accent); }}
.container {{ position: relative; max-width: 1180px; margin: 0 auto; padding: 40px 24px; }}
header {{ border-bottom: 1px solid var(--border); padding-bottom: 28px; margin-bottom: 24px; }}
h1 {{
  margin: 0;
  max-width: 980px;
  font-family: var(--font-display);
  font-size: clamp(34px, 5vw, 64px);
  line-height: 1.05;
  letter-spacing: -0.03em;
  font-weight: 600;
}}
.subtitle {{ max-width: 860px; color: var(--text-secondary); font-size: 16px; line-height: 1.6; }}
code {{ overflow-wrap: anywhere; word-break: break-word; }}
.meta-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 10px; margin: 24px 0; }}
.meta-chip {{
  background: #ffffff;
  border: 1px solid var(--border);
  border-radius: 4px;
  padding: 14px 16px;
  box-shadow: 0 1px 2px rgba(0,0,0,0.03);
}}
.meta-chip strong {{ display: block; font-family: var(--font-body); font-size: 26px; font-weight: 700; color: var(--fg); }}
.meta-chip span {{ color: var(--text-secondary); font-size: 12px; font-weight: 500; letter-spacing: normal; text-transform: none; }}
.section-head {{ margin: 40px 0 16px; max-width: 900px; }}
.section-head .eyebrow {{ color: var(--accent); font-size: 11px; font-weight: 600; letter-spacing: normal; text-transform: none; margin: 0 0 6px; }}
.section-head h2 {{ margin: 0; font-family: var(--font-display); font-size: clamp(26px, 3.5vw, 42px); font-weight: 600; letter-spacing: -0.025em; }}
.section-head p {{ color: var(--text-secondary); font-size: 14px; }}
.table-wrap, .workbench-card {{
  background: #ffffff;
  border: 1px solid var(--border);
  border-radius: 4px;
  box-shadow: 0 1px 2px rgba(0,0,0,0.03);
  overflow-x: auto;
}}
table {{ width: 100%; border-collapse: collapse; min-width: 720px; }}
th {{ text-align: left; color: var(--text-secondary); font-size: 11px; font-weight: 600; letter-spacing: normal; text-transform: none; background: #fcfaf7; }}
th, td {{ border-bottom: 1px solid var(--border); padding: 10px 14px; vertical-align: top; }}
td span, td em {{ display: block; color: var(--muted); font-style: normal; font-size: 12px; }}
.score-pill {{ display: inline-block; min-width: 46px; text-align: center; padding: 2px 8px; border-radius: 3px; border: 1px solid var(--border); font-family: var(--font-body); font-weight: 600; font-size: 12px; }}
.good {{ background: rgba(13, 118, 128, 0.08); color: #0d7680; border-color: rgba(13, 118, 128, 0.25); }}
.neutral {{ background: rgba(184, 98, 0, 0.08); color: #b86200; border-color: rgba(184, 98, 0, 0.25); }}
.bad {{ background: rgba(153, 15, 61, 0.08); color: #990f3d; border-color: rgba(153, 15, 61, 0.25); }}
.workbench-grid {{ display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 14px; margin-top: 14px; }}
.workbench-card {{ padding: 18px; }}
.workbench-card h3 {{ margin: 0 0 12px; font-family: var(--font-display); font-weight: 600; font-size: 22px; }}
.workbench-card table {{ min-width: 520px; }}
.signal-list {{ list-style: none; margin: 0; padding: 0; display: grid; gap: 10px; }}
.signal-list li {{ border-top: 1px solid var(--border); padding-top: 10px; }}
.signal-list strong {{ display: block; font-size: 12px; font-weight: 600; letter-spacing: normal; text-transform: none; }}
.signal-list span {{ display: block; color: var(--text-secondary); font-size: 12px; margin-top: 3px; }}
.controls {{ display: flex; gap: 8px; flex-wrap: wrap; align-items: center; margin: 20px 0 14px; }}
.controls button, .controls input {{
  border: 1px solid var(--border);
  background: #ffffff;
  color: var(--fg);
  padding: 6px 12px;
  border-radius: 4px;
  font: inherit;
  font-size: 12px;
}}
.controls button.active {{ border-color: var(--fg); background: var(--fg); color: #ffffff; font-weight: 600; }}
.controls input {{ min-width: min(280px, 100%); }}
.grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 14px; }}
.card {{
  display: block;
  color: inherit;
  text-decoration: none;
  background: #ffffff;
  border: 1px solid var(--border);
  border-top: 3px solid var(--border-strong);
  border-radius: 4px;
  box-shadow: 0 1px 2px rgba(0,0,0,0.03);
  padding: 20px;
  transition: border-color 0.15s ease;
}}
.card.warn {{ border-top-color: var(--warn); }}
.card:hover {{ border-color: var(--border-strong); box-shadow: 0 2px 4px rgba(0,0,0,0.05); }}
.card-kicker {{ color: var(--accent); font-size: 11px; font-weight: 600; letter-spacing: normal; text-transform: none; }}
.card h2 {{ margin: 6px 0 14px; font-family: var(--font-display); font-weight: 600; font-size: 28px; }}
.stats {{ display: grid; gap: 7px; }}
.stat {{ display: flex; justify-content: space-between; gap: 16px; border-bottom: 1px solid var(--border); padding: 7px 0; }}
.stat span {{ color: var(--text-secondary); font-size: 12px; }}
.stat strong {{ text-align: right; font-family: var(--font-body); font-weight: 600; }}
.links {{ margin-top: 20px; display: flex; gap: 8px; flex-wrap: wrap; }}
.links a {{
  color: var(--accent);
  border: 1px solid var(--border);
  background: #fcfaf7;
  padding: 5px 12px;
  text-decoration: none;
  border-radius: 4px;
  font-size: 12px;
}}
footer {{ margin-top: 36px; padding-top: 24px; border-top: 1px solid var(--border); color: var(--muted); font-size: 12px; }}
@media (max-width: 720px) {{
  .topbar {{ align-items: flex-start; flex-direction: column; padding: 10px 18px; }}
  .container {{ padding: 24px 16px; }}
  .workbench-grid {{ grid-template-columns: 1fr; }}
}}
</style>
</head>
<body>
<div class="topbar">
  <div class="brand">East Meridian <span>/ Country Primer</span></div>
  <div>Macro Dashboard Archive · CEE-4 v4 + China + Euro Area + Japan + South Africa + UK + US</div>
</div>
<main class="container">
  <header>
    <h1>Macro Dashboard Archive</h1>
    <p class="subtitle">Generated archive for the CEE-4 public dashboards and the China, Euro Area, Japan, South Africa, UK, and US data-first pages. Cards are rebuilt from the latest country summaries and the CE4 canonical pipeline, then exported to <code>{escape(archive_json_href)}</code> so homepage data stays linked to dashboard builds.</p>
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
