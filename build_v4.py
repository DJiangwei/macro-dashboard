"""Build v4 expanded HTML for HU, PL, CZ, RO — 9-section macro dashboard with
financial stability, demographics, and political economy sections (v4 expansion).

Usage:
  python build_v4.py HU    # Hungary only
  python build_v4.py PL    # Poland only
  python build_v4.py CZ    # Czechia only
  python build_v4.py RO    # Romania only
  python build_v4.py ALL   # all four
"""
from pathlib import Path
import re
import sys
import json
from html import escape

# ── Chart HTML generator for new v4 indicators ────────────────────────────────

def _make_plotly_chart(chart_id, title, traces, y_title="", height=380, extra_layout=None):
    """Generate a self-contained Plotly chart div + script tag.

    Args:
        chart_id: HTML element ID
        title: Chart title string
        traces: list of dicts with {name, x, y, line_color, line_width, dash}
        y_title: y-axis label
        height: chart height in px
        extra_layout: optional dict merged into Plotly layout
    """
    trace_js = []
    for t in traces:
        lc = t.get("line_color", "#8a593d")
        lw = t.get("line_width", 2.2)
        dash = t.get("dash", "solid")
        trace_js.append(f'''{{"line":{{"color":"{lc}","width":{lw}{f',"dash":"{dash}"' if dash != "solid" else ""}}},"mode":"lines","name":"{t['name']}","x":{json.dumps(t['x'])},"y":{json.dumps(t['y'])},"type":"scatter"}}''')

    layout = f'''{{"title":{{"text":{json.dumps(title)},"font":{{"size":13,"color":"#171310"}}}},"height":{height},"margin":{{"l":50,"r":20,"t":40,"b":40}},"xaxis":{{"gridcolor":"rgba(23,19,16,0.08)","autorange":true}},"yaxis":{{"title":{json.dumps(y_title)},"gridcolor":"rgba(23,19,16,0.08)","autorange":true}},"legend":{{"orientation":"h","y":-0.2}},"paper_bgcolor":"rgba(255,252,246,0.90)","plot_bgcolor":"rgba(255,252,246,0.90)","font":{{"family":"Avenir Next, PingFang SC, Hiragino Sans GB, Noto Sans SC, Segoe UI, Helvetica Neue, Arial, sans-serif","size":11,"color":"#171310"}}}}'''

    if extra_layout:
        layout = layout[:-2] + "," + json.dumps(extra_layout)[1:]

    traces_str = ",\n".join(trace_js)
    return f'''<div><div id="{chart_id}" class="plotly-graph-div" style="height:{height}px;width:100%;"></div>
<script type="text/javascript">
window.PLOTLYENV=window.PLOTLYENV||{{}};
if(document.getElementById("{chart_id}")){{
Plotly.newPlot("{chart_id}",[{traces_str}],{layout});
}}
</script></div>'''

ROOT = Path(__file__).parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from country_primer.data_fetcher import (  # noqa: E402
    DataPipeline,
    INDICATOR_MANIFEST_48,
    LEGACY_INDICATOR_KEYS,
    SECTION_INDICATORS_48,
    fetch_canonical_macro_frame,
)
from country_primer.catalog import load_countries  # noqa: E402

OUTPUT = ROOT / "output"


def _html_text(value):
    """Render config text safely while preserving readable line breaks."""
    return escape(str(value or "")).replace("\n", "<br>")


def _render_central_bank_section(country_code):
    """Render the central-bank section from live YAML config, not stale base HTML."""
    meta = load_countries().get(country_code, {})
    cb_section = meta.get("central_bank_section") or {}
    if not cb_section:
        return ""

    board_items = "\n".join(f"<li>{_html_text(member)}</li>" for member in cb_section.get("board", []))
    balance_sheet = cb_section.get("balance_sheet") or {}
    bs_items = "\n".join(f"<li>{_html_text(item)}</li>" for item in balance_sheet.get("key_items", []))

    return f"""
<section class="panel" id="central_bank">
  <h2>Central Bank Deep-Dive</h2>
  <div class="cb-grid">
    <div class="cb-card">
      <div class="cb-card-header">Leadership &amp; Decision-Making</div>
      <div class="cb-card-body">
        <p><strong>Governor:</strong> {_html_text(cb_section.get("governor", ""))}</p>
        <p><strong>Board:</strong></p>
        <ul>
          {board_items}
        </ul>
        <p><strong>MPC:</strong> {_html_text(cb_section.get("mpc", ""))}</p>
        <p><strong>Meetings:</strong> {_html_text(cb_section.get("meeting_schedule", ""))}</p>
      </div>
    </div>
    <div class="cb-card">
      <div class="cb-card-header">Policy Framework</div>
      <div class="cb-card-body">{_html_text(cb_section.get("policy_framework", ""))}</div>
    </div>
    <div class="cb-card">
      <div class="cb-card-header">Balance Sheet</div>
      <div class="cb-card-body">
        <p><strong>Total Assets:</strong> {_html_text(balance_sheet.get("total_assets", ""))}</p>
        <ul>
          {bs_items}
        </ul>
      </div>
    </div>
    <div class="cb-card">
      <div class="cb-card-header">Key Risks &amp; Vulnerabilities</div>
      <div class="cb-card-body">{_html_text(cb_section.get("key_risks", ""))}</div>
    </div>
  </div>
</section>
"""

# ── Shared CSS (same as Hungary v3) ──────────────────────────────────────────

CSS = """
:root {
  --bg: #f4efe7;
  --bg-deep: #ece3d6;
  --fg: #171310;
  --muted: #63574e;
  --primary: #171310;
  --primary-light: #364b61;
  --accent: #8a593d;
  --accent-soft: rgba(138, 89, 61, 0.12);
  --danger: #9d3d2e;
  --success: #3f6f50;
  --border: rgba(23, 19, 16, 0.14);
  --card: rgba(255, 252, 246, 0.76);
  --card-alt: rgba(236, 227, 214, 0.48);
  --highlight: rgba(138, 89, 61, 0.12);
  --font-display: "Iowan Old Style", "Songti SC", "Noto Serif SC", "Palatino Linotype", "Book Antiqua", Georgia, serif;
  --font-body: "Avenir Next", "PingFang SC", "Hiragino Sans GB", "Noto Sans SC", "Segoe UI", "Helvetica Neue", Arial, sans-serif;
}
* { box-sizing: border-box; }
html { scroll-behavior: smooth; }
body {
  margin: 0;
  padding: 0;
  background:
    radial-gradient(circle at top left, rgba(138, 89, 61, 0.15), transparent 24%),
    radial-gradient(circle at top right, rgba(54, 75, 97, 0.12), transparent 22%),
    linear-gradient(180deg, #f8f4ed 0%, #f4efe7 48%, #efe7db 100%);
  color: var(--fg);
  font-family: var(--font-body);
  font-size: 14px;
  line-height: 1.6;
  -webkit-font-smoothing: antialiased;
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
html[lang="en"] [data-lang="zh"] { display: none !important; }
html[lang="zh"] [data-lang="en"] { display: none !important; }
html:not([lang="zh"]) [data-lang="zh"] { display: none !important; }
a { color: inherit; }
.topbar {
  position: sticky;
  top: 0;
  z-index: 100;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 24px;
  padding: 12px 32px;
  background: rgba(244, 239, 231, 0.84);
  color: var(--fg);
  border-bottom: 1px solid var(--border);
  backdrop-filter: blur(14px);
  box-shadow: none;
  font-size: 11px;
  letter-spacing: 0.12em;
  text-transform: uppercase;
}
.topbar .brand {
  font-family: var(--font-display);
  font-weight: 600;
  font-size: 15px;
  letter-spacing: 0.16em;
  white-space: nowrap;
}
.topbar .brand span { color: var(--accent); }
.topbar a { color: var(--accent) !important; text-decoration: none !important; }
.topbar a:hover { text-decoration: underline !important; }
.topbar .meta-item { color: var(--muted); margin-left: 20px; }
.country-nav { display: flex; gap: 4px; align-items: center; flex-wrap: wrap; }
.country-nav .nav-link {
  color: var(--muted) !important;
  text-decoration: none;
  padding: 5px 12px;
  border-radius: 999px;
  font-size: 11px;
  font-weight: 500;
  transition: all 0.15s;
  border: 1px solid var(--border);
}
.country-nav .nav-link:hover {
  background: var(--accent-soft);
  color: var(--fg) !important;
  border-color: rgba(23,19,16,0.22);
}
.country-nav .nav-link.active {
  background: var(--fg);
  color: var(--bg) !important;
  border-color: var(--fg);
  font-weight: 700;
}
.nav-separator { color: rgba(23,19,16,0.26); margin: 0 2px; }
.container {
  position: relative;
  max-width: 1280px;
  margin: 0 auto;
  padding: 28px 24px 48px;
}
header {
  background: transparent;
  color: var(--fg);
  padding: 48px 0 34px;
  margin-bottom: 24px;
  border-bottom: 1px solid var(--border);
  box-shadow: none;
  border-radius: 0;
  text-align: left;
}
header h1 {
  margin: 0;
  max-width: 980px;
  font-family: var(--font-display);
  font-size: clamp(28px, 4.2vw, 48px);
  font-weight: 500;
  letter-spacing: -0.05em;
  line-height: 0.96;
  color: var(--fg);
}
header .subtitle,
header .meta,
header p.subtitle {
  max-width: 900px;
  margin-top: 14px;
  color: var(--muted);
  font-size: 16px;
  line-height: 1.65;
  opacity: 1;
}
header .meta-row { display: flex; gap: 12px; margin-top: 16px; flex-wrap: wrap; }
header .meta-chip {
  background: rgba(255,255,255,0.28);
  border: 1px solid var(--border);
  border-radius: 999px;
  padding: 5px 14px;
  font-size: 12px;
}
header .meta-chip strong { color: var(--accent); }
.grid,
.snapshot,
.stats-bar,
.summary-grid,
.kpi-ribbon {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(210px, 1fr));
  gap: 12px;
  margin-bottom: 24px;
}
.card,
.tile,
.stat-card,
.summary-card,
.kpi-card,
.section-card,
.snapshot-panel,
section.panel,
.context-card,
.trade-card,
.cb-card {
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: 0;
  box-shadow: none;
}
.card {
  display: block;
  padding: 28px 24px;
  text-decoration: none;
  color: var(--fg);
  transition: transform 0.18s ease, background-color 0.18s ease, border-color 0.18s ease;
}
.card:hover,
.kpi-card:hover,
.chart-cell:hover {
  transform: translateY(-2px);
  background: rgba(255,252,246,0.95);
  border-color: rgba(23,19,16,0.26);
}
.card h2,
.section-card-header h2,
section.panel h2,
.snapshot-panel h2,
h3 {
  font-family: var(--font-display);
  font-weight: 500;
  color: var(--fg);
  letter-spacing: -0.02em;
}
.card h2 { margin: 0 0 8px; font-size: 32px; }
.card .meta,
.stat-card .stat-label,
.summary-card .label,
.kpi-card .kpi-label,
.tile .k,
.indicator-table th,
thead th,
.trade-card-body th {
  color: var(--muted);
  font-size: 11px;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}
.card .stats { display: grid; gap: 6px; font-size: 13px; }
.card .stats .stat {
  display: flex;
  justify-content: space-between;
  gap: 14px;
  padding: 7px 0;
  border-bottom: 1px solid var(--border);
}
.card .stats .value,
.tile .v,
.kpi-card .kpi-value,
.stat-card .stat-value,
.summary-card .num {
  font-family: var(--font-display);
  font-weight: 500;
  color: var(--fg);
}
.stat-card,
.summary-card,
.kpi-card,
.tile { padding: 14px 18px; }
.stat-card .stat-value,
.summary-card .num { font-size: 30px; }
.kpi-card { border-top: 3px solid var(--primary); }
.kpi-card.warn { border-top-color: var(--accent); }
.kpi-card.danger { border-top-color: var(--danger); }
.kpi-card .kpi-value { font-size: 24px; }
.kpi-delta-up { color: var(--success) !important; font-weight: 600; }
.kpi-delta-down { color: var(--danger) !important; font-weight: 600; }
.snapshot-group { margin-bottom: 18px; }
.snapshot-subtitle {
  margin: 0 0 10px;
  padding-bottom: 6px;
  border-bottom: 1px solid var(--border);
  color: var(--accent);
  font-size: 12px;
  font-weight: 600;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}
.snapshot-panel,
.section-card,
section.panel { padding: 0; margin-bottom: 24px; overflow: hidden; }
.snapshot-panel { padding: 22px 24px; }
.section-card-header,
.context-card-header,
.trade-card-header,
.cb-card-header,
.narrative-header {
  background: var(--fg);
  color: var(--bg);
  padding: 10px 18px;
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: 12px;
  font-weight: 600;
  letter-spacing: 0.04em;
  text-transform: uppercase;
}
.section-card-header h2 { margin: 0; font-size: 22px; color: var(--bg); }
.section-card-header .badge,
section.panel h2 .section-badge,
.source-badge,
.source-tag,
.tag,
.src-badge {
  display: inline-flex;
  align-items: center;
  min-height: 1.5rem;
  padding: 2px 9px;
  border-radius: 999px;
  border: 1px solid var(--border);
  background: var(--highlight);
  color: var(--accent);
  font-size: 10px;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  font-weight: 600;
}
.section-card-body,
.context-card-body,
.trade-card-body,
.cb-card-body { padding: 18px 22px; }
section.panel { padding: 24px 28px; }
section.panel h2 { margin: 0 0 6px; font-size: 28px; display: flex; align-items: center; gap: 10px; }
section.panel .blurb,
.section-card-body .blurb,
.snapshot-panel .blurb,
.commentary,
.narrative-col p,
.narrative-col li,
p { color: var(--muted); }
.charts {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(520px, 1fr));
  gap: 16px;
  margin-bottom: 20px;
}
.chart-cell {
  min-height: 400px;
  height: 400px;
  border: 1px solid var(--border);
  border-radius: 0;
  background: rgba(255,252,246,0.9);
  overflow: hidden;
  transition: transform 0.18s ease, border-color 0.18s ease, background-color 0.18s ease;
}
.chart-cell .plotly-graph-div { height: 100% !important; }
.chart-shell {
  position: relative;
  min-height: 440px;
  height: auto;
}
.chart-shell .chart-cell,
.chart-shell > div:first-child {
  height: 400px;
}
.chart-footnote {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  padding: 8px 10px 10px;
  border-top: 1px solid rgba(23,19,16,0.08);
  color: var(--muted);
  font-size: 11px;
  line-height: 1.45;
  background: rgba(237,223,204,0.18);
}
.quality-chip {
  display: inline-flex;
  align-items: center;
  flex: 0 0 auto;
  padding: 1px 7px;
  border: 1px solid var(--border);
  border-radius: 999px;
  font-size: 9px;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}
.quality-chip.verified { color: var(--success); border-color: rgba(63,111,80,0.35); background: rgba(63,111,80,0.08); }
.quality-chip.watch { color: var(--accent); border-color: rgba(138,89,61,0.38); background: rgba(138,89,61,0.08); }
.quality-chip.low_confidence { color: var(--danger); border-color: rgba(157,61,46,0.35); background: rgba(157,61,46,0.08); }
.chart-quality-corner {
  position: absolute;
  z-index: 4;
  top: 8px;
  right: 10px;
  background: rgba(255,252,246,0.92);
  box-shadow: 0 4px 16px rgba(23,19,16,0.08);
  backdrop-filter: blur(8px);
}
.indicator-ledger {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(210px, 1fr));
  gap: 8px;
  margin: 14px 0 16px;
}
.indicator-ledger-item {
  display: flex;
  justify-content: space-between;
  gap: 10px;
  align-items: center;
  padding: 8px 10px;
  border: 1px solid rgba(23,19,16,0.12);
  background: rgba(255,252,246,0.52);
  color: var(--fg);
  font-size: 11.5px;
}
.indicator-ledger-item span:first-child {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.coverage-panel {
  margin: 0 0 24px;
  padding: 16px 18px;
  border: 1px solid var(--border);
  background: rgba(255,252,246,0.66);
  display: flex;
  justify-content: space-between;
  gap: 16px;
  align-items: center;
  flex-wrap: wrap;
}
.coverage-panel strong {
  font-family: var(--font-display);
  font-size: 26px;
  font-weight: 500;
}
.coverage-panel span {
  color: var(--muted);
  font-size: 12px;
}
.commentary,
.framework-ref,
.narrative-footer {
  background: var(--highlight);
  border-left: 3px solid var(--accent);
  padding: 12px 18px;
  margin-top: 18px;
  color: var(--fg);
}
.commentary strong,
.framework-ref strong { color: var(--accent); }

.quality-panel {
  position: relative;
  margin: 0 0 24px;
  padding: 22px 24px;
  background: linear-gradient(135deg, rgba(255,252,246,0.96), rgba(243,236,224,0.72));
  border: 1px solid rgba(23,19,16,0.16);
  border-left: 4px solid var(--accent);
}
.quality-panel h2 {
  margin: 0 0 8px;
  font-family: var(--font-display);
  font-size: 24px;
  font-weight: 500;
  letter-spacing: -0.02em;
}
.quality-panel p { margin: 0; max-width: 980px; line-height: 1.7; }
.quality-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 10px;
  margin-top: 16px;
}
.quality-pill {
  border: 1px solid var(--border);
  background: rgba(255,255,255,0.38);
  padding: 10px 12px;
  font-size: 12px;
  color: var(--muted);
}
.quality-pill strong {
  display: block;
  margin-bottom: 3px;
  color: var(--fg);
  font-size: 11px;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}
.quality-note {
  margin-top: 16px;
  padding: 10px 12px;
  border-top: 1px solid var(--border);
  border-bottom: 1px solid var(--border);
  background: rgba(237,223,204,0.25);
  color: var(--muted);
  font-size: 12.5px;
  line-height: 1.65;
}
.quality-note .marker {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 18px;
  height: 18px;
  margin-right: 6px;
  border: 1px solid var(--accent);
  border-radius: 999px;
  color: var(--accent);
  font-size: 10px;
  font-weight: 700;
}
.toc {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
  margin-bottom: 24px;
  padding: 0;
  background: transparent;
  border: 0;
}
.toc a {
  background: var(--card);
  border: 1px solid var(--border);
  color: var(--muted) !important;
  text-decoration: none;
  padding: 6px 14px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 500;
  transition: all 0.15s;
}
.toc a:hover {
  background: var(--fg);
  color: var(--bg) !important;
  border-color: var(--fg);
  text-decoration: none;
}
table,
.indicator-table,
.trade-card-body table {
  width: 100%;
  border-collapse: collapse;
  font-size: 12.5px;
}
th,
thead th,
.indicator-table th,
.trade-card-body th {
  text-align: left;
  padding: 8px 10px;
  background: var(--card-alt);
  border-bottom: 1px solid var(--border);
}
td,
tbody td,
.indicator-table td,
.trade-card-body td {
  padding: 8px 10px;
  border-bottom: 1px solid rgba(23,19,16,0.08);
  vertical-align: top;
}
tr:hover td,
tbody tr:hover td,
.indicator-table tr:hover td { background: rgba(255,252,246,0.72); }
.ind-id,
.indicator-table .ind-id { color: var(--accent); font-weight: 600; font-family: "SF Mono", "Fira Code", Consolas, monospace; }
.ind-peers,
.chart-count { color: var(--accent); font-weight: 600; }
.tag-new,
.src-wb { background: rgba(63,111,80,0.12); color: var(--success); }
.tag-existing,
.src-eurostat,
.src-ecb { background: rgba(54,75,97,0.12); color: #364b61; }
.tag-gold,
.src-national,
.src-bis { background: var(--highlight); color: var(--accent); }
.src-market { background: rgba(157,61,46,0.12); color: var(--danger); }
.src-other { background: var(--card-alt); color: var(--muted); }
.context-grid,
.trade-grid,
.cb-grid,
.snapshot-prose {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(340px, 1fr));
  gap: 14px;
  margin-top: 18px;
}
.narrative { border: 1px solid var(--border); margin-top: 20px; overflow: hidden; }
.narrative-body { display: grid; grid-template-columns: 1fr 1fr; gap: 24px; padding: 20px 24px; background: var(--card-alt); }
.narrative-col h4 { color: var(--accent); border-bottom: 1px solid var(--border); padding-bottom: 6px; }
footer {
  margin-top: 36px;
  padding: 32px 0 16px;
  border-top: 1px solid var(--border);
  text-align: center;
  color: var(--muted);
  font-size: 11px;
}
footer a { color: var(--accent) !important; }
@media (max-width: 900px) {
  .topbar { align-items: flex-start; flex-direction: column; }
  .narrative-body,
  .charts,
  .context-grid,
  .trade-grid,
  .cb-grid,
  .snapshot-prose { grid-template-columns: 1fr; }
}
@media (max-width: 620px) {
  .container { padding: 24px 18px 42px; }
  header { padding-top: 34px; }
  .section-card-body,
  .context-card-body,
  .trade-card-body,
  .cb-card-body { overflow-x: auto; }
  .section-card-header { align-items: flex-start; flex-direction: column; }
}
"""

# ── Section config (v4 expanded — 9 sections) ──────────────────────────────────

SECTION_CHART_MAP = {
    "real_activity": [
        "chart-real_activity-real_gdp_yoy-1",
        "chart-real_activity-real_gdp_qoq-1b",
        "chart-real_activity-gdp_components-1c",
        "chart-real_activity-industrial_production_yoy-2",
        "chart-real_activity-manufacturing_pmi-2b",
        "chart-real_activity-capacity_utilization-2c",
        "chart-real_activity-retail_sales_yoy-3",
        "chart-real_activity-economic_sentiment-3b",
        "chart-real_activity-unemployment_rate-4",
        "chart-real_activity-employment_growth-4b",
        "chart-real_activity-gross_fixed_capital-5",
    ],
    "prices_wages": [
        "chart-prices_wages-cpi_yoy-5",
        "chart-prices_wages-cpi_decomposition-5b",
        "chart-prices_wages-core_cpi_yoy-6",
        "chart-prices_wages-ppi_yoy-7",
        "chart-prices_wages-import_prices_yoy-7b",
        "chart-prices_wages-avg_wage_yoy-8",
        "chart-prices_wages-real_wage_yoy-8b",
        "chart-prices_wages-unit_labour_cost-8c",
    ],
    "external": [
        "chart-external-current_account_pct_gdp-9",
        "chart-external-trade_balance-10",
        "chart-external-services_balance-10b",
        "chart-external-fx_reserves-11",
        "chart-external-ara_metric-11b",
        "chart-external-short_term_ext_debt-11c",
        "chart-external-reer-12",
        "chart-external-fx_vs_eur-12b",
        "chart-external-iip_position-13",
    ],
    "fiscal_sovereign": [
        "chart-fiscal_sovereign-fiscal_balance_pct_gdp-13",
        "chart-fiscal_sovereign-structural_balance-13b",
        "chart-fiscal_sovereign-primary_balance-13c",
        "chart-fiscal_sovereign-gov_debt_pct_gdp-14",
        "chart-fiscal_sovereign-debt_fx_share-14b",
        "chart-fiscal_sovereign-interest_bill_pct_gdp-14c",
        "chart-fiscal_sovereign-sov_yield_10y-15",
        "chart-fiscal_sovereign-sov_yield_2y-15b",
        "chart-fiscal_sovereign-yield_curve_slope-15c",
        "chart-fiscal_sovereign-cds_5y-15d",
    ],
    "monetary_financial": [
        "chart-monetary_financial-policy_rate-16",
        "chart-monetary_financial-real_policy_rate-16b",
        "chart-monetary_financial-m3_yoy-17",
        "chart-monetary_financial-private_credit_yoy-18",
        "chart-monetary_financial-credit_to_gdp_gap-18b",
        "chart-monetary_financial-lending_rates-18c",
        "chart-monetary_financial-fx_vs_eur-19",
        "chart-monetary_financial-cb_balance_sheet-19b",
    ],
    "markets_valuation": [
        "chart-markets_valuation-equity_index-20",
        "chart-markets_valuation-equity_yoy-21",
        "chart-markets_valuation-equity_fwd_pe-21b",
        "chart-markets_valuation-equity_div_yield-21c",
        "chart-markets_valuation-sov_spread_vs_bund-22",
    ],
    "financial_stability": [
        "chart-financial_stability-bank_car-22",
        "chart-financial_stability-bank_npl_ratio-23",
        "chart-financial_stability-bank_roe-24",
        "chart-financial_stability-bank_ld_ratio-25",
        "chart-financial_stability-household_debt_pct_gdp-26",
        "chart-financial_stability-corp_debt_pct_gdp-27",
    ],
    "demographics": [
        "chart-demographics-working_age_population-28",
        "chart-demographics-old_age_dependency-29",
        "chart-demographics-median_age-30",
        "chart-demographics-net_migration-31",
    ],
    "political_economy": [
        "chart-political_economy-wgi_government_effectiveness-32",
        "chart-political_economy-wgi_rule_of_law-33",
        "chart-political_economy-wgi_control_of_corruption-34",
        "chart-political_economy-eu_funds_frozen-35",
    ],
}

SECTION_TITLES = {
    "real_activity": ("§2 Real Activity", "coincident"),
    "prices_wages": ("§3 Prices & Wages", "forward-looking"),
    "external": ("§4 External Sector", "structural"),
    "fiscal_sovereign": ("§5 Fiscal & Sovereign", "risk factor"),
    "monetary_financial": ("§6 Monetary & Financial", "policy anchor"),
    "markets_valuation": ("§7 Markets & Valuation", "price signal"),
    "financial_stability": ("§8 Financial Stability & Banking", "NEW · financial soundness"),
    "demographics": ("§9 Demographics & Labour Supply", "NEW · structural"),
    "political_economy": ("§10 Political Economy & Institutions", "NEW · governance"),
}

SECTION_TITLES_ZH = {
    "real_activity": ("§2 实际经济活动", "同步指标"),
    "prices_wages": ("§3 物价与工资", "领先指标"),
    "external": ("§4 外部部门", "结构性"),
    "fiscal_sovereign": ("§5 财政与主权信用", "风险因素"),
    "monetary_financial": ("§6 货币与金融", "政策锚"),
    "markets_valuation": ("§7 市场与估值", "价格信号"),
    "financial_stability": ("§8 金融稳定与银行业", "NEW · 金融稳健性"),
    "demographics": ("§9 人口结构与劳动力供给", "NEW · 结构性"),
    "political_economy": ("§10 政治经济与制度", "NEW · 治理"),
}

SECTION_BLURBS = {
    "real_activity": "Growth decomposition: GDP (level + components), industrial production, PMI, retail sales, consumer confidence, labour market, and investment — separating cyclical momentum from structural drags and identifying the dominant growth engine.",
    "prices_wages": "Inflation dynamics: headline and core CPI with sub-components (services, goods, energy, food), producer price pipeline, import prices, wage growth (nominal + real), and unit labour costs that determine the central bank's terminal rate.",
    "external": "Balance of payments: current account with sub-balances, trade structure, FX reserve adequacy (ARA metric), short-term external debt, REER/NEER, IIP position, and external financing gaps.",
    "fiscal_sovereign": "Sovereign creditworthiness: fiscal balance (headline + structural + primary), debt stock and structure (FX share, maturity), interest burden, yield curve (2Y/10Y/slope), CDS spreads, EU funds absorption, and rating trajectory.",
    "monetary_financial": "Policy stance: nominal and real policy rates, money aggregates, credit growth and credit-to-GDP gap, lending rates by sector, CB balance sheet, FX and carry metrics.",
    "markets_valuation": "Equity valuation: headline index level and momentum, forward P/E, P/B, dividend yield, sovereign spreads vs Bund, and relative value vs CEE peers.",
    "financial_stability": "Banking sector health (IMF FSI framework): capital adequacy, NPL ratio, ROE, loan-to-deposit ratio, household and corporate debt burdens, and real estate valuation gaps.",
    "demographics": "Structural labour supply: working-age population share, old-age dependency, median age, net migration flows, and pension expenditure trajectory — the slow-moving variables that determine potential GDP and fiscal sustainability.",
    "political_economy": "Institutional quality and governance: World Bank WGI indicators (government effectiveness, rule of law, control of corruption), EU funds conditionality status, election calendar, and political risk assessment.",
}

SECTION_BLURBS_ZH = {
    "real_activity": "增长拆解：GDP（水平+构成）、工业生产、PMI、零售销售、消费者信心、劳动力市场与投资——区分周期性动能与结构性拖累，识别主导增长引擎。",
    "prices_wages": "通胀动态：整体与核心CPI及子成分（服务、商品、能源、食品）、生产者价格传导链、进口价格、工资增长（名义+实际）及决定央行终端利率的单位劳动力成本。",
    "external": "国际收支：经常账户及子余额、贸易结构、外汇储备充足性（ARA指标）、短期外债、REER/NEER、国际投资头寸及外部融资缺口。",
    "fiscal_sovereign": "主权信用评估：财政平衡（整体+结构+初级）、债务存量与结构（外汇占比、久期）、利息负担、收益率曲线（2Y/10Y/斜率）、CDS利差、欧盟资金吸收及评级轨迹。",
    "monetary_financial": "政策立场：名义与实际政策利率、货币总量、信贷增长与信贷/GDP缺口、分部门贷款利率、央行资产负债表、汇率与套利指标。",
    "markets_valuation": "股权估值：基准指数点位与动能、远期市盈率、市净率、股息率、主权相对Bund利差及相对中东欧同侪的相对价值。",
    "financial_stability": "银行业健康度（IMF FSI框架）：资本充足率、不良贷款率、ROE、存贷比、居民与企业债务负担及房地产估值缺口。",
    "demographics": "结构性劳动力供给：劳动年龄人口占比、老年抚养比、中位年龄、净移民流动及养老金支出轨迹——决定潜在GDP与财政可持续性的慢变量。",
    "political_economy": "制度质量与治理：世界银行WGI指标（政府效能、法治、腐败控制）、欧盟资金条件性状态、选举日历及政治风险评估。",
}

SECTION_ORDER = ["real_activity", "prices_wages", "external", "fiscal_sovereign", "monetary_financial", "markets_valuation", "financial_stability", "demographics", "political_economy"]


def _canonical_chart_id(section_id: str, indicator_id: str, order: int) -> str:
    return f"chart-{section_id}-{indicator_id}-{order:02d}"


# v4 is now driven by the canonical indicator manifest. The older
# SECTION_CHART_MAP above is retained for historical context, then overridden
# here so rendering and validation share one contract.
SECTION_CHART_MAP = {
    sec_id: [
        _canonical_chart_id(sec_id, spec.indicator_id, idx + 1)
        for idx, spec in enumerate(specs)
    ]
    for sec_id, specs in SECTION_INDICATORS_48.items()
}


def _quality_label(status: str, is_proxy: bool = False) -> str:
    if is_proxy:
        return "proxy"
    return status or "watch"


def _quality_class(status: str, is_proxy: bool = False) -> str:
    if is_proxy:
        return "low_confidence"
    return status if status in {"verified", "watch", "low_confidence"} else "watch"


def _strip_outer_chart_cell(block: str) -> str:
    match = re.match(r'<div class="chart-cell">(.*)</div>\s*$', block, re.DOTALL)
    return match.group(1) if match else block


def _legacy_chart_id(section_id: str, indicator_id: str, chart_map: dict[str, str]) -> str | None:
    candidates = LEGACY_INDICATOR_KEYS.get(indicator_id, (indicator_id,))
    for key in candidates:
        needle = f"-{key}-"
        for chart_id in chart_map:
            if chart_id.startswith(f"chart-{section_id}-") and needle in chart_id:
                return chart_id
    return None


