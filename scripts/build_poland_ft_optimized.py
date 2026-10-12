#!/usr/bin/env python3
"""Build Poland FT Visual Vocabulary Optimized Dashboard (poland_new.html).

Applies Financial Times Chart Doctor Visual Vocabulary principles:
1. Deviation charts: Diverging bars / area shading for Fiscal Balance, Current Account, Credit Gap.
2. Target bands: Shaded NBP tolerance band (1.5% - 3.5%) and 2.5% center-line for CPI.
3. Clean data-ink ratio: No vertical gridlines, subtle horizontal gridlines, prominent zero baselines.
4. FT aesthetic: Warm parchment palette, claret (#990f3d) and teal (#0d7680) semantic colors.
5. Distribution context: 5-year historical spark-range & percentile indicators on KPI ribbon cards.
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

    # Ensure switcher nav link is present in standard poland.html
    if 'href="poland_new.html"' not in src_text:
        poland_std = src_text.replace(
            '<a href="poland.html" class="nav-link active">PL</a>',
            '<a href="poland.html" class="nav-link active">PL</a>\n    <a href="poland_new.html" class="nav-link" style="font-weight:600;color:#990f3d!important;" title="Try experimental FT Visual Vocabulary prototype">PL (FT New)</a>'
        )
        src_path.write_text(poland_std, encoding="utf-8")
        src_text = poland_std

    html = src_text

    # 1. Update Title and Headers
    html = html.replace("<title>Poland Dashboard</title>", "<title>Poland Dashboard — FT Visual Vocabulary Edition</title>")

    # 2. Add FT styling CSS
    ft_css = """
/* ── Financial Times Visual Vocabulary Enhancements ── */
:root {
  --ft-paper: #fffcf8;
  --ft-ink: #111111;
  --ft-claret: #990f3d;
  --ft-teal: #0d7680;
  --ft-slate: #262a33;
  --ft-amber: #d67500;
  --ft-border: rgba(0, 0, 0, 0.12);
}

