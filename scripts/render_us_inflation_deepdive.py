"""Renderer for Institutional US Inflation & PPI Deep-Dive Modules.

Generates FT / Morgan Stanley institutional-grade interactive HTML components for the US:
- Table 1: CPI Inflation by product group (BLS 8 expenditure categories, sub-items, Supercore, Core PCE)
- Short-Term Inflation Momentum Monitor (1M, 3M, 6M annualized rates vs 12M YoY & trajectory chart)
- Table 2: PPI Inflation by stage (Final Demand Goods, Services, Construction, Intermediate Demand)
- PPI - CPI Margin Scissors Pipeline (Spread chart, margin squeeze monitor)
- Pricing Expectations & Capacity Studio (Michigan 1Y/5Y, TIPS 5Y/10Y breakevens, Fed Capacity Utilization)
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
  min-width: 200px;
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
.inflation-table .text-muted {
  color: var(--muted, #64748b);
}
.table-footnote {
  font-size: 11px;
  color: var(--muted, #64748b);
  margin-top: 8px;
  line-height: 1.4;
}
.subchart-container {
  margin-top: 20px;
  padding-top: 16px;
  border-top: 1px dashed var(--border, #e2e8f0);
}
.subchart-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
}
.subchart-header h4 {
  font-size: 13px;
  font-weight: 600;
  margin: 0;
  color: var(--fg, #0f172a);
}
.status-badge {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 2px 8px;
  border-radius: 3px;
  font-size: 11px;
  font-weight: 600;
}
.badge-squeeze {
  background: #fef2f2;
  color: #b91c1c;
  border: 1px solid #fecaca;
}
.badge-expand {
  background: #ecfdf5;
  color: #047857;
  border: 1px solid #a7f3d0;
}
.badge-neutral {
  background: #f8fafc;
  color: #475569;
  border: 1px solid #e2e8f0;
}
.momentum-kpi-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
  gap: 12px;
  margin-bottom: 18px;
}
.momentum-kpi-card {
  background: #f8fafc;
  border: 1px solid var(--border, #e2e8f0);
  border-radius: 5px;
  padding: 12px 14px;
}
.momentum-kpi-card.highlight-card {
  background: #f0fdf4;
  border-color: #bbf7d0;
}
.kpi-label {
  font-size: 11px;
  font-weight: 600;
  color: var(--muted, #64748b);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  margin-bottom: 4px;
}
.kpi-val {
  font-size: 24px;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
  color: var(--fg, #0f172a);
}
.kpi-subtext {
  font-size: 11px;
  color: var(--text-secondary, #475569);
  margin-top: 4px;
}
.scissors-kpi-card {
  background: #f8fafc;
  border: 1px solid var(--border, #e2e8f0);
  border-radius: 6px;
  padding: 16px;
  margin-bottom: 16px;
}
.scissors-val-row {
  display: flex;
  align-items: baseline;
  gap: 12px;
  margin: 6px 0 10px 0;
  flex-wrap: wrap;
}
.scissors-val {
  font-size: 28px;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
  color: var(--fg, #0f172a);
}
.exp-sector-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 12px;
  margin-bottom: 20px;
}
.exp-sector-card {
  background: #f8fafc;
  border: 1px solid var(--border, #e2e8f0);
  border-radius: 6px;
  padding: 14px;
  display: flex;
  flex-direction: column;
}
.exp-card-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}
.exp-card-icon {
  font-size: 18px;
}
.exp-card-title {
  font-size: 13px;
  font-weight: 700;
  color: var(--fg, #0f172a);
}
.exp-card-sub {
  font-size: 10px;
  color: var(--muted, #64748b);
}
.exp-card-val-row {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  margin: 6px 0;
}
.exp-card-val {
  font-size: 22px;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
  color: var(--fg, #0f172a);
}
.exp-card-trend {
  font-size: 11px;
  font-weight: 600;
}
.trend-up { color: #b91c1c; }
.trend-down { color: #047857; }
.trend-flat { color: #64748b; }
.exp-meter-track {
  width: 100%;
  height: 6px;
  background: #e2e8f0;
  border-radius: 3px;
  overflow: hidden;
  margin: 6px 0;
}
.exp-meter-fill {
  height: 100%;
  background: #3b82f6;
  border-radius: 3px;
}
.exp-meter-scale {
  display: flex;
  justify-content: space-between;
  font-size: 10px;
  color: var(--muted, #64748b);
}
.exp-pct-tag {
  font-weight: 600;
  color: #1e293b;
}
.exp-card-takeaway {
  font-size: 11px;
  color: var(--text-secondary, #475569);
  margin-top: 10px;
  padding-top: 8px;
  border-top: 1px dashed var(--border, #e2e8f0);
  line-height: 1.4;
  flex: 1;
}
</style>
"""


def _format_num(val, dec=1, signed=False):
    if val is None:
        return "—"
    try:
        f = float(val)
        if signed and f > 0:
            return f"+{f:.{dec}f}"
        return f"{f:.{dec}f}"
    except (ValueError, TypeError):
        return "—"


def format_mon_yy(dt_str):
    if not dt_str or "-" not in dt_str:
        return dt_str or ""
    parts = dt_str.split("-")
    if len(parts) >= 2:
        m_map = {
            "01": "Jan", "02": "Feb", "03": "Mar", "04": "Apr",
            "05": "May", "06": "Jun", "07": "Jul", "08": "Aug",
            "09": "Sep", "10": "Oct", "11": "Nov", "12": "Dec"
        }
        return f"{m_map.get(parts[1], parts[1])}-{parts[0][2:]}"
    return dt_str


