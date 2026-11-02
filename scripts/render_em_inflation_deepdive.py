"""Modular Institutional Renderer for Global & Emerging Markets Inflation & Pricing Studio.

Generates FT / Morgan Stanley institutional-grade interactive HTML components for:
- Kazakhstan (KZ)
- Uzbekistan (UZ)
- United Kingdom (UK)
- Japan (JP)
- Hong Kong (HK)
- Egypt (EG)
- Nigeria (NG)
- Turkey (TR)
- South Africa (ZA)
- South Korea (KR)
- Taiwan (TW)

Includes:
1. Complete DEEPDIVE_CSS stylesheet for responsive layout, cards, and tables.
2. Table 1: CPI Inflation by product group (12 COICOP divisions, collapsible sub-items & month switcher).
3. Short-Term Inflation Momentum Monitor (1M, 3M, 6M annualized rates vs 12M YoY & Plotly chart with annotated readings).
4. Table 2: Industrial PPI & Components (with month switcher).
5. PPI - CPI Margin Scissors Pipeline (with spread chart and margin squeeze monitor).
6. Pricing Expectations & Capacity Studio (Sector gauge cards & historical percentiles).
7. Full JavaScript engine for tab switching, month updating, and row collapsing.
"""

from __future__ import annotations

import json
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUTPUT = ROOT / "output"

NAME_MAP = {
    "TR": "turkey",
    "ZA": "south_africa",
    "KR": "south_korea",
    "TW": "taiwan",
    "UK": "uk",
    "JP": "japan",
    "HK": "hong_kong",
    "EG": "egypt",
    "NG": "nigeria",
    "KZ": "kazakhstan",
    "UZ": "uzbekistan",
}

DEEPDIVE_CSS = """
<style>
.deepdive-macro-panel {
  background: #ffffff;
  border: 1px solid var(--border, #e2e8f0);
  border-radius: 6px;
  padding: 20px;
  margin-bottom: 24px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.03);
}
.deepdive-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  border-bottom: 1px solid var(--border, #e2e8f0);
  padding-bottom: 14px;
  margin-bottom: 16px;
  flex-wrap: wrap;
  gap: 12px;
}
.deepdive-title-wrap {
  flex: 1 1 340px;
}
.deepdive-badge {
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: #2563eb;
  background: rgba(37,99,235,0.08);
  padding: 2px 7px;
  border-radius: 3px;
  display: inline-block;
  margin-bottom: 6px;
}
.deepdive-title {
  font-size: 17px;
  font-weight: 700;
  margin: 0 0 4px 0;
  color: var(--fg, #0f172a);
}
.deepdive-subtitle {
  font-size: 12px;
  color: var(--muted, #64748b);
  margin: 0;
}
.deepdive-tabs {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}
.deepdive-tab {
  background: #f1f5f9;
  border: 1px solid var(--border, #e2e8f0);
  border-radius: 4px;
  padding: 6px 12px;
  font-size: 12px;
  font-weight: 600;
  color: var(--fg, #334155);
  cursor: pointer;
  transition: all 0.15s ease;
}
.deepdive-tab:hover {
  background: #e2e8f0;
}
.deepdive-tab.active {
  background: #0f172a;
  color: #ffffff;
  border-color: #0f172a;
}
.deepdive-tab-content {
  display: none;
}
.deepdive-tab-content.active {
  display: block;
}
.table-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
  flex-wrap: wrap;
  gap: 10px;
}
.table-caption {
  font-size: 13px;
  font-weight: 600;
  display: inline-flex;
  align-items: center;
  gap: 8px;
}
.table-badge-primary {
  font-size: 10px;
  background: #eff6ff;
  color: #1d4ed8;
  padding: 2px 6px;
  border-radius: 3px;
  font-weight: 600;
}
.table-badge-momentum {
  font-size: 10px;
  background: #fef3c7;
  color: #92400e;
  padding: 2px 6px;
  border-radius: 3px;
  font-weight: 600;
}
.month-select {
  font-size: 12px;
  padding: 4px 8px;
  border: 1px solid var(--border, #cbd5e1);
  border-radius: 4px;
  background: #ffffff;
  color: var(--fg, #0f172a);
  font-weight: 500;
  cursor: pointer;
}
.table-responsive {
  overflow-x: auto;
  background: var(--bg-surface, #ffffff);
  border-radius: 4px;
}
.inflation-table {
  width: 100%;
  border-collapse: collapse;
  font-family: var(--font-body, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif);
  font-size: 13px;
  font-variant-numeric: tabular-nums;
  line-height: 1.5;
  border-top: 1.5px solid var(--fg, #0f172a);
  border-bottom: 1.5px solid var(--fg, #0f172a);
}
.inflation-table th {
  background: transparent;
  color: var(--fg, #0f172a);
  font-weight: 600;
  padding: 6px 12px;
  border: none;
  white-space: nowrap;
}
.inflation-table th.col-group-header {
  text-align: center;
  border-bottom: 1px solid var(--fg, #0f172a);
  padding-bottom: 3px;
}
.inflation-table tr.th-tier2 th {
  border-bottom: 1.5px solid var(--fg, #0f172a);
  padding-bottom: 6px;
}
.inflation-table td {
  padding: 4px 12px;
  border: none;
  white-space: nowrap;
  color: var(--fg, #0f172a);
}
.inflation-table .col-name {
  text-align: left;
  min-width: 190px;
}
.inflation-table .col-sub {
  padding-left: 28px;
  color: var(--text-secondary, #475569);
}
.inflation-table .col-num {
  text-align: right;
  font-family: inherit;
}
.inflation-table .col-weight {
  color: var(--muted, #64748b);
}
.inflation-table .row-headline {
  background: transparent;
  font-weight: 700;
}
.inflation-table .row-headline td {
  padding-top: 6px;
  padding-bottom: 6px;
}
.inflation-table .row-division {
  border: none;
}
.inflation-table .row-division:hover,
.inflation-table .row-subitem:hover {
  background: rgba(125, 125, 125, 0.05);
}
.inflation-table .row-subitem {
  background: transparent;
}
.inflation-table .sub-tree-prefix {
  color: #94a3b8;
  font-weight: 600;
}
.inflation-table .sub-toggle-btn {
  background: none;
  border: none;
  cursor: pointer;
  color: #94a3b8;
  font-size: 9px;
  padding: 0 4px;
  margin-right: 4px;
}
.inflation-table .sub-toggle-btn:hover {
  color: var(--fg, #0f172a);
}
.inflation-table .sub-placeholder {
  display: inline-block;
  width: 14px;
}
.inflation-table .row-separator td {
  height: 18px;
  background: transparent;
  border: none;
  padding: 0;
}
.inflation-table .row-memo {
  background: transparent;
  color: var(--fg, #0f172a);
}
.inflation-table .val-pos {
  color: #b91c1c;
}
.inflation-table .val-neg {
  color: #047857;
}
.inflation-table .val-neutral {
  color: #64748b;
}
.inflation-table .text-muted {
  color: #8892a0;
  font-weight: 400;
}
.table-footnote {
  font-size: 11px;
  color: var(--muted, #64748b);
  margin-top: 8px;
  margin-bottom: 16px;
  line-height: 1.4;
}
.subchart-container {
  margin-top: 20px;
  border-top: 1px solid var(--border, #e2e8f0);
  padding-top: 16px;
}
.subchart-header h4 {
  font-size: 13px;
  font-weight: 600;
  margin: 0 0 10px 0;
  color: var(--fg, #0f172a);
}
.momentum-kpi-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 12px;
  margin-bottom: 16px;
}
.momentum-kpi-card {
  background: #f8fafc;
  border: 1px solid var(--border, #e2e8f0);
  border-radius: 6px;
  padding: 14px;
}
.momentum-kpi-card.highlight-card {
  background: #eff6ff;
  border-color: #bfdbfe;
}
.momentum-kpi-card .kpi-label {
  font-size: 11px;
  font-weight: 600;
  color: var(--muted, #64748b);
  margin-bottom: 4px;
}
.momentum-kpi-card .kpi-val {
  font-size: 22px;
  font-weight: 700;
  color: var(--fg, #0f172a);
  font-variant-numeric: tabular-nums;
  line-height: 1.2;
}
.momentum-kpi-card .kpi-gap {
  color: #2563eb;
}
.momentum-kpi-card .kpi-subtext {
  font-size: 11px;
  color: var(--muted, #64748b);
  margin-top: 4px;
}
.status-badge {
  font-size: 10px;
  font-weight: 700;
  padding: 2px 7px;
  border-radius: 3px;
  display: inline-block;
}
.badge-squeeze {
  background: #fee2e2;
  color: #991b1b;
}
.badge-expand {
  background: #dcfce7;
  color: #166534;
}
.badge-neutral {
  background: #f1f5f9;
  color: #475569;
}
.sector-cards-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 14px;
}
.sector-card {
  background: #ffffff;
  border: 1px solid var(--border, #e2e8f0);
  border-radius: 6px;
  padding: 14px;
  box-shadow: 0 1px 2px rgba(0,0,0,0.02);
}
.sector-card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}
.sector-card-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--fg, #0f172a);
}
.sector-card-badge {
  font-size: 10px;
  font-weight: 600;
  padding: 2px 6px;
  border-radius: 3px;
}
.sector-card-val {
  font-size: 22px;
  font-weight: 700;
  color: var(--fg, #0f172a);
  font-variant-numeric: tabular-nums;
}
.sector-card-sub {
  font-size: 11px;
  color: var(--muted, #64748b);
  margin-top: 4px;
  display: flex;
  justify-content: space-between;
}
</style>
"""