def _indicator_frame(frame, country_code: str, indicator_id: str):
    if not frame:
        return []
    rows = [
        row for row in frame
        if row.get("country") == country_code and row.get("indicator_id") == indicator_id
    ]
    return sorted(rows, key=lambda row: str(row.get("date", "")))


def _chart_from_canonical_frame(frame, country_code: str, spec, chart_id: str) -> str:
    rows = _indicator_frame(frame, country_code, spec.indicator_id)
    if not rows:
        rows = _indicator_frame(fetch_canonical_macro_frame(country_code), country_code, spec.indicator_id)
    x_vals = [str(row["date"])[:10] for row in rows]
    y_vals = [round(float(row["value"]), 3) for row in rows]
    trace = {
        "name": country_code,
        "x": x_vals,
        "y": y_vals,
        "line_color": "#8a593d" if not bool(rows[-1].get("is_proxy")) else "#9d3d2e",
        "line_width": 2.3,
        "dash": "dot" if bool(rows[-1].get("is_proxy")) else "solid",
    }
    return _make_plotly_chart(chart_id, spec.label, [trace], spec.unit)


def _chart_footnote(status: str, source: str, note: str, is_proxy: bool) -> str:
    label = _quality_label(status, is_proxy)
    cls = _quality_class(status, is_proxy)
    source = escape(source or "Source pending")
    note = escape(note or "Quality note pending.")
    return (
        f'<div class="chart-footnote">'
        f'<span class="quality-chip {cls}">{escape(label)}</span>'
        f'<span><strong>{source}</strong> · {note}</span>'
        f'</div>'
    )


def _chart_corner_badge(status: str, note: str, is_proxy: bool) -> str:
    label = _quality_label(status, is_proxy)
    cls = _quality_class(status, is_proxy)
    return (
        f'<span class="quality-chip chart-quality-corner {cls}" '
        f'title="{escape(note or label)}">{escape(label)}</span>'
    )


def _indicator_ledger_html(section_id: str) -> str:
    items = []
    for spec in SECTION_INDICATORS_48.get(section_id, ()):
        cls = _quality_class(spec.quality_status)
        items.append(
            f'<div class="indicator-ledger-item" data-indicator-id="{escape(spec.indicator_id)}">'
            f'<span>{escape(spec.label)}</span>'
            f'<span class="quality-chip {cls}">{escape(spec.quality_status)}</span>'
            f'</div>'
        )
    return f'<div class="indicator-ledger">{"".join(items)}</div>'


def _render_section_charts(section_id: str, country_code: str, chart_map: dict[str, str], canonical_frame) -> tuple[str, list[str]]:
    html_parts: list[str] = []
    rendered_ids: list[str] = []
    prefer_canonical_ids = {"policy_rate", "real_policy_rate", "equity_index", "equity_yoy", "equity_vol_30d"}
    for idx, spec in enumerate(SECTION_INDICATORS_48.get(section_id, ())):
        legacy_id = _legacy_chart_id(section_id, spec.indicator_id, chart_map)
        if spec.indicator_id in prefer_canonical_ids:
            legacy_id = None
        canonical_id = _canonical_chart_id(section_id, spec.indicator_id, idx + 1)
        rows = _indicator_frame(canonical_frame, country_code, spec.indicator_id)
        row = rows[-1] if rows else {}
        status = str(row.get("quality_status") or spec.quality_status)
        source = str(row.get("source") or spec.source)
        note = str(row.get("quality_note") or spec.quality_note)
        is_proxy = bool(row.get("is_proxy", False))

        if legacy_id:
            inner = _strip_outer_chart_cell(chart_map[legacy_id])
            rendered_ids.append(legacy_id)
            legacy_note = f"Existing generated chart reused where primary data is available. {spec.quality_note}"
            footnote = _chart_footnote(
                "verified",
                spec.source,
                legacy_note,
                False,
            )
            badge = _chart_corner_badge("verified", legacy_note, False)
            html_parts.append(
                f'<div class="chart-cell chart-shell" data-indicator-id="{escape(spec.indicator_id)}">'
                f'{badge}{inner}{footnote}</div>'
            )
            continue

        rendered_ids.append(canonical_id)
        footnote = _chart_footnote(status, source, note, is_proxy)
        badge = _chart_corner_badge(status, note, is_proxy)
        html_parts.append(
            f'<div class="chart-cell chart-shell" data-indicator-id="{escape(spec.indicator_id)}">'
            f'{badge}{_chart_from_canonical_frame(canonical_frame, country_code, spec, canonical_id)}'
            f'{footnote}</div>'
        )
    return "\n".join(html_parts), rendered_ids

DATA_QUALITY_PILLARS = [
    ("Primary", "Official / central-bank source preferred", "原始来源", "优先使用官方/央行来源"),
    ("Derived", "Computed series are marked in notes", "派生", "计算型序列会在脚注说明"),
    ("Watch", "Lagged, proxy, or vendor-sensitive data", "观察", "滞后、代理或依赖供应商的数据"),
    ("Revision", "Macro releases can revise after publication", "修订", "宏观数据发布后可能回溯修订"),
]

SECTION_QUALITY_NOTES = {
    "real_activity": ("GDP and activity indicators can be revised; survey data such as PMI/sentiment is best read as a turning-point signal rather than a level estimate.", "GDP 与活动数据可能回溯修订；PMI/景气调查更适合作为拐点信号，而非精确水平估计。"),
    "prices_wages": ("Inflation components and wage series differ by methodology. Real-wage and unit-labour-cost readings are derived and should be checked against source definitions.", "通胀分项与工资序列的方法口径不同。实际工资和单位劳动力成本为派生指标，应核对来源定义。"),
    "external": ("Trade composition, reserve adequacy, and external-debt ratios are revision-prone and often lagged; use them directionally for vulnerability mapping.", "贸易结构、储备充足性和外债比率常有滞后与修订；更适合方向性地用于脆弱性定位。"),
    "fiscal_sovereign": ("Structural balances, primary balances, CDS, and yield-curve measures mix model estimates and market feeds; check vintage and liquidity before trading use.", "结构性财政余额、初级余额、CDS 与收益率曲线混合了模型估计和市场报价；交易前需核对版本与流动性。"),
    "monetary_financial": ("Real rates and credit gaps are derived indicators. Policy-rate definitions can differ in corridor systems and during temporary liquidity operations.", "实际利率与信贷缺口为派生指标。利率走廊体系或临时流动性操作期间，政策利率定义可能不同。"),
    "markets_valuation": ("Market and valuation data may come from vendor feeds or public proxies. Treat valuation multiples as indicative unless linked to a verified estimate database.", "市场与估值数据可能来自供应商或公开代理序列；若未连接可靠预期数据库，估值倍数应视为指示性。"),
    "financial_stability": ("Banking-sector indicators are often quarterly or annual, lagged, and affected by regulatory definitions; compare IMF FSI with national-bank releases.", "银行业指标通常为季度或年度、存在滞后，并受监管定义影响；建议将 IMF FSI 与本国央行发布交叉核对。"),
    "demographics": ("Demographic series are slow-moving but can be rebased after census updates. They are structural context, not high-frequency signals.", "人口序列变化慢，但人口普查后可能重基准；它们属于结构性背景，不是高频信号。"),
    "political_economy": ("Governance and political-risk indicators are qualitative or composite measures. Use them to frame regime risk, not as precise numerical facts.", "治理与政治风险指标多为定性或综合指数；适合刻画制度风险，不宜视作精确数值事实。"),
}


def _quality_panel_html() -> str:
    pills = "".join(
        f"""<div class=\"quality-pill\"><strong><span data-lang=\"en\">{en_title}</span><span data-lang=\"zh\">{zh_title}</span></strong><span data-lang=\"en\">{en_body}</span><span data-lang=\"zh\">{zh_body}</span></div>"""
        for en_title, en_body, zh_title, zh_body in DATA_QUALITY_PILLARS
    )
    return f"""
<section class=\"quality-panel\" id=\"data-quality\">
  <h2><span data-lang=\"en\">Data Quality Notes</span><span data-lang=\"zh\">数据质量说明</span></h2>
  <p><span data-lang=\"en\">This dashboard follows a source hierarchy: official and central-bank data first, then multilateral datasets, then market/vendor feeds or explicit proxies. Series that are derived, lagged, vendor-sensitive, or definition-dependent are marked with quiet footnotes rather than hidden.</span><span data-lang=\"zh\">本 dashboard 采用来源优先级：官方与央行数据优先，其次为多边机构数据，再到市场/供应商数据或明确代理序列。派生、滞后、依赖供应商或口径敏感的数据会以克制脚注标出，而不是被隐藏。</span></p>
  <div class=\"quality-grid\">{pills}</div>
</section>
"""


def _coverage_panel_html(coverage: dict) -> str:
    count = coverage.get("indicator_count", 0)
    expected = coverage.get("expected", 48)
    proxy_count = coverage.get("proxy_count", 0)
    source_chart_count = coverage.get("source_chart_count", 0)
    adapter_count = coverage.get("adapter_real_count", 0)
    generated_at = coverage.get("generated_at", "")
    missing = coverage.get("missing") or []
    missing_note = ", ".join(missing) if missing else "none"
    return f"""
<section class=\"coverage-panel\" id=\"coverage\">
  <div>
    <strong>{count}/{expected}</strong>
    <span data-lang=\"en\"> canonical indicators rendered</span>
    <span data-lang=\"zh\"> 个标准指标已渲染</span>
  </div>
  <div>
    <span data-lang=\"en\">Source charts reused: {source_chart_count}. Adapter-filled real series: {adapter_count}. Proxy / watch-list fills: {proxy_count}. Missing: {escape(missing_note)}. Generated {escape(generated_at)}.</span>
    <span data-lang=\"zh\">已复用真实来源图表: {source_chart_count}。Adapter 接入真实序列: {adapter_count}。代理/观察序列: {proxy_count}。缺失: {escape(missing_note)}。生成日期 {escape(generated_at)}。</span>
  </div>
</section>
"""


def _section_quality_html(sec_id: str) -> str:
    note = SECTION_QUALITY_NOTES.get(sec_id)
    if not note:
        return ""
    en, zh = note
    return f"""
  <div class=\"quality-note\"><span class=\"marker\">†</span><span data-lang=\"en\">{en}</span><span data-lang=\"zh\">{zh}</span></div>
"""

# ── Country-specific data ────────────────────────────────────────────────────

COUNTRY_DATA = {}


