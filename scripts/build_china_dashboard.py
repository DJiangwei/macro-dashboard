"""Build the China macro dashboard from PDF-aligned indicator config.

The China page is intentionally data-first. It follows the section logic from
Goldman Sachs' China statistics guide, but only renders charts from sources
that can be fetched reproducibly from public endpoints in this repo.
"""
from __future__ import annotations

import json
import os
import re
from datetime import UTC, date, datetime, timedelta
from html import escape
from pathlib import Path
from typing import Any

import requests
import yaml


ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "config" / "china_indicators.yaml"
OUTPUT = ROOT / "output"
OUT_HTML = OUTPUT / "china_2026Q2_v1.html"
SUMMARY_JSON = OUTPUT / "china_dashboard_summary.json"

ACCENT = "#8a593d"
INK = "#171310"
MUTED = "#63574e"
PAPER = "rgba(255,252,246,0.90)"


def _load_config() -> dict[str, Any]:
    return yaml.safe_load(CONFIG_PATH.read_text()) or {}


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False)


def _clean_text(value: str) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def _write_clean(path: Path, content: str) -> None:
    path.write_text("\n".join(line.rstrip() for line in content.splitlines()) + "\n")


def _apply_transform(value: float, transform: str | None) -> float:
    if transform == "usd_trn":
        return value / 1_000_000_000_000
    if transform == "people_billion":
        return value / 1_000_000_000
    return value


def _parse_year(value: str) -> int | None:
    try:
        return int(str(value)[:4])
    except (TypeError, ValueError):
        return None


def fetch_world_bank(spec: dict[str, Any]) -> dict[str, Any]:
    code = spec["series"]
    url = f"https://api.worldbank.org/v2/country/CHN/indicator/{code}"
    response = requests.get(url, params={"format": "json", "per_page": 20000}, timeout=30)
    response.raise_for_status()
    payload = response.json()
    meta = payload[0] if isinstance(payload, list) and payload else {}
    rows = payload[1] if isinstance(payload, list) and len(payload) > 1 else []
    observations: list[dict[str, Any]] = []
    for row in rows:
        raw_value = row.get("value")
        if raw_value is None:
            continue
        try:
            value = _apply_transform(float(raw_value), spec.get("transform"))
        except (TypeError, ValueError):
            continue
        observations.append({"date": str(row.get("date")), "value": value})
    observations.sort(key=lambda item: item["date"])
    return {
        **spec,
        "observations": observations,
        "provider_updated": meta.get("lastupdated", ""),
        "api_url": url,
    }


def fetch_imf_datamapper(spec: dict[str, Any]) -> dict[str, Any]:
    code = spec["series"]
    url = f"https://www.imf.org/external/datamapper/api/v1/{code}/CHN"
    response = requests.get(url, timeout=45)
    response.raise_for_status()
    payload = response.json()
    country_values = ((payload.get("values") or {}).get(code) or {}).get("CHN") or {}
    observations = [
        {"date": str(year), "value": _apply_transform(float(value), spec.get("transform"))}
        for year, value in country_values.items()
        if value is not None and str(year).isdigit()
    ]
    observations.sort(key=lambda item: int(item["date"]))
    return {
        **spec,
        "observations": observations,
        "provider_updated": datetime.now(UTC).date().isoformat(),
        "api_url": url,
    }


def _safe_rows() -> list[list[str]]:
    end = date.today()
    start = end - timedelta(days=365)
    response = requests.post(
        "https://www.safe.gov.cn/AppStructured/hlw/RMBQuery.do",
        data={"startDate": start.isoformat(), "endDate": end.isoformat(), "queryYN": "true"},
        timeout=45,
    )
    response.raise_for_status()
    rows: list[list[str]] = []
    for tr in re.findall(r'<tr[^>]*class="first"[^>]*>(.*?)</tr>', response.text, flags=re.S):
        cells = [
            _clean_text(re.sub(r"<.*?>", "", cell))
            for cell in re.findall(r"<td[^>]*>(.*?)</td>", tr, flags=re.S)
        ]
        cells = [cell for cell in cells if cell]
        if len(cells) >= 3 and re.match(r"\d{4}-\d{2}-\d{2}", cells[0]):
            rows.append(cells)
    rows.sort(key=lambda item: item[0])
    return rows


