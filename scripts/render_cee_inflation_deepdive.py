"""Renderer for Institutional CEE Inflation & PPI Deep-Dive Modules.

Generates FT / Morgan Stanley institutional-grade interactive HTML components:
- Table 1: CPI Inflation by product group (with collapsible sub-items & month switcher)
- Table 2: PPI Inflation by stage & MIGs (with month switcher)
- PPI - CPI Margin Scissors Pipeline (with spread chart and margin squeeze monitor)
- CPI 4-Way Historical Contribution Stacked Bar Chart (with YoY / MoM toggle)
- Expectations & Capacity Utilization Multi-Track Suite
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
  border: 1px solid var(--border, #e2e8f0);
  border-radius: 4px;
  background: #ffffff;
}
.inflation-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 12px;
  font-variant-numeric: tabular-nums;
  line-height: 1.4;
}
.inflation-table th {
  background: #f8fafc;
  color: var(--fg, #1e293b);
  font-weight: 600;
  padding: 8px 10px;
  border: 1px solid var(--border, #e2e8f0);
  white-space: nowrap;
}
.inflation-table th.col-group-header {
  text-align: center;
  border-bottom: 1px solid var(--border, #cbd5e1);
}
.inflation-table td {
  padding: 6px 10px;
  border: 1px solid var(--border, #e2e8f0);
  white-space: nowrap;
}
.inflation-table .col-name {
  text-align: left;
  min-width: 180px;
}
.inflation-table .col-sub {
  padding-left: 24px;
}
.inflation-table .col-num {
  text-align: right;
  font-family: SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
}
.inflation-table .row-headline {
  background: #f1f5f9;
  font-weight: 700;
  border-top: 2px solid #0f172a;
  border-bottom: 2px solid #0f172a;
}
.inflation-table .row-division {
  border-bottom: 1px solid #f1f5f9;
}
.inflation-table .row-division:hover {
  background: #f8fafc;
}
.inflation-table .row-subitem {
  background: #fafbfc;
}
.inflation-table .row-subitem:hover {
  background: #f1f5f9;
}
.inflation-table .sub-tree-prefix {
  color: #94a3b8;
  font-weight: 600;
}
.inflation-table .sub-toggle-btn {
  background: none;
  border: none;
  cursor: pointer;
  color: #64748b;
  font-size: 10px;
  padding: 0 4px;
  margin-right: 2px;
}
.inflation-table .sub-toggle-btn:hover {
  color: #0f172a;
}
.inflation-table .sub-placeholder {
  display: inline-block;
  width: 14px;
}
.inflation-table .row-separator td {
  height: 6px;
  background: #f8fafc;
  border-left: none;
  border-right: none;
  padding: 0;
}
.inflation-table .row-memo {
  background: #fcfdfe;
  color: #475569;
}
.inflation-table .val-pos {
  color: #b91c1c;
  font-weight: 600;
}
.inflation-table .val-neg {
  color: #047857;
  font-weight: 600;
}
.inflation-table .val-neutral {
  color: #64748b;
}
.inflation-table .text-muted {
  color: #94a3b8;
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
.pipeline-kpi-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 12px;
  margin-bottom: 16px;
}
.pipeline-kpi-card {
  background: #f8fafc;
  border: 1px solid var(--border, #e2e8f0);
  border-radius: 6px;
  padding: 14px;
}
.pipeline-kpi-card.highlight-card {
  background: #eff6ff;
  border-color: #bfdbfe;
}
.pipeline-kpi-card .kpi-label {
  font-size: 11px;
  font-weight: 600;
  color: var(--muted, #64748b);
  margin-bottom: 4px;
}
.pipeline-kpi-card .kpi-val {
  font-size: 22px;
  font-weight: 700;
  color: var(--fg, #0f172a);
  font-variant-numeric: tabular-nums;
  line-height: 1.2;
}
.pipeline-kpi-card .kpi-gap {
  color: #2563eb;
}
.pipeline-kpi-card .kpi-subtext {
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
.expectations-intro {
  font-size: 12px;
  color: var(--muted, #64748b);
  margin-bottom: 12px;
  line-height: 1.5;
}
</style>
"""


def _format_num(val, decimals=1, signed=False):
    if val is None:
        return "—"
    sign = "+" if signed and val > 0 else ""
    return f"{sign}{val:.{decimals}f}"


def _sign_class(val):
    if val is None:
        return ""
    if val > 0.05:
        return "val-pos"
    if val < -0.05:
        return "val-neg"
    return "val-neutral"