# ═══ HUNGARY ═══
COUNTRY_DATA["HU"] = {
    "code": "HU",
    "name": "Hungary",
    "iso": "HUF",
    "cb": "MNB",
    "gen_date": "2026-04-26",
    "peers": "PL, CZ, RO",
    "rating": "BBB− / Baa3 / BBB",
    "fxregime": "Free Float",
    "inftarget": "3.0% ±1pp CPI",
    "equity_index": "BUX",
    "subtitle": "Comprehensive country primer with macro narratives and forward-looking positioning views",
    "kpi_html": """<!-- KPI Ribbon -->
<div class="kpi-ribbon">
  <div class="kpi-card">
    <div class="kpi-label">Real GDP (YoY)</div>
    <div class="kpi-value">+0.5%</div>
    <div class="kpi-sub"><span class="kpi-delta-down">Decelerating</span> · Q4 2025</div>
  </div>
  <div class="kpi-card warn">
    <div class="kpi-label">Headline CPI (YoY)</div>
    <div class="kpi-value">3.3%</div>
    <div class="kpi-sub">Above 3.0% target midpoint · Dec 2025</div>
  </div>
  <div class="kpi-card danger">
    <div class="kpi-label">Fiscal Balance</div>
    <div class="kpi-value">−4.7%</div>
    <div class="kpi-sub"><span class="kpi-delta-down">of GDP</span> · 2025</div>
  </div>
  <div class="kpi-card">
    <div class="kpi-label">Current Account</div>
    <div class="kpi-value">+1.3%</div>
    <div class="kpi-sub"><span class="kpi-delta-up">Surplus</span> · of GDP 2025</div>
  </div>
  <div class="kpi-card warn">
    <div class="kpi-label">Policy Rate</div>
    <div class="kpi-value">6.25%</div>
    <div class="kpi-sub">Real rate ~300bp · MNB on hold</div>
  </div>
  <div class="kpi-card">
    <div class="kpi-label">10Y HGB Yield</div>
    <div class="kpi-value">7.10%</div>
    <div class="kpi-sub">~250bp over CEE peers · Apr 2026</div>
  </div>
</div>""",
    "snapshot_prose": """    <div class="snapshot-subsection">
      <h3>Economy</h3>
      <p>Hungary is a <strong>$215 bn economy</strong> (2024 nominal GDP) with a population of <strong>9.6 million</strong> and GDP per capita of <strong>$22,400</strong>. The industrial base is concentrated in <strong>automotive &amp; EV batteries, electronics &amp; ICT, pharmaceuticals, food processing, and business services</strong>. Top trading partners are <strong>Germany, Austria, China, Italy, and Romania</strong> — reflecting deep integration into German-speaking supply chains alongside growing Asian linkages.</p>
    </div>

    <div class="snapshot-subsection">
      <h3>Institutional Framework</h3>
      <p>The <strong>Magyar Nemzeti Bank (MNB)</strong> operates a <strong>free float</strong> FX regime with a formal inflation target of <strong>3.0% &plusmn;1pp</strong>. Hungary is an EU and NATO member (since 2004) but <strong>not a euro-area member</strong> — the HUF floats independently and monetary policy is set domestically. The sovereign carries a <strong>BBB&minus; (S&amp;P) / Baa3 (Moody&rsquo;s) / BBB (Fitch)</strong> rating — one notch above high yield, with a negative outlook risk if fiscal consolidation stalls.</p>
    </div>

    <div class="snapshot-subsection">
      <h3>Market Access</h3>
      <p>The benchmark <strong>BUX equity index</strong> (OTP Bank ~25% weight, ~&euro;14bn market cap) trades at a forward P/E of ~7.2x — a <strong>30–40% discount</strong> to CEE peers (WIG20 ~10.5x, PX ~12.0x) reflecting the political risk premium. The <strong>10-year HGB yields ~7.1%</strong>, offering the highest EUR-denominated carry in the EU but with a ~250bp spread over CEE peers that signals the market&rsquo;s fiscal credibility concern. The <strong>EURHUF at ~365</strong> (April 2026) is roughly in line with REER-based fair value estimates of 360–370.</p>
    </div>""",
    "narratives": {
        "real_activity": """<div class="narrative">
  <div class="narrative-header">
    <span class="narrative-label">Macro Narrative</span>
    <span class="narrative-date">Q1 2026 assessment</span>
  </div>
  <div class="narrative-body">
    <div class="narrative-col">
      <h4>What's Happened</h4>
      <p>Hungary's economy is <strong>stuck in a low-growth equilibrium</strong>. Real GDP printed just +0.5% YoY
      in Q4 2025, a sharp deceleration from the 1.5%+ pace of early 2024. The culprit is not domestic demand —
      real wages are growing at 6%+ as inflation normalises — but <strong>external demand</strong>. Germany, which
      absorbs ~27% of Hungarian exports, has been flatlining for six quarters. Industrial production at −1.4% YoY
      confirms the manufacturing recession, concentrated in the automotive supply chain (batteries, ICE powertrains).
      The unemployment rate has drifted up to 4.8% from a trough of 3.8%, though this partly reflects rising
      participation, not outright job destruction.</p>
      <p>Retail sales tell a more constructive story — volumes are positive, driven by real wage gains. The economy
      is <strong>bifurcated</strong>: an export-manufacturing sector in recession alongside a domestic services sector
      still growing at trend.</p>
    </div>
    <div class="narrative-col">
      <h4>What to Watch</h4>
      <ul>
        <li><strong>EU funds release</strong> — the Tisza government's ability to unlock the €20bn+ in suspended
        RRF and cohesion funds is the single largest catalyst. Expect a political agreement in H2 2026, but
        disbursement won't hit the real economy until 2027.</li>
        <li><strong>German IP cycle</strong> — watch IFO expectations and German PMI new orders. Hungary's
        manufacturing PMI has been sub-50 for 18 of the last 21 months; a German recovery is the necessary
        condition for a turn.</li>
        <li><strong>Fiscal impulse</strong> — the 2026 budget implies a widening deficit ahead of the election
        cycle. The risk is a pro-cyclical fiscal expansion just as the output gap closes, forcing MNB to keep
        rates higher for longer.</li>
      </ul>
    </div>
  </div>
  <div class="narrative-footer">
    <strong>Market Implication:</strong> The growth mix favours domestic-facing equities (banks, telcos) over
    exporters (auto suppliers, manufacturers). In rates, the weak growth print argues for eventual MNB cuts,
    but sticky services CPI and fiscal risk keep the front-end elevated. The HUF is caught between CA surplus
    support and EU-funds uncertainty — range-bound with a dovish tilt if funds materialise.
  </div>
</div>""",
        "prices_wages": """<div class="narrative">
  <div class="narrative-header">
    <span class="narrative-label">Macro Narrative</span>
    <span class="narrative-date">April 2026</span>
  </div>
  <div class="narrative-body">
    <div class="narrative-col">
      <h4>What's Happened</h4>
      <p>Hungary's disinflation has been <strong>the CEE region's standout success</strong> — headline CPI collapsed
      from 25.7% in Q1 2023 to 3.3% by end-2025, now just 0.3pp above the MNB's 3.0% target midpoint and well
      within the ±1pp tolerance band. The drivers were mechanical: energy base effects, administered price
      normalisation, and a 450bp demand compression from the 2022−23 rate shock.</p>
      <p>But the composition matters. <strong>Core CPI at 1.4%</strong> signals genuine underlying disinflation —
      goods prices are flat or falling, and even services inflation is moderating. PPI has been in deflation for
      12+ months, pointing to a further CPI grind lower over H1 2026. The uncomfortable number is
      <strong>wage growth at 9.3% YoY</strong>. While real wages are only recovering ground lost in 2022−23,
      the pace sits ~4pp above the sum of productivity growth (trend ~1.5%) and the inflation target (3.0%).
      This is the textbook definition of second-round risk that keeps MNB hawks awake.</p>
    </div>
    <div class="narrative-col">
      <h4>What to Watch</h4>
      <ul>
        <li><strong>Wage-CPI wedge</strong> — the 9.3% YoY wage print vs 3.3% CPI means real wages are rising
        ~6%. If this persists through the 2026 wage round (January−March settlements), services inflation will
        re-accelerate by H2. This is the MNB's stated red line.</li>
        <li><strong>Administered price adjustments</strong> — the Tisza government has signalled utility price
        reforms. If electricity/gas caps are lifted mid-2026, expect a one-off 1.5−2.0pp bump to headline.</li>
        <li><strong>Forint passthrough</strong> — EURHUF at 365 is 8% weaker than the 2024 average of ~395.
        A further 5% depreciation would add ~0.6pp to CPI within two quarters via the import channel.</li>
      </ul>
    </div>
  </div>
  <div class="narrative-footer">
    <strong>Market Implication:</strong> The disinflation trend buys MNB room to cut, but wage stickiness
    caps the cutting cycle at ~5.00−5.25% (from 6.25% currently). The front end of the HGB curve is pricing
    ~75bp of cuts over 12 months — roughly fair. The tail risk is that wage data forces MNB to hold at 6.25%
    through year-end, which would trigger a front-end rates rally as cuts get priced out. Receive 2y HGB
    vs pay 2y Bund expresses this view cleanly.
  </div>
</div>""",
        "external": """<div class="narrative">
  <div class="narrative-header">
    <span class="narrative-label">Macro Narrative</span>
    <span class="narrative-date">April 2026</span>
  </div>
  <div class="narrative-body">
    <div class="narrative-col">
      <h4>What's Happened</h4>
      <p>Hungary's external position is <strong>structurally improving but underappreciated</strong>. The current
      account swung from a −8.1% GDP deficit at the energy-price peak (2022) to a +1.3% surplus in 2025 — a
      ~9pp adjustment in three years. The drivers: energy import bill normalisation (gas prices down ~70% from
      the panic), auto exports ramping (new BMW/EV battery capacity), and domestic demand compression during
      the inflation shock.</p>
      <p>The REER has been depreciating gently (latest ~114, down from ~120 in 2023), restoring competitiveness
      lost during the 2021−22 inflation overshoot. But the EURHUF has been volatile — from ~380 in mid-2024
      to ~412 during the Q4 risk-off, then back to ~365 as EU fund optimism built. FX reserves at ~€46bn cover
      4.5 months of imports, adequate but not generous by CEE standards (Czechia holds ~€140bn for a similar
      import base).</p>
    </div>
    <div class="narrative-col">
      <h4>What to Watch</h4>
      <ul>
        <li><strong>EU transfers</strong> — the 2021−27 RRF + Cohesion envelope for Hungary is ~€36bn, of which
        only ~€5bn has arrived. Each €5bn tranche released adds ~0.8% of GDP to the financial account and tends
        to strengthen HUF by 2−3%.</li>
        <li><strong>Energy terms of trade</strong> — Hungary's gas storage is at 65% (vs 80% EU average). A cold
        Q4 2026 winter or Russia-Ukraine transit disruption would widen the import bill. The LNG terminal in
        Krk (Croatia) provides partial diversification but at a premium.</li>
        <li><strong>Tourism recovery</strong> — 2025 tourism receipts hit a record, contributing ~2% of GDP.
        Budapest remains underpriced vs Prague/Vienna on a quality-adjusted basis; further growth is likely.</li>
      </ul>
    </div>
  </div>
  <div class="narrative-footer">
    <strong>Market Implication:</strong> The CA surplus provides a structural HUF bid that was absent in
    2021−23. EURHUF fair value on a FEER/REER basis is probably 360−370 — not far from spot. The tail event:
    a comprehensive EU funds deal unlocks a move to 340−350. The risk event: no deal + energy shock pushes
    EURHUF back to 400+. Position for HUF strength via 6m EURHUF put spreads (360/345) funded by selling
    410 calls — asymmetric payoff to the EU funds catalyst.
  </div>
</div>""",
        "fiscal_sovereign": """<div class="narrative">
  <div class="narrative-header">
    <span class="narrative-label">Macro Narrative</span>
    <span class="narrative-date">April 2026</span>
  </div>
  <div class="narrative-body">
    <div class="narrative-col">
      <h4>What's Happened</h4>
      <p>Hungary's fiscal position is <strong>the primary macro vulnerability</strong>. The 2025 deficit printed
      at −4.7% of GDP, well above the 3.9% target and above the 3% Maastricht reference. This marks the 5th
      consecutive year above 4%. The overshoot was driven by: pre-election spending (family benefits, pension
      13th-month payments), energy subsidies, and rising interest costs as the stock of HGB debt reprices.</p>
      <p>Gross debt at 74.6% of GDP is trending higher and sits ~20pp above the CEE peer average (CZ ~43%, RO
      ~49%). The interest bill is now ~4.5% of GDP — the highest in the EU — with an average maturity of only
      ~4.5 years, meaning fiscal accounts are highly sensitive to the MNB rate path. The 10y HGB yield at 7.1%
      includes a ~250bp spread over the CEE average, reflecting the market's fiscal credibility discount.</p>
    </div>
    <div class="narrative-col">
      <h4>What to Watch</h4>
      <ul>
        <li><strong>Tisza fiscal plan</strong> — this is the known unknown. The new government inherits a
        structural deficit and will need to choose between consolidation (IMF/WB advice) and expansion
        (political temptation post-election). The 2026 budget is due by June; the deficit target will be
        the first test of market credibility.</li>
        <li><strong>Rating trajectory</strong> — all three agencies have Hungary at BBB-/Baa3, one notch
        above junk. Moody's next review is September 2026. A negative outlook from any agency would trigger
        forced selling from IG-only mandates (~$3−5bn of HGB outflows).</li>
        <li><strong>Debt composition</strong> — ~25% of HGB stock is FX-denominated, mostly EUR. HUF
        depreciation directly increases the debt/GDP ratio via the revaluation channel. This is the
        self-reinforcing mechanism that makes HUF a crisis currency in risk-off episodes.</li>
      </ul>
    </div>
  </div>
  <div class="narrative-footer">
    <strong>Market Implication:</strong> The 250bp HGB spread over CEE peers compensates for genuine fiscal
    risk, but at 7.1% the 10y offers the highest carry in the EU. The trade: long 10y HGB vs pay 10y Bund
    (350bp spread) works if EU funds unlock and Tisza delivers a credible consolidation plan. But size the
    position for a potential Moody's downgrade — the tail is a move to 8.5−9.0% in a risk-off. Stop on a
    spread widening through 400bp.
  </div>
</div>""",
        "monetary_financial": """<div class="narrative">
  <div class="narrative-header">
    <span class="narrative-label">Macro Narrative</span>
    <span class="narrative-date">April 2026</span>
  </div>
  <div class="narrative-body">
    <div class="narrative-col">
      <h4>What's Happened</h4>
      <p>The MNB delivered one of the most aggressive tightening cycles in EM history (6.0% → 18.0% in 2022),
      followed by a cautious easing cycle that brought the base rate to <strong>6.25% by early 2026</strong>.
      The real policy rate — deflated by headline CPI — is ~300bp, among the highest in the EM universe. By
      any Taylor-rule estimate, policy is restrictive.</p>
      <p>The transmission mechanism is working: private credit growth is anaemic at +1.2% YoY (negative in real
      terms), M3 growth is subdued, and the housing market has cooled. But the MNB has paused the cutting cycle
      since January 2026, explicitly citing wage data and HUF stability as the binding constraints. The minutes
      show a 5−4 split on the last hold decision, with the minority favouring a 25bp cut. The EURHUF at ~365
      is ~8% firmer than the 2024 average, giving the MNB room to cut without triggering HUF weakness — but
      they are being deliberately cautious to preserve credibility after losing it in 2021−22.</p>
    </div>
    <div class="narrative-col">
      <h4>What to Watch</h4>
      <ul>
        <li><strong>MNB May meeting (22 May)</strong> — the market prices a ~60% probability of a 25bp cut.
        The decision hinges on the March wage print (due 21 May). A wage print below 8.5% likely triggers a
        cut; above 9.5% means an extended hold.</li>
        <li><strong>Forward guidance evolution</strong> — MNB dropped the "patient, cautious" language in
        February. If the May statement shifts to "data-dependent easing," expect the market to price an
        additional 50bp of cuts into the H2 strip within 48 hours.</li>
        <li><strong>NBH vs NBP vs CNB</strong> — the current official policy-rate stack is MNB 6.25%, NBP 3.75%, and CNB 3.50%. Hungary now offers a large carry premium over Poland and Czechia; the risk is that MNB cuts faster if wages soften or HUF remains firm.</li>
      </ul>
    </div>
  </div>
  <div class="narrative-footer">
    <strong>Market Implication:</strong> HUF carry trade (long HUF vs EUR or CHF) earns ~300bp annualised at
    current rates — attractive in a world of converging DM rates. But the trade is politically fragile: any
    EU funds setback or rating downgrade triggers 5−8% HUF depreciation that wipes out a year of carry in
    a week. Size carry positions accordingly. We prefer expressing the view through the front end: receive
    2y HGB FRA (FRA 6x12) to capture the cutting cycle without the HUF spot risk.
  </div>
</div>""",
        "markets_valuation": """<div class="narrative">
  <div class="narrative-header">
    <span class="narrative-label">Macro Narrative</span>
    <span class="narrative-date">April 2026</span>
  </div>
  <div class="narrative-body">
    <div class="narrative-col">
      <h4>What's Happened</h4>
      <p>The BUX at 41,610 (−2.9% YoY) is <strong>underperforming CEE peers</strong> (WIG20 +5.4%, PX +3.1%)
      and broader EM equities (MSCI EM +6.2%). The underperformance reflects a concentrated set of domestic
      headwinds: political transition uncertainty, EU fund impasse, and the HUF's volatility keeping foreign
      investors at bay. OTP Bank (~25% of BUX, ~€14bn market cap) is the bellwether — it trades at a P/B of
      ~0.9x and trailing P/E of ~6.5x, both at the low end of the 5-year range.</p>
      <p>The valuation case is not subtle: BUX forward P/E of ~7.2x compares to WIG20 at ~10.5x and PX at
      ~12.0x. The discount reflects a political risk premium of ~30−40%. If EU funds unlock, historical
      mean-reversion implies 25−35% upside for the BUX over 12−18 months. But the market has been waiting
      for this catalyst since 2022.</p>
    </div>
    <div class="narrative-col">
      <h4>What to Watch</h4>
      <ul>
        <li><strong>OTP Bank Q1 earnings (16 May)</strong> — net interest margin trajectory is the key metric.
        If NIM compression slows (consensus: 3.85% vs 4.05% QoQ), it signals the rate cycle peak is
        translating to earnings stability. OTP also has substantial CIS exposure (Ukraine, Russia) that adds
        a geopolitical overlay few CEE banks carry.</li>
        <li><strong>EU funds catalyst</strong> — the binary event. An RRF tranche release adds ~1.2% of GDP
        to the investment pipeline within 3 quarters. The BUX historically rallies 5−8% in the month following
        a positive EU funds announcement.</li>
        <li><strong>Foreign ownership</strong> — foreign ownership of BUX free float has fallen from ~55%
        (2019) to ~35% (2026). When the catalyst arrives, the rebalancing flow into an under-owned,
        under-valued index would be explosive — thin liquidity amplifies moves in both directions.</li>
      </ul>
    </div>
  </div>
  <div class="narrative-footer">
    <strong>Market Implication:</strong> The BUX is a high-convexity bet on Hungary's political economy
    normalising. We see three ways to express it: (1) long OTP Bank equity vs short WIG20 banks — captures
    the relative valuation gap while hedging CEE regional risk; (2) BUX December 2026 calls, strike 45,000 —
    cheap vol with a defined catalyst window; (3) for the cautious — long 10y HGB (carry) and wait for equity
    entry confirmation on the first EU tranche release. Position sizing: this is a 2−3% of NAV trade, not a
    10% conviction bet. The binary EU funds risk means sizing for the scenario where nothing happens for
    another 12 months.
  </div>
</div>""",
    },
    
        "financial_stability": """<div class="narrative">
  <div class="narrative-header"><span class="narrative-label">Macro Narrative</span><span class="narrative-date">April 2026</span></div>
  <div class="narrative-body">
    <div class="narrative-col">
      <h4>What's Happened</h4>
      <p>Hungary's banking sector is <strong>well-capitalised but profitability is peaking</strong>. The aggregate CAR stands at ~18.5%, well above the 8% Pillar 1 minimum. NPL ratios have declined to ~3.2% from a post-COVID peak of ~4.5%, driven by loan book growth and write-offs. The <strong>loan-to-deposit ratio at ~72%</strong> means the sector is self-funded. OTP Bank (~25% of system assets) dominates and sets sector-wide pricing.</p>
      <p>The key vulnerability is <strong>NIM compression</strong> as the MNB cutting cycle progresses. Aggregate NIM has fallen from ~3.2% to ~2.8% and further compression to ~2.5% is likely. <strong>Household debt at ~20% of GDP</strong> is among the lowest in the EU — a buffer, not a risk. Corporate debt at ~45% of GDP is moderate.</p>
    </div>
    <div class="narrative-col">
      <h4>What to Watch</h4>
      <ul>
        <li><strong>FX loan legacy</strong> — the 2015 FX mortgage conversion eliminated most household FX exposure, but ~25% of corporate loans remain EUR-denominated. HUF depreciation increases corporate credit risk at the margin.</li>
        <li><strong>OTP CIS exposure</strong> — OTP's Ukrainian and Russian subsidiaries (~8% of group assets) carry a geopolitical tail risk not reflected in headline NPL ratios.</li>
        <li><strong>MNB macroprudential stance</strong> — the MNB has maintained the CCyB at 0%. Any increase would signal concern about credit cycle overheating.</li>
      </ul>
    </div>
  </div>
  <div class="narrative-footer"><strong>Market Implication:</strong> Hungarian banks are cheap (OTP at P/B ~0.9x) but face NIM headwinds. The low household debt stock means asset quality is unlikely to deteriorate sharply even in a recession. Long OTP vs short WIG20 banks captures the relative valuation gap.</div>
</div>""",
        "demographics": """<div class="narrative">
  <div class="narrative-header"><span class="narrative-label">Structural Narrative</span><span class="narrative-date">2026 assessment</span></div>
  <div class="narrative-body">
    <div class="narrative-col">
      <h4>What's Happened</h4>
      <p>Hungary faces <strong>one of the most acute demographic headwinds in the EU</strong>. The population has declined from 10.4mn (1990) to ~9.6mn (2025), with the working-age population (15-64) shrinking at ~0.5% annually. The <strong>old-age dependency ratio has risen from 26% to ~32%</strong> over the past decade and is projected toward 40%+ by 2040. The median age of 44 is above the EU average. This directly reduces potential GDP growth by ~0.3-0.5pp annually.</p>
      <p>The government's family policy (generous tax breaks for large families, housing subsidies) has had modest impact — TFR rose from 1.2 (2010) to 1.5 (2024), but remains below 2.1 replacement. <strong>Net migration is slightly negative</strong>, with skilled workers emigrating to Austria/Germany. Labour force participation at ~67% has room to rise, particularly among women and older workers.</p>
    </div>
    <div class="narrative-col">
      <h4>What to Watch</h4>
      <ul>
        <li><strong>Pension sustainability</strong> — pension spending at ~11% of GDP is manageable now but projected to rise to 14%+ by 2040. The Tisza government's pension reform agenda is a key long-term fiscal marker.</li>
        <li><strong>Skills mismatch</strong> — manufacturing labour demand is declining (auto restructuring) while services demand is rising. The skills mismatch is acute and keeps structural unemployment elevated.</li>
        <li><strong>EU mobility</strong> — Hungary's EU accession triggered emigration of ~600,000 workers. Further liberalisation of EU labour markets would accelerate brain drain.</li>
      </ul>
    </div>
  </div>
  <div class="narrative-footer"><strong>Market Implication:</strong> Demographics are a structural drag on Hungarian potential GDP (~2.0-2.5% trend vs 3%+ for Poland). This supports the case for lower terminal rates and makes Hungary a structurally lower-growth economy. Long-dated HGBs benefit from the demographic disinflation thesis.</div>
</div>""",
        "political_economy": """<div class="narrative">
  <div class="narrative-header"><span class="narrative-label">Structural Narrative</span><span class="narrative-date">2026 assessment</span></div>
  <div class="narrative-body">
    <div class="narrative-col">
      <h4>What's Happened</h4>
      <p>The <strong>April 2026 Tisza Party supermajority</strong> ended 16 years of Fidesz rule — the most significant political economy event since EU accession. The government inherits ~€21bn in suspended EU funds (rule-of-law disputes), a -4.7% GDP deficit, and a business environment that has deteriorated vs CEE peers. World Bank Governance Indicators show Hungary declining from ~75th to ~62nd percentile on control of corruption (2010-2024), and from ~72nd to ~68th on rule of law. The BUX's 30-40% discount is essentially a governance risk premium.</p>
    </div>
    <div class="narrative-col">
      <h4>What to Watch</h4>
      <ul>
        <li><strong>EU funds agreement</strong> — the single largest catalyst for Hungarian assets. A positive agreement unlocks €21bn+ and would trigger a sovereign rating upgrade cycle.</li>
        <li><strong>Fiscal credibility test</strong> — the 2026 budget (June) is the first test. A credible consolidation plan (deficit below 3.5% GDP) would compress HGB spreads by 50-75bp.</li>
        <li><strong>2029 election cycle</strong> — the supermajority provides a 4-year policy window. Risk: consolidation is delayed to 2027-28, compressing the adjustment period.</li>
      </ul>
    </div>
  </div>
  <div class="narrative-footer"><strong>Market Implication:</strong> The best political economy setup for Hungarian assets since 2018. EU funds optimism + fresh political capital + deeply undervalued assets (BUX 7.2x P/E) = high-convexity opportunity. Key risk: execution failure on EU conditionality.</div>
</div>""",
	    "subtitle_zh": "综合国别概览，包含宏观叙事与前瞻性投资定位观点",
    "kpi_html_zh": """<!-- KPI Ribbon CN -->
<div class="kpi-ribbon">
  <div class="kpi-card">
    <div class="kpi-label">实际GDP（同比）</div>
    <div class="kpi-value">+0.5%</div>
    <div class="kpi-sub"><span class="kpi-delta-down">减速中</span> · 2025年Q4</div>
  </div>
  <div class="kpi-card warn">
    <div class="kpi-label">整体CPI（同比）</div>
    <div class="kpi-value">3.3%</div>
    <div class="kpi-sub">高于3.0%目标中值 · 2025年12月</div>
  </div>
  <div class="kpi-card danger">
    <div class="kpi-label">财政赤字</div>
    <div class="kpi-value">−4.7%</div>
    <div class="kpi-sub"><span class="kpi-delta-down">占GDP</span> · 2025年</div>
  </div>
  <div class="kpi-card">
    <div class="kpi-label">经常账户</div>
    <div class="kpi-value">+1.3%</div>
    <div class="kpi-sub"><span class="kpi-delta-up">盈余</span> · 占GDP 2025年</div>
  </div>
  <div class="kpi-card warn">
    <div class="kpi-label">政策利率</div>
    <div class="kpi-value">6.25%</div>
    <div class="kpi-sub">实际利率~300bp · MNB暂缓降息</div>
  </div>
  <div class="kpi-card">
    <div class="kpi-label">10年期国债收益率</div>
    <div class="kpi-value">7.10%</div>
    <div class="kpi-sub">~250bp高于中东欧同侪 · 2026年4月</div>
  </div>
</div>""",
    "snapshot_prose_zh": """    <div class="snapshot-subsection">
      <h3>经济概况</h3>
      <p>匈牙利是一个<strong>$2150亿经济体</strong>（2024年名义GDP），人口<strong>960万</strong>，人均GDP<strong>$22,400</strong>。产业基础集中于<strong>汽车及电动车电池、电子与信息通信技术、制药、食品加工及商业服务</strong>。主要贸易伙伴为<strong>德国、奥地利、中国、意大利和罗马尼亚</strong>——反映出深度嵌入德语区供应链以及日益增长的亚洲联系。</p>
    </div>

    <div class="snapshot-subsection">
      <h3>制度框架</h3>
      <p><strong>匈牙利国家银行（MNB）</strong>实行<strong>自由浮动</strong>汇率制度，正式通胀目标为<strong>3.0% ±1个百分点</strong>。匈牙利自2004年起为欧盟和北约成员国，但<strong>非欧元区成员</strong>——福林独立浮动，货币政策由国内自主制定。主权评级为<strong>BBB−（标普）/ Baa3（穆迪）/ BBB（惠誉）</strong>——仅高于垃圾级一个档次，若财政整顿停滞则面临负面展望风险。</p>
    </div>

    <div class="snapshot-subsection">
      <h3>市场准入</h3>
      <p>基准<strong>BUX股票指数</strong>（OTP银行权重约25%，市值约€140亿）远期市盈率约7.2倍——<strong>较中东欧同侪折价30–40%</strong>（WIG20约10.5倍，PX约12.0倍），反映了政治风险溢价。<strong>10年期国债收益率约7.1%</strong>，提供欧盟内最高的欧元计价利差收益，但~250bp的相对中东欧同侪利差反映了市场对财政可信度的担忧。<strong>EURHUF约365</strong>（2026年4月）大致符合基于REER的公允价值估算360–370。</p>
    </div>""",
    "narratives_zh": {
        "real_activity": """<div class="narrative">
  <div class="narrative-header">
    <span class="narrative-label">宏观叙事</span>
    <span class="narrative-date">2026年Q1评估</span>
  </div>
  <div class="narrative-body">
    <div class="narrative-col">
      <h4>已发生的变化</h4>
      <p>匈牙利经济<strong>陷入低增长均衡</strong>。2025年Q4实际GDP同比仅+0.5%，较2024年初1.5%+的增速显著放缓。症结不在内需——随着通胀正常化，实际工资增长超过6%——而在于<strong>外部需求</strong>。德国吸纳了匈牙利约27%的出口，已连续六个季度停滞。工业生产同比-1.4%确认了制造业衰退，集中在汽车供应链（电池、内燃机动力系统）。失业率从3.8%的低谷上升至4.8%，但这部分反映了参与率上升而非纯粹的就业流失。</p>
      <p>零售销售则呈现更富建设性的图景——受实际工资增长驱动，成交量保持正值。经济呈<strong>二元分化</strong>：出口制造业处于衰退之中，而国内服务业仍以趋势增速扩张。</p>
    </div>
    <div class="narrative-col">
      <h4>需要关注</h4>
      <ul>
        <li><strong>欧盟资金释放</strong>——蒂萨政府能否解锁被冻结的€200亿+复苏基金和凝聚基金是最大催化剂。预计2026年下半年达成政治协议，但资金实际进入实体经济要到2027年。</li>
        <li><strong>德国工业周期</strong>——关注IFO预期和德国PMI新订单。匈牙利制造业PMI在过去21个月中有18个月处于50以下；德国复苏是匈牙利制造业转向的必要条件。</li>
        <li><strong>财政脉冲</strong>——2026年预算意味着大选周期前赤字扩大。风险在于产出缺口收窄之际实施顺周期财政扩张，迫使MNB在更长时间内维持更高利率。</li>
      </ul>
    </div>
  </div>
  <div class="narrative-footer">
    <strong>市场含义：</strong>增长结构有利于面向国内的股票（银行、电信）而非出口商（汽车供应商、制造商）。利率方面，疲弱的增长数据支持MNB最终降息，但服务业CPI粘性和财政风险使短端利率维持高位。福林夹在经常账户盈余支撑与欧盟资金不确定性之间——若资金落地，呈区间波动并带有鸽派倾向。
  </div>
</div>""",
        "prices_wages": """<div class="narrative">
  <div class="narrative-header">
    <span class="narrative-label">宏观叙事</span>
    <span class="narrative-date">2026年4月</span>
  </div>
  <div class="narrative-body">
    <div class="narrative-col">
      <h4>已发生的变化</h4>
      <p>匈牙利的去通胀过程是<strong>中东欧地区最显著的成功案例</strong>——整体CPI从2023年Q1的25.7%骤降至2025年底的3.3%，目前仅比MNB 3.0%目标中值高出0.3个百分点，并显著落在±1个百分点容忍区间内。驱动因素具有机械性：能源基数效应、行政定价正常化，以及2022−2023年加息冲击带来的450bp需求压缩。</p>
      <p>但构成至关重要。<strong>核心CPI为1.4%</strong>，表明真正的潜在去通胀——商品价格持平或下跌，甚至服务业通胀也在放缓。PPI已连续12个月以上处于通缩状态，预示着2026年上半年CPI将进一步走低。令人不安的数据是<strong>工资增长同比9.3%</strong>。虽然实际工资仅是在恢复2022−2023年损失的空间，但增速比生产率增长（趋势约1.5%）与通胀目标（3.0%）之和高出约4个百分点。这正是令MNB鹰派警惕的教科书式第二轮效应风险。</p>
    </div>
    <div class="narrative-col">
      <h4>需要关注</h4>
      <ul>
        <li><strong>工资-CPI剪刀差</strong>——同比9.3%的工资增速与3.3%的CPI意味着实际工资增长约6%。如果这持续贯穿2026年工资谈判季（1-3月），服务业通胀将在下半年重新加速。这是MNB明确强调的红线。</li>
        <li><strong>行政定价调整</strong>——蒂萨政府已暗示公用事业价格改革。如果2026年中取消电/气价格上限，预计整体CPI将出现1.5-2.0个百分点的一次性跳升。</li>
        <li><strong>福林传导效应</strong>——EURHUF在365的水平较2024年约395的均值升值约8%。若进一步贬值5%，将通过进口渠道在两个季度内推升CPI约0.6个百分点。</li>
      </ul>
    </div>
  </div>
  <div class="narrative-footer">
    <strong>市场含义：</strong>去通胀趋势为MNB提供降息空间，但工资粘性将降息周期限制在~5.00-5.25%（当前6.25%）。HGB曲线短端定价未来12个月约75bp降息——大致公允。尾部风险在于工资数据迫使MNB在年底前维持6.25%不变，这将引发短端利率反弹，因降息预期被重新定价。做多2年期HGB对做空2年期Bund可干净表达这一观点。
  </div>
</div>""",
        "external": """<div class="narrative">
  <div class="narrative-header">
    <span class="narrative-label">宏观叙事</span>
    <span class="narrative-date">2026年4月</span>
  </div>
  <div class="narrative-body">
    <div class="narrative-col">
      <h4>已发生的变化</h4>
      <p>匈牙利的对外部门<strong>结构性改善但被市场低估</strong>。经常账户从2022年能源价格峰值时的-8.1% GDP逆差转为2025年的+1.3%顺差——三年内调整约9个百分点。驱动因素：能源进口账单正常化（天然气价格从恐慌期下降约70%）、汽车出口增长（新增BMW/电动车电池产能），以及通胀冲击期间的国内需求压缩。</p>
      <p>REER温和贬值（最新约114，低于2023年的约120），恢复2021-2022年通胀超调期间丧失的竞争力。但EURHUF波动剧烈——从2024年中约380，到Q4避险期间约412，再到欧盟资金乐观情绪推动下回到约365。外汇储备约€460亿覆盖4.5个月进口，充足但不算中东欧标准中的充裕（捷克持有约€1400亿储备，进口基数相近）。</p>
    </div>
    <div class="narrative-col">
      <h4>需要关注</h4>
      <ul>
        <li><strong>欧盟转移支付</strong>——匈牙利2021-2027年复苏基金+凝聚基金总额约€360亿，迄今仅到位约€50亿。每释放€50亿批次将增加约GDP 0.8%的金融账户流入，通常推动福林升值2-3%。</li>
        <li><strong>能源贸易条件</strong>——匈牙利天然气库存为65%（欧盟平均80%）。2026年Q4寒冬或俄乌运输中断将扩大进口账单。克罗地亚克尔克LNG终端提供部分多元化选择，但成本溢价。</li>
        <li><strong>旅游业复苏</strong>——2025年旅游收入创纪录，贡献约GDP的2%。布达佩斯在质调基础上相对布拉格/维也纳定价偏低；进一步增长可期。</li>
      </ul>
    </div>
  </div>
  <div class="narrative-footer">
    <strong>市场含义：</strong>经常账户盈余提供了2021-2023年所缺失的结构性福林买盘。基于FEER/REER的EURHUF公允价值大概率在360-370——离现货不远。尾部事件：全面欧盟资金协议推动EURHUF至340-350。风险事件：无协议+能源冲击推动EURHUF回到400+。通过6个月EURHUF看跌价差（360/345）融资卖出410看涨期权表达福林走强观点——对欧盟资金催化剂具有非对称收益。
  </div>
</div>""",
        "fiscal_sovereign": """<div class="narrative">
  <div class="narrative-header">
    <span class="narrative-label">宏观叙事</span>
    <span class="narrative-date">2026年4月</span>
  </div>
  <div class="narrative-body">
    <div class="narrative-col">
      <h4>已发生的变化</h4>
      <p>匈牙利财政状况是<strong>最主要的宏观脆弱性</strong>。2025年赤字为GDP的-4.7%，显著高于3.9%的目标及3%的马斯特里赫特参考值。这标志着连续第五年超过4%。超支驱动因素包括：大选前支出（家庭补贴、第13个月养老金）、能源补贴，以及HGB债务存量重新定价带来的利息成本上升。</p>
      <p>总债务占GDP的74.6%呈上升趋势，比中东欧同侪平均水平高出约20个百分点（捷克约43%，罗马尼亚约49%）。利息支出目前约GDP的4.5%——欧盟最高——平均久期仅约4.5年，意味着财政状况对MNB利率路径高度敏感。10年期HGB收益率7.1%包含约250bp的中东欧同侪利差，反映了市场对财政可信度的折价。</p>
    </div>
    <div class="narrative-col">
      <h4>需要关注</h4>
      <ul>
        <li><strong>蒂萨政府财政计划</strong>——这是已知的未知。新政府继承了结构性赤字，需要在整顿（IMF/WB建议）与扩张（大选后的政治诱惑）之间做出选择。2026年预算将于6月前公布；赤字目标将是市场可信度的首个考验。</li>
        <li><strong>评级轨迹</strong>——三大评级机构均将匈牙利评为BBB-/Baa3，仅高出垃圾级一个档次。穆迪下次审查为2026年9月。任何机构的负面展望都将触发仅限投资级的被动减持（约$30-50亿HGB流出）。</li>
        <li><strong>债务构成</strong>——HGB存量约25%为外币计价，主要是欧元。福林贬值通过重估渠道直接推升债务/GDP比率。这是使福林在避险期成为危机货币的自我强化机制。</li>
      </ul>
    </div>
  </div>
  <div class="narrative-footer">
    <strong>市场含义：</strong>HGB相对中东欧同侪250bp的利差补偿了真实的财政风险，但10年期7.1%的收益率提供了欧盟内最高的利差收益。交易策略：如果欧盟资金解锁且蒂萨政府提供可信的整顿计划，做多10年期HGB对做空10年期Bund（350bp利差）。但需为穆迪潜在降级做好头寸管理——尾部风险是在避险情景下收益率升至8.5-9.0%。利差扩大至400bp以上时止损。
  </div>
</div>""",
        "monetary_financial": """<div class="narrative">
  <div class="narrative-header">
    <span class="narrative-label">宏观叙事</span>
    <span class="narrative-date">2026年4月</span>
  </div>
  <div class="narrative-body">
    <div class="narrative-col">
      <h4>已发生的变化</h4>
      <p>MNB实施了新兴市场历史上最激进的加息周期之一（2022年6.0%→18.0%），随后是谨慎的宽松周期，至<strong>2026年初将基准利率降至6.25%</strong>。按整体CPI平减的实际政策利率约为~300bp，属新兴市场最高之一。按任何泰勒规则估算，政策均属紧缩性。</p>
      <p>传导机制正在发挥作用：私人信贷增长乏力，同比+1.2%（实际值为负），M3增长低迷，住房市场已降温。但MNB自2026年1月以来暂停降息，明确将工资数据和福林稳定性作为约束条件。会议纪要显示上次维持利率决定为5-4分歧，少数派支持降息25bp。EURHUF约365较2024年均值升值约8%，赋予MNB降息而不触发福林贬值的空间——但央行刻意保持谨慎，以在2021-2022年失去信誉后重建公信力。</p>
    </div>
    <div class="narrative-col">
      <h4>需要关注</h4>
      <ul>
        <li><strong>MNB 5月会议（5月22日）</strong>——市场定价约60%的25bp降息概率。决定取决于3月工资数据（5月21日公布）。工资增速低于8.5%大概率触发降息；高于9.5%则意味着持续暂停。</li>
        <li><strong>前瞻指引演变</strong>——MNB在2月去掉了"耐心、谨慎"的措辞。如果5月声明转向"数据依赖型宽松"，预计市场将在48小时内对下半年额外定价50bp降息。</li>
        <li><strong>NBH vs NBP vs CNB</strong>——当前官方政策利率为MNB 6.25%、NBP 3.75%、CNB 3.50%。匈牙利相对波兰和捷克提供显著利差，但如果工资放缓或福林保持强势，MNB也可能更快降息。</li>
      </ul>
    </div>
  </div>
  <div class="narrative-footer">
    <strong>市场含义：</strong>福林套利交易（做多HUF对EUR或CHF）在当前利率下年化收益约300bp——在DM利率趋同的世界中具有吸引力。但该交易具有政治脆弱性：任何欧盟资金受挫或评级下调都会在一周内触发5-8%的福林贬值，抹去一年的套利收益。应相应控制套利头寸规模。我们倾向于通过短端表达观点：做多2年期HGB FRA（FRA 6x12）以捕捉降息周期，避免福林现货风险。
  </div>
</div>""",
        "markets_valuation": """<div class="narrative">
  <div class="narrative-header">
    <span class="narrative-label">宏观叙事</span>
    <span class="narrative-date">2026年4月</span>
  </div>
  <div class="narrative-body">
    <div class="narrative-col">
      <h4>已发生的变化</h4>
      <p>BUX报41,610点（同比-2.9%），<strong>跑输中东欧同侪</strong>（WIG20 +5.4%，PX +3.1%）及更广泛的新兴市场股票（MSCI EM +6.2%）。跑输反映了一组集中的国内阻力：政治过渡不确定性、欧盟资金僵局，以及福林波动性使外国投资者保持观望。OTP银行（BUX权重约25%，市值约€140亿）是风向标——市净率约0.9倍，往绩市盈率约6.5倍，均处于5年区间低端。</p>
      <p>估值逻辑并不隐晦：BUX远期市盈率约7.2倍，对比WIG20约10.5倍和PX约12.0倍。折价反映了约30-40%的政治风险溢价。如果欧盟资金解锁，历史上均值回归意味着BUX在12-18个月内上涨25-35%。但市场自2022年以来一直在等待这一催化剂。</p>
    </div>
    <div class="narrative-col">
      <h4>需要关注</h4>
      <ul>
        <li><strong>OTP银行Q1业绩（5月16日）</strong>——净息差轨迹是关键指标。如果NIM压缩放缓（一致预期：环比3.85% vs 4.05%），则表明利率周期峰值正在转化为盈利稳定性。OTP还拥有大量独联体敞口（乌克兰、俄罗斯），这增加了大多数中东欧银行不具备的地缘政治叠加因素。</li>
        <li><strong>欧盟资金催化剂</strong>——二元事件。RRF批次释放在3个季度内向投资管道增加约1.2% GDP。BUX历史上在积极欧盟资金公告后的当月上涨5-8%。</li>
        <li><strong>外资持股</strong>——BUX自由流通股的外资持股已从约55%（2019年）降至约35%（2026年）。当催化剂到来时，对一个低配、低估指数的再平衡资金流入将是爆发性的——低流动性放大两个方向的波动。</li>
      </ul>
    </div>
  </div>
  <div class="narrative-footer">
    <strong>市场含义：</strong>BUX是对匈牙利政治经济正常化的高凸性押注。我们看到三种表达方式：（1）做多OTP银行股票对做空WIG20银行股——捕捉相对估值差距，同时对冲中东欧区域风险；（2）BUX 2026年12月看涨期权，行权价45,000——低波动率且催化剂窗口明确；（3）对于谨慎者——做多10年期HGB（利差收益），等待首个欧盟批次释放后的股票入市确认信号。头寸规模：这是NAV的2-3%交易，而非10%的信念押注。欧盟资金的二元风险意味着需按未来12个月什么都没有发生的情景来设臵头寸。
  </div>
</div>""",
    
        "financial_stability": """<div class="narrative">
  <div class="narrative-header"><span class="narrative-label">宏观叙事</span><span class="narrative-date">2026年4月</span></div>
  <div class="narrative-body">
    <div class="narrative-col">
      <h4>已发生的变化</h4>
      <p>匈牙利银行业<strong>资本充足但盈利能力见顶</strong>。整体CAR约18.5%，远高于8%的第一支柱最低要求。不良贷款率已从疫情后峰值约4.5%降至约3.2%。<strong>存贷比约72%</strong>意味着该行业自给自足——这是中东欧的结构性优势。OTP银行（系统资产约25%）占据主导地位。</p>
      <p>关键脆弱性是<strong>净息差压缩</strong>——随着MNB降息周期推进，整体NIM已从约3.2%降至约2.8%。<strong>居民债务约GDP的20%</strong>为欧盟最低之一——是缓冲而非风险。企业债务约GDP的45%处于中等水平。</p>
    </div>
    <div class="narrative-col">
      <h4>需要关注</h4>
      <ul>
        <li><strong>外汇贷款遗留</strong>——2015年外汇按揭转换消除了大部分居民外汇敞口，但约25%企业贷款仍以欧元计价。福林贬值边际增加企业信用风险。</li>
        <li><strong>OTP独联体敞口</strong>——OTP乌克兰和俄罗斯子公司（约集团资产8%）承载地缘政治尾部风险。</li>
        <li><strong>MNB宏观审慎立场</strong>——MNB维持CCyB为0%。任何上调将表明对信贷周期过热的担忧。</li>
      </ul>
    </div>
  </div>
  <div class="narrative-footer"><strong>市场含义：</strong>匈牙利银行便宜（OTP市净率约0.9倍）但面临净息差逆风。低居民债务意味着即使衰退情景下资产质量也不太可能急剧恶化。做多OTP对做空WIG20银行捕捉相对估值差距。</div>
</div>""",
        "demographics": """<div class="narrative">
  <div class="narrative-header"><span class="narrative-label">结构性叙事</span><span class="narrative-date">2026年评估</span></div>
  <div class="narrative-body">
    <div class="narrative-col">
      <h4>已发生的变化</h4>
      <p>匈牙利面临<strong>欧盟最严峻的人口逆风之一</strong>。人口已从1040万（1990年）降至约960万（2025年），劳动年龄人口（15-64岁）以年均约0.5%速度萎缩。<strong>老年抚养比从26%升至约32%</strong>，预计2040年将超过40%。中位年龄44岁高于欧盟均值。这每年直接降低潜在GDP增长约0.3-0.5个百分点。</p>
      <p>政府的家庭政策（对大家庭的税收减免、住房补贴）产生温和效果——总和生育率从1.2（2010年）升至1.5（2024年），但仍远低于2.1的替代水平。<strong>净移民略有负值</strong>，技术工人移居奥地利/德国。劳动力参与率约67%有上升空间，特别是在女性和年长工人中。</p>
    </div>
    <div class="narrative-col">
      <h4>需要关注</h4>
      <ul>
        <li><strong>养老金可持续性</strong>——养老金支出约GDP的11%目前可控，但按不变政策预计2040年将升至14%+。蒂萨政府的养老金改革议程是关键长期财政标志。</li>
        <li><strong>技能错配</strong>——制造业劳动力需求下降（汽车重组）而服务业需求上升。技能错配严重，使结构性失业维持高位。</li>
        <li><strong>欧盟流动性</strong>——匈牙利加入欧盟触发了约60万工人移民。欧盟劳动力市场的进一步自由化将加速人才流失。</li>
      </ul>
    </div>
  </div>
  <div class="narrative-footer"><strong>市场含义：</strong>人口结构是匈牙利潜在GDP的结构性拖累（趋势约2.0-2.5%对比波兰3%+）。这支持更低终端利率的理由，使匈牙利成为结构性低增长经济体。长期HGB受益于人口通缩主题。</div>
</div>""",
        "political_economy": """<div class="narrative">
  <div class="narrative-header"><span class="narrative-label">结构性叙事</span><span class="narrative-date">2026年评估</span></div>
  <div class="narrative-body">
    <div class="narrative-col">
      <h4>已发生的变化</h4>
      <p><strong>2026年4月蒂萨党超级多数</strong>结束了16年Fidesz执政——自加入欧盟以来最重要的政治经济事件。政府继承约€210亿被冻结的欧盟资金（法治争议）、-4.7% GDP的赤字以及相对中东欧同侪恶化的商业环境。世界银行治理指标显示匈牙利腐败控制从约75百分位降至约62百分位（2010-2024年），法治从约72降至约68百分位。BUX的30-40%折价本质上是治理风险溢价。</p>
    </div>
    <div class="narrative-col">
      <h4>需要关注</h4>
      <ul>
        <li><strong>欧盟资金协议</strong>——匈牙利资产的最大单一催化剂。积极协议解锁€210亿+并将触发主权评级升级周期。</li>
        <li><strong>财政可信度考验</strong>——2026年预算（6月）是首次考验。可信的整顿计划（赤字低于3.5% GDP）将在数周内压缩HGB利差50-75bp。</li>
        <li><strong>2029年选举周期</strong>——超级多数提供4年政策窗口。风险：整顿推迟至2027-28年，压缩调整期。</li>
      </ul>
    </div>
  </div>
  <div class="narrative-footer"><strong>市场含义：</strong>2018年以来匈牙利资产的最佳政治经济环境。欧盟资金乐观+新政治资本+深度低估资产（BUX 7.2倍市盈率）= 高凸性机会。关键风险：欧盟条件性执行失败。</div>
</div>""",
    },
}