def fetch_safe_midpoint(spec: dict[str, Any], rows: list[list[str]]) -> dict[str, Any]:
    column = 1 if spec["id"] == "usd_cny_midpoint" else 2
    observations: list[dict[str, Any]] = []
    for row in rows:
        try:
            value = float(row[column]) / 100.0
        except (IndexError, TypeError, ValueError):
            continue
        observations.append({"date": row[0], "value": value})
    return {
        **spec,
        "observations": observations,
        "provider_updated": observations[-1]["date"] if observations else "",
        "api_url": spec["source_url"],
    }


def fetch_pbc_card(card: dict[str, Any]) -> dict[str, Any]:
    response = requests.get(card["url"], timeout=30)
    response.raise_for_status()
    text = re.sub(r"<[^>]+>", "\n", response.text)
    lines = [_clean_text(line) for line in text.splitlines()]
    lines = [line for line in lines if line]
    title = card["expected_title"]
    title_idx = next((i for i, line in enumerate(lines) if line == title), -1)
    value = "n/a"
    if title_idx >= 0:
        for line in lines[title_idx + 1 : title_idx + 14]:
            if re.match(r"^-?\d+(?:\.\d+)?(?:%|TN|BN|MN)?$", line, flags=re.I):
                value = line
                break
    update_idx = next((i for i, line in enumerate(lines) if line == "Latest Update"), -1)
    updated = ""
    if update_idx >= 0:
        for line in lines[update_idx + 1 : update_idx + 5]:
            if re.match(r"\d{2}/\d{2}/\d{4}", line):
                updated = line
                break
    return {**card, "value": value, "updated": updated or "n/a"}


def validate_series(series: dict[str, Any]) -> dict[str, Any]:
    observations = series.get("observations") or []
    notes: list[str] = []
    if not observations:
        return {**series, "quality_status": "unavailable", "quality_notes": ["No observations returned."]}
    if len(observations) < 10:
        notes.append("Short history.")

    frequency = str(series.get("frequency", "")).lower()
    latest_date = str(observations[-1]["date"])
    if frequency == "annual":
        latest_year = _parse_year(latest_date)
        if latest_year and latest_year < date.today().year - 2:
            notes.append(f"Lagged annual series; latest observation is {latest_year}.")
    elif frequency == "daily":
        try:
            latest_dt = datetime.strptime(latest_date, "%Y-%m-%d").date()
            if (date.today() - latest_dt).days > 14:
                notes.append(f"Daily series looks stale; latest observation is {latest_date}.")
        except ValueError:
            notes.append("Daily date could not be parsed.")

    source_name = str(series.get("source_name", ""))
    if "World Bank" in source_name:
        notes.append("Annual WDI data is lagged and revision-prone.")
    if "IMF WEO" in source_name:
        notes.append("IMF WEO includes estimates/projections; dashed segment marks forecast years.")
    if series.get("caveat_en"):
        notes.append(series["caveat_en"])

    if not notes:
        status = "verified"
    elif len(notes) <= 2:
        status = "watch"
    else:
        status = "low_confidence"
    return {**series, "quality_status": status, "quality_notes": notes[:3]}


