"""Modular Institutional Renderer for Labour Market & Wage-Price Spiral Deepdive.

Renders 5-tab institutional deepdive panels for all 18 economies:
- Tab 1: Labour Market Tightness & Beveridge Curve Matrix
- Tab 2: Nominal vs Real Wage Trackers & Sectoral Breakdown
- Tab 3: Unit Labour Costs (ULC) & Productivity Identity
- Tab 4: Wage-Price Spiral Risk Gauge & Pass-Through
- Tab 5: Demographics & Structural Labour Supply

Supports bilingual EN/ZH labels and responsive FT / Claude UI styling.
"""

from __future__ import annotations

import json
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUTPUT = ROOT / "output"

GEO_NAME_MAP = {
    "US": "us",
    "UK": "uk",
    "EA": "euro_area",
    "PL": "poland",
    "HU": "hungary",
    "CZ": "czechia",
    "RO": "romania",
    "CN": "china",
    "JP": "japan",
    "KZ": "kazakhstan",
    "UZ": "uzbekistan",
    "TR": "turkey",
    "ZA": "south_africa",
    "KR": "south_korea",
    "TW": "taiwan",
    "HK": "hong_kong",
    "EG": "egypt",
    "NG": "nigeria",
}

LABOUR_CSS = """
<style>
.labour-panel {
  background: var(--surface, #ffffff);
  border: 1px solid var(--border, #e2e8f0);
  border-radius: 6px;
  padding: 20px;
  margin-bottom: 24px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.03);
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
  color: var(--text-primary, #0f172a);
}
.labour-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  border-bottom: 1px solid var(--border, #e2e8f0);
  padding-bottom: 14px;
  margin-bottom: 16px;
  flex-wrap: wrap;
  gap: 12px;
}
.labour-badge {
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: #0284c7;
  background: rgba(2, 132, 199, 0.08);
  padding: 3px 8px;
  border-radius: 3px;
  display: inline-block;
  margin-bottom: 4px;
}
.labour-title {
  font-size: 17px;
  font-weight: 700;
  color: var(--text-primary, #0f172a);
  margin: 0 0 4px 0;
}
.labour-desc {
  font-size: 12px;
  color: var(--muted, #64748b);
  margin: 0;
  line-height: 1.4;
}
.labour-tabs {
  display: flex;
  gap: 4px;
  border-bottom: 1px solid var(--border, #e2e8f0);
  margin-bottom: 16px;
  overflow-x: auto;
  scrollbar-width: none;
}
.labour-tabs::-webkit-scrollbar {
  display: none;
}
.labour-tab-btn {
  background: transparent;
  border: none;
  border-bottom: 2px solid transparent;
  padding: 8px 12px;
  font-size: 12px;
  font-weight: 600;
  color: var(--muted, #64748b);
  cursor: pointer;
  white-space: nowrap;
  transition: all 0.15s ease;
}
.labour-tab-btn:hover {
  color: var(--text-primary, #0f172a);
}
.labour-tab-btn.active {
  color: #0284c7;
  border-bottom-color: #0284c7;
}
.labour-tab-content {
  display: none;
}
.labour-tab-content.active {
  display: block;
}

/* KPI Ribbon */
.labour-kpi-ribbon {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
  gap: 12px;
  margin-bottom: 16px;
}
.labour-kpi-card {
  background: var(--surface-secondary, #f8fafc);
  border: 1px solid var(--border, #e2e8f0);
  border-radius: 6px;
  padding: 10px 12px;
}
.labour-kpi-title {
  font-size: 11px;
  font-weight: 600;
  color: var(--muted, #64748b);
  margin-bottom: 4px;
}
.labour-kpi-val {
  font-size: 18px;
  font-weight: 700;
  color: var(--text-primary, #0f172a);
  line-height: 1.2;
}
.labour-kpi-sub {
  font-size: 10px;
  color: var(--muted, #94a3b8);
  margin-top: 3px;
}

/* Risk Pill */
.risk-pill {
  display: inline-block;
  font-size: 10px;
  font-weight: 700;
  padding: 2px 6px;
  border-radius: 3px;
  text-transform: uppercase;
}
.risk-low {
  background: rgba(16, 185, 129, 0.12);
  color: #059669;
}
.risk-moderate {
  background: rgba(245, 158, 11, 0.12);
  color: #d97706;
}
.risk-elevated {
  background: rgba(239, 68, 68, 0.12);
  color: #dc2626;
}

/* Tables */
.labour-table-wrap {
  overflow-x: auto;
  border: 1px solid var(--border, #e2e8f0);
  border-radius: 6px;
  margin-bottom: 14px;
}
.labour-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 12px;
}
.labour-table th {
  background: var(--surface-secondary, #f8fafc);
  padding: 8px 12px;
  text-align: left;
  font-weight: 600;
  color: var(--muted, #475569);
  border-bottom: 1px solid var(--border, #e2e8f0);
}
.labour-table th.col-num, .labour-table td.col-num {
  text-align: right;
  font-variant-numeric: tabular-nums;
}
.labour-table td {
  padding: 8px 12px;
  border-bottom: 1px solid var(--border, #f1f5f9);
  color: var(--text-primary, #1e293b);
}
.labour-table tr:last-child td {
  border-bottom: none;
}

/* Institutional Note Block */
.labour-note-box {
  background: var(--surface-secondary, #f8fafc);
  border-left: 3px solid #0284c7;
  padding: 10px 14px;
  border-radius: 0 4px 4px 0;
  font-size: 12px;
  color: var(--text-primary, #334155);
  line-height: 1.5;
  margin-top: 12px;
}
.labour-note-box strong {
  color: #0284c7;
}

/* SVG Beveridge Plot */
.beveridge-container {
  display: flex;
  gap: 16px;
  align-items: center;
  flex-wrap: wrap;
  margin-bottom: 12px;
}
.beveridge-svg-wrap {
  flex: 1 1 360px;
  background: #ffffff;
  border: 1px solid var(--border, #e2e8f0);
  border-radius: 6px;
  padding: 10px;
}
.beveridge-legend-wrap {
  flex: 1 1 240px;
  font-size: 12px;
}
.beveridge-legend-item {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 6px;
  color: var(--muted, #475569);
}
.beveridge-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  display: inline-block;
}

/* Progress bar for Inactivity */
.inactivity-row {
  margin-bottom: 10px;
}
.inactivity-label-row {
  display: flex;
  justify-content: space-between;
  font-size: 11px;
  font-weight: 600;
  color: var(--text-primary, #334155);
  margin-bottom: 4px;
}
.inactivity-bar-bg {
  background: var(--border, #e2e8f0);
  height: 6px;
  border-radius: 3px;
  overflow: hidden;
}
.inactivity-bar-fill {
  background: #0284c7;
  height: 100%;
  border-radius: 3px;
}
</style>
"""