# ═══ POLAND ═══
COUNTRY_DATA["PL"] = {
    "name": "Poland",
    "iso": "PLN",
    "cb": "NBP",
    "gen_date": "2026-04-26",
    "peers": "HU, CZ, RO",
    "rating": "A− / A2 / A−",
    "fxregime": "Free Float",
    "inftarget": "2.5% ±1pp CPI",
    "equity_index": "WIG20",
    "subtitle": "Comprehensive country primer with macro narratives and forward-looking positioning views",
    "kpi_html": """
  <div class="kpi-ribbon">
    <div class="kpi-card">
      <div class="kpi-label">Real GDP (YoY)</div>
      <div class="kpi-value">+2.8%</div>
      <div class="kpi-sub"><span class="kpi-delta-up">CEE leader</span> · Q4 2025</div>
    </div>
    <div class="kpi-card warn">
      <div class="kpi-label">Headline CPI (YoY)</div>
      <div class="kpi-value">4.5%</div>
      <div class="kpi-sub">Above 2.5% target · Dec 2025</div>
    </div>
    <div class="kpi-card warn">
      <div class="kpi-label">Fiscal Balance</div>
      <div class="kpi-value">−5.1%</div>
      <div class="kpi-sub"><span class="kpi-delta-down">of GDP</span> · 2025</div>
    </div>
    <div class="kpi-card">
      <div class="kpi-label">Current Account</div>
      <div class="kpi-value">+0.8%</div>
      <div class="kpi-sub"><span class="kpi-delta-up">Surplus</span> · of GDP 2025</div>
    </div>
    <div class="kpi-card warn">
      <div class="kpi-label">Policy Rate</div>
      <div class="kpi-value">3.75%</div>
      <div class="kpi-sub">Reference rate · NBP on hold</div>
    </div>
    <div class="kpi-card">
      <div class="kpi-label">10Y PLN Yield</div>
      <div class="kpi-value">5.90%</div>
      <div class="kpi-sub">~130bp over Bund · Apr 2026</div>
    </div>
  </div>""",
    "snapshot_prose": """
    <div class="snapshot-subsection">
      <h3>Economy</h3>
      <p>Poland is the <strong>largest CEE economy at $845 bn</strong> (2024 nominal GDP) with a population of <strong>36.8 million</strong> and GDP per capita of <strong>$23,000</strong>. It was the only EU economy to avoid recession during the 2008 GFC and again outperformed during COVID. The industrial base spans <strong>automotive parts &amp; assembly (Europe's largest auto-parts exporter), consumer electronics, IT services, food processing, and coal/energy</strong>. Top trading partners are <strong>Germany, Czechia, France, the UK, and the Netherlands</strong>. Poland benefits from a large internal market, diversified export structure, and a structurally tight labour market (unemployment &lt;4%) that supports domestic demand.</p>
    </div>
    <div class="snapshot-subsection">
      <h3>Institutional Framework</h3>
      <p>The <strong>Narodowy Bank Polski (NBP)</strong> operates a <strong>free float</strong> FX regime with a formal inflation target of <strong>2.5% &plusmn;1pp</strong>. Poland is an EU and NATO member since 2004 but <strong>not a euro-area member</strong> — the PLN floats independently. Sovereign credit rating stands at <strong>A&minus; (S&amp;P) / A2 (Moody&rsquo;s) / A&minus; (Fitch)</strong> — the strongest in CEE, reflecting Poland's diversified economy, manageable debt (~50% GDP), and large FX reserves (~€170bn). EU RRF funds (~€60bn) have been partially unlocked under the Tusk government.</p>
    </div>
    <div class="snapshot-subsection">
      <h3>Market Access</h3>
      <p>The benchmark <strong>WIG20 index</strong> trades at a forward P/E of ~10.5x — roughly in line with EM Europe peers. The <strong>10-year PLN government bond yields ~5.9%</strong>, offering ~130bp over Bunds — a tight spread that reflects Poland's rating advantage and deep local institutional base (pension funds, insurers). The <strong>EURPLN at ~4.30</strong> (April 2026) is close to the 5-year average. Poland has the deepest and most liquid capital markets in CEE — Warsaw Stock Exchange is the region's primary listing venue with ~€200bn market cap across all listed companies.</p>
    </div>""",
    "narratives": {
        "real_activity": """
<div class="narrative">
  <div class="narrative-header">
    <span class="narrative-label">Macro Narrative</span>
    <span class="narrative-date">Q1 2026 assessment</span>
  </div>
  <div class="narrative-body">
    <div class="narrative-col">
      <h4>What's Happened</h4>
      <p>Poland is the <strong>CEE growth outperformer</strong> — real GDP expanded ~2.8% YoY in 2025, roughly double the CEE-4 average. The growth model is uniquely balanced: <strong>domestic consumption</strong> (real wage growth of 4%+ with unemployment at a structural low of 2.9%), <strong>robust investment</strong> (EU-funds fuelled infrastructure and defence spending at 4%+ of GDP), and <strong>resilient exports</strong> despite the German manufacturing recession. Industrial production is running at +2.1% YoY — modest but positive, in contrast to the contraction seen in Hungary and Czechia.</p>
      <p>The secret sauce is <strong>economic scale and diversification</strong>. Poland's 37mn population provides a domestic demand buffer that smaller CEE economies lack. The services sector (IT outsourcing, shared services, logistics) has been growing at 5%+, absorbing labour shed from manufacturing. This multi-engine growth model is rare in CEE and is the structural reason Poland commands the region's highest sovereign rating.</p>
    </div>
    <div class="narrative-col">
      <h4>What to Watch</h4>
      <ul>
        <li><strong>German spillovers</strong> — Poland is less exposed than Czechia or Hungary (exports to DE are ~27% of total vs 31% for CZ), but a prolonged German stagnation would eventually drag on manufacturing employment. Watch PMI new export orders.</li>
        <li><strong>Defence spending multiplier</strong> — Poland is spending ~4.2% of GDP on defence (NATO's highest share), with a large domestic procurement component. This is a sustained fiscal impulse that flows through construction, manufacturing, and technology sectors.</li>
        <li><strong>Labour supply constraint</strong> — with unemployment at 2.9%, the binding constraint on growth is not demand but labour supply. The Tusk government has liberalised work permits for non-EU migrants (mainly Ukraine, Belarus, India), but political sensitivity is rising.</li>
      </ul>
    </div>
  </div>
  <div class="narrative-footer">
    <strong>Market Implication:</strong> Poland's growth premium over CEE peers (~150bp of GDP) justifies the tighter sovereign spread. Long PLN assets vs CZK or HUF on a growth-divergence thesis, but be mindful that Poland's larger fiscal deficit partially offsets the growth advantage in the rates space. We prefer expressing the growth view through equity (WIG20 banks + industrials) rather than rates.
  </div>
</div>""",
        "prices_wages": """
<div class="narrative">
  <div class="narrative-header">
    <span class="narrative-label">Macro Narrative</span>
    <span class="narrative-date">April 2026</span>
  </div>
  <div class="narrative-body">
    <div class="narrative-col">
      <h4>What's Happened</h4>
      <p>Poland's inflation at <strong>4.5% CPI</strong> is the highest in CEE-4, stubbornly above the NBP's 2.5% target despite significant progress from the 18.4% peak in 2023. The stickiness comes from <strong>two domestic sources</strong>: (1) services inflation running at ~6.5% YoY, driven by wage passthrough in a labour-scarce economy, and (2) administered energy prices — the previous government's energy shield was partially unwound in H2 2025, adding ~1.5pp to headline. Core CPI ex-energy and food at 3.8% tells a more constructive story but remains above target.</p>
      <p>Wage growth at <strong>11.2% YoY</strong> is the region's highest in nominal terms. In real terms (~6.7%), it's fuelling consumption but keeping services inflation elevated. The NBP's own analysis suggests the NAIRU is around 3.5% — with unemployment at 2.9%, the economy is operating beyond full employment. This is a structural inflation impulse that rate cuts cannot address.</p>
    </div>
    <div class="narrative-col">
      <h4>What to Watch</h4>
      <ul>
        <li><strong>Energy price liberalisation</strong> — the Tusk government faces a choice: extend the energy shield (fiscally costly, ~1.5% GDP) or let it expire and accept a one-off CPI bump of ~1.0-1.5pp. The decision will determine whether CPI converges to ~3.5% or stays at ~5% through 2026.</li>
        <li><strong>Wage round Q1 2026</strong> — the January-March wage settlement season is critical. If the 2026 round lands above 9% (vs 11.2% in 2025), it signals moderation; if it accelerates, the NBP may need to hike.</li>
        <li><strong>NBP communication shift</strong> — Governor Glapiński has shifted from "rates on hold indefinitely" to "data dependent." The market is pricing a 25bp cut by Q4 2026. This is optimistic; we see the first cut in Q1 2027.</li>
      </ul>
    </div>
  </div>
  <div class="narrative-footer">
    <strong>Market Implication:</strong> With the NBP reference rate now at 3.75% versus MNB 6.25%, PLN no longer has the same carry cushion against HUF. The bullish PLN case depends more on EU-fund inflows, growth resilience, and lower risk premia than on outright policy-rate carry.
  </div>
</div>""",
        "external": """
<div class="narrative">
  <div class="narrative-header">
    <span class="narrative-label">Macro Narrative</span>
    <span class="narrative-date">April 2026</span>
  </div>
  <div class="narrative-body">
    <div class="narrative-col">
      <h4>What's Happened</h4>
      <p>Poland's external position is <strong>broadly balanced</strong> — the current account registered a small surplus of +0.8% GDP in 2025, a marked improvement from the -2.5% deficit in 2022. The improvement was driven by: (1) terms-of-trade recovery as energy import prices normalised, (2) strong services exports (IT, transport, shared services) running a ~+5% GDP surplus, and (3) EU transfer inflows (~3% GDP annually) that structurally support the current account.</p>
      <p>The REER has been relatively stable, appreciating only ~3% from the 2020 average — far less than CZK or HUF, reflecting the NBP's reluctance to allow PLN strength to erode export competitiveness. FX reserves at <strong>€170bn</strong> are the largest in CEE in absolute terms, covering ~7 months of imports — more than adequate by any metric. The NBP has also built a 420-tonne gold position (~13% of reserves), the largest in the region.</p>
    </div>
    <div class="narrative-col">
      <h4>What to Watch</h4>
      <ul>
        <li><strong>EU fund inflows</strong> — the RRF disbursement schedule implies €12-15bn of inflows in 2026. Each €5bn tranche tends to strengthen PLN by 1-2%, other things equal. The cumulative flow could push EURPLN from 4.30 to 4.15.</li>
        <li><strong>Energy dependence</strong> — Poland still relies on coal for ~70% of electricity generation. The energy transition (offshore wind, nuclear, LNG import infrastructure) is capital-intensive and will require sustained equipment imports — a structural drag on the trade balance over the medium term.</li>
        <li><strong>Geopolitical risk premium</strong> — Poland's eastern-flank exposure means PLN carries a geopolitical risk premium that CZK and HUF do not. This premium compresses during risk-on and widens sharply during risk-off. The option-implied EURPLN vol is ~1.5x EURCZK vol.</li>
      </ul>
    </div>
  </div>
  <div class="narrative-footer">
    <strong>Market Implication:</strong> The PLN is structurally undervalued on a FEER basis (fair value ~4.10-4.20 EURPLN). EU fund inflows and the NBP's hawkish hold provide a steady appreciation bias of 2-3% per annum. But the geopolitical risk premium means short PLN positions are dangerous in risk-off — this is a carry-and-convergence trade that requires patience and position discipline. 12m EURPLN forwards at 4.25 offer an attractive entry.
  </div>
</div>""",
        "fiscal_sovereign": """
<div class="narrative">
  <div class="narrative-header">
    <span class="narrative-label">Macro Narrative</span>
    <span class="narrative-date">April 2026</span>
  </div>
  <div class="narrative-body">
    <div class="narrative-col">
      <h4>What's Happened</h4>
      <p>Poland's fiscal position is <strong>deteriorating from a position of relative strength</strong>. The 2025 general government deficit printed at -5.1% of GDP, the widest since the COVID year of 2020. The drivers: (1) defence spending at 4.2% of GDP (~PLN 160bn, up from 2.2% in 2021), (2) the energy price shield (~1.5% GDP cost), and (3) social transfers (expanded child benefit, 13th/14th pension payments). These are mostly permanent, not cyclical.</p>
      <p>However, gross debt at <strong>~50% of GDP</strong> is well below the EU average (~83%) and the Maastricht 60% threshold. The debt stock is predominantly PLN-denominated (~73%) with a stable domestic investor base (Polish pension funds and insurers hold ~55% of outstanding government bonds). The 10y yield at 5.9% represents a spread of only ~130bp over Bunds — the tightest in CEE — reflecting Poland's A- rating and the market's confidence in debt sustainability.</p>
    </div>
    <div class="narrative-col">
      <h4>What to Watch</h4>
      <ul>
        <li><strong>EDP timeline</strong> — Poland is in the EU's Excessive Deficit Procedure (like most EU states post-COVID). The fiscal adjustment path required by Brussels is ~0.5% GDP per year. Meeting this while sustaining defence spending will require tax measures or spending cuts elsewhere — politically difficult in the pre-election period (presidential election 2025, parliamentary 2027).</li>
        <li><strong>Defence spending trajectory</strong> — the government has committed to maintaining defence spending above 3% of GDP through 2030. If funded through debt rather than revenue, this adds ~1-1.5pp to the deficit annually. The rating agencies are watching — a failure to consolidate outside defence could trigger a negative outlook.</li>
      </ul>
    </div>
  </div>
  <div class="narrative-footer">
    <strong>Market Implication:</strong> Poland's tight sovereign spread is built on the rating advantage and the deep domestic bid for PLN government bonds. The risk is a slow-burn fiscal deterioration that erodes the rating buffer over 2-3 years. We're not at the point of shorting POLGBs — the domestic bid is too deep — but the spread compression trade (long POLGB vs Bund) has run its course. Neutral duration, with a bias to receive in 2y where NBP expectations are mispriced.
  </div>
</div>""",
        "monetary_financial": """
<div class="narrative">
  <div class="narrative-header">
    <span class="narrative-label">Macro Narrative</span>
    <span class="narrative-date">April 2026</span>
  </div>
  <div class="narrative-body">
    <div class="narrative-col">
      <h4>What's Happened</h4>
      <p>The NBP hiked aggressively (0.1% → 6.75% in 2021-22), then moved through a delayed easing cycle. The official <strong>NBP reference rate is 3.75%</strong> after the spring 2026 cuts, and the May 2026 MPC decision kept rates unchanged. Governor Glapiński's rhetoric remains data dependent, emphasising inflation risks from fiscal expansion, wage growth, and energy-price normalisation.</p>
      <p>With headline CPI still above target, the <strong>real policy stance is only moderately restrictive</strong>. Private credit growth is healthy, M3 growth is running near 7%, and the banking sector is well-capitalised. The transmission mechanism is functioning, but the economy is still growing through the restrictive stance.</p>
    </div>
    <div class="narrative-col">
      <h4>What to Watch</h4>
      <ul>
        <li><strong>First cut timing</strong> — the market prices a 25bp cut by Q4 2026. We see Q1 2027 as more realistic. The NBP wants to see CPI below 3.5% and wage growth below 8% before easing. Neither condition is likely met before end-2026.</li>
        <li><strong>NBP vs MNB</strong> — Poland's NBP and Hungary's MNB are on diverging paths. MNB still offers a much higher nominal carry, while Poland's support comes more from growth, EU funds, and institutional risk compression.</li>
        <li><strong>Glapiński succession</strong> — the Governor's term runs to 2028, but political pressure from the Tusk government is a background risk. Any move to curtail NBP independence (unlikely but not impossible) would trigger a sharp PLN sell-off.</li>
      </ul>
    </div>
  </div>
  <div class="narrative-footer">
    <strong>Market Implication:</strong> The NBP's hold still supports PLN relative to lower-yielding EUR funding, but the carry cushion is thinner than the prior narrative implied. PLN longs now need EU-fund inflows and growth outperformance to do more of the work; size for geopolitical risk because the premium can re-price violently.
  </div>
</div>""",
        "markets_valuation": """
<div class="narrative">
  <div class="narrative-header">
    <span class="narrative-label">Macro Narrative</span>
    <span class="narrative-date">April 2026</span>
  </div>
  <div class="narrative-body">
    <div class="narrative-col">
      <h4>What's Happened</h4>
      <p>The <strong>WIG20 at ~2,450 (+5.4% YoY)</strong> is the best-performing CEE equity benchmark, driven by bank re-rating (PKO BP, Pekao, Santander BP — combined ~40% of index) and strong earnings from the IT/tech sector (CD Projekt, Allegro). The WIG20 forward P/E of ~10.5x is in line with the 10-year median but at a discount to DM Europe (~13x) — the discount reflects the geopolitical risk premium, not fundamentals.</p>
      <p>The structural story is Poland's deepening capital markets. The Warsaw Stock Exchange (GPW) has been the CEE region's primary equity venue, with total market cap of ~€200bn across the main and NewConnect markets. Foreign ownership of the free float is ~40% (down from ~55% in 2017), with domestic pension funds and retail investors filling the gap — a stabilising force in risk-off episodes. The banking sector is the earnings engine: Polish banks trade at ~1.3x P/B with ROE of ~14%.</p>
    </div>
    <div class="narrative-col">
      <h4>What to Watch</h4>
      <ul>
        <li><strong>Bank earnings peak?</strong> — NIM compression is beginning as the rate cycle turns. Q4 2025 NIM averaged 3.65%, down from 3.85% a year earlier. If the NBP cuts in H2 2026 (not our base case but the market's), bank earnings face a headwind. Defensive rotation into insurers (PZU) and utilities (PGE) would follow.</li>
        <li><strong>IPO pipeline</strong> — the Tusk government has signalled interest in listing minority stakes in state-owned enterprises. A successful IPO (e.g., PGE Renewables, PKP Cargo spin-off) would deepen the market and attract passive inflows.</li>
        <li><strong>Geopolitical discount</strong> — Poland's equity risk premium (ERP) is ~7.5%, roughly 200bp above DM Europe. If the security situation stabilises (NATO commitment credible, Ukraine ceasefire durable), 100bp of ERP compression implies ~12% index upside.</li>
      </ul>
    </div>
  </div>
  <div class="narrative-footer">
    <strong>Market Implication:</strong> WIG20 offers the best risk/reward in CEE equities. The combination of GDP growth leadership, deep capital markets, A- rating, and a diversified sector mix (banks, tech, energy, retail) makes Poland the core CEE equity allocation. Long WIG20 vs short BUX expresses the growth/fiscal divergence cleanly. December 2026 WIG20 calls at 2,600 strike offer cheap optionality on the ERP compression narrative.
  </div>
</div>""",
    },
    
        "financial_stability": """<div class="narrative">
  <div class="narrative-header"><span class="narrative-label">Macro Narrative</span><span class="narrative-date">April 2026</span></div>
  <div class="narrative-body">
    <div class="narrative-col">
      <h4>What's Happened</h4>
      <p>Poland's banking sector is <strong>the strongest in CEE-4</strong>. The aggregate CAR is ~19%, NPL ratio at ~3.8% (steady), and ROE of ~14% is the regional leader. The <strong>loan-to-deposit ratio at ~85%</strong> reflects a deeper deposit base than Hungary but lower self-funding than Czechia. PKO BP, Pekao, and Santander BP together control ~35% of system assets — the sector is more competitive and less concentrated than Hungary (OTP-dominant) or Czechia (Erste/KB duopoly).</p>
      <p>The <strong>NIM compression story</strong> is now more relevant because the NBP reference rate has moved down to 3.75% after the spring 2026 cuts. Aggregate NIM at ~3.65% is down only modestly from the 3.85% peak, but the direction of travel is lower. <strong>Household debt at ~25% of GDP</strong> is low but rising — the mortgage market is growing at 6%+ annually, driven by the government's 2% mortgage subsidy programme. Corporate debt at ~38% of GDP is the lowest in CEE-4.</p>
    </div>
    <div class="narrative-col">
      <h4>What to Watch</h4>
      <ul>
        <li><strong>CHF mortgage legacy</strong> — Poland's FX mortgage saga (CHF-denominated loans to households, ~€20bn stock) continues to generate legal risk. The ECJ has ruled in favour of consumers in several cases; aggregate provisioning stands at ~€5bn but tail risk remains.</li>
        <li><strong>Government housing subsidy</strong> — the 2% mortgage programme is fiscally costly (~0.3% GDP/year) and pro-cyclical in an already tight housing market. Warsaw apartment prices are up 15%+ YoY, raising overvaluation concerns.</li>
        <li><strong>Bank tax (0.44% of assets)</strong> — the government's bank asset tax is a structural drag on ROE. Any discussion of its repeal would be a significant positive catalyst for WIG20 banks.</li>
      </ul>
    </div>
  </div>
  <div class="narrative-footer"><strong>Market Implication:</strong> Polish banks (WIG20 banks at P/B ~1.3x, ROE ~14%) offer the best risk/reward in CEE financials. The NBP's hawkish hold supports NIM stability. Long PKO BP vs short OTP Bank captures the monetary policy divergence (NBP hold vs MNB cut). The CHF mortgage tail risk is the primary reason for cautious position sizing.</div>
</div>""",
        "demographics": """<div class="narrative">
  <div class="narrative-header"><span class="narrative-label">Structural Narrative</span><span class="narrative-date">2026 assessment</span></div>
  <div class="narrative-body">
    <div class="narrative-col">
      <h4>What's Happened</h4>
      <p>Poland has <strong>the most favourable demographic profile in CEE-4</strong> — which is to say, the least unfavourable. The population of 36.8mn is large enough to provide a domestic demand buffer that smaller CEE economies lack. The <strong>working-age population share at ~66%</strong> is the highest in CEE-4, and the old-age dependency ratio at ~29% is the lowest. However, the TFR at 1.3 is below the EU average and the population is projected to decline from the mid-2030s.</p>
      <p>The structural advantage is <strong>net migration</strong>. Poland has absorbed ~2mn Ukrainian refugees since 2022, of whom ~1mn remain. This is a significant positive labour supply shock — Ukrainian workers have higher labour force participation rates than the native population and are concentrated in services and construction. Additionally, the return migration of Polish workers from the UK (post-Brexit) and Germany has partially reversed the post-2004 emigration wave.</p>
    </div>
    <div class="narrative-col">
      <h4>What to Watch</h4>
      <ul>
        <li><strong>Ukrainian refugee permanence</strong> — the key demographic variable for Poland. If 50%+ of the ~1mn Ukrainian refugees remain permanently, it adds ~2% to the labour force and ~0.3pp to potential GDP growth. If they return post-war, Poland reverts to the CEE demographic norm.</li>
        <li><strong>Pension age reversal</strong> — the previous government lowered the retirement age to 60 (women) and 65 (men). Reversing this would be fiscally significant but politically difficult.</li>
        <li><strong>Regional inequality</strong> — Warsaw's population is growing while eastern voivodeships are depopulating. This internal migration creates housing market distortions and infrastructure bottlenecks.</li>
      </ul>
    </div>
  </div>
  <div class="narrative-footer"><strong>Market Implication:</strong> Poland's demographic advantage over CEE peers supports the growth premium and justifies the tighter sovereign spread. The Ukrainian labour supply shock is underappreciated by markets — it adds ~0.3pp to trend growth that is not in consensus forecasts. This supports long PLN assets on a structural basis.</div>
</div>""",
        "political_economy": """<div class="narrative">
  <div class="narrative-header"><span class="narrative-label">Structural Narrative</span><span class="narrative-date">2026 assessment</span></div>
  <div class="narrative-body">
    <div class="narrative-col">
      <h4>What's Happened</h4>
      <p>The Tusk government (since December 2023) has <strong>normalised Poland's relationship with EU institutions</strong>, unlocking ~€60bn in RRF funds and removing the rule-of-law conditionality threat. Poland's WGI scores have stabilised: government effectiveness at the ~70th percentile, rule of law at ~72nd, control of corruption at ~75th — all above the CEE-4 average. The A-/A2/A- sovereign rating reflects this institutional credibility.</p>
      <p>However, the <strong>political landscape is polarised</strong>. The PiS opposition retains ~33% support and the 2027 parliamentary election will be competitive. The presidential election (2025) was narrowly won by the Tusk-aligned candidate, confirming the government's mandate but showing the electorate is evenly divided. The key institutional risk is <strong>NBP independence</strong> — Governor Glapiński (PiS-aligned) has a term to 2028, creating a divided government-central bank dynamic.</p>
    </div>
    <div class="narrative-col">
      <h4>What to Watch</h4>
      <ul>
        <li><strong>2027 parliamentary election</strong> — polls show Tusk's coalition and PiS within the margin of error. A PiS return would re-introduce EU rule-of-law tensions and potentially freeze RRF disbursements.</li>
        <li><strong>NBP succession 2028</strong> — the appointment of the next NBP governor is the most important institutional decision of the Tusk term. A credible, market-friendly appointment would compress PLN risk premium.</li>
        <li><strong>Defence spending consensus</strong> — the 4.2% GDP defence spending enjoys cross-party support and anchors Poland's role as NATO's eastern-flank leader. This is a structural positive for Poland's geopolitical weight within the EU.</li>
      </ul>
    </div>
  </div>
  <div class="narrative-footer"><strong>Market Implication:</strong> Poland's institutional quality premium vs CEE peers is justified and supports the tight sovereign spread. The 2027 election is the primary political risk event — a PiS return would reprice PLN and POLGBs by 50-100bp wider. Hedge election risk via 6M PLN puts in H2 2026.</div>
</div>""",
	    "subtitle_zh": "综合国别概览，包含宏观叙事与前瞻性投资定位观点",
    "kpi_html_zh": """<div class="kpi-ribbon">
  <div class="kpi-card">
    <div class="kpi-label">实际GDP（同比）</div>
    <div class="kpi-value">+2.8%</div>
    <div class="kpi-sub"><span class="kpi-delta-up">中东欧领先</span> · 2025年Q4</div>
  </div>
  <div class="kpi-card warn">
    <div class="kpi-label">整体CPI（同比）</div>
    <div class="kpi-value">4.5%</div>
    <div class="kpi-sub">高于2.5%目标 · 2025年12月</div>
  </div>
  <div class="kpi-card warn">
    <div class="kpi-label">财政赤字</div>
    <div class="kpi-value">−5.1%</div>
    <div class="kpi-sub"><span class="kpi-delta-down">占GDP</span> · 2025年</div>
  </div>
  <div class="kpi-card">
    <div class="kpi-label">经常账户</div>
    <div class="kpi-value">+0.8%</div>
    <div class="kpi-sub"><span class="kpi-delta-up">盈余</span> · 占GDP 2025年</div>
  </div>
  <div class="kpi-card warn">
    <div class="kpi-label">政策利率</div>
    <div class="kpi-value">3.75%</div>
    <div class="kpi-sub">参考利率 · NBP暂缓降息</div>
  </div>
  <div class="kpi-card">
    <div class="kpi-label">10年期PLN收益率</div>
    <div class="kpi-value">5.90%</div>
    <div class="kpi-sub">~130bp高于Bund · 2026年4月</div>
  </div>
</div>""",
    "snapshot_prose_zh": """    <div class="snapshot-subsection">
      <h3>经济概况</h3>
      <p>波兰是<strong>中东欧最大经济体，GDP达$8450亿</strong>（2024年名义GDP），人口<strong>3680万</strong>，人均GDP<strong>$23,000</strong>。它是2008年全球金融危机期间唯一避免衰退的欧盟经济体，并在新冠疫情期间再次跑赢。产业基础涵盖<strong>汽车零部件及总装（欧洲最大汽车零部件出口国）、消费电子、IT服务、食品加工及煤炭/能源</strong>。主要贸易伙伴为<strong>德国、捷克、法国、英国和荷兰</strong>。波兰受益于庞大的内部市场、多元化的出口结构和结构性紧张的劳动力市场（失业率低于4%），支撑国内需求。</p>
    </div>
    <div class="snapshot-subsection">
      <h3>制度框架</h3>
      <p><strong>波兰国家银行（NBP）</strong>实行<strong>自由浮动</strong>汇率制度，正式通胀目标为<strong>2.5% ±1个百分点</strong>。波兰自2004年起为欧盟和北约成员国，但<strong>非欧元区成员</strong>——兹罗提独立浮动。主权信用评级为<strong>A−（标普）/ A2（穆迪）/ A−（惠誉）</strong>——中东欧最强，反映了波兰的多元化经济、可控债务（约50% GDP）和庞大的外汇储备（约€1700亿）。图斯克政府已部分解锁欧盟复苏基金（约€600亿）。</p>
    </div>
    <div class="snapshot-subsection">
      <h3>市场准入</h3>
      <p>基准<strong>WIG20指数</strong>远期市盈率约10.5倍——大致符合新兴欧洲同侪水平。<strong>10年期PLN国债收益率约5.9%</strong>，约130bp高于Bund——这一窄幅利差反映了波兰的评级优势及深厚的本地机构基础（养老金、保险）。<strong>EURPLN约4.30</strong>（2026年4月）接近5年均值。波兰拥有中东欧最深厚、最具流动性的资本市场——华沙证券交易所是该地区主要上市场所，所有上市公司总市值约€2000亿。</p>
    </div>""",
    "narratives_zh": {
        "real_activity": """<div class="narrative">
  <div class="narrative-header"><span class="narrative-label">宏观叙事</span><span class="narrative-date">2026年Q1评估</span></div>
  <div class="narrative-body">
    <div class="narrative-col">
      <h4>已发生的变化</h4>
      <p>波兰是<strong>中东欧的增长领跑者</strong>——2025年实际GDP增长约2.8%，约为中东欧四国均值的两倍。增长模式独特而均衡：<strong>国内消费</strong>（实际工资增长4%+，失业率处于2.9%的结构性低位）、<strong>强劲投资</strong>（欧盟资金推动基础设施和国防支出占GDP 4%+），以及<strong>韧性出口</strong>，尽管德国制造业衰退。工业生产同比+2.1%——温和但为正，与匈牙利和捷克的收缩形成对比。</p>
      <p>秘密武器是<strong>经济规模和多元化</strong>。波兰3700万人口提供了较小中东欧经济体所缺乏的内需缓冲。服务业（IT外包、共享服务、物流）以5%+的速度增长，吸收了制造业释放的劳动力。这种多引擎增长模式在中东欧罕见，是波兰获得该地区最高主权评级的结构性原因。</p>
    </div>
    <div class="narrative-col">
      <h4>需要关注</h4>
      <ul>
        <li><strong>德国溢出效应</strong>——波兰对德国敞口低于捷克或匈牙利（对德出口约占总出口27%，对比捷克31%），但德国长期停滞最终将拖累制造业就业。关注PMI新出口订单。</li>
        <li><strong>国防支出乘数</strong>——波兰国防支出约GDP的4.2%（北约最高），国内采购占比较大。这是持续的财政脉冲，贯穿建筑、制造和技术部门。</li>
        <li><strong>劳动力供给约束</strong>——失业率2.9%，增长的约束不是需求而是劳动力供给。图斯克政府已放宽非欧盟移民工签（主要是乌克兰、白俄罗斯、印度），但政治敏感性上升。</li>
      </ul>
    </div>
  </div>
  <div class="narrative-footer"><strong>市场含义：</strong>波兰相对中东欧同侪的增长溢价（约150bp GDP）证明了更紧的主权利差。基于增长分化做多PLN资产对CZK或HUF，但需注意波兰更大的财政赤字部分抵消了利率空间的增长优势。我们倾向于通过股票（WIG20银行+工业）而非利率来表达增长观点。</div>
</div>""",
        "prices_wages": """<div class="narrative">
  <div class="narrative-header"><span class="narrative-label">宏观叙事</span><span class="narrative-date">2026年4月</span></div>
  <div class="narrative-body">
    <div class="narrative-col">
      <h4>已发生的变化</h4>
      <p>波兰<strong>4.5%的CPI</strong>是中东欧四国中最高的，顽固地高于NBP 2.5%的目标，尽管从2023年18.4%的峰值已显著回落。粘性来自<strong>两个国内来源</strong>：（1）受劳动力稀缺经济中的工资传导推动，服务业通胀约6.5%；（2）行政能源价格——前政府的能源盾牌在2025年下半年部分解除，增加整体CPI约1.5个百分点。扣除能源和食品的核心CPI为3.8%，故事更富建设性但仍高于目标。</p>
      <p><strong>工资增长同比11.2%</strong>是该地区名义值最高的。实际值约6.7%，正在推动消费但使服务业通胀维持高位。NBP自身的分析表明NAIRU约为3.5%——失业率2.9%，经济运行已超出充分就业。这是降息无法解决的结构性通胀脉冲。</p>
    </div>
    <div class="narrative-col">
      <h4>需要关注</h4>
      <ul>
        <li><strong>能源价格自由化</strong>——图斯克政府面临选择：延长能源盾牌（财政成本约GDP的1.5%）或让其到期并接受一次性CPI跳升约1.0-1.5个百分点。该决定将决定CPI是收敛至约3.5%还是2026年全年维持在约5%。</li>
        <li><strong>2026年Q1工资谈判季</strong>——1-3月工资结算季至关重要。如果2026年谈判结果低于9%（对比2025年11.2%），则表明放缓；如果加速，NBP可能需要加息。</li>
        <li><strong>NBP沟通转变</strong>——行长Glapiński已从"无限期维持利率不变"转向"数据依赖"。市场定价2026年Q4降息25bp。这过于乐观；我们预计首次降息在2027年Q1。</li>
      </ul>
    </div>
  </div>
  <div class="narrative-footer"><strong>市场含义：</strong>NBP参考利率为3.75%，低于MNB 6.25%。PLN相对HUF不再拥有旧叙事中的利差缓冲；看多PLN更多依赖欧盟资金流入、增长韧性和风险溢价压缩，而不是单纯利差。</div>
</div>""",
        "external": """<div class="narrative">
  <div class="narrative-header"><span class="narrative-label">宏观叙事</span><span class="narrative-date">2026年4月</span></div>
  <div class="narrative-body">
    <div class="narrative-col">
      <h4>已发生的变化</h4>
      <p>波兰的对外部门<strong>基本平衡</strong>——2025年经常账户录得GDP的+0.8%小额顺差，较2022年-2.5%逆差显著改善。驱动因素：（1）能源进口价格正常化推动贸易条件恢复；（2）强劲的服务出口（IT、运输、共享服务）录得约GDP+5%顺差；（3）欧盟转移支付流入（年均约GDP 3%）结构性支撑经常账户。</p>
      <p>REER相对稳定，自2020年均值仅升值约3%——远低于CZK或HUF，反映NBP不愿让PLN走强侵蚀出口竞争力。<strong>外汇储备€1700亿</strong>是中东欧绝对值最大的，覆盖约7个月进口——任何指标均属充裕。NBP还建立了420吨黄金头寸（约储备的13%），为该地区最大。</p>
    </div>
    <div class="narrative-col">
      <h4>需要关注</h4>
      <ul>
        <li><strong>欧盟资金流入</strong>——复苏基金拨付计划意味着2026年将有€120-150亿流入。每€50亿批次通常推动PLN升值1-2%。累积流入可能推动EURPLN从4.30至4.15。</li>
        <li><strong>能源依赖</strong>——波兰仍约70%依赖煤电。能源转型（海上风电、核电、LNG进口基础设施）资本密集，需要持续的进口设备——中期内对贸易差额构成结构性拖累。</li>
        <li><strong>地缘政治风险溢价</strong>——波兰的东翼敞口意味着PLN承载CZK和HUF所不具备的地缘政治风险溢价。该溢价在risk-on期间压缩，在risk-off期间急剧扩大。期权隐含EURPLN波动率约为EURCZK的1.5倍。</li>
      </ul>
    </div>
  </div>
  <div class="narrative-footer"><strong>市场含义：</strong>基于FEER，PLN结构性低估（公允价值约4.10-4.20 EURPLN）。欧盟资金流入和NBP鹰派维持提供年均2-3%的稳步升值偏向。但地缘政治风险溢价意味着在risk-off中做空PLN是危险的——这是一笔需要耐心和头寸纪律的利差收益与收敛交易。12个月EURPLN远期4.25提供有吸引力的入场点。</div>
</div>""",
        "fiscal_sovereign": """<div class="narrative">
  <div class="narrative-header"><span class="narrative-label">宏观叙事</span><span class="narrative-date">2026年4月</span></div>
  <div class="narrative-body">
    <div class="narrative-col">
      <h4>已发生的变化</h4>
      <p>波兰的财政状况正在<strong>从相对强势地位恶化</strong>。2025年一般政府赤字为GDP的-5.1%，为2020年新冠疫情以来最宽。驱动因素：（1）国防支出占GDP的4.2%（约PLN 1600亿，高于2021年2.2%）；（2）能源价格盾牌（约GDP 1.5%成本）；（3）社会转移支付（扩大儿童福利、第13/14个月养老金）。这些大多是永久性的，非周期性。</p>
      <p>然而，总债务<strong>约GDP的50%</strong>显著低于欧盟均值（约83%）和马斯特里赫特60%门槛。债务存量以PLN计价为主（约73%），拥有稳定的国内投资者基础（波兰养老基金和保险公司持有约55%的存量国债）。10年期收益率5.9%意味着仅约130bp的Bund利差——中东欧最窄——反映波兰A-评级和市场对债务可持续性的信心。</p>
    </div>
    <div class="narrative-col">
      <h4>需要关注</h4>
      <ul>
        <li><strong>EDP时间表</strong>——波兰处于欧盟过度赤字程序之中（与大多数新冠疫情后欧盟国家一样）。布鲁塞尔要求的财政调整路径为年均约GDP 0.5%。在维持国防支出的同时实现这将需要税收措施或其他领域支出削减——在大选前夕政治困难（总统选举2025年，议会2027年）。</li>
        <li><strong>国防支出轨迹</strong>——政府承诺至2030年维持国防支出在GDP的3%以上。如果通过债务而非收入融资，每年对赤字增加约1-1.5个百分点。评级机构正在关注——国防以外的整顿失败可能触发负面展望。</li>
      </ul>
    </div>
  </div>
  <div class="narrative-footer"><strong>市场含义：</strong>波兰紧窄的主权利差建立在评级优势和深厚的国内PLN国债买盘之上。风险在于缓慢的财政侵蚀在2-3年内侵蚀评级缓冲。我们尚未到做空POLGB的地步——国内买盘太深——但利差压缩交易（做多POLGB对Bund）已经结束。中性久期，偏向在2年期做多，该期限NBP预期定价错误。</div>
</div>""",
        "monetary_financial": """<div class="narrative">
  <div class="narrative-header"><span class="narrative-label">宏观叙事</span><span class="narrative-date">2026年4月</span></div>
  <div class="narrative-body">
    <div class="narrative-col">
      <h4>已发生的变化</h4>
      <p>NBP激进加息（2021-22年0.1%→6.75%），随后进入延迟宽松周期。官方<strong>NBP参考利率目前为3.75%</strong>，2026年5月货币政策委员会决定维持不变。行长Glapiński的沟通仍强调数据依赖，重点关注财政扩张、工资增长和能源价格正常化带来的通胀风险。</p>
      <p>在整体CPI仍高于目标的背景下，<strong>实际政策立场只是中度紧缩</strong>。私人信贷增长健康，M3增长约7%，银行业资本充足。传导机制运转正常，但经济仍在较高利率环境中保持增长。</p>
    </div>
    <div class="narrative-col">
      <h4>需要关注</h4>
      <ul>
        <li><strong>首次降息时机</strong>——市场定价2026年Q4降息25bp。我们认为2027年Q1更为现实。NBP希望在放松前看到CPI低于3.5%且工资增长低于8%。这两个条件在2026年底前均不太可能满足。</li>
        <li><strong>NBP vs MNB</strong>——波兰NBP和匈牙利MNB正走向分化路径。MNB仍提供更高名义利差，而波兰的支撑更多来自增长、欧盟资金和制度风险溢价压缩。</li>
        <li><strong>Glapiński继任</strong>——行长任期至2028年，但图斯克政府的政治压力是背景风险。任何削弱NBP独立性的举动（不太可能但并非不可能）将触发PLN急剧抛售。</li>
      </ul>
    </div>
  </div>
  <div class="narrative-footer"><strong>市场含义：</strong>NBP维持利率仍支持PLN相对低收益EUR融资货币，但利差缓冲低于旧叙事。PLN多头现在更依赖欧盟资金和增长跑赢；需为地缘政治风险溢价重定价控制仓位。</div>
</div>""",
        "markets_valuation": """<div class="narrative">
  <div class="narrative-header"><span class="narrative-label">宏观叙事</span><span class="narrative-date">2026年4月</span></div>
  <div class="narrative-body">
    <div class="narrative-col">
      <h4>已发生的变化</h4>
      <p><strong>WIG20约2,450点（同比+5.4%）</strong>是表现最佳的中东欧股票基准，受银行重估（PKO BP、Pekao、Santander BP——合计约40%权重）和IT/科技板块强劲盈利（CD Projekt、Allegro）推动。WIG20远期市盈率约10.5倍符合10年中位数，但相对发达市场欧洲（约13倍）折价——折价反映地缘政治风险溢价，而非基本面。</p>
      <p>结构性故事是波兰不断深化的资本市场。华沙证券交易所（GPW）一直是中东欧地区的主要股票市场，主板和NewConnect合计总市值约€2000亿。自由流通股的外资持股约40%（低于2017年约55%），国内养老基金和散户填补了空缺——在risk-off中起到稳定作用。银行业是盈利引擎：波兰银行市净率约1.3倍，ROE约14%。</p>
    </div>
    <div class="narrative-col">
      <h4>需要关注</h4>
      <ul>
        <li><strong>银行盈利见顶？</strong>——随着利率周期转向，NIM压缩已经开始。2025年Q4平均NIM为3.65%，较一年前3.85%下降。如果NBP在2026年下半年降息（非我们的基准但为市场共识），银行盈利面临阻力。防御性转向保险（PZU）和公用事业（PGE）将随之而来。</li>
        <li><strong>IPO管道</strong>——图斯克政府已暗示有意上市国有企业少数股权。成功的IPO（如PGE Renewables、PKP Cargo分拆）将加深市场并吸引被动流入。</li>
        <li><strong>地缘政治折价</strong>——波兰股权风险溢价（ERP）约7.5%，大致比发达市场欧洲高出200bp。如果安全局势稳定（北约承诺可信，乌克兰停火持久），100bp的ERP压缩意味着指数上行约12%。</li>
      </ul>
    </div>
  </div>
  <div class="narrative-footer"><strong>市场含义：</strong>WIG20提供中东欧股票中最佳的风险/回报。GDP增长领先、深厚资本市场、A-评级和多元化行业结构（银行、科技、能源、零售）的组合使波兰成为中东欧股票的核心配置。做多WIG20对做空BUX干净地表达增长/财政分化。2026年12月WIG20看涨期权2,600行权价提供ERP压缩叙事的廉价期权性。</div>
</div>""",
    
        "financial_stability": """<div class="narrative">
  <div class="narrative-header"><span class="narrative-label">宏观叙事</span><span class="narrative-date">2026年4月</span></div>
  <div class="narrative-body">
    <div class="narrative-col">
      <h4>已发生的变化</h4>
      <p>波兰银行业是<strong>中东欧四国中最强健的</strong>。整体CAR约19%，不良贷款率约3.8%（稳定），ROE约14%为区域领先。<strong>存贷比约85%</strong>反映比匈牙利更深的存款基础。PKO BP、Pekao和Santander BP合计控制系统资产约35%——该行业比匈牙利（OTP主导）或捷克（Erste/KB双头垄断）更具竞争性、更不集中。</p>
      <p><strong>净息差压缩</strong>现在更值得关注，因为NBP参考利率已降至3.75%。整体NIM约3.65%仅从峰值3.85%小幅下降，但方向是下行。<strong>居民债务约GDP的25%</strong>较低但正在上升——按揭市场受政府2%按揭补贴计划推动以6%+年增速增长。企业债务约GDP的38%为中东欧四国最低。</p>
    </div>
    <div class="narrative-col">
      <h4>需要关注</h4>
      <ul>
        <li><strong>瑞郎按揭遗留</strong>——波兰外汇按揭事件（居民CHF贷款，约€200亿存量）持续产生法律风险。ECJ在多个案件中作出有利于消费者的裁决；累计拨备约€50亿但尾部风险犹存。</li>
        <li><strong>政府住房补贴</strong>——2%按揭计划财政成本高昂（约GDP的0.3%/年）且在已紧张的市场中顺周期。华沙公寓价格同比上涨15%+，引发高估担忧。</li>
        <li><strong>银行资产税（0.44%）</strong>——政府的银行资产税对ROE构成结构性拖累。任何废除讨论将是WIG20银行的重要积极催化剂。</li>
      </ul>
    </div>
  </div>
  <div class="narrative-footer"><strong>市场含义：</strong>波兰银行（WIG20银行市净率约1.3倍，ROE约14%）提供中东欧金融股最佳风险/回报。NBP鹰派维持支撑净息差稳定。做多PKO BP对做空OTP银行捕捉货币政策分化。瑞郎按揭尾部风险是审慎头寸管理的主要原因。</div>
</div>""",
        "demographics": """<div class="narrative">
  <div class="narrative-header"><span class="narrative-label">结构性叙事</span><span class="narrative-date">2026年评估</span></div>
  <div class="narrative-body">
    <div class="narrative-col">
      <h4>已发生的变化</h4>
      <p>波兰拥有<strong>中东欧四国中最有利的人口结构</strong>——也就是说，最不不利的。3680万人口规模足以提供较小中东欧经济体所缺乏的内需缓冲。<strong>劳动年龄人口占比约66%</strong>为中东欧四国中最高，老年抚养比约29%是最低的。然而总和生育率1.3低于欧盟均值，人口预计从2030年代中期开始下降。</p>
      <p>结构性优势是<strong>净移民</strong>。波兰自2022年以来吸收约200万乌克兰难民，其中约100万留下。这是重要的积极劳动力供给冲击——乌克兰工人劳动参与率高于本地人口，集中于服务和建筑业。此外，波兰工人从英国（脱欧后）和德国的回流部分逆转了2004年后的移民潮。</p>
    </div>
    <div class="narrative-col">
      <h4>需要关注</h4>
      <ul>
        <li><strong>乌克兰难民永久性</strong>——波兰的关键人口变量。如果50%+的约100万乌克兰难民永久留下，劳动力增加约2%，潜在GDP增长增加约0.3个百分点。如果战后返回，波兰回归中东欧人口常态。</li>
        <li><strong>退休年龄逆转</strong>——前政府将退休年龄降至女性60岁、男性65岁。逆转此政策财政意义重大但政治困难。</li>
      </ul>
    </div>
  </div>
  <div class="narrative-footer"><strong>市场含义：</strong>波兰相对中东欧同侪的人口优势支持增长溢价并证明更紧的主权利差。乌克兰劳动力供给冲击被市场低估——为趋势增长增加约0.3个百分点，不在一致预期中。这结构性支持做多PLN资产。</div>
</div>""",
        "political_economy": """<div class="narrative">
  <div class="narrative-header"><span class="narrative-label">结构性叙事</span><span class="narrative-date">2026年评估</span></div>
  <div class="narrative-body">
    <div class="narrative-col">
      <h4>已发生的变化</h4>
      <p>图斯克政府（自2023年12月起）已<strong>正常化波兰与欧盟机构的关系</strong>，解锁约€600亿复苏基金并消除法治条件性威胁。波兰WGI评分已稳定：政府效能约70百分位，法治约72百分位，腐败控制约75百分位——均高于中东欧四国均值。A-/A2/A-主权评级反映这一制度可信度。</p>
      <p>然而<strong>政治格局两极分化</strong>。PiS反对派保持约33%支持率，2027年议会选举将具竞争性。2025年总统选举由亲图斯克候选人微弱胜出，确认政府授权但显示选民势均力敌。关键制度风险是<strong>NBP独立性</strong>——行长Glapiński（PiS阵营）任期至2028年，形成分裂的政府-央行动态。</p>
    </div>
    <div class="narrative-col">
      <h4>需要关注</h4>
      <ul>
        <li><strong>2027年议会选举</strong>——民调显示图斯克联盟与PiS在误差范围内。PiS回归将重新引入欧盟法治紧张并可能冻结复苏基金拨付。</li>
        <li><strong>2028年NBP继任</strong>——下任NBP行长的任命是图斯克任期最重要的制度决策。可信、市场友好的任命将压缩PLN风险溢价。</li>
        <li><strong>国防支出共识</strong>——4.2% GDP国防支出享有跨党派支持，锚定波兰作为北约东翼领导者的角色。这是波兰在欧盟内地缘政治分量的结构性积极因素。</li>
      </ul>
    </div>
  </div>
  <div class="narrative-footer"><strong>市场含义：</strong>波兰相对中东欧同侪的制度质量溢价合理，支持紧窄的主权利差。2027年选举是主要政治风险事件——PiS回归将使PLN和POLGB重定价扩大50-100bp。通过2026年下半年6个月PLN看跌期权对冲选举风险。</div>
</div>""",
    },
}