def fetch_all(config: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    safe_rows: list[list[str]] | None = None
    series_list: list[dict[str, Any]] = []
    for spec in config.get("indicators", []):
        fetcher = spec.get("fetcher")
        try:
            if fetcher == "world_bank":
                series = fetch_world_bank(spec)
            elif fetcher == "imf_datamapper":
                series = fetch_imf_datamapper(spec)
            elif fetcher == "safe_rmb_midpoint":
                if safe_rows is None:
                    safe_rows = _safe_rows()
                series = fetch_safe_midpoint(spec, safe_rows)
            else:
                series = {**spec, "observations": [], "quality_status": "unavailable", "quality_notes": ["Unknown fetcher."]}
        except Exception as exc:  # noqa: BLE001 - build should degrade, not crash, per data-quality policy.
            series = {
                **spec,
                "observations": [],
                "quality_status": "unavailable",
                "quality_notes": [f"Fetch failed: {exc}"],
            }
        series_list.append(validate_series(series))

    cards: list[dict[str, Any]] = []
    for card in config.get("latest_cards", []):
        try:
            cards.append(fetch_pbc_card(card))
        except Exception as exc:  # noqa: BLE001
            cards.append({**card, "value": "n/a", "updated": "n/a", "error": str(exc)})
    return series_list, cards


def _latest(series: dict[str, Any]) -> dict[str, Any] | None:
    observations = series.get("observations") or []
    return observations[-1] if observations else None


def _format_value(value: float, unit: str) -> str:
    if unit == "USD":
        return f"${value:,.2f}tn"
    if unit == "people":
        return f"{value:,.2f}bn"
    if abs(value) >= 100:
        return f"{value:,.0f}"
    if abs(value) >= 10:
        return f"{value:,.1f}"
    return f"{value:,.2f}"


def _chart_html(series: dict[str, Any]) -> str:
    observations = series.get("observations") or []
    if not observations:
        return ""
    chart_id = f"chart-{series['id']}"
    actual_through = series.get("actual_through")
    traces: list[dict[str, Any]] = []
    if actual_through:
        actual = [item for item in observations if (_parse_year(item["date"]) or 9999) <= int(actual_through)]
        forecast = [item for item in observations if (_parse_year(item["date"]) or 0) >= int(actual_through)]
        if actual:
            traces.append({
                "name": "Actual / history",
                "x": [item["date"] for item in actual],
                "y": [item["value"] for item in actual],
                "mode": "lines",
                "line": {"color": ACCENT, "width": 2.4},
                "type": "scatter",
            })
        if forecast:
            traces.append({
                "name": "IMF WEO estimate / forecast",
                "x": [item["date"] for item in forecast],
                "y": [item["value"] for item in forecast],
                "mode": "lines",
                "line": {"color": "#364b61", "width": 2.2, "dash": "dash"},
                "type": "scatter",
            })
    else:
        traces.append({
            "name": series["label_en"],
            "x": [item["date"] for item in observations],
            "y": [item["value"] for item in observations],
            "mode": "lines",
            "line": {"color": ACCENT, "width": 2.4},
            "type": "scatter",
        })

    layout = {
        "height": 360,
        "margin": {"l": 52, "r": 18, "t": 20, "b": 46},
        "paper_bgcolor": PAPER,
        "plot_bgcolor": PAPER,
        "font": {
            "family": "Avenir Next, PingFang SC, Hiragino Sans GB, Noto Sans SC, Segoe UI, sans-serif",
            "size": 12,
            "color": INK,
        },
        "xaxis": {"gridcolor": "rgba(23,19,16,0.08)", "autorange": True, "automargin": True},
        "yaxis": {
            "title": series.get("unit", ""),
            "gridcolor": "rgba(23,19,16,0.08)",
            "autorange": True,
            "automargin": True,
        },
        "legend": {"orientation": "h", "y": -0.24},
        "hovermode": "x unified",
        "autosize": True,
    }
    latest = _latest(series)
    latest_text = ""
    if latest:
        latest_text = f"{escape(str(latest['date']))} · {_format_value(float(latest['value']), series.get('unit', ''))} {escape(series.get('unit', ''))}"
    quality = escape(series.get("quality_status", "unchecked").replace("_", " "))
    caveat_en = escape(series.get("caveat_en", ""))
    caveat_zh = escape(series.get("caveat_zh", ""))
    source_url = escape(series.get("source_url") or series.get("api_url") or "#")
    return f"""
<article class="chart-card chart-quality-{escape(series.get('quality_status', 'unchecked'))}">
  <div class="chart-head">
    <div>
      <h3><span data-lang="en">{escape(series['label_en'])}</span><span data-lang="zh">{escape(series['label_zh'])}</span></h3>
      <p>{latest_text}</p>
    </div>
    <span class="quality-pill">{quality}</span>
  </div>
  <div id="{chart_id}" class="plotly-chart"></div>
  <script>
    Plotly.newPlot("{chart_id}", {_json(traces)}, {_json(layout)}, {{displayModeBar:"hover", displaylogo:false, responsive:true}});
  </script>
  <footer>
    <span>Source: <a href="{source_url}" target="_blank" rel="noreferrer">{escape(series.get('source_name', 'unknown'))}</a></span>
    <span>Series: {escape(series.get('series', ''))}</span>
    <span>Frequency: {escape(series.get('frequency', ''))}</span>
    <span>Provider update: {escape(series.get('provider_updated', '') or 'n/a')}</span>
  </footer>
  <p class="caveat"><span data-lang="en">{caveat_en}</span><span data-lang="zh">{caveat_zh}</span></p>
</article>
"""


def _render_cards(series_list: list[dict[str, Any]], pbc_cards: list[dict[str, Any]]) -> str:
    headline_ids = ["real_gdp_growth", "cpi_inflation", "usd_cny_midpoint", "general_gov_debt"]
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
    for card in pbc_cards:
        cards.append(f"""
<div class="data-card">
  <span><span data-lang="en">{escape(card['label_en'])}</span><span data-lang="zh">{escape(card['label_zh'])}</span></span>
  <strong>{escape(str(card.get('value', 'n/a')))}</strong>
  <small>{escape(str(card.get('updated', 'n/a')))} · PBC</small>
</div>""")
    return "\n".join(cards)


def _section_nav(config: dict[str, Any]) -> str:
    links = []
    for section_id, section in config.get("sections", {}).items():
        links.append(
            f'<a href="#{escape(section_id)}"><span data-lang="en">{escape(section["title_en"])}</span>'
            f'<span data-lang="zh">{escape(section["title_zh"])}</span></a>'
        )
    links.append('<a href="#data-gaps"><span data-lang="en">Data Gaps</span><span data-lang="zh">数据缺口</span></a>')
    return "\n".join(links)


def _sections_html(config: dict[str, Any], series_list: list[dict[str, Any]]) -> str:
    by_section: dict[str, list[dict[str, Any]]] = {}
    for item in series_list:
        if item.get("observations"):
            by_section.setdefault(item["section"], []).append(item)
    html_parts: list[str] = []
    for section_id, section in config.get("sections", {}).items():
        charts = "\n".join(_chart_html(item) for item in by_section.get(section_id, []))
        empty = ""
        if not charts:
            empty = '<div class="empty-note"><span data-lang="en">No reproducible public chart wired yet for this section.</span><span data-lang="zh">本节暂未接入可复跑的公开图表数据。</span></div>'
        html_parts.append(f"""
<section class="panel" id="{escape(section_id)}">
  <div class="section-title">
    <p>PDF logic</p>
    <h2><span data-lang="en">{escape(section['title_en'])}</span><span data-lang="zh">{escape(section['title_zh'])}</span></h2>
    <div class="logic"><span data-lang="en">{escape(section['report_logic_en'])}</span><span data-lang="zh">{escape(section['report_logic_zh'])}</span></div>
  </div>
  <div class="charts-grid">
    {charts}
    {empty}
  </div>
</section>""")
    return "\n".join(html_parts)


def _gaps_html(config: dict[str, Any]) -> str:
    sections = config.get("sections", {})
    rows = []
    for gap in config.get("data_gaps", []):
        section = sections.get(gap["section"], {})
        rows.append(f"""
<tr>
  <td><span data-lang="en">{escape(section.get('title_en', gap['section']))}</span><span data-lang="zh">{escape(section.get('title_zh', gap['section']))}</span></td>
  <td><span data-lang="en">{escape(gap['item_en'])}</span><span data-lang="zh">{escape(gap['item_zh'])}</span></td>
  <td><span data-lang="en">{escape(gap['status_en'])}</span><span data-lang="zh">{escape(gap['status_zh'])}</span></td>
</tr>""")
    return "\n".join(rows)


CSS = """
:root {
  --bg: #f4efe7;
  --fg: #171310;
  --muted: #63574e;
  --accent: #8a593d;
  --accent-soft: rgba(138, 89, 61, 0.12);
  --border: rgba(23, 19, 16, 0.14);
  --card: rgba(255, 252, 246, 0.76);
  --blue: #364b61;
  --warn: #9d6a2e;
  --low: #9d3d2e;
  --font-display: "Iowan Old Style", "Songti SC", "Noto Serif SC", Georgia, serif;
  --font-body: "Avenir Next", "PingFang SC", "Hiragino Sans GB", "Noto Sans SC", "Segoe UI", sans-serif;
}
* { box-sizing: border-box; }
html { scroll-behavior: smooth; }
html[lang="en"] [data-lang="zh"] { display: none !important; }
html[lang="zh"] [data-lang="en"] { display: none !important; }
html:not([lang="zh"]) [data-lang="zh"] { display: none !important; }
body {
  margin: 0;
  background:
    radial-gradient(circle at top left, rgba(138, 89, 61, 0.15), transparent 24%),
    radial-gradient(circle at top right, rgba(54, 75, 97, 0.12), transparent 22%),
    linear-gradient(180deg, #f8f4ed 0%, #f4efe7 48%, #efe7db 100%);
  color: var(--fg);
  font-family: var(--font-body);
  line-height: 1.6;
}
body::before {
  content: "";
  position: fixed;
  inset: 0;
  pointer-events: none;
  background:
    linear-gradient(to right, rgba(23, 19, 16, 0.025) 1px, transparent 1px),
    linear-gradient(to bottom, rgba(23, 19, 16, 0.02) 1px, transparent 1px);
  background-size: 48px 48px;
  mask-image: linear-gradient(180deg, rgba(0, 0, 0, 0.45), transparent 85%);
}
a { color: inherit; }
.topbar {
  position: sticky;
  top: 0;
  z-index: 20;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 12px 32px;
  background: rgba(244, 239, 231, 0.86);
  border-bottom: 1px solid var(--border);
  backdrop-filter: blur(14px);
  font-size: 11px;
  letter-spacing: 0.12em;
  text-transform: uppercase;
}
.brand { font-family: var(--font-display); font-size: 15px; letter-spacing: 0.16em; white-space: nowrap; }
.brand span { color: var(--accent); }
.country-nav { display: flex; gap: 5px; flex-wrap: wrap; align-items: center; }
.country-nav a {
  text-decoration: none;
  color: var(--muted);
  border: 1px solid var(--border);
  border-radius: 999px;
  padding: 5px 12px;
}
.country-nav a.active { background: var(--fg); color: var(--bg); border-color: var(--fg); }
.lang-toggle {
  border: 1px solid var(--border);
  background: rgba(255,252,246,0.7);
  color: var(--fg);
  border-radius: 999px;
  padding: 6px 12px;
  cursor: pointer;
  font: inherit;
}
.container { position: relative; max-width: 1320px; margin: 0 auto; padding: 38px 24px 56px; }
header { border-bottom: 1px solid var(--border); padding: 36px 0 30px; margin-bottom: 24px; }
h1 {
  margin: 0;
  max-width: 980px;
  font-family: var(--font-display);
  font-size: clamp(36px, 6vw, 76px);
  font-weight: 500;
  letter-spacing: -0.06em;
  line-height: 0.92;
}
.subtitle { max-width: 880px; color: var(--muted); font-size: 16px; margin-top: 16px; }
.meta-row { display: flex; gap: 10px; flex-wrap: wrap; margin-top: 18px; }
.meta-chip {
  border: 1px solid var(--border);
  background: rgba(255,252,246,0.48);
  border-radius: 999px;
  padding: 5px 13px;
  color: var(--muted);
  font-size: 12px;
}
.toc {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  margin: 20px 0 28px;
}
.toc a {
  text-decoration: none;
  border: 1px solid var(--border);
  border-radius: 999px;
  padding: 7px 12px;
  background: var(--card);
  color: var(--muted);
  font-size: 12px;
}
.data-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(170px, 1fr));
  gap: 10px;
  margin-bottom: 24px;
}
.data-card, .chart-card, .panel, .data-note, .gaps-table {
  background: var(--card);
  border: 1px solid var(--border);
}
.data-card { padding: 16px; min-height: 118px; }
.data-card span {
  display: block;
  color: var(--muted);
  font-size: 11px;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}
.data-card strong {
  display: block;
  font-family: var(--font-display);
  font-size: 30px;
  font-weight: 500;
  line-height: 1.05;
  margin: 12px 0 8px;
}
.data-card small { color: var(--muted); }
.panel { padding: 26px; margin-bottom: 26px; }
.section-title { display: grid; grid-template-columns: 180px 1fr; gap: 18px; align-items: baseline; border-bottom: 1px solid var(--border); padding-bottom: 16px; margin-bottom: 18px; }
.section-title p {
  margin: 0;
  color: var(--accent);
  font-size: 11px;
  letter-spacing: 0.12em;
  text-transform: uppercase;
}
.section-title h2 {
  margin: 0;
  font-family: var(--font-display);
  font-size: clamp(26px, 3.2vw, 44px);
  font-weight: 500;
  letter-spacing: -0.04em;
}
.logic { grid-column: 2; color: var(--muted); max-width: 860px; }
.charts-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(min(520px, 100%), 1fr)); gap: 16px; margin-bottom: 20px; }
.chart-card { padding: 16px; min-width: 0; overflow: hidden; transition: transform 0.16s ease, border-color 0.16s ease; }
.chart-card:hover { transform: translateY(-2px); border-color: rgba(23,19,16,0.26); }
.chart-head { display: flex; justify-content: space-between; gap: 14px; align-items: flex-start; border-bottom: 1px solid var(--border); padding-bottom: 10px; margin-bottom: 8px; }
.chart-head > div { min-width: 0; }
.chart-head h3 { margin: 0; font-family: var(--font-display); font-size: 22px; font-weight: 500; letter-spacing: -0.02em; }
.chart-head p { margin: 4px 0 0; color: var(--muted); font-size: 12px; }
.quality-pill {
  border: 1px solid var(--border);
  border-radius: 999px;
  padding: 4px 9px;
  color: var(--muted);
  font-size: 11px;
  white-space: nowrap;
}
.chart-quality-verified .quality-pill { color: #3f6f50; border-color: rgba(63,111,80,0.35); }
.chart-quality-watch .quality-pill { color: var(--warn); border-color: rgba(157,106,46,0.35); }
.chart-quality-low_confidence .quality-pill { color: var(--low); border-color: rgba(157,61,46,0.35); }
.plotly-chart { width: 100%; min-width: 0; height: 360px; }
.plot-container, .svg-container { max-width: 100% !important; }
#js-plotly-tester { width: 1px !important; max-width: 1px !important; overflow: hidden !important; }
.chart-card footer {
  display: grid;
  gap: 3px;
  color: var(--muted);
  font-size: 11px;
  border-top: 1px solid var(--border);
  padding-top: 10px;
}
.chart-card footer a { color: var(--accent); }
.caveat { color: var(--muted); font-size: 12px; margin: 10px 0 0; }
.empty-note { padding: 20px; color: var(--muted); border: 1px dashed var(--border); }
.data-note { padding: 18px; margin-bottom: 26px; color: var(--muted); }
.gaps-table { width: 100%; border-collapse: collapse; font-size: 13px; }
.gaps-table th, .gaps-table td { padding: 12px; border-bottom: 1px solid var(--border); vertical-align: top; text-align: left; }
.gaps-table th { color: var(--muted); font-size: 11px; letter-spacing: 0.08em; text-transform: uppercase; }
footer.page-footer { color: var(--muted); border-top: 1px solid var(--border); padding-top: 20px; font-size: 12px; }
@media (max-width: 760px) {
  .topbar { align-items: flex-start; flex-direction: column; padding: 12px 18px; }
  .container { padding: 28px 16px 42px; }
  .section-title { grid-template-columns: 1fr; }
  .logic { grid-column: 1; }
  .charts-grid { grid-template-columns: 1fr; }
  .chart-card { padding: 13px; }
  .chart-head { flex-direction: column; gap: 8px; }
  .chart-head h3 { font-size: 19px; }
  .plotly-chart { height: 320px; }
}
"""


def render_html(config: dict[str, Any], series_list: list[dict[str, Any]], cards: list[dict[str, Any]]) -> str:
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
<title>China Dashboard</title>
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
    <a href="china_2026Q2_v1.html" class="active">CN</a>
    <a href="uk_2026Q2_v1.html">UK</a>
    <a href="us_2026Q2_v1.html">US</a>
  </nav>
  <button class="lang-toggle" onclick="toggleLang()" id="lang-btn">中文</button>
</div>

<main class="container">
  <header>
    <h1><span data-lang="en">China Dashboard</span><span data-lang="zh">中国 Dashboard</span></h1>
    <p class="subtitle"><span data-lang="en">A chart-and-data-only China macro page aligned to the report logic in <em>Understanding China's Economic Statistics</em>. It uses reproducible public sources only; missing China-native monthly indicators are called out rather than proxied.</span><span data-lang="zh">一个仅聚焦图表和数据的中国宏观页面，结构对齐 <em>Understanding China's Economic Statistics</em> 的报告逻辑。页面仅使用可复跑公开来源；尚未稳定接入的中国本土月度指标会明确列为缺口，不用 proxy 替代。</span></p>
    <div class="meta-row">
      <span class="meta-chip">{chart_count} <span data-lang="en">charts</span><span data-lang="zh">张图</span></span>
      <span class="meta-chip">{source_count} <span data-lang="en">public source groups</span><span data-lang="zh">组公开来源</span></span>
      <span class="meta-chip">{gap_count} <span data-lang="en">official-data gaps tracked</span><span data-lang="zh">个官方数据缺口</span></span>
      <span class="meta-chip">{low_count} <span data-lang="en">low-confidence charts</span><span data-lang="zh">张低置信图</span></span>
    </div>
  </header>

  <section class="data-grid" aria-label="latest data cards">
    {_render_cards(series_list, cards)}
  </section>

  <nav class="toc" aria-label="section navigation">
    {_section_nav(config)}
  </nav>

  <div class="data-note">
    <span data-lang="en">Data policy: no fabricated proxies. World Bank and IMF annual series provide the durable public skeleton; SAFE provides official daily RMB fixing data; PBC cards show latest official monetary prints where history is not yet wired.</span>
    <span data-lang="zh">数据原则：不制造 proxy。World Bank 与 IMF 年度序列提供可维护的公开骨架；SAFE 提供官方人民币日度中间价；PBC 卡片展示暂未接入历史序列的最新官方货币数据。</span>
  </div>

  {_sections_html(config, series_list)}

  <section class="panel" id="data-gaps">
    <div class="section-title">
      <p>Pipeline</p>
      <h2><span data-lang="en">Official Data Gaps</span><span data-lang="zh">官方数据缺口</span></h2>
      <div class="logic"><span data-lang="en">These are PDF-native indicators that matter for China but are not yet rendered because a reproducible public adapter has not been validated.</span><span data-lang="zh">这些是报告逻辑中的中国本土核心指标，但由于尚未验证可复跑的公开 adapter，当前暂不渲染为图。</span></div>
    </div>
    <table class="gaps-table">
      <thead><tr><th>Section</th><th>Indicator family</th><th>Status</th></tr></thead>
      <tbody>{_gaps_html(config)}</tbody>
    </table>
  </section>

  <footer class="page-footer">
    <span data-lang="en">Research artefact only, not investment advice. Generated {generated_date} from <code>config/china_indicators.yaml</code>.</span>
    <span data-lang="zh">仅为研究工具，不构成投资建议。生成日期 {generated_date}，配置来源 <code>config/china_indicators.yaml</code>。</span>
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
  <!-- China dashboard card -->
  <a href="china_2026Q2_v1.html" class="card clean">
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


def build() -> Path:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    config = _load_config()
    series_list, cards = fetch_all(config)
    _write_clean(OUT_HTML, render_html(config, series_list, cards))

    charted = [item for item in series_list if item.get("observations")]
    usd_cny = next((item for item in charted if item["id"] == "usd_cny_midpoint"), None)
    usd_latest = _latest(usd_cny) if usd_cny else None
    summary = {
        "file": OUT_HTML.name,
        "generated": datetime.now(UTC).isoformat(),
        "charts": len(charted),
        "source_groups": len({item.get("source_name") for item in charted}),
        "data_gaps": len(config.get("data_gaps", [])),
        "low_confidence": sum(1 for item in charted if item.get("quality_status") == "low_confidence"),
        "usd_cny_latest": (
            f"{float(usd_latest['value']):.4f} ({usd_latest['date']})" if usd_latest else "n/a"
        ),
    }
    SUMMARY_JSON.write_text(json.dumps(summary, indent=2, ensure_ascii=False))
    inject_index(summary)
    if not os.environ.get("COUNTRY_PRIMER_SKIP_ARCHIVE"):
        from build_dashboard_archive import build_archive
        build_archive()
    return OUT_HTML


if __name__ == "__main__":
    path = build()
    print(f"Wrote {path} ({path.stat().st_size:,} bytes)")