def render_deepdive_panel(country_code: str) -> str:
    """Render the full institutional inflation and industrial PPI suite for a CEE country."""
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
    ts = c_data.get("time_series", {})

    if not cpi_tables:
        return ""

    sorted_cpi_months = sorted(list(cpi_tables.keys()), reverse=True)
    latest_cpi_month = sorted_cpi_months[0]
    latest_cpi_tbl = cpi_tables[latest_cpi_month]

    sorted_ppi_months = sorted(list(ppi_tables.keys()), reverse=True)
    latest_ppi_month = sorted_ppi_months[0] if sorted_ppi_months else latest_cpi_month
    latest_ppi_tbl = ppi_tables.get(latest_ppi_month, {})

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
        head = tbl.get("headline", {})
        h_html = f"""
        <tr class="row-headline">
          <td class="col-name"><strong>Headline HICP</strong></td>
          <td class="col-num">—</td>
          <td class="col-num"><strong>{_format_num(head.get('yoy'))}</strong></td>
          <td class="col-num text-muted">{_format_num(head.get('yoy_prev'))}</td>
          <td class="col-num"><strong>{_format_num(head.get('contrib_yoy'), 2, signed=True)}</strong></td>
          <td class="col-num"><strong>{_format_num(head.get('mom'))}</strong></td>
          <td class="col-num text-muted">{_format_num(head.get('mom_ago'))}</td>
          <td class="col-num"><strong>{_format_num(head.get('contrib_mom'), 2, signed=True)}</strong></td>
        </tr>
        """

        items_html = []
        for it in tbl.get("items", []):
            has_sub = bool(it.get("sub_items"))
            toggle_btn = f'<button class="sub-toggle-btn" onclick="toggleSubRows(\'{country_code}-{it["code"]}\', this)">▶</button>' if has_sub else '<span class="sub-placeholder"></span>'
            cy_cls = _sign_class(it.get("contrib_yoy"))
            cm_cls = _sign_class(it.get("contrib_mom"))

            row = f"""
            <tr class="row-division" data-group="{country_code}-{it['code']}">
              <td class="col-name">{toggle_btn} <span>{escape(it['name'])}</span></td>
              <td class="col-num">{_format_num(it.get('weight'))}</td>
              <td class="col-num">{_format_num(it.get('yoy'))}</td>
              <td class="col-num text-muted">{_format_num(it.get('yoy_prev'))}</td>
              <td class="col-num {cy_cls}">{_format_num(it.get('contrib_yoy'), 2, signed=True)}</td>
              <td class="col-num">{_format_num(it.get('mom'))}</td>
              <td class="col-num text-muted">{_format_num(it.get('mom_ago'))}</td>
              <td class="col-num {cm_cls}">{_format_num(it.get('contrib_mom'), 2, signed=True)}</td>
            </tr>
            """
            items_html.append(row)

            # Sub-items
            if has_sub:
                for sub in it["sub_items"]:
                    s_cy_cls = _sign_class(sub.get("contrib_yoy"))
                    s_cm_cls = _sign_class(sub.get("contrib_mom"))
                    sub_row = f"""
                    <tr class="row-subitem sub-{country_code}-{it['code']}" style="display: none;">
                      <td class="col-name col-sub"><span class="sub-tree-prefix">↳</span> {escape(sub['name'])}</td>
                      <td class="col-num text-muted">{_format_num(sub.get('weight'), 2)}</td>
                      <td class="col-num">{_format_num(sub.get('yoy'))}</td>
                      <td class="col-num text-muted">{_format_num(sub.get('yoy_prev'))}</td>
                      <td class="col-num {s_cy_cls}">{_format_num(sub.get('contrib_yoy'), 2, signed=True)}</td>
                      <td class="col-num">{_format_num(sub.get('mom'))}</td>
                      <td class="col-num text-muted">{_format_num(sub.get('mom_ago'))}</td>
                      <td class="col-num {s_cm_cls}">{_format_num(sub.get('contrib_mom'), 2, signed=True)}</td>
                    </tr>
                    """
                    items_html.append(sub_row)

        memo_html = []
        for m in tbl.get("memo", []):
            m_row = f"""
            <tr class="row-memo">
              <td class="col-name"><em>{escape(m['name'])}</em></td>
              <td class="col-num text-muted">{_format_num(m.get('weight')) if m.get('weight') else '—'}</td>
              <td class="col-num">{_format_num(m.get('yoy'))}</td>
              <td class="col-num text-muted">{_format_num(m.get('yoy_prev'))}</td>
              <td class="col-num">—</td>
              <td class="col-num">{_format_num(m.get('mom'))}</td>
              <td class="col-num text-muted">{_format_num(m.get('mom_ago'))}</td>
              <td class="col-num">—</td>
            </tr>
            """
            memo_html.append(m_row)

        return h_html + "\n".join(items_html) + """<tr class="row-separator"><td colspan="8"></td></tr>""" + "\n".join(memo_html)

    # Build PPI Table Rows HTML
    def _render_ppi_rows(tbl):
        if not tbl:
            return ""
        head = tbl.get("headline", {})
        h_html = f"""
        <tr class="row-headline">
          <td class="col-name"><strong>Headline PPI (Domestic Market)</strong></td>
          <td class="col-num">100.0</td>
          <td class="col-num"><strong>{_format_num(head.get('yoy'))}</strong></td>
          <td class="col-num text-muted">{_format_num(head.get('yoy_prev'))}</td>
          <td class="col-num"><strong>{_format_num(head.get('contrib_yoy'), 2, signed=True)}</strong></td>
          <td class="col-num"><strong>{_format_num(head.get('mom'))}</strong></td>
          <td class="col-num text-muted">{_format_num(head.get('mom_ago'))}</td>
          <td class="col-num"><strong>{_format_num(head.get('contrib_mom'), 2, signed=True)}</strong></td>
        </tr>
        """

        items_html = []
        for it in tbl.get("items", []):
            cy_cls = _sign_class(it.get("contrib_yoy"))
            cm_cls = _sign_class(it.get("contrib_mom"))
            row = f"""
            <tr class="row-division">
              <td class="col-name"><span>{escape(it['name'])}</span></td>
              <td class="col-num">{_format_num(it.get('weight'))}</td>
              <td class="col-num">{_format_num(it.get('yoy'))}</td>
              <td class="col-num text-muted">{_format_num(it.get('yoy_prev'))}</td>
              <td class="col-num {cy_cls}">{_format_num(it.get('contrib_yoy'), 2, signed=True)}</td>
              <td class="col-num">{_format_num(it.get('mom'))}</td>
              <td class="col-num text-muted">{_format_num(it.get('mom_ago'))}</td>
              <td class="col-num {cm_cls}">{_format_num(it.get('contrib_mom'), 2, signed=True)}</td>
            </tr>
            """
            items_html.append(row)

        memo_html = []
        for m in tbl.get("memo", []):
            m_row = f"""
            <tr class="row-memo">
              <td class="col-name"><em>{escape(m['name'])}</em></td>
              <td class="col-num text-muted">—</td>
              <td class="col-num">{_format_num(m.get('yoy'))}</td>
              <td class="col-num text-muted">{_format_num(m.get('yoy_prev'))}</td>
              <td class="col-num">—</td>
              <td class="col-num">{_format_num(m.get('mom'))}</td>
              <td class="col-num text-muted">{_format_num(m.get('mom_ago'))}</td>
              <td class="col-num">—</td>
            </tr>
            """
            memo_html.append(m_row)

        return h_html + "\n".join(items_html) + """<tr class="row-separator"><td colspan="8"></td></tr>""" + "\n".join(memo_html)

    # Prepare month options for select dropdown
    cpi_month_options = "\n".join([
        f'<option value="{m}" {"selected" if m == latest_cpi_month else ""}>{m} {"(Latest)" if m == latest_cpi_month else ""}</option>'
        for m in sorted_cpi_months
    ])
    ppi_month_options = "\n".join([
        f'<option value="{m}" {"selected" if m == latest_ppi_month else ""}>{m} {"(Latest)" if m == latest_ppi_month else ""}</option>'
        for m in sorted_ppi_months
    ])

    # Serialized JSON data for dynamic client-side month switching
    cpi_json_str = json.dumps(cpi_tables)
    ppi_json_str = json.dumps(ppi_tables)

    # 4-Component historical time series data for Plotly stacked chart
    cf_dates = [o["date"] for o in ts.get("cpi_contrib_food_yoy", [])]
    cf_vals = [o["value"] for o in ts.get("cpi_contrib_food_yoy", [])]
    cg_vals = [o["value"] for o in ts.get("cpi_contrib_goods_yoy", [])]
    ce_vals = [o["value"] for o in ts.get("cpi_contrib_energy_yoy", [])]
    cs_vals = [o["value"] for o in ts.get("cpi_contrib_services_yoy", [])]

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

    html_out = f"""{DEEPDIVE_CSS}
<!-- ══════════════════════════════════════════════════════════════════════════ -->
<!-- INSTITUTIONAL INFLATION & INDUSTRIAL PRICING DEEP-DIVE STUDIO            -->
<!-- ══════════════════════════════════════════════════════════════════════════ -->
<div class="deepdive-macro-panel" id="deepdive-inflation-{country_code}">
  <div class="deepdive-header">
    <div class="deepdive-title-wrap">
      <span class="deepdive-badge"><span data-lang="en">INSTITUTIONAL DECOMPOSITION</span><span data-lang="zh">机构级通胀解构</span></span>
      <h3 class="deepdive-title"><span data-lang="en">CPI & Industrial PPI Disaggregation Studio</span><span data-lang="zh">通胀分项与工业物价解构工坊</span></h3>
      <p class="deepdive-subtitle">
        <span data-lang="en">Exact percentage-point contributions across 12 COICOP divisions, sub-components, 5 PPI MIGs, margin scissors & pricing expectations.</span>
        <span data-lang="zh">12大消费类目与细分子项、5大工业分组（MIGs）、利润剪刀差传导链与定价预期微观解构。</span>
      </p>
    </div>
    <div class="deepdive-tabs">
      <button class="deepdive-tab active" onclick="switchDeepdiveTab('{country_code}', 'cpi', this)">
        <span data-lang="en">Table 1: CPI Breakdown</span><span data-lang="zh">表1：CPI分项贡献</span>
      </button>
      <button class="deepdive-tab" onclick="switchDeepdiveTab('{country_code}', 'ppi', this)">
        <span data-lang="en">Table 2: PPI & MIGs</span><span data-lang="zh">表2：PPI工业分组</span>
      </button>
      <button class="deepdive-tab" onclick="switchDeepdiveTab('{country_code}', 'pipeline', this)">
        <span data-lang="en">Margin Scissors & Pipeline</span><span data-lang="zh">传导链与利润剪刀差</span>
      </button>
      <button class="deepdive-tab" onclick="switchDeepdiveTab('{country_code}', 'expectations', this)">
        <span data-lang="en">Pricing Expectations</span><span data-lang="zh">行业提价预期与产能</span>
      </button>
    </div>
  </div>

  <!-- ── TAB 1: CPI TABLE ────────────────────────────────────────────────── -->
  <div class="deepdive-tab-content active" id="tab-cpi-{country_code}">
    <div class="table-toolbar">
      <div class="toolbar-left">
        <span class="table-caption">
          <strong><span data-lang="en">Table 1: CPI Inflation by product group</span><span data-lang="zh">表 1：居民消费价格分项及百分点贡献</span></strong>
          <span class="table-badge-primary">HICP COICOP</span>
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
            <th rowspan="2" class="col-name text-left"><span data-lang="en">Product group</span><span data-lang="zh">产品分项分组</span></th>
            <th rowspan="2" class="col-num"><span data-lang="en">Weights</span><span data-lang="zh">篮子权重%</span></th>
            <th colspan="3" class="col-group-header"><span data-lang="en">y / y</span><span data-lang="zh">同 比 (y/y)</span></th>
            <th colspan="3" class="col-group-header"><span data-lang="en">m / m</span><span data-lang="zh">环 比 (m/m)</span></th>
          </tr>
          <tr class="th-tier2">
            <th class="col-num th-curr-yoy">{latest_cpi_month}</th>
            <th class="col-num th-prev-yoy">{latest_cpi_tbl.get('prev_date', '')}</th>
            <th class="col-num th-contrib-yoy"><span data-lang="en">Contrib* to y/y</span><span data-lang="zh">同比贡献(pp)</span></th>
            <th class="col-num th-curr-mom">{latest_cpi_month}</th>
            <th class="col-num th-ago-mom"><span data-lang="en">1Y ago</span><span data-lang="zh">去年同期</span></th>
            <th class="col-num th-contrib-mom"><span data-lang="en">Contrib* to m/m</span><span data-lang="zh">环比贡献(pp)</span></th>
          </tr>
        </thead>
        <tbody id="tbody-cpi-{country_code}">
          {_render_cpi_rows(latest_cpi_tbl)}
        </tbody>
      </table>
    </div>
    <div class="table-footnote">
      <span data-lang="en">*Note: Percentage-point contributions sum up to headline HICP inflation. Click ▶ to drill down into 3-digit sub-items. Source: Eurostat prc_hicp_minr / prc_hicp_iw.</span>
      <span data-lang="zh">*注：百分点贡献加总严格恒等于整体 HICP 通胀率。点击 ▶ 可展开下钻至 3 位与 4 位细分商品服务项。数据源：Eurostat prc_hicp_minr / prc_hicp_iw。</span>
    </div>

    <!-- Stacked Historical Contribution Chart -->
    <div class="subchart-container">
      <div class="subchart-header">
        <h4><span data-lang="en">Historical CPI Component Contributions (2020–2026)</span><span data-lang="zh">CPI 四大类贡献历史演变趋势 (2020–2026)</span></h4>
      </div>
      <div id="chart-cpi-contrib-{country_code}" style="height: 350px; width: 100%;"></div>
    </div>
  </div>

  <!-- ── TAB 2: PPI TABLE ────────────────────────────────────────────────── -->
  <div class="deepdive-tab-content" id="tab-ppi-{country_code}">
    <div class="table-toolbar">
      <div class="toolbar-left">
        <span class="table-caption">
          <strong><span data-lang="en">Table 2: PPI Inflation by stage & MIGs</span><span data-lang="zh">表 2：工业品出厂价格阶段与分组矩阵 (MIGs)</span></strong>
          <span class="table-badge-secondary">Domestic Industry</span>
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
            <th rowspan="2" class="col-name text-left"><span data-lang="en">Industrial Grouping (MIGs)</span><span data-lang="zh">工业大类分组</span></th>
            <th rowspan="2" class="col-num"><span data-lang="en">Weight%</span><span data-lang="zh">权重占比%</span></th>
            <th colspan="3" class="col-group-header"><span data-lang="en">y / y</span><span data-lang="zh">同 比 (y/y)</span></th>
            <th colspan="3" class="col-group-header"><span data-lang="en">m / m</span><span data-lang="zh">环 比 (m/m)</span></th>
          </tr>
          <tr class="th-tier2">
            <th class="col-num th-curr-ppi-yoy">{latest_ppi_month}</th>
            <th class="col-num th-prev-ppi-yoy">{latest_ppi_tbl.get('prev_date', '')}</th>
            <th class="col-num th-contrib-ppi-yoy"><span data-lang="en">Contrib* to y/y</span><span data-lang="zh">同比贡献(pp)</span></th>
            <th class="col-num th-curr-ppi-mom">{latest_ppi_month}</th>
            <th class="col-num th-ago-ppi-mom"><span data-lang="en">1Y ago</span><span data-lang="zh">去年同期</span></th>
            <th class="col-num th-contrib-ppi-mom"><span data-lang="en">Contrib* to m/m</span><span data-lang="zh">环比贡献(pp)</span></th>
          </tr>
        </thead>
        <tbody id="tbody-ppi-{country_code}">
          {_render_ppi_rows(latest_ppi_tbl)}
        </tbody>
      </table>
    </div>
    <div class="table-footnote">
      <span data-lang="en">*Note: Percentage-point contributions sum up to Headline Domestic PPI (B-E36). Coverage: Domestic producer prices. Source: Eurostat sts_inppd_m.</span>
      <span data-lang="zh">*注：百分点贡献加总严格恒等于国内工业品出厂 PPI（B-E36）。统计口径：国内生产者市场。数据源：Eurostat sts_inppd_m。</span>
    </div>
  </div>

  <!-- ── TAB 3: MARGIN SCISSORS & PIPELINE ───────────────────────────────── -->
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

    <div id="chart-scissors-gap-{country_code}" style="height: 380px; width: 100%;"></div>
  </div>

  <!-- ── TAB 4: PRICING EXPECTATIONS & CAPACITY ─────────────────────────── -->
  <div class="deepdive-tab-content" id="tab-expectations-{country_code}">
    <div class="expectations-intro">
      <p>
        <span data-lang="en">Forward-looking pricing intentions from European Commission harmonised business & consumer surveys. Capacity utilization above 80% signals supply bottlenecks and enhanced corporate pricing power.</span>
        <span data-lang="zh">来自欧盟委员会月度企业与消费者联合调查的前瞻物价预期。工业产能利用率超过 80% 代表供给端存在产能瓶颈，企业具备较强向下游提价的能力。</span>
      </p>
    </div>
    <div id="chart-expectations-{country_code}" style="height: 400px; width: 100%;"></div>
  </div>
</div>

<!-- Serialized Data Script for Dynamic Switching -->
<script type="text/javascript">
window.CEE_CPI_DATA_{country_code} = {cpi_json_str};
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

  // Trigger plotly resize
  window.dispatchEvent(new Event('resize'));
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
  if (thCurrY) thCurrY.innerText = selectedMonth;
  if (thPrevY) thPrevY.innerText = tbl.prev_date || '';
  if (thCurrM) thCurrM.innerText = selectedMonth;

  var tbody = document.getElementById('tbody-cpi-' + geo);
  if (!tbody) return;

  var fmt = function(v, d, s) {{
    if (v === null || v === undefined) return '—';
    var sign = (s && v > 0) ? '+' : '';
    return sign + Number(v).toFixed(d || 1);
  }};
  var scls = function(v) {{
    if (v === null || v === undefined) return '';
    if (v > 0.05) return 'val-pos';
    if (v < -0.05) return 'val-neg';
    return 'val-neutral';
  }};

  var h = tbl.headline || {{}};
  var html = '<tr class="row-headline">' +
    '<td class="col-name"><strong>Headline HICP</strong></td>' +
    '<td class="col-num">—</td>' +
    '<td class="col-num"><strong>' + fmt(h.yoy) + '</strong></td>' +
    '<td class="col-num text-muted">' + fmt(h.yoy_prev) + '</td>' +
    '<td class="col-num"><strong>' + fmt(h.contrib_yoy, 2, true) + '</strong></td>' +
    '<td class="col-num"><strong>' + fmt(h.mom) + '</strong></td>' +
    '<td class="col-num text-muted">' + fmt(h.mom_ago) + '</td>' +
    '<td class="col-num"><strong>' + fmt(h.contrib_mom, 2, true) + '</strong></td>' +
    '</tr>';

  (tbl.items || []).forEach(function(it) {{
    var hasSub = it.sub_items && it.sub_items.length > 0;
    var btn = hasSub ? '<button class="sub-toggle-btn" onclick="toggleSubRows(\\'' + geo + '-' + it.code + '\\', this)">▶</button>' : '<span class="sub-placeholder"></span>';
    html += '<tr class="row-division" data-group="' + geo + '-' + it.code + '">' +
      '<td class="col-name">' + btn + ' <span>' + it.name + '</span></td>' +
      '<td class="col-num">' + fmt(it.weight) + '</td>' +
      '<td class="col-num">' + fmt(it.yoy) + '</td>' +
      '<td class="col-num text-muted">' + fmt(it.yoy_prev) + '</td>' +
      '<td class="col-num ' + scls(it.contrib_yoy) + '">' + fmt(it.contrib_yoy, 2, true) + '</td>' +
      '<td class="col-num">' + fmt(it.mom) + '</td>' +
      '<td class="col-num text-muted">' + fmt(it.mom_ago) + '</td>' +
      '<td class="col-num ' + scls(it.contrib_mom) + '">' + fmt(it.contrib_mom, 2, true) + '</td>' +
      '</tr>';

    if (hasSub) {{
      it.sub_items.forEach(function(sub) {{
        html += '<tr class="row-subitem sub-' + geo + '-' + it.code + '" style="display: none;">' +
          '<td class="col-name col-sub"><span class="sub-tree-prefix">↳</span> ' + sub.name + '</td>' +
          '<td class="col-num text-muted">' + fmt(sub.weight, 2) + '</td>' +
          '<td class="col-num">' + fmt(sub.yoy) + '</td>' +
          '<td class="col-num text-muted">' + fmt(sub.yoy_prev) + '</td>' +
          '<td class="col-num ' + scls(sub.contrib_yoy) + '">' + fmt(sub.contrib_yoy, 2, true) + '</td>' +
          '<td class="col-num">' + fmt(sub.mom) + '</td>' +
          '<td class="col-num text-muted">' + fmt(sub.mom_ago) + '</td>' +
          '<td class="col-num ' + scls(sub.contrib_mom) + '">' + fmt(sub.contrib_mom, 2, true) + '</td>' +
          '</tr>';
      }});
    }}
  }});

  html += '<tr class="row-separator"><td colspan="8"></td></tr>';
  (tbl.memo || []).forEach(function(m) {{
    html += '<tr class="row-memo">' +
      '<td class="col-name"><em>' + m.name + '</em></td>' +
      '<td class="col-num text-muted">' + (m.weight ? fmt(m.weight) : '—') + '</td>' +
      '<td class="col-num">' + fmt(m.yoy) + '</td>' +
      '<td class="col-num text-muted">' + fmt(m.yoy_prev) + '</td>' +
      '<td class="col-num">—</td>' +
      '<td class="col-num">' + fmt(m.mom) + '</td>' +
      '<td class="col-num text-muted">' + fmt(m.mom_ago) + '</td>' +
      '<td class="col-num">—</td>' +
      '</tr>';
  }});

  tbody.innerHTML = html;
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
  if (thCurrY) thCurrY.innerText = selectedMonth;
  if (thPrevY) thPrevY.innerText = tbl.prev_date || '';
  if (thCurrM) thCurrM.innerText = selectedMonth;

  var tbody = document.getElementById('tbody-ppi-' + geo);
  if (!tbody) return;

  var fmt = function(v, d, s) {{
    if (v === null || v === undefined) return '—';
    var sign = (s && v > 0) ? '+' : '';
    return sign + Number(v).toFixed(d || 1);
  }};
  var scls = function(v) {{
    if (v === null || v === undefined) return '';
    if (v > 0.05) return 'val-pos';
    if (v < -0.05) return 'val-neg';
    return 'val-neutral';
  }};

  var h = tbl.headline || {{}};
  var html = '<tr class="row-headline">' +
    '<td class="col-name"><strong>Headline PPI (Domestic Market)</strong></td>' +
    '<td class="col-num">100.0</td>' +
    '<td class="col-num"><strong>' + fmt(h.yoy) + '</strong></td>' +
    '<td class="col-num text-muted">' + fmt(h.yoy_prev) + '</td>' +
    '<td class="col-num"><strong>' + fmt(h.contrib_yoy, 2, true) + '</strong></td>' +
    '<td class="col-num"><strong>' + fmt(h.mom) + '</strong></td>' +
    '<td class="col-num text-muted">' + fmt(h.mom_ago) + '</td>' +
    '<td class="col-num"><strong>' + fmt(h.contrib_mom, 2, true) + '</strong></td>' +
    '</tr>';

  (tbl.items || []).forEach(function(it) {{
    html += '<tr class="row-division">' +
      '<td class="col-name"><span>' + it.name + '</span></td>' +
      '<td class="col-num">' + fmt(it.weight) + '</td>' +
      '<td class="col-num">' + fmt(it.yoy) + '</td>' +
      '<td class="col-num text-muted">' + fmt(it.yoy_prev) + '</td>' +
      '<td class="col-num ' + scls(it.contrib_yoy) + '">' + fmt(it.contrib_yoy, 2, true) + '</td>' +
      '<td class="col-num">' + fmt(it.mom) + '</td>' +
      '<td class="col-num text-muted">' + fmt(it.mom_ago) + '</td>' +
      '<td class="col-num ' + scls(it.contrib_mom) + '">' + fmt(it.contrib_mom, 2, true) + '</td>' +
      '</tr>';
  }});

  html += '<tr class="row-separator"><td colspan="8"></td></tr>';
  (tbl.memo || []).forEach(function(m) {{
    html += '<tr class="row-memo">' +
      '<td class="col-name"><em>' + m.name + '</em></td>' +
      '<td class="col-num text-muted">—</td>' +
      '<td class="col-num">' + fmt(m.yoy) + '</td>' +
      '<td class="col-num text-muted">' + fmt(m.yoy_prev) + '</td>' +
      '<td class="col-num">—</td>' +
      '<td class="col-num">' + fmt(m.mom) + '</td>' +
      '<td class="col-num text-muted">' + fmt(m.mom_ago) + '</td>' +
      '<td class="col-num">—</td>' +
      '</tr>';
  }});

  tbody.innerHTML = html;
}}

// Initialize Plotly Charts for Deep-dive
document.addEventListener("DOMContentLoaded", function() {{
  if (typeof Plotly === "undefined") return;

  // 1. Stacked CPI Contribution Chart
  var cpiDiv = document.getElementById("chart-cpi-contrib-{country_code}");
  if (cpiDiv) {{
    var dates = {json.dumps(cf_dates)};
    var traceFood = {{x: dates, y: {json.dumps(cf_vals)}, name: 'Food (食品)', type: 'bar', marker: {{color: '#f59e0b'}}}};
    var traceGoods = {{x: dates, y: {json.dumps(cg_vals)}, name: 'Goods (商品)', type: 'bar', marker: {{color: '#3b82f6'}}}};
    var traceEnergy = {{x: dates, y: {json.dumps(ce_vals)}, name: 'Energy (公用能源)', type: 'bar', marker: {{color: '#ef4444'}}}};
    var traceServices = {{x: dates, y: {json.dumps(cs_vals)}, name: 'Services (服务)', type: 'bar', marker: {{color: '#10b981'}}}};
    var layout = {{
      barmode: 'relative',
      height: 350,
      margin: {{l: 45, r: 20, t: 25, b: 40}},
      legend: {{orientation: 'h', y: -0.25}},
      paper_bgcolor: '#ffffff',
      plot_bgcolor: '#ffffff',
      font: {{family: '-apple-system, BlinkMacSystemFont, Segoe UI, Roboto, sans-serif', size: 11, color: '#12151a'}},
      yaxis: {{title: 'Contribution (% points)', gridcolor: 'rgba(0,0,0,0.06)', zeroline: true, zerolinecolor: '#333'}},
      xaxis: {{gridcolor: 'rgba(0,0,0,0.04)'}}
    }};
    Plotly.newPlot(cpiDiv, [traceFood, traceGoods, traceEnergy, traceServices], layout, {{responsive: true}});
  }}

  // 2. Scissors Gap Chart
  var gapDiv = document.getElementById("chart-scissors-gap-{country_code}");
  if (gapDiv) {{
    var gDates = {json.dumps(sg_dates)};
    var tracePpi = {{x: gDates, y: {json.dumps(ppi_head_vals)}, name: 'Domestic PPI YoY', type: 'scatter', mode: 'lines', line: {{color: '#6366f1', width: 2.5}}}};
    var traceGap = {{x: gDates, y: {json.dumps(sg_vals)}, name: 'Scissors Gap (PPI - CPI)', type: 'bar', marker: {{color: '#0ea5e9', opacity: 0.7}}}};
    var layoutGap = {{
      height: 380,
      margin: {{l: 45, r: 20, t: 30, b: 40}},
      legend: {{orientation: 'h', y: -0.2}},
      paper_bgcolor: '#ffffff',
      plot_bgcolor: '#ffffff',
      font: {{family: '-apple-system, BlinkMacSystemFont, Segoe UI, Roboto, sans-serif', size: 11, color: '#12151a'}},
      yaxis: {{title: 'YoY Growth & Spread (pp)', gridcolor: 'rgba(0,0,0,0.06)', zeroline: true, zerolinecolor: '#333'}}
    }};
    Plotly.newPlot(gapDiv, [tracePpi, traceGap], layoutGap, {{responsive: true}});
  }}

  // 3. Expectations & Capacity Utilization Chart
  var expDiv = document.getElementById("chart-expectations-{country_code}");
  if (expDiv) {{
    var eDates = {json.dumps(exp_dates)};
    var tInd = {{x: eDates, y: {json.dumps(exp_ind_vals)}, name: 'Industry 3M Price Exp', type: 'scatter', mode: 'lines', line: {{color: '#2563eb', width: 2}}}};
    var tSrv = {{x: eDates, y: {json.dumps(exp_srv_vals)}, name: 'Services 3M Price Exp', type: 'scatter', mode: 'lines', line: {{color: '#059669', width: 2}}}};
    var tRet = {{x: eDates, y: {json.dumps(exp_ret_vals)}, name: 'Retail 3M Price Exp', type: 'scatter', mode: 'lines', line: {{color: '#d97706', width: 2}}}};
    var tCns = {{x: eDates, y: {json.dumps(exp_cns_vals)}, name: 'Consumer 12M Exp', type: 'scatter', mode: 'lines', line: {{color: '#dc2626', width: 2, dash: 'dot'}}}};
    var tCu = {{x: {json.dumps(cu_dates)}, y: {json.dumps(cu_vals)}, name: 'Capacity Util (%) [R-axis]', yaxis: 'y2', type: 'scatter', mode: 'lines', line: {{color: '#7c3aed', width: 2.2}}}};

    var layoutExp = {{
      height: 400,
      margin: {{l: 45, r: 45, t: 30, b: 40}},
      legend: {{orientation: 'h', y: -0.22}},
      paper_bgcolor: '#ffffff',
      plot_bgcolor: '#ffffff',
      font: {{family: '-apple-system, BlinkMacSystemFont, Segoe UI, Roboto, sans-serif', size: 11, color: '#12151a'}},
      yaxis: {{title: 'Price Expectations (Net Balance %)', gridcolor: 'rgba(0,0,0,0.06)', zeroline: true, zerolinecolor: '#333'}},
      yaxis2: {{title: 'Capacity Utilization (%)', overlaying: 'y', side: 'right', range: [50, 100], gridcolor: 'rgba(0,0,0,0)'}}
    }};
    Plotly.newPlot(expDiv, [tInd, tSrv, tRet, tCns, tCu], layoutExp, {{responsive: true}});
  }}
}});
</script>
<!-- ══════════════════════════════════════════════════════════════════════════ -->
"""
    cleaned_lines = [line.rstrip() for line in html_out.splitlines()]
    return "\n".join(cleaned_lines) + "\n"