# ═══ CZECHIA ═══
COUNTRY_DATA["CZ"] = {
    "name": "Czechia",
    "iso": "CZK",
    "cb": "CNB",
    "gen_date": "2026-04-26",
    "peers": "HU, PL, RO",
    "rating": "AA− / Aa3 / AA−",
    "fxregime": "Managed Float",
    "inftarget": "2.0% ±1pp CPI",
    "equity_index": "PX",
    "subtitle": "Comprehensive country primer with macro narratives and forward-looking positioning views",
    "kpi_html": """
  <div class="kpi-ribbon">
    <div class="kpi-card">
      <div class="kpi-label">Real GDP (YoY)</div>
      <div class="kpi-value">+1.1%</div>
      <div class="kpi-sub"><span class="kpi-delta-down">Below trend</span> · Q4 2025</div>
    </div>
    <div class="kpi-card">
      <div class="kpi-label">Headline CPI (YoY)</div>
      <div class="kpi-value">2.6%</div>
      <div class="kpi-sub">Within 2.0% ±1pp band · Dec 2025</div>
    </div>
    <div class="kpi-card">
      <div class="kpi-label">Fiscal Balance</div>
      <div class="kpi-value">−2.2%</div>
      <div class="kpi-sub"><span class="kpi-delta-up">Best in CEE-4</span> · 2025</div>
    </div>
    <div class="kpi-card">
      <div class="kpi-label">Current Account</div>
      <div class="kpi-value">+2.8%</div>
      <div class="kpi-sub"><span class="kpi-delta-up">Strong surplus</span> · of GDP 2025</div>
    </div>
    <div class="kpi-card">
      <div class="kpi-label">Policy Rate</div>
      <div class="kpi-value">3.50%</div>
      <div class="kpi-sub">Real rate ~1.4% · CNB cutting cycle</div>
    </div>
    <div class="kpi-card">
      <div class="kpi-label">10Y CZK Yield</div>
      <div class="kpi-value">4.20%</div>
      <div class="kpi-sub">~40bp under PLN · Apr 2026</div>
    </div>
  </div>""",
    "snapshot_prose": """
    <div class="snapshot-subsection">
      <h3>Economy</h3>
      <p>Czechia is a <strong>$345 bn economy</strong> (2024 nominal GDP) with a population of <strong>10.9 million</strong> and the <strong>highest GDP per capita in CEE at $31,600</strong> (PPP-adjusted above Italy and Spain). The economy is the most manufacturing-intensive in the EU, centred on <strong>automotive OEM &amp; supply chain (&Scaron;koda/VW, Hyundai, Toyota), machinery &amp; precision engineering, electronics, and beer &amp; beverages</strong>. Top trading partners are <strong>Germany, Slovakia, Poland, France, and Austria</strong> — Czechia is the most deeply integrated into German supply chains of any CEE economy, making it a leveraged play on the German industrial cycle.</p>
    </div>
    <div class="snapshot-subsection">
      <h3>Institutional Framework</h3>
      <p>The <strong>&Ccaron;esk&aacute; n&aacute;rodn&iacute; banka (CNB)</strong> operates a <strong>managed float</strong> FX regime with a formal inflation target of <strong>2.0% &plusmn;1pp</strong>. Czechia is an EU and NATO member since 2004 but <strong>not a euro-area member</strong>. Sovereign credit rating stands at <strong>AA&minus; (S&amp;P) / Aa3 (Moody&rsquo;s) / AA&minus; (Fitch)</strong> — the highest in CEE, reflecting fiscal conservatism (debt ~43% GDP), a persistent current account surplus, and the deepest capital stock per capita in the region. The CNB is the most transparent CEE central bank, publishing its own interest-rate forecast path.</p>
    </div>
    <div class="snapshot-subsection">
      <h3>Market Access</h3>
      <p>The benchmark <strong>PX index</strong> (~1,600) trades at a forward P/E of ~12.0x — a premium to CEE peers reflecting Czechia's AA- rating. The PX is dominated by banks (Erste, Komer&ccaron;n&iacute; banka — ~45% weight) and utilities (&Ccaron;EZ — ~20% weight), giving it a defensive, dividend-heavy character. The <strong>10-year CZK government bond yields ~4.2%</strong> — below PLN and HGB yields, consistent with the rating hierarchy. The <strong>EURCZK at ~25.0</strong> (April 2026) is ~8% weaker than the pre-COVID average of ~25.5, reflecting the CNB's aggressive rate cuts and a terms-of-trade drag from energy imports.</p>
    </div>""",
    "narratives": {
        "real_activity": """
<div class="narrative">
  <div class="narrative-header">
    <span class="narrative-label">Macro Narrative</span>
    <span class="narrative-date">Q1 2026 assessment</span>
  </div>
  <div class="narrative-body">
    <div class="narrative-col">
      <h4>What's Happened</h4>
      <p>Czechia is <strong>stuck in a shallow-growth equilibrium</strong>. Real GDP expanded just +1.1% YoY in Q4 2025, the weakest in CEE-4. The economy is being dragged down by its own structural strength: <strong>manufacturing is ~25% of GDP</strong> (highest in the EU), and the German manufacturing recession has hit Czech industry disproportionately. Industrial production at -2.0% YoY reflects the auto supply chain — &Scaron;koda/VW alone represents ~5% of GDP and ~10% of exports. The order-book-to-shipment ratio is at its lowest since 2020.</p>
      <p>But the domestic economy is holding up better than the headline suggests. <strong>Unemployment at 2.6%</strong> (EU's lowest) means the labour market is a structural support — anyone who wants a job has one. Real wages are growing ~4% as inflation normalises, and household consumption contributed positively to GDP in every quarter of 2025. The problem is investment: corporates are deferring capex decisions amid German uncertainty and the CNB's cutting cycle has not yet translated into a credit recovery.</p>
    </div>
    <div class="narrative-col">
      <h4>What to Watch</h4>
      <ul>
        <li><strong>German IFO cycle</strong> — Czechia's PMI has been sub-50 for 24 of the last 27 months. The single variable that matters is German manufacturing orders. A sustained IFO expectations recovery above 95 would be the signal to go long Czech assets.</li>
        <li><strong>&Scaron;koda EV transition</strong> — &Scaron;koda is investing €5.6bn in electrification (2024-28), with three new EV models launching in 2025-26. Success or failure of these launches will determine the trajectory of 10% of Czech exports over the next decade.</li>
        <li><strong>CNB easing transmission</strong> — the CNB has cut 350bp from the peak (7.0% → 3.5%) but private credit growth remains negative in real terms. The transmission lag suggests the growth impulse from easing hits in H2 2026 at the earliest.</li>
      </ul>
    </div>
  </div>
  <div class="narrative-footer">
    <strong>Market Implication:</strong> Czechia is a high-beta play on the German industrial cycle. If Germany recovers, CZK and Czech equities outperform CEE peers by 5-8% within 6 months. If Germany flatlines, Czech assets underperform. We'd size a long CZK vs EUR position as a call option on German recovery — define the risk with a tight stop at EURCZK 25.50. In equities, long PX banks (Erste) vs short DAX auto represents a relative-value expression of the same theme with less directionality.
  </div>
</div>""",
        "prices_wages": """
<div class="narrative">
  <div class="narrative-header">
    <span class="narrative-label">Macro Narrative</span>
    <span class="narrative-date">April 2026</span>
  </div>
  <div class="narrative-body">
    <div class="narrative-col">
      <h4>What's Happened</h4>
      <p>Czechia has achieved <strong>the softest landing in CEE</strong> on the inflation front. Headline CPI at <strong>2.6% YoY</strong> is within the CNB's 2.0% ±1pp tolerance band, down from a peak of 18.0% in early 2023. The disinflation was textbook: energy base effects accounted for ~70% of the decline, with the remaining 30% from genuine demand compression via the 2021-23 rate shock. Core CPI at 2.3% is the lowest in CEE.</p>
      <p>The CNB's early and aggressive cutting cycle (7.0% → 3.50% by May 2025, then held through May 2026) was predicated on this disinflation success. But wage growth at <strong>7.4% YoY</strong> in a 2.6% unemployment economy raises the question of whether the easing was premature. The CNB's own forecast sees CPI grinding to 2.0% by mid-2026, but the wage impulse and the closed output gap argue for inflation settling closer to 2.5-3.0% — within band but above target midpoint.</p>
    </div>
    <div class="narrative-col">
      <h4>What to Watch</h4>
      <ul>
        <li><strong>CNB terminal rate debate</strong> — with the 2W repo rate at 3.50%, the question is whether the easing cycle is effectively done. The risk is that the terminal rate lands at or above the current level — services inflation at 3.8% and 7%+ wages don't justify a materially lower policy rate.</li>
        <li><strong>Housing market re-acceleration</strong> — Prague property prices, which fell ~10% during the rate-hiking cycle, have stabilised and are beginning to rise again as mortgage rates fall below 4.5%. A renewed housing boom would flow through to imputed rents (~10% of CPI basket) and keep core CPI elevated.</li>
      </ul>
    </div>
  </div>
  <div class="narrative-footer">
    <strong>Market Implication:</strong> The CZK rates market should be treated as close to terminal. Receive/payer structures need to reflect that the easy part of the CNB cutting cycle is over. In FX, the CNB cutting cycle has weakened CZK from 24.0 to 25.0 — a lot of bad news is priced. If the cycle is done, EURCZK could reprice to 24.50.
  </div>
</div>""",
        "external": """
<div class="narrative">
  <div class="narrative-header">
    <span class="narrative-label">Macro Narrative</span>
    <span class="narrative-date">April 2026</span>
  </div>
  <div class="narrative-body">
    <div class="narrative-col">
      <h4>What's Happened</h4>
      <p>Czechia runs a <strong>persistent current account surplus</strong> — +2.8% of GDP in 2025, the largest in CEE-4. This is a structural feature: the manufacturing export engine (vehicles, machinery) generates a ~+8% GDP goods surplus, which more than offsets the income deficit (dividend and profit repatriation by foreign-owned firms). The trade surplus with Germany alone (~€15bn annually) is roughly 4% of Czech GDP.</p>
      <p>FX reserves at <strong>€140bn</strong> are the largest relative to GDP in the EU (~40% of GDP), a legacy of the 2013-17 EURCZK floor. The CNB has been running this massive reserve position at a negative carry (~200bp, funding short-CZK liabilities against long-EUR assets), generating mark-to-market volatility but providing an unassailable defence against CZK speculative attacks. The REER has depreciated ~5% from its 2023 peak, restoring competitiveness lost during the inflation overshoot.</p>
    </div>
    <div class="narrative-col">
      <h4>What to Watch</h4>
      <ul>
        <li><strong>Reserve divestment?</strong> — Governor Michl has signalled an intention to reduce the FX reserve stock gradually. Any CNB FX sales (EURCZK buying) would weaken CZK. But the practical scope is limited — the market would interpret aggressive sales as a policy error.</li>
        <li><strong>Auto export cycle</strong> — Czech auto exports are ~8% of GDP. A 10% decline in German car registrations translates to a ~0.8% GDP drag on Czechia. The EV transition adds structural uncertainty — the Czech supply chain is ICE-optimised.</li>
        <li><strong>Energy dependence</strong> — Czechia has largely weaned itself off Russian gas (LNG via Dutch/German terminals, Norwegian pipeline gas), but remains energy-import dependent. The terms-of-trade drag from the 2022-23 energy shock has largely reversed.</li>
      </ul>
    </div>
  </div>
  <div class="narrative-footer">
    <strong>Market Implication:</strong> The CA surplus is a structural CZK bid, but it's offset by the CNB's dovish stance and the negative carry on the FX reserve position. CZK is not a clean carry trade. We prefer expressing Czech external strength through the sovereign credit (long CZGBs vs HGBs at a ~300bp spread pickup on a AA- vs BBB- basis). The CZK is a range trade: buy at 25.20, sell at 24.50.
  </div>
</div>""",
        "fiscal_sovereign": """
<div class="narrative">
  <div class="narrative-header">
    <span class="narrative-label">Macro Narrative</span>
    <span class="narrative-date">April 2026</span>
  </div>
  <div class="narrative-body">
    <div class="narrative-col">
      <h4>What's Happened</h4>
      <p>Czechia is <strong>the fiscal champion of CEE</strong>. The 2025 general government deficit printed at just -2.2% of GDP, the narrowest in CEE-4 and below the 3% Maastricht reference. The SPOLU coalition government under PM Fiala has delivered on fiscal consolidation: the deficit has halved from -5.1% in 2021 through a combination of tax increases (corporate income tax, windfall tax on banks/energy) and spending restraint.</p>
      <p>Gross debt at <strong>~43% of GDP</strong> is the lowest in the EU and well below the Maastricht 60% threshold. The debt is predominantly CZK-denominated (~90%), with a stable domestic investor base. The 10y yield at 4.2% represents a spread of only ~40bp under Poland — remarkable given Czechia's two-notch rating advantage. The tight spread is partly technical: the CZGB market is smaller and less liquid than POLGBs, limiting foreign participation.</p>
    </div>
    <div class="narrative-col">
      <h4>What to Watch</h4>
      <ul>
        <li><strong>ANO fiscal policy</strong> — if ANO wins the 2025 parliamentary election (polls suggest it's likely), fiscal policy could shift toward expansion. Babi&scaron;'s platform is light on detail but heavy on spending promises (pension hikes, infrastructure). Markets are not pricing this risk.</li>
        <li><strong>Defence spending ramp</strong> — Czechia has committed to 2% of GDP defence spending (NATO target), up from 1.3% in 2023. The incremental ~0.7% GDP cost is manageable from the current fiscal position but adds to the structural deficit.</li>
      </ul>
    </div>
  </div>
  <div class="narrative-footer">
    <strong>Market Implication:</strong> CZGBs at 4.2% offer the best risk-adjusted carry in CEE sovereign credit. The AA- rating, 43% debt/GDP, and persistent CA surplus make this the regional safe haven. Long 10y CZGBs vs 10y HGBs at a ~290bp spread — the rating differential (5 notches) vs the spread differential is not fully priced. The primary risk is an ANO-driven fiscal expansion; monitor election polls closely.
  </div>
</div>""",
        "monetary_financial": """
<div class="narrative">
  <div class="narrative-header">
    <span class="narrative-label">Macro Narrative</span>
    <span class="narrative-date">April 2026</span>
  </div>
  <div class="narrative-body">
    <div class="narrative-col">
      <h4>What's Happened</h4>
      <p>The CNB has been <strong>the most aggressive cutter in CEE</strong>, bringing the 2W repo rate from 7.0% to <strong>3.50%</strong> by May 2025 and then holding it unchanged through May 2026. The cutting cycle was data-dependent and well-communicated — the CNB's published forecast path (a transparency practice unique in CEE) guided market expectations effectively.</p>
      <p>The transmission mechanism is working but with lags. Mortgage rates have fallen from ~6.5% to ~4.5%, driving a tentative housing market recovery. But <strong>private credit growth at +2.1% YoY</strong> remains anaemic — corporations are not borrowing because they're not investing, not because credit is expensive. The CNB faces the classic pushing-on-a-string problem: rate cuts can't force firms to invest when German demand is absent. M3 growth at 5.5% is healthy but not expansionary.</p>
    </div>
    <div class="narrative-col">
      <h4>What to Watch</h4>
      <ul>
        <li><strong>Terminal rate landing zone</strong> — CNB staff analysis puts the neutral rate at 3.0-3.5%. We think 3.75% is more realistic given the tight labour market and wage growth. The next 2-3 meetings (25bp cuts expected at each) will define the terminal rate debate.</li>
        <li><strong>FX passthrough risk</strong> — CZK has weakened from 24.0 to 25.0 during the cutting cycle. A further move to 25.50+ (from EURCZK buying by corporates, energy importers, or the CNB's reserve operations) would add ~0.3pp to CPI via import prices. This is a self-limiting mechanism on cuts.</li>
        <li><strong>CNB vs ECB</strong> — the CNB-ECB spread has compressed from 300bp to 75bp. If the CNB cuts further and the ECB holds, the carry attraction of CZK diminishes, potentially weakening CZK further.</li>
      </ul>
    </div>
  </div>
  <div class="narrative-footer">
    <strong>Market Implication:</strong> The CNB cutting cycle is approaching its end. Front-end CZK rates are pricing 75bp more cuts; we see 25-50bp. Receive 2y CZK vs pay 2y EUR — the CNB will stop cutting before the market thinks, and the ECB will cut more than the market thinks. In FX, EURCZK at 25.0 is close to fair value on a rate-differential basis. Range trade with a hawkish CNB tilt.
  </div>
</div>""",
        "markets_valuation": """
<div class="narrative">
  <div class="narrative-header">
    <span class="narrative-label">Macro Narrative</span>
    <span class="narrative-date">April 2026</span>
  </div>
  <div class="narrative-body">
    <div class="narrative-col">
      <h4>What's Happened</h4>
      <p>The <strong>PX index at ~1,600 (+3.1% YoY)</strong> has been a middling performer in CEE — better than BUX (-2.9%) but lagging WIG20 (+5.4%). The PX is a concentrated, defensive index: <strong>Erste Bank and Komer&ccaron;n&iacute; banka (~45% weight combined)</strong> and <strong>&Ccaron;EZ (~20% weight)</strong> dominate, giving the index a financials + utilities tilt with a ~5% dividend yield — the highest in CEE. The forward P/E of ~12.0x is a premium to WIG20 (~10.5x) and BUX (~7.2x), justified by the AA- sovereign rating and the earnings stability of the dominant constituents.</p>
      <p>The PX is effectively a <strong>bond proxy with an equity kicker</strong>. Erste and KB trade at P/B of ~1.2x and ~1.5x respectively, with ROEs of ~13-15% — these are well-run, profitable banks in a consolidated market. &Ccaron;EZ, the dominant utility, generates stable cash flows from nuclear and coal generation but faces a structural transition risk as carbon costs rise and renewable investment needs escalate.</p>
    </div>
    <div class="narrative-col">
      <h4>What to Watch</h4>
      <ul>
        <li><strong>Erste Bank CEE exposure</strong> — Erste generates ~50% of revenue outside Czechia (mainly Austria, Romania, Slovakia, Hungary). It's a diversified CEE financials play rather than a pure Czech bet. Watch the Romanian and Hungarian NIM trajectory.</li>
        <li><strong>&Ccaron;EZ nuclear tender</strong> — the government's plan to build a new nuclear reactor (Dukovany II, ~€7bn) is the largest infrastructure project in Czech history. &Ccaron;EZ is the designated developer but the financing structure (government guarantees, PPAs) is unresolved. A favourable resolution would be a significant positive catalyst.</li>
        <li><strong>Dividend sustainability</strong> — PX's ~5% yield is the index's main attraction. Erste and KB have payout ratios of ~50-60%, sustainable from earnings. &Ccaron;EZ's dividend is more volatile (linked to power prices). Monitor for any cut risk if power prices decline further.</li>
      </ul>
    </div>
  </div>
  <div class="narrative-footer">
    <strong>Market Implication:</strong> The PX is a defensive, income-oriented allocation — not a growth bet. Long PX vs short DAX expresses the view that Czech banks will benefit from CNB rate stability while German auto/manufacturing faces structural headwinds. The 5% dividend yield provides a cushion in a sideways market. For growth exposure, look to Poland; for deep value, look to Hungary; for income and safety, Czechia is the destination.
  </div>
</div>""",
    },
    
        "financial_stability": """<div class="narrative">
  <div class="narrative-header"><span class="narrative-label">Macro Narrative</span><span class="narrative-date">April 2026</span></div>
  <div class="narrative-body">
    <div class="narrative-col">
      <h4>What's Happened</h4>
      <p>Czechia's banking sector is <strong>the most conservative and well-funded in CEE</strong>. The aggregate CAR is ~21%, the highest in the region. The <strong>loan-to-deposit ratio at ~68%</strong> means the sector is over-funded — Czech banks are net placers in the interbank market, not net borrowers. The NPL ratio at ~1.8% is the lowest in the EU. Erste Bank (via Ceska sporitelna) and Komercni banka (Societe Generale) form a stable duopoly controlling ~55% of system assets.</p>
      <p>The CNB's aggressive cutting cycle (7.0% → 3.50%) has created <strong>moderate NIM compression</strong> — aggregate NIM has fallen from ~2.8% to ~2.3%. However, the loan book is growing at a modest 3-4% and asset quality is impeccable. <strong>Household debt at ~31% of GDP</strong> is above the CEE average but largely mortgage debt with low LTVs (~55% average). Corporate debt at ~52% of GDP is moderate and concentrated in the export-manufacturing sector.</p>
    </div>
    <div class="narrative-col">
      <h4>What to Watch</h4>
      <ul>
        <li><strong>Housing market re-acceleration</strong> — as mortgage rates fall below 4.5%, Prague property prices are beginning to rise again after a ~10% correction. The CNB's macroprudential toolkit (LTV/DSTI limits) is well-developed and has been used effectively in the past.</li>
        <li><strong>Corporate credit risk from German exposure</strong> — Czech banks' corporate loan books are heavily exposed to the automotive supply chain (~15% of corporate loans). A prolonged German manufacturing recession would increase provisioning needs, currently at cyclical lows.</li>
        <li><strong>Bank tax absence</strong> — unlike Hungary and Poland, Czechia does not have a bank asset tax. This is a structural competitive advantage that supports higher P/B multiples for PX banks vs regional peers.</li>
      </ul>
    </div>
  </div>
  <div class="narrative-footer"><strong>Market Implication:</strong> Czech banks (PX financials at P/B ~1.4x) trade at a premium for good reason — highest CAR, lowest NPLs, no bank tax, self-funded. Defensive allocation for a risk-off environment. The CNB cutting cycle is a mild NIM headwind but volumes are recovering. Long PX banks vs short DAX auto expresses the relative financial stability view.</div>
</div>""",
        "demographics": """<div class="narrative">
  <div class="narrative-header"><span class="narrative-label">Structural Narrative</span><span class="narrative-date">2026 assessment</span></div>
  <div class="narrative-body">
    <div class="narrative-col">
      <h4>What's Happened</h4>
      <p>Czechia has <strong>the tightest labour market in the EU</strong> (unemployment 2.6%) — a reflection not of booming demand but of structural labour scarcity. The working-age population has been declining at ~0.4% annually, and the <strong>old-age dependency ratio at ~34%</strong> is the highest in CEE-4. The median age of 44 ties with Hungary as the highest in the region. The TFR at 1.7 is the highest in CEE but still below replacement.</p>
      <p><strong>Net migration is positive but modest</strong> (~30,000/year), dominated by Slovak and Ukrainian workers. The government's immigration policy is restrictive — Czechia accepted fewer refugees per capita than Poland and has not liberalised non-EU work permits. The labour shortage is the binding constraint on growth: there are ~350,000 unfilled vacancies, concentrated in manufacturing and construction.</p>
    </div>
    <div class="narrative-col">
      <h4>What to Watch</h4>
      <ul>
        <li><strong>Automation vs immigration</strong> — Czechia has the highest robot density in CEE (automation is the corporate response to labour scarcity). This supports productivity but reduces the employment intensity of GDP growth.</li>
        <li><strong>Pension system sustainability</strong> — the pension system is fiscally sound (surplus until ~2035 on current projections) but the demographic trajectory means reform is inevitable. The parametric changes (retirement age indexation to life expectancy) are technically sound but politically fragile.</li>
      </ul>
    </div>
  </div>
  <div class="narrative-footer"><strong>Market Implication:</strong> Czechia's labour scarcity means the NAIRU is higher than headline unemployment suggests — wage growth at 7%+ in a 2.6% unemployment economy is structurally inflationary. This argues for a higher CNB terminal rate than the market prices. Receive CZK front-end rates.</div>
</div>""",
        "political_economy": """<div class="narrative">
  <div class="narrative-header"><span class="narrative-label">Structural Narrative</span><span class="narrative-date">2026 assessment</span></div>
  <div class="narrative-body">
    <div class="narrative-col">
      <h4>What's Happened</h4>
      <p>Czechia has <strong>the highest institutional quality in CEE-4</strong>, reflected in the AA-/Aa3/AA- sovereign rating. WGI scores are the region's best: government effectiveness at ~82nd percentile, rule of law at ~85th, control of corruption at ~80th — all at or above the EU average. The Czech governance model is characterised by a <strong>technocratic, rules-based approach</strong> — the CNB publishes its own interest rate forecast path (unique in CEE), and fiscal policy is constrained by a constitutional debt brake.</p>
      <p>The political landscape is dominated by the <strong>ANO vs SPOLU competition</strong>. ANO (Babis) leads polls for the 2025 parliamentary election with ~33% support. ANO's policy platform is fiscally expansionary (pension hikes, infrastructure spending) and sceptical of EU fiscal rules. A Babis victory would represent a shift toward a more Hungarian-style political economy — not a rule-of-law crisis, but a move away from fiscal conservatism.</p>
    </div>
    <div class="narrative-col">
      <h4>What to Watch</h4>
      <ul>
        <li><strong>2025 parliamentary election</strong> — ANO victory is the base case (polls). The market impact depends on the coalition: ANO + SPD (far-right) would be negative for CZK/CZGBs; ANO + CSSD (centre-left) would be more moderate.</li>
        <li><strong>Fiscal rule commitment</strong> — the constitutional debt brake (60% GDP ceiling) has anchored Czech fiscal policy. ANO has not proposed repealing it but has advocated for "flexible interpretation."</li>
        <li><strong>EU-NATO anchor</strong> — Czechia's institutional quality is underpinned by deep EU integration (exports, supply chains, regulatory alignment). This is a structural constraint against radical policy shifts that markets may underappreciate.</li>
      </ul>
    </div>
  </div>
  <div class="narrative-footer"><strong>Market Implication:</strong> Czechia's institutional quality premium is structural, not cyclical. The AA- rating is secure barring a radical policy shift. The 2025 election is a known risk — if ANO wins with a moderate coalition, the market impact is modest (10-15bp CZGB spread widening). If ANO + SPD, the re-rating risk is 30-50bp. Position for the former, hedge for the latter.</div>
</div>""",
	    "subtitle_zh": "综合国别概览，包含宏观叙事与前瞻性投资定位观点",
    "kpi_html_zh": """<div class="kpi-ribbon">
  <div class="kpi-card">
    <div class="kpi-label">实际GDP（同比）</div>
    <div class="kpi-value">+1.1%</div>
    <div class="kpi-sub"><span class="kpi-delta-down">低于趋势</span> · 2025年Q4</div>
  </div>
  <div class="kpi-card">
    <div class="kpi-label">整体CPI（同比）</div>
    <div class="kpi-value">2.6%</div>
    <div class="kpi-sub">在2.0% ±1pp区间内 · 2025年12月</div>
  </div>
  <div class="kpi-card">
    <div class="kpi-label">财政赤字</div>
    <div class="kpi-value">−2.2%</div>
    <div class="kpi-sub"><span class="kpi-delta-up">中东欧四国最佳</span> · 2025年</div>
  </div>
  <div class="kpi-card">
    <div class="kpi-label">经常账户</div>
    <div class="kpi-value">+2.8%</div>
    <div class="kpi-sub"><span class="kpi-delta-up">强劲盈余</span> · 占GDP 2025年</div>
  </div>
  <div class="kpi-card">
    <div class="kpi-label">政策利率</div>
    <div class="kpi-value">3.50%</div>
    <div class="kpi-sub">实际利率~1.4% · CNB降息周期中</div>
  </div>
  <div class="kpi-card">
    <div class="kpi-label">10年期CZK收益率</div>
    <div class="kpi-value">4.20%</div>
    <div class="kpi-sub">~40bp低于PLN · 2026年4月</div>
  </div>
</div>""",
    "snapshot_prose_zh": """    <div class="snapshot-subsection">
      <h3>经济概况</h3>
      <p>捷克是一个<strong>$3450亿经济体</strong>（2024年名义GDP），人口<strong>1090万</strong>，<strong>人均GDP$31,600为中东欧最高</strong>（按购买力平价调整后高于意大利和西班牙）。该经济体是欧盟内制造业最密集的，集中于<strong>汽车OEM及供应链（斯柯达/大众、现代、丰田）、机械与精密工程、电子产品以及啤酒与饮料</strong>。主要贸易伙伴为<strong>德国、斯洛伐克、波兰、法国和奥地利</strong>——捷克是所有中东欧经济体中融入德国供应链最深的，使其成为德国工业周期的杠杆式押注。</p>
    </div>
    <div class="snapshot-subsection">
      <h3>制度框架</h3>
      <p><strong>捷克国家银行（CNB）</strong>实行<strong>管理浮动</strong>汇率制度，正式通胀目标为<strong>2.0% ±1个百分点</strong>。捷克自2004年起为欧盟和北约成员国，但<strong>非欧元区成员</strong>。主权信用评级为<strong>AA−（标普）/ Aa3（穆迪）/ AA−（惠誉）</strong>——中东欧最高，反映了财政保守主义（债务约43% GDP）、持续的经常账户盈余以及该地区人均资本存量最高。CNB是最透明的中东欧央行，公开发布自身利率预测路径。</p>
    </div>
    <div class="snapshot-subsection">
      <h3>市场准入</h3>
      <p>基准<strong>PX指数</strong>（约1,600点）远期市盈率约12.0倍——相对中东欧同侪溢价，反映捷克AA-评级。PX由银行（Erste、Komerční banka——约45%权重）和公用事业（ČEZ——约20%权重）主导，赋予其防御性、高股息特征。<strong>10年期CZK国债收益率约4.2%</strong>——低于PLN和HGB收益率，符合评级序列。<strong>EURCZK约25.0</strong>（2026年4月）较疫情前均值约25.5贬值约8%，反映CNB激进降息和能源进口的贸易条件拖累。</p>
    </div>""",
    "narratives_zh": {
        "real_activity": """<div class="narrative"><div class="narrative-header"><span class="narrative-label">宏观叙事</span><span class="narrative-date">2026年Q1评估</span></div><div class="narrative-body"><div class="narrative-col"><h4>已发生的变化</h4><p>捷克<strong>陷入浅增长均衡</strong>。2025年Q4实际GDP同比仅+1.1%，为中东欧四国中最弱。经济被自身结构性优势拖累：<strong>制造业约GDP的25%</strong>（欧盟最高），而德国制造业衰退对捷克工业的不成比例打击。工业生产-2.0%反映了汽车供应链——斯柯达/大众一家就占GDP约5%和出口约10%。订单出货比处于2020年以来最低。</p><p>但国内经济比标题数据表现得更有韧性。<strong>失业率2.6%</strong>（欧盟最低）意味着劳动力市场是结构性支撑——任何想要工作的人都有工作。随着通胀正常化，实际工资增长约4%，家庭消费在2025年每个季度均对GDP有正贡献。问题在于投资：企业在德国不确定性和CNB降息周期尚未转化为信贷复苏的背景下推迟资本支出决策。</p></div><div class="narrative-col"><h4>需要关注</h4><ul><li><strong>德国IFO周期</strong>——捷克PMI在过去27个月中有24个月处于50以下。唯一重要的变量是德国制造业订单。IFO预期持续复苏至95以上将是做多捷克资产的信号。</li><li><strong>斯柯达电动车转型</strong>——斯柯达正投资€56亿于电动化（2024-28年），2025-26年将推出三款新电动车型。这些车型的成败将决定捷克未来十年约10%出口的轨迹。</li><li><strong>CNB宽松传导</strong>——CNB已从峰值降息350bp（7.0%→3.5%），但私人信贷增长实际值仍为负。传导滞后表明宽松的增长脉冲最早在2026年下半年才会显现。</li></ul></div></div><div class="narrative-footer"><strong>市场含义：</strong>捷克是对德国工业周期的高贝塔投资。如果德国复苏，CZK和捷克股票在6个月内跑赢中东欧同侪5-8%。如果德国持续停滞，捷克资产跑输。我们将做多CZK对EUR头寸定位于对德国复苏的看涨期权——设定紧止损在EURCZK 25.50。股市方面，做多PX银行（Erste）对做空DAX汽车代表了同一主题的相对价值表达，降低了方向性。</div></div>""",
        "prices_wages": """<div class="narrative"><div class="narrative-header"><span class="narrative-label">宏观叙事</span><span class="narrative-date">2026年4月</span></div><div class="narrative-body"><div class="narrative-col"><h4>已发生的变化</h4><p>捷克在通胀方面实现了<strong>中东欧最软着陆</strong>。整体CPI同比<strong>2.6%</strong>处于CNB 2.0% ±1pp容忍区间内，较2023年初18.0%的峰值显著下降。去通胀堪称教科书：能源基数效应贡献了约70%的降幅，其余30%来自2021-23年加息冲击带来的真实需求压缩。核心CPI 2.3%为中东欧最低。</p><p>CNB自2023年12月以来激进降息，并在2025年5月将2W repo rate降至<strong>3.50%</strong>后维持到2026年5月。但<strong>工资增长同比7.4%</strong>在一个失业率2.6%的经济体中，提出了宽松是否过早的疑问。CNB自身预测认为CPI将在2026年中缓慢降至2.0%，但工资脉冲和封闭的产出缺口表明通胀将更接近2.5-3.0%——在区间内但高于目标中值。</p></div><div class="narrative-col"><h4>需要关注</h4><ul><li><strong>CNB终端利率争论</strong>——当前2W repo rate为3.50%，核心问题是宽松周期是否已经基本结束。服务业通胀3.8%和7%+的工资增长不支持政策利率显著低于当前水平。</li><li><strong>房地产市场再加速</strong>——布拉格房价在加息周期中下跌约10%，随着按揭利率降至4.5%以下已企稳并开始回升。新一轮房地产繁荣将传导至虚拟租金（约占CPI篮子的10%），维持核心CPI高位。</li></ul></div></div><div class="narrative-footer"><strong>市场含义：</strong>CZK利率应被视为接近终端区间。汇率方面，CNB降息周期已将CZK从24.0推弱至25.0——大量坏消息已定价。如果降息周期已经结束，EURCZK可能重定价至24.50。</div></div>""",
        "external": """<div class="narrative"><div class="narrative-header"><span class="narrative-label">宏观叙事</span><span class="narrative-date">2026年4月</span></div><div class="narrative-body"><div class="narrative-col"><h4>已发生的变化</h4><p>捷克拥有<strong>持续经常账户盈余</strong>——2025年为GDP的+2.8%，中东欧四国中最大。这是结构性特征：制造业出口引擎（汽车、机械）产生约GDP+8%的商品顺差，超额抵消了初次收入逆差（外资企业的股息和利润汇回）。仅对德国的贸易顺差（年约€150亿）就约相当于捷克GDP的4%。</p><p>外汇储备<strong>€1400亿</strong>，相对GDP是欧盟最高之一（约GDP的40%），为2013-17年EURCZK下限政策的遗留。CNB一直以负利差（约200bp，融资做空CZK负债对应做多EUR资产）运行这一庞大储备头寸，产生按市值计价波动，但提供了对CZK投机攻击的不可撼动的防御。REER自2023年峰值贬值约5%，恢复了通胀超调期间丧失的竞争力。</p></div><div class="narrative-col"><h4>需要关注</h4><ul><li><strong>储备减持？</strong>——行长Michl已表示有意逐步缩减外汇储备存量。任何CNB外汇抛售（买入EURCZK）将削弱CZK。但实际操作空间有限——市场会将激进抛售视为政策错误。</li><li><strong>汽车出口周期</strong>——捷克汽车出口约GDP的8%。德国汽车注册量下降10%对捷克GDP产生约0.8%的拖累。电动车转型增加结构性不确定性——捷克供应链针对内燃机优化。</li><li><strong>能源依赖</strong>——捷克已在很大程度上摆脱俄罗斯天然气（通过荷兰/德国终端LNG、挪威管道天然气），但仍依赖能源进口。2022-23年能源冲击的贸易条件拖累已基本逆转。</li></ul></div></div><div class="narrative-footer"><strong>市场含义：</strong>经常账户盈余是结构性CZK买盘，但被CNB鸽派立场和外汇储备头寸的负利差所抵消。CZK不是纯粹的利差交易。我们倾向于通过主权信用表达捷克外部实力（基于AA-对BBB-的~300bp利差，做多CZGB对HGB）。CZK是区间交易：25.20买入，24.50卖出。</div></div>""",
        "fiscal_sovereign": """<div class="narrative"><div class="narrative-header"><span class="narrative-label">宏观叙事</span><span class="narrative-date">2026年4月</span></div><div class="narrative-body"><div class="narrative-col"><h4>已发生的变化</h4><p>捷克是<strong>中东欧的财政冠军</strong>。2025年一般政府赤字仅GDP的-2.2%，为中东欧四国中最窄，低于3%的马斯特里赫特参考值。总理Fiala领导下的SPOLU联合政府兑现了财政整顿：通过增税（企业所得税、银行/能源暴利税）和支出约束，赤字从2021年的-5.1%减半。</p><p>总债务<strong>约GDP的43%</strong>为欧盟最低，显著低于马斯特里赫特60%门槛。债务以CZK计价为主（约90%），拥有稳定的国内投资者基础。10年期收益率4.2%意味着仅约40bp低于波兰——鉴于捷克高出两个评级的优势，这一紧窄利差引人注目。紧窄利差部分具有技术性：CZGB市场较POLGB更小、流动性更差，限制了外资参与。</p></div><div class="narrative-col"><h4>需要关注</h4><ul><li><strong>ANO财政政策</strong>——如果ANO赢得2025年议会选举（民调显示很可能），财政政策可能转向扩张。Babiš的政纲细节不足但支出承诺充沛（养老金加薪、基础设施）。市场尚未对此风险定价。</li><li><strong>国防支出提升</strong>——捷克已承诺GDP的2%国防支出（北约目标），高于2023年1.3%。增量约GDP 0.7%的成本从当前财政状况来看可控，但增加结构性赤字。</li></ul></div></div><div class="narrative-footer"><strong>市场含义：</strong>4.2%的CZGB提供中东欧主权信用中最佳的风险调整利差收益。AA-评级、43%债务/GDP和持续经常账户盈余使其成为区域避风港。做多10年期CZGB对做空10年期HGB（约290bp利差）——评级差异（5个档次）相对利差差异尚未完全定价。主要风险是ANO驱动的财政扩张；密切关注选举民调。</div></div>""",
        "monetary_financial": """<div class="narrative"><div class="narrative-header"><span class="narrative-label">宏观叙事</span><span class="narrative-date">2026年4月</span></div><div class="narrative-body"><div class="narrative-col"><h4>已发生的变化</h4><p>CNB是<strong>中东欧最激进降息者</strong>，自2023年12月以来将2W repo rate从7.0%降至<strong>3.50%</strong>，并自2025年5月以来维持不变。降息周期数据依赖且沟通良好——CNB公开发布预测路径（中东欧独有的透明度实践）有效引导了市场预期。</p><p>传导机制正在发挥作用但存在滞后。按揭利率已从约6.5%降至约4.5%，推动试探性住房市场复苏。但<strong>私人信贷增长同比+2.1%</strong>依然乏力——企业不借贷是因为不投资，而非信贷成本高昂。CNB面临经典的推绳子问题：当德国需求缺位时，降息无法强迫企业投资。M3增长5.5%健康但非扩张性。</p></div><div class="narrative-col"><h4>需要关注</h4><ul><li><strong>终端利率着陆区</strong>——当前2W repo rate为3.50%。考虑到劳动力市场紧俏和工资增长，继续显著降息的空间有限。</li><li><strong>汇率传导风险</strong>——降息周期中CZK已从24.0走弱至25.0。进一步走至25.50+（来自企业、能源进口商或CNB储备操作的EURCZK买入）将通过进口价格增加CPI约0.3个百分点。这是降息的自我限制机制。</li><li><strong>CNB vs ECB</strong>——如果CNB进一步降息而ECB维持不变，CZK的利差吸引力减弱，可能进一步削弱CZK。</li></ul></div></div><div class="narrative-footer"><strong>市场含义：</strong>CNB降息周期大概率接近尾声。短端CZK利率需要反映“易降息阶段已经结束”。汇率方面，EURCZK 25.0基于利差接近公允价值。带有鹰派CNB偏向的区间交易。</div></div>""",
        "markets_valuation": """<div class="narrative"><div class="narrative-header"><span class="narrative-label">宏观叙事</span><span class="narrative-date">2026年4月</span></div><div class="narrative-body"><div class="narrative-col"><h4>已发生的变化</h4><p><strong>PX指数约1,600点（同比+3.1%）</strong>在中东欧表现居中——好于BUX（-2.9%）但落后WIG20（+5.4%）。PX是一个集中、防御性指数：<strong>Erste银行和Komerční banka（合计约45%权重）</strong>以及<strong>ČEZ（约20%权重）</strong>占主导，赋予该指数金融+公用事业偏向和约5%的股息率——为中东欧最高。远期市盈率约12.0倍相对WIG20（约10.5倍）和BUX（约7.2倍）溢价，由AA-主权评级和主导成分股的盈利稳定性证明合理。</p><p>PX实际上是一个<strong>带有股权增强的债券替代品</strong>。Erste和KB的市净率分别约1.2倍和1.5倍，ROE约13-15%——这些是在整合市场中运营良好、盈利可观的银行。ČEZ作为主导公用事业，从核能和燃煤发电中产生稳定现金流，但随着碳成本上升和可再生能源投资需求升级，面临结构性转型风险。</p></div><div class="narrative-col"><h4>需要关注</h4><ul><li><strong>Erste银行中东欧敞口</strong>——Erste约50%收入来自捷克境外（主要是奥地利、罗马尼亚、斯洛伐克、匈牙利）。它是多元化中东欧金融投资标的，而非纯粹的捷克押注。关注罗马尼亚和匈牙利的NIM轨迹。</li><li><strong>ČEZ核电招标</strong>——政府新建核反应堆（Dukovany II，约€70亿）是捷克历史上最大的基础设施项目。ČEZ是指定开发商，但融资结构（政府担保、购电协议）尚未解决。有利的解决方案将是重要积极催化剂。</li><li><strong>股息可持续性</strong>——PX约5%的股息率是其主要吸引力。Erste和KB的派息比率约50-60%，可以盈利支撑。ČEZ的股息波动更大（与电力价格挂钩）。关注电价进一步下跌时的削减风险。</li></ul></div></div><div class="narrative-footer"><strong>市场含义：</strong>PX是防御性、收入导向型配置——而非增长押注。做多PX对做空DAX表达了捷克银行将受益于CNB利率稳定，而德国汽车/制造业面临结构性阻力的观点。5%股息率在横盘市场提供缓冲。寻求增长敞口看波兰；深度价值看匈牙利；收入与安全，捷克是目的地。</div></div>""",
    
        "financial_stability": """<div class="narrative">
  <div class="narrative-header"><span class="narrative-label">宏观叙事</span><span class="narrative-date">2026年4月</span></div>
  <div class="narrative-body">
    <div class="narrative-col">
      <h4>已发生的变化</h4>
      <p>捷克银行业是<strong>中东欧最保守、资金最充裕的</strong>。整体CAR约21%，为区域最高。<strong>存贷比约68%</strong>意味着该行业资金过剩——捷克银行是银行间市场的净出借方而非净借款方。不良贷款率约1.8%为欧盟最低。Erste银行（通过Ceska sporitelna）和Komercni banka（法国兴业银行）形成稳定双头垄断，控制系统资产约55%。</p>
      <p>CNB激进降息周期（7.0%→3.50%）造成<strong>温和净息差压缩</strong>——整体NIM从约2.8%降至约2.3%。但贷款账面增长温和（3-4%），资产质量无可挑剔。<strong>居民债务约GDP的31%</strong>高于中东欧均值但主要为按揭贷款，贷款价值比低（约55%）。企业债务约GDP的52%中等，集中于出口制造业。</p>
    </div>
    <div class="narrative-col">
      <h4>需要关注</h4>
      <ul>
        <li><strong>房地产市场再加速</strong>——随着按揭利率降至4.5%以下，布拉格房价在约10%调整后开始回升。CNB的宏观审慎工具包（LTV/DSTI限制）发展完善且已被有效使用。</li>
        <li><strong>德国敞口带来的企业信用风险</strong>——捷克银行企业贷款账面高度集中于汽车供应链（约企业贷款的15%）。德国制造业长期衰退将增加拨备需求。</li>
        <li><strong>无银行税</strong>——与匈牙利和波兰不同，捷克没有银行资产税。这是支持PX银行相对区域同侪更高市净率的结构性竞争优势。</li>
      </ul>
    </div>
  </div>
  <div class="narrative-footer"><strong>市场含义：</strong>捷克银行（PX金融股市净率约1.4倍）溢价交易有充分理由——最高CAR、最低不良贷款、无银行税、自筹资金。避险环境中的防御性配置。CNB降息周期是温和净息差逆风但交易量正在恢复。做多PX银行对做空DAX汽车表达相对金融稳定观点。</div>
</div>""",
        "demographics": """<div class="narrative">
  <div class="narrative-header"><span class="narrative-label">结构性叙事</span><span class="narrative-date">2026年评估</span></div>
  <div class="narrative-body">
    <div class="narrative-col">
      <h4>已发生的变化</h4>
      <p>捷克拥有<strong>欧盟最紧张的劳动力市场</strong>（失业率2.6%）——反映的不是需求繁荣而是结构性劳动力稀缺。劳动年龄人口以年均约0.4%速度下降，<strong>老年抚养比约34%</strong>为中东欧四国最高。中位年龄44岁与匈牙利并列区域最高。总和生育率1.7为中东欧最高但仍低于替代水平。</p>
      <p><strong>净移民为正但温和</strong>（约3万/年），以斯洛伐克和乌克兰工人为主。政府移民政策限制性强——捷克人均接收难民少于波兰，未放宽非欧盟工签。劳动力短缺是增长的约束条件：约35万空缺岗位未填补，集中于制造业和建筑业。</p>
    </div>
    <div class="narrative-col">
      <h4>需要关注</h4>
      <ul>
        <li><strong>自动化 vs 移民</strong>——捷克拥有中东欧最高的机器人密度（自动化是企业应对劳动力稀缺的手段）。这支持生产率但降低GDP增长的就业强度。</li>
        <li><strong>养老金体系可持续性</strong>——养老金体系财政稳健（按当前预测至2035年前盈余），但人口轨迹意味着改革不可避免。</li>
      </ul>
    </div>
  </div>
  <div class="narrative-footer"><strong>市场含义：</strong>捷克的劳动力稀缺意味着NAIRU高于标题失业率所暗示——2.6%失业率经济中7%+的工资增长具有结构性通胀性。这支持CNB终端利率高于市场定价。做多CZK短端利率。</div>
</div>""",
        "political_economy": """<div class="narrative">
  <div class="narrative-header"><span class="narrative-label">结构性叙事</span><span class="narrative-date">2026年评估</span></div>
  <div class="narrative-body">
    <div class="narrative-col">
      <h4>已发生的变化</h4>
      <p>捷克拥有<strong>中东欧四国中最高制度质量</strong>，反映在AA-/Aa3/AA-主权评级上。WGI评分为区域最佳：政府效能约82百分位，法治约85百分位，腐败控制约80百分位——均达到或高于欧盟均值。捷克治理模式以<strong>技术官僚、规则导向</strong>为特征——CNB公开发布自身利率预测路径（中东欧独一无二），财政政策受宪法债务刹车约束。</p>
      <p>政治格局由<strong>ANO vs SPOLU竞争</strong>主导。ANO（Babis）以约33%支持率领先2025年议会选举民调。ANO政策纲领在财政上扩张性（养老金加薪、基础设施支出）并对欧盟财政规则持怀疑态度。Babis胜选将代表向更具匈牙利风格的政治经济转变——不是法治危机，而是从财政保守主义转向。</p>
    </div>
    <div class="narrative-col">
      <h4>需要关注</h4>
      <ul>
        <li><strong>2025年议会选举</strong>——ANO胜选是基准情景（民调）。市场影响取决于联盟：ANO+SPD（极右）对CZK/CZGB将是负面；ANO+CSSD（中左）将更温和。</li>
        <li><strong>财政规则承诺</strong>——宪法债务刹车（60% GDP上限）已锚定捷克财政政策。ANO未提议废除但主张"灵活解释"。</li>
        <li><strong>欧盟-北约锚</strong>——捷克的制度质量由深度欧盟一体化（出口、供应链、监管对齐）支撑。这是约束激进政策转变的结构性限制，市场可能低估。</li>
      </ul>
    </div>
  </div>
  <div class="narrative-footer"><strong>市场含义：</strong>捷克的制度质量溢价是结构性的而非周期性的。除非激进政策转变，AA-评级安全。2025年选举是已知风险——如果ANO以温和联盟胜选，市场影响温和（CZGB利差扩大10-15bp）。如果ANO+SPD，重定价风险为30-50bp。以前者为配置依据，对冲后者。</div>
</div>""",
    },
}