def render_us_deepdive_panel() -> str:
    """Render the full institutional US inflation, momentum, and industrial PPI suite."""
    data_file = OUTPUT / "us_inflation_deepdive.json"
    if not data_file.exists():
        return ""

    try:
        with open(data_file, "r", encoding="utf-8") as f:
            c_data = json.load(f)
    except Exception:
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
    if ts.get("ppi_final_demand_yoy"):
        latest_ppi_head = ts["ppi_final_demand_yoy"][-1].get("value")

    latest_cpi_head = latest_cpi_tbl.get("headline", {}).get("yoy")

    if latest_gap_val is not None:
        gap_sign = "+" if latest_gap_val > 0 else ""
        gap_str = f"{gap_sign}{latest_gap_val:.2f} pp"
        if latest_gap_val > 0.5:
            gap_badge = '<span class="status-badge badge-squeeze"><span data-lang="en">Margin Squeeze (PPI > CPI)</span><span data-lang="zh">毛利挤压 (PPI > CPI)</span></span>'
            gap_expl_en = "Upstream Final Demand PPI is rising faster than consumer CPI. Manufacturers and distributors face margin compression as input and service wholesale costs outpace retail price passthrough."
            gap_expl_zh = "上游最终需求 PPI 涨幅显著高于消费物价 CPI，工业与分销企业无法全额向下游消费者转嫁出厂成本，毛利率面临压缩。"
        elif latest_gap_val < -0.5:
            gap_badge = '<span class="status-badge badge-expand"><span data-lang="en">Margin Expansion (PPI < CPI)</span><span data-lang="zh">毛利扩张 (PPI < CPI)</span></span>'
            gap_expl_en = "Upstream goods and services factory-gate prices are disinflating faster than retail prices. Downstream retailers and consumer-facing businesses enjoy positive profit margins."
            gap_expl_zh = "上游工业品与出厂服务降温快于终端零售物价，消费端商户与下游分销商享受成本红利与利润重估。"
        else:
            gap_badge = '<span class="status-badge badge-neutral"><span data-lang="en">Balanced Pipeline (PPI ≈ CPI)</span><span data-lang="zh">传导平衡 (PPI ≈ CPI)</span></span>'
            gap_expl_en = "Upstream final demand factory prices are well aligned with consumer prices."
            gap_expl_zh = "上游最终需求出厂端与消费物价涨幅基本持平，产销传导处于常态均衡。"
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
          <td class="col-name"><strong>Headline CPI</strong></td>
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
            toggle_btn = f'<button class="sub-toggle-btn" onclick="toggleSubRows(\'us-{it["code"]}\', this)">▶</button>' if has_sub else '<span class="sub-placeholder"></span>'

            row = f"""
            <tr class="row-division" data-group="us-{it['code']}">
              <td class="col-name">{toggle_btn} <span>{escape(it['name'])}</span></td>
              <td class="col-num col-weight">{_format_num(it.get('weight'))}</td>
              <td class="col-num"><strong>{_format_num(it.get('yoy'))}</strong></td>
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
                    <tr class="row-subitem sub-us-{it['code']}" style="display: none;">
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
              <td class="col-num"><strong>{_format_num(m.get('yoy'))}</strong></td>
              <td class="col-num text-muted">{_format_num(m.get('yoy_prev'))}</td>
              <td class="col-num">&nbsp;</td>
              <td class="col-num">{_format_num(m.get('mom')) if m.get('mom') is not None else '&nbsp;'}</td>
              <td class="col-num text-muted">{_format_num(m.get('mom_ago')) if m.get('mom_ago') is not None else '&nbsp;'}</td>
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
            is_head = it.get("code") == "TOTAL"
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
          <td class="col-name"><strong>Final Demand PPI (Headline)</strong></td>
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
              <td class="col-num"><strong>{_format_num(it.get('yoy'))}</strong></td>
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
              <td class="col-num"><strong>{_format_num(m.get('yoy'))}</strong></td>
              <td class="col-num text-muted">{_format_num(m.get('yoy_prev'))}</td>
              <td class="col-num">&nbsp;</td>
              <td class="col-num">{_format_num(m.get('mom')) if m.get('mom') is not None else '&nbsp;'}</td>
              <td class="col-num text-muted">{_format_num(m.get('mom_ago')) if m.get('mom_ago') is not None else '&nbsp;'}</td>
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

    # 4-Component historical time series data for Plotly stacked chart
    cf_dates = [o["date"] for o in ts.get("cpi_contrib_food_yoy", [])]
    cf_vals = [o["value"] for o in ts.get("cpi_contrib_food_yoy", [])]
    ce_vals = [o["value"] for o in ts.get("cpi_contrib_energy_yoy", [])]
    cg_vals = [o["value"] for o in ts.get("cpi_contrib_goods_yoy", [])]
    cshel_vals = [o["value"] for o in ts.get("cpi_contrib_shelter_yoy", [])]
    cserv_vals = [o["value"] for o in ts.get("cpi_contrib_services_yoy", [])]
    chead_vals = [o["value"] for o in ts.get("cpi_head_yoy", [])]

    # Momentum series for Trajectory chart
    mom_dates = [o["date"] for o in ts.get("cpi_head_3m_ann", [])]
    mom_head_3m = [o["value"] for o in ts.get("cpi_head_3m_ann", [])]
    mom_head_yoy = [o["value"] for o in ts.get("cpi_head_12m_yoy", [])]
    mom_core_3m = [o["value"] for o in ts.get("cpi_core_3m_ann", [])]
    mom_core_yoy = [o["value"] for o in ts.get("cpi_core_12m_yoy", [])]
    mom_super_3m = [o["value"] for o in ts.get("cpi_supercore_3m_ann", [])]

    # Scissors Gap time series
    sg_dates = [o["date"] for o in ts.get("ppi_cpi_scissors_gap", [])]
    sg_vals = [o["value"] for o in ts.get("ppi_cpi_scissors_gap", [])]
    ppi_head_vals = [o["value"] for o in ts.get("ppi_final_demand_yoy", [])]

    # Expectations series
    exp_dates = [o["date"] for o in ts.get("exp_michigan_1y", [])]
    exp_mich_1y = [o["value"] for o in ts.get("exp_michigan_1y", [])]
    exp_mich_5y = [o["value"] for o in ts.get("exp_michigan_5y", [])]
    exp_tips_5y = [o["value"] for o in ts.get("exp_tips_5y", [])]
    exp_tips_10y = [o["value"] for o in ts.get("exp_tips_10y", [])]
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

    lw_deepdive_specs = {
        "deepdive-chart-cpi-contrib-US": {
            "title": "CPI Component Contributions",
            "unit": "pp",
            "badge": {"text": "Fed Target: 2.0%", "color": "#0d7680", "bg": "rgba(13, 118, 128, 0.10)"},
            "series": [
                {"name": "Headline CPI (YoY %)", "type": "line", "color": "#0f172a", "width": 2, "style": 0, "isPrimary": True, "data": _lw_pts(cf_dates, chead_vals)},
                {"name": "Shelter (住房)", "type": "line", "color": "#8b5cf6", "width": 2, "style": 0, "data": _lw_pts(cf_dates, cshel_vals)},
                {"name": "Other Core Services (其他核心服务)", "type": "line", "color": "#10b981", "width": 2, "style": 0, "data": _lw_pts(cf_dates, cserv_vals)},
                {"name": "Food (食品)", "type": "line", "color": "#f59e0b", "width": 2, "style": 0, "data": _lw_pts(cf_dates, cf_vals)},
                {"name": "Core Goods (核心商品)", "type": "line", "color": "#06b6d4", "width": 2, "style": 0, "data": _lw_pts(cf_dates, cg_vals)},
                {"name": "Energy (能源)", "type": "line", "color": "#64748b", "width": 2, "style": 0, "data": _lw_pts(cf_dates, ce_vals)},
            ],
            "priceLines": [
                {"price": 2.0, "color": "#0d7680", "width": 2, "style": 2, "title": "Target 2%", "axisLabel": False},
                {"price": 0.0, "color": "rgba(18, 21, 26, 0.40)", "width": 1, "style": 0, "title": "", "axisLabel": False},
            ],
        },
        "deepdive-chart-mom-trajectory-US": {
            "title": "Inflation Momentum Trajectory",
            "unit": "%",
            "badge": {"text": "Fed Target: 2.0%", "color": "#0d7680", "bg": "rgba(13, 118, 128, 0.10)"},
            "series": [
                {"name": "Headline 3M Ann.", "type": "line", "color": "#2563eb", "width": 2, "style": 0, "isPrimary": True, "data": _lw_pts(mom_dates, mom_head_3m)},
                {"name": "Headline 12M YoY", "type": "line", "color": "#93c5fd", "width": 2, "style": 2, "data": _lw_pts(mom_dates, mom_head_yoy)},
                {"name": "Core 3M Ann.", "type": "line", "color": "#990f3d", "width": 2, "style": 0, "data": _lw_pts(mom_dates, mom_core_3m)},
                {"name": "Core 12M YoY", "type": "line", "color": "#fca5a5", "width": 2, "style": 1, "data": _lw_pts(mom_dates, mom_core_yoy)},
                {"name": "Supercore 3M Ann.", "type": "line", "color": "#7c3aed", "width": 2, "style": 0, "data": _lw_pts(mom_dates, mom_super_3m)},
            ],
            "priceLines": [
                {"price": 2.0, "color": "#0d7680", "width": 2, "style": 2, "title": "Target 2%", "axisLabel": False},
                {"price": 0.0, "color": "rgba(18, 21, 26, 0.35)", "width": 1, "style": 0, "title": "", "axisLabel": False},
            ],
        },
        "deepdive-chart-margin-scissors-US": {
            "title": "PPI vs CPI Margin Scissors",
            "unit": "pp / %",
            "series": [
                {"name": "Scissors Gap (PPI - CPI pp)", "type": "histogram", "color": "#0d7680", "data": _lw_pts(sg_dates, sg_vals, is_bar=True)},
                {"name": "Final Demand PPI (YoY %)", "type": "line", "color": "#6366f1", "width": 2, "style": 0, "isPrimary": True, "data": _lw_pts(sg_dates, ppi_head_vals)},
            ],
            "priceLines": [{"price": 0.0, "color": "rgba(18, 21, 26, 0.40)", "width": 1, "style": 0, "title": "", "axisLabel": False}],
        },
        "deepdive-chart-expectations-US": {
            "title": "Inflation Expectations & Capacity Utilization",
            "unit": "%",
            "badge": {"text": "Right Scale: Capacity Util (%)", "color": "#7c3aed", "bg": "rgba(124, 58, 237, 0.08)"},
            "series": [
                {"name": "Michigan 1Y Exp", "type": "line", "color": "#2563eb", "width": 2, "style": 0, "scale": "left", "isPrimary": True, "data": _lw_pts(exp_dates, exp_mich_1y)},
                {"name": "Michigan 5Y Exp", "type": "line", "color": "#059669", "width": 2, "style": 0, "scale": "left", "data": _lw_pts(exp_dates, exp_mich_5y)},
                {"name": "5Y TIPS Breakeven", "type": "line", "color": "#d97706", "width": 2, "style": 0, "scale": "left", "data": _lw_pts(exp_dates, exp_tips_5y)},
                {"name": "10Y TIPS Breakeven", "type": "line", "color": "#dc2626", "width": 2, "style": 1, "scale": "left", "data": _lw_pts(exp_dates, exp_tips_10y)},
                {"name": "Capacity Util (%) [R]", "type": "line", "color": "#7c3aed", "width": 2, "style": 0, "scale": "right", "data": _lw_pts(cu_dates, cu_vals)},
            ],
            "priceLines": [{"price": 2.0, "color": "#0d7680", "width": 1, "style": 2, "title": "Target 2%", "axisLabel": False}],
        },
    }
    us_deepdive_chart_init_js = (
        "window.CP_LW_CHARTS = Object.assign(window.CP_LW_CHARTS || {}, "
        + json.dumps(lw_deepdive_specs, ensure_ascii=False, separators=(",", ":"))
        + ");"
    )

    # Build Sector Expectations Cards HTML
    exp_cards_html = []
    for s_key in ["exp_michigan_1y", "exp_michigan_5y", "exp_tips_5y", "exp_tips_10y", "capacity_utilization"]:
        s_data = exp_summary.get(s_key, {})
        if not s_data:
            continue
        cur = s_data.get("current", 0.0)
        diff3 = s_data.get("diff_3m", 0.0)
        pct = s_data.get("pct", 50)
        val_str = f"{cur:.2f}%" if "tips" in s_key or "michigan" in s_key else f"{cur:.1f}%"
        trend_cls = "trend-up" if diff3 > 0.1 else ("trend-down" if diff3 < -0.1 else "trend-flat")
        trend_sign = "+" if diff3 > 0 else ""
        trend_arrow = "▲" if diff3 > 0.05 else ("▼" if diff3 < -0.05 else "▬")
        trend_str = f"{trend_arrow} {trend_sign}{diff3:.2f} pts vs 3M"

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
<!-- INSTITUTIONAL INFLATION, MOMENTUM & INDUSTRIAL PRICING STUDIO (US)         -->
<!-- ══════════════════════════════════════════════════════════════════════════ -->
<div class="deepdive-macro-panel" id="deepdive-inflation-US">
  <div class="deepdive-header">
    <div class="deepdive-title-wrap">
      <span class="deepdive-badge"><span data-lang="en">INSTITUTIONAL SUITE</span><span data-lang="zh">机构级通胀与工业定价工坊</span></span>
      <h3 class="deepdive-title"><span data-lang="en">US Inflation Decomposition, Momentum & Pricing Studio</span><span data-lang="zh">美国通胀分项贡献、短期动量与工业定价工坊</span></h3>
      <p class="deepdive-subtitle">
        <span data-lang="en">BLS 8 expenditure categories, Supercore Services (ex-housing), 1M/3M/6M annualized momentum, PPI Final Demand stages & market inflation expectations.</span>
        <span data-lang="zh">BLS 8大消费支出大类、超级核心服务(剔住房)、1M/3M/6M年化动量监控、最终需求PPI出厂阶段与市场远期通胀预期。</span>
      </p>
    </div>
    <div class="deepdive-tabs">
      <button class="deepdive-tab active" onclick="switchDeepdiveTab('US', 'cpi', this)">
        <span data-lang="en">Table 1: CPI Breakdown</span><span data-lang="zh">表1：CPI分项贡献</span>
      </button>
      <button class="deepdive-tab" onclick="switchDeepdiveTab('US', 'momentum', this)">
        <span data-lang="en">Short-Term Momentum</span><span data-lang="zh">通胀短期动量监控</span>
      </button>
      <button class="deepdive-tab" onclick="switchDeepdiveTab('US', 'ppi', this)">
        <span data-lang="en">Table 2: PPI Final Demand</span><span data-lang="zh">表2：PPI出厂需求</span>
      </button>
      <button class="deepdive-tab" onclick="switchDeepdiveTab('US', 'pipeline', this)">
        <span data-lang="en">Margin Scissors & Pipeline</span><span data-lang="zh">传导链与利润剪刀差</span>
      </button>
      <button class="deepdive-tab" onclick="switchDeepdiveTab('US', 'expectations', this)">
        <span data-lang="en">Pricing Expectations</span><span data-lang="zh">通胀预期与产能利用率</span>
      </button>
    </div>
  </div>

  <!-- ── TAB 1: CPI TABLE ────────────────────────────────────────────────── -->
  <div class="deepdive-tab-content active" id="tab-cpi-US">
    <div class="table-toolbar">
      <div class="toolbar-left">
        <span class="table-caption">
          <strong><span data-lang="en">Table 1: CPI Inflation by product group</span><span data-lang="zh">表 1：CPI 分项通胀与贡献拆解</span></strong>
        </span>
      </div>
      <div class="toolbar-right">
        <label for="cpi-select-US"><span data-lang="en">Release Print:</span><span data-lang="zh">发布期数：</span></label>
        <select id="cpi-select-US" class="month-select" onchange="updateCpiTable('US', this.value)">
          {cpi_month_options}
        </select>
      </div>
    </div>

    <div class="table-responsive">
      <table class="inflation-table" id="table-cpi-US">
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
        <tbody id="tbody-cpi-US">
          {_render_cpi_rows(latest_cpi_tbl)}
        </tbody>
      </table>
    </div>
    <div class="table-footnote">
      <span data-lang="en">*Methodology: Contribution to y/y and m/m inflation calculated using BLS relative importance weights (percentage points summing to headline). Memo items (Core CPI, Supercore Services, Core PCE) reflect specialized policy concepts and do not sum into headline. Source: Bureau of Labor Statistics (BLS) & Federal Reserve.</span>
      <span data-lang="zh">*编制方法：同比与环比通胀贡献度基于 BLS 相对权重测算（百分点严格加总至 Headline）。备忘项（核心 CPI、超级核心服务、核心 PCE）为央行政策观察重点，为重叠概念不计入加总。数据源：美国劳工统计局 (BLS) 与美联储。</span>
    </div>

    <!-- Stacked Historical Contribution Chart -->
    <div class="subchart-container">
      <div class="subchart-header" style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px;">
        <h4><span data-lang="en">Historical CPI Component Contributions (2022–2026)</span><span data-lang="zh">CPI 分项贡献历史演变趋势 (2022–2026)</span></h4>
        <div class="lw-chart-meta" id="lw-meta-deepdive-chart-cpi-contrib-US"></div>
      </div>
      <div id="deepdive-chart-cpi-contrib-US" class="lw-chart-plot" data-lw-chart="deepdive-chart-cpi-contrib-US" style="height: 350px; width: 100%;"></div>
    </div>
  </div>

  <!-- ── TAB 2: SHORT-TERM INFLATION MOMENTUM ─────────────────────────────── -->
  <div class="deepdive-tab-content" id="tab-momentum-US">
    <div class="momentum-kpi-grid">
      <div class="momentum-kpi-card highlight-card">
        <div class="kpi-label"><span data-lang="en">Headline 3M Annualized (Compounded)</span><span data-lang="zh">整体 CPI 3个月年化增速</span></div>
        <div class="kpi-val" id="kpi-mom-head-val-US">{_format_num(head_ann_3m, 1, signed=True)}%</div>
        <div class="kpi-subtext" id="kpi-mom-head-sub-US">
          <span data-lang="en">vs 12M YoY: <strong>{_format_num(head_yoy, 1)}%</strong> | Momentum Spread: <strong>{_format_num(head_gap, 1, signed=True)} pp</strong></span>
          <span data-lang="zh">对比 12M 同比: <strong>{_format_num(head_yoy, 1)}%</strong> | 动量差值: <strong>{_format_num(head_gap, 1, signed=True)} pp</strong></span>
        </div>
      </div>
      <div class="momentum-kpi-card">
        <div class="kpi-label"><span data-lang="en">Core 3M Annualized (ex-Food & Energy)</span><span data-lang="zh">核心 CPI 3个月年化增速 (剔食品能源)</span></div>
        <div class="kpi-val" id="kpi-mom-core-val-US">{_format_num(core_ann_3m, 1, signed=True)}%</div>
        <div class="kpi-subtext" id="kpi-mom-core-sub-US">
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
          <span data-lang="en">3M annualized pace filters base effects and leads YoY prints by ~1-2 quarters for Fed decision-making.</span>
          <span data-lang="zh">3个月年化复合增速剔除基数扰动，领先同比读数1至2个季度，为美联储利率决策关键依据。</span>
        </div>
      </div>
    </div>

    <div class="table-toolbar">
      <div class="toolbar-left">
        <span class="table-caption">
          <strong><span data-lang="en">Short-Term Inflation Momentum Monitor</span><span data-lang="zh">短期通胀动量与年化增速监控表</span></strong>
        </span>
      </div>
      <div class="toolbar-right">
        <label for="mom-select-US"><span data-lang="en">Release Print:</span><span data-lang="zh">发布期数：</span></label>
        <select id="mom-select-US" class="month-select" onchange="updateMomTable('US', this.value)">
          {mom_month_options}
        </select>
      </div>
    </div>

    <div class="table-responsive">
      <table class="inflation-table" id="table-mom-US">
        <thead>
          <tr class="th-tier1">
            <th class="col-name text-left"><span data-lang="en">Indicator / Sub-Component</span><span data-lang="zh">监控指标 / 分项</span></th>
            <th class="col-num"><span data-lang="en">Weight</span><span data-lang="zh">权重%</span></th>
            <th class="col-num"><span data-lang="en">1M Ann.</span><span data-lang="zh">1M年化</span></th>
            <th class="col-num"><strong><span data-lang="en">3M Ann.</span><span data-lang="zh">3M年化</span></strong></th>
            <th class="col-num text-muted"><span data-lang="en">6M Ann.</span><span data-lang="zh">6M年化</span></th>
            <th class="col-num"><span data-lang="en">12M YoY</span><span data-lang="zh">12M同比</span></th>
            <th class="col-num"><strong><span data-lang="en">Momentum Gap</span><span data-lang="zh">动量差值</span></strong></th>
            <th class="col-name" style="text-align: center;"><span data-lang="en">Regime</span><span data-lang="zh">动量态势</span></th>
          </tr>
        </thead>
        <tbody id="tbody-mom-US">
          {_render_momentum_rows(latest_mom_tbl)}
        </tbody>
      </table>
    </div>

    <!-- Momentum Trajectory Chart -->
    <div class="subchart-container">
      <div class="subchart-header" style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px;">
        <h4><span data-lang="en">Momentum Trajectory: 3M Annualized vs 12M YoY Inflation (2022–2026)</span><span data-lang="zh">通胀动量演变：3M年化增速 vs 12M同比走势 (2022–2026)</span></h4>
        <div class="lw-chart-meta" id="lw-meta-deepdive-chart-mom-trajectory-US"></div>
      </div>
      <div id="deepdive-chart-mom-trajectory-US" class="lw-chart-plot" data-lw-chart="deepdive-chart-mom-trajectory-US" style="height: 360px; width: 100%;"></div>
    </div>
  </div>

  <!-- ── TAB 3: PPI TABLE ────────────────────────────────────────────────── -->
  <div class="deepdive-tab-content" id="tab-ppi-US">
    <div class="table-toolbar">
      <div class="toolbar-left">
        <span class="table-caption">
          <strong><span data-lang="en">Table 2: Producer Price Index (PPI) Final Demand by Stage</span><span data-lang="zh">表 2：最终需求工业出厂价格指数 (PPI)</span></strong>
        </span>
      </div>
      <div class="toolbar-right">
        <label for="ppi-select-US"><span data-lang="en">Release Print:</span><span data-lang="zh">发布期数：</span></label>
        <select id="ppi-select-US" class="month-select" onchange="updatePpiTable('US', this.value)">
          {ppi_month_options}
        </select>
      </div>
    </div>

    <div class="table-responsive">
      <table class="inflation-table" id="table-ppi-US">
        <thead>
          <tr class="th-tier1">
            <th rowspan="2" class="col-name text-left"><span data-lang="en">Final Demand Category</span><span data-lang="zh">最终需求类别</span></th>
            <th rowspan="2" class="col-num"><span data-lang="en">Weights</span><span data-lang="zh">权重%</span></th>
            <th colspan="3" class="col-group-header"><span data-lang="en">y / y</span><span data-lang="zh">同 比 (y/y)</span></th>
            <th colspan="3" class="col-group-header"><span data-lang="en">m / m</span><span data-lang="zh">环 比 (m/m)</span></th>
          </tr>
          <tr class="th-tier2">
            <th class="col-num th-curr-ppi-yoy">{format_mon_yy(latest_ppi_month)}</th>
            <th class="col-num th-prev-ppi-yoy text-muted">{format_mon_yy(latest_ppi_tbl.get('prev_date', ''))}</th>
            <th class="col-num"><span data-lang="en">Contrib*<br>to y/y</span><span data-lang="zh">同比贡献*</span></th>
            <th class="col-num th-curr-ppi-mom">{format_mon_yy(latest_ppi_month)}</th>
            <th class="col-num text-muted"><span data-lang="en">1Y ago</span><span data-lang="zh">去年同期</span></th>
            <th class="col-num"><span data-lang="en">Contrib*<br>to m/m</span><span data-lang="zh">环比贡献*</span></th>
          </tr>
        </thead>
        <tbody id="tbody-ppi-US">
          {_render_ppi_rows(latest_ppi_tbl)}
        </tbody>
      </table>
    </div>
    <div class="table-footnote">
      <span data-lang="en">*Source: BLS Producer Price Index Final Demand (FD Goods, FD Services, FD Construction). Memo rows cover intermediate demand stages.</span>
      <span data-lang="zh">*数据源：BLS 工业生产者最终需求指数（商品、服务与建筑营造）。备忘项包含中间需求加工品。</span>
    </div>
  </div>

  <!-- ── TAB 4: MARGIN SCISSORS & PIPELINE ───────────────────────────────── -->
  <div class="deepdive-tab-content" id="tab-pipeline-US">
    <div class="scissors-kpi-card">
      <div class="kpi-label"><span data-lang="en">PPI - CPI Margin Scissors Spread (Final Demand vs Retail)</span><span data-lang="zh">工业利润剪刀差：出厂端 PPI vs 消费端 CPI</span></div>
      <div class="scissors-val-row">
        <span class="scissors-val">{gap_str}</span>
        {gap_badge}
      </div>
      <div class="kpi-subtext">
        <span data-lang="en">Latest Final Demand PPI YoY: <strong>{_format_num(latest_ppi_head, 1)}%</strong> | Headline CPI YoY: <strong>{_format_num(latest_cpi_head, 1)}%</strong>. {gap_expl_en}</span>
        <span data-lang="zh">最新最终需求 PPI 同比: <strong>{_format_num(latest_ppi_head, 1)}%</strong> | 终端 CPI 同比: <strong>{_format_num(latest_cpi_head, 1)}%</strong>。{gap_expl_zh}</span>
      </div>
    </div>

    <div class="subchart-container">
      <div class="subchart-header" style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px;">
        <h4><span data-lang="en">Historical Margin Scissors Gap & Wholesale Transmission (2022–2026)</span><span data-lang="zh">工业利润剪刀差与出厂传导历史走势 (2022–2026)</span></h4>
        <div class="lw-chart-meta" id="lw-meta-deepdive-chart-margin-scissors-US"></div>
      </div>
      <div id="deepdive-chart-margin-scissors-US" class="lw-chart-plot" data-lw-chart="deepdive-chart-margin-scissors-US" style="height: 370px; width: 100%;"></div>
    </div>
  </div>

  <!-- ── TAB 5: PRICING EXPECTATIONS & CAPACITY STUDIO ────────────────────── -->
  <div class="deepdive-tab-content" id="tab-expectations-US">
    <div class="exp-sector-grid">
      {"".join(exp_cards_html)}
    </div>

    <div class="subchart-container">
      <div class="subchart-header" style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px;">
        <h4><span data-lang="en">Inflation Expectations & Capacity Utilization Multi-Track Overview (2022–2026)</span><span data-lang="zh">多维通胀预期与工业产能利用率全景走势 (2022–2026)</span></h4>
        <div class="lw-chart-meta" id="lw-meta-deepdive-chart-expectations-US"></div>
      </div>
      <div id="deepdive-chart-expectations-US" class="lw-chart-plot" data-lw-chart="deepdive-chart-expectations-US" style="height: 420px; width: 100%;"></div>
    </div>
  </div>
</div>

<script>
// ── TAB SWITCHING ────────────────────────────────────────────────────────────
function switchDeepdiveTab(cc, tabId, btn) {{
  var container = document.getElementById("deepdive-inflation-" + cc);
  if (!container) return;
  var tabs = container.querySelectorAll(".deepdive-tab");
  tabs.forEach(function(t) {{ t.classList.remove("active"); }});
  btn.classList.add("active");

  var contents = container.querySelectorAll(".deepdive-tab-content");
  contents.forEach(function(c) {{ c.classList.remove("active"); }});
  var target = document.getElementById("tab-" + tabId + "-" + cc);
  if (target) {{
    target.classList.add("active");
    if (window.CPChart && window.CPChart.mountVisibleIn) {{
      window.CPChart.mountVisibleIn(target);
    }}
    window.dispatchEvent(new Event("resize"));
  }}
}}

// ── SUB-ITEMS COLLAPSE TOGGLE ────────────────────────────────────────────────
function toggleSubRows(grpId, btn) {{
  var rows = document.querySelectorAll(".sub-" + grpId);
  var isExpanded = btn.innerText === "▼";
  rows.forEach(function(r) {{
    r.style.display = isExpanded ? "none" : "table-row";
  }});
  btn.innerText = isExpanded ? "▶" : "▼";
}}

// ── DYNAMIC MONTH SWITCHERS ──────────────────────────────────────────────────
var usDeepdiveData = {json.dumps(c_data)};

function updateCpiTable(cc, month) {{
  var tbl = usDeepdiveData.cpi_tables[month];
  if (!tbl) return;
  var tbody = document.getElementById("tbody-cpi-" + cc);
  if (!tbody) return;

  var thCurrYoy = document.querySelector("#table-cpi-" + cc + " .th-curr-yoy");
  var thPrevYoy = document.querySelector("#table-cpi-" + cc + " .th-prev-yoy");
  var thCurrMom = document.querySelector("#table-cpi-" + cc + " .th-curr-mom");
  if (thCurrYoy) thCurrYoy.innerText = month;
  if (thPrevYoy) thPrevYoy.innerText = tbl.prev_date || "";
  if (thCurrMom) thCurrMom.innerText = month;

  var head = tbl.headline || {{}};
  var hHtml = '<tr class="row-headline">' +
    '<td class="col-name"><strong>Headline CPI</strong></td><td class="col-num">&nbsp;</td>' +
    '<td class="col-num"><strong>' + (head.yoy !== null ? head.yoy.toFixed(1) : '—') + '</strong></td>' +
    '<td class="col-num text-muted">' + (head.yoy_prev !== null ? head.yoy_prev.toFixed(1) : '—') + '</td>' +
    '<td class="col-num">&nbsp;</td>' +
    '<td class="col-num"><strong>' + (head.mom !== null ? head.mom.toFixed(1) : '—') + '</strong></td>' +
    '<td class="col-num text-muted">' + (head.mom_ago !== null ? head.mom_ago.toFixed(1) : '—') + '</td>' +
    '<td class="col-num"><strong>' + (head.contrib_mom !== null ? head.contrib_mom.toFixed(1) : '—') + '</strong></td></tr>';

  var itemsHtml = [];
  (tbl.items || []).forEach(function(it) {{
    var hasSub = it.sub_items && it.sub_items.length > 0;
    var toggleBtn = hasSub ? '<button class="sub-toggle-btn" onclick="toggleSubRows(\\'' + cc.toLowerCase() + '-' + it.code + '\\', this)">▶</button>' : '<span class="sub-placeholder"></span>';
    var r = '<tr class="row-division" data-group="' + cc.toLowerCase() + '-' + it.code + '">' +
      '<td class="col-name">' + toggleBtn + ' <span>' + it.name + '</span></td>' +
      '<td class="col-num col-weight">' + (it.weight !== null ? it.weight.toFixed(1) : '—') + '</td>' +
      '<td class="col-num"><strong>' + (it.yoy !== null ? it.yoy.toFixed(1) : '—') + '</strong></td>' +
      '<td class="col-num text-muted">' + (it.yoy_prev !== null ? it.yoy_prev.toFixed(1) : '—') + '</td>' +
      '<td class="col-num">' + (it.contrib_yoy !== null ? it.contrib_yoy.toFixed(1) : '—') + '</td>' +
      '<td class="col-num">' + (it.mom !== null ? it.mom.toFixed(1) : '—') + '</td>' +
      '<td class="col-num text-muted">' + (it.mom_ago !== null ? it.mom_ago.toFixed(1) : '—') + '</td>' +
      '<td class="col-num">' + (it.contrib_mom !== null ? it.contrib_mom.toFixed(1) : '—') + '</td></tr>';
    itemsHtml.push(r);

    if (hasSub) {{
      it.sub_items.forEach(function(sub) {{
        var sr = '<tr class="row-subitem sub-' + cc.toLowerCase() + '-' + it.code + '" style="display: none;">' +
          '<td class="col-name col-sub"><span class="sub-tree-prefix">↳</span> ' + sub.name + '</td>' +
          '<td class="col-num col-weight text-muted">' + (sub.weight !== null ? sub.weight.toFixed(2) : '—') + '</td>' +
          '<td class="col-num">' + (sub.yoy !== null ? sub.yoy.toFixed(1) : '—') + '</td>' +
          '<td class="col-num text-muted">' + (sub.yoy_prev !== null ? sub.yoy_prev.toFixed(1) : '—') + '</td>' +
          '<td class="col-num">' + (sub.contrib_yoy !== null ? sub.contrib_yoy.toFixed(1) : '—') + '</td>' +
          '<td class="col-num">' + (sub.mom !== null ? sub.mom.toFixed(1) : '—') + '</td>' +
          '<td class="col-num text-muted">' + (sub.mom_ago !== null ? sub.mom_ago.toFixed(1) : '—') + '</td>' +
          '<td class="col-num">' + (sub.contrib_mom !== null ? sub.contrib_mom.toFixed(1) : '—') + '</td></tr>';
        itemsHtml.push(sr);
      }});
    }}
  }});

  var memoHtml = [];
  (tbl.memo || []).forEach(function(m) {{
    var mr = '<tr class="row-memo">' +
      '<td class="col-name"><span>' + m.name + '</span></td>' +
      '<td class="col-num col-weight">' + (m.weight ? m.weight.toFixed(1) : '&nbsp;') + '</td>' +
      '<td class="col-num"><strong>' + (m.yoy !== null ? m.yoy.toFixed(1) : '—') + '</strong></td>' +
      '<td class="col-num text-muted">' + (m.yoy_prev !== null ? m.yoy_prev.toFixed(1) : '—') + '</td>' +
      '<td class="col-num">&nbsp;</td>' +
      '<td class="col-num">' + (m.mom !== null && m.mom !== undefined ? m.mom.toFixed(1) : '&nbsp;') + '</td>' +
      '<td class="col-num text-muted">' + (m.mom_ago !== null && m.mom_ago !== undefined ? m.mom_ago.toFixed(1) : '&nbsp;') + '</td>' +
      '<td class="col-num">&nbsp;</td></tr>';
    memoHtml.push(mr);
  }});

  tbody.innerHTML = hHtml + itemsHtml.join('') + '<tr class="row-separator"><td colspan="8"></td></tr>' + memoHtml.join('');
}}

function updateMomTable(cc, month) {{
  var tbl = usDeepdiveData.momentum_tables[month];
  if (!tbl) return;
  var tbody = document.getElementById("tbody-mom-" + cc);
  if (!tbody) return;

  var kpiHeadVal = document.getElementById("kpi-mom-head-val-" + cc);
  var kpiCoreVal = document.getElementById("kpi-mom-core-val-" + cc);
  if (kpiHeadVal) kpiHeadVal.innerText = (tbl.headline_ann_3m !== null ? (tbl.headline_ann_3m > 0 ? '+' : '') + tbl.headline_ann_3m.toFixed(1) : '—') + '%';
  if (kpiCoreVal) kpiCoreVal.innerText = (tbl.core_ann_3m !== null ? (tbl.core_ann_3m > 0 ? '+' : '') + tbl.core_ann_3m.toFixed(1) : '—') + '%';

  var rowsHtml = [];
  (tbl.items || []).forEach(function(it) {{
    var isHead = it.code === "TOTAL";
    var rowCls = isHead ? "row-headline" : "row-division";
    var gapVal = it.gap;
    var gapCls = gapVal && gapVal > 0.5 ? "val-pos" : (gapVal && gapVal < -0.5 ? "val-neg" : "val-neutral");
    var badge = '<span class="status-badge ' + (it.badge || 'badge-neutral') + '">' + (it.icon || '') + ' <span data-lang="en">' + (it.signal_en || '') + '</span><span data-lang="zh">' + (it.signal_zh || '') + '</span></span>';

    var r = '<tr class="' + rowCls + '">' +
      '<td class="col-name"><span><span data-lang="en">' + it.name_en + '</span><span data-lang="zh">' + it.name_zh + '</span></span></td>' +
      '<td class="col-num col-weight">' + (it.weight !== null ? it.weight.toFixed(1) : '—') + '</td>' +
      '<td class="col-num">' + (it.mom_1m_ann !== null ? (it.mom_1m_ann > 0 ? '+' : '') + it.mom_1m_ann.toFixed(1) : '—') + '%</td>' +
      '<td class="col-num"><strong>' + (it.mom_3m_ann !== null ? (it.mom_3m_ann > 0 ? '+' : '') + it.mom_3m_ann.toFixed(1) : '—') + '%</strong></td>' +
      '<td class="col-num text-muted">' + (it.mom_6m_ann !== null ? (it.mom_6m_ann > 0 ? '+' : '') + it.mom_6m_ann.toFixed(1) : '—') + '%</td>' +
      '<td class="col-num">' + (it.yoy !== null ? (it.yoy > 0 ? '+' : '') + it.yoy.toFixed(1) : '—') + '%</td>' +
      '<td class="col-num ' + gapCls + '"><strong>' + (gapVal !== null ? (gapVal > 0 ? '+' : '') + gapVal.toFixed(1) : '—') + ' pp</strong></td>' +
      '<td class="col-name" style="text-align: center;">' + badge + '</td></tr>';
    rowsHtml.push(r);
  }});
  tbody.innerHTML = rowsHtml.join('');
}}

function updatePpiTable(cc, month) {{
  var tbl = usDeepdiveData.ppi_tables[month];
  if (!tbl) return;
  var tbody = document.getElementById("tbody-ppi-" + cc);
  if (!tbody) return;

  var thCurr = document.querySelector("#table-ppi-" + cc + " .th-curr-ppi-yoy");
  var thPrev = document.querySelector("#table-ppi-" + cc + " .th-prev-ppi-yoy");
  var thMom = document.querySelector("#table-ppi-" + cc + " .th-curr-ppi-mom");
  if (thCurr) thCurr.innerText = month;
  if (thPrev) thPrev.innerText = tbl.prev_date || "";
  if (thMom) thMom.innerText = month;

  var head = tbl.headline || {{}};
  var hHtml = '<tr class="row-headline">' +
    '<td class="col-name"><strong>Final Demand PPI (Headline)</strong></td><td class="col-num">&nbsp;</td>' +
    '<td class="col-num"><strong>' + (head.yoy !== null ? head.yoy.toFixed(1) : '—') + '</strong></td>' +
    '<td class="col-num text-muted">' + (head.yoy_prev !== null ? head.yoy_prev.toFixed(1) : '—') + '</td>' +
    '<td class="col-num">&nbsp;</td>' +
    '<td class="col-num"><strong>' + (head.mom !== null ? head.mom.toFixed(1) : '—') + '</strong></td>' +
    '<td class="col-num text-muted">' + (head.mom_ago !== null ? head.mom_ago.toFixed(1) : '—') + '</td>' +
    '<td class="col-num"><strong>' + (head.contrib_mom !== null ? head.contrib_mom.toFixed(1) : '—') + '</strong></td></tr>';

  var itemsHtml = [];
  (tbl.items || []).forEach(function(it) {{
    var r = '<tr class="row-division">' +
      '<td class="col-name"><span>' + it.name + '</span></td>' +
      '<td class="col-num col-weight">' + (it.weight !== null ? it.weight.toFixed(1) : '—') + '</td>' +
      '<td class="col-num"><strong>' + (it.yoy !== null ? it.yoy.toFixed(1) : '—') + '</strong></td>' +
      '<td class="col-num text-muted">' + (it.yoy_prev !== null ? it.yoy_prev.toFixed(1) : '—') + '</td>' +
      '<td class="col-num">' + (it.contrib_yoy !== null ? it.contrib_yoy.toFixed(1) : '—') + '</td>' +
      '<td class="col-num">' + (it.mom !== null ? it.mom.toFixed(1) : '—') + '</td>' +
      '<td class="col-num text-muted">' + (it.mom_ago !== null ? it.mom_ago.toFixed(1) : '—') + '</td>' +
      '<td class="col-num">' + (it.contrib_mom !== null ? it.contrib_mom.toFixed(1) : '—') + '</td></tr>';
    itemsHtml.push(r);
  }});

  var memoHtml = [];
  (tbl.memo || []).forEach(function(m) {{
    var mr = '<tr class="row-memo">' +
      '<td class="col-name"><span>' + m.name + '</span></td>' +
      '<td class="col-num col-weight">&nbsp;</td>' +
      '<td class="col-num"><strong>' + (m.yoy !== null ? m.yoy.toFixed(1) : '—') + '</strong></td>' +
      '<td class="col-num text-muted">' + (m.yoy_prev !== null ? m.yoy_prev.toFixed(1) : '—') + '</td>' +
      '<td class="col-num">&nbsp;</td>' +
      '<td class="col-num">' + (m.mom !== null && m.mom !== undefined ? m.mom.toFixed(1) : '&nbsp;') + '</td>' +
      '<td class="col-num text-muted">' + (m.mom_ago !== null && m.mom_ago !== undefined ? m.mom_ago.toFixed(1) : '&nbsp;') + '</td>' +
      '<td class="col-num">&nbsp;</td></tr>';
    memoHtml.push(mr);
  }});

  tbody.innerHTML = hHtml + itemsHtml.join('') + '<tr class="row-separator"><td colspan="8"></td></tr>' + memoHtml.join('');
}}

// ── LIGHTWEIGHT CHARTS REGISTRATION ──────────────────────────────────────────
{us_deepdive_chart_init_js}
</script>
<!-- ══════════════════════════════════════════════════════════════════════════ -->
"""
    cleaned_lines = [line.rstrip() for line in html_out.splitlines()]
    return "\n".join(cleaned_lines) + "\n"
