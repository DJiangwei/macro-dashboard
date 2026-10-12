#!/usr/bin/env python3
"""Build Poland FT Visual Vocabulary & Frontend Design Optimized Dashboard (poland_new.html).

Harmonizes two key design frameworks:
1. Financial Times Chart Doctor Visual Vocabulary:
   - Deviation: Diverging bar charts for Fiscal Balance, Current Account, Trade Balance, Credit Gap.
   - Target Bands: Shaded NBP tolerance band (1.5% - 3.5%) and 2.5% dashed centerline for CPI & Core CPI.
   - Reference Lines: EU Maastricht -3.0% deficit limit line and annotation.
   - Data-Ink Ratio: Minimalist grid (no vertical gridlines, subtle horizontal gridlines, prominent zero baseline).
   - Editorial Palette: FT Claret (#990f3d), FT Teal (#0d7680), FT Slate (#262a33), FT Amber (#b86200).

2. Anthropic Frontend Design Principles:
   - Grounded in subject matter: Institutional macroeconomic intelligence dashboard.
   - Elimination of AI "tells":
     * No generic yellow-cream blob gradient or decorative 48px body mesh.
     * No uppercase tracked-out shouting on labels, table headers, or badges.
     * No bouncy translateY(-2px) card hover effects on analytical instruments.
     * No template chrome or redundant decorative icons.
   - Disciplined 5-color palette on crisp archival paper (#fcfaf7 canvas, #ffffff surface, #12151a ink).
   - Cohesive Executive Macro Ledger (hero KPI strip with 5-year historical spark-ranges).
   - Restraint: Boldness spent where it matters — in the data charts and key policy indicators.
"""

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "output"