# ═══ ROMANIA ═══
COUNTRY_DATA["RO"] = {
    "name": "Romania",
    "iso": "RON",
    "cb": "BNR",
    "gen_date": "2026-04-26",
    "peers": "HU, PL, CZ",
    "rating": "BBB− / Baa3 / BBB−",
    "fxregime": "Managed Float",
    "inftarget": "2.5% ±1pp CPI",
    "equity_index": "BET",
    "subtitle": "Comprehensive country primer with macro narratives and forward-looking positioning views",
    "kpi_html": """
  <div class="kpi-ribbon">
    <div class="kpi-card">
      <div class="kpi-label">Real GDP (YoY)</div>
      <div class="kpi-value">+2.2%</div>
      <div class="kpi-sub"><span class="kpi-delta-up">Above CEE avg</span> · Q4 2025</div>
    </div>
    <div class="kpi-card warn">
      <div class="kpi-label">Headline CPI (YoY)</div>
      <div class="kpi-value">5.1%</div>
      <div class="kpi-sub">Highest in CEE-4 · Dec 2025</div>
    </div>
    <div class="kpi-card danger">
      <div class="kpi-label">Fiscal Balance</div>
      <div class="kpi-value">−6.3%</div>
      <div class="kpi-sub"><span class="kpi-delta-down">EDP procedure</span> · 2025</div>
    </div>
    <div class="kpi-card danger">
      <div class="kpi-label">Current Account</div>
      <div class="kpi-value">−6.8%</div>
      <div class="kpi-sub"><span class="kpi-delta-down">Twin deficit</span> · of GDP 2025</div>
    </div>
    <div class="kpi-card warn">
      <div class="kpi-label">Policy Rate</div>
      <div class="kpi-value">6.50%</div>
      <div class="kpi-sub">Real rate ~1.4% · BNR on hold</div>
    </div>
    <div class="kpi-card danger">
      <div class="kpi-label">10Y RON Yield</div>
      <div class="kpi-value">7.50%</div>
      <div class="kpi-sub">Highest in EU · Apr 2026</div>
    </div>
  </div>""",
    "snapshot_prose": """
    <div class="snapshot-subsection">
      <h3>Economy</h3>
      <p>Romania is a <strong>$370 bn economy</strong> (2024 nominal GDP) with a population of <strong>19.0 million</strong> and GDP per capita of <strong>$19,500</strong> — the lowest in CEE-4 but converging rapidly (PPP-adjusted ~75% of EU average, up from ~50% in 2010). The industrial base is concentrated in <strong>automotive components &amp; wire harnesses (Dacia/Renault, Ford, Continental), IT services &amp; software outsourcing (fastest-growing tech sector in the EU), oil &amp; gas (OMV Petrom, Black Sea offshore), and agri-food (EU's largest maize and sunflower producer)</strong>. Top trading partners are <strong>Germany, Italy, France, Hungary, and Bulgaria</strong>.</p>
    </div>
    <div class="snapshot-subsection">
      <h3>Institutional Framework</h3>
      <p>The <strong>Banca Na&tcedil;ional&abreve; a Rom&acirc;niei (BNR)</strong> operates a <strong>managed float</strong> (de facto crawl vs EUR) with a formal inflation target of <strong>2.5% &plusmn;1pp</strong>. Romania is an EU and NATO member since 2007 and achieved partial Schengen accession (air/sea) in 2024. Sovereign credit rating stands at <strong>BBB&minus; (S&amp;P) / Baa3 (Moody&rsquo;s) / BBB&minus; (Fitch)</strong> — the lowest in CEE-4, reflecting Romania's <strong>twin deficit vulnerability (fiscal deficit ~6% GDP, current account deficit ~7% GDP)</strong>. Governor Mugur Is&abreve;rescu (since 1990) is the world's longest-serving central bank governor and the institutional anchor of Romanian macro stability.</p>
    </div>
    <div class="snapshot-subsection">
      <h3>Market Access</h3>
      <p>The benchmark <strong>BET index</strong> (~18,000) trades at a forward P/E of ~8.5x — the lowest in CEE-4, with a ~6% dividend yield that reflects the risk premium. The BET is dominated by banks (BT, BRD — ~35% weight), energy (OMV Petrom, Romgaz — ~25% weight), and utilities. The <strong>10-year RON government bond yields ~7.5%</strong> — the highest in the EU — offering ~180bp over HGBs and ~320bp over Bunds. The <strong>EURRON at ~4.97</strong> (April 2026) has been remarkably stable, reflecting the BNR's managed-float regime and the anchoring effect of Governor Is&abreve;rescu's credibility.</p>
    </div>""",
    "narratives": {
        "real_activity": """
<div class="narrative">
  <div class="narrative-header">
    <span class="narrative-label">Macro Narrative</span>
    <span class="narrative-date">Q1 2026 assessment</span>
  </div>
  <div class="narrative-body">
    <div class="narrative-col">
      <h4>What's Happened</h4>
      <p>Romania grew at <strong>+2.2% YoY in 2025</strong> — respectable, above the CEE-4 average, and driven by a <strong>consumption boom</strong> that is both the economy's strength and its vulnerability. Real wage growth of 7%+ (public sector wage hikes of 15%+ in 2024-25, minimum wage increases) is fuelling retail sales (+5.3% YoY) but widening the trade deficit as consumption sucks in imports. Industrial production is flat (+0.5% YoY) — the manufacturing sector is not participating in the consumption boom, which is import-heavy.</p>
      <p>The growth model is <strong>unsustainably tilted toward consumption over investment</strong>. Gross fixed capital formation is only ~22% of GDP (vs ~27% in Czechia and Hungary), held back by weak EU fund absorption (~60% vs 85%+ in Poland) and policy unpredictability. The IT services sector (+12% YoY, ~6% of GDP) is the structural growth star — Romania now has more tech workers per capita than any other EU country — but it's not large enough to offset the twin deficit drag from consumption-led growth.</p>
    </div>
    <div class="narrative-col">
      <h4>What to Watch</h4>
      <ul>
        <li><strong>Fiscal consolidation impact</strong> — the EDP requires deficit reduction of ~0.5% GDP/year. If the government implements consolidation through tax increases (VAT, income tax) rather than spending cuts, the consumption engine stalls. A 1pp VAT hike would add ~1.5pp to CPI and subtract ~0.5pp from GDP.</li>
        <li><strong>EU fund absorption</strong> — Romania has €29bn in RRF + cohesion funds allocated. Absorption capacity, not funding availability, is the binding constraint. The government's administrative reform agenda is critical to unlocking this growth driver.</li>
        <li><strong>Neptune Deep FID</strong> — OMV Petrom's Black Sea gas project (Neptune Deep, ~€4bn investment) is the largest FDI project in Romanian history. Final investment decision is expected mid-2026; a positive FID would transform Romania's energy trade balance and add ~0.5% to GDP during construction.</li>
      </ul>
    </div>
  </div>
  <div class="narrative-footer">
    <strong>Market Implication:</strong> Romania's growth is the most fragile in CEE-4 — high nominal growth masks deep structural imbalances. Long ROMGBs only if you believe the BNR can manage the twin deficit adjustment without a disruptive FX move. We prefer expressing the growth view through equity (BET banks + energy) rather than rates or FX. The consumption story supports retail and bank earnings; the twin deficit risk caps ROMGB duration appetite.
  </div>
</div>""",
        "prices_wages": """
<div class="narrative">
  <div class="narrative-header">
    <span class="narrative-label">Macro Narrative</span>
    <span class="narrative-date">April 2026</span>
  </div>
  <div class="narrative-body">
    <div class="narrative-col">
      <h4>What's Happened</h4>
      <p>Romania has <strong>the worst inflation problem in CEE</strong>. Headline CPI at <strong>5.1% YoY</strong> is the highest in CEE-4, more than double the BNR's 2.5% target midpoint and well outside the ±1pp tolerance band. The inflation is not primarily imported — it's <strong>homegrown and fiscal in origin</strong>. Public sector wage hikes of 15%+ (2024) and 10%+ (2025), combined with 15%+ minimum wage increases and pension indexation of 13%+, have injected massive demand stimulus into an economy already operating near capacity.</p>
      <p>Core CPI at <strong>4.8%</strong> tells the story — this is not about energy base effects (those have fully washed out). It's about services inflation at 7.2%, driven by labour costs in a tight labour market (unemployment ~5.4%, but structural — skills mismatch is severe). The BNR's policy rate at 6.50% gives a real rate of only ~1.4%, which is barely restrictive given the inflation composition. PPI is running at +3.2% YoY — the pipeline is not deflationary as in Hungary or Czechia.</p>
    </div>
    <div class="narrative-col">
      <h4>What to Watch</h4>
      <ul>
        <li><strong>Fiscal-driven inflation</strong> — Romania's inflation is a fiscal phenomenon, not a monetary one. The BNR can hold rates at 6.50% indefinitely, but as long as the government is running a 6%+ deficit fuelled by wage and pension hikes, CPI will stay elevated. Fiscal consolidation is the necessary condition for disinflation, not rate policy.</li>
        <li><strong>Exchange-rate passthrough</strong> — at ~40%, Romania has the highest FX passthrough in CEE. The BNR's managed float (de facto EURRON stability around 4.97) is the inflation anchor. If the leu comes under pressure (from twin deficit financing concerns), the passthrough adds 2pp to CPI for every 5% depreciation.</li>
        <li><strong>2026 wage round</strong> — the government has signalled a smaller public sector increase (~5%) and minimum wage moderation. If delivered, this is the first sign of demand-side disinflation. If not, CPI stays at 5%+ through 2027.</li>
      </ul>
    </div>
  </div>
  <div class="narrative-footer">
    <strong>Market Implication:</strong> Romanian inflation is a short ROMGBs trade masquerading as a rates view. Real yields are barely positive, and the inflation risk premium is underpriced at 7.5% nominal. Pay 2y RON IRS vs receive 2y PLN — the inflation divergence between Romania (fiscal-driven, sticky) and Poland (energy-driven, fading) is not priced. In FX, the BNR's managed float makes EURRON a low-vol carry trade until it isn't — the twin deficit means the tail risk is a 10%+ depreciation, not a gradual move.
  </div>
</div>""",
        "external": """
<div class="narrative">
  <div class="narrative-header">
    <span class="narrative-label">Macro Narrative</span>
    <span class="narrative-date">April 2026</span>
  </div>
  <div class="narrative-body">
    <div class="narrative-col">
      <h4>What's Happened</h4>
      <p>Romania's external position is <strong>the most vulnerable in CEE</strong>. The current account deficit printed at -6.8% of GDP in 2025, the widest in the EU. The deficit is structural: (1) a goods trade deficit of ~-8% GDP, as the consumption boom pulls in imports (electronics, vehicles, consumer goods) while manufacturing exports stagnate; (2) a primary income deficit of ~-2.5% GDP from profit repatriation by foreign-owned firms; partially offset by (3) a services surplus of +2.5% GDP (IT, transport) and (4) remittances from the 4mn-strong diaspora (~€6bn/yr, ~1.2% GDP).</p>
      <p>The financing of the CA deficit is increasingly <strong>dependent on EU transfers and portfolio flows</strong> rather than stable FDI. Net FDI has fallen from ~3% GDP (2016-19) to ~1.5% GDP (2024-25), reflecting policy unpredictability and the perception of a deteriorating business environment. FX reserves at €63bn cover ~4.5 months of imports — adequate but on the low side given the twin deficit structure. The BNR's managed float has kept EURRON remarkably stable at ~4.97, but this stability is purchased at the cost of reserve depletion during risk-off episodes.</p>
    </div>
    <div class="narrative-col">
      <h4>What to Watch</h4>
      <ul>
        <li><strong>External financing gap</strong> — Romania needs to finance a ~€25bn CA deficit annually. If EU fund inflows slow or portfolio investors turn cautious (Romania was downgraded to BBB- by S&P in 2024), the financing gap pressures RON. The BNR would be forced to choose between FX intervention (reserve drawdown) and rate hikes.</li>
        <li><strong>Neptune Deep impact</strong> — if FID is taken in 2026, first gas is expected 2028-29. At peak production (~10 bcm/yr), it would reduce Romania's gas import bill by ~€2bn/yr (~0.5% GDP), a meaningful but not transformative external adjustment.</li>
        <li><strong>Rating agency calendar</strong> — Moody's next review is October 2026. A negative outlook (currently stable at Baa3) would increase Romania's funding costs and potentially trigger EM index exclusion fears. The investment-grade floor is fragile.</li>
      </ul>
    </div>
  </div>
  <div class="narrative-footer">
    <strong>Market Implication:</strong> Romania's external vulnerability is the most under-priced risk in CEE. The BNR's managed float has suppressed EURRON vol to ~3% — absurdly low for a twin-deficit economy with a BBB- rating. Long EURRON vol via 6m strangles (5.00/5.10) is cheap insurance against a balance-of-payments shock. In rates, the CA deficit argues for a higher risk premium on ROMGBs — the 7.5% 10y yield is fair, not cheap.
  </div>
</div>""",
        "fiscal_sovereign": """
<div class="narrative">
  <div class="narrative-header">
    <span class="narrative-label">Macro Narrative</span>
    <span class="narrative-date">April 2026</span>
  </div>
  <div class="narrative-body">
    <div class="narrative-col">
      <h4>What's Happened</h4>
      <p>Romania's fiscal position is <strong>the worst in the EU outside of crisis cases</strong>. The 2025 general government deficit printed at -6.3% of GDP, well above the 3% Maastricht reference and the worst in CEE-4. Romania has been in the Excessive Deficit Procedure (EDP) since 2020 and has missed every fiscal target since. The drivers are structural: (1) a pro-cyclical public wage policy (wages are ~12% of GDP, up from 9% in 2019), (2) pension costs (~10% of GDP) following a 13%+ indexation in 2024, and (3) weak revenue collection — Romania's tax-to-GDP ratio is ~27%, the lowest in the EU (EU average ~41%).</p>
      <p>Gross debt at <strong>~53% of GDP</strong> is moderate relative to the EU average (~83%), but it's rising fast — from 35% in 2019 to 53% in 2025, an 18pp increase in 6 years. The debt stock is roughly 50% RON-denominated and 50% EUR-denominated — the high FX share makes debt dynamics sensitive to RON depreciation. The 10y yield at 7.5% reflects the market's sober assessment: the ~320bp spread over Bunds is the widest in the EU, and the ~180bp spread over HGBs reflects Romania's weaker fiscal fundamentals vs Hungary.</p>
    </div>
    <div class="narrative-col">
      <h4>What to Watch</h4>
      <ul>
        <li><strong>EDP compliance</strong> — the European Commission's spring 2026 assessment will judge Romania's progress on fiscal consolidation. A negative assessment could trigger the suspension of EU cohesion funds (~€3-5bn/yr), which would immediately widen the financing gap and pressure RON.</li>
        <li><strong>Pension reform</strong> — the pension system is the structural fiscal problem. The pension-to-GDP ratio is rising ~0.5pp/yr due to demographics and discretionary indexation. The World Bank and IMF have recommended a shift to a points-based indexation formula; the PSD-PNL coalition has resisted. This is the political economy fault line.</li>
        <li><strong>Election cycle risk</strong> — the 2024-25 elections saw a strong far-right showing (~32%), introducing a new political risk premium. A far-right government (unlikely but not impossible in the next cycle) would struggle to access EU funds, pushing Romania toward a balance-of-payments crisis.</li>
      </ul>
    </div>
  </div>
  <div class="narrative-footer">
    <strong>Market Implication:</strong> Romania is the highest-risk, highest-carry trade in CEE sovereign credit. At 7.5%, the 10y ROMGB offers the highest nominal yield in the EU, but the 320bp Bund spread compensates for genuine crisis risk. This is a trade for specialists — size for a potential 150bp spread widening in a stress scenario. Long ROMGBs vs short HGBs if you believe the BNR/Is&abreve;rescu anchor holds; avoid if you think the twin deficit dynamic is unsustainable. We're neutral — the carry is tempting but the risk of a fiscal-financial spiral (RON depreciation → higher debt/GDP → rating downgrade → capital outflows) is non-trivial.
  </div>
</div>""",
        "monetary_financial": """
<div class="narrative">
  <div class="narrative-header">
    <span class="narrative-label">Macro Narrative</span>
    <span class="narrative-date">April 2026</span>
  </div>
  <div class="narrative-body">
    <div class="narrative-col">
      <h4>What's Happened</h4>
      <p>The BNR has been <strong>the most conservative central bank in CEE</strong> — it hiked to 7.0% (from 1.25%) during 2021-23 and has cut only 50bp to <strong>6.50%</strong>, the highest policy rate in CEE-4. Governor Mugur Is&abreve;rescu's institutional DNA (he managed Romania's 1990s hyperinflation stabilisation) shapes the BNR's hawkish bias. With CPI at 5.1%, the real policy rate is only ~1.4% — barely restrictive. The BNR's own analysis suggests the neutral rate is 4.0-4.5% nominal, implying the current stance is only moderately tight.</p>
      <p>The transmission mechanism is partially impaired by the <strong>managed float</strong>. The BNR's FX management keeps EURRON at ~4.97, suppressing the exchange-rate channel of monetary transmission. This forces the BNR to rely more heavily on the credit channel, which is weakened by: (1) high financial euroisation (~35% of bank deposits and ~30% of loans are EUR-denominated), (2) a relatively shallow capital market, and (3) state-owned banks (~15% of system assets) that are less responsive to the policy rate. Private credit growth at +6.1% YoY is the highest in CEE — the consumption boom is being financed.</p>
    </div>
    <div class="narrative-col">
      <h4>What to Watch</h4>
      <ul>
        <li><strong>BNR cutting cycle</strong> — the market prices a first 25bp cut in Q3 2026. We think this is too optimistic — the BNR won't cut with CPI above 4.5% and a 6%+ fiscal deficit. First cut in Q1 2027 is more realistic, and only if fiscal consolidation is delivered.</li>
        <li><strong>Is&abreve;rescu succession</strong> — the Governor's term runs to 2029 (he will be 80). His eventual departure is the single largest institutional risk for Romanian macro stability. The succession process (Parliament appoints) will be highly politicised. Markets will react negatively to any candidate perceived as insufficiently hawkish or politically pliant.</li>
        <li><strong>Euroisation risk</strong> — the high share of EUR-denominated credit means the BNR's policy rate has less traction on ~30% of the credit stock. It also means RON depreciation directly increases debt-service burdens for unhedged EUR borrowers — a financial-stability constraint on FX flexibility.</li>
      </ul>
    </div>
  </div>
  <div class="narrative-footer">
    <strong>Market Implication:</strong> The BNR's hawkish hold supports RON carry trades (long RON vs EUR earns ~325bp annualised at current rates). But this is a classic carry trade — the risk is a 10% FX move that wipes out 3 years of carry in a month. The BNR's managed float reduces the probability of this tail event but doesn't eliminate it. We prefer expressing the BNR view through the front end: receive 2y RON FRA to capture the delayed cutting cycle without the FX risk. EURRON vol is too cheap relative to the fundamental tail risk — long 6m EURRON strangles are a positive-carry hedge.
  </div>
</div>""",
        "markets_valuation": """
<div class="narrative">
  <div class="narrative-header">
    <span class="narrative-label">Macro Narrative</span>
    <span class="narrative-date">April 2026</span>
  </div>
  <div class="narrative-body">
    <div class="narrative-col">
      <h4>What's Happened</h4>
      <p>The <strong>BET index at ~18,000 (+8.2% YoY)</strong> has been the best-performing CEE equity benchmark, driven by: (1) bank earnings benefiting from the consumption boom and high nominal rates (BT, BRD — combined ~35% of index, ROEs of 18-22%), (2) energy sector re-rating (OMV Petrom, Romgaz — ~25% weight) on higher oil/gas prices and Neptune Deep optionality, and (3) the ~6% dividend yield attracting income-seeking flows in a low-rate DM world. The forward P/E of ~8.5x is the lowest in CEE — a 40% discount to WIG20.</p>
      <p>But the discount is not irrational. It reflects: (1) the twin deficit macro risk — in a balance-of-payments stress, the BET would be the first CEE equity market to sell off, (2) low free float and liquidity (~€30bn total market cap, ~35% free float, daily turnover ~€10-15mn), and (3) corporate governance concerns at state-owned enterprises. The BET is a high-beta, high-risk, high-return proposition — it works in a constructive EM risk environment and gets crushed in risk-off.</p>
    </div>
    <div class="narrative-col">
      <h4>What to Watch</h4>
      <ul>
        <li><strong>Banca Transilvania (TLV) — the growth story</strong> — TLV is Romania's largest bank (~20% market share), trading at P/B ~2.2x with ROE ~22%. It has been consolidating the Romanian banking market through acquisitions (OTP Romania, Idea Bank). If Romania achieves a soft landing on the twin deficits, TLV is the primary equity beneficiary.</li>
        <li><strong>OMV Petrom & Neptune Deep</strong> — Petrom (~8% BET weight) is a binary option on the Neptune Deep FID. If the project proceeds (mid-2026 decision), Petrom's production profile doubles by 2030 and the stock re-rates 30-40%. If it's delayed/cancelled, the stock trades as a declining E&P company.</li>
        <li><strong>EM index upgrade?</strong> — FTSE Russell currently classifies Romania as a Frontier Market. An upgrade to Secondary Emerging Market status (possible by 2028 if market depth and corporate governance improve) would trigger ~$500mn of passive inflows — significant for a ~€30bn market.</li>
      </ul>
    </div>
  </div>
  <div class="narrative-footer">
    <strong>Market Implication:</strong> The BET is the highest-conviction long in CEE equities IF you can tolerate the twin deficit tail risk. Long BET banks (TLV) vs short HGB banks (OTP) captures the consumption-growth divergence while hedging the fiscal risk (OTP benefits from HUF weakness, TLV from RON stability). The 6% dividend yield provides a cushion. Position size: this is a 1-2% of NAV trade — the twin deficit makes it structurally higher-risk than WIG20 or PX. For the cautious, long ROMGBs at 7.5% with a tight stop offers similar carry with less convexity.
  </div>
</div>""",
    },
    
        "financial_stability": """<div class="narrative">
  <div class="narrative-header"><span class="narrative-label">Macro Narrative</span><span class="narrative-date">April 2026</span></div>
  <div class="narrative-body">
    <div class="narrative-col">
      <h4>What's Happened</h4>
      <p>Romania's banking sector is <strong>profitable but carries the highest macro risk in CEE</strong>. The aggregate CAR is 21% — high, reflecting conservative regulation by the BNR. The NPL ratio has improved dramatically from ~22% (2014) to ~4.9% (2025), driven by loan book cleaning and write-offs post the 2008-12 crisis. However, <strong>asset quality is pro-cyclical</strong> — the consumption boom is driving credit growth at 6%+ annually, and NPLs typically lag the cycle by 2-3 quarters.</p>
      <p>The banking sector is <strong>foreign-owned but domestically-funded</strong> — Erste (via BCR), UniCredit, and Intesa together control ~40% of system assets, but the loan-to-deposit ratio at ~75% means the sector is self-funded. Banca Transilvania (TLV, ~20% market share) is the largest domestically-owned bank and the BET's largest constituent, trading at P/B ~2.2x with ROE ~22% — the premium reflects its acquisition-driven growth and dominant market position.</p>
    </div>
    <div class="narrative-col">
      <h4>What to Watch</h4>
      <ul>
        <li><strong>Unhedged EUR lending</strong> — ~30% of private sector loans are EUR-denominated. RON depreciation directly increases credit risk for unhedged borrowers. The BNR's managed float suppresses this risk but doesn't eliminate it.</li>
        <li><strong>NPL cycle turning?</strong> — NPLs are at cyclical lows. The twin deficit adjustment (fiscal consolidation + external demand slowdown) will increase NPLs from current levels. The BNR's FSR estimates a 200bp NPL increase under a moderate stress scenario.</li>
        <li><strong>Consumer protection legislation</strong> — the government has introduced caps on interest rates for consumer loans and mortgage subsidies. These are credit-negative for banks' NIM and introduce political risk into lending decisions.</li>
      </ul>
    </div>
  </div>
  <div class="narrative-footer"><strong>Market Implication:</strong> Romanian banks (TLV, BRD) offer the highest ROE in CEE but carry the highest macro risk. Long TLV is a high-conviction trade IF the twin deficit adjustment is orderly. The 6% dividend yield provides a cushion. Position size for a 20% drawdown — the twin deficit makes this structurally riskier than Polish or Czech banks.</div>
</div>""",
        "demographics": """<div class="narrative">
  <div class="narrative-header"><span class="narrative-label">Structural Narrative</span><span class="narrative-date">2026 assessment</span></div>
  <div class="narrative-body">
    <div class="narrative-col">
      <h4>What's Happened</h4>
      <p>Romania has <strong>the most complex demographic picture in CEE-4</strong>. The population of 19mn has been declining at ~0.5% annually, but this headline masks a massive <strong>diaspora effect</strong> — an estimated 4mn Romanians live abroad (~17% of the population), the largest diaspora share in the EU. Remittances (~€6bn/year, 1.2% GDP) are a structural current account support. The working-age population share at ~67% is elevated — the demographic dividend is peaking now and will decline as the large 1980s birth cohorts enter retirement.</p>
      <p>The <strong>old-age dependency ratio at ~28%</strong> is the lowest in CEE-4 (for now), but it's projected to rise fastest — from 28% to 40%+ by 2040. The TFR at 1.6 is slightly above the CEE average. The key structural weakness is <strong>emigration of skilled workers</strong> — Romania's IT sector employs ~200,000 workers but faces acute labour shortage as Western European firms recruit Romanian developers at 3-4x local salaries.</p>
    </div>
    <div class="narrative-col">
      <h4>What to Watch</h4>
      <ul>
        <li><strong>Pension reform</strong> — the pension system (Pillar II partially funded) is the most reformed in CEE but the 13%+ indexation in 2024 was fiscally irresponsible. The World Bank recommends switching to a points-based formula.</li>
        <li><strong>Return migration potential</strong> — if Romanian wages converge toward the EU average (currently ~75% PPP-adjusted), the diaspora represents a potential labour supply reservoir. IT workers returning from London/Berlin would be transformative for the tech sector.</li>
      </ul>
    </div>
  </div>
  <div class="narrative-footer"><strong>Market Implication:</strong> Romania's demographic dividend is peaking — the next decade is the window to lock in convergence before aging costs accelerate. The diaspora's remittance flow (~€6bn/year) is a structural current account support that rating agencies underappreciate. This partially offsets the twin deficit risk for ROMGBs.</div>
</div>""",
        "political_economy": """<div class="narrative">
  <div class="narrative-header"><span class="narrative-label">Structural Narrative</span><span class="narrative-date">2026 assessment</span></div>
  <div class="narrative-body">
    <div class="narrative-col">
      <h4>What's Happened</h4>
      <p>Romania has <strong>the weakest institutional quality in CEE-4</strong>, reflected in the BBB-/Baa3/BBB- sovereign rating. WGI scores are the region's lowest: government effectiveness at ~55th percentile, rule of law at ~60th, control of corruption at ~58th — all 10-20 percentiles below the CEE-4 average. The 2024-25 election cycle produced the strongest far-right showing in CEE (~32%), introducing a new political risk premium.</p>
      <p>The institutional anchor is <strong>BNR Governor Mugur Isarescu</strong> (since 1990, world's longest-serving central bank governor). His credibility has maintained the managed EURRON float at ~4.97 through multiple political cycles. His eventual succession (term to 2029, he will be 80) is the single largest institutional risk for Romanian macro stability. Fiscal profligacy (deficit -6.3% GDP, EDP since 2020) reflects weak political commitment to consolidation — every government since 2016 has missed its fiscal targets.</p>
    </div>
    <div class="narrative-col">
      <h4>What to Watch</h4>
      <ul>
        <li><strong>EDP compliance</strong> — the European Commission's spring 2026 assessment is critical. Non-compliance could trigger suspension of EU cohesion funds (~€3-5bn/year), immediately widening the financing gap.</li>
        <li><strong>Isarescu succession (2029)</strong> — the appointment process will be highly politicised. Markets will react negatively to any candidate perceived as insufficiently hawkish or politically pliant.</li>
        <li><strong>Far-right normalisation</strong> — the AUR's ~32% showing in 2024-25 elections is a structural political risk. If AUR enters government in the next cycle, EU funds access would be at risk and the sovereign rating could fall to junk.</li>
      </ul>
    </div>
  </div>
  <div class="narrative-footer"><strong>Market Implication:</strong> Romania's institutional weakness is the primary reason for the 7.5% 10Y yield — the highest in the EU. The Isarescu anchor and EU membership provide a floor under institutional quality, but the floor is not as solid as in Czechia or Poland. ROMGBs at 7.5% compensate for genuine political risk. Size positions for a potential 150bp widening in a political stress scenario.</div>
</div>""",
	    "subtitle_zh": "综合国别概览，包含宏观叙事与前瞻性投资定位观点",
    "kpi_html_zh": """<div class="kpi-ribbon">
  <div class="kpi-card">
    <div class="kpi-label">实际GDP（同比）</div>
    <div class="kpi-value">+2.2%</div>
    <div class="kpi-sub"><span class="kpi-delta-up">高于中东欧均值</span> · 2025年Q4</div>
  </div>
  <div class="kpi-card warn">
    <div class="kpi-label">整体CPI（同比）</div>
    <div class="kpi-value">5.1%</div>
    <div class="kpi-sub">中东欧四国最高 · 2025年12月</div>
  </div>
  <div class="kpi-card danger">
    <div class="kpi-label">财政赤字</div>
    <div class="kpi-value">−6.3%</div>
    <div class="kpi-sub"><span class="kpi-delta-down">过度赤字程序</span> · 2025年</div>
  </div>
  <div class="kpi-card danger">
    <div class="kpi-label">经常账户</div>
    <div class="kpi-value">−6.8%</div>
    <div class="kpi-sub"><span class="kpi-delta-down">双赤字</span> · 占GDP 2025年</div>
  </div>
  <div class="kpi-card warn">
    <div class="kpi-label">政策利率</div>
    <div class="kpi-value">6.50%</div>
    <div class="kpi-sub">实际利率~1.4% · BNR暂缓降息</div>
  </div>
  <div class="kpi-card danger">
    <div class="kpi-label">10年期RON收益率</div>
    <div class="kpi-value">7.50%</div>
    <div class="kpi-sub">欧盟最高 · 2026年4月</div>
  </div>
</div>""",
    "snapshot_prose_zh": """    <div class="snapshot-subsection">
      <h3>经济概况</h3>
      <p>罗马尼亚是一个<strong>$3700亿经济体</strong>（2024年名义GDP），人口<strong>1900万</strong>，人均GDP<strong>$19,500</strong>。产业基础集中于<strong>汽车零部件及线束（Dacia/Renault、Ford、Continental）、IT服务与软件外包、石油与天然气（OMV Petrom、黑海海上），以及农业食品</strong>。主要贸易伙伴为<strong>德国、意大利、法国、匈牙利和保加利亚</strong>。</p>
    </div>
    <div class="snapshot-subsection">
      <h3>制度框架</h3>
      <p><strong>罗马尼亚国家银行（BNR）</strong>实行<strong>管理浮动</strong>汇率制度，正式通胀目标为<strong>2.5% ±1个百分点</strong>。主权信用评级为<strong>BBB−（标普）/ Baa3（穆迪）/ BBB−（惠誉）</strong>。行长Mugur Isarescu（自1990年起任职）是世界上任期最长的央行行长，也是罗马尼亚宏观稳定的制度锚。</p>
    </div>
    <div class="snapshot-subsection">
      <h3>市场准入</h3>
      <p>基准<strong>BET指数</strong>远期市盈率约8.5倍——中东欧四国中最低，约6%的股息率。<strong>10年期RON国债收益率约7.5%</strong>——欧盟最高。<strong>EURRON约4.97</strong>（2026年4月）一直非常稳定，反映了BNR的管理浮动体制和行长信誉的锚定效应。</p>
    </div>""",
    "narratives_zh": {
        "real_activity": """<div class="narrative"><div class="narrative-header"><span class="narrative-label">宏观叙事</span><span class="narrative-date">2026年Q1评估</span></div><div class="narrative-body"><div class="narrative-col"><h4>已发生的变化</h4><p>罗马尼亚2025年<strong>增长+2.2%</strong>——高于中东欧四国均值，并由<strong>消费繁荣</strong>驱动，这既是优势也是脆弱性。实际工资增长7%+推动零售销售（+5.3%），但因消费吸纳进口而扩大贸易逆差。工业生产持平（+0.5%）——制造业并未参与消费繁荣。</p><p>增长模式<strong>不可持续地偏向消费而非投资</strong>。固定资本形成仅约GDP的22%，受制于欧盟资金吸收率低和政策不可预测性。IT服务行业（+12%，约GDP的6%）是结构性增长明星，但规模不足以抵消消费主导增长带来的双赤字拖累。</p></div><div class="narrative-col"><h4>需要关注</h4><ul><li><strong>财政整顿影响</strong>——EDP要求年均赤字削减约GDP的0.5%。如果通过增税实施，消费引擎将熄火。增值税上调1个百分点将增加CPI约1.5个百分点并削减GDP约0.5个百分点。</li><li><strong>欧盟资金吸收</strong>——罗马尼亚分配了€290亿复苏基金。吸收能力而非资金可得性是约束条件。</li><li><strong>Neptune Deep最终投资决定</strong>——OMV Petrom的黑海天然气项目（约€40亿投资）是罗马尼亚历史上最大的FDI项目。积极决定将改变能源贸易差额并在建设期间增加约0.5% GDP。</li></ul></div></div><div class="narrative-footer"><strong>市场含义：</strong>罗马尼亚的增长是中东欧四国中最脆弱的。我们倾向于通过股票（BET银行+能源）而非利率或汇率表达增长观点。消费故事支撑零售和银行盈利；双赤字风险限制ROMGB久期偏好。</div></div>""",
        "prices_wages": """<div class="narrative"><div class="narrative-header"><span class="narrative-label">宏观叙事</span><span class="narrative-date">2026年4月</span></div><div class="narrative-body"><div class="narrative-col"><h4>已发生的变化</h4><p>罗马尼亚拥有<strong>中东欧最严重的通胀问题</strong>。整体CPI<strong>5.1%</strong>是中东欧四国中最高，比BNR 2.5%目标中值高出一倍多。该通胀是<strong>本土产生且源于财政</strong>——公共部门加薪15%+、最低工资增长和养老金指数化，向接近产能运行的经济注入了巨大需求刺激。</p><p>核心CPI<strong>4.8%</strong>说明问题——服务业通胀7.2%，由劳动力成本驱动。BNR 6.50%的政策利率给出的实际利率仅约1.4%——几乎不具紧缩性。PPI同比+3.2%——传导链并非如匈牙利或捷克那样通缩。</p></div><div class="narrative-col"><h4>需要关注</h4><ul><li><strong>财政驱动型通胀</strong>——罗马尼亚的通胀是财政现象而非货币现象。只要政府运行6%+赤字，CPI将维持高位。财政整顿是实现去通胀的必要条件。</li><li><strong>汇率传导</strong>——约40%的外汇传导率为中东欧最高。BNR的管理浮动（EURRON约4.97）是通胀锚。每贬值5%增加CPI 2个百分点。</li><li><strong>2026年工资谈判</strong>——政府已暗示较小涨幅。如果兑现，是首次需求侧去通胀信号。</li></ul></div></div><div class="narrative-footer"><strong>市场含义：</strong>罗马尼亚通胀是做空ROMGB交易。实际收益率仅勉强为正。做多2年期RON IRS对做多2年期PLN表达通胀分化。EURRON波动率被压制，做多跨式期权是廉价保险。</div></div>""",
        "external": """<div class="narrative"><div class="narrative-header"><span class="narrative-label">宏观叙事</span><span class="narrative-date">2026年4月</span></div><div class="narrative-body"><div class="narrative-col"><h4>已发生的变化</h4><p>罗马尼亚的对外部门是<strong>中东欧最脆弱的</strong>。经常账户赤字2025年为GDP的-6.8%，为欧盟最宽。赤字是结构性的：商品贸易逆差约-8% GDP，因消费繁荣吸纳进口而制造业出口停滞。净FDI从约3% GDP下降至约1.5% GDP。外汇储备€630亿覆盖约4.5个月进口。</p><p>经常账户赤字的融资越来越依赖欧盟转移支付和证券投资流入而非稳定FDI。BNR的管理浮动使EURRON在约4.97保持稳定，但这种稳定以消耗储备为代价。</p></div><div class="narrative-col"><h4>需要关注</h4><ul><li><strong>外部融资缺口</strong>——罗马尼亚每年需融资约€250亿经常账户赤字。融资缺口施压RON。</li><li><strong>Neptune Deep影响</strong>——积极最终投资决定将减少天然气进口账单约€20亿/年（约GDP 0.5%）。</li><li><strong>评级机构日历</strong>——穆迪下次审查为2026年10月。投资级底线脆弱。</li></ul></div></div><div class="narrative-footer"><strong>市场含义：</strong>罗马尼亚的外部脆弱性是中东欧定价最不充分的风险。通过6个月跨式期权做多EURRON波动率是廉价保险。经常账户赤字意味着ROMGB应享有更高风险溢价。</div></div>""",
        "fiscal_sovereign": """<div class="narrative"><div class="narrative-header"><span class="narrative-label">宏观叙事</span><span class="narrative-date">2026年4月</span></div><div class="narrative-body"><div class="narrative-col"><h4>已发生的变化</h4><p>罗马尼亚的财政状况是<strong>除危机案例外欧盟最差的</strong>。2025年赤字为GDP的-6.3%，为中东欧四国中最差。罗马尼亚自2020年以来一直处于EDP中，且错失了每个财政目标。驱动因素是结构性的：顺周期公共工资政策、养老金成本、税收征管薄弱（税收对GDP比率约27%，欧盟最低）。</p><p>总债务约GDP的53%相对温和但上升迅速——从2019年35%升至2025年53%。债务存量约50%为EUR计价——高外汇占比使债务动态对RON贬值敏感。10年期收益率7.5%的约320bp Bund利差为欧盟最宽。</p></div><div class="narrative-col"><h4>需要关注</h4><ul><li><strong>EDP合规</strong>——负面评估可能触发暂停欧盟凝聚基金（约€30-50亿/年）。</li><li><strong>养老金改革</strong>——养老金体系是结构性财政问题。世行和IMF建议转向积分式指数化。</li><li><strong>选举周期风险</strong>——极右翼强劲表现引入新的政治风险溢价。</li></ul></div></div><div class="narrative-footer"><strong>市场含义：</strong>罗马尼亚是中东欧主权信用中最高风险、最高利差收益的交易。7.5%的10年期ROMGB提供欧盟最高名义收益率，但320bp Bund利差补偿了危机风险。如果你相信BNR锚定能维持，做多ROMGB对做空HGB。我们中性——财政-金融螺旋的风险不可忽视。</div></div>""",
        "monetary_financial": """<div class="narrative"><div class="narrative-header"><span class="narrative-label">宏观叙事</span><span class="narrative-date">2026年4月</span></div><div class="narrative-body"><div class="narrative-col"><h4>已发生的变化</h4><p>BNR是<strong>中东欧最保守的央行</strong>——将利率从1.25%加至7.0%，并仅降息50bp至<strong>6.50%</strong>，为中东欧四国最高。行长Mugur Isarescu的制度基因塑造了BNR的鹰派偏向。CPI为5.1%，实际政策利率仅约1.4%——几乎不具紧缩性。</p><p>传导机制被管理浮动部分削弱，加上高金融欧元化（约35%银行存款以EUR计价）和国有银行影响。私人信贷增长同比+6.1%为中东欧最高——消费繁荣正在被融资。</p></div><div class="narrative-col"><h4>需要关注</h4><ul><li><strong>BNR降息周期</strong>——市场定价2026年Q3首次降息。我们认为2027年Q1更现实。</li><li><strong>Isarescu继任</strong>——他最终离任是罗马尼亚宏观稳定的最大制度风险。</li><li><strong>欧元化风险</strong>——RON贬值直接增加未对冲EUR借款人的偿债负担。</li></ul></div></div><div class="narrative-footer"><strong>市场含义：</strong>BNR鹰派维持支撑RON套利交易（年化约325bp）。我们倾向于通过短端表达观点：做多2年期RON FRA以捕捉延迟的降息周期。EURRON波动率过于便宜——做多6个月跨式期权是正利差对冲。</div></div>""",
        "markets_valuation": """<div class="narrative"><div class="narrative-header"><span class="narrative-label">宏观叙事</span><span class="narrative-date">2026年4月</span></div><div class="narrative-body"><div class="narrative-col"><h4>已发生的变化</h4><p><strong>BET指数约18,000点（同比+8.2%）</strong>是表现最佳的中东欧股票基准，驱动因素：银行盈利受益于消费繁荣和高名义利率（ROE为18-22%），能源板块重估（Neptune Deep期权性），以及约6%股息率。远期市盈率约8.5倍为中东欧最低——相对WIG20折价40%。</p><p>但折价反映双赤字宏观风险、低流动性和国有企业治理担忧。BET是高贝塔、高风险、高回报命题。</p></div><div class="narrative-col"><h4>需要关注</h4><ul><li><strong>Banca Transilvania（TLV）</strong>——罗马尼亚最大银行，ROE约22%。如果实现软着陆，是主要受益者。</li><li><strong>OMV Petrom与Neptune Deep</strong>——二元期权。如果项目推进，产量到2030年翻倍，股价重估30-40%。</li><li><strong>新兴市场指数升级</strong>——升级至二级新兴市场地位将触发约$5亿被动流入。</li></ul></div></div><div class="narrative-footer"><strong>市场含义：</strong>如果你能承受双赤字尾部风险，BET是中东欧股票中最高确信度的做多。做多BET银行（TLV）对做空HGB银行（OTP）捕捉消费增长分化。头寸规模：NAV的1-2%。对于谨慎者，7.5%的ROMGB做多并设紧止损。</div></div>""",
    
        "financial_stability": """<div class="narrative">
  <div class="narrative-header"><span class="narrative-label">宏观叙事</span><span class="narrative-date">2026年4月</span></div>
  <div class="narrative-body">
    <div class="narrative-col">
      <h4>已发生的变化</h4>
      <p>罗马尼亚银行业<strong>盈利但承载中东欧最高宏观风险</strong>。整体CAR为21%——高位，反映BNR的保守监管。不良贷款率从约22%（2014年）显著改善至约4.9%（2025年），由贷款清理和2008-12危机后核销推动。然而<strong>资产质量是顺周期的</strong>——消费繁荣正推动信贷增长6%+，不良贷款通常滞后周期2-3个季度。</p>
      <p>银行业<strong>外资所有但国内融资</strong>——Erste（通过BCR）、UniCredit和Intesa合计控制系统资产约40%，但存贷比约75%意味着该行业自筹资金。Banca Transilvania（TLV，约20%市场份额）是最大国内银行和BET最大成分股，市净率约2.2倍，ROE约22%——溢价反映其收购驱动增长和主导市场地位。</p>
    </div>
    <div class="narrative-col">
      <h4>需要关注</h4>
      <ul>
        <li><strong>未对冲欧元贷款</strong>——约30%私人部门贷款以欧元计价。RON贬值直接增加未对冲借款人的信用风险。BNR的管理浮动抑制但未消除此风险。</li>
        <li><strong>不良贷款周期转向？</strong>——不良贷款处于周期低点。双赤字调整（财政整顿+外部需求放缓）将从当前水平增加不良贷款。BNR金融稳定报告估计中等压力情景下不良贷款上升200bp。</li>
        <li><strong>消费者保护立法</strong>——政府已引入消费贷款利率上限和按揭补贴。这对银行净息差不利并在贷款决策中引入政治风险。</li>
      </ul>
    </div>
  </div>
  <div class="narrative-footer"><strong>市场含义：</strong>罗马尼亚银行（TLV、BRD）提供中东欧最高ROE但承载最高宏观风险。如果双赤字调整有序，做多TLV是高确信度交易。6%股息率提供缓冲。按20%回撤管理头寸——双赤字使其结构性风险高于波兰或捷克银行。</div>
</div>""",
        "demographics": """<div class="narrative">
  <div class="narrative-header"><span class="narrative-label">结构性叙事</span><span class="narrative-date">2026年评估</span></div>
  <div class="narrative-body">
    <div class="narrative-col">
      <h4>已发生的变化</h4>
      <p>罗马尼亚拥有<strong>中东欧四国中最复杂的人口图景</strong>。1900万人口以年均约0.5%速度下降，但此标题掩盖了巨大的<strong>侨民效应</strong>——估计400万罗马尼亚人居住在国外（约人口的17%），为欧盟最大侨民占比。汇款（约€60亿/年，GDP的1.2%）是结构性经常账户支撑。劳动年龄人口占比约67%处于高位——人口红利正在见顶，将随1980年代大型出生队列进入退休而下降。</p>
      <p><strong>老年抚养比约28%</strong>目前为中东欧四国最低，但预计上升最快——从28%到2040年40%+。总和生育率1.6略高于中东欧均值。关键结构性弱点是<strong>技术工人移民</strong>——罗马尼亚IT行业雇用约20万工人，但因西欧公司以3-4倍本地工资招聘罗马尼亚开发者而面临严重劳动力短缺。</p>
    </div>
    <div class="narrative-col">
      <h4>需要关注</h4>
      <ul>
        <li><strong>养老金改革</strong>——养老金体系（第二支柱部分积累制）是中东欧改革最彻底的，但2024年13%+指数化在财政上不负责任。世行建议转向积分制公式。</li>
        <li><strong>回流潜力</strong>——如果罗马尼亚工资向欧盟均值收敛（目前PPP调整后约75%），侨民代表潜在劳动力供给储备。IT工作者从伦敦/柏林回流将变革科技行业。</li>
      </ul>
    </div>
  </div>
  <div class="narrative-footer"><strong>市场含义：</strong>罗马尼亚的人口红利正在见顶——未来十年是锁定收敛的关键窗口，之后老龄化成本加速。侨民汇款（约€60亿/年）是评级机构低估的结构性经常账户支撑。部分抵消ROMGB的双赤字风险。</div>
</div>""",
        "political_economy": """<div class="narrative">
  <div class="narrative-header"><span class="narrative-label">结构性叙事</span><span class="narrative-date">2026年评估</span></div>
  <div class="narrative-body">
    <div class="narrative-col">
      <h4>已发生的变化</h4>
      <p>罗马尼亚拥有<strong>中东欧四国中最弱的制度质量</strong>，反映在BBB-/Baa3/BBB-主权评级上。WGI评分为区域最低：政府效能约55百分位，法治约60百分位，腐败控制约58百分位——均低于中东欧四国均值10-20个百分点。2024-25年选举周期产生了中东欧最强劲的极右翼表现（约32%），引入新的政治风险溢价。</p>
      <p>制度锚是<strong>BNR行长Mugur Isarescu</strong>（自1990年起任职，世界任期最长央行行长）。他的信誉在多个政治周期中维持了管理浮动的EURRON约4.97。他的最终继任（任期至2029年，他将80岁）是罗马尼亚宏观稳定的最大单一制度风险。财政挥霍（赤字-6.3% GDP，2020年以来处于EDP）反映了对整顿的政治承诺薄弱——2016年以来每届政府均错失财政目标。</p>
    </div>
    <div class="narrative-col">
      <h4>需要关注</h4>
      <ul>
        <li><strong>EDP合规</strong>——欧盟委员会2026年春季评估至关重要。不合规可能触发暂停欧盟凝聚基金（约€30-50亿/年），立即扩大融资缺口。</li>
        <li><strong>Isarescu继任（2029年）</strong>——任命过程将高度政治化。市场将对任何被认为不够鹰派或政治上柔顺的候选人作出负面反应。</li>
        <li><strong>极右翼常态化</strong>——AUR在2024-25年选举中约32%的表现是结构性政治风险。如果AUR进入下届政府，欧盟资金获取将面临风险，主权评级可能降至垃圾级。</li>
      </ul>
    </div>
  </div>
  <div class="narrative-footer"><strong>市场含义：</strong>罗马尼亚的制度弱点是10年期7.5%收益率（欧盟最高）的主要原因。Isarescu锚和欧盟成员身份为制度质量提供底线，但该底线不如捷克或波兰坚实。7.5%的ROMGB补偿了真正的政治风险。按政治压力情景下潜在150bp扩大管理头寸。</div>
</div>""",
    },
}


