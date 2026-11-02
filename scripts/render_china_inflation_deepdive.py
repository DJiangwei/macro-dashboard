"""Renderer for Institutional China Inflation & PPI Deep-Dive Modules.

Generates sell-side institutional interactive HTML components for China:
- Table 1: CPI Inflation by product group (NBS 8 expenditure categories, pork/veg sub-items, Core CPI, goods vs services)
- Short-Term Inflation Momentum Monitor (1M, 3M, 6M annualized rates vs 12M YoY & trajectory chart)
- Table 2: Industrial PPI Breakdown (生产资料 vs 生活资料: Mining, Raw Materials, Processing, Consumer Goods)
- PPI - CPI Industrial Margin Scissors Pipeline (Spread chart, margin squeeze monitor)
- Pricing Expectations, Pork Cycle & Upstream Studio (Live hog cash price cycle, Veg Basket 200, Agri wholesale, PMI price DI)
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
  color: #b91c1c;
  background: rgba(185, 28, 28, 0.08);
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
  min-width: 220px;
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
}
.sector-cards-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 12px;
  margin-bottom: 20px;
}
.sector-card {
  background: #f8fafc;
  border: 1px solid var(--border, #e2e8f0);
  border-radius: 6px;
  padding: 12px;
  transition: all 0.2s ease;
}
.sector-card:hover {
  border-color: #cbd5e1;
  box-shadow: 0 2px 4px rgba(0,0,0,0.04);
}
.sector-card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 6px;
}
.sector-card-title {
  font-size: 12px;
  font-weight: 700;
  color: var(--fg, #1e293b);
}
.sector-card-badge {
  font-size: 10px;
  font-weight: 600;
  padding: 1px 6px;
  border-radius: 3px;
}
.badge-expand {
  background: rgba(16, 185, 129, 0.12);
  color: #047857;
}
.badge-squeeze {
  background: rgba(239, 68, 68, 0.12);
  color: #b91c1c;
}
.badge-neutral {
  background: rgba(148, 163, 184, 0.15);
  color: #475569;
}
.sector-card-val {
  font-size: 20px;
  font-weight: 700;
  color: var(--fg, #0f172a);
  font-variant-numeric: tabular-nums;
  margin-bottom: 4px;
}
.sector-card-sub {
  font-size: 11px;
  color: var(--muted, #64748b);
  display: flex;
  justify-content: space-between;
  gap: 4px;
}
.momentum-summary-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 12px;
  margin-bottom: 16px;
}
.momentum-card {
  background: #f8fafc;
  border: 1px solid var(--border, #e2e8f0);
  border-radius: 6px;
  padding: 12px 14px;
}
.momentum-card-title {
  font-size: 11px;
  font-weight: 700;
  text-transform: uppercase;
  color: var(--muted, #64748b);
  margin-bottom: 4px;
}
.momentum-card-value {
  font-size: 22px;
  font-weight: 700;
  color: var(--fg, #0f172a);
  font-variant-numeric: tabular-nums;
}
.momentum-card-foot {
  font-size: 11px;
  margin-top: 4px;
  display: flex;
  align-items: center;
  gap: 6px;
}
.signal-pill {
  font-size: 10px;
  font-weight: 700;
  padding: 1px 6px;
  border-radius: 3px;
  text-transform: uppercase;
}
</style>
"""


def _fmt(val, plus_sign=False):
    if val is None:
        return "—"
    prefix = "+" if (plus_sign and val > 0) else ""
    return f"{prefix}{val:.1f}"


