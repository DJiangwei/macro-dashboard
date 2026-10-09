SUMMARY_KEY_IDS = [
    "real_gdp_growth",
    "industrial_value_added_yoy_akshare",
    "fixed_asset_investment_yoy_akshare",
    "commercial_housing_sales_value_eastmoney",
    "real_estate_development_investment_ytd_eastmoney",
    "passenger_vehicle_retail_cpca",
    "new_energy_vehicle_share_cpca",
    "customs_exports_yoy_akshare",
    "usd_cny_midpoint",
    "m2_yoy_akshare",
    "financial_institution_deposits_stock_akshare",
    "vegetable_basket_price_index_akshare",
    "pbc_total_assets_akshare",
    "pbc_reserve_money_akshare",
    "cpi_yoy_akshare",
    "ppi_yoy_akshare",
]

def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False)

def _write_clean(path: Path, content: str) -> None:
    path.write_text("\n".join(line.rstrip() for line in content.splitlines()) + "\n")

def _parse_year(value: str) -> int | None:
    try:
        return int(str(value)[:4])
    except (TypeError, ValueError):
        return None

def _latest(series: dict[str, Any]) -> dict[str, Any] | None:
    observations = series.get("observations") or []
    if not observations:
        return None

    actual_through = series.get("actual_through")
    if actual_through not in (None, ""):
        try:
            cutoff_year = int(actual_through)
        except (TypeError, ValueError):
            cutoff_year = None
        if cutoff_year is not None:
            actual = [
                item for item in observations
                if (_parse_year(str(item.get("date", ""))) or 9999) <= cutoff_year
            ]
            if actual:
                return actual[-1]

    observed = [
        item for item in observations
        if not bool(item.get("is_projection"))
        and str(item.get("observation_type") or "").lower() not in {"forecast", "projection"}
    ]
    return observed[-1] if observed else observations[-1]

