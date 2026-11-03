"""Renderer for Institutional CEE Inflation & PPI Deep-Dive Modules.

Generates FT / Morgan Stanley institutional-grade interactive HTML components:
- Table 1: CPI Inflation by product group (with collapsible sub-items & month switcher)
- Short-Term Inflation Momentum Monitor (1M, 3M, 6M annualized rates vs 12M YoY & trajectory chart)
- Table 2: PPI Inflation by stage & MIGs (with month switcher)
- PPI - CPI Margin Scissors Pipeline (with spread chart and margin squeeze monitor)
- Pricing Expectations & Capacity Studio (Sector gauge cards, historical percentiles & annotated charts)
- Explicit latest reading callouts across all interactive charts
"""

import json
from pathlib import Path
from html import escape

ROOT = Path(__file__).resolve().parent.parent
OUTPUT = ROOT / "output"

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
.table-badge-secondary {
  font-size: 10px;
  background: #f5f3ff;
  color: #6d28d9;
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
.pipeline-kpi-grid, .momentum-kpi-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 12px;
  margin-bottom: 16px;
}
.pipeline-kpi-card, .momentum-kpi-card {
  background: #f8fafc;
  border: 1px solid var(--border, #e2e8f0);
  border-radius: 6px;
  padding: 14px;
}
.pipeline-kpi-card.highlight-card, .momentum-kpi-card.highlight-card {
  background: #eff6ff;
  border-color: #bfdbfe;
}
.pipeline-kpi-card .kpi-label, .momentum-kpi-card .kpi-label {
  font-size: 11px;
  font-weight: 600;
  color: var(--muted, #64748b);
  margin-bottom: 4px;
}
.pipeline-kpi-card .kpi-val, .momentum-kpi-card .kpi-val {
  font-size: 22px;
  font-weight: 700;
  color: var(--fg, #0f172a);
  font-variant-numeric: tabular-nums;
  line-height: 1.2;
}
.pipeline-kpi-card .kpi-gap, .momentum-kpi-card .kpi-gap {
  color: #2563eb;
}
.pipeline-kpi-card .kpi-subtext, .momentum-kpi-card .kpi-subtext {
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
.pipeline-expl-box {
  background: #f8fafc;
  border: 1px solid var(--border, #e2e8f0);
  border-radius: 6px;
  padding: 12px 14px;
  margin-bottom: 16px;
  font-size: 12px;
  line-height: 1.5;
}
.pipeline-flow-diagram {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 10px;
  flex-wrap: wrap;
}
.flow-step {
  background: #ffffff;
  border: 1px solid var(--border, #cbd5e1);
  border-radius: 4px;
  padding: 4px 8px;
  font-size: 11px;
  font-weight: 600;
  display: inline-flex;
  align-items: center;
}
.flow-num {
  background: #2563eb;
  color: #ffffff;
  border-radius: 50%;
  width: 15px;
  height: 15px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 9px;
  margin-right: 5px;
}
.flow-arrow {
  color: #94a3b8;
  font-size: 11px;
  font-weight: 600;
}

/* Redesigned Pricing Expectations Sector Gauges */
.exp-cards-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
  gap: 14px;
  margin-bottom: 20px;
}
.exp-sector-card {
  background: #ffffff;
  border: 1px solid var(--border, #e2e8f0);
  border-radius: 6px;
  padding: 14px;
  box-shadow: 0 1px 2px rgba(0,0,0,0.02);
  display: flex;
  flex-direction: column;
  justify-content: space-between;
}
.exp-card-header {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  margin-bottom: 10px;
}
.exp-card-icon {
  font-size: 18px;
  line-height: 1;
}
.exp-card-title {
  font-size: 12px;
  font-weight: 700;
  color: var(--fg, #0f172a);
  line-height: 1.3;
}
.exp-card-sub {
  font-size: 10px;
  color: var(--muted, #64748b);
  margin-top: 1px;
}
.exp-card-val-row {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  margin-bottom: 10px;
}
.exp-card-val {
  font-size: 22px;
  font-weight: 700;
  font-family: SFMono-Regular, Menlo, Monaco, Consolas, monospace;
}
.exp-card-trend {
  font-size: 11px;
  font-weight: 600;
  padding: 2px 6px;
  border-radius: 3px;
}
.trend-up {
  background: #fee2e2;
  color: #991b1b;
}
.trend-down {
  background: #dcfce7;
  color: #166534;
}
.trend-flat {
  background: #f1f5f9;
  color: #475569;
}
.exp-meter-track {
  height: 6px;
  background: #f1f5f9;
  border-radius: 3px;
  overflow: hidden;
  position: relative;
  margin-bottom: 6px;
}
.exp-meter-fill {
  height: 100%;
  border-radius: 3px;
  background: linear-gradient(90deg, #3b82f6, #f59e0b, #ef4444);
}
.exp-meter-scale {
  display: flex;
  justify-content: space-between;
  font-size: 10px;
  color: var(--muted, #94a3b8);
  font-family: monospace;
}
.exp-pct-tag {
  font-weight: 700;
  color: #2563eb;
}
.exp-card-takeaway {
  font-size: 11px;
  color: var(--muted, #475569);
  line-height: 1.4;
  margin-top: 10px;
  padding-top: 8px;
  border-top: 1px dashed var(--border, #e2e8f0);
}
</style>
"""


def _format_num(val, decimals=1, signed=False):
    if val is None:
        return "—"
    sign = "+" if signed and val > 0 else ""
    return f"{sign}{val:.{decimals}f}"


def format_mon_yy(ym_str: str) -> str:
    if not ym_str or len(ym_str) < 7:
        return ym_str or ""
    try:
        parts = ym_str.split("-")
        months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
        m_idx = int(parts[1]) - 1
        y = parts[0][2:] if len(parts[0]) >= 4 else parts[0]
        return f"{months[m_idx]}-{y}"
    except Exception:
        return ym_str


def _sign_class(val):
    if val is None:
        return ""
    if val > 0.05:
        return "val-pos"
    if val < -0.05:
        return "val-neg"
    return "val-neutral"


def render_deepdive_panel(country_code: str) -> str:
    """Render the full institutional inflation, momentum, and industrial PPI suite for a CEE country."""
    data_file = OUTPUT / "cee_inflation_deepdive.json"
    if not data_file.exists():
        return ""

    try:
        with open(data_file, "r", encoding="utf-8") as f:
            full_data = json.load(f)
    except Exception:
        return ""

    c_data = full_data.get("countries", {}).get(country_code)
    if not c_data:
        return ""

    cpi_tables = c_data.get("cpi_tables", {})
    ppi_tables = c_data.get("ppi_tables", {})
    mom_tables = c_data.get("momentum_tables", {})
    exp_summary = c_data.get("expectations_summary", {})
    ts = c_data.get("time_series", {})

    if not cpi_tables:
        return ""

    sorted_cpi_months = sorted(list(cpi_tables.keys()), reverse=True)
    latest_cpi_month = sorted_cpi_months[0]
    latest_cpi_tbl = cpi_tables[latest_cpi_month]

    sorted_ppi_months = sorted(list(ppi_tables.keys()), reverse=True)
    latest_ppi_month = sorted_ppi_months[0] if sorted_ppi_months else latest_cpi_month
    latest_ppi_tbl = ppi_tables.get(latest_ppi_month, {})

    sorted_mom_months = sorted(list(mom_tables.keys()), reverse=True)
    latest_mom_month = sorted_mom_months[0] if sorted_mom_months else latest_cpi_month
    latest_mom_tbl = mom_tables.get(latest_mom_month, {})

    # Momentum KPIs
    head_ann_3m = latest_mom_tbl.get("headline_ann_3m")
    head_yoy = latest_mom_tbl.get("headline_yoy")
    head_gap = latest_mom_tbl.get("headline_gap")
    core_ann_3m = latest_mom_tbl.get("core_ann_3m")
    core_yoy = latest_mom_tbl.get("core_yoy")
    core_gap = latest_mom_tbl.get("core_gap")

    # Scissors Gap Metric
    latest_gap_val = None
    if ts.get("ppi_cpi_scissors_gap"):
        latest_gap_val = ts["ppi_cpi_scissors_gap"][-1].get("value")

    latest_ppi_head = None
    if ts.get("ppi_domestic_yoy"):
        latest_ppi_head = ts["ppi_domestic_yoy"][-1].get("value")

    latest_cpi_head = latest_cpi_tbl.get("headline", {}).get("yoy")

    if latest_gap_val is not None:
        gap_sign = "+" if latest_gap_val > 0 else ""
        gap_str = f"{gap_sign}{latest_gap_val:.2f} pp"
        if latest_gap_val > 0.5:
            gap_badge = '<span class="status-badge badge-squeeze"><span data-lang="en">Margin Squeeze (PPI > CPI)</span><span data-lang="zh">毛利挤压 (PPI > CPI)</span></span>'
            gap_expl_en = "Upstream industrial prices are rising faster than consumer prices. Manufacturers face gross margin compression as input costs cannot be fully passed through."
            gap_expl_zh = "上游工业生产者价格涨幅显著高于消费物价，下游无法全额转嫁成本，工业企业毛利率面临压缩。"
        elif latest_gap_val < -0.5:
            gap_badge = '<span class="status-badge badge-expand"><span data-lang="en">Margin Expansion (PPI < CPI)</span><span data-lang="zh">毛利扩张 (PPI < CPI)</span></span>'
            gap_expl_en = "Upstream input costs are disinflating faster than retail prices. Manufacturers and distributors benefit from profit repair."
            gap_expl_zh = "上游工业原料及能源降温快于终端零售价，中下游工业企业与分销商享受成本红利与利润重估。"
        else:
            gap_badge = '<span class="status-badge badge-neutral"><span data-lang="en">Balanced Pipeline (PPI ≈ CPI)</span><span data-lang="zh">传导平衡 (PPI ≈ CPI)</span></span>'
            gap_expl_en = "Industrial price changes are roughly aligned with retail inflation."
            gap_expl_zh = "工业出厂端与消费物价端涨幅基本持平，成本传导处于常态均衡。"
    else:
        gap_str = "—"
        gap_badge = ""
        gap_expl_en = ""
        gap_expl_zh = ""

    # Build CPI Table Rows HTML
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
            has_sub = bool(it.get("sub_items"))
            toggle_btn = f'<button class="sub-toggle-btn" onclick="toggleSubRows(\'{country_code}-{it["code"]}\', this)">▶</button>' if has_sub else '<span class="sub-placeholder"></span>'

            row = f"""
            <tr class="row-division" data-group="{country_code}-{it['code']}">
              <td class="col-name">{toggle_btn} <span>{escape(it['name'])}</span></td>
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

            # Sub-items
            if has_sub:
                for sub in it["sub_items"]:
                    sub_row = f"""
                    <tr class="row-subitem sub-{country_code}-{it['code']}" style="display: none;">
                      <td class="col-name col-sub"><span class="sub-tree-prefix">↳</span> {escape(sub['name'])}</td>
                      <td class="col-num col-weight text-muted">{_format_num(sub.get('weight'), 2)}</td>
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
            m_row = f"""
            <tr class="row-memo">
              <td class="col-name"><span>{escape(m['name'])}</span></td>
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

        return h_html + "\n".join(items_html) + """<tr class="row-separator"><td colspan="8"></td></tr>""" + "\n".join(memo_html)

    # Build Momentum Table Rows HTML
    def _render_momentum_rows(tbl):
        if not tbl:
            return ""
        rows_html = []
        for it in tbl.get("items", []):
            is_head = it["code"] == "TOTAL"
            row_cls = "row-headline" if is_head else "row-division"
            gap_val = it.get("gap")
            gap_cls = "val-pos" if gap_val and gap_val > 0.5 else ("val-neg" if gap_val and gap_val < -0.5 else "val-neutral")
            badge = f'<span class="status-badge {it.get("badge", "badge-neutral")}">{it.get("icon", "")} <span data-lang="en">{it.get("signal_en", "")}</span><span data-lang="zh">{it.get("signal_zh", "")}</span></span>'

            row = f"""
            <tr class="{row_cls}">
              <td class="col-name"><span><span data-lang="en">{escape(it['name_en'])}</span><span data-lang="zh">{escape(it['name_zh'])}</span></span></td>
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

    # Build PPI Table Rows HTML
    def _render_ppi_rows(tbl):
        if not tbl:
            return ""
        head = tbl.get("headline", {})
        h_html = f"""
        <tr class="row-headline">
          <td class="col-name"><strong>Headline PPI (Domestic Market)</strong></td>
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
            row = f"""
            <tr class="row-division">
              <td class="col-name"><span>{escape(it['name'])}</span></td>
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

        memo_html = []
        for m in tbl.get("memo", []):
            m_row = f"""
            <tr class="row-memo">
              <td class="col-name"><span>{escape(m['name'])}</span></td>
              <td class="col-num col-weight">&nbsp;</td>
              <td class="col-num">{_format_num(m.get('yoy'))}</td>
              <td class="col-num text-muted">{_format_num(m.get('yoy_prev'))}</td>
              <td class="col-num">&nbsp;</td>
              <td class="col-num">{_format_num(m.get('mom'))}</td>
              <td class="col-num text-muted">{_format_num(m.get('mom_ago'))}</td>
              <td class="col-num">&nbsp;</td>
            </tr>
            """
            memo_html.append(m_row)

        return h_html + "\n".join(items_html) + """<tr class="row-separator"><td colspan="8"></td></tr>""" + "\n".join(memo_html)

    # Prepare month options for select dropdown
    cpi_month_options = "\n".join([
        f'<option value="{m}" {"selected" if m == latest_cpi_month else ""}>{m} {"(Latest)" if m == latest_cpi_month else ""}</option>'
        for m in sorted_cpi_months
    ])
    mom_month_options = "\n".join([
        f'<option value="{m}" {"selected" if m == latest_mom_month else ""}>{m} {"(Latest)" if m == latest_mom_month else ""}</option>'
        for m in sorted_mom_months
    ])
    ppi_month_options = "\n".join([
        f'<option value="{m}" {"selected" if m == latest_ppi_month else ""}>{m} {"(Latest)" if m == latest_ppi_month else ""}</option>'
        for m in sorted_ppi_months
    ])

    # Serialized JSON data for dynamic client-side month switching (compacted)
    cpi_json_str = json.dumps(cpi_tables, ensure_ascii=False, separators=(",", ":"))
    mom_json_str = json.dumps(mom_tables, ensure_ascii=False, separators=(",", ":"))
    ppi_json_str = json.dumps(ppi_tables, ensure_ascii=False, separators=(",", ":"))

    # 4-Component historical time series data for Plotly stacked chart
    cf_dates = [o["date"] for o in ts.get("cpi_contrib_food_yoy", [])]
    cf_vals = [o["value"] for o in ts.get("cpi_contrib_food_yoy", [])]
    cg_vals = [o["value"] for o in ts.get("cpi_contrib_goods_yoy", [])]
    ce_vals = [o["value"] for o in ts.get("cpi_contrib_energy_yoy", [])]
    cs_vals = [o["value"] for o in ts.get("cpi_contrib_services_yoy", [])]

    # Momentum series for Trajectory chart
    mom_dates = [o["date"] for o in ts.get("cpi_head_3m_ann", [])]
    mom_head_3m = [o["value"] for o in ts.get("cpi_head_3m_ann", [])]
    mom_head_yoy = [o["value"] for o in ts.get("cpi_head_12m_yoy", [])]
    mom_core_3m = [o["value"] for o in ts.get("cpi_core_3m_ann", [])]
    mom_core_yoy = [o["value"] for o in ts.get("cpi_core_12m_yoy", [])]

    # Scissors Gap time series
    sg_dates = [o["date"] for o in ts.get("ppi_cpi_scissors_gap", [])]
    sg_vals = [o["value"] for o in ts.get("ppi_cpi_scissors_gap", [])]
    ppi_head_vals = [o["value"] for o in ts.get("ppi_domestic_yoy", [])]

    # Expectations series
    exp_dates = [o["date"] for o in ts.get("exp_industry_3m", [])]
    exp_ind_vals = [o["value"] for o in ts.get("exp_industry_3m", [])]
    exp_srv_vals = [o["value"] for o in ts.get("exp_services_3m", [])]
    exp_ret_vals = [o["value"] for o in ts.get("exp_retail_3m", [])]
    exp_cns_vals = [o["value"] for o in ts.get("exp_consumer_12m", [])]
    cu_dates = [o["date"] for o in ts.get("capacity_utilization", [])]
    cu_vals = [o["value"] for o in ts.get("capacity_utilization", [])]

    def _lw_pts(d_list, v_list, *, is_bar=False):
        pts = {}
        for d, v in zip(d_list, v_list):
            if v is None:
                continue
            ds = str(d)
            if len(ds) == 7:
                ds = f"{ds}-01"
            elif len(ds) == 4:
                ds = f"{ds}-12-31"
            else:
                ds = ds[:10]
            val = round(float(v), 3)
            pt = {"time": ds, "value": val}
            if is_bar:
                pt["color"] = "#0d7680" if val >= 0 else "#990f3d"
            pts[ds] = pt
        return [pts[k] for k in sorted(pts)]

    head_sum_vals = [
        round((f or 0) + (g or 0) + (e or 0) + (s or 0), 2)
        for f, g, e, s in zip(cf_vals, cg_vals, ce_vals, cs_vals)
    ]
    target_bands = {
        "PL": {"center": 2.5, "min": 1.5, "max": 3.5, "label": "NBP Target: 2.5% (1.5%–3.5% band)"},
        "CZ": {"center": 2.0, "min": 1.0, "max": 3.0, "label": "CNB Target: 2.0% (1.0%–3.0% band)"},
        "HU": {"center": 3.0, "min": 2.0, "max": 4.0, "label": "MNB Target: 3.0% (2.0%–4.0% band)"},
        "RO": {"center": 2.5, "min": 1.5, "max": 3.5, "label": "NBR Target: 2.5% (1.5%–3.5% band)"},
        "EA": {"center": 2.0, "min": None, "max": None, "label": "ECB Target: 2.0%"},
    }
    t_band = target_bands.get(country_code, {"center": 2.0, "min": None, "max": None, "label": "Inflation Target: 2.0%"})
    mom_price_lines = []
    if t_band.get("max") is not None:
        mom_price_lines.append({"price": t_band["max"], "color": "rgba(13, 118, 128, 0.55)", "width": 1, "style": 3, "title": f"Upper {t_band['max']:g}%", "axisLabel": False})
    if t_band.get("center") is not None:
        mom_price_lines.append({"price": t_band["center"], "color": "#0d7680", "width": 2, "style": 2, "title": f"Target {t_band['center']:g}%", "axisLabel": False})
    if t_band.get("min") is not None:
        mom_price_lines.append({"price": t_band["min"], "color": "rgba(13, 118, 128, 0.55)", "width": 1, "style": 3, "title": f"Lower {t_band['min']:g}%", "axisLabel": False})
    mom_price_lines.append({"price": 0.0, "color": "rgba(18, 21, 26, 0.35)", "width": 1, "style": 0, "title": "", "axisLabel": False})

    lw_deepdive_specs = {
        f"deepdive-chart-cpi-contrib-{country_code}": {
            "title": "CPI Component Contributions",
            "unit": "pp",
            "series": [
                {"name": "Headline YoY", "type": "line", "color": "#12151a", "width": 2, "style": 0, "isPrimary": True, "data": _lw_pts(cf_dates, head_sum_vals)},
                {"name": "Services (服务)", "type": "line", "color": "#10b981", "width": 2, "style": 0, "data": _lw_pts(cf_dates, cs_vals)},
                {"name": "Food (食品)", "type": "line", "color": "#f59e0b", "width": 2, "style": 0, "data": _lw_pts(cf_dates, cf_vals)},
                {"name": "Energy (能源)", "type": "line", "color": "#ef4444", "width": 2, "style": 0, "data": _lw_pts(cf_dates, ce_vals)},
                {"name": "Goods (商品)", "type": "line", "color": "#3b82f6", "width": 2, "style": 0, "data": _lw_pts(cf_dates, cg_vals)},
            ],
            "priceLines": [{"price": 0.0, "color": "rgba(18, 21, 26, 0.40)", "width": 1, "style": 0, "title": "", "axisLabel": False}],
        },
        f"deepdive-chart-momentum-{country_code}": {
            "title": "Inflation Momentum Trajectory",
            "unit": "%",
            "badge": {"text": t_band["label"], "color": "#0d7680", "bg": "rgba(13, 118, 128, 0.10)"},
            "series": [
                {"name": "Headline 3M Ann.", "type": "line", "color": "#1e3a8a", "width": 2, "style": 0, "isPrimary": True, "data": _lw_pts(mom_dates, mom_head_3m)},
                {"name": "Headline 12M YoY", "type": "line", "color": "#64748b", "width": 2, "style": 2, "data": _lw_pts(mom_dates, mom_head_yoy)},
                {"name": "Core 3M Ann.", "type": "line", "color": "#990f3d", "width": 2, "style": 0, "data": _lw_pts(mom_dates, mom_core_3m)},
                {"name": "Core 12M YoY", "type": "line", "color": "#f43f5e", "width": 2, "style": 1, "data": _lw_pts(mom_dates, mom_core_yoy)},
            ],
            "priceLines": mom_price_lines,
        },
        f"deepdive-chart-scissors-gap-{country_code}": {
            "title": "PPI vs CPI Margin Scissors",
            "unit": "pp / %",
            "series": [
                {"name": "Scissors Gap (PPI - CPI)", "type": "histogram", "color": "#0d7680", "data": _lw_pts(sg_dates, sg_vals, is_bar=True)},
                {"name": "Domestic PPI YoY", "type": "line", "color": "#6366f1", "width": 2, "style": 0, "isPrimary": True, "data": _lw_pts(sg_dates, ppi_head_vals)},
            ],
            "priceLines": [{"price": 0.0, "color": "rgba(18, 21, 26, 0.40)", "width": 1, "style": 0, "title": "", "axisLabel": False}],
        },
        f"deepdive-chart-expectations-{country_code}": {
            "title": "Pricing Expectations & Capacity Utilization",
            "unit": "Net Bal %",
            "badge": {"text": "Right Scale: Capacity Util (%)", "color": "#7c3aed", "bg": "rgba(124, 58, 237, 0.08)"},
            "series": [
                {"name": "Industry 3M Exp", "type": "line", "color": "#2563eb", "width": 2, "style": 0, "scale": "left", "isPrimary": True, "data": _lw_pts(exp_dates, exp_ind_vals)},
                {"name": "Services 3M Exp", "type": "line", "color": "#059669", "width": 2, "style": 0, "scale": "left", "data": _lw_pts(exp_dates, exp_srv_vals)},
                {"name": "Retail 3M Exp", "type": "line", "color": "#d97706", "width": 2, "style": 0, "scale": "left", "data": _lw_pts(exp_dates, exp_ret_vals)},
                {"name": "Consumer 12M Exp", "type": "line", "color": "#dc2626", "width": 2, "style": 1, "scale": "left", "data": _lw_pts(exp_dates, exp_cns_vals)},
                {"name": "Capacity Util (%) [R]", "type": "line", "color": "#7c3aed", "width": 2, "style": 0, "scale": "right", "data": _lw_pts(cu_dates, cu_vals)},
            ],
            "priceLines": [{"price": 0.0, "color": "rgba(18, 21, 26, 0.35)", "width": 1, "style": 1, "title": "", "axisLabel": False}],
        },
    }
    deepdive_chart_init_js = (
        "window.CP_LW_CHARTS = Object.assign(window.CP_LW_CHARTS || {}, "
        + json.dumps(lw_deepdive_specs, ensure_ascii=False, separators=(",", ":"))
        + ");"
    )

    # Build Sector Expectations Cards HTML
    exp_cards_html = []
    for s_key in ["exp_industry_3m", "exp_services_3m", "exp_retail_3m", "exp_consumer_12m", "capacity_utilization"]:
        s_data = exp_summary.get(s_key, {})
        if not s_data:
            continue
        cur = s_data.get("current", 0.0)
        diff3 = s_data.get("diff_3m", 0.0)
        pct = s_data.get("pct", 50)
        val_str = f"{cur:+.1f}" if s_key != "capacity_utilization" else f"{cur:.1f}%"
        trend_cls = "trend-up" if diff3 > 1.0 else ("trend-down" if diff3 < -1.0 else "trend-flat")
        trend_sign = "+" if diff3 > 0 else ""
        trend_arrow = "▲" if diff3 > 0.5 else ("▼" if diff3 < -0.5 else "▬")
        trend_str = f"{trend_arrow} {trend_sign}{diff3:.1f} pts vs 3M"

        card = f"""
        <div class="exp-sector-card">
          <div class="exp-card-header">
            <span class="exp-card-icon">{s_data.get('icon', '📊')}</span>
            <div>
              <div class="exp-card-title"><span data-lang="en">{s_data.get('label_en')}</span><span data-lang="zh">{s_data.get('label_zh')}</span></div>
              <div class="exp-card-sub">{s_data.get('unit')}</div>
            </div>
          </div>
          <div class="exp-card-val-row">
            <span class="exp-card-val">{val_str}</span>
            <span class="exp-card-trend {trend_cls}">{trend_str}</span>
          </div>
          <div class="exp-meter-track">
            <div class="exp-meter-fill" style="width: {pct}%;"></div>
          </div>
          <div class="exp-meter-scale">
            <span>Min: {s_data.get('min', 0):.1f}</span>
            <span class="exp-pct-tag"><span data-lang="en">{pct}% Percentile · {s_data.get('regime_en')}</span><span data-lang="zh">{pct}% 历史分位 · {s_data.get('regime_zh')}</span></span>
            <span>Max: {s_data.get('max', 100):.1f}</span>
          </div>
          <div class="exp-card-takeaway">
            <span data-lang="en">{s_data.get('takeaway_en')}</span>
            <span data-lang="zh">{s_data.get('takeaway_zh')}</span>
          </div>
        </div>
        """
        exp_cards_html.append(card)

    html_out = f"""{DEEPDIVE_CSS}
<!-- ══════════════════════════════════════════════════════════════════════════ -->
<!-- INSTITUTIONAL INFLATION, MOMENTUM & INDUSTRIAL PRICING STUDIO             -->
<!-- ══════════════════════════════════════════════════════════════════════════ -->
<div class="deepdive-macro-panel" id="deepdive-inflation-{country_code}">
  <div class="deepdive-header">
    <div class="deepdive-title-wrap">
      <span class="deepdive-badge"><span data-lang="en">INSTITUTIONAL SUITE</span><span data-lang="zh">机构级通胀与工业物价工坊</span></span>
      <h3 class="deepdive-title"><span data-lang="en">Inflation Decomposition, Momentum & Pricing Studio</span><span data-lang="zh">通胀分项贡献、短期动量与工业定价工坊</span></h3>
      <p class="deepdive-subtitle">
        <span data-lang="en">Institutional disaggregation across 12 COICOP divisions, 1M/3M/6M annualized momentum, 5 PPI MIGs, margin scissors pipeline & forward pricing expectations.</span>
        <span data-lang="zh">12大消费类目贡献拆解、1M/3M/6M短期通胀动量年化监控、5大工业分组(MIGs)、利润剪刀差传导链与多行业提价意向全景。</span>
      </p>
    </div>
    <div class="deepdive-tabs">
      <button class="deepdive-tab active" onclick="switchDeepdiveTab('{country_code}', 'cpi', this)">
        <span data-lang="en">Table 1: CPI Breakdown</span><span data-lang="zh">表1：CPI分项贡献</span>
      </button>
      <button class="deepdive-tab" onclick="switchDeepdiveTab('{country_code}', 'momentum', this)">
        <span data-lang="en">Short-Term Momentum</span><span data-lang="zh">通胀短期动量监控</span>
      </button>
      <button class="deepdive-tab" onclick="switchDeepdiveTab('{country_code}', 'ppi', this)">
        <span data-lang="en">Table 2: PPI & MIGs</span><span data-lang="zh">表2：PPI工业分组</span>
      </button>
      <button class="deepdive-tab" onclick="switchDeepdiveTab('{country_code}', 'pipeline', this)">
        <span data-lang="en">Margin Scissors & Pipeline</span><span data-lang="zh">传导链与利润剪刀差</span>
      </button>
      <button class="deepdive-tab" onclick="switchDeepdiveTab('{country_code}', 'expectations', this)">
        <span data-lang="en">Pricing Expectations</span><span data-lang="zh">行业提价意向与产能</span>
      </button>
    </div>
  </div>

  <!-- ── TAB 1: CPI TABLE ────────────────────────────────────────────────── -->
  <div class="deepdive-tab-content active" id="tab-cpi-{country_code}">
    <div class="table-toolbar">
      <div class="toolbar-left">
        <span class="table-caption">
          <strong><span data-lang="en">Table 1: CPI Inflation by product group</span><span data-lang="zh">表 1：CPI 分项通胀与贡献拆解</span></strong>
        </span>
      </div>
      <div class="toolbar-right">
        <label for="cpi-select-{country_code}"><span data-lang="en">Release Print:</span><span data-lang="zh">发布期数：</span></label>
        <select id="cpi-select-{country_code}" class="month-select" onchange="updateCpiTable('{country_code}', this.value)">
          {cpi_month_options}
        </select>
      </div>
    </div>

    <div class="table-responsive">
      <table class="inflation-table" id="table-cpi-{country_code}">
        <thead>
          <tr class="th-tier1">
            <th rowspan="2" class="col-name text-left"><span data-lang="en">&nbsp;</span><span data-lang="zh">&nbsp;</span></th>
            <th rowspan="2" class="col-num"><span data-lang="en">Weights</span><span data-lang="zh">权重%</span></th>
            <th colspan="3" class="col-group-header"><span data-lang="en">y / y</span><span data-lang="zh">同 比 (y/y)</span></th>
            <th colspan="3" class="col-group-header"><span data-lang="en">m / m</span><span data-lang="zh">环 比 (m/m)</span></th>
          </tr>
          <tr class="th-tier2">
            <th class="col-num th-curr-yoy">{format_mon_yy(latest_cpi_month)}</th>
            <th class="col-num th-prev-yoy text-muted">{format_mon_yy(latest_cpi_tbl.get('prev_date', ''))}</th>
            <th class="col-num th-contrib-yoy"><span data-lang="en">Contrib*<br>to y/y</span><span data-lang="zh">同比贡献*</span></th>
            <th class="col-num th-curr-mom">{format_mon_yy(latest_cpi_month)}</th>
            <th class="col-num th-ago-mom text-muted"><span data-lang="en">1Y ago</span><span data-lang="zh">去年同期</span></th>
            <th class="col-num th-contrib-mom"><span data-lang="en">Contrib*<br>to m/m</span><span data-lang="zh">环比贡献*</span></th>
          </tr>
        </thead>
        <tbody id="tbody-cpi-{country_code}">
          {_render_cpi_rows(latest_cpi_tbl)}
        </tbody>
      </table>
    </div>
    <div class="table-footnote">
      <span data-lang="en">*Methodology: Contribution to y/y and m/m inflation calculated using Eurostat HICP item weights and chain-linked price relatives (percentage points). Memo aggregates do not sum to headline. Source: Eurostat prc_hicp_minr / prc_hicp_iw.</span>
      <span data-lang="zh">*编制方法：同比与环比通胀贡献度基于 Eurostat HICP 分项权重与链式价格指数测算（单位：百分点）。核心等汇总项为重叠分类不参与加总。数据源：Eurostat prc_hicp_minr / prc_hicp_iw。</span>
    </div>

    <!-- Stacked Historical Contribution Chart -->
    <div class="subchart-container">
      <div class="subchart-header" style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px;">
        <h4><span data-lang="en">Historical CPI Component Contributions (2022–2026)</span><span data-lang="zh">CPI 四大类贡献历史演变趋势 (2022–2026)</span></h4>
        <div class="lw-chart-meta" id="lw-meta-deepdive-chart-cpi-contrib-{country_code}"></div>
      </div>
      <div id="deepdive-chart-cpi-contrib-{country_code}" class="lw-chart-plot" data-lw-chart="deepdive-chart-cpi-contrib-{country_code}" style="height: 350px; width: 100%;"></div>
    </div>
  </div>

  <!-- ── TAB 2: SHORT-TERM INFLATION MOMENTUM ─────────────────────────────── -->
  <div class="deepdive-tab-content" id="tab-momentum-{country_code}">
    <div class="momentum-kpi-grid">
      <div class="momentum-kpi-card highlight-card">
        <div class="kpi-label"><span data-lang="en">Headline 3M Annualized (Compounded)</span><span data-lang="zh">整体调和 CPI 3个月年化增速</span></div>
        <div class="kpi-val" id="kpi-mom-head-val-{country_code}">{_format_num(head_ann_3m, 1, signed=True)}%</div>
        <div class="kpi-subtext" id="kpi-mom-head-sub-{country_code}">
          <span data-lang="en">vs 12M YoY: <strong>{_format_num(head_yoy, 1)}%</strong> | Momentum Spread: <strong>{_format_num(head_gap, 1, signed=True)} pp</strong></span>
          <span data-lang="zh">对比 12M 同比: <strong>{_format_num(head_yoy, 1)}%</strong> | 动量差值: <strong>{_format_num(head_gap, 1, signed=True)} pp</strong></span>
        </div>
      </div>
      <div class="momentum-kpi-card">
        <div class="kpi-label"><span data-lang="en">Core 3M Annualized (ex-Food & Energy)</span><span data-lang="zh">核心 CPI 3个月年化增速 (剔食品能源)</span></div>
        <div class="kpi-val" id="kpi-mom-core-val-{country_code}">{_format_num(core_ann_3m, 1, signed=True)}%</div>
        <div class="kpi-subtext" id="kpi-mom-core-sub-{country_code}">
          <span data-lang="en">vs Core YoY: <strong>{_format_num(core_yoy, 1)}%</strong> | Core Spread: <strong>{_format_num(core_gap, 1, signed=True)} pp</strong></span>
          <span data-lang="zh">对比核心同比: <strong>{_format_num(core_yoy, 1)}%</strong> | 核心动量差: <strong>{_format_num(core_gap, 1, signed=True)} pp</strong></span>
        </div>
      </div>
      <div class="momentum-kpi-card">
        <div class="kpi-label"><span data-lang="en">Momentum Regime Verdict</span><span data-lang="zh">短期通胀动量研判结论</span></div>
        <div class="kpi-val" style="font-size: 16px; margin-top: 4px;">
          <span class="status-badge {'badge-squeeze' if head_gap and head_gap > 1.0 else ('badge-expand' if head_gap and head_gap < -0.2 else 'badge-neutral')}">
            <span data-lang="en">{latest_mom_tbl.get('headline_signal_en', 'Stable')}</span>
            <span data-lang="zh">{latest_mom_tbl.get('headline_signal_zh', '常态平稳')}</span>
          </span>
        </div>
        <div class="kpi-subtext">
          <span data-lang="en">3M annualized pace leads YoY inflation by ~1-2 quarters by filtering out 12M base effects.</span>
          <span data-lang="zh">3个月年化增速剔除过去12个月高基数扰动，领先同比指标约1至2个季度反映最新通胀动量。</span>
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
        <label for="mom-select-{country_code}"><span data-lang="en">Release Print:</span><span data-lang="zh">发布期数：</span></label>
        <select id="mom-select-{country_code}" class="month-select" onchange="updateMomentumTable('{country_code}', this.value)">
          {mom_month_options}
        </select>
      </div>
    </div>

    <div class="table-responsive">
      <table class="inflation-table" id="table-mom-{country_code}">
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
        <tbody id="tbody-mom-{country_code}">
          {_render_momentum_rows(latest_mom_tbl)}
        </tbody>
      </table>
    </div>
    <div class="table-footnote">
      <span data-lang="en">*Methodology: 1M annualized = (1+m)^12 - 1; 3M annualized = (prod(1+m_i))^4 - 1; 6M annualized = (prod(1+m_i))^2 - 1. Gap = 3M Ann - 12M YoY. Source: Eurostat prc_hicp_minr.</span>
      <span data-lang="zh">*计算口径：1M 年化 = (1+m)^12 - 1；3M 年化 = (∏(1+m_i))^4 - 1；6M 年化 = (∏(1+m_i))^2 - 1。动量差值 = 3M年化增速 - 12M同比。数据源：Eurostat prc_hicp_minr。</span>
    </div>

    <!-- Momentum Trajectory Chart -->
    <div class="subchart-container">
      <div class="subchart-header" style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px;">
        <h4><span data-lang="en">Inflation Momentum Trajectory: 3M Annualized vs 12M YoY (2022–2026)</span><span data-lang="zh">通胀短期动量演变轨迹：3个月年化增速 vs 12个月同比 (2022–2026)</span></h4>
        <div class="lw-chart-meta" id="lw-meta-deepdive-chart-momentum-{country_code}"></div>
      </div>
      <div id="deepdive-chart-momentum-{country_code}" class="lw-chart-plot" data-lw-chart="deepdive-chart-momentum-{country_code}" style="height: 380px; width: 100%;"></div>
    </div>
  </div>

  <!-- ── TAB 3: PPI TABLE ────────────────────────────────────────────────── -->
  <div class="deepdive-tab-content" id="tab-ppi-{country_code}">
    <div class="table-toolbar">
      <div class="toolbar-left">
        <span class="table-caption">
          <strong><span data-lang="en">Table 2: PPI Inflation by MIG division (Domestic Market)</span><span data-lang="zh">表 2：工业品出厂价格阶段与分组矩阵 (MIGs)</span></strong>
        </span>
      </div>
      <div class="toolbar-right">
        <label for="ppi-select-{country_code}"><span data-lang="en">Release Print:</span><span data-lang="zh">发布期数：</span></label>
        <select id="ppi-select-{country_code}" class="month-select" onchange="updatePpiTable('{country_code}', this.value)">
          {ppi_month_options}
        </select>
      </div>
    </div>

    <div class="table-responsive">
      <table class="inflation-table" id="table-ppi-{country_code}">
        <thead>
          <tr class="th-tier1">
            <th rowspan="2" class="col-name text-left"><span data-lang="en">&nbsp;</span><span data-lang="zh">&nbsp;</span></th>
            <th rowspan="2" class="col-num"><span data-lang="en">Weights</span><span data-lang="zh">权重%</span></th>
            <th colspan="3" class="col-group-header"><span data-lang="en">y / y</span><span data-lang="zh">同 比 (y/y)</span></th>
            <th colspan="3" class="col-group-header"><span data-lang="en">m / m</span><span data-lang="zh">环 比 (m/m)</span></th>
          </tr>
          <tr class="th-tier2">
            <th class="col-num th-curr-ppi-yoy">{format_mon_yy(latest_ppi_month)}</th>
            <th class="col-num th-prev-ppi-yoy text-muted">{format_mon_yy(latest_ppi_tbl.get('prev_date', ''))}</th>
            <th class="col-num th-contrib-ppi-yoy"><span data-lang="en">Contrib*<br>to y/y</span><span data-lang="zh">同比贡献*</span></th>
            <th class="col-num th-curr-ppi-mom">{format_mon_yy(latest_ppi_month)}</th>
            <th class="col-num th-ago-ppi-mom text-muted"><span data-lang="en">1Y ago</span><span data-lang="zh">去年同期</span></th>
            <th class="col-num th-contrib-ppi-mom"><span data-lang="en">Contrib*<br>to m/m</span><span data-lang="zh">环比贡献*</span></th>
          </tr>
        </thead>
        <tbody id="tbody-ppi-{country_code}">
          {_render_ppi_rows(latest_ppi_tbl)}
        </tbody>
      </table>
    </div>
    <div class="table-footnote">
      <span data-lang="en">*Methodology: Percentage-point contributions sum up to Headline Domestic PPI (B-E36). Source: Eurostat sts_inppd_m.</span>
      <span data-lang="zh">*编制方法：百分点贡献加总严格恒等于国内工业品出厂 PPI（B-E36）。数据源：Eurostat sts_inppd_m。</span>
    </div>
  </div>

  <!-- ── TAB 4: MARGIN SCISSORS & PIPELINE ───────────────────────────────── -->
  <div class="deepdive-tab-content" id="tab-pipeline-{country_code}">
    <div class="pipeline-kpi-grid">
      <div class="pipeline-kpi-card">
        <div class="kpi-label"><span data-lang="en">Domestic PPI (YoY)</span><span data-lang="zh">国内工业品 PPI (同比)</span></div>
        <div class="kpi-val">{_format_num(latest_ppi_head, signed=True)}%</div>
        <div class="kpi-subtext"><span data-lang="en">Upstream industrial pressure</span><span data-lang="zh">上游工业出厂物价</span></div>
      </div>
      <div class="pipeline-kpi-card">
        <div class="kpi-label"><span data-lang="en">Headline CPI (YoY)</span><span data-lang="zh">整体居民 CPI (同比)</span></div>
        <div class="kpi-val">{_format_num(latest_cpi_head, signed=True)}%</div>
        <div class="kpi-subtext"><span data-lang="en">Downstream consumer inflation</span><span data-lang="zh">终端消费物价</span></div>
      </div>
      <div class="pipeline-kpi-card highlight-card">
        <div class="kpi-label"><span data-lang="en">PPI - CPI Margin Scissors (Δ)</span><span data-lang="zh">PPI - CPI 利润剪刀差 (Δ)</span></div>
        <div class="kpi-val kpi-gap">{gap_str}</div>
        <div class="kpi-subtext">{gap_badge}</div>
      </div>
    </div>

    <div class="pipeline-expl-box">
      <p><span data-lang="en"><strong>Economic Mechanism:</strong> {gap_expl_en}</span><span data-lang="zh"><strong>经济学机制：</strong>{gap_expl_zh}</span></p>
      <div class="pipeline-flow-diagram">
        <div class="flow-step">
          <span class="flow-num">1</span>
          <span class="flow-text"><span data-lang="en">Intermediate Goods (MIG_ING)</span><span data-lang="zh">中间品原料</span></span>
        </div>
        <span class="flow-arrow">→ (~2M lead) →</span>
        <div class="flow-step">
          <span class="flow-num">2</span>
          <span class="flow-text"><span data-lang="en">Consumer Goods PPI (MIG_COG)</span><span data-lang="zh">消费品出厂价</span></span>
        </div>
        <span class="flow-arrow">→ (~1M lead) →</span>
        <div class="flow-step">
          <span class="flow-num">3</span>
          <span class="flow-text"><span data-lang="en">Core Goods CPI (NEIG)</span><span data-lang="zh">终端非能源工业品 CPI</span></span>
        </div>
      </div>
    </div>

    <div class="subchart-container">
      <div class="subchart-header" style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px;">
        <h4><span data-lang="en">Domestic PPI vs PPI-CPI Margin Scissors Spread (2022–2026)</span><span data-lang="zh">国内工业 PPI 同比与 PPI-CPI 剪刀差演变 (2022–2026)</span></h4>
        <div class="lw-chart-meta" id="lw-meta-deepdive-chart-scissors-gap-{country_code}"></div>
      </div>
      <div id="deepdive-chart-scissors-gap-{country_code}" class="lw-chart-plot" data-lw-chart="deepdive-chart-scissors-gap-{country_code}" style="height: 380px; width: 100%;"></div>
    </div>
  </div>

  <!-- ── TAB 5: PRICING EXPECTATIONS & CAPACITY STUDIO ────────────────────── -->
  <div class="deepdive-tab-content" id="tab-expectations-{country_code}">
    <div class="expectations-intro">
      <p>
        <span data-lang="en">Forward-looking pricing intentions from European Commission harmonised business & consumer surveys. Evaluated against 4-year historical distributions (Min/Max percentiles). Capacity utilization above 80% signals supply bottlenecks and enhanced corporate pricing power.</span>
        <span data-lang="zh">来自欧盟委员会月度企业与消费者联合调查的前瞻物价预期。通过4年历史区间分位数（Percentile）精准定位景气区间。工业产能利用率超过 80% 代表供给端存在产能瓶颈，企业具备较强向下游提价的溢价底气。</span>
      </p>
    </div>

    <!-- 5 Sector Gauge Cards -->
    <div class="exp-cards-grid">
      {"\n".join(exp_cards_html)}
    </div>

    <!-- Expectations Multi-Track Chart with Latest Reading Callouts -->
    <div class="subchart-container">
      <div class="subchart-header" style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px;">
        <h4><span data-lang="en">Multi-Track Pricing Expectations & Capacity Utilization (2022–2026)</span><span data-lang="zh">多维度前瞻提价预期与工业产能利用率演变趋势 (2022–2026)</span></h4>
        <div class="lw-chart-meta" id="lw-meta-deepdive-chart-expectations-{country_code}"></div>
      </div>
      <div id="deepdive-chart-expectations-{country_code}" class="lw-chart-plot" data-lw-chart="deepdive-chart-expectations-{country_code}" style="height: 420px; width: 100%;"></div>
    </div>
  </div>
</div>

<!-- Serialized Data Script for Dynamic Switching -->
<script type="text/javascript">
window.CEE_CPI_DATA_{country_code} = {cpi_json_str};
window.CEE_MOM_DATA_{country_code} = {mom_json_str};
window.CEE_PPI_DATA_{country_code} = {ppi_json_str};

function toggleSubRows(groupKey, btn) {{
  var rows = document.querySelectorAll('.sub-' + groupKey);
  var isExpanded = btn.innerText === '▼';
  for (var i = 0; i < rows.length; i++) {{
    rows[i].style.display = isExpanded ? 'none' : 'table-row';
  }}
  btn.innerText = isExpanded ? '▶' : '▼';
}}

function switchDeepdiveTab(geo, tabName, btn) {{
  var parent = document.getElementById('deepdive-inflation-' + geo);
  if (!parent) return;
  var tabs = parent.querySelectorAll('.deepdive-tab');
  for (var i = 0; i < tabs.length; i++) tabs[i].classList.remove('active');
  btn.classList.add('active');

  var contents = parent.querySelectorAll('.deepdive-tab-content');
  for (var j = 0; j < contents.length; j++) contents[j].classList.remove('active');
  var target = document.getElementById('tab-' + tabName + '-' + geo);
  if (target) target.classList.add('active');

  if (window.CPChart && window.CPChart.mountVisibleIn && target) {{
    window.CPChart.mountVisibleIn(target);
  }}
  // Trigger resize
  window.dispatchEvent(new Event('resize'));
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
  var data = window['CEE_CPI_DATA_' + geo];
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
    var hasSub = it.sub_items && it.sub_items.length > 0;
    var btn = hasSub ? '<button class="sub-toggle-btn" onclick="toggleSubRows(\\'' + geo + '-' + it.code + '\\', this)">▶</button>' : '<span class="sub-placeholder"></span>';
    html += '<tr class="row-division" data-group="' + geo + '-' + it.code + '">' +
      '<td class="col-name">' + btn + ' <span>' + it.name + '</span></td>' +
      '<td class="col-num col-weight">' + fmt(it.weight) + '</td>' +
      '<td class="col-num">' + fmt(it.yoy) + '</td>' +
      '<td class="col-num text-muted">' + fmt(it.yoy_prev) + '</td>' +
      '<td class="col-num">' + fmt(it.contrib_yoy) + '</td>' +
      '<td class="col-num">' + fmt(it.mom) + '</td>' +
      '<td class="col-num text-muted">' + fmt(it.mom_ago) + '</td>' +
      '<td class="col-num">' + fmt(it.contrib_mom) + '</td>' +
      '</tr>';

    if (hasSub) {{
      it.sub_items.forEach(function(sub) {{
        html += '<tr class="row-subitem sub-' + geo + '-' + it.code + '" style="display: none;">' +
          '<td class="col-name col-sub"><span class="sub-tree-prefix">↳</span> ' + sub.name + '</td>' +
          '<td class="col-num col-weight text-muted">' + fmt(sub.weight, 2) + '</td>' +
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

  html += '<tr class="row-separator"><td colspan="8"></td></tr>';
  (tbl.memo || []).forEach(function(m) {{
    html += '<tr class="row-memo">' +
      '<td class="col-name"><span>' + m.name + '</span></td>' +
      '<td class="col-num col-weight">' + (m.weight ? fmt(m.weight) : '&nbsp;') + '</td>' +
      '<td class="col-num">' + fmt(m.yoy) + '</td>' +
      '<td class="col-num text-muted">' + fmt(m.yoy_prev) + '</td>' +
      '<td class="col-num">&nbsp;</td>' +
      '<td class="col-num">' + fmt(m.mom) + '</td>' +
      '<td class="col-num text-muted">' + fmt(m.mom_ago) + '</td>' +
      '<td class="col-num">&nbsp;</td>' +
      '</tr>';
  }});

  tbody.innerHTML = html;
}}

function updateMomentumTable(geo, selectedMonth) {{
  var data = window['CEE_MOM_DATA_' + geo];
  if (!data || !data[selectedMonth]) return;
  var tbl = data[selectedMonth];
  var tbody = document.getElementById('tbody-mom-' + geo);
  if (!tbody) return;

  var fmt = function(v, d, s) {{
    if (v === null || v === undefined) return '—';
    var sign = (s && v > 0) ? '+' : '';
    return sign + Number(v).toFixed(d || 1);
  }};

  var html = '';
  (tbl.items || []).forEach(function(it) {{
    var isHead = it.code === 'TOTAL';
    var rowCls = isHead ? 'row-headline' : 'row-division';
    var gapVal = it.gap;
    var gapCls = (gapVal && gapVal > 0.5) ? 'val-pos' : ((gapVal && gapVal < -0.5) ? 'val-neg' : 'val-neutral');
    var badge = '<span class="status-badge ' + (it.badge || 'badge-neutral') + '">' + (it.icon || '') +
      ' <span data-lang="en">' + it.signal_en + '</span><span data-lang="zh">' + it.signal_zh + '</span></span>';

    html += '<tr class="' + rowCls + '">' +
      '<td class="col-name"><span><span data-lang="en">' + it.name_en + '</span><span data-lang="zh">' + it.name_zh + '</span></span></td>' +
      '<td class="col-num">' + fmt(it.weight) + '</td>' +
      '<td class="col-num">' + fmt(it.mom_1m_ann, 1, true) + '%</td>' +
      '<td class="col-num"><strong>' + fmt(it.mom_3m_ann, 1, true) + '%</strong></td>' +
      '<td class="col-num text-muted">' + fmt(it.mom_6m_ann, 1, true) + '%</td>' +
      '<td class="col-num">' + fmt(it.yoy, 1, true) + '%</td>' +
      '<td class="col-num ' + gapCls + '"><strong>' + fmt(gapVal, 1, true) + ' pp</strong></td>' +
      '<td class="col-name" style="text-align: center;">' + badge + '</td>' +
      '</tr>';
  }});
  tbody.innerHTML = html;

  // Update Top KPIs
  var kpiHead = document.getElementById('kpi-mom-head-val-' + geo);
  if (kpiHead) kpiHead.innerText = fmt(tbl.headline_ann_3m, 1, true) + '%';
  var kpiCore = document.getElementById('kpi-mom-core-val-' + geo);
  if (kpiCore) kpiCore.innerText = fmt(tbl.core_ann_3m, 1, true) + '%';
}}

function updatePpiTable(geo, selectedMonth) {{
  var data = window['CEE_PPI_DATA_' + geo];
  if (!data || !data[selectedMonth]) return;
  var tbl = data[selectedMonth];
  var tableEl = document.getElementById('table-ppi-' + geo);
  if (!tableEl) return;

  var thCurrY = tableEl.querySelector('.th-curr-ppi-yoy');
  var thPrevY = tableEl.querySelector('.th-prev-ppi-yoy');
  var thCurrM = tableEl.querySelector('.th-curr-ppi-mom');
  if (thCurrY) thCurrY.innerText = formatMonYy(selectedMonth);
  if (thPrevY) thPrevY.innerText = formatMonYy(tbl.prev_date || '');
  if (thCurrM) thCurrM.innerText = formatMonYy(selectedMonth);

  var tbody = document.getElementById('tbody-ppi-' + geo);
  if (!tbody) return;

  var fmt = function(v, d) {{
    if (v === null || v === undefined) return '—';
    return Number(v).toFixed(d || 1);
  }};

  var h = tbl.headline || {{}};
  var html = '<tr class="row-headline">' +
    '<td class="col-name"><strong>Headline PPI (Domestic Market)</strong></td>' +
    '<td class="col-num">&nbsp;</td>' +
    '<td class="col-num"><strong>' + fmt(h.yoy) + '</strong></td>' +
    '<td class="col-num text-muted">' + fmt(h.yoy_prev) + '</td>' +
    '<td class="col-num">&nbsp;</td>' +
    '<td class="col-num"><strong>' + fmt(h.mom) + '</strong></td>' +
    '<td class="col-num text-muted">' + fmt(h.mom_ago) + '</td>' +
    '<td class="col-num"><strong>' + fmt(h.contrib_mom) + '</strong></td>' +
    '</tr>';

  (tbl.items || []).forEach(function(it) {{
    html += '<tr class="row-division">' +
      '<td class="col-name"><span>' + it.name + '</span></td>' +
      '<td class="col-num col-weight">' + fmt(it.weight) + '</td>' +
      '<td class="col-num">' + fmt(it.yoy) + '</td>' +
      '<td class="col-num text-muted">' + fmt(it.yoy_prev) + '</td>' +
      '<td class="col-num">' + fmt(it.contrib_yoy) + '</td>' +
      '<td class="col-num">' + fmt(it.mom) + '</td>' +
      '<td class="col-num text-muted">' + fmt(it.mom_ago) + '</td>' +
      '<td class="col-num">' + fmt(it.contrib_mom) + '</td>' +
      '</tr>';
  }});

  html += '<tr class="row-separator"><td colspan="8"></td></tr>';
  (tbl.memo || []).forEach(function(m) {{
    html += '<tr class="row-memo">' +
      '<td class="col-name"><span>' + m.name + '</span></td>' +
      '<td class="col-num col-weight">&nbsp;</td>' +
      '<td class="col-num">' + fmt(m.yoy) + '</td>' +
      '<td class="col-num text-muted">' + fmt(m.yoy_prev) + '</td>' +
      '<td class="col-num">&nbsp;</td>' +
      '<td class="col-num">' + fmt(m.mom) + '</td>' +
      '<td class="col-num text-muted">' + fmt(m.mom_ago) + '</td>' +
      '<td class="col-num">&nbsp;</td>' +
      '</tr>';
  }});

  tbody.innerHTML = html;
}}

{deepdive_chart_init_js}
</script>
<!-- ══════════════════════════════════════════════════════════════════════════ -->
"""
    cleaned_lines = [line.rstrip() for line in html_out.splitlines()]
    return "\n".join(cleaned_lines) + "\n"