def render_china_deepdive_panel():
    """Build and return full HTML for China Inflation, Momentum & Industrial Pricing Studio."""
    data_path = OUTPUT / "china_inflation_deepdive.json"
    if not data_path.exists():
        return ""

    with open(data_path, "r", encoding="utf-8") as f:
        deepdive = json.load(f)

    available_months = deepdive.get("available_months", [])
    if not available_months:
        return ""

    latest_m = available_months[0]
    cpi_tables = deepdive.get("cpi_tables", {})
    momentum_tables = deepdive.get("momentum_tables", {})
    ppi_tables = deepdive.get("ppi_tables", {})
    exp_summary = deepdive.get("expectations_summary", {})
    ts = deepdive.get("time_series", {})

    # Build Table 1 Month Views
    table1_month_views = []
    for m in available_months:
        t_data = cpi_tables.get(m)
        if not t_data:
            continue
        display_style = "display: block;" if m == latest_m else "display: none;"
        cur_dt = t_data.get("date", m)
        prev_dt = t_data.get("prev_date", "")
        ago_dt = t_data.get("ago_date", "")

        def _fmt_hdr(dt_str):
            if not dt_str:
                return "—"
            try:
                from datetime import datetime
                d = datetime.strptime(dt_str, "%Y-%m")
                return d.strftime("%b-%y")
            except Exception:
                return dt_str

        hdr_cur = _fmt_hdr(cur_dt)
        hdr_prev = _fmt_hdr(prev_dt)

        # Headline Row
        hd = t_data.get("headline", {})
        hd_yoy = _fmt(hd.get("yoy"))
        hd_yoy_prev = _fmt(hd.get("yoy_prev"))
        hd_mom = _fmt(hd.get("mom"))
        hd_mom_ago = _fmt(hd.get("mom_ago"))
        hd_contrib_mom = _fmt(hd.get("contrib_mom"))

        tbody_rows = []
        tbody_rows.append(f"""
          <tr class="row-headline">
            <td class="col-name"><span data-lang="en">Headline CPI (全国居民消费价格)</span><span data-lang="zh">全国居民消费价格 (CPI总指数)</span></td>
            <td class="col-num col-weight">100.0</td>
            <td class="col-num"><strong>{hd_yoy}</strong></td>
            <td class="col-num text-muted">{hd_yoy_prev}</td>
            <td class="col-num"></td>
            <td class="col-num">{hd_mom}</td>
            <td class="col-num text-muted">{hd_mom_ago}</td>
            <td class="col-num">{hd_contrib_mom}</td>
          </tr>
        """)

        # Categories & Sub-items
        for cat in t_data.get("items", []):
            code = cat.get("code")
            name_en = escape(cat.get("name_en", ""))
            name_zh = escape(cat.get("name_zh", ""))
            w = _fmt(cat.get("weight"))
            yoy = _fmt(cat.get("yoy"))
            yoy_p = _fmt(cat.get("yoy_prev"))
            c_yoy = _fmt(cat.get("contrib_yoy"))
            mom = _fmt(cat.get("mom"))
            mom_a = _fmt(cat.get("mom_ago"))
            c_mom = _fmt(cat.get("contrib_mom"))

            sub_items = cat.get("sub_items", [])
            has_sub = len(sub_items) > 0
            toggle_html = f'<button class="sub-toggle-btn" onclick="toggleSubRows(\'cn-{code}-{m}\', this)">▼</button>' if has_sub else '<span class="sub-placeholder"></span>'

            tbody_rows.append(f"""
              <tr class="row-division">
                <td class="col-name">{toggle_html}<span data-lang="en">{name_en}</span><span data-lang="zh">{name_zh}</span></td>
                <td class="col-num col-weight">{w}</td>
                <td class="col-num"><strong>{yoy}</strong></td>
                <td class="col-num text-muted">{yoy_p}</td>
                <td class="col-num">{c_yoy}</td>
                <td class="col-num">{mom}</td>
                <td class="col-num text-muted">{mom_a}</td>
                <td class="col-num">{c_mom}</td>
              </tr>
            """)

            for sub in sub_items:
                s_code = sub.get("code")
                s_name_en = escape(sub.get("name_en", ""))
                s_name_zh = escape(sub.get("name_zh", ""))
                s_w = _fmt(sub.get("weight"))
                s_yoy = _fmt(sub.get("yoy"))
                s_yoy_p = _fmt(sub.get("yoy_prev"))
                s_c_yoy = _fmt(sub.get("contrib_yoy"))
                s_mom = _fmt(sub.get("mom"))
                s_mom_a = _fmt(sub.get("mom_ago"))
                s_c_mom = _fmt(sub.get("contrib_mom"))

                tbody_rows.append(f"""
                  <tr class="row-subitem cn-subitem-cn-{code}-{m}">
                    <td class="col-name col-sub"><span class="sub-tree-prefix">↳ </span><span data-lang="en">{s_name_en}</span><span data-lang="zh">{s_name_zh}</span></td>
                    <td class="col-num col-weight">{s_w}</td>
                    <td class="col-num">{s_yoy}</td>
                    <td class="col-num text-muted">{s_yoy_p}</td>
                    <td class="col-num">{s_c_yoy}</td>
                    <td class="col-num">{s_mom}</td>
                    <td class="col-num text-muted">{s_mom_a}</td>
                    <td class="col-num">{s_c_mom}</td>
                  </tr>
                """)

        # Separator for Memo items
        tbody_rows.append('<tr class="row-separator"><td colspan="8"></td></tr>')

        # Memo items
        for memo in t_data.get("memo", []):
            m_name_en = escape(memo.get("name_en", ""))
            m_name_zh = escape(memo.get("name_zh", ""))
            m_w = _fmt(memo.get("weight")) if memo.get("weight") is not None else ""
            m_yoy = _fmt(memo.get("yoy"))
            m_yoy_p = _fmt(memo.get("yoy_prev"))
            m_c_yoy = _fmt(memo.get("contrib_yoy")) if memo.get("contrib_yoy") is not None else ""
            m_mom = _fmt(memo.get("mom"))
            m_mom_a = _fmt(memo.get("mom_ago"))
            m_c_mom = _fmt(memo.get("contrib_mom")) if memo.get("contrib_mom") is not None else ""

            tbody_rows.append(f"""
              <tr class="row-memo">
                <td class="col-name"><span data-lang="en">{m_name_en}</span><span data-lang="zh">{m_name_zh}</span></td>
                <td class="col-num col-weight">{m_w}</td>
                <td class="col-num"><strong>{m_yoy}</strong></td>
                <td class="col-num text-muted">{m_yoy_p}</td>
                <td class="col-num">{m_c_yoy}</td>
                <td class="col-num">{m_mom}</td>
                <td class="col-num text-muted">{m_mom_a}</td>
                <td class="col-num">{m_c_mom}</td>
              </tr>
            """)

        rows_html = "".join(tbody_rows)
        table1_month_views.append(f"""
        <div id="cpi-month-view-cn-{m}" class="cpi-month-view-cn" style="{display_style}">
          <div class="table-responsive">
            <table class="inflation-table">
              <thead>
                <tr class="th-tier1">
                  <th rowspan="2" class="col-name"><span data-lang="en">Product Group (NBS 8 Categories)</span><span data-lang="zh">消费类别 (统计局8大类及核心细项)</span></th>
                  <th rowspan="2" class="col-num col-weight"><span data-lang="en">Weights</span><span data-lang="zh">权重比重</span></th>
                  <th colspan="3" class="col-group-header">y/y</th>
                  <th colspan="3" class="col-group-header">m/m</th>
                </tr>
                <tr class="th-tier2">
                  <th class="col-num"><strong>{hdr_cur}</strong></th>
                  <th class="col-num text-muted">{hdr_prev}</th>
                  <th class="col-num">Contrib* to y/y</th>
                  <th class="col-num"><strong>{hdr_cur}</strong></th>
                  <th class="col-num text-muted">1Y ago</th>
                  <th class="col-num">Contrib* to m/m</th>
                </tr>
              </thead>
              <tbody>
                {rows_html}
              </tbody>
            </table>
          </div>
        </div>
        """)

    table1_all_html = "".join(table1_month_views)

    # Options for Month Select dropdown
    month_options = "\n".join([f'<option value="{m}" {"selected" if m == latest_m else ""}>{m}</option>' for m in available_months])

    # Build Momentum Table (Tab 2)
    mom_m_data = momentum_tables.get(latest_m, {})
    mom_rows = []
    for it in mom_m_data.get("items", []):
        n_en = escape(it.get("name_en", ""))
        n_zh = escape(it.get("name_zh", ""))
        w = _fmt(it.get("weight"))
        m1 = _fmt(it.get("mom_1m_ann"))
        m3 = _fmt(it.get("mom_3m_ann"))
        m6 = _fmt(it.get("mom_6m_ann"))
        yoy = _fmt(it.get("yoy"))
        gap = _fmt(it.get("gap"), plus_sign=True)
        sig_en = escape(it.get("signal_en", ""))
        sig_zh = escape(it.get("signal_zh", ""))
        bdg = it.get("badge", "badge-neutral")
        icn = it.get("icon", "▬")

        mom_rows.append(f"""
          <tr class="row-division">
            <td class="col-name"><span data-lang="en">{n_en}</span><span data-lang="zh">{n_zh}</span></td>
            <td class="col-num col-weight">{w}</td>
            <td class="col-num">{m1}</td>
            <td class="col-num"><strong>{m3}</strong></td>
            <td class="col-num">{m6}</td>
            <td class="col-num">{yoy}</td>
            <td class="col-num"><strong>{gap}</strong></td>
            <td class="col-num"><span class="signal-pill {bdg}">{icn} <span data-lang="en">{sig_en}</span><span data-lang="zh">{sig_zh}</span></span></td>
          </tr>
        """)
    mom_rows_html = "".join(mom_rows)

    # Build PPI Table (Tab 3)
    ppi_m_data = ppi_tables.get(latest_m, {})
    ppi_hd = ppi_m_data.get("headline", {})
    ppi_rows = []
    ppi_rows.append(f"""
      <tr class="row-headline">
        <td class="col-name"><span data-lang="en">Domestic PPI (工业生产者出厂价格指数)</span><span data-lang="zh">工业品出厂价格总指数 (PPI)</span></td>
        <td class="col-num col-weight">100.0</td>
        <td class="col-num"><strong>{_fmt(ppi_hd.get('yoy'))}</strong></td>
        <td class="col-num text-muted">{_fmt(ppi_hd.get('yoy_prev'))}</td>
        <td class="col-num"></td>
        <td class="col-num">{_fmt(ppi_hd.get('mom'))}</td>
        <td class="col-num text-muted">{_fmt(ppi_hd.get('mom_ago'))}</td>
        <td class="col-num">{_fmt(ppi_hd.get('contrib_mom'))}</td>
      </tr>
    """)

    for pcat in ppi_m_data.get("items", []):
        p_code = pcat.get("code")
        p_en = escape(pcat.get("name_en", ""))
        p_zh = escape(pcat.get("name_zh", ""))
        p_w = _fmt(pcat.get("weight"))
        p_yoy = _fmt(pcat.get("yoy"))
        p_yoy_p = _fmt(pcat.get("yoy_prev"))
        p_c_yoy = _fmt(pcat.get("contrib_yoy"))
        p_mom = _fmt(pcat.get("mom"))
        p_mom_a = _fmt(pcat.get("mom_ago"))
        p_c_mom = _fmt(pcat.get("contrib_mom"))

        p_subs = pcat.get("sub_items", [])
        has_p_sub = len(p_subs) > 0
        p_toggle = f'<button class="sub-toggle-btn" onclick="toggleSubRows(\'cn-ppi-{p_code}-{latest_m}\', this)">▼</button>' if has_p_sub else '<span class="sub-placeholder"></span>'

        ppi_rows.append(f"""
          <tr class="row-division">
            <td class="col-name">{p_toggle}<span data-lang="en">{p_en}</span><span data-lang="zh">{p_zh}</span></td>
            <td class="col-num col-weight">{p_w}</td>
            <td class="col-num"><strong>{p_yoy}</strong></td>
            <td class="col-num text-muted">{p_yoy_p}</td>
            <td class="col-num">{p_c_yoy}</td>
            <td class="col-num">{p_mom}</td>
            <td class="col-num text-muted">{p_mom_a}</td>
            <td class="col-num">{p_c_mom}</td>
          </tr>
        """)

        for psub in p_subs:
            ps_en = escape(psub.get("name_en", ""))
            ps_zh = escape(psub.get("name_zh", ""))
            ps_w = _fmt(psub.get("weight"))
            ps_yoy = _fmt(psub.get("yoy"))
            ps_yoy_p = _fmt(psub.get("yoy_prev"))
            ps_c_yoy = _fmt(psub.get("contrib_yoy"))
            ps_mom = _fmt(psub.get("mom"))
            ps_mom_a = _fmt(psub.get("mom_ago"))
            ps_c_mom = _fmt(psub.get("contrib_mom"))

            ppi_rows.append(f"""
              <tr class="row-subitem cn-subitem-cn-ppi-{p_code}-{latest_m}">
                <td class="col-name col-sub"><span class="sub-tree-prefix">↳ </span><span data-lang="en">{ps_en}</span><span data-lang="zh">{ps_zh}</span></td>
                <td class="col-num col-weight">{ps_w}</td>
                <td class="col-num">{ps_yoy}</td>
                <td class="col-num text-muted">{ps_yoy_p}</td>
                <td class="col-num">{ps_c_yoy}</td>
                <td class="col-num">{ps_mom}</td>
                <td class="col-num text-muted">{ps_mom_a}</td>
                <td class="col-num">{ps_c_mom}</td>
              </tr>
            """)
    ppi_rows_html = "".join(ppi_rows)

    # Expectations Gauge Cards (Tab 5)
    hog_data = exp_summary.get("hog_spot_price", {})
    veg_data = exp_summary.get("veg_basket_200", {})
    agri_data = exp_summary.get("agri_wholesale_index", {})
    pmi_data = exp_summary.get("pmi_price_indices", {})
    cap_data = exp_summary.get("capacity_utilization", {})

    # Time series JSON payloads for Plotly
    ts_dates = ts.get("dates", [])
    ts_cpi = ts.get("cpi_yoy", [])
    ts_core = ts.get("core_yoy", [])
    ts_ppi = ts.get("ppi_yoy", [])
    ts_scissors = ts.get("scissors_spread", [])
    ts_ent = ts.get("enterprise_goods_yoy", [])

    # Momentum chart series
    mom_dates = sorted(list(momentum_tables.keys()))
    mom_h3 = [momentum_tables[d].get("headline_ann_3m") for d in mom_dates]
    mom_hy = [momentum_tables[d].get("headline_yoy") for d in mom_dates]
    mom_c3 = [momentum_tables[d].get("core_ann_3m") for d in mom_dates]
    mom_cy = [momentum_tables[d].get("core_yoy") for d in mom_dates]

    # Hog cycle series
    hog_cycle_list = ts.get("hog_cycle", [])
    hog_dates = [r.get("date") for r in hog_cycle_list]
    hog_spots = [r.get("price_spot") for r in hog_cycle_list]
    hog_indices = [r.get("index") for r in hog_cycle_list]
    hog_ma12 = [r.get("ma_12m") for r in hog_cycle_list]

    html = f"""
{DEEPDIVE_CSS}
<div class="deepdive-macro-panel" id="deepdive-inflation-CN">
  <div class="deepdive-header">
    <div class="deepdive-title-wrap">
      <span class="deepdive-badge">China Inflation & Pricing Studio</span>
      <h3 class="deepdive-title">
        <span data-lang="en">China Inflation, Pork Cycle & Industrial Pricing Studio</span>
        <span data-lang="zh">中国通胀分解、生猪供给周期与工业定价全景监控</span>
      </h3>
      <p class="deepdive-subtitle">
        <span data-lang="en">National Bureau of Statistics 8 expenditure categories, pork/veg sub-items, 1M/3M/6M momentum & PPI margin scissors.</span>
        <span data-lang="zh">国家统计局 8 大类生活消费支出、生猪现金均价周期、短期动能年化跟踪与 PPI-CPI 工业利润剪刀差。</span>
      </p>
    </div>
    <div class="deepdive-tabs">
      <button class="deepdive-tab active" onclick="switchDeepdiveTab('cn-cpi-breakdown', this)">
        <span data-lang="en">Table 1: CPI by Product Group</span><span data-lang="zh">表1: CPI分项贡献表</span>
      </button>
      <button class="deepdive-tab" onclick="switchDeepdiveTab('cn-momentum', this)">
        <span data-lang="en">Short-Term Momentum</span><span data-lang="zh">短期通胀动能监控</span>
      </button>
      <button class="deepdive-tab" onclick="switchDeepdiveTab('cn-ppi-matrix', this)">
        <span data-lang="en">Table 2: Industrial PPI</span><span data-lang="zh">表2: PPI生产与生活资料</span>
      </button>
      <button class="deepdive-tab" onclick="switchDeepdiveTab('cn-margin-scissors', this)">
        <span data-lang="en">Margin Scissors</span><span data-lang="zh">PPI-CPI 利润剪刀差</span>
      </button>
      <button class="deepdive-tab" onclick="switchDeepdiveTab('cn-expectations', this)">
        <span data-lang="en">Expectations & Pork Cycle</span><span data-lang="zh">预期与生猪周期高频</span>
      </button>
    </div>
  </div>

  <!-- TAB 1: CPI BREAKDOWN TABLE 1 -->
  <div id="cn-cpi-breakdown" class="deepdive-tab-content active">
    <div class="table-toolbar">
      <div class="table-caption">
        <strong>Table 1: CPI Inflation by product group</strong>
        <span class="text-muted">(NBS 8 Categories, %, additive contributions to headline)</span>
      </div>
      <div>
        <label for="cn-month-selector" style="font-size: 12px; margin-right: 6px; color: var(--muted, #64748b);">
          <span data-lang="en">Reporting Period:</span><span data-lang="zh">统计报告期:</span>
        </label>
        <select id="cn-month-selector" class="month-select" onchange="switchCpiMonthCN(this.value)">
          {month_options}
        </select>
      </div>
    </div>

    {table1_all_html}

    <div class="table-footnote">
      <span data-lang="en">* Note: Contrib to y/y and m/m are additive percentage point contributions summing directly to Headline CPI. Sub-items (↳) can be toggled using the arrows. Data source: National Bureau of Statistics (NBS) & AKShare Eastmoney Data Center.</span>
      <span data-lang="zh">* 注：Contrib 贡献率为百分点贡献，各分项加总等于 CPI 总指数。点击 ↳ 可折叠/展开细项。数据来源：国家统计局 (NBS) 及东方财富数据中心宏观镜像。</span>
    </div>

    <div class="subchart-container">
      <div class="subchart-header">
        <h4><span data-lang="en">China CPI 8 Expenditure Categories YoY Trajectory (%)</span><span data-lang="zh">中国 CPI 8 大类消费支出同比演进趋势 (%)</span></h4>
        <span class="text-muted" style="font-size: 11px;">2022 – Present</span>
      </div>
      <div id="deepdive-chart-cn-cpi-categories" style="width: 100%; height: 360px;"></div>
    </div>
  </div>

  <!-- TAB 2: SHORT-TERM MOMENTUM -->
  <div id="cn-momentum" class="deepdive-tab-content">
    <div class="momentum-summary-grid">
      <div class="momentum-card">
        <div class="momentum-card-title"><span data-lang="en">Headline CPI 3M Ann.</span><span data-lang="zh">CPI 总指数 3M 年化</span></div>
        <div class="momentum-card-value">{_fmt(mom_m_data.get('headline_ann_3m'))}%</div>
        <div class="momentum-card-foot">
          <span class="text-muted">vs 12M YoY: {_fmt(mom_m_data.get('headline_yoy'))}%</span>
          <span class="signal-pill badge-expand">Gap: {_fmt(mom_m_data.get('headline_gap'), plus_sign=True)}pp</span>
        </div>
      </div>
      <div class="momentum-card">
        <div class="momentum-card-title"><span data-lang="en">Core CPI 3M Ann.</span><span data-lang="zh">核心 CPI 3M 年化</span></div>
        <div class="momentum-card-value">{_fmt(mom_m_data.get('core_ann_3m'))}%</div>
        <div class="momentum-card-foot">
          <span class="text-muted">vs 12M YoY: {_fmt(mom_m_data.get('core_yoy'))}%</span>
          <span class="signal-pill badge-neutral">Gap: {_fmt(mom_m_data.get('core_gap'), plus_sign=True)}pp</span>
        </div>
      </div>
      <div class="momentum-card">
        <div class="momentum-card-title"><span data-lang="en">Pork Supply Phase</span><span data-lang="zh">生猪周期运行阶段</span></div>
        <div class="momentum-card-value" style="font-size: 17px; line-height: 26px;">
          <span data-lang="en">{escape(hog_data.get('phase_en', 'Bottoming'))}</span>
          <span data-lang="zh">{escape(hog_data.get('phase_zh', '去产能筑底'))}</span>
        </div>
        <div class="momentum-card-foot">
          <span class="text-muted">Spot: {hog_data.get('value', 9.7)} CNY/kg</span>
          <span class="signal-pill badge-squeeze">Drag</span>
        </div>
      </div>
      <div class="momentum-card">
        <div class="momentum-card-title"><span data-lang="en">Industrial PPI Momentum</span><span data-lang="zh">工业品出厂 PPI 动能</span></div>
        <div class="momentum-card-value" style="color: #b91c1c;">{_fmt(ppi_hd.get('yoy'))}%</div>
        <div class="momentum-card-foot">
          <span class="text-muted">MoM: {_fmt(ppi_hd.get('mom'))}%</span>
          <span class="signal-pill badge-squeeze">Contraction</span>
        </div>
      </div>
    </div>

    <div class="table-responsive">
      <table class="inflation-table">
        <thead>
          <tr class="th-tier1">
            <th rowspan="2" class="col-name"><span data-lang="en">Indicator Track / Category</span><span data-lang="zh">通胀监测维度 / 分类分项</span></th>
            <th rowspan="2" class="col-num col-weight"><span data-lang="en">Weights</span><span data-lang="zh">权重</span></th>
            <th colspan="3" class="col-group-header">Annualized Rates (%)</th>
            <th rowspan="2" class="col-num">12M YoY</th>
            <th rowspan="2" class="col-num">Gap (3M-12M)</th>
            <th rowspan="2" class="col-num">Regime Signal</th>
          </tr>
          <tr class="th-tier2">
            <th class="col-num">1M Ann.</th>
            <th class="col-num">3M Ann.</th>
            <th class="col-num">6M Ann.</th>
          </tr>
        </thead>
        <tbody>
          {mom_rows_html}
        </tbody>
      </table>
    </div>
    <div class="table-footnote">
      <span data-lang="en">Annualized rates compounded as ((1+r)^k - 1)*100. Gap = 3M Annualized rate minus 12M YoY rate. A positive gap (>0.3pp) indicates reflationary acceleration; a negative gap (<-0.8pp) flags deflationary persistence.</span>
      <span data-lang="zh">动能年化按标准复利 ((1+r)^k - 1)*100 计算。动能裂口 (Gap) = 3M年化率减去12M同比率。正裂口(>0.3pp)代表再通胀加速，深负裂口(<-0.8pp)代表通缩压力延续。</span>
    </div>

    <div class="subchart-container">
      <div class="subchart-header">
        <h4><span data-lang="en">China Inflation Momentum Trajectory: 3M Annualized vs 12M YoY (%)</span><span data-lang="zh">短期通胀动能走势：3M 年化动能 vs 12M 同比基准 (%)</span></h4>
        <span class="text-muted" style="font-size: 11px;">Monthly Compounded Track</span>
      </div>
      <div id="deepdive-chart-cn-momentum" style="width: 100%; height: 360px;"></div>
    </div>
  </div>

  <!-- TAB 3: INDUSTRIAL PPI BREAKDOWN -->
  <div id="cn-ppi-matrix" class="deepdive-tab-content">
    <div class="table-toolbar">
      <div class="table-caption">
        <strong>Table 2: Producer Price Index (PPI) by Stage of Production</strong>
        <span class="text-muted">(NBS Domestic PPI, 生产资料 vs 生活资料)</span>
      </div>
      <div class="text-muted" style="font-size: 12px;">Reporting Month: <strong>{latest_m}</strong></div>
    </div>

    <div class="table-responsive">
      <table class="inflation-table">
        <thead>
          <tr class="th-tier1">
            <th rowspan="2" class="col-name"><span data-lang="en">Production Sector / Sub-item</span><span data-lang="zh">工业行业大类 / 生产资料与生活资料</span></th>
            <th rowspan="2" class="col-num col-weight"><span data-lang="en">Weights</span><span data-lang="zh">估算权重</span></th>
            <th colspan="3" class="col-group-header">y/y</th>
            <th colspan="3" class="col-group-header">m/m</th>
          </tr>
          <tr class="th-tier2">
            <th class="col-num"><strong>{latest_m}</strong></th>
            <th class="col-num text-muted">Prev Month</th>
            <th class="col-num">Contrib to y/y</th>
            <th class="col-num"><strong>{latest_m}</strong></th>
            <th class="col-num text-muted">1Y ago</th>
            <th class="col-num">Contrib to m/m</th>
          </tr>
        </thead>
        <tbody>
          {ppi_rows_html}
        </tbody>
      </table>
    </div>
    <div class="table-footnote">
      <span data-lang="en">Data source: National Bureau of Statistics Industrial Producer Price Survey. Production Materials account for ~75% and Living Materials for ~25% of Chinese factory-gate PPI.</span>
      <span data-lang="zh">数据来源：国家统计局工业生产者出厂价格调查。生产资料占出厂PPI比重约75%，生活资料占约25%。</span>
    </div>
  </div>

  <!-- TAB 4: MARGIN SCISSORS -->
  <div id="cn-margin-scissors" class="deepdive-tab-content">
    <div class="subchart-container" style="margin-top: 0; border-top: none; padding-top: 0;">
      <div class="subchart-header">
        <h4><span data-lang="en">PPI - CPI Industrial Margin Scissors & Transmission (pp)</span><span data-lang="zh">PPI - CPI 工业利润剪刀差与价格传导机制 (百分点)</span></h4>
        <span class="text-muted" style="font-size: 11px;">Spread = PPI YoY - CPI YoY</span>
      </div>
      <div id="deepdive-chart-cn-scissors" style="width: 100%; height: 380px;"></div>
    </div>
    <div class="table-footnote">
      <span data-lang="en">Analytical Framework: When PPI - CPI > 0 (Upstream Expansion Zone), upstream mining and raw material producers capture higher pricing power, elevating intermediate input costs. When PPI - CPI < 0 (Downstream Compression / Deflationary Drag Zone), downstream firms absorb factory-gate deflation without retail elasticity, suppressing corporate operating profits.</span>
      <span data-lang="zh">分析框架：当 PPI - CPI > 0（上游利润扩张区），上游采掘与原材料行业议价能力增强，中下游面临成本推升；当 PPI - CPI < 0（工业通缩承压区），工业品价格持续低于消费终端，反映需求不足与中下游利润承压。</span>
    </div>
  </div>

  <!-- TAB 5: EXPECTATIONS & PORK CYCLE -->
  <div id="cn-expectations" class="deepdive-tab-content">
    <div class="sector-cards-grid">
      <!-- Card 1: Hog Spot Price -->
      <div class="sector-card">
        <div class="sector-card-header">
          <span class="sector-card-title"><span data-lang="en">Live Hog Spot Price</span><span data-lang="zh">全国生猪出栏现金均价</span></span>
          <span class="sector-card-badge badge-squeeze"><span data-lang="en">Pork Cycle</span><span data-lang="zh">生猪周期</span></span>
        </div>
        <div class="sector-card-val">{hog_data.get('value', 9.7)} <span style="font-size: 13px; font-weight: normal; color: var(--muted, #64748b);">CNY/kg</span></div>
        <div class="sector-card-sub">
          <span>{hog_data.get('date', '2026-10-26')}</span>
          <span>12M MA: {hog_data.get('ma_12m', 74.36)}</span>
          <span>Pct: {hog_data.get('percentile', 28.0)}%</span>
        </div>
        <p style="font-size: 11px; margin: 8px 0 0 0; color: var(--text-secondary, #475569); line-height: 1.35;">
          <span data-lang="en">{escape(hog_data.get('eval_en', ''))}</span>
          <span data-lang="zh">{escape(hog_data.get('eval_zh', ''))}</span>
        </p>
      </div>

      <!-- Card 2: Veg Basket 200 -->
      <div class="sector-card">
        <div class="sector-card-header">
          <span class="sector-card-title"><span data-lang="en">Veg Basket 200 Index</span><span data-lang="zh">菜篮子批发价格 200 指数</span></span>
          <span class="sector-card-badge badge-neutral"><span data-lang="en">Wholesale Food</span><span data-lang="zh">批发食品</span></span>
        </div>
        <div class="sector-card-val">{veg_data.get('value', 114.92)}</div>
        <div class="sector-card-sub">
          <span>{veg_data.get('date', '2026-10-09')}</span>
          <span>Pct: {veg_data.get('percentile', 42.5)}%</span>
        </div>
        <p style="font-size: 11px; margin: 8px 0 0 0; color: var(--text-secondary, #475569); line-height: 1.35;">
          <span data-lang="en">{escape(veg_data.get('eval_en', ''))}</span>
          <span data-lang="zh">{escape(veg_data.get('eval_zh', ''))}</span>
        </p>
      </div>

      <!-- Card 3: Agricultural Wholesale Index -->
      <div class="sector-card">
        <div class="sector-card-header">
          <span class="sector-card-title"><span data-lang="en">Agri Wholesale Index</span><span data-lang="zh">农产品批发价格指数</span></span>
          <span class="sector-card-badge badge-neutral"><span data-lang="en">Farm Input</span><span data-lang="zh">农贸总成</span></span>
        </div>
        <div class="sector-card-val">{agri_data.get('value', 114.78)}</div>
        <div class="sector-card-sub">
          <span>{agri_data.get('date', '2026-10-09')}</span>
          <span>Pct: {agri_data.get('percentile', 41.0)}%</span>
        </div>
        <p style="font-size: 11px; margin: 8px 0 0 0; color: var(--text-secondary, #475569); line-height: 1.35;">
          <span data-lang="en">{escape(agri_data.get('eval_en', ''))}</span>
          <span data-lang="zh">{escape(agri_data.get('eval_zh', ''))}</span>
        </p>
      </div>

      <!-- Card 4: PMI Output vs Input Prices -->
      <div class="sector-card">
        <div class="sector-card-header">
          <span class="sector-card-title"><span data-lang="en">PMI Output vs Input DI</span><span data-lang="zh">制造业 PMI 出厂与购进价格</span></span>
          <span class="sector-card-badge badge-squeeze"><span data-lang="en">Spread -2.4</span><span data-lang="zh">价差 -2.4</span></span>
        </div>
        <div class="sector-card-val">{pmi_data.get('pmi_output_price', 47.8)} <span style="font-size: 13px; font-weight: normal; color: var(--muted, #64748b);">vs In: {pmi_data.get('pmi_input_price', 50.2)}</span></div>
        <div class="sector-card-sub">
          <span>{pmi_data.get('date', '2026-09-30')}</span>
          <span>Output < 50 (Contraction)</span>
        </div>
        <p style="font-size: 11px; margin: 8px 0 0 0; color: var(--text-secondary, #475569); line-height: 1.35;">
          <span data-lang="en">{escape(pmi_data.get('eval_en', ''))}</span>
          <span data-lang="zh">{escape(pmi_data.get('eval_zh', ''))}</span>
        </p>
      </div>

      <!-- Card 5: Capacity Utilization -->
      <div class="sector-card">
        <div class="sector-card-header">
          <span class="sector-card-title"><span data-lang="en">Capacity Utilization</span><span data-lang="zh">制造业产能利用率</span></span>
          <span class="sector-card-badge badge-neutral"><span data-lang="en">NBS Q3</span><span data-lang="zh">统计局三季度</span></span>
        </div>
        <div class="sector-card-val">{cap_data.get('value', 75.1)}%</div>
        <div class="sector-card-sub">
          <span>Benchmark: {cap_data.get('corridor', '74% - 78%')}</span>
          <span>Pct: {cap_data.get('percentile', 32.0)}%</span>
        </div>
        <p style="font-size: 11px; margin: 8px 0 0 0; color: var(--text-secondary, #475569); line-height: 1.35;">
          <span data-lang="en">{escape(cap_data.get('eval_en', ''))}</span>
          <span data-lang="zh">{escape(cap_data.get('eval_zh', ''))}</span>
        </p>
      </div>
    </div>

    <div class="subchart-container" style="margin-top: 0; border-top: none; padding-top: 0;">
      <div class="subchart-header">
        <h4><span data-lang="en">China Pork Cycle & Wholesale Food Pipeline: Cash Hog Spot vs Veg Basket 200</span><span data-lang="zh">中国生猪周期与农产品高频通道：生猪现金价 vs 菜篮子200指数</span></h4>
        <span class="text-muted" style="font-size: 11px;">Dual-Axis Weekly Tracking</span>
      </div>
      <div id="deepdive-chart-cn-hog-cycle" style="width: 100%; height: 380px;"></div>
    </div>
  </div>
</div>

<script>
function switchDeepdiveTab(tabId, btn) {{
  var parent = btn.closest('.deepdive-macro-panel');
  if (!parent) return;
  var tabs = parent.querySelectorAll('.deepdive-tab');
  tabs.forEach(function(t) {{ t.classList.remove('active'); }});
  btn.classList.add('active');

  var contents = parent.querySelectorAll('.deepdive-tab-content');
  contents.forEach(function(c) {{ c.classList.remove('active'); }});

  var target = document.getElementById(tabId);
  if (target) {{
    target.classList.add('active');
    // Trigger Plotly relayout to redraw charts in newly shown tab
    setTimeout(function() {{
      window.dispatchEvent(new Event('resize'));
    }}, 50);
  }}
}}

function switchCpiMonthCN(selectedMonth) {{
  var allViews = document.querySelectorAll('.cpi-month-view-cn');
  allViews.forEach(function(v) {{
    v.style.display = 'none';
  }});
  var target = document.getElementById('cpi-month-view-cn-' + selectedMonth);
  if (target) {{
    target.style.display = 'block';
  }}
}}

function toggleSubRows(groupKey, btn) {{
  var rows = document.querySelectorAll('.cn-subitem-' + groupKey);
  var isExpanded = btn.textContent === '▼';
  rows.forEach(function(r) {{
    r.style.display = isExpanded ? 'none' : 'table-row';
  }});
  btn.textContent = isExpanded ? '▶' : '▼';
}}

// Initialize Plotly Charts for China Deep-Dive
document.addEventListener("DOMContentLoaded", function() {{
  if (typeof Plotly === "undefined") return;

  // 1. CPI 8 Categories YoY Trajectory
  var catDiv = document.getElementById("deepdive-chart-cn-cpi-categories");
  if (catDiv) {{
    var cDates = {json.dumps(ts_dates)};
    var cHead = {json.dumps(ts_cpi)};
    var cCore = {json.dumps(ts_core)};
    var lastDate = cDates.length ? cDates[cDates.length - 1] : '';
    var lastHead = cHead.length ? cHead[cHead.length - 1] : 0;
    var lastCore = cCore.length ? cCore[cCore.length - 1] : 0;

    var traceHead = {{
      x: cDates, y: cHead, name: 'Headline CPI YoY',
      type: 'scatter', mode: 'lines+markers',
      line: {{color: '#b91c1c', width: 2.8}}, marker: {{size: 5}}
    }};
    var traceCore = {{
      x: cDates, y: cCore, name: 'Core CPI YoY',
      type: 'scatter', mode: 'lines',
      line: {{color: '#2563eb', width: 2.2, dash: 'dash'}}
    }};

    var layoutCat = {{
      height: 360,
      margin: {{l: 40, r: 80, t: 30, b: 40}},
      legend: {{orientation: 'h', y: -0.22}},
      paper_bgcolor: '#ffffff',
      plot_bgcolor: '#ffffff',
      font: {{family: '-apple-system, BlinkMacSystemFont, Segoe UI, Roboto, sans-serif', size: 11, color: '#12151a'}},
      yaxis: {{title: 'YoY Growth Rate (%)', gridcolor: 'rgba(0,0,0,0.06)', zeroline: true, zerolinecolor: '#333'}},
      shapes: [
        {{type: 'line', xref: 'paper', x0: 0, x1: 1, yref: 'y', y0: 0, y1: 0, line: {{color: '#94a3b8', width: 1, dash: 'solid'}}}}
      ],
      annotations: [
        {{
          x: lastDate, y: lastHead, xref: 'x', yref: 'y',
          text: 'CPI: ' + (lastHead > 0 ? '+' : '') + lastHead.toFixed(1) + '%',
          showarrow: true, arrowhead: 2, arrowsize: 1, arrowwidth: 1.5, arrowcolor: '#b91c1c',
          ax: 35, ay: -18, bgcolor: '#b91c1c',
          font: {{color: '#ffffff', size: 10, family: 'monospace', weight: 'bold'}}, borderpad: 3
        }},
        {{
          x: lastDate, y: lastCore, xref: 'x', yref: 'y',
          text: 'Core: ' + (lastCore > 0 ? '+' : '') + lastCore.toFixed(1) + '%',
          showarrow: true, arrowhead: 2, arrowsize: 1, arrowwidth: 1.5, arrowcolor: '#2563eb',
          ax: 35, ay: 18, bgcolor: '#2563eb',
          font: {{color: '#ffffff', size: 10, family: 'monospace', weight: 'bold'}}, borderpad: 3
        }}
      ]
    }};
    Plotly.newPlot(catDiv, [traceHead, traceCore], layoutCat, {{responsive: true}});
  }}

  // 2. Momentum Trajectory Chart
  var momDiv = document.getElementById("deepdive-chart-cn-momentum");
  if (momDiv) {{
    var mDates = {json.dumps(mom_dates)};
    var mHead3 = {json.dumps(mom_h3)};
    var mHeadY = {json.dumps(mom_hy)};
    var mCore3 = {json.dumps(mom_c3)};
    var mCoreY = {json.dumps(mom_cy)};

    var lDate = mDates.length ? mDates[mDates.length - 1] : '';
    var lH3 = mHead3.length ? mHead3[mHead3.length - 1] : 0;
    var lHY = mHeadY.length ? mHeadY[mHeadY.length - 1] : 0;
    var lC3 = mCore3.length ? mCore3[mCore3.length - 1] : 0;

    var trH3 = {{x: mDates, y: mHead3, name: 'Headline 3M Ann.', type: 'scatter', mode: 'lines+markers', line: {{color: '#2563eb', width: 2.5}}, marker: {{size: 5}}}};
    var trHY = {{x: mDates, y: mHeadY, name: 'Headline 12M YoY', type: 'scatter', mode: 'lines', line: {{color: '#93c5fd', width: 1.8, dash: 'dot'}}}};
    var trC3 = {{x: mDates, y: mCore3, name: 'Core 3M Ann.', type: 'scatter', mode: 'lines+markers', line: {{color: '#dc2626', width: 2.2}}, marker: {{size: 5}}}};
    var trCY = {{x: mDates, y: mCoreY, name: 'Core 12M YoY', type: 'scatter', mode: 'lines', line: {{color: '#fca5a5', width: 1.8, dash: 'dot'}}}};

    var layoutMom = {{
      height: 360,
      margin: {{l: 40, r: 85, t: 30, b: 40}},
      legend: {{orientation: 'h', y: -0.22}},
      paper_bgcolor: '#ffffff',
      plot_bgcolor: '#ffffff',
      font: {{family: '-apple-system, BlinkMacSystemFont, Segoe UI, Roboto, sans-serif', size: 11, color: '#12151a'}},
      yaxis: {{title: 'Compounded Rate (%)', gridcolor: 'rgba(0,0,0,0.06)', zeroline: true, zerolinecolor: '#333'}},
      annotations: [
        {{
          x: lDate, y: lH3, xref: 'x', yref: 'y',
          text: 'Head 3M: ' + (lH3 > 0 ? '+' : '') + lH3.toFixed(1) + '%',
          showarrow: true, arrowhead: 2, arrowsize: 1, arrowwidth: 1.5, arrowcolor: '#2563eb',
          ax: 35, ay: -15, bgcolor: '#2563eb',
          font: {{color: '#ffffff', size: 10, family: 'monospace', weight: 'bold'}}, borderpad: 3
        }},
        {{
          x: lDate, y: lC3, xref: 'x', yref: 'y',
          text: 'Core 3M: ' + (lC3 > 0 ? '+' : '') + lC3.toFixed(1) + '%',
          showarrow: true, arrowhead: 2, arrowsize: 1, arrowwidth: 1.5, arrowcolor: '#dc2626',
          ax: 35, ay: 15, bgcolor: '#dc2626',
          font: {{color: '#ffffff', size: 10, family: 'monospace', weight: 'bold'}}, borderpad: 3
        }}
      ]
    }};
    Plotly.newPlot(momDiv, [trH3, trHY, trC3, trCY], layoutMom, {{responsive: true}});
  }}

  // 3. Margin Scissors Chart
  var sciDiv = document.getElementById("deepdive-chart-cn-scissors");
  if (sciDiv) {{
    var sDates = {json.dumps(ts_dates)};
    var sSpread = {json.dumps(ts_scissors)};
    var sPpi = {json.dumps(ts_ppi)};
    var sCpi = {json.dumps(ts_cpi)};

    var lSDate = sDates.length ? sDates[sDates.length - 1] : '';
    var lP = sPpi.length ? sPpi[sPpi.length - 1] : 0;
    var lC = sCpi.length ? sCpi[sCpi.length - 1] : 0;
    var lSpr = sSpread.length ? sSpread[sSpread.length - 1] : 0;

    var trPpi = {{x: sDates, y: sPpi, name: 'PPI YoY (%)', type: 'scatter', mode: 'lines+markers', line: {{color: '#6366f1', width: 2.2}}, marker: {{size: 4}}}};
    var trCpi = {{x: sDates, y: sCpi, name: 'CPI YoY (%)', type: 'scatter', mode: 'lines', line: {{color: '#b91c1c', width: 2.2}}}};
    var trSpread = {{
      x: sDates, y: sSpread, name: 'Scissors Spread (PPI - CPI pp)',
      type: 'bar',
      marker: {{color: sSpread.map(function(v) {{ return v > 0 ? '#10b981' : '#ef4444'; }})}}
    }};

    var layoutSci = {{
      height: 380,
      margin: {{l: 40, r: 85, t: 30, b: 40}},
      legend: {{orientation: 'h', y: -0.22}},
      paper_bgcolor: '#ffffff',
      plot_bgcolor: '#ffffff',
      font: {{family: '-apple-system, BlinkMacSystemFont, Segoe UI, Roboto, sans-serif', size: 11, color: '#12151a'}},
      yaxis: {{title: 'Rate & Spread (pp)', gridcolor: 'rgba(0,0,0,0.06)', zeroline: true, zerolinecolor: '#333'}},
      annotations: [
        {{
          x: lSDate, y: lP, xref: 'x', yref: 'y',
          text: 'PPI: ' + (lP > 0 ? '+' : '') + lP.toFixed(1) + '%',
          showarrow: true, arrowhead: 2, arrowsize: 1, arrowwidth: 1.5, arrowcolor: '#6366f1',
          ax: 40, ay: -15, bgcolor: '#6366f1',
          font: {{color: '#ffffff', size: 10, family: 'monospace', weight: 'bold'}}, borderpad: 3
        }},
        {{
          x: lSDate, y: lSpr, xref: 'x', yref: 'y',
          text: 'Spread: ' + (lSpr > 0 ? '+' : '') + lSpr.toFixed(1) + 'pp',
          showarrow: true, arrowhead: 2, arrowsize: 1, arrowwidth: 1.5, arrowcolor: '#ef4444',
          ax: 40, ay: 20, bgcolor: '#ef4444',
          font: {{color: '#ffffff', size: 10, family: 'monospace', weight: 'bold'}}, borderpad: 3
        }}
      ]
    }};
    Plotly.newPlot(sciDiv, [trPpi, trCpi, trSpread], layoutSci, {{responsive: true}});
  }}

  // 4. Pork Cycle & Veg Basket Chart
  var hogDiv = document.getElementById("deepdive-chart-cn-hog-cycle");
  if (hogDiv) {{
    var hDates = {json.dumps(hog_dates)};
    var hSpots = {json.dumps(hog_spots)};
    var hIndices = {json.dumps(hog_indices)};
    var hMa12 = {json.dumps(hog_ma12)};

    var lHDate = hDates.length ? hDates[hDates.length - 1] : '';
    var lSpot = hSpots.length ? hSpots[hSpots.length - 1] : 0;
    var lIdx = hIndices.length ? hIndices[hIndices.length - 1] : 0;

    var trSpot = {{
      x: hDates, y: hSpots, name: 'Hog Cash Spot Price (元/公斤)',
      type: 'scatter', mode: 'lines+markers',
      line: {{color: '#d97706', width: 2.5}}, marker: {{size: 4}},
      yaxis: 'y'
    }};
    var trIdx = {{
      x: hDates, y: hIndices, name: 'National Hog Price Index',
      type: 'scatter', mode: 'lines',
      line: {{color: '#2563eb', width: 2.0}},
      yaxis: 'y2'
    }};
    var trMa12 = {{
      x: hDates, y: hMa12, name: '12M Moving Average Index',
      type: 'scatter', mode: 'lines',
      line: {{color: '#94a3b8', width: 1.5, dash: 'dot'}},
      yaxis: 'y2'
    }};

    var layoutHog = {{
      height: 380,
      margin: {{l: 45, r: 60, t: 30, b: 40}},
      legend: {{orientation: 'h', y: -0.22}},
      paper_bgcolor: '#ffffff',
      plot_bgcolor: '#ffffff',
      font: {{family: '-apple-system, BlinkMacSystemFont, Segoe UI, Roboto, sans-serif', size: 11, color: '#12151a'}},
      yaxis: {{title: 'Cash Price (CNY/kg)', gridcolor: 'rgba(0,0,0,0.06)'}},
      yaxis2: {{title: 'Hog Index', overlaying: 'y', side: 'right', gridcolor: 'rgba(0,0,0,0.02)'}},
      annotations: [
        {{
          x: lHDate, y: lSpot, xref: 'x', yref: 'y',
          text: 'Spot: ' + lSpot.toFixed(1) + ' CNY/kg',
          showarrow: true, arrowhead: 2, arrowsize: 1, arrowwidth: 1.5, arrowcolor: '#d97706',
          ax: -45, ay: -20, bgcolor: '#d97706',
          font: {{color: '#ffffff', size: 10, family: 'monospace', weight: 'bold'}}, borderpad: 3
        }}
      ]
    }};
    Plotly.newPlot(hogDiv, [trSpot, trIdx, trMa12], layoutHog, {{responsive: true}});
  }}
}});
</script>
"""
    return html


if __name__ == "__main__":
    out_html = render_china_deepdive_panel()
    print(f"Rendered China deepdive panel length: {len(out_html)} chars")