def _format_period(date_text: str, frequency: str, locale: str) -> str:
    text = str(date_text or "")
    try:
        parsed = datetime.strptime(text[:10], "%Y-%m-%d")
    except ValueError:
        year = _parse_year(text)
        return f"{year}年" if year and locale == "zh" else str(year or text)

    frequency = str(frequency or "").lower()
    if frequency == "annual":
        return f"{parsed.year}年" if locale == "zh" else str(parsed.year)
    if frequency == "quarterly":
        quarter = ((parsed.month - 1) // 3) + 1
        return f"{parsed.year}年 Q{quarter}" if locale == "zh" else f"Q{quarter} {parsed.year}"
    if frequency == "monthly":
        return f"{parsed.year}年{parsed.month}月" if locale == "zh" else parsed.strftime("%b %Y")
    if locale == "zh":
        return f"{parsed.year}年{parsed.month}月{parsed.day}日"
    return f"{parsed.day} {parsed.strftime('%b %Y')}"

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

def _chart_html(series: dict[str, Any], country_code: str) -> str:
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

    latest = _latest(series)
    if latest:
        traces.append({
            "name": "Latest observation",
            "meta": "cp-latest-marker",
            "x": [latest["date"]],
            "y": [latest["value"]],
            "mode": "markers",
            "marker": {
                "size": 9,
                "color": ACCENT,
                "line": {"width": 2, "color": "#fffdf8"},
            },
            "showlegend": False,
            "hovertemplate": "Latest: %{y}<extra></extra>",
            "cliponaxis": False,
            "type": "scatter",
        })

    layout = {
        "height": 360,
        "margin": {"l": 52, "r": 26, "t": 20, "b": 46},
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
    latest_reading = ""
    if latest:
        value = _format_value(float(latest["value"]), series.get("unit", ""))
        unit = escape(series.get("unit", ""))
        date_text = escape(str(latest["date"]))
        period_en = escape(_format_period(str(latest["date"]), series.get("frequency", ""), "en"))
        period_zh = escape(_format_period(str(latest["date"]), series.get("frequency", ""), "zh"))
        latest_reading = f"""
      <div class="latest-reading" data-latest-reading data-latest-date="{date_text}">
        <span class="latest-label"><span data-lang="en">Latest observation</span><span data-lang="zh">最新读数</span></span>
        <span class="latest-value"><strong>{value}</strong><em>{unit}</em></span>
        <time datetime="{date_text}"><span data-lang="en">{period_en}</span><span data-lang="zh">{period_zh}</span></time>
      </div>"""
    quality_data = series.get("data_quality") or {}
    authority = escape(str(quality_data.get("source_authority", "")).replace("_", " "))
    freshness = escape(str(quality_data.get("freshness", "")).replace("_", " "))
    quality = escape(series.get("quality_status", "unchecked").replace("_", " "))
    chips = (
        f'<span class="quality-pill">{quality}</span>'
        f'<span class="authority-chip">{authority}</span>'
        f'<span class="freshness-chip">{freshness}</span>'
    )
    caveat_en = escape(series.get("caveat_en", ""))
    caveat_zh = escape(series.get("caveat_zh", ""))
    source_url = escape(series.get("source_url") or series.get("api_url") or "#")
    concept_id = concept_id_for(country_code, str(series["id"]))
    view = "deep" if ":" in concept_id else "core"
    cross = series.get("cross_check") or {}
    cross_html = ""
    if cross:
        status = cross["status"]
        window_months = cross.get("window_months")
        window_label = f"last {window_months} months" if window_months else "recent window"
        if status == "insufficient":
            # No overlapping observations in the recent window (and possibly none
            # at all) — nothing to agree or diverge on, so say so plainly rather
            # than formatting fields (e.g. `latest_diff`) that may be None here.
            mark = "— No recent overlap for"
            headline = f"{window_label}: no common periods to compare"
            cls = "cross-check"
        elif status in {"agree", "minor"}:
            mark = "✓ Agrees with"
            headline = (
                f"{window_label}: {cross['window_n_common']} common periods, "
                f"max gap {cross['window_max_abs_diff']:.2f} (tolerance {cross['tolerance']:.2f})"
            )
            cls = "cross-check"
        else:
            mark = "⚠ Diverges from"
            headline = (
                f"{window_label}: {cross['window_n_breaches']} of {cross['window_n_common']} periods "
                f"beyond tolerance {cross['tolerance']:.2f}, latest gap {cross['latest_diff']:.2f} "
                f"({cross['last_breach_date']})"
            )
            cls = "cross-check diverged"
        if cross["n_breaches"]:
            history = (
                f"Full history: {cross['n_breaches']} of {cross['n_common']} periods beyond tolerance "
                f"(most recently {cross['last_breach_date']}; max gap {cross['max_abs_diff']:.2f})."
            )
        else:
            history = f"Full history: no breaches across {cross['n_common']} common periods."
        cross_html = (
            f'\n  <p class="{cls}">{mark} <strong>{escape(cross["label_en"])}</strong> · {escape(headline)}'
            f'<br><span class="cross-check-history">{escape(history)}</span></p>'
        )
    return f"""
<article class="chart-card chart-quality-{escape(series.get('quality_status', 'unchecked'))}" data-dashboard-view="{view}" data-concept-id="{escape(concept_id)}">
  <div class="chart-head">
    <div class="chart-title">
      <h3><span data-lang="en">{escape(series['label_en'])}</span><span data-lang="zh">{escape(series['label_zh'])}</span></h3>
    </div>
    <div class="chart-status">
      {latest_reading}
      {chips}
    </div>
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
  </footer>{cross_html}
  <p class="caveat"><span data-lang="en">{caveat_en}</span><span data-lang="zh">{caveat_zh}</span></p>
</article>
"""

def _section_nav(config: dict[str, Any]) -> str:
    links = []
    for section_id, section in config.get("sections", {}).items():
        links.append(
            f'<a href="#{escape(section_id)}"><span data-lang="en">{escape(section["title_en"])}</span>'
            f'<span data-lang="zh">{escape(section["title_zh"])}</span></a>'
        )
    links.append('<a href="#data-gaps"><span data-lang="en">Data Gaps</span><span data-lang="zh">数据缺口</span></a>')
    return "\n".join(links)

def _sections_html(config: dict[str, Any], series_list: list[dict[str, Any]], country_code: str) -> str:
    by_section: dict[str, list[dict[str, Any]]] = {}
    for item in series_list:
        if item.get("observations"):
            by_section.setdefault(item["section"], []).append(item)
    html_parts: list[str] = []
    for section_id, section in config.get("sections", {}).items():
        charts = "\n".join(_chart_html(item, country_code) for item in by_section.get(section_id, []))
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
.view-switch {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  margin: -12px 0 26px;
}
.view-switch > span { color: var(--muted); font-size: 12px; margin-right: 3px; }
.view-switch button {
  border: 1px solid var(--border);
  border-radius: 999px;
  padding: 7px 13px;
  background: var(--card);
  color: var(--muted);
  cursor: pointer;
  font: inherit;
  font-size: 12px;
}
.view-switch button[aria-pressed="true"] { background: var(--fg); color: var(--bg); border-color: var(--fg); }
body[data-dashboard-view="core"] .chart-card[data-dashboard-view="deep"] { display: none; }
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
.chart-head { display: flex; justify-content: space-between; gap: 18px; align-items: stretch; border-bottom: 1px solid var(--border); padding-bottom: 12px; margin-bottom: 8px; }
.chart-title { min-width: 0; flex: 1 1 auto; padding-top: 2px; }
.chart-head h3 { margin: 0; font-family: var(--font-display); font-size: 22px; font-weight: 500; letter-spacing: -0.02em; }
.chart-status { display: flex; align-items: flex-start; gap: 10px; flex: 0 0 auto; }
.latest-reading {
  display: grid;
  grid-template-columns: auto auto;
  column-gap: 9px;
  align-items: baseline;
  min-width: 160px;
  padding-left: 14px;
  border-left: 1px solid var(--border);
  font-variant-numeric: tabular-nums;
}
.latest-label {
  grid-column: 1 / -1;
  color: var(--accent);
  font-size: 9px;
  font-weight: 700;
  letter-spacing: 0.1em;
  line-height: 1.2;
  text-transform: uppercase;
}
.latest-value { display: inline-flex; align-items: baseline; gap: 5px; min-width: 0; }
.latest-value strong {
  font-family: var(--font-display);
  font-size: 24px;
  font-weight: 600;
  line-height: 1;
  letter-spacing: -0.035em;
  color: var(--fg);
  white-space: nowrap;
}
.latest-value em { color: var(--muted); font-size: 9px; font-style: normal; white-space: nowrap; }
.latest-reading time { color: var(--muted); font-size: 10px; white-space: nowrap; }
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
.authority-chip, .freshness-chip {
  font-size: 11px; letter-spacing: .02em; padding: 2px 7px; border-radius: 999px;
  border: 1px solid rgba(23,19,16,0.16); color: var(--muted, #63574e); margin-left: 6px;
}
.authority-chip { background: rgba(63,111,80,0.10); }
.freshness-chip { background: rgba(54,75,97,0.10); }
.cross-check { font-size: 12px; color: #63574e; margin-top: 4px; }
.cross-check.diverged { color: #9d3d2e; }
.cross-check-history { color: var(--muted); }
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
  .panel { overflow-x: auto; }
  .chart-card { padding: 13px; }
  .chart-head { flex-direction: column; gap: 8px; }
  .chart-head h3 { font-size: 19px; }
  .chart-status { width: 100%; justify-content: space-between; align-items: center; }
  .latest-reading { flex: 1 1 auto; min-width: 0; border-left: 0; border-top: 1px solid var(--border); padding: 8px 0 0; }
  .latest-value strong { font-size: 22px; }
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
<body data-dashboard-view="core">
<div class="topbar">
  <a href="../index.html" style="text-decoration:none;color:inherit;"><div class="brand">East Meridian <span>/ Macro Dashboard</span></div></a>
  <nav class="country-nav" aria-label="country dashboards">
    <a href="hungary.html">HU</a>
    <a href="poland.html">PL</a>
    <a href="czechia.html">CZ</a>
    <a href="romania.html">RO</a>
    <a href="china.html" class="active">CN</a>
    <a href="japan.html">JP</a>
    <a href="south_africa.html">ZA</a>
    <a href="uk.html">UK</a>
    <a href="us.html">US</a>
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

  <div class="view-switch" role="group" aria-label="chart density">
    <span><span data-lang="en">Chart view</span><span data-lang="zh">图表视图</span></span>
    <button type="button" data-view-option="core" aria-pressed="true" onclick="setDashboardView('core')"><span data-lang="en">Core 48</span><span data-lang="zh">核心 48</span></button>
    <button type="button" data-view-option="deep" aria-pressed="false" onclick="setDashboardView('deep')"><span data-lang="en">All deep-dive charts</span><span data-lang="zh">全部深度指标</span></button>
  </div>

  <div class="data-note">
    <span data-lang="en">Data policy: no fabricated proxies. World Bank and IMF annual series provide the durable public skeleton; SAFE provides official daily RMB fixing data; PBC cards show latest official monetary prints where history is not yet wired.</span>
    <span data-lang="zh">数据原则：不制造 proxy。World Bank 与 IMF 年度序列提供可维护的公开骨架；SAFE 提供官方人民币日度中间价；PBC 卡片展示暂未接入历史序列的最新官方货币数据。</span>
  </div>

  {_sections_html(config, series_list, "CN")}

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
  <!-- China dashboard card -->
  <a href="china.html" class="card clean">
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