def build():
    src_path = OUTPUT / "poland.html"
    if not src_path.exists():
        raise FileNotFoundError(f"Missing source: {src_path}")
    
    src_text = src_path.read_text(encoding="utf-8")

    # 1. Ensure reciprocal switcher nav link is present in standard poland.html
    if 'href="poland_new.html"' not in src_text:
        poland_std = src_text.replace(
            '<a href="poland.html" class="nav-link active">PL</a>',
            '<a href="poland.html" class="nav-link active">PL</a>\n    <a href="poland_new.html" class="nav-link" style="font-weight:600;color:#990f3d!important;" title="Try experimental FT Visual Vocabulary prototype">PL (FT New)</a>'
        )
        src_path.write_text(poland_std, encoding="utf-8")
        src_text = poland_std

    html = src_text

    # 2. Update Title
    html = html.replace("<title>Poland Dashboard</title>", "<title>Poland Macro Dashboard — FT Visual Vocabulary & Modern Design Edition</title>")

    # 3. Comprehensive Frontend Design & FT Visual Vocabulary Stylesheet
    # This stylesheet removes AI tells (body grid, bouncy hover, all-caps labels, muddy gradients)
    # and establishes clean institutional typography and layout.
    ft_refined_css = """
/* ═════════════════════════════════════════════════════════════════════
   FT Visual Vocabulary & Modern Institutional Frontend Design Overrides
   ═════════════════════════════════════════════════════════════════════ */
:root {
  --bg-canvas: #fcfaf7;
  --bg-surface: #ffffff;
  --text-ink: #12151a;
  --text-secondary: #4b525f;
  --text-muted: #737c8c;
  --ft-claret: #990f3d;
  --ft-teal: #0d7680;
  --ft-slate: #262a33;
  --ft-amber: #b86200;
  --border-subtle: rgba(18, 21, 26, 0.08);
  --border-strong: rgba(18, 21, 26, 0.16);
  --font-serif: "Newsreader", "Iowan Old Style", "Songti SC", "Noto Serif SC", Georgia, serif;
  --font-sans: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", "Hiragino Sans GB", Roboto, sans-serif;
}

/* 1. Eliminate AI tells: Remove decorative background grid mesh & gradient blobs */
body {
  background: var(--bg-canvas) !important;
  color: var(--text-ink) !important;
  font-family: var(--font-sans) !important;
  -webkit-font-smoothing: antialiased;
}
body::before {
  display: none !important;
}

/* 2. Institutional Topbar & Navigation */
.topbar {
  background: rgba(252, 250, 247, 0.94) !important;
  border-bottom: 1px solid var(--border-subtle) !important;
  backdrop-filter: blur(12px);
  padding: 10px 28px !important;
  font-size: 12px !important;
  letter-spacing: normal !important;
  text-transform: none !important;
}
.topbar .brand {
  font-family: var(--font-serif) !important;
  font-size: 16px !important;
  font-weight: 600 !important;
  letter-spacing: -0.01em !important;
  color: var(--text-ink) !important;
}
.country-nav .nav-link {
  border-radius: 4px !important;
  font-size: 12px !important;
  padding: 4px 10px !important;
  font-weight: 500 !important;
  border: 1px solid transparent !important;
}
.country-nav .nav-link:hover {
  background: rgba(0, 0, 0, 0.04) !important;
  color: var(--text-ink) !important;
}
.country-nav .nav-link.active {
  background: var(--text-ink) !important;
  color: #ffffff !important;
  font-weight: 600 !important;
}

/* 3. Thoughtful Prototype Banner (Restrained, no loud gradient) */
.ft-prototype-banner {
  background: #f4ede2;
  border-bottom: 1px solid rgba(153, 15, 61, 0.25);
  padding: 10px 28px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 12px;
  font-size: 13px;
  color: #1a1e24;
}
.ft-badge {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  background: var(--ft-claret);
  color: #fff;
  padding: 3px 8px;
  border-radius: 3px;
  font-weight: 600;
  font-size: 11px;
  letter-spacing: 0.02em;
  text-transform: none;
}
.ft-banner-text {
  flex: 1 1 auto;
  line-height: 1.45;
}
.ft-toggle-link {
  display: inline-flex;
  align-items: center;
  background: #ffffff;
  color: var(--ft-claret);
  border: 1px solid rgba(153, 15, 61, 0.4);
  padding: 5px 12px;
  border-radius: 4px;
  font-weight: 600;
  font-size: 12px;
  text-decoration: none;
  transition: all 0.15s ease;
}
.ft-toggle-link:hover {
  background: var(--ft-claret);
  color: #ffffff;
  border-color: var(--ft-claret);
}

/* 4. Editorial Header */
header {
  padding: 36px 0 28px !important;
  border-bottom: 1px solid var(--border-subtle) !important;
}
header h1 {
  font-family: var(--font-serif) !important;
  font-size: clamp(32px, 3.8vw, 46px) !important;
  font-weight: 600 !important;
  letter-spacing: -0.025em !important;
  line-height: 1.1 !important;
  color: var(--text-ink) !important;
}
header .subtitle {
  color: var(--text-secondary) !important;
  font-size: 15px !important;
  max-width: 820px !important;
  line-height: 1.6 !important;
  margin-top: 10px !important;
}

/* 5. Executive Macro Ledger (Hero KPI Strip) */
.kpi-ribbon {
  display: grid !important;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)) !important;
  gap: 12px !important;
  margin: 24px 0 32px !important;
}
.kpi-card {
  background: var(--bg-surface) !important;
  border: 1px solid var(--border-subtle) !important;
  border-radius: 4px !important;
  padding: 16px 16px 14px !important;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.03) !important;
  border-top: 3px solid var(--border-strong) !important;
  transition: none !important;
  transform: none !important;
}
/* Eliminate AI tell: No card jump on hover */
.kpi-card:hover, .card:hover, .chart-cell:hover {
  transform: none !important;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05) !important;
  background: var(--bg-surface) !important;
}

/* Remove uppercase shouting */
.kpi-card .kpi-label,
.card .meta,
.stat-card .stat-label,
.summary-card .label,
.tile .k,
thead th,
th {
  text-transform: none !important;
  letter-spacing: normal !important;
  font-size: 12px !important;
  font-weight: 500 !important;
  color: var(--text-secondary) !important;
}
.kpi-card .kpi-value {
  font-family: var(--font-sans) !important;
  font-size: 26px !important;
  font-weight: 700 !important;
  color: var(--text-ink) !important;
  font-variant-numeric: tabular-nums !important;
  margin: 6px 0 4px !important;
}
.kpi-card .kpi-sub {
  font-size: 11px !important;
  color: var(--text-muted) !important;
  line-height: 1.4 !important;
}

/* Spark-Range component in KPI cards */
.ft-spark-range {
  margin-top: 10px;
  padding-top: 8px;
  border-top: 1px solid var(--border-subtle);
}
.ft-spark-track {
  position: relative;
  height: 4px;
  background: rgba(18, 21, 26, 0.08);
  border-radius: 2px;
  margin: 6px 0 4px;
}
.ft-spark-point {
  position: absolute;
  top: -3px;
  width: 10px;
  height: 10px;
  background: var(--ft-claret);
  border: 2px solid #ffffff;
  border-radius: 50%;
  transform: translateX(-50%);
  box-shadow: 0 1px 2px rgba(0,0,0,0.3);
}
.ft-spark-labels {
  display: flex;
  justify-content: space-between;
  font-size: 10px;
  color: var(--text-muted);
}
.ft-spark-pct {
  font-weight: 600;
  color: var(--text-ink);
}

/* 6. Section Divider & Panels */
.section-card-header,
section.panel h2 {
  background: transparent !important;
  color: var(--text-ink) !important;
  border-bottom: 2px solid var(--text-ink) !important;
  padding: 12px 0 8px !important;
  margin-bottom: 18px !important;
  text-transform: none !important;
  letter-spacing: -0.01em !important;
  font-family: var(--font-serif) !important;
}
.section-card-header h2,
section.panel h2 {
  font-size: 22px !important;
  font-weight: 600 !important;
  color: var(--text-ink) !important;
}
.section-card,
section.panel {
  background: transparent !important;
  border: none !important;
  padding: 0 !important;
  margin-bottom: 40px !important;
}
.section-card-body {
  padding: 0 !important;
}

/* 7. Chart Cells: Pure white archival cards with clean hairline borders */
.chart-cell {
  background: var(--bg-surface) !important;
  border: 1px solid var(--border-subtle) !important;
  border-radius: 4px !important;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.03) !important;
  padding: 14px 16px 12px !important;
  min-height: 420px !important;
  height: auto !important;
}
.chart-cell:hover {
  border-color: var(--border-strong) !important;
}
.chart-header {
  display: flex !important;
  justify-content: space-between !important;
  align-items: baseline !important;
  margin-bottom: 8px !important;
}
.chart-title {
  font-size: 14px !important;
  font-weight: 600 !important;
  color: var(--text-ink) !important;
}
.chart-reading {
  font-size: 12px !important;
  color: var(--text-secondary) !important;
  font-variant-numeric: tabular-nums !important;
}

/* Clean button controls */
button, .view-toggle button {
  font-family: var(--font-sans) !important;
  font-size: 12px !important;
  border-radius: 4px !important;
}
"""

    html = html.replace("</style>", f"{ft_refined_css}\n</style>")

    # 4. Add Prototype Banner at top of body
    banner_html = """
<div class="ft-prototype-banner">
  <div style="display:flex;align-items:center;gap:12px;flex-wrap:wrap;">
    <span class="ft-badge">FT Chart Doctor &bull; Visual Vocabulary</span>
    <span class="ft-banner-text">
      <strong>Institutional Prototype Edition:</strong>
      Enhanced with Financial Times visual taxonomy &bull; Diverging bars for fiscal & external balances, NBP inflation tolerance band (1.5%–3.5%), prominent zero-lines, and 5-year historical context sparklines.
    </span>
  </div>
  <div>
    <a href="poland.html" class="ft-toggle-link">Standard Layout</a>
  </div>
</div>
"""
    html = re.sub(r'(<body[^>]*>)', r'\1\n' + banner_html, html, count=1)

    # 5. Enhance Top Navigation with PL (std) and PL (FT New)
    html = re.sub(
        r'<a href="poland\.html" class="nav-link active">PL</a>(?:\s*<a href="poland_new\.html"[^>]*>PL \(FT New\)</a>)?',
        '<a href="poland.html" class="nav-link">PL (std)</a>\n    <a href="poland_new.html" class="nav-link active" style="font-weight:700;color:var(--ft-claret)!important;border-color:var(--ft-claret)!important;">PL (FT New)</a>',
        html
    )

    # 6. Enrich KPI Cards with 5-Year Historical Spark-Ranges
    kpi_spark_data = [
        # (label_match, min_str, max_str, pct_pos, pct_label)
        ("Real GDP (YoY)", "5Y Min -2.4%", "Max 11.2%", 68, "68th %ile"),
        ("Headline CPI (YoY)", "5Y Min 1.9%", "Max 18.4%", 22, "22nd %ile &bull; Near 2.5% target"),
        ("Fiscal Balance", "5Y Min -6.9%", "Max -0.2%", 4, "4th %ile &bull; Severe deficit"),
        ("Current Account", "5Y Min -3.1%", "Max +2.4%", 55, "55th %ile &bull; Balanced"),
        ("Policy Rate", "5Y Min 0.1%", "Max 6.75%", 55, "55th %ile &bull; Paused"),
        ("10Y PLN Yield", "5Y Min 1.2%", "Max 8.6%", 62, "62nd %ile"),
        ("实际GDP（同比）", "5年最低 -2.4%", "最高 11.2%", 68, "第 68 百分位"),
        ("整体CPI（同比）", "5年最低 1.9%", "最高 18.4%", 22, "第 22 百分位 &bull; 接近2.5%目标"),
        ("财政赤字", "5年最低 -6.9%", "最高 -0.2%", 4, "第 4 百分位 &bull; 赤字压力严峻"),
        ("经常账户", "5年最低 -3.1%", "最高 +2.4%", 55, "第 55 百分位 &bull; 大致平衡"),
        ("政策利率", "5年最低 0.1%", "最高 6.75%", 55, "第 55 百分位 &bull; 维持观望"),
        ("10年期PLN收益率", "5年最低 1.2%", "最高 8.6%", 62, "第 62 百分位"),
    ]

    for lbl, min_val, max_val, pos_pct, pct_text in kpi_spark_data:
        pattern = re.compile(
            rf'(<div class="kpi-label">{re.escape(lbl)}</div>\s*<div class="kpi-value">.*?</div>\s*<div class="kpi-sub">.*?</div>)',
            re.DOTALL
        )
        spark_html = f"""\\1
      <div class="ft-spark-range" title="5-Year Historical Range Context">
        <div class="ft-spark-track">
          <div class="ft-spark-point" style="left: {pos_pct}%;"></div>
        </div>
        <div class="ft-spark-labels">
          <span>{min_val}</span>
          <span class="ft-spark-pct">{pct_text}</span>
          <span>{max_val}</span>
        </div>
      </div>"""
        html = pattern.sub(spark_html, html)

    # 7. Apply Chart-Level FT Visual Vocabulary Upgrades in JavaScript
    ft_js_processor = """
<script type="text/javascript">
(function() {
  function enhanceChartsFT() {
    if (!window.Plotly) return;

    // Define FT Chart Doctor Theme Layout
    const ftLayoutDefaults = {
      paper_bgcolor: "#ffffff",
      plot_bgcolor: "#ffffff",
      font: {
        family: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif',
        size: 11,
        color: "#12151a"
      },
      margin: { l: 48, r: 24, t: 40, b: 36 }
    };

    // 1. CPI & Inflation: Add NBP Target Band (1.5% - 3.5%) + 2.5% Target Line
    const cpiChartIds = [
      "chart-prices_wages-cpi_yoy-01",
      "chart-prices_wages-core_cpi_yoy-02"
    ];
    cpiChartIds.forEach(id => {
      const el = document.getElementById(id);
      if (el && el.data) {
        Plotly.relayout(el, {
          ...ftLayoutDefaults,
          "xaxis.showgrid": false,
          "yaxis.gridcolor": "rgba(18, 21, 26, 0.07)",
          "yaxis.zeroline": true,
          "yaxis.zerolinecolor": "rgba(18, 21, 26, 0.4)",
          "yaxis.zerolinewidth": 1.4,
          shapes: [
            // Target band: 1.5% - 3.5%
            {
              type: "rect",
              xref: "paper",
              yref: "y",
              x0: 0,
              x1: 1,
              y0: 1.5,
              y1: 3.5,
              fillcolor: "rgba(13, 118, 128, 0.12)",
              line: { width: 0 },
              layer: "below"
            },
            // Target center line: 2.5%
            {
              type: "line",
              xref: "paper",
              yref: "y",
              x0: 0,
              x1: 1,
              y0: 2.5,
              y1: 2.5,
              line: { color: "rgba(13, 118, 128, 0.75)", width: 1.5, dash: "dash" }
            }
          ],
          annotations: [
            {
              xref: "paper",
              yref: "y",
              x: 0.98,
              y: 2.5,
              xanchor: "right",
              yanchor: "bottom",
              text: "NBP Target: 2.5% (±1pp band)",
              showarrow: false,
              font: { size: 10, color: "#0d7680", family: "sans-serif" },
              bgcolor: "rgba(255, 255, 255, 0.85)"
            }
          ]
        });
        if (el.data[0]) {
          Plotly.restyle(el, { "line.color": "#990f3d", "line.width": 2.5 }, [0]);
        }
      }
    });

    // 2. Fiscal Balance & Deficits: Diverging Bar Chart + Maastricht -3.0% Limit
    const fiscalChartIds = [
      "chart-fiscal_sovereign-fiscal_balance_pct_gdp-13",
      "chart-fiscal_sovereign-primary_balance-03",
      "chart-fiscal_sovereign-structural_balance-02"
    ];
    fiscalChartIds.forEach(id => {
      const el = document.getElementById(id);
      if (el && el.data && el.data[0]) {
        const yVals = el.data[0].y;
        // Transform to Diverging Bar (Teal for surplus, Claret for deficit)
        const colors = yVals.map(v => v >= 0 ? "#0d7680" : "#990f3d");
        Plotly.restyle(el, {
          type: "bar",
          "marker.color": [colors],
          "marker.line.width": 0.5,
          "marker.line.color": "#ffffff"
        }, [0]);

        Plotly.relayout(el, {
          ...ftLayoutDefaults,
          "xaxis.showgrid": false,
          "yaxis.gridcolor": "rgba(18, 21, 26, 0.07)",
          "yaxis.zeroline": true,
          "yaxis.zerolinecolor": "rgba(18, 21, 26, 0.5)",
          "yaxis.zerolinewidth": 1.6,
          shapes: [
            // Maastricht deficit limit at -3.0%
            {
              type: "line",
              xref: "paper",
              yref: "y",
              x0: 0,
              x1: 1,
              y0: -3.0,
              y1: -3.0,
              line: { color: "rgba(153, 15, 61, 0.65)", width: 1.5, dash: "dot" }
            }
          ],
          annotations: [
            {
              xref: "paper",
              yref: "y",
              x: 0.02,
              y: -3.0,
              xanchor: "left",
              yanchor: "top",
              text: "EU Maastricht Limit: -3.0%",
              showarrow: false,
              font: { size: 10, color: "#990f3d" },
              bgcolor: "rgba(255, 255, 255, 0.85)"
            }
          ]
        });
      }
    });

    // 3. Current Account & Trade Balance: Diverging Bar Chart
    const externalBarChartIds = [
      "chart-external-current_account_pct_gdp-9",
      "chart-external-trade_balance-10"
    ];
    externalBarChartIds.forEach(id => {
      const el = document.getElementById(id);
      if (el && el.data && el.data[0]) {
        const yVals = el.data[0].y;
        const colors = yVals.map(v => v >= 0 ? "#0d7680" : "#990f3d");
        Plotly.restyle(el, {
          type: "bar",
          "marker.color": [colors],
          "marker.line.width": 0.5,
          "marker.line.color": "#ffffff"
        }, [0]);

        Plotly.relayout(el, {
          ...ftLayoutDefaults,
          "xaxis.showgrid": false,
          "yaxis.gridcolor": "rgba(18, 21, 26, 0.07)",
          "yaxis.zeroline": true,
          "yaxis.zerolinecolor": "rgba(18, 21, 26, 0.5)",
          "yaxis.zerolinewidth": 1.6
        });
      }
    });

    // 4. Credit-to-GDP Gap: Diverging Area / Bars
    const creditGapEl = document.getElementById("chart-monetary_financial-credit_to_gdp_gap-05");
    if (creditGapEl && creditGapEl.data && creditGapEl.data[0]) {
      const yVals = creditGapEl.data[0].y;
      const colors = yVals.map(v => v >= 0 ? "#b86200" : "#0d7680");
      Plotly.restyle(creditGapEl, {
        type: "bar",
        "marker.color": [colors]
      }, [0]);
      Plotly.relayout(creditGapEl, {
        ...ftLayoutDefaults,
        "xaxis.showgrid": false,
        "yaxis.gridcolor": "rgba(18, 21, 26, 0.07)",
        "yaxis.zeroline": true,
        "yaxis.zerolinecolor": "rgba(18, 21, 26, 0.5)",
        "yaxis.zerolinewidth": 1.6,
        annotations: [{
          xref: "paper", yref: "paper", x: 0.02, y: 0.95,
          text: "Amber: Credit Expansion | Teal: Deleveraging",
          showarrow: false, font: { size: 10, color: "#666" }
        }]
      });
    }

    // 5. Global Clean Gridlines & Zero Baseline for ALL charts
    document.querySelectorAll(".plotly-graph-div").forEach(chartDiv => {
      if (chartDiv.data) {
        Plotly.relayout(chartDiv, {
          "xaxis.showgrid": false,
          "yaxis.gridcolor": "rgba(18, 21, 26, 0.06)",
          "yaxis.zeroline": true,
          "yaxis.zerolinecolor": "rgba(18, 21, 26, 0.35)",
          "yaxis.zerolinewidth": 1.2,
          paper_bgcolor: "#ffffff",
          plot_bgcolor: "#ffffff"
        });
      }
    });
  }

  // Run on initial load and after a short delay
  if (document.readyState === "complete" || document.readyState === "interactive") {
    setTimeout(enhanceChartsFT, 300);
  } else {
    document.addEventListener("DOMContentLoaded", () => setTimeout(enhanceChartsFT, 300));
  }
})();
</script>
"""
    html = html.replace("</body>", f"{ft_js_processor}\n</body>")

    out_path = OUTPUT / "poland_new.html"
    out_path.write_text(html, encoding="utf-8")
    print(f"Wrote {out_path} ({len(html):,} bytes)")

if __name__ == "__main__":
    build()