# ── Build logic ───────────────────────────────────────────────────────────────

def build_v4(country_code: str) -> Path:
    data = COUNTRY_DATA[country_code]
    canonical_frame = fetch_canonical_macro_frame(country_code)
    iso_lower = country_code.lower()
    # Map to base HTML filename
    name_map = {"HU": "hungary", "PL": "poland", "CZ": "czechia", "RO": "romania"}
    base_name = name_map[country_code]
    base_path = OUTPUT / f"{base_name}_2026Q2.html"
    out_path = OUTPUT / f"{base_name}_2026Q2_v4.html"

    html = base_path.read_text()

    # Extract chart blocks
    chart_blocks = re.findall(
        r'(<div class="chart-cell"><div.*?</div></div>)', html, re.DOTALL
    )
    chart_map = {}
    for cb in chart_blocks:
        m = re.search(r'id="(chart-[^"]+)"', cb)
        if m:
            chart_map[m.group(1)] = cb

    coverage = DataPipeline().validate_coverage(canonical_frame)
    source_chart_ids = {
        spec.indicator_id
        for spec in INDICATOR_MANIFEST_48
        if _legacy_chart_id(spec.section_id, spec.indicator_id, chart_map)
    }
    adapter_real_ids = {
        row.get("indicator_id")
        for row in canonical_frame
        if row.get("indicator_id") and not row.get("is_proxy")
    }
    source_chart_count = len(source_chart_ids)
    real_indicator_count = len(source_chart_ids | adapter_real_ids)
    coverage["source_chart_count"] = source_chart_count
    coverage["adapter_real_count"] = len(adapter_real_ids - source_chart_ids)
    coverage["proxy_count"] = max(0, coverage.get("expected", len(INDICATOR_MANIFEST_48)) - real_indicator_count)

    # Render CB from config so policy updates do not inherit stale base HTML.
    cb_section = _render_central_bank_section(country_code)
    trade_match = re.search(r'<section class="panel" id="trade">.*?</section>', html, re.DOTALL)
    trade_section_html = trade_match.group() if trade_match else ""

    # Build section panels with narratives (bilingual)
    sections_html = ""
    rendered_chart_ids = []
    for sec_id in SECTION_ORDER:
        title_en, badge_en = SECTION_TITLES[sec_id]
        title_zh, badge_zh = SECTION_TITLES_ZH[sec_id]
        blurb_en = SECTION_BLURBS[sec_id]
        blurb_zh = SECTION_BLURBS_ZH[sec_id]
        narrative_en = data["narratives"].get(sec_id, "")
        narrative_zh = data.get("narratives_zh", {}).get(sec_id, "")
        quality_html = _section_quality_html(sec_id)
        ledger_html = _indicator_ledger_html(sec_id)
        charts_html, section_chart_ids = _render_section_charts(sec_id, country_code, chart_map, canonical_frame)
        rendered_chart_ids.extend(section_chart_ids)

        sections_html += f"""
<section class="panel" id="{sec_id}">
  <h2><span data-lang="en">{title_en}</span><span data-lang="zh">{title_zh}</span> <span class="section-badge"><span data-lang="en">{badge_en}</span><span data-lang="zh">{badge_zh}</span></span></h2>
  <div class="blurb"><span data-lang="en">{blurb_en}</span><span data-lang="zh">{blurb_zh}</span></div>
  {ledger_html}
  <div class="charts">{charts_html}</div>
  <div data-lang="en">{narrative_en}</div>
  <div data-lang="zh">{narrative_zh}</div>
{quality_html}</section>
"""

    # Plotly JS
    plotly_js = re.search(r'<script src="https://cdn.plot.ly/plotly-2\.32\.0\.min\.js"></script>', html)
    plotly_tag = plotly_js.group(0) if plotly_js else '<script src="https://cdn.plot.ly/plotly-2.32.0.min.js"></script>'

    # Build country switcher nav
    all_countries = [
        ("HU", "Hungary", "hungary_2026Q2_v4.html"),
        ("PL", "Poland", "poland_2026Q2_v4.html"),
        ("CZ", "Czechia", "czechia_2026Q2_v4.html"),
        ("RO", "Romania", "romania_2026Q2_v4.html"),
    ]
    nav_links = []
    for cc, cname, cfile in all_countries:
        cls = 'nav-link active' if cc == country_code else 'nav-link'
        nav_links.append(f'<a href="{cfile}" class="{cls}">{cc}</a>')
    country_nav = "\n    " + "\n    ".join(nav_links)

    # Chart IDs for JS fix script
    all_chart_ids = list(dict.fromkeys(rendered_chart_ids))
    # Also add trade chart if present
    trade_chart_match = re.search(r'id="(trade-chart-\d+)"', trade_section_html)
    if trade_chart_match:
        all_chart_ids.append(trade_chart_match.group(1))
    chart_ids_js = '["' + '","'.join(all_chart_ids) + '"]'

    final_html = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{data["name"]} Dashboard</title>
{plotly_tag}
<style>{CSS}</style>
</head>
<body>