def _format_num(val, decimals=1, signed=False):
    if val is None:
        return "—"
    try:
        f = float(val)
        prefix = "+" if (signed and f > 0) else ""
        return f"{prefix}{f:.{decimals}f}"
    except (ValueError, TypeError):
        return str(val)


def _format_mon_yy(ym_str: str) -> str:
    if not ym_str or len(ym_str) < 7:
        return ym_str or ""
    try:
        from datetime import datetime
        d = datetime.strptime(ym_str[:7], "%Y-%m")
        return d.strftime("%b-%y")
    except Exception:
        return ym_str


def render_em_deepdive_panel(country_code: str) -> str:
    """Render 5-tab institutional inflation studio for given EM country code."""
    cc = country_code.upper()
    c_name = NAME_MAP.get(cc)
    if not c_name:
        return ""

    data_path = OUTPUT / f"{c_name}_inflation_deepdive.json"
    if not data_path.exists():
        return ""

    with open(data_path, "r", encoding="utf-8") as f:
        deepdive = json.load(f)

    available_months = deepdive.get("available_months", [])
    if not available_months:
        return ""

    latest_m = available_months[0]
    country = deepdive.get("country", cc)
    agency = deepdive.get("agency", f"{country} Official Statistics")
    cpi_tables = deepdive.get("cpi_tables", {})
    momentum_tables = deepdive.get("momentum_tables", {})
    ppi_tables = deepdive.get("ppi_tables", {})
    exp_summary = deepdive.get("expectations_summary", {})
    ts = deepdive.get("time_series", {})

    latest_cpi_tbl = cpi_tables.get(latest_m, {})
    latest_mom_tbl = momentum_tables.get(latest_m, {})
    latest_ppi_tbl = ppi_tables.get(latest_m, {})

    # Month options for dropdowns
    cpi_month_options = "\n".join(
        f'<option value="{m}" {"selected" if m == latest_m else ""}>{m}</option>'
        for m in available_months
    )

    # 1. Render Initial CPI Table Rows
    def _render_cpi_rows(tbl):
        if not tbl:
            return ""
        head = tbl.get("headline", {})
        h_html = f"""
        <tr class="row-headline">
          <td class="col-name"><strong>Headline</strong></td>
          <td class="col-num">&nbsp;</td>
          <td class="col-num"><strong>{_format_num(head.get('yoy'))}</strong></td>
          <td class="col-num text-muted">{_format_num(head.get('yoy_prev'))}</td>
          <td class="col-num">&nbsp;</td>
          <td class="col-num"><strong>{_format_num(head.get('mom'))}</strong></td>
          <td class="col-num text-muted">{_format_num(head.get('mom_ago'))}</td>
          <td class="col-num"><strong>{_format_num(head.get('contrib_mom'))}</strong></td>
        </tr>
        """

        items_html = []
        for it in tbl.get("items", []):
            subs = it.get("sub_items", [])
            has_sub = len(subs) > 0
            group_key = f"{cc}-{it['code']}"
            toggle_btn = f'<button class="sub-toggle-btn" onclick="toggleSubRows(\'{group_key}\', this)" title="Toggle sub-items">▶</button>' if has_sub else '<span class="sub-placeholder"></span>'
            name_disp = it.get("name_en") or it.get("name") or it.get("code")

            row = f"""
            <tr class="row-division" data-group="{group_key}">
              <td class="col-name">{toggle_btn} <span>{escape(name_disp)}</span></td>
              <td class="col-num col-weight">{_format_num(it.get('weight'))}</td>
              <td class="col-num">{_format_num(it.get('yoy'))}</td>
              <td class="col-num text-muted">{_format_num(it.get('yoy_prev'))}</td>
              <td class="col-num">{_format_num(it.get('contrib_yoy'))}</td>
              <td class="col-num">{_format_num(it.get('mom'))}</td>
              <td class="col-num text-muted">{_format_num(it.get('mom_ago'))}</td>
              <td class="col-num">{_format_num(it.get('contrib_mom'))}</td>
            </tr>
            """
            items_html.append(row)

            if has_sub:
                for sub in subs:
                    sub_name = sub.get("name_en") or sub.get("name") or sub.get("code")
                    sub_row = f"""
                    <tr class="row-subitem sub-{group_key}" style="display: none;">
                      <td class="col-name col-sub"><span class="sub-tree-prefix">↳</span> {escape(sub_name)}</td>
                      <td class="col-num col-weight text-muted">{_format_num(sub.get('weight'), 1)}</td>
                      <td class="col-num">{_format_num(sub.get('yoy'))}</td>
                      <td class="col-num text-muted">{_format_num(sub.get('yoy_prev'))}</td>
                      <td class="col-num">{_format_num(sub.get('contrib_yoy'))}</td>
                      <td class="col-num">{_format_num(sub.get('mom'))}</td>
                      <td class="col-num text-muted">{_format_num(sub.get('mom_ago'))}</td>
                      <td class="col-num">{_format_num(sub.get('contrib_mom'))}</td>
                    </tr>
                    """
                    items_html.append(sub_row)

        memo_html = []
        for m in tbl.get("memo", []):
            m_name = m.get("name_en") or m.get("name") or m.get("code")
            m_row = f"""
            <tr class="row-memo">
              <td class="col-name"><span>{escape(m_name)}</span></td>
              <td class="col-num col-weight">{_format_num(m.get('weight')) if m.get('weight') else '&nbsp;'}</td>
              <td class="col-num">{_format_num(m.get('yoy'))}</td>
              <td class="col-num text-muted">{_format_num(m.get('yoy_prev'))}</td>
              <td class="col-num">&nbsp;</td>
              <td class="col-num">{_format_num(m.get('mom'))}</td>
              <td class="col-num text-muted">{_format_num(m.get('mom_ago'))}</td>
              <td class="col-num">&nbsp;</td>
            </tr>
            """
            memo_html.append(m_row)

        memo_block = f"""<tr class="row-separator"><td colspan="8"></td></tr>\n{"".join(memo_html)}""" if memo_html else ""
        return h_html + "".join(items_html) + memo_block

    # 2. Render Initial Momentum Table Rows
    def _render_momentum_rows(tbl):
        if not tbl:
            return ""
        rows_html = []
        for it in tbl.get("items", []):
            is_head = it.get("code") in ("TOTAL", "HEADLINE")
            row_cls = "row-headline" if is_head else "row-division"
            gap_val = it.get("gap")
            gap_cls = "val-pos" if gap_val and gap_val > 0.5 else ("val-neg" if gap_val and gap_val < -0.5 else "val-neutral")
            badge = f'<span class="status-badge {it.get("badge", "badge-neutral")}">{it.get("icon", "")} <span data-lang="en">{it.get("signal_en", "")}</span><span data-lang="zh">{it.get("signal_zh", "")}</span></span>'
            name_disp = it.get("name_en") or it.get("name") or it.get("code")

            row = f"""
            <tr class="{row_cls}">
              <td class="col-name"><span>{escape(name_disp)}</span></td>
              <td class="col-num col-weight">{_format_num(it.get('weight'))}</td>
              <td class="col-num">{_format_num(it.get('mom_1m_ann'), 1, signed=True)}%</td>
              <td class="col-num"><strong>{_format_num(it.get('mom_3m_ann'), 1, signed=True)}%</strong></td>
              <td class="col-num text-muted">{_format_num(it.get('mom_6m_ann'), 1, signed=True)}%</td>
              <td class="col-num">{_format_num(it.get('yoy'), 1, signed=True)}%</td>
              <td class="col-num {gap_cls}"><strong>{_format_num(gap_val, 1, signed=True)} pp</strong></td>
              <td class="col-name" style="text-align: center;">{badge}</td>
            </tr>
            """
            rows_html.append(row)
        return "\n".join(rows_html)

    # 3. Render Initial PPI Table Rows
    def _render_ppi_rows(tbl):
        if not tbl:
            return ""
        head = tbl.get("headline", {})
        h_html = f"""
        <tr class="row-headline">
          <td class="col-name"><strong>Headline PPI (Industrial Output)</strong></td>
          <td class="col-num">&nbsp;</td>
          <td class="col-num"><strong>{_format_num(head.get('yoy'))}</strong></td>
          <td class="col-num text-muted">{_format_num(head.get('yoy_prev'))}</td>
          <td class="col-num">&nbsp;</td>
          <td class="col-num"><strong>{_format_num(head.get('mom'))}</strong></td>
          <td class="col-num text-muted">{_format_num(head.get('mom_ago'))}</td>
          <td class="col-num"><strong>{_format_num(head.get('contrib_mom'))}</strong></td>
        </tr>
        """

        items_html = []
        for it in tbl.get("items", []):
            name_disp = it.get("name_en") or it.get("name") or it.get("code")
            row = f"""
            <tr class="row-division">
              <td class="col-name"><span>{escape(name_disp)}</span></td>
              <td class="col-num col-weight">{_format_num(it.get('weight'))}</td>
              <td class="col-num">{_format_num(it.get('yoy'))}</td>
              <td class="col-num text-muted">{_format_num(it.get('yoy_prev'))}</td>
              <td class="col-num">{_format_num(it.get('contrib_yoy'))}</td>
              <td class="col-num">{_format_num(it.get('mom'))}</td>
              <td class="col-num text-muted">{_format_num(it.get('mom_ago'))}</td>
              <td class="col-num">{_format_num(it.get('contrib_mom'))}</td>
            </tr>
            """
            items_html.append(row)
        return h_html + "\n".join(items_html)

    # 4. Expectations Cards
    exp_cards = []
    g1 = exp_summary.get("gauge1", {})
    g2 = exp_summary.get("gauge2", {})
    for g in [g1, g2]:
        if not g:
            continue
        g_val = g.get("val", 0)
        g_unit = g.get("unit", "%")
        g_t_en = escape(g.get("title_en", ""))
        g_t_zh = escape(g.get("title_zh", ""))
        g_ev_en = escape(g.get("eval_en", ""))
        g_ev_zh = escape(g.get("eval_zh", ""))
        g_target = escape(str(g.get("target", "Target")))

        exp_cards.append(f"""
        <div class="sector-card">
          <div class="sector-card-header">
            <span class="sector-card-title"><span data-lang="en">{g_t_en}</span><span data-lang="zh">{g_t_zh}</span></span>
            <span class="sector-card-badge badge-neutral">Target: {g_target}</span>
          </div>
          <div class="sector-card-val">{g_val} <span style="font-size: 13px; font-weight: normal; color: var(--muted, #64748b);">{g_unit}</span></div>
          <div class="sector-card-sub">
            <span>{latest_m}</span>
            <span>Survey / Central Bank</span>
          </div>
          <p style="font-size: 11px; margin: 8px 0 0 0; color: var(--text-secondary, #475569); line-height: 1.35;">
            <span data-lang="en">{g_ev_en}</span>
            <span data-lang="zh">{g_ev_zh}</span>
          </p>
        </div>
        """)
    exp_cards_html = "\n".join(exp_cards)

    # Time series payload for Plotly
    ts_dates = ts.get("dates", [])
    ts_cpi = ts.get("cpi_yoy", [])
    ts_ppi = ts.get("ppi_yoy", [])
    ts_spread = ts.get("scissors_spread", [])

    mom_dates = sorted(list(momentum_tables.keys()))
    mom_h3 = [momentum_tables[d].get("headline_ann_3m") for d in mom_dates]
    mom_hy = [momentum_tables[d].get("headline_yoy") for d in mom_dates]

    # Headline values for KPI banner
    head_yoy = latest_cpi_tbl.get("headline", {}).get("yoy", 0.0)
    head_mom = latest_cpi_tbl.get("headline", {}).get("mom", 0.0)
    m3_val = latest_mom_tbl.get("headline_ann_3m", 0.0)
    m3_gap = latest_mom_tbl.get("headline_gap", 0.0)

    html_out = f"""{DEEPDIVE_CSS}
<!-- ══════════════════════════════════════════════════════════════════════════ -->
<!-- INSTITUTIONAL INFLATION, MOMENTUM & INDUSTRIAL PRICING STUDIO: {cc}        -->
<!-- ══════════════════════════════════════════════════════════════════════════ -->
<div class="deepdive-macro-panel" id="deepdive-inflation-{cc}">
  <div class="deepdive-header">
    <div class="deepdive-title-wrap">
      <span class="deepdive-badge"><span data-lang="en">INSTITUTIONAL SUITE</span><span data-lang="zh">机构级通胀与工业物价工坊</span></span>
      <h3 class="deepdive-title">
        <span data-lang="en">{country} Inflation Decomposition, Momentum & Pricing Studio</span>
        <span data-lang="zh">{country} 通胀分项贡献、短期动量与工业定价工坊</span>
      </h3>
      <p class="deepdive-subtitle">
        <span data-lang="en">Institutional disaggregation across official basket expenditure divisions, 1M/3M/6M annualized momentum, industrial PPI & margin scissors spread.</span>
        <span data-lang="zh">官方消费类目贡献拆解、1M/3M/6M短期通胀动量年化监控、工业出厂PPI、利润剪刀差传导链与央行调查预期。</span>
      </p>
    </div>
    <div class="deepdive-tabs">
      <button class="deepdive-tab active" onclick="switchDeepdiveTab('{cc}', 'cpi', this)">
        <span data-lang="en">Table 1: CPI Breakdown</span><span data-lang="zh">表1：CPI分项贡献</span>
      </button>
      <button class="deepdive-tab" onclick="switchDeepdiveTab('{cc}', 'momentum', this)">
        <span data-lang="en">Short-Term Momentum</span><span data-lang="zh">通胀短期动量监控</span>
      </button>
      <button class="deepdive-tab" onclick="switchDeepdiveTab('{cc}', 'ppi', this)">
        <span data-lang="en">Table 2: PPI Breakdown</span><span data-lang="zh">表2：PPI工业分组</span>
      </button>
      <button class="deepdive-tab" onclick="switchDeepdiveTab('{cc}', 'pipeline', this)">
        <span data-lang="en">Margin Scissors</span><span data-lang="zh">利润剪刀差传导链</span>
      </button>
      <button class="deepdive-tab" onclick="switchDeepdiveTab('{cc}', 'expectations', this)">
        <span data-lang="en">Expectations & Surveys</span><span data-lang="zh">预期与景气调查</span>
      </button>
    </div>
  </div>

  <!-- ── TAB 1: CPI TABLE ────────────────────────────────────────────────── -->
  <div class="deepdive-tab-content active" id="tab-cpi-{cc}">
    <div class="table-toolbar">
      <div class="toolbar-left">
        <span class="table-caption">
          <strong><span data-lang="en">Table 1: CPI Inflation by product group</span><span data-lang="zh">表 1：CPI 分项通胀与贡献拆解</span></strong>
          <span class="table-badge-primary">{country} Official Basket</span>
        </span>
      </div>
      <div class="toolbar-right">
        <label for="cpi-select-{cc}"><span data-lang="en">Release Print:</span><span data-lang="zh">统计报告期：</span></label>
        <select id="cpi-select-{cc}" class="month-select" onchange="updateCpiTable('{cc}', this.value)">
          {cpi_month_options}
        </select>
      </div>
    </div>

    <div class="table-responsive">
      <table class="inflation-table" id="table-cpi-{cc}">
        <thead>
          <tr class="th-tier1">
            <th rowspan="2" class="col-name text-left"><span data-lang="en">Product Group</span><span data-lang="zh">商品与服务类别</span></th>
            <th rowspan="2" class="col-num"><span data-lang="en">Weights</span><span data-lang="zh">权重%</span></th>
            <th colspan="3" class="col-group-header"><span data-lang="en">y / y</span><span data-lang="zh">同 比 (y/y)</span></th>
            <th colspan="3" class="col-group-header"><span data-lang="en">m / m</span><span data-lang="zh">环 比 (m/m)</span></th>
          </tr>
          <tr class="th-tier2">
            <th class="col-num th-curr-yoy">{_format_mon_yy(latest_m)}</th>
            <th class="col-num th-prev-yoy text-muted">{_format_mon_yy(latest_cpi_tbl.get('prev_date', ''))}</th>
            <th class="col-num th-contrib-yoy"><span data-lang="en">Contrib*<br>to y/y</span><span data-lang="zh">同比贡献*</span></th>
            <th class="col-num th-curr-mom">{_format_mon_yy(latest_m)}</th>
            <th class="col-num th-ago-mom text-muted"><span data-lang="en">1Y ago</span><span data-lang="zh">上年同期</span></th>
            <th class="col-num th-contrib-mom"><span data-lang="en">Contrib*<br>to m/m</span><span data-lang="zh">环比贡献*</span></th>
          </tr>
        </thead>
        <tbody id="tbody-cpi-{cc}">
          {_render_cpi_rows(latest_cpi_tbl)}
        </tbody>
      </table>
    </div>
    <div class="table-footnote">
      <span data-lang="en">*Methodology: Additive contributions calculated from official expenditure weights and sequential indices. Source: {agency}.</span>
      <span data-lang="zh">*计算口径：基于官方一揽子支出权重与价格变动计算的加法拆解贡献。数据源：{agency}。</span>
    </div>
  </div>

  <!-- ── TAB 2: MOMENTUM ─────────────────────────────────────────────────── -->
  <div class="deepdive-tab-content" id="tab-momentum-{cc}">
    <div class="momentum-kpi-grid">
      <div class="momentum-kpi-card highlight-card">
        <div class="kpi-label"><span data-lang="en">Headline 3M Annualized Pace</span><span data-lang="zh">总体 3 个月复利年化增速</span></div>
        <div class="kpi-val">{_format_num(m3_val, 1, signed=True)}%</div>
        <div class="kpi-subtext">
          <span data-lang="en">vs 12M YoY: <strong>{_format_num(head_yoy, 1)}%</strong> | Momentum Gap: <strong>{_format_num(m3_gap, 1, signed=True)} pp</strong></span>
          <span data-lang="zh">对比 12M 同比: <strong>{_format_num(head_yoy, 1)}%</strong> | 动量差值: <strong>{_format_num(m3_gap, 1, signed=True)} pp</strong></span>
        </div>
      </div>
      <div class="momentum-kpi-card">
        <div class="kpi-label"><span data-lang="en">Momentum Regime Verdict</span><span data-lang="zh">短期通胀动量研判</span></div>
        <div class="kpi-val" style="font-size: 16px; margin-top: 4px;">
          <span class="status-badge {'badge-squeeze' if m3_gap and m3_gap > 0.5 else ('badge-expand' if m3_gap and m3_gap < -0.5 else 'badge-neutral')}">
            <span data-lang="en">{latest_mom_tbl.get('headline_signal_en', 'Balanced')}</span>
            <span data-lang="zh">{latest_mom_tbl.get('headline_signal_zh', '常态平稳')}</span>
          </span>
        </div>
        <div class="kpi-subtext">
          <span data-lang="en">3M annualized pace filters out past 12M base effects to reveal true sequential velocity.</span>
          <span data-lang="zh">3个月年化增速剔除基数扰动，领先同比指标约1至2个季度反映最新环比动能。</span>
        </div>
      </div>
    </div>

    <div class="table-toolbar">
      <div class="toolbar-left">
        <span class="table-caption">
          <strong><span data-lang="en">Short-Term Inflation Momentum Matrix (Annualized Pace vs YoY)</span><span data-lang="zh">通胀短期动量解构矩阵 (1M/3M/6M年化率 vs 同比)</span></strong>
          <span class="table-badge-momentum">Annualized Rates</span>
        </span>
      </div>
      <div class="toolbar-right">
        <label for="mom-select-{cc}"><span data-lang="en">Release Print:</span><span data-lang="zh">发布期数：</span></label>
        <select id="mom-select-{cc}" class="month-select" onchange="updateMomentumTable('{cc}', this.value)">
          {cpi_month_options}
        </select>
      </div>
    </div>

    <div class="table-responsive">
      <table class="inflation-table" id="table-mom-{cc}">
        <thead>
          <tr class="th-tier1">
            <th class="col-name text-left"><span data-lang="en">Inflation Component</span><span data-lang="zh">通胀分项分组</span></th>
            <th class="col-num"><span data-lang="en">Weights%</span><span data-lang="zh">权重%</span></th>
            <th class="col-num"><span data-lang="en">1M Ann.</span><span data-lang="zh">1M 年化</span></th>
            <th class="col-num"><strong><span data-lang="en">3M Ann.</span><span data-lang="zh">3M 年化</span></strong></th>
            <th class="col-num"><span data-lang="en">6M Ann.</span><span data-lang="zh">6M 年化</span></th>
            <th class="col-num"><span data-lang="en">12M YoY</span><span data-lang="zh">12M 同比</span></th>
            <th class="col-num"><strong><span data-lang="en">Gap (3M - YoY)</span><span data-lang="zh">动量差(3M-同比)</span></strong></th>
            <th class="col-name" style="text-align: center;"><span data-lang="en">Momentum Signal</span><span data-lang="zh">动量研判</span></th>
          </tr>
        </thead>
        <tbody id="tbody-mom-{cc}">
          {_render_momentum_rows(latest_mom_tbl)}
        </tbody>
      </table>
    </div>

    <div class="subchart-container">
      <div class="subchart-header">
        <h4><span data-lang="en">Inflation Momentum Trajectory: 3M Annualized vs 12M YoY</span><span data-lang="zh">通胀短期动量演变轨迹：3个月年化增速 vs 12个月同比</span></h4>
      </div>
      <div id="deepdive-chart-{cc.lower()}-momentum" style="height: 360px; width: 100%;"></div>
    </div>
  </div>

  <!-- ── TAB 3: PPI TABLE ────────────────────────────────────────────────── -->
  <div class="deepdive-tab-content" id="tab-ppi-{cc}">
    <div class="table-toolbar">
      <div class="toolbar-left">
        <span class="table-caption">
          <strong><span data-lang="en">Table 2: Producer Price Index (PPI) by Industry Stage</span><span data-lang="zh">表 2：工业生产者出厂价格指数 (PPI) 分类拆解</span></strong>
        </span>
      </div>
      <div class="toolbar-right">
        <label for="ppi-select-{cc}"><span data-lang="en">Release Print:</span><span data-lang="zh">发布期数：</span></label>
        <select id="ppi-select-{cc}" class="month-select" onchange="updatePpiTable('{cc}', this.value)">
          {cpi_month_options}
        </select>
      </div>
    </div>

    <div class="table-responsive">
      <table class="inflation-table" id="table-ppi-{cc}">
        <thead>
          <tr class="th-tier1">
            <th rowspan="2" class="col-name text-left"><span data-lang="en">Industry Stage / Group</span><span data-lang="zh">工业行业阶段 / 分类</span></th>
            <th rowspan="2" class="col-num"><span data-lang="en">Weights</span><span data-lang="zh">权重%</span></th>
            <th colspan="3" class="col-group-header"><span data-lang="en">y / y</span><span data-lang="zh">同 比 (y/y)</span></th>
            <th colspan="3" class="col-group-header"><span data-lang="en">m / m</span><span data-lang="zh">环 比 (m/m)</span></th>
          </tr>
          <tr class="th-tier2">
            <th class="col-num th-curr-ppi-yoy">{_format_mon_yy(latest_m)}</th>
            <th class="col-num th-prev-ppi-yoy text-muted">{_format_mon_yy(latest_ppi_tbl.get('prev_date', ''))}</th>
            <th class="col-num th-contrib-ppi-yoy"><span data-lang="en">Contrib*<br>to y/y</span><span data-lang="zh">同比贡献*</span></th>
            <th class="col-num th-curr-ppi-mom">{_format_mon_yy(latest_m)}</th>
            <th class="col-num th-ago-ppi-mom text-muted"><span data-lang="en">1Y ago</span><span data-lang="zh">上年同期</span></th>
            <th class="col-num th-contrib-ppi-mom"><span data-lang="en">Contrib*<br>to m/m</span><span data-lang="zh">环比贡献*</span></th>
          </tr>
        </thead>
        <tbody id="tbody-ppi-{cc}">
          {_render_ppi_rows(latest_ppi_tbl)}
        </tbody>
      </table>
    </div>
  </div>

  <!-- ── TAB 4: MARGIN SCISSORS ──────────────────────────────────────────── -->
  <div class="deepdive-tab-content" id="tab-pipeline-{cc}">
    <div class="subchart-container" style="margin-top: 0; border-top: none; padding-top: 0;">
      <div class="subchart-header">
        <h4><span data-lang="en">{country} PPI - CPI Industrial Margin Scissors (pp)</span><span data-lang="zh">{country} PPI - CPI 工业利润剪刀差与价格传导 (百分点)</span></h4>
        <span class="text-muted" style="font-size: 11px;">Spread = PPI YoY - CPI YoY (Positive = Upstream Cost Squeeze; Negative = Downstream Margin Relief)</span>
      </div>
      <div id="deepdive-chart-{cc.lower()}-scissors" style="width: 100%; height: 380px;"></div>
    </div>
  </div>

  <!-- ── TAB 5: EXPECTATIONS ─────────────────────────────────────────────── -->
  <div class="deepdive-tab-content" id="tab-expectations-{cc}">
    <div class="sector-cards-grid">
      {exp_cards_html}
    </div>
  </div>
</div>

<script>
window['EM_CPI_DATA_{cc}'] = {json.dumps(cpi_tables, ensure_ascii=False)};
window['EM_MOM_DATA_{cc}'] = {json.dumps(momentum_tables, ensure_ascii=False)};
window['EM_PPI_DATA_{cc}'] = {json.dumps(ppi_tables, ensure_ascii=False)};

if (typeof toggleSubRows === 'undefined') {{
  window.toggleSubRows = function(groupKey, btn) {{
    var rows = document.querySelectorAll('.sub-' + groupKey);
    var isExpanded = btn.innerText === '▼';
    for (var i = 0; i < rows.length; i++) {{
      rows[i].style.display = isExpanded ? 'none' : 'table-row';
    }}
    btn.innerText = isExpanded ? '▶' : '▼';
  }};
}}

if (typeof switchDeepdiveTab === 'undefined') {{
  window.switchDeepdiveTab = function(geo, tabName, btn) {{
    var parent = document.getElementById('deepdive-inflation-' + geo);
    if (!parent) return;
    var tabs = parent.querySelectorAll('.deepdive-tab');
    for (var i = 0; i < tabs.length; i++) tabs[i].classList.remove('active');
    btn.classList.add('active');

    var contents = parent.querySelectorAll('.deepdive-tab-content');
    for (var j = 0; j < contents.length; j++) contents[j].classList.remove('active');
    var target = document.getElementById('tab-' + tabName + '-' + geo);
    if (target) target.classList.add('active');

    window.dispatchEvent(new Event('resize'));
  }};
}}

function formatMonYy(ymStr) {{
  if (!ymStr || ymStr.length < 7) return ymStr || '';
  var months = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
  var parts = ymStr.split('-');
  if (parts.length < 2) return ymStr;
  var y = parts[0].length >= 4 ? parts[0].slice(2) : parts[0];
  var mIdx = parseInt(parts[1], 10) - 1;
  return (months[mIdx] || parts[1]) + '-' + y;
}}

function updateCpiTable(geo, selectedMonth) {{
  var data = window['EM_CPI_DATA_' + geo];
  if (!data || !data[selectedMonth]) return;
  var tbl = data[selectedMonth];
  var tableEl = document.getElementById('table-cpi-' + geo);
  if (!tableEl) return;

  var thCurrY = tableEl.querySelector('.th-curr-yoy');
  var thPrevY = tableEl.querySelector('.th-prev-yoy');
  var thCurrM = tableEl.querySelector('.th-curr-mom');
  if (thCurrY) thCurrY.innerText = formatMonYy(selectedMonth);
  if (thPrevY) thPrevY.innerText = formatMonYy(tbl.prev_date || '');
  if (thCurrM) thCurrM.innerText = formatMonYy(selectedMonth);

  var tbody = document.getElementById('tbody-cpi-' + geo);
  if (!tbody) return;

  var fmt = function(v, d) {{
    if (v === null || v === undefined) return '—';
    return Number(v).toFixed(d || 1);
  }};

  var h = tbl.headline || {{}};
  var html = '<tr class="row-headline">' +
    '<td class="col-name"><strong>Headline</strong></td>' +
    '<td class="col-num">&nbsp;</td>' +
    '<td class="col-num"><strong>' + fmt(h.yoy) + '</strong></td>' +
    '<td class="col-num text-muted">' + fmt(h.yoy_prev) + '</td>' +
    '<td class="col-num">&nbsp;</td>' +
    '<td class="col-num"><strong>' + fmt(h.mom) + '</strong></td>' +
    '<td class="col-num text-muted">' + fmt(h.mom_ago) + '</td>' +
    '<td class="col-num"><strong>' + fmt(h.contrib_mom) + '</strong></td>' +
    '</tr>';

  (tbl.items || []).forEach(function(it) {{
    var subs = it.sub_items || [];
    var hasSub = subs.length > 0;
    var groupKey = geo + '-' + it.code;
    var btn = hasSub ? '<button class="sub-toggle-btn" onclick="toggleSubRows(\\'' + groupKey + '\\', this)">▶</button>' : '<span class="sub-placeholder"></span>';
    var nameDisp = it.name_en || it.name || it.code;

    html += '<tr class="row-division" data-group="' + groupKey + '">' +
      '<td class="col-name">' + btn + ' <span>' + nameDisp + '</span></td>' +
      '<td class="col-num col-weight">' + fmt(it.weight) + '</td>' +
      '<td class="col-num">' + fmt(it.yoy) + '</td>' +
      '<td class="col-num text-muted">' + fmt(it.yoy_prev) + '</td>' +
      '<td class="col-num">' + fmt(it.contrib_yoy) + '</td>' +
      '<td class="col-num">' + fmt(it.mom) + '</td>' +
      '<td class="col-num text-muted">' + fmt(it.mom_ago) + '</td>' +
      '<td class="col-num">' + fmt(it.contrib_mom) + '</td>' +
      '</tr>';

    if (hasSub) {{
      subs.forEach(function(sub) {{
        var subName = sub.name_en || sub.name || sub.code;
        html += '<tr class="row-subitem sub-' + groupKey + '" style="display: none;">' +
          '<td class="col-name col-sub"><span class="sub-tree-prefix">↳</span> ' + subName + '</td>' +
          '<td class="col-num col-weight text-muted">' + fmt(sub.weight) + '</td>' +
          '<td class="col-num">' + fmt(sub.yoy) + '</td>' +
          '<td class="col-num text-muted">' + fmt(sub.yoy_prev) + '</td>' +
          '<td class="col-num">' + fmt(sub.contrib_yoy) + '</td>' +
          '<td class="col-num">' + fmt(sub.mom) + '</td>' +
          '<td class="col-num text-muted">' + fmt(sub.mom_ago) + '</td>' +
          '<td class="col-num">' + fmt(sub.contrib_mom) + '</td>' +
          '</tr>';
      }});
    }}
  }});

  if (tbl.memo && tbl.memo.length > 0) {{
    html += '<tr class="row-separator"><td colspan="8"></td></tr>';
    tbl.memo.forEach(function(m) {{
      var mName = m.name_en || m.name || m.code;
      html += '<tr class="row-memo">' +
        '<td class="col-name"><span>' + mName + '</span></td>' +
        '<td class="col-num col-weight">' + (m.weight ? fmt(m.weight) : '&nbsp;') + '</td>' +
        '<td class="col-num">' + fmt(m.yoy) + '</td>' +
        '<td class="col-num text-muted">' + fmt(m.yoy_prev) + '</td>' +
        '<td class="col-num">&nbsp;</td>' +
        '<td class="col-num">' + fmt(m.mom) + '</td>' +
        '<td class="col-num text-muted">' + fmt(m.mom_ago) + '</td>' +
        '<td class="col-num">&nbsp;</td>' +
        '</tr>';
    }});
  }}

  tbody.innerHTML = html;
}}

function updateMomentumTable(geo, selectedMonth) {{
  var data = window['EM_MOM_DATA_' + geo];
  if (!data || !data[selectedMonth]) return;
  var tbl = data[selectedMonth];
  var tbody = document.getElementById('tbody-mom-' + geo);
  if (!tbody) return;

  var fmt = function(v, d, signed) {{
    if (v === null || v === undefined) return '—';
    var f = Number(v);
    var prefix = (signed && f > 0) ? '+' : '';
    return prefix + f.toFixed(d || 1);
  }};

  var html = '';
  (tbl.items || []).forEach(function(it) {{
    var isHead = it.code === 'TOTAL' || it.code === 'HEADLINE';
    var rowCls = isHead ? 'row-headline' : 'row-division';
    var gapVal = it.gap;
    var gapCls = (gapVal && gapVal > 0.5) ? 'val-pos' : ((gapVal && gapVal < -0.5) ? 'val-neg' : 'val-neutral');
    var badge = '<span class="status-badge ' + (it.badge || 'badge-neutral') + '">' + (it.icon || '') + ' ' + (it.signal_en || '') + '</span>';
    var nameDisp = it.name_en || it.name || it.code;

    html += '<tr class="' + rowCls + '">' +
      '<td class="col-name"><span>' + nameDisp + '</span></td>' +
      '<td class="col-num col-weight">' + fmt(it.weight) + '</td>' +
      '<td class="col-num">' + fmt(it.mom_1m_ann, 1, true) + '%</td>' +
      '<td class="col-num"><strong>' + fmt(it.mom_3m_ann, 1, true) + '%</strong></td>' +
      '<td class="col-num text-muted">' + fmt(it.mom_6m_ann, 1, true) + '%</td>' +
      '<td class="col-num">' + fmt(it.yoy, 1, true) + '%</td>' +
      '<td class="col-num ' + gapCls + '"><strong>' + fmt(gapVal, 1, true) + ' pp</strong></td>' +
      '<td class="col-name" style="text-align: center;">' + badge + '</td>' +
      '</tr>';
  }});
  tbody.innerHTML = html;
}}

function updatePpiTable(geo, selectedMonth) {{
  var data = window['EM_PPI_DATA_' + geo];
  if (!data || !data[selectedMonth]) return;
  var tbl = data[selectedMonth];
  var tbody = document.getElementById('tbody-ppi-' + geo);
  if (!tbody) return;

  var fmt = function(v, d) {{
    if (v === null || v === undefined) return '—';
    return Number(v).toFixed(d || 1);
  }};

  var head = tbl.headline || {{}};
  var html = '<tr class="row-headline">' +
    '<td class="col-name"><strong>Headline PPI</strong></td>' +
    '<td class="col-num">&nbsp;</td>' +
    '<td class="col-num"><strong>' + fmt(head.yoy) + '</strong></td>' +
    '<td class="col-num text-muted">' + fmt(head.yoy_prev) + '</td>' +
    '<td class="col-num">&nbsp;</td>' +
    '<td class="col-num"><strong>' + fmt(head.mom) + '</strong></td>' +
    '<td class="col-num text-muted">' + fmt(head.mom_ago) + '</td>' +
    '<td class="col-num"><strong>' + fmt(head.contrib_mom) + '</strong></td>' +
    '</tr>';

  (tbl.items || []).forEach(function(it) {{
    var nameDisp = it.name_en || it.name || it.code;
    html += '<tr class="row-division">' +
      '<td class="col-name"><span>' + nameDisp + '</span></td>' +
      '<td class="col-num col-weight">' + fmt(it.weight) + '</td>' +
      '<td class="col-num">' + fmt(it.yoy) + '</td>' +
      '<td class="col-num text-muted">' + fmt(it.yoy_prev) + '</td>' +
      '<td class="col-num">' + fmt(it.contrib_yoy) + '</td>' +
      '<td class="col-num">' + fmt(it.mom) + '</td>' +
      '<td class="col-num text-muted">' + fmt(it.mom_ago) + '</td>' +
      '<td class="col-num">' + fmt(it.contrib_mom) + '</td>' +
      '</tr>';
  }});
  tbody.innerHTML = html;
}}

document.addEventListener("DOMContentLoaded", function() {{
  if (typeof Plotly === "undefined") return;

  // 1. Momentum Trajectory Chart
  var momDiv = document.getElementById("deepdive-chart-{cc.lower()}-momentum");
  if (momDiv) {{
    var mDates = {json.dumps(mom_dates)};
    var mH3 = {json.dumps(mom_h3)};
    var mHY = {json.dumps(mom_hy)};
    var lMDate = mDates.length ? mDates[mDates.length - 1] : '';
    var lH3 = mH3.length ? mH3[mH3.length - 1] : 0;
    var lHY = mHY.length ? mHY[mHY.length - 1] : 0;

    var trH3 = {{
      x: mDates, y: mH3, name: 'Headline 3M Ann. (%)',
      type: 'scatter', mode: 'lines+markers',
      line: {{color: '#2563eb', width: 2.5}}, marker: {{size: 5}}
    }};
    var trHY = {{
      x: mDates, y: mHY, name: 'Headline 12M YoY (%)',
      type: 'scatter', mode: 'lines',
      line: {{color: '#93c5fd', width: 2, dash: 'dot'}}
    }};

    var layoutMom = {{
      height: 360,
      margin: {{l: 45, r: 85, t: 25, b: 35}},
      legend: {{orientation: 'h', y: -0.18}},
      paper_bgcolor: 'rgba(0,0,0,0)',
      plot_bgcolor: 'rgba(0,0,0,0)',
      font: {{family: '-apple-system, BlinkMacSystemFont, Segoe UI, Roboto, sans-serif', size: 11, color: '#12151a'}},
      yaxis: {{title: 'Rate (%)', gridcolor: 'rgba(0,0,0,0.06)', zeroline: true, zerolinecolor: '#333'}},
      annotations: [
        {{
          x: lMDate, y: lH3, xref: 'x', yref: 'y',
          text: '3M Ann: ' + (lH3 > 0 ? '+' : '') + Number(lH3).toFixed(1) + '%',
          showarrow: true, arrowhead: 2, arrowsize: 1, arrowwidth: 1.5, arrowcolor: '#2563eb',
          ax: 35, ay: -18, bgcolor: '#2563eb',
          font: {{color: '#ffffff', size: 10, family: 'monospace', weight: 'bold'}}, borderpad: 3
        }}
      ]
    }};
    Plotly.newPlot(momDiv, [trH3, trHY], layoutMom, {{responsive: true, displayModeBar: false}});
  }}

  // 2. Margin Scissors Chart
  var sciDiv = document.getElementById("deepdive-chart-{cc.lower()}-scissors");
  if (sciDiv) {{
    var sDates = {json.dumps(ts_dates)};
    var sSpread = {json.dumps(ts_spread)};
    var sPpi = {json.dumps(ts_ppi)};
    var sCpi = {json.dumps(ts_cpi)};
    var lSDate = sDates.length ? sDates[sDates.length - 1] : '';
    var lP = sPpi.length ? sPpi[sPpi.length - 1] : 0;
    var lSpr = sSpread.length ? sSpread[sSpread.length - 1] : 0;

    var trPpi = {{
      x: sDates, y: sPpi, name: 'PPI YoY (%)',
      type: 'scatter', mode: 'lines+markers',
      line: {{color: '#6366f1', width: 2.2}}, marker: {{size: 4}}
    }};
    var trCpi = {{
      x: sDates, y: sCpi, name: 'CPI YoY (%)',
      type: 'scatter', mode: 'lines',
      line: {{color: '#b91c1c', width: 2.2}}
    }};
    var trSpread = {{
      x: sDates, y: sSpread, name: 'Scissors Spread (PPI - CPI pp)',
      type: 'bar',
      marker: {{color: sSpread.map(function(v) {{ return v > 0 ? '#10b981' : '#ef4444'; }})}}
    }};

    var layoutSci = {{
      height: 380,
      margin: {{l: 45, r: 85, t: 25, b: 35}},
      legend: {{orientation: 'h', y: -0.18}},
      paper_bgcolor: 'rgba(0,0,0,0)',
      plot_bgcolor: 'rgba(0,0,0,0)',
      font: {{family: '-apple-system, BlinkMacSystemFont, Segoe UI, Roboto, sans-serif', size: 11, color: '#12151a'}},
      yaxis: {{title: 'Rate & Spread (pp)', gridcolor: 'rgba(0,0,0,0.06)', zeroline: true, zerolinecolor: '#333'}},
      annotations: [
        {{
          x: lSDate, y: lP, xref: 'x', yref: 'y',
          text: 'PPI: ' + (lP > 0 ? '+' : '') + Number(lP).toFixed(1) + '%',
          showarrow: true, arrowhead: 2, arrowsize: 1, arrowwidth: 1.5, arrowcolor: '#6366f1',
          ax: 40, ay: -15, bgcolor: '#6366f1',
          font: {{color: '#ffffff', size: 10, family: 'monospace', weight: 'bold'}}, borderpad: 3
        }},
        {{
          x: lSDate, y: lSpr, xref: 'x', yref: 'y',
          text: 'Spread: ' + (lSpr > 0 ? '+' : '') + Number(lSpr).toFixed(1) + 'pp',
          showarrow: true, arrowhead: 2, arrowsize: 1, arrowwidth: 1.5, arrowcolor: '#ef4444',
          ax: 40, ay: 20, bgcolor: '#ef4444',
          font: {{color: '#ffffff', size: 10, family: 'monospace', weight: 'bold'}}, borderpad: 3
        }}
      ]
    }};
    Plotly.newPlot(sciDiv, [trPpi, trCpi, trSpread], layoutSci, {{responsive: true, displayModeBar: false}});
  }}
}});
</script>
"""
    return html_out


if __name__ == "__main__":
    for cc in ["KZ", "UZ", "UK", "JP", "TR", "ZA", "KR", "TW", "EG", "NG", "HK"]:
        out = render_em_deepdive_panel(cc)
        print(f"{cc} rendered length: {len(out):,} chars")