def render_beveridge_svg(points: list[dict[str, Any]]) -> str:
    if not points:
        return ""
    # Find min and max for scaling
    u_vals = [p["u"] for p in points]
    v_vals = [p["v"] for p in points]
    u_min, u_max = min(u_vals), max(u_vals)
    v_min, v_max = min(v_vals), max(v_vals)
    u_span = max(u_max - u_min, 1.0)
    v_span = max(v_max - v_min, 0.8)

    width = 380
    height = 200
    pad_l, pad_r, pad_t, pad_b = 40, 30, 20, 30
    plot_w = width - pad_l - pad_r
    plot_h = height - pad_t - pad_b

    def get_x(u):
        return pad_l + ((u - u_min) / u_span) * plot_w

    def get_y(v):
        return height - pad_b - ((v - v_min) / v_span) * plot_h

    # Build polyline path
    path_d = []
    circles = []
    labels = []
    for i, pt in enumerate(points):
        x = get_x(pt["u"])
        y = get_y(pt["v"])
        if i == 0:
            path_d.append(f"M {x:.1f} {y:.1f}")
        else:
            path_d.append(f"L {x:.1f} {y:.1f}")

        # Current vs historical color
        is_curr = i == len(points) - 1
        fill_color = "#0284c7" if is_curr else "#94a3b8"
        r = 5 if is_curr else 3.5
        circles.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r}" fill="{fill_color}" stroke="#ffffff" stroke-width="1.5"/>')
        labels.append(f'<text x="{x + 6:.1f}" y="{y - 4:.1f}" font-size="9" fill="#475569" font-family="sans-serif">{pt["date"]}</text>')

    path_str = " ".join(path_d)

    svg = f"""<svg width="100%" height="200" viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg">
  <!-- Grid Lines -->
  <line x1="{pad_l}" y1="{height - pad_b}" x2="{width - pad_r}" y2="{height - pad_b}" stroke="#cbd5e1" stroke-width="1"/>
  <line x1="{pad_l}" y1="{pad_t}" x2="{pad_l}" y2="{height - pad_b}" stroke="#cbd5e1" stroke-width="1"/>
  <text x="{width - pad_r}" y="{height - pad_b + 20}" font-size="9" fill="#64748b" text-anchor="end">Unemployment Rate (U) % →</text>
  <text x="{pad_l}" y="{pad_t - 6}" font-size="9" fill="#64748b">↑ Vacancy (V)</text>
  <!-- Beveridge Trajectory Path -->
  <path d="{path_str}" fill="none" stroke="#38bdf8" stroke-width="2" stroke-dasharray="3,3"/>
  {''.join(circles)}
  {''.join(labels)}
</svg>"""
    return svg