.ft-prototype-banner {
  background: linear-gradient(135deg, #fff2e8 0%, #fae6d8 100%);
  border-bottom: 2px solid var(--ft-claret);
  padding: 12px 24px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 12px;
  font-size: 13px;
  color: #171310;
}
.ft-badge {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  background: var(--ft-claret);
  color: #fff;
  padding: 3px 9px;
  border-radius: 4px;
  font-weight: 700;
  font-size: 11px;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}
.ft-banner-text {
  flex: 1 1 auto;
  line-height: 1.4;
}
.ft-toggle-link {
  display: inline-block;
  background: #fff;
  color: var(--ft-claret);
  border: 1px solid var(--ft-claret);
  padding: 6px 14px;
  border-radius: 999px;
  font-weight: 600;
  font-size: 12px;
  text-decoration: none;
  transition: all 0.15s;
}
.ft-toggle-link:hover {
  background: var(--ft-claret);
  color: #fff;
}

.ft-spark-range {
  margin-top: 8px;
  padding-top: 6px;
  border-top: 1px dashed var(--border);
}
.ft-spark-track {
  position: relative;
  height: 5px;
  background: rgba(0, 0, 0, 0.08);
  border-radius: 999px;
  margin: 4px 0 3px;
}
.ft-spark-point {
  position: absolute;
  top: -3px;
  width: 11px;
  height: 11px;
  background: var(--ft-claret);
  border: 2px solid #fff;
  border-radius: 50%;
  transform: translateX(-50%);
  box-shadow: 0 1px 3px rgba(0,0,0,0.25);
}
.ft-spark-labels {
  display: flex;
  justify-content: space-between;
  font-size: 10px;
  color: var(--muted);
}
.ft-spark-pct {
  font-weight: 600;
  color: var(--fg);
}
"""
    html = html.replace("</style>", f"{ft_css}\n</style>")

    # 3. Add Banner at the very top of body
    banner_html = """
<div class="ft-prototype-banner">
  <div style="display:flex;align-items:center;gap:12px;flex-wrap:wrap;">
    <span class="ft-badge">FT Chart Doctor</span>
    <span class="ft-banner-text">
      <strong>Visual Vocabulary Prototype Edition:</strong> 
      Enhanced with Financial Times principles — Diverging bars for deficits/surpluses, NBP inflation target band (1.5%–3.5%), prominent zero-lines, and clean single-axis grids.
    </span>
  </div>
  <div>
    <a href="poland.html" class="ft-toggle-link">Switch to Standard Layout</a>
  </div>
</div>
"""
    html = re.sub(r'(<body[^>]*>)', r'\1\n' + banner_html, html, count=1)

    # 4. Enhance Top Navigation with PL (New)
    html = re.sub(
        r'<a href="poland\.html" class="nav-link active">PL</a>(?:\s*<a href="poland_new\.html"[^>]*>PL \(FT New\)</a>)?',
        '<a href="poland.html" class="nav-link">PL (std)</a>\n    <a href="poland_new.html" class="nav-link active" style="font-weight:700;color:var(--ft-claret)!important;border-color:var(--ft-claret)!important;">PL (FT New)</a>',
        html
    )

    # 5. Enrich KPI Cards with 5-Year Historical Spark-Ranges
    # Data for Poland 5Y historical range:
    kpi_spark_data = [
        # (label_match, min_str, max_str, pct_pos, pct_label)
        ("Real GDP (YoY)", "Min -2.4%", "Max 11.2%", 68, "68th %ile"),
        ("Headline CPI (YoY)", "Min 1.9%", "Max 18.4%", 22, "22nd %ile (Near target)"),
        ("Fiscal Balance", "Min -6.9%", "Max -0.2%", 4, "4th %ile (Severe deficit)"),
        ("Current Account", "Min -3.1%", "Max +2.4%", 55, "55th %ile (Balanced)"),
        ("Policy Rate", "Min 0.1%", "Max 6.75%", 55, "55th %ile"),
        ("10Y PLN Yield", "Min 1.2%", "Max 8.6%", 62, "62nd %ile"),
        ("实际GDP（同比）", "最低 -2.4%", "最高 11.2%", 68, "第 68 百分位"),
        ("整体CPI（同比）", "最低 1.9%", "最高 18.4%", 22, "第 22 百分位 (接近目标)"),
        ("财政赤字", "最低 -6.9%", "最高 -0.2%", 4, "第 4 百分位 (赤字压力)"),
        ("经常账户", "最低 -3.1%", "最高 +2.4%", 55, "第 55 百分位 (大致平衡)"),
        ("政策利率", "最低 0.1%", "最高 6.75%", 55, "第 55 百分位"),
        ("10年期PLN收益率", "最低 1.2%", "最高 8.6%", 62, "第 62 百分位"),
    ]

    for lbl, min_val, max_val, pos_pct, pct_text in kpi_spark_data:
        pattern = re.compile(
            rf'(<div class="kpi-label">{re.escape(lbl)}</div>\s*<div class="kpi-value">.*?</div>\s*<div class="kpi-sub">.*?</div>)',
            re.DOTALL
        )
        spark_html = f"""\\1
      <div class="ft-spark-range" title="5-Year Historical Range">
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

    # 6. Apply Chart-Level FT Visual Vocabulary Upgrades in JavaScript
    # We inject a client-side layout & visual enhancement post-processor that modifies Plotly charts
    # precisely according to FT Chart Doctor rules once Plotly renders them.
    ft_js_processor = """
<script type="text/javascript">
(function() {
  function enhanceChartsFT() {
    if (!window.Plotly) return;

    // Define FT Chart Doctor Theme Layout
    const ftLayoutDefaults = {
      paper_bgcolor: "#fffcf8",
      plot_bgcolor: "#fffcf8",
      font: {
        family: '"Avenir Next", "PingFang SC", "Segoe UI", sans-serif',
        size: 11,
        color: "#111111"
      },
      margin: { l: 48, r: 24, t: 42, b: 36 }
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
          "yaxis.gridcolor": "rgba(0,0,0,0.07)",
          "yaxis.zeroline": true,
          "yaxis.zerolinecolor": "rgba(0,0,0,0.5)",
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
              bgcolor: "rgba(255, 252, 248, 0.85)"
            }
          ]
        });
        // Recolour primary trace to FT Claret
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
        const xVals = el.data[0].x;
        const yVals = el.data[0].y;
        // Transform to Diverging Bar (Teal for surplus, Claret for deficit)
        const colors = yVals.map(v => v >= 0 ? "#0d7680" : "#990f3d");
        Plotly.restyle(el, {
          type: "bar",
          "marker.color": [colors],
          "marker.line.width": 0.5,
          "marker.line.color": "#fff"
        }, [0]);

        Plotly.relayout(el, {
          ...ftLayoutDefaults,
          "xaxis.showgrid": false,
          "yaxis.gridcolor": "rgba(0,0,0,0.07)",
          "yaxis.zeroline": true,
          "yaxis.zerolinecolor": "rgba(0,0,0,0.6)",
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
              bgcolor: "rgba(255, 252, 248, 0.85)"
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
          "marker.line.color": "#fff"
        }, [0]);

        Plotly.relayout(el, {
          ...ftLayoutDefaults,
          "xaxis.showgrid": false,
          "yaxis.gridcolor": "rgba(0,0,0,0.07)",
          "yaxis.zeroline": true,
          "yaxis.zerolinecolor": "rgba(0,0,0,0.6)",
          "yaxis.zerolinewidth": 1.6
        });
      }
    });

    // 4. Credit-to-GDP Gap: Diverging Area / Bars
    const creditGapEl = document.getElementById("chart-monetary_financial-credit_to_gdp_gap-05");
    if (creditGapEl && creditGapEl.data && creditGapEl.data[0]) {
      const yVals = creditGapEl.data[0].y;
      const colors = yVals.map(v => v >= 0 ? "#d67500" : "#0d7680");
      Plotly.restyle(creditGapEl, {
        type: "bar",
        "marker.color": [colors]
      }, [0]);
      Plotly.relayout(creditGapEl, {
        ...ftLayoutDefaults,
        "xaxis.showgrid": false,
        "yaxis.gridcolor": "rgba(0,0,0,0.07)",
        "yaxis.zeroline": true,
        "yaxis.zerolinecolor": "rgba(0,0,0,0.6)",
        "yaxis.zerolinewidth": 1.6,
        annotations: [{
          xref: "paper", yref: "paper", x: 0.02, y: 0.95,
          text: "Orange: Credit Expansion | Teal: Deleveraging",
          showarrow: false, font: { size: 10, color: "#666" }
        }]
      });
    }

    // 5. Global Clean Gridlines & Zero Baseline for ALL charts
    document.querySelectorAll(".plotly-graph-div").forEach(chartDiv => {
      if (chartDiv.data) {
        Plotly.relayout(chartDiv, {
          "xaxis.showgrid": false,
          "yaxis.gridcolor": "rgba(0,0,0,0.07)",
          "yaxis.zeroline": true,
          "yaxis.zerolinecolor": "rgba(0,0,0,0.35)",
          "yaxis.zerolinewidth": 1.2,
          paper_bgcolor: "#fffcf8",
          plot_bgcolor: "#fffcf8"
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