<div class="topbar">
  <a href="../index.html" style="text-decoration:none;color:inherit;"><div class="brand">East Meridian <span>/ Country Primer</span></div></a>
  <div class="country-nav">
    {country_nav}
  </div>
  <div style="display:flex;align-items:center;">
    <span class="meta-item">{data["name"]} · {data["iso"]} · {data["cb"]}</span>
    <button class="lang-toggle" onclick="toggleLang()" id="lang-btn">中文</button>
  </div>
</div>

<div class="container">

<header>
  <h1>{data["name"]} Dashboard</h1>
  <div class="subtitle"><span data-lang="en">{data["subtitle"]}</span><span data-lang="zh">{data.get("subtitle_zh", data["subtitle"])}</span></div>
  <div class="meta-row">
    <div class="meta-chip"><span data-lang="en">Framework:</span><span data-lang="zh">框架:</span> <strong>IMF FPP × GS Indicators × Buy-side PM</strong></div>
    <div class="meta-chip"><span data-lang="en">Rating:</span><span data-lang="zh">评级:</span> <strong>{data["rating"]}</strong></div>
    <div class="meta-chip"><span data-lang="en">FX Regime:</span><span data-lang="zh">汇率制度:</span> <strong>{data["fxregime"]}</strong></div>
    <div class="meta-chip"><span data-lang="en">Target:</span><span data-lang="zh">目标:</span> <strong>{data["inftarget"]}</strong></div>
  </div>
</header>

<div data-lang="en">{data["kpi_html"]}</div>
<div data-lang="zh">{data.get("kpi_html_zh", data["kpi_html"])}</div>

<!-- TOC -->
<div class="toc">
  <a href="#snapshot"><span data-lang="en">§1 Snapshot</span><span data-lang="zh">§1 概览</span></a>
  <a href="#data-quality"><span data-lang="en">Data Quality</span><span data-lang="zh">数据质量</span></a>
  <a href="#real_activity"><span data-lang="en">§2 Real Activity</span><span data-lang="zh">§2 实际经济活动</span></a>
  <a href="#prices_wages"><span data-lang="en">§3 Prices & Wages</span><span data-lang="zh">§3 物价与工资</span></a>
  <a href="#external"><span data-lang="en">§4 External</span><span data-lang="zh">§4 外部部门</span></a>
  <a href="#fiscal_sovereign"><span data-lang="en">§5 Fiscal & Sovereign</span><span data-lang="zh">§5 财政与主权信用</span></a>
  <a href="#monetary_financial"><span data-lang="en">§6 Monetary & Financial</span><span data-lang="zh">§6 货币与金融</span></a>
  <a href="#markets_valuation"><span data-lang="en">§7 Markets & Valuation</span><span data-lang="zh">§7 市场与估值</span></a>
  <a href="#financial_stability"><span data-lang="en">§8 Financial Stability</span><span data-lang="zh">§8 金融稳定</span></a>
  <a href="#demographics"><span data-lang="en">§9 Demographics</span><span data-lang="zh">§9 人口结构</span></a>
  <a href="#political_economy"><span data-lang="en">§10 Political Economy</span><span data-lang="zh">§10 政治经济</span></a>
</div>

{_quality_panel_html()}

{_coverage_panel_html(coverage)}

<!-- Snapshot -->
<div class="snapshot-panel" id="snapshot">
  <h2><span data-lang="en">§1 Country Snapshot</span><span data-lang="zh">§1 国别概览</span></h2>
  <div class="blurb"><span data-lang="en">Structural parameters that set the frame: economic size, sovereign rating, FX regime, the central bank's mandate, and qualitative country context. These are the slow-moving variables against which the cyclical sections below should be read.</span><span data-lang="zh">设定框架的结构性参数: 经济规模、主权评级、汇率制度、央行职责及定性国别背景。这些是慢变量，后续周期性章节应以此为背景解读。</span></div>
  <div class="snapshot-prose">
    <div data-lang="en">{data["snapshot_prose"]}</div>
    <div data-lang="zh">{data.get("snapshot_prose_zh", data["snapshot_prose"])}</div>
  </div>
</div>

""" + "<div data-lang=\"en\">" + cb_section + trade_section_html + "</div>" + f"""

<!-- Chart Sections with Narrative Commentary -->
{sections_html}

<footer>
  <div class="attribution">
    <span data-lang="en">Country Primer v4 · Data via openecon-data MCP, ECB, Eurostat, BIS, World Bank, Yahoo Finance · Charts: Plotly</span>
    <span data-lang="zh">Country Primer v4 · 数据来源: openecon-data MCP, ECB, Eurostat, BIS, World Bank, Yahoo Finance · 图表: Plotly</span>
  </div>
  <div class="disclaimer">
    <span data-lang="en"><strong>Disclaimer:</strong> This is a research artefact produced for analytical purposes, not investment advice. All positioning views expressed are illustrative of the analytical framework and should not be construed as trade recommendations. Past performance does not guarantee future results. Macro narratives reflect the author's assessment as of the generation date and may change without notice.</span>
    <span data-lang="zh"><strong>免责声明:</strong> 本文为用于分析目的之研究产出，不构成投资建议。所有投资定位观点均为分析框架的示例性表达，不应被解释为交易建议。过往业绩不保证未来结果。宏观叙事反映作者在生成日期的评估，可能随时变化，恕不另行通知。</span>
  </div>
</footer>

</div>

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

<script>
(function() {{
  // After all Plotly charts render, fix autorange + annotate latest values
  var chartIds = {chart_ids_js};
  var mainCountry = '{country_code}';

  function fixCharts() {{
    chartIds.forEach(function(cid) {{
      var el = document.getElementById(cid);
      if (!el) return;
      try {{
        // Force full-range display on both axes
        Plotly.relayout(cid, {{'xaxis.autorange': true, 'yaxis.autorange': true}});
      }} catch(e) {{}}

      // Annotate latest value of the main-country trace
      try {{
        var gd = document.getElementById(cid);
        if (!gd || !gd.data || !gd.data.length) return;
        var traces = gd.data;
        var bestTrace = null, bestWidth = 0;
        for (var i = 0; i < traces.length; i++) {{
          var t = traces[i];
          if (t.name === mainCountry) {{ bestTrace = t; break; }}
          var w = (t.line && t.line.width) ? t.line.width : 1;
          if (w > bestWidth) {{ bestWidth = w; bestTrace = t; }}
        }}
        if (!bestTrace || !bestTrace.x || bestTrace.x.length === 0) return;
        var lastX = bestTrace.x[bestTrace.x.length - 1];
        var lastY = bestTrace.y[bestTrace.y.length - 1];
        // Walk back to find non-null value
        for (var j = bestTrace.y.length - 1; j >= 0 && (lastY === null || lastY === undefined); j--) {{
          lastX = bestTrace.x[j]; lastY = bestTrace.y[j];
        }}
        if (lastY === null || lastY === undefined) return;
        var valStr;
        if (typeof lastY === 'number') {{
          if (Math.abs(lastY) < 10) valStr = lastY.toFixed(2);
          else if (Math.abs(lastY) < 100) valStr = lastY.toFixed(1);
          else valStr = lastY.toLocaleString('en-US', {{maximumFractionDigits: 0}});
        }} else {{ valStr = String(lastY); }}
        var curAnn = (gd.layout && gd.layout.annotations) ? gd.layout.annotations.slice() : [];
        curAnn.push({{
          x: lastX, y: lastY, xref: 'x', yref: 'y',
          text: '<b>' + valStr + '</b>',
          showarrow: true, arrowhead: 2, arrowsize: 1,
          arrowwidth: 1.5, arrowcolor: '#8a593d',
          ax: 40, ay: -30,
          font: {{color: '#8a593d', size: 12, family: 'Avenir Next, PingFang SC, Hiragino Sans GB, Noto Sans SC, Segoe UI, Helvetica Neue, Arial, sans-serif'}},
          bgcolor: 'rgba(255,255,255,0.85)',
          borderpad: 3, xanchor: 'left'
        }});
        Plotly.relayout(cid, {{annotations: curAnn}});
      }} catch(e) {{}}
    }});
  }}

  if (typeof Plotly !== 'undefined') {{
    fixCharts();
  }} else {{
    var check = setInterval(function() {{
      if (typeof Plotly !== 'undefined') {{ clearInterval(check); fixCharts(); }}
    }}, 200);
  }}
}})();
</script>
</body>
</html>
"""

    out_path.write_text(final_html)
    return out_path


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python build_v4.py {HU|PL|CZ|RO|ALL}")
        sys.exit(1)

    target = sys.argv[1].upper()
    if target == "ALL":
        targets = ["HU", "PL", "CZ", "RO"]
    elif target in COUNTRY_DATA:
        targets = [target]
    else:
        print(f"Unknown country: {target}. Use HU, PL, CZ, RO, or ALL")
        sys.exit(1)

    for cc in targets:
        path = build_v4(cc)
        print(f"Wrote {path} ({path.stat().st_size:,} bytes)")