def render_labour_deepdive_panel(geo_code: str) -> str:
    geo = geo_code.upper()
    name = GEO_NAME_MAP.get(geo, geo.lower())
    data_file = OUTPUT / f"{name}_labour_deepdive.json"

    if not data_file.exists():
        return ""

    try:
        data = json.loads(data_file.read_text(encoding="utf-8"))
    except Exception:
        return ""

    t1 = data.get("tab1_tightness", {})
    t1_kpi = t1.get("kpi", {})
    t2 = data.get("tab2_wages", {})
    t3 = data.get("tab3_ulc", {})
    t3_kpi = t3.get("kpi", {})
    t4 = data.get("tab4_spiral", {})
    t4_kpi = t4.get("kpi", {})
    t5 = data.get("tab5_supply", {})
    t5_kpi = t5.get("kpi", {})

    # Beveridge SVG
    bev_svg = render_beveridge_svg(t1.get("beveridge_points", []))

    # Risk class
    risk_level = t4_kpi.get("spiral_risk_level", "LOW")
    risk_cls = "risk-low" if risk_level == "LOW" else ("risk-moderate" if risk_level == "MODERATE" else "risk-elevated")

    html = f"""
{LABOUR_CSS}
<div class="labour-panel" id="deepdive-labour-{geo}">
  <div class="labour-header">
    <div class="labour-title-wrap">
      <span class="labour-badge"><span data-lang="en">Labour & Wages Deepdive</span><span data-lang="zh">劳动力与薪资深度透视</span></span>
      <h3 class="labour-title">
        <span data-lang="en">Labour Market Tightness & Wage-Price Spiral Analysis</span>
        <span data-lang="zh">劳动力市场紧度与薪资-物价二次传导透视</span>
      </h3>
      <p class="labour-desc">
        <span data-lang="en">Institutional analysis of Beveridge curve tightness, nominal vs real wage trackers, Unit Labour Costs (ULC), and pass-through to core services inflation.</span>
        <span data-lang="zh">贝弗里奇供求匹配曲线、实际薪资回补缺口、单位用工成本(ULC)生产率分解及对核心服务通胀传导的机构级分析。</span>
      </p>
    </div>
    <div style="text-align: right; font-size: 11px; color: var(--muted, #64748b);">
      <div><strong>{escape(data.get('agency', 'Official Statistics'))}</strong></div>
      <div><span data-lang="en">Updated:</span><span data-lang="zh">更新报告期:</span> {escape(data.get('last_updated', '2026-11'))}</div>
    </div>
  </div>

  <div class="labour-tabs">
    <button class="labour-tab-btn active" onclick="switchLabourTab('{geo}', 'tightness', this)">
      <span data-lang="en">1. Slack & Beveridge</span><span data-lang="zh">1. 市场紧度与贝弗里奇</span>
    </button>
    <button class="labour-tab-btn" onclick="switchLabourTab('{geo}', 'wages', this)">
      <span data-lang="en">2. Wage Trackers</span><span data-lang="zh">2. 名义与实际薪资</span>
    </button>
    <button class="labour-tab-btn" onclick="switchLabourTab('{geo}', 'ulc', this)">
      <span data-lang="en">3. ULC & Productivity</span><span data-lang="zh">3. 单位用工成本与生产率</span>
    </button>
    <button class="labour-tab-btn" onclick="switchLabourTab('{geo}', 'spiral', this)">
      <span data-lang="en">4. Wage-Price Spiral</span><span data-lang="zh">4. 薪资-物价二次螺旋</span>
    </button>
    <button class="labour-tab-btn" onclick="switchLabourTab('{geo}', 'supply', this)">
      <span data-lang="en">5. Structural Supply</span><span data-lang="zh">5. 结构供给与人口</span>
    </button>
  </div>

  <!-- TAB 1: TIGHTNESS & BEVERIDGE -->
  <div class="labour-tab-content active" id="tab-labour-tightness-{geo}">
    <div class="labour-kpi-ribbon">
      <div class="labour-kpi-card">
        <div class="labour-kpi-title"><span data-lang="en">Unemployment Rate (U)</span><span data-lang="zh">失业率 (U)</span></div>
        <div class="labour-kpi-val">{t1_kpi.get('unemployment_rate', {}).get('val', 0.0)}%</div>
        <div class="labour-kpi-sub">{t1_kpi.get('unemployment_rate', {}).get('status', 'Observed')}</div>
      </div>
      <div class="labour-kpi-card">
        <div class="labour-kpi-title"><span data-lang="en">Vacancy Indicator (V)</span><span data-lang="zh">职位空缺指标 (V)</span></div>
        <div class="labour-kpi-val">{t1_kpi.get('vacancy_indicator', {}).get('val', 0.0)}{t1_kpi.get('vacancy_indicator', {}).get('unit', '%')}</div>
        <div class="labour-kpi-sub">{t1_kpi.get('vacancy_indicator', {}).get('date', '')}</div>
      </div>
      <div class="labour-kpi-card">
        <div class="labour-kpi-title"><span data-lang="en">V / U Tightness Ratio</span><span data-lang="zh">V / U 紧度比值</span></div>
        <div class="labour-kpi-val" style="color: #0284c7;">{t1_kpi.get('tightness_vu', {}).get('val', 1.0)}</div>
        <div class="labour-kpi-sub"><span data-lang="en">Bench:</span><span data-lang="zh">中枢:</span> {t1_kpi.get('tightness_vu', {}).get('benchmark', 1.0)}</div>
      </div>
      <div class="labour-kpi-card">
        <div class="labour-kpi-title"><span data-lang="en">Sahm Rule Indicator</span><span data-lang="zh">萨姆衰退指标</span></div>
        <div class="labour-kpi-val">{t1_kpi.get('sahm_rule', {}).get('val', 0.0)} pp</div>
        <div class="labour-kpi-sub"><span class="risk-pill { 'risk-low' if t1_kpi.get('sahm_rule', {}).get('status') == 'SAFE' else 'risk-elevated' }">{t1_kpi.get('sahm_rule', {}).get('status', 'SAFE')}</span></div>
      </div>
      <div class="labour-kpi-card">
        <div class="labour-kpi-title"><span data-lang="en">Broad Labour Slack</span><span data-lang="zh">广义劳动力松弛度</span></div>
        <div class="labour-kpi-val">{t1_kpi.get('broad_slack_val', 0.0)}%</div>
        <div class="labour-kpi-sub"><span data-lang="en">Underemployed</span><span data-lang="zh">含边缘未充分就业</span></div>
      </div>
    </div>

    <div class="beveridge-container">
      <div class="beveridge-svg-wrap">
        <div style="font-size: 11px; font-weight: 700; color: var(--muted, #64748b); margin-bottom: 6px;">
          <span data-lang="en">Beveridge Curve Trajectory (U vs V)</span>
          <span data-lang="zh">贝弗里奇供求匹配曲线动线轨迹 (U vs V)</span>
        </div>
        {bev_svg}
      </div>
      <div class="beveridge-legend-wrap">
        <div style="font-size: 12px; font-weight: 700; color: var(--text-primary, #0f172a); margin-bottom: 8px;">
          <span data-lang="en">Historical Regime Shifting</span>
          <span data-lang="zh">经济周期与制度性匹配轨迹</span>
        </div>
        <div class="beveridge-legend-item">
          <span class="beveridge-dot" style="background: #38bdf8;"></span>
          <span><span data-lang="en">2021-2022: Post-pandemic outward shift & extreme tightening</span><span data-lang="zh">2021-2022: 疫情后外生冲击与空缺率峰值过热</span></span>
        </div>
        <div class="beveridge-legend-item">
          <span class="beveridge-dot" style="background: #0284c7;"></span>
          <span><span data-lang="en">2023-2026: Inward trajectory towards pre-shock equilibrium</span><span data-lang="zh">2023-2026: 曲线内生性回归至均衡常态化通道</span></span>
        </div>
        <div class="labour-note-box" style="margin-top: 10px;">
          <strong><span data-lang="en">Assessment:</span><span data-lang="zh">机构研判：</span></strong>
          <span data-lang="en">{escape(t1.get('eval_en', ''))}</span>
          <span data-lang="zh">{escape(t1.get('eval_zh', ''))}</span>
        </div>
      </div>
    </div>
  </div>

  <!-- TAB 2: WAGE TRACKERS -->
  <div class="labour-tab-content" id="tab-labour-wages-{geo}">
    <div class="labour-table-wrap">
      <table class="labour-table">
        <thead>
          <tr>
            <th><span data-lang="en">Wage & Compensation Component</span><span data-lang="zh">薪酬与工资指标分类</span></th>
            <th class="col-num"><span data-lang="en">Latest</span><span data-lang="zh">最新读数</span></th>
            <th class="col-num"><span data-lang="en">Previous</span><span data-lang="zh">上期值</span></th>
            <th class="col-num"><span data-lang="en">1Y Ago</span><span data-lang="zh">上年同期</span></th>
            <th class="col-num"><span data-lang="en">3M Momentum (saar)</span><span data-lang="zh">3M年化季调动量</span></th>
            <th><span data-lang="en">Unit</span><span data-lang="zh">单位</span></th>
          </tr>
        </thead>
        <tbody>
"""
    for r in t2.get("table_rows", []):
        html += f"""
          <tr>
            <td><strong><span data-lang="en">{escape(r['label_en'])}</span><span data-lang="zh">{escape(r['label_zh'])}</span></strong></td>
            <td class="col-num" style="font-weight: 700; color: #0284c7;">{r['latest']}</td>
            <td class="col-num" style="color: var(--muted, #64748b);">{r['prev']}</td>
            <td class="col-num" style="color: var(--muted, #64748b);">{r['ago_1y']}</td>
            <td class="col-num">{r['momentum_3m']}</td>
            <td style="color: var(--muted, #64748b); font-size: 11px;">{escape(r['unit'])}</td>
          </tr>
"""

    html += f"""
        </tbody>
      </table>
    </div>

    <div class="labour-note-box">
      <strong><span data-lang="en">Wage Dynamic Assessment:</span><span data-lang="zh">薪资动态研判：</span></strong>
      <span data-lang="en">{escape(t2.get('eval_en', ''))}</span>
      <span data-lang="zh">{escape(t2.get('eval_zh', ''))}</span>
    </div>
  </div>

  <!-- TAB 3: ULC & PRODUCTIVITY -->
  <div class="labour-tab-content" id="tab-labour-ulc-{geo}">
    <div class="labour-kpi-ribbon">
      <div class="labour-kpi-card">
        <div class="labour-kpi-title"><span data-lang="en">Unit Labour Cost (ULC)</span><span data-lang="zh">单位劳动力成本 (ULC)</span></div>
        <div class="labour-kpi-val" style="color: #0284c7;">{t3_kpi.get('ulc_growth', {}).get('val', 0.0)}%</div>
        <div class="labour-kpi-sub">YoY Growth</div>
      </div>
      <div class="labour-kpi-card">
        <div class="labour-kpi-title"><span data-lang="en">Labour Productivity</span><span data-lang="zh">劳动生产率增速</span></div>
        <div class="labour-kpi-val">{t3_kpi.get('productivity_growth', {}).get('val', 0.0)}%</div>
        <div class="labour-kpi-sub">Output per Hour/Worker</div>
      </div>
      <div class="labour-kpi-card">
        <div class="labour-kpi-title"><span data-lang="en">Nominal Compensation</span><span data-lang="zh">名义报酬增速</span></div>
        <div class="labour-kpi-val">{t3_kpi.get('nominal_compensation', {}).get('val', 0.0)}%</div>
        <div class="labour-kpi-sub">Hourly / Per Employee</div>
      </div>
      <div class="labour-kpi-card">
        <div class="labour-kpi-title"><span data-lang="en">Target Hurdle Line</span><span data-lang="zh">通胀相容基准线</span></div>
        <div class="labour-kpi-val">{t3_kpi.get('inflation_target_hurdle', {}).get('val', 0.0)}%</div>
        <div class="labour-kpi-sub">{escape(t3_kpi.get('inflation_target_hurdle', {}).get('desc', ''))}</div>
      </div>
      <div class="labour-kpi-card">
        <div class="labour-kpi-title"><span data-lang="en">Excess Labour Pressure</span><span data-lang="zh">超额用工成本压力</span></div>
        <div class="labour-kpi-val">{t3_kpi.get('excess_labor_cost_pressure', {}).get('val', 0.0):+} pp</div>
        <div class="labour-kpi-sub"><span class="risk-pill { 'risk-low' if t3_kpi.get('excess_labor_cost_pressure', {}).get('status') == 'CONTAINED' else 'risk-moderate' }">{t3_kpi.get('excess_labor_cost_pressure', {}).get('status', 'CONTAINED')}</span></div>
      </div>
    </div>

    <div class="labour-note-box">
      <strong><span data-lang="en">Productivity Identity:</span><span data-lang="zh">生产率恒等式：</span></strong>
      <span>Δln(ULC) = Δln(Compensation) - Δln(Productivity). </span>
      <span data-lang="en">{escape(t3.get('eval_en', ''))}</span>
      <span data-lang="zh">{escape(t3.get('eval_zh', ''))}</span>
    </div>
  </div>

  <!-- TAB 4: WAGE-PRICE SPIRAL -->
  <div class="labour-tab-content" id="tab-labour-spiral-{geo}">
    <div class="labour-kpi-ribbon">
      <div class="labour-kpi-card">
        <div class="labour-kpi-title"><span data-lang="en">Catch-Up Gap</span><span data-lang="zh">实际工资回补缺口</span></div>
        <div class="labour-kpi-val" style="color: #0284c7;">{t4_kpi.get('catch_up_gap', {}).get('val', '0.0%')}</div>
        <div class="labour-kpi-sub"><span data-lang="en">Post-2021 Cumulative</span><span data-lang="zh">2021后累积回补</span></div>
      </div>
      <div class="labour-kpi-card">
        <div class="labour-kpi-title"><span data-lang="en">Headline CPI Inflation</span><span data-lang="zh">消费物价通胀 (CPI)</span></div>
        <div class="labour-kpi-val">{t4_kpi.get('cpi_yoy', {}).get('val', 0.0)}%</div>
        <div class="labour-kpi-sub">YoY Benchmark</div>
      </div>
      <div class="labour-kpi-card">
        <div class="labour-kpi-title"><span data-lang="en">Wage - CPI Wedge</span><span data-lang="zh">薪资-物价剪刀差</span></div>
        <div class="labour-kpi-val">{t4_kpi.get('wage_services_gap', {}).get('val', 0.0):+} pp</div>
        <div class="labour-kpi-sub"><span data-lang="en">Real Purchasing Spread</span><span data-lang="zh">购买力净利差</span></div>
      </div>
      <div class="labour-kpi-card">
        <div class="labour-kpi-title"><span data-lang="en">Spiral Risk Level</span><span data-lang="zh">二次螺旋风险等级</span></div>
        <div class="labour-kpi-val"><span class="risk-pill {risk_cls}">{risk_level}</span></div>
        <div class="labour-kpi-sub"><span data-lang="en">Institutional Gauge</span><span data-lang="zh">机构风险预警仪</span></div>
      </div>
      <div class="labour-kpi-card">
        <div class="labour-kpi-title"><span data-lang="en">Profit Margin Buffer</span><span data-lang="zh">企业利润率缓冲垫</span></div>
        <div class="labour-kpi-val" style="color: #059669;">{t4_kpi.get('profit_margin_buffer', {}).get('level', 'STRONG')}</div>
        <div class="labour-kpi-sub"><span data-lang="en">Absorption Capacity</span><span data-lang="zh">成本吸收缓冲</span></div>
      </div>
    </div>

    <div class="labour-note-box">
      <strong><span data-lang="en">Services Pass-Through & Spiral Assessment:</span><span data-lang="zh">服务业传导与螺旋研判：</span></strong>
      <span data-lang="en">{escape(t4.get('lead_lag_note_en', ''))} {escape(t4.get('eval_en', ''))}</span>
      <span data-lang="zh">{escape(t4.get('lead_lag_note_zh', ''))} {escape(t4.get('eval_zh', ''))}</span>
    </div>
  </div>

  <!-- TAB 5: DEMOGRAPHICS & SUPPLY -->
  <div class="labour-tab-content" id="tab-labour-supply-{geo}">
    <div class="labour-kpi-ribbon">
      <div class="labour-kpi-card">
        <div class="labour-kpi-title"><span data-lang="en">Total LFPR</span><span data-lang="zh">总劳动参与率</span></div>
        <div class="labour-kpi-val">{t5_kpi.get('lfpr_total', {}).get('val', 0.0)}%</div>
        <div class="labour-kpi-sub">Age 15+ / 16+</div>
      </div>
      <div class="labour-kpi-card">
        <div class="labour-kpi-title"><span data-lang="en">Prime-Age LFPR (25-54)</span><span data-lang="zh">黄金年龄参与率 (25-54)</span></div>
        <div class="labour-kpi-val" style="color: #0284c7;">{t5_kpi.get('prime_age_lfpr', {}).get('val', 0.0)}%</div>
        <div class="labour-kpi-sub">Core Capacity</div>
      </div>
      <div class="labour-kpi-card">
        <div class="labour-kpi-title"><span data-lang="en">Economic Inactivity</span><span data-lang="zh">经济不活跃率</span></div>
        <div class="labour-kpi-val">{t5_kpi.get('inactivity_rate', {}).get('val', 0.0)}%</div>
        <div class="labour-kpi-sub">Non-Participating</div>
      </div>
      <div class="labour-kpi-card">
        <div class="labour-kpi-title"><span data-lang="en">Youth Unemployment</span><span data-lang="zh">青年失业率</span></div>
        <div class="labour-kpi-val">{t5_kpi.get('youth_unemployment', {}).get('val', 0.0)}%</div>
        <div class="labour-kpi-sub">Under 25 Cohort</div>
      </div>
      <div class="labour-kpi-card">
        <div class="labour-kpi-title"><span data-lang="en">Old-Age Dependency</span><span data-lang="zh">老年抚养比</span></div>
        <div class="labour-kpi-val">{t5_kpi.get('old_age_dependency', {}).get('val', 0.0)}%</div>
        <div class="labour-kpi-sub">65+ / (15-64)</div>
      </div>
    </div>

    <div style="background: var(--surface-secondary, #f8fafc); border: 1px solid var(--border, #e2e8f0); border-radius: 6px; padding: 14px; margin-bottom: 12px;">
      <div style="font-size: 12px; font-weight: 700; color: var(--text-primary, #0f172a); margin-bottom: 10px;">
        <span data-lang="en">Working-Age Economic Inactivity by Cause</span>
        <span data-lang="zh">适龄劳动力未参与就业主要原因结构拆解</span>
      </div>
"""
    for c in t5.get("inactivity_breakdown", []):
        html += f"""
      <div class="inactivity-row">
        <div class="inactivity-label-row">
          <span><span data-lang="en">{escape(c['cause_en'])}</span><span data-lang="zh">{escape(c['cause_zh'])}</span></span>
          <span>{c['share']}%</span>
        </div>
        <div class="inactivity-bar-bg">
          <div class="inactivity-bar-fill" style="width: {c['share']}%;"></div>
        </div>
      </div>
"""
    html += f"""
    </div>

    <div class="labour-note-box">
      <strong><span data-lang="en">Structural Supply Assessment:</span><span data-lang="zh">供给结构研判：</span></strong>
      <span data-lang="en">{escape(t5.get('eval_en', ''))}</span>
      <span data-lang="zh">{escape(t5.get('eval_zh', ''))}</span>
    </div>
  </div>
</div>

<script>
window.switchLabourTab = function(geo, tabName, btn) {{
  var parent = document.getElementById('deepdive-labour-' + geo);
  if (!parent) return;
  var btns = parent.querySelectorAll('.labour-tab-btn');
  btns.forEach(function(b) {{ b.classList.remove('active'); }});
  if (btn) btn.classList.add('active');

  var contents = parent.querySelectorAll('.labour-tab-content');
  contents.forEach(function(c) {{ c.classList.remove('active'); }});

  var target = document.getElementById('tab-labour-' + tabName + '-' + geo);
  if (target) {{
    target.classList.add('active');
  }}
}};
</script>
"""
    return html


if __name__ == "__main__":
    sample = render_labour_deepdive_panel("US")
    print(f"Rendered US Labour Deepdive ({len(sample)} chars)")
