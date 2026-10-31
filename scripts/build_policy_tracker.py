#!/usr/bin/env python3
"""Build script for the Central Bank Policy & Macro Event Tracker.

Generates output/policy_tracker.html and policy_tracker.html in the root.
Includes:
  1. Global Central Bank Policy Corridors & Decision Countdown Matrix (Fed, ECB, BoE, BoJ, PBOC, and key peers)
  2. Interactive FOMC Dot Plot vs Market Implied Forward Pricing Curve (Plotly)
  3. Word-level Statement Semantic Diff & Hawk/Dove Tone Sentiment Analyzer (FOMC, ECB, BoE)
  4. Interactive Macro Shock Scenario Simulators (Crude Oil, US 10Y Yield Curve, Universal Tariffs)
  5. 2026/2027 Central Bank Meeting Calendar & Schedule with filtering and export
  6. FT & Claude UI design system tokens, responsive layout, and complete bilingual support (EN/ZH).
"""
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "output"

COUNTRY_NAV = [
    ("HU", "Hungary", "匈牙利", "hungary.html"),
    ("PL", "Poland", "波兰", "poland.html"),
    ("CZ", "Czechia", "捷克", "czechia.html"),
    ("RO", "Romania", "罗马尼亚", "romania.html"),
    ("CN", "China", "中国", "china.html"),
    ("EA", "Euro Area", "欧元区", "euro_area.html"),
    ("JP", "Japan", "日本", "japan.html"),
    ("ZA", "South Africa", "南非", "south_africa.html"),
    ("UK", "United Kingdom", "英国", "uk.html"),
    ("US", "United States", "美国", "us.html"),
    ("TR", "Turkey", "土耳其", "turkey.html"),
    ("HK", "Hong Kong", "中国香港", "hong_kong.html"),
    ("KR", "South Korea", "韩国", "south_korea.html"),
    ("TW", "Taiwan", "中国台湾", "taiwan.html"),
    ("KZ", "Kazakhstan", "哈萨克斯坦", "kazakhstan.html"),
    ("UZ", "Uzbekistan", "乌兹别克斯坦", "uzbekistan.html"),
    ("EG", "Egypt", "埃及", "egypt.html"),
    ("NG", "Nigeria", "尼日利亚", "nigeria.html"),
]


def load_macro_workbench_summary() -> dict:
    """Load latest compiled macro workbench summary if available."""
    wb_file = OUTPUT / "macro_workbench_summary.json"
    if wb_file.exists():
        try:
            with open(wb_file, encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"Warning: Failed to load {wb_file}: {e}")
    return {}


def build_policy_tracker_html() -> str:
    """Generate the complete standalone Policy Tracker HTML application."""
    wb = load_macro_workbench_summary()
    stances = wb.get("monetary_stance_monitor", {})
    liquidity_items = wb.get("central_bank_liquidity_monitor", [])

    country_nav_links = "\n    ".join(
        f'<a href="{href}" title="{name_en} ({name_zh})">{code}</a>'
        for code, name_en, name_zh, href in COUNTRY_NAV
    )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Central Bank Policy & Event Tracker · 全球央行与宏观事件追踪</title>
  <link rel="icon" href="data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 100 100%22><text y=%22.9em%22 font-size=%2290%22>🏛️</text></svg>">
  <script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script>
  <style>
    :root {{
      --bg: #fffdfa;
      --surface: #ffffff;
      --card-bg: #ffffff;
      --border: #e8e4df;
      --border-subtle: #f0ebe4;
      --fg: #12151a;
      --text-secondary: #737c8c;
      --accent: #990f3d; /* FT Burgundy */
      --teal: #0d7680;   /* FT Teal */
      --slate: #364b61;  /* Slate Navy */
      --amber: #d97706;  /* Claude Amber */
      --good: #0d7680;
      --bad: #990f3d;
      --font-main: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
      --font-serif: "Newsreader", "Iowan Old Style", "Songti SC", Georgia, serif;
      --font-mono: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
      --shadow-sm: 0 1px 2px rgba(18, 21, 26, 0.04);
      --shadow-md: 0 4px 12px rgba(18, 21, 26, 0.08);
      --shadow-lg: 0 8px 24px rgba(18, 21, 26, 0.12);
      --radius: 6px;
    }}

    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      font-family: var(--font-main);
      background-color: var(--bg);
      color: var(--fg);
      line-height: 1.5;
      padding-bottom: 80px;
      -webkit-font-smoothing: antialiased;
    }}

    /* Topbar matching institutional standard */
    .topbar {{
      position: sticky;
      top: 0;
      z-index: 100;
      background: var(--surface);
      border-bottom: 1px solid var(--border);
      padding: 0 20px;
      height: 48px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 16px;
    }}
    .brand {{
      font-family: var(--font-serif);
      font-size: 16px;
      font-weight: 700;
      color: var(--fg);
      text-decoration: none;
      letter-spacing: -0.01em;
      white-space: nowrap;
    }}
    .brand span {{
      color: var(--accent);
      font-weight: 400;
    }}

    .country-nav {{
      display: flex;
      align-items: center;
      gap: 6px;
      overflow-x: auto;
      white-space: nowrap;
      padding: 4px 0;
      scrollbar-width: none;
    }}
    .country-nav::-webkit-scrollbar {{ display: none; }}
    .country-nav a {{
      font-size: 11px;
      font-weight: 600;
      color: var(--text-secondary);
      text-decoration: none;
      padding: 3px 6px;
      border-radius: 3px;
      transition: background 0.15s, color 0.15s;
    }}
    .country-nav a:hover {{
      background: var(--border-subtle);
      color: var(--fg);
    }}

    .topbar-actions {{
      display: flex;
      align-items: center;
      gap: 10px;
      flex-shrink: 0;
    }}
    .topbar-btn {{
      font-size: 11px;
      font-weight: 600;
      padding: 4px 10px;
      border-radius: 4px;
      border: 1px solid var(--border);
      background: var(--surface);
      color: var(--fg);
      cursor: pointer;
      text-decoration: none;
      display: inline-flex;
      align-items: center;
      gap: 4px;
      transition: background 0.15s;
    }}
    .topbar-btn:hover {{
      background: var(--border-subtle);
    }}
    .topbar-btn.active {{
      background: var(--accent);
      color: #ffffff;
      border-color: var(--accent);
    }}

    /* Container Layout */
    .container {{
      max-width: 1440px;
      margin: 0 auto;
      padding: 24px 20px;
    }}

    /* Header Section */
    .header-banner {{
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: var(--radius);
      padding: 24px 28px;
      box-shadow: var(--shadow-sm);
      margin-bottom: 24px;
      position: relative;
    }}
    .header-row {{
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      gap: 20px;
      flex-wrap: wrap;
    }}
    .header-title-box h1 {{
      font-family: var(--font-serif);
      font-size: 32px;
      font-weight: 700;
      color: var(--fg);
      line-height: 1.15;
      margin-bottom: 8px;
    }}
    .header-subtitle {{
      color: var(--text-secondary);
      font-size: 13.5px;
      max-width: 860px;
      line-height: 1.5;
    }}
    .header-pills {{
      display: flex;
      align-items: center;
      gap: 10px;
      flex-wrap: wrap;
      margin-top: 14px;
    }}
    .pill {{
      font-size: 11.5px;
      background: #fbf9f6;
      border: 1px solid var(--border);
      padding: 4px 10px;
      border-radius: 4px;
      color: var(--text-secondary);
      display: inline-flex;
      align-items: center;
      gap: 6px;
    }}
    .pill strong {{
      color: var(--fg);
      font-family: var(--font-mono);
      font-weight: 600;
    }}
    .pill.accent {{
      border-color: rgba(153, 15, 61, 0.3);
      background: rgba(153, 15, 61, 0.05);
      color: var(--accent);
    }}
    .pill.teal {{
      border-color: rgba(13, 118, 128, 0.3);
      background: rgba(13, 118, 128, 0.05);
      color: var(--teal);
    }}

    /* Global Stance Bar */
    .cycle-ticker {{
      background: #fdfaf6;
      border: 1px solid var(--border);
      border-radius: 6px;
      padding: 12px 18px;
      margin-top: 16px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      flex-wrap: wrap;
      gap: 16px;
      font-size: 12.5px;
    }}
    .cycle-stats {{
      display: flex;
      align-items: center;
      gap: 18px;
      flex-wrap: wrap;
    }}
    .cycle-item {{
      display: inline-flex;
      align-items: center;
      gap: 6px;
    }}
    .cycle-badge {{
      padding: 2px 7px;
      border-radius: 3px;
      font-size: 10.5px;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.03em;
    }}
    .cycle-badge.easing {{ background: #e6f4ea; color: #137333; }}
    .cycle-badge.holding {{ background: #fef7e0; color: #b06000; }}
    .cycle-badge.hiking {{ background: #fce8e6; color: #c5221f; }}

    /* Tab Navigation */
    .module-nav {{
      display: flex;
      align-items: center;
      gap: 8px;
      border-bottom: 2px solid var(--border);
      margin-bottom: 24px;
      overflow-x: auto;
      scrollbar-width: none;
      padding-bottom: 2px;
    }}
    .module-nav::-webkit-scrollbar {{ display: none; }}
    .tab-btn {{
      font-family: var(--font-main);
      font-size: 13px;
      font-weight: 600;
      padding: 9px 18px;
      border: none;
      background: transparent;
      color: var(--text-secondary);
      cursor: pointer;
      border-bottom: 2px solid transparent;
      margin-bottom: -2px;
      transition: color 0.15s, border-color 0.15s;
      display: inline-flex;
      align-items: center;
      gap: 8px;
      white-space: nowrap;
    }}
    .tab-btn:hover {{
      color: var(--fg);
    }}
    .tab-btn.active {{
      color: var(--accent);
      border-bottom-color: var(--accent);
      font-weight: 700;
    }}

    /* Module Panes */
    .tab-pane {{
      display: none;
    }}
    .tab-pane.active {{
      display: block;
    }}

    /* Section Header */
    .section-head {{
      display: flex;
      justify-content: space-between;
      align-items: flex-end;
      margin-bottom: 16px;
      flex-wrap: wrap;
      gap: 12px;
    }}
    .section-head h2 {{
      font-family: var(--font-serif);
      font-size: 20px;
      font-weight: 700;
      color: var(--fg);
    }}
    .section-head p {{
      font-size: 12.5px;
      color: var(--text-secondary);
    }}

    /* Central Bank Decision Cards Grid */
    .cb-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(420px, 1fr));
      gap: 20px;
      margin-bottom: 28px;
    }}
    @media (max-width: 640px) {{
      .cb-grid {{ grid-template-columns: 1fr; }}
    }}

    .cb-card {{
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: var(--radius);
      box-shadow: var(--shadow-sm);
      overflow: hidden;
      display: flex;
      flex-direction: column;
      transition: transform 0.15s, box-shadow 0.15s;
    }}
    .cb-card:hover {{
      box-shadow: var(--shadow-md);
    }}
    .cb-card-header {{
      padding: 14px 18px;
      background: #faf8f5;
      border-bottom: 1px solid var(--border-subtle);
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 12px;
    }}
    .cb-name-wrap {{
      display: flex;
      align-items: center;
      gap: 10px;
    }}
    .cb-flag {{
      font-size: 24px;
      line-height: 1;
    }}
    .cb-name {{
      font-size: 14px;
      font-weight: 700;
      color: var(--fg);
    }}
    .cb-inst {{
      font-size: 11px;
      color: var(--text-secondary);
      font-family: var(--font-mono);
    }}

    .cb-badge {{
      font-size: 10.5px;
      font-weight: 700;
      padding: 3px 8px;
      border-radius: 4px;
      text-transform: uppercase;
      letter-spacing: 0.03em;
    }}
    .cb-badge.easing {{ background: #e6f4ea; color: #137333; }}
    .cb-badge.holding {{ background: #fef7e0; color: #b06000; }}
    .cb-badge.hiking {{ background: #fce8e6; color: #c5221f; }}

    .cb-card-body {{
      padding: 18px;
      display: flex;
      flex-direction: column;
      gap: 14px;
      flex: 1;
    }}

    /* Policy Rates Hero */
    .cb-rate-hero {{
      display: flex;
      align-items: baseline;
      justify-content: space-between;
      padding-bottom: 12px;
      border-bottom: 1px solid var(--border-subtle);
    }}
    .cb-rate-val {{
      font-family: var(--font-serif);
      font-size: 32px;
      font-weight: 700;
      color: var(--fg);
      line-height: 1;
    }}
    .cb-rate-meta {{
      text-align: right;
    }}
    .cb-rate-label {{
      font-size: 11px;
      color: var(--text-secondary);
      font-weight: 600;
      text-transform: uppercase;
    }}
    .cb-rate-delta {{
      font-size: 12px;
      font-weight: 700;
      font-family: var(--font-mono);
    }}
    .cb-rate-delta.neg {{ color: #137333; }}
    .cb-rate-delta.pos {{ color: #c5221f; }}

    /* Corridor Visualizer Bar */
    .corridor-box {{
      background: #fbf9f6;
      border: 1px solid var(--border-subtle);
      border-radius: 4px;
      padding: 10px 12px;
      display: flex;
      flex-direction: column;
      gap: 6px;
    }}
    .corridor-title {{
      font-size: 11px;
      font-weight: 700;
      color: var(--text-secondary);
      text-transform: uppercase;
      letter-spacing: 0.03em;
      display: flex;
      justify-content: space-between;
    }}
    .corridor-tiers {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 6px;
      font-family: var(--font-mono);
      font-size: 11.5px;
    }}
    .corridor-node {{
      text-align: center;
      padding: 4px 6px;
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: 3px;
      flex: 1;
    }}
    .corridor-node.current {{
      background: #fdf5f7;
      border-color: var(--accent);
      color: var(--accent);
      font-weight: 700;
    }}
    .corridor-node .node-label {{
      font-size: 9.5px;
      color: var(--text-secondary);
      display: block;
    }}

    /* Next Meeting Countdown Box */
    .meeting-box {{
      background: #fcfaf7;
      border: 1px solid var(--border);
      border-radius: 4px;
      padding: 10px 12px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
    }}
    .meeting-date-wrap {{
      display: flex;
      flex-direction: column;
      gap: 2px;
    }}
    .meeting-label {{
      font-size: 10.5px;
      font-weight: 600;
      color: var(--text-secondary);
      text-transform: uppercase;
    }}
    .meeting-date {{
      font-size: 12.5px;
      font-weight: 700;
      color: var(--fg);
    }}
    .countdown-chip {{
      font-family: var(--font-mono);
      font-size: 12px;
      font-weight: 700;
      background: var(--slate);
      color: #ffffff;
      padding: 4px 10px;
      border-radius: 4px;
      white-space: nowrap;
      letter-spacing: 0.02em;
    }}

    /* Market Probabilities Bar */
    .market-pricing {{
      display: flex;
      flex-direction: column;
      gap: 6px;
    }}
    .prob-head {{
      display: flex;
      justify-content: space-between;
      font-size: 11px;
      color: var(--text-secondary);
    }}
    .prob-bar {{
      height: 8px;
      background: var(--border-subtle);
      border-radius: 4px;
      overflow: hidden;
      display: flex;
    }}
    .prob-segment {{
      height: 100%;
      transition: width 0.3s;
    }}
    .prob-segment.cut {{ background: #0d7680; }}
    .prob-segment.hold {{ background: #d97706; }}
    .prob-segment.hike {{ background: #990f3d; }}

    /* Supplementary Table */
    .peer-table-wrap {{
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: var(--radius);
      box-shadow: var(--shadow-sm);
      overflow-x: auto;
      margin-bottom: 28px;
    }}
    .peer-table {{
      width: 100%;
      border-collapse: collapse;
      font-size: 12.5px;
      text-align: left;
    }}
    .peer-table th {{
      background: #faf8f5;
      padding: 10px 14px;
      color: var(--text-secondary);
      font-weight: 700;
      font-size: 11px;
      text-transform: uppercase;
      letter-spacing: 0.03em;
      border-bottom: 1px solid var(--border);
    }}
    .peer-table td {{
      padding: 10px 14px;
      border-bottom: 1px solid var(--border-subtle);
      vertical-align: middle;
    }}
    .peer-table tr:hover {{
      background: #fdfcf9;
    }}

    /* Dot Plot Section */
    .dotplot-wrap {{
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: var(--radius);
      padding: 20px;
      box-shadow: var(--shadow-sm);
      margin-bottom: 24px;
    }}
    .dotplot-meta {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      flex-wrap: wrap;
      gap: 12px;
      margin-bottom: 16px;
      padding-bottom: 14px;
      border-bottom: 1px solid var(--border-subtle);
    }}
    .divergence-callout {{
      background: #fcf6ec;
      border-left: 3px solid var(--amber);
      padding: 10px 14px;
      border-radius: 0 4px 4px 0;
      font-size: 12.5px;
      color: #6e4808;
      line-height: 1.45;
    }}
    .divergence-callout strong {{
      color: #452c00;
    }}

    /* Statement Diff Section */
    .diff-container {{
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: var(--radius);
      box-shadow: var(--shadow-sm);
      overflow: hidden;
      margin-bottom: 28px;
    }}
    .diff-toolbar {{
      padding: 12px 18px;
      background: #faf8f5;
      border-bottom: 1px solid var(--border);
      display: flex;
      justify-content: space-between;
      align-items: center;
      flex-wrap: wrap;
      gap: 12px;
    }}
    .diff-select-group {{
      display: flex;
      align-items: center;
      gap: 10px;
    }}
    .diff-select {{
      font-family: var(--font-main);
      font-size: 12.5px;
      padding: 5px 10px;
      border: 1px solid var(--border);
      border-radius: 4px;
      background: var(--surface);
      color: var(--fg);
      outline: none;
      font-weight: 600;
    }}
    .diff-mode-btn {{
      font-size: 11px;
      padding: 5px 10px;
      border: 1px solid var(--border);
      background: var(--surface);
      color: var(--text-secondary);
      border-radius: 4px;
      cursor: pointer;
      font-weight: 600;
    }}
    .diff-mode-btn.active {{
      background: var(--slate);
      color: #ffffff;
      border-color: var(--slate);
    }}

    /* Hawk Dove Sentiment Gauge */
    .diff-sentiment-bar {{
      padding: 12px 18px;
      background: #fdfaf6;
      border-bottom: 1px solid var(--border-subtle);
      display: flex;
      align-items: center;
      justify-content: space-between;
      flex-wrap: wrap;
      gap: 16px;
    }}
    .gauge-wrapper {{
      display: flex;
      align-items: center;
      gap: 12px;
    }}
    .gauge-label {{
      font-size: 11px;
      font-weight: 700;
      color: var(--text-secondary);
      text-transform: uppercase;
      letter-spacing: 0.03em;
    }}
    .gauge-meter {{
      width: 140px;
      height: 8px;
      background: #e8e4df;
      border-radius: 4px;
      position: relative;
      overflow: hidden;
    }}
    .gauge-center-line {{
      position: absolute;
      left: 50%;
      top: 0;
      bottom: 0;
      width: 2px;
      background: #737c8c;
    }}
    .gauge-fill {{
      position: absolute;
      top: 0;
      bottom: 0;
      border-radius: 4px;
    }}
    .gauge-fill.dove {{
      right: 50%;
      background: #0d7680;
    }}
    .gauge-fill.hawk {{
      left: 50%;
      background: #990f3d;
    }}

    .diff-legend {{
      display: flex;
      align-items: center;
      gap: 14px;
      font-size: 11px;
    }}
    .legend-item {{
      display: inline-flex;
      align-items: center;
      gap: 4px;
    }}
    .legend-box {{
      width: 12px;
      height: 12px;
      border-radius: 2px;
    }}
    .legend-box.add {{ background: #d4edda; border: 1px solid #c3e6cb; }}
    .legend-box.del {{ background: #f8d7da; border: 1px solid #f5c6cb; }}

    /* Diff Content Area */
    .diff-body {{
      padding: 24px;
      font-family: var(--font-serif);
      font-size: 15px;
      line-height: 1.75;
      color: #24292e;
    }}
    .diff-paragraph {{
      margin-bottom: 16px;
      position: relative;
    }}
    .diff-paragraph:last-child {{
      margin-bottom: 0;
    }}
    ins.diff-add {{
      background-color: #e6f4ea;
      color: #137333;
      text-decoration: none;
      padding: 1px 4px;
      border-radius: 3px;
      font-weight: 600;
    }}
    del.diff-del {{
      background-color: #fce8e6;
      color: #c5221f;
      text-decoration: line-through;
      padding: 1px 4px;
      border-radius: 3px;
      opacity: 0.8;
    }}
    .keyword-tag {{
      display: inline-block;
      font-family: var(--font-main);
      font-size: 10px;
      font-weight: 700;
      padding: 2px 6px;
      border-radius: 3px;
      vertical-align: middle;
      margin: 0 2px;
      text-transform: uppercase;
      letter-spacing: 0.04em;
    }}
    .keyword-tag.hawk {{ background: #fce8e6; color: #c5221f; }}
    .keyword-tag.dove {{ background: #e6f4ea; color: #137333; }}

    /* Macro Shock Simulator Section */
    .simulator-grid {{
      display: grid;
      grid-template-columns: 360px 1fr;
      gap: 24px;
      margin-bottom: 28px;
    }}
    @media (max-width: 900px) {{
      .simulator-grid {{ grid-template-columns: 1fr; }}
    }}

    .sim-controls {{
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: var(--radius);
      padding: 20px;
      box-shadow: var(--shadow-sm);
      display: flex;
      flex-direction: column;
      gap: 20px;
    }}
    .sim-preset-row {{
      display: flex;
      flex-direction: column;
      gap: 8px;
    }}
    .preset-label {{
      font-size: 11px;
      font-weight: 700;
      color: var(--text-secondary);
      text-transform: uppercase;
      letter-spacing: 0.03em;
    }}
    .preset-btn-group {{
      display: flex;
      flex-direction: column;
      gap: 6px;
    }}
    .preset-btn {{
      font-size: 11.5px;
      font-weight: 600;
      text-align: left;
      padding: 7px 10px;
      border: 1px solid var(--border);
      border-radius: 4px;
      background: #faf8f5;
      color: var(--fg);
      cursor: pointer;
      transition: background 0.15s, border-color 0.15s;
    }}
    .preset-btn:hover {{
      background: #f0ebe4;
      border-color: var(--text-secondary);
    }}
    .preset-btn.active {{
      background: rgba(153, 15, 61, 0.08);
      border-color: var(--accent);
      color: var(--accent);
    }}

    .slider-group {{
      display: flex;
      flex-direction: column;
      gap: 8px;
    }}
    .slider-head {{
      display: flex;
      justify-content: space-between;
      align-items: baseline;
    }}
    .slider-title {{
      font-size: 12px;
      font-weight: 700;
      color: var(--fg);
    }}
    .slider-value {{
      font-family: var(--font-mono);
      font-size: 13px;
      font-weight: 700;
      color: var(--accent);
    }}
    .range-input {{
      width: 100%;
      height: 6px;
      -webkit-appearance: none;
      background: #e8e4df;
      border-radius: 3px;
      outline: none;
    }}
    .range-input::-webkit-slider-thumb {{
      -webkit-appearance: none;
      appearance: none;
      width: 16px;
      height: 16px;
      border-radius: 50%;
      background: var(--accent);
      cursor: pointer;
      box-shadow: 0 1px 3px rgba(0,0,0,0.2);
    }}

    .sim-results {{
      display: flex;
      flex-direction: column;
      gap: 20px;
    }}
    .impact-matrix-card {{
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: var(--radius);
      padding: 20px;
      box-shadow: var(--shadow-sm);
    }}
    .matrix-title {{
      font-family: var(--font-serif);
      font-size: 16px;
      font-weight: 700;
      color: var(--fg);
      margin-bottom: 14px;
      display: flex;
      align-items: center;
      gap: 8px;
    }}
    .impact-cards-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
      gap: 14px;
    }}
    .impact-stat {{
      background: #fbf9f6;
      border: 1px solid var(--border-subtle);
      border-radius: 4px;
      padding: 12px 14px;
      display: flex;
      flex-direction: column;
      gap: 4px;
    }}
    .impact-label {{
      font-size: 11px;
      color: var(--text-secondary);
      font-weight: 600;
    }}
    .impact-val {{
      font-family: var(--font-mono);
      font-size: 20px;
      font-weight: 700;
      color: var(--fg);
    }}
    .impact-sub {{
      font-size: 11px;
      color: var(--text-secondary);
    }}

    /* Calendar Section */
    .cal-filter-row {{
      display: flex;
      align-items: center;
      gap: 8px;
      margin-bottom: 16px;
      flex-wrap: wrap;
    }}
    .cal-btn {{
      font-size: 11.5px;
      font-weight: 600;
      padding: 5px 12px;
      border: 1px solid var(--border);
      background: var(--surface);
      color: var(--fg);
      border-radius: 4px;
      cursor: pointer;
    }}
    .cal-btn.active {{
      background: var(--slate);
      color: #ffffff;
      border-color: var(--slate);
    }}

    .cal-table-wrap {{
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: var(--radius);
      box-shadow: var(--shadow-sm);
      overflow-x: auto;
    }}
    .cal-table {{
      width: 100%;
      border-collapse: collapse;
      font-size: 12.5px;
      text-align: left;
    }}
    .cal-table th {{
      background: #faf8f5;
      padding: 10px 14px;
      color: var(--text-secondary);
      font-weight: 700;
      font-size: 11px;
      text-transform: uppercase;
      letter-spacing: 0.03em;
      border-bottom: 1px solid var(--border);
    }}
    .cal-table td {{
      padding: 10px 14px;
      border-bottom: 1px solid var(--border-subtle);
      vertical-align: middle;
    }}
    .cal-table tr:hover {{
      background: #fdfcf9;
    }}
    .tag-sep {{
      font-size: 10px;
      font-weight: 700;
      background: #eef2f6;
      color: #1e3a8a;
      padding: 2px 6px;
      border-radius: 3px;
      text-transform: uppercase;
      margin-left: 6px;
    }}

    /* Footer matching institutional primer */
    .footer {{
      margin-top: 48px;
      padding-top: 24px;
      border-top: 1px solid var(--border);
      color: var(--text-secondary);
      font-size: 12px;
      display: flex;
      justify-content: space-between;
      flex-wrap: wrap;
      gap: 16px;
    }}
    .footer a {{
      color: var(--fg);
      text-decoration: underline;
    }}

    /* Bilingual display helper */
    [data-lang="zh"] {{ display: none; }}
    body.lang-zh [data-lang="en"] {{ display: none; }}
    body.lang-zh [data-lang="zh"] {{ display: inline; }}
    body.lang-zh .block-zh {{ display: block !important; }}
    body.lang-zh .block-en {{ display: none !important; }}
    .block-zh {{ display: none; }}
    .block-en {{ display: block; }}
  </style>
</head>
<body>

<!-- Institutional Topbar Navigation -->
<div class="topbar">
  <div style="display:flex;align-items:center;gap:16px;">
    <a href="index.html" class="brand">Macro<span>Dashboard</span></a>
    <nav class="country-nav">
      {country_nav_links}
    </nav>
  </div>
  <div class="topbar-actions">
    <a href="chart_studio.html" class="topbar-btn" title="Macro Chart Studio · 宏观图表工坊">📈 Studio</a>
    <a href="my_dashboard.html" class="topbar-btn" title="My Dashboard · 我的自选宏观看板">⭐ My Dashboard</a>
    <a href="policy_tracker.html" class="topbar-btn active" title="Central Bank Policy & Event Tracker · 全球央行与宏观事件追踪">🏛️ Policy</a>
    <button class="topbar-btn" onclick="toggleLang()" id="lang-btn">中文</button>
  </div>
</div>

<div class="container">

  <!-- Header Banner -->
  <div class="header-banner">
    <div class="header-row">
      <div class="header-title-box">
        <h1>
          <span data-lang="en">Central Bank Policy & Macro Event Tracker</span>
          <span data-lang="zh">全球央行决议与重大宏观事件追踪器</span>
        </h1>
        <p class="header-subtitle">
          <span data-lang="en">Institutional real-time tracking of G5 policy corridors, FOMC dot plot projections vs market implied curves, word-level statement semantic diffs, and interactive macro shock scenario simulators.</span>
          <span data-lang="zh">机构级全球央行监测平台：覆盖 G5 政策利率走廊、FOMC 点阵图与市场定价曲线对比、议息声明逐字语义 Diff 与鹰鸽情绪打分，以及多维宏观冲击情景模拟引擎。</span>
        </p>
        <div class="header-pills">
          <div class="pill teal">
            <span data-lang="en">Policy Frameworks:</span>
            <span data-lang="zh">监测框架：</span>
            <strong>Fed · ECB · BoE · BoJ · PBOC</strong>
          </div>
          <div class="pill accent">
            <span data-lang="en">Next Key Decision:</span>
            <span data-lang="zh">下个关键决议：</span>
            <strong id="next-major-decision">ECB (Dec 12)</strong>
          </div>
          <div class="pill">
            <span data-lang="en">Global QT Runoff:</span>
            <span data-lang="zh">全球缩表总规模：</span>
            <strong>-$2.65T Cumulative</strong>
          </div>
        </div>
      </div>
    </div>

    <!-- Cycle Ticker -->
    <div class="cycle-ticker">
      <div class="cycle-stats">
        <div class="cycle-item">
          <strong><span data-lang="en">Global Cycle Stance:</span><span data-lang="zh">全球货币周期：</span></strong>
          <span class="cycle-badge easing"><span data-lang="en">Synchronized Easing (12/17)</span><span data-lang="zh">同步宽松中 (12/17)</span></span>
        </div>
        <div class="cycle-item">
          <span style="color:var(--text-secondary);">•</span>
          <span data-lang="en">Net 2024 Cuts:</span><span data-lang="zh">2024 年净降息：</span>
          <strong style="color:var(--good);font-family:var(--font-mono);">-1,425 bps</strong>
        </div>
        <div class="cycle-item">
          <span style="color:var(--text-secondary);">•</span>
          <span data-lang="en">Lone Hiker:</span><span data-lang="zh">唯一定期加息国：</span>
          <strong style="color:var(--bad);">🇯🇵 BoJ (+35 bps)</strong>
        </div>
      </div>
      <div>
        <span style="color:var(--text-secondary);font-size:11.5px;">
          <span data-lang="en">Live Fed EFFR: <strong>4.83%</strong> | ECB DFR: <strong>3.25%</strong> | PBOC 7D: <strong>1.50%</strong></span>
          <span data-lang="zh">实时有效利率: 美联储 <strong>4.83%</strong> | 欧央行 <strong>3.25%</strong> | 人行7天逆回购 <strong>1.50%</strong></span>
        </span>
      </div>
    </div>
  </div>

  <!-- Tab Navigation -->
  <nav class="module-nav">
    <button class="tab-btn active" onclick="switchTab('corridors')">
      🏛️ <span data-lang="en">Policy Corridors & Decisions</span><span data-lang="zh">利率走廊与议息矩阵</span>
    </button>
    <button class="tab-btn" onclick="switchTab('dotplot')">
      📊 <span data-lang="en">FOMC Dot Plot vs Market Pricing</span><span data-lang="zh">点阵图与市场定价曲线</span>
    </button>
    <button class="tab-btn" onclick="switchTab('diff')">
      🔍 <span data-lang="en">Statement Semantic Diff & Hawk/Dove Tone</span><span data-lang="zh">议息声明逐字对比与鹰鸽情绪</span>
    </button>
    <button class="tab-btn" onclick="switchTab('simulator')">
      ⚡ <span data-lang="en">Macro Shock Scenario Simulator</span><span data-lang="zh">宏观冲击情景模拟器</span>
    </button>
    <button class="tab-btn" onclick="switchTab('calendar')">
      📅 <span data-lang="en">Central Bank Decision Calendar</span><span data-lang="zh">央行决议日历与时间表</span>
    </button>
  </nav>

  <!-- TAB 1: Policy Corridors & Decisions -->
  <div id="tab-corridors" class="tab-pane active">
    <div class="section-head">
      <div>
        <h2>
          <span data-lang="en">G5 Central Bank Policy Rates & Operational Corridors</span>
          <span data-lang="zh">G5 全球央行基准利率与流动性走廊</span>
        </h2>
        <p>
          <span data-lang="en">Comprehensive breakdown of official targets, operational floor/ceiling facilities, balance sheet tightening, and real policy stance.</span>
          <span data-lang="zh">全面解析官方目标利率、上下限走廊工具（IORB/RRP/SLF/MLF）、量化紧缩 (QT) 规模与实际中性利率缺口。</span>
        </p>
      </div>
    </div>

    <!-- Central Bank Cards Grid -->
    <div class="cb-grid">

      <!-- 1. Federal Reserve -->
      <div class="cb-card">
        <div class="cb-card-header">
          <div class="cb-name-wrap">
            <span class="cb-flag">🇺🇸</span>
            <div>
              <div class="cb-name"><span data-lang="en">Federal Reserve</span><span data-lang="zh">美联储 (Fed / FOMC)</span></div>
              <div class="cb-inst">Federal Open Market Committee</div>
            </div>
          </div>
          <span class="cb-badge easing"><span data-lang="en">Easing (-75 bps)</span><span data-lang="zh">降息周期 (-75 bps)</span></span>
        </div>
        <div class="cb-card-body">
          <div class="cb-rate-hero">
            <div>
              <div class="cb-rate-val">4.75% – 5.00%</div>
              <div class="cb-rate-label"><span data-lang="en">Federal Funds Target Range</span><span data-lang="zh">联邦基金目标利率区间</span></div>
            </div>
            <div class="cb-rate-meta">
              <div class="cb-rate-delta neg">-25 bps</div>
              <div class="cb-rate-label"><span data-lang="en">Nov 7 Decision</span><span data-lang="zh">11月7日决议</span></div>
            </div>
          </div>

          <!-- Corridor Breakdown -->
          <div class="corridor-box">
            <div class="corridor-title">
              <span><span data-lang="en">Operational Corridor Structure</span><span data-lang="zh">准备金走廊结构</span></span>
              <span>EFFR: 4.83%</span>
            </div>
            <div class="corridor-tiers">
              <div class="corridor-node">
                <span class="node-label"><span data-lang="en">Upper Target</span><span data-lang="zh">上限</span></span>
                <strong>5.00%</strong>
              </div>
              <div class="corridor-node">
                <span class="node-label">IORB (Anchor)</span>
                <strong>4.90%</strong>
              </div>
              <div class="corridor-node current">
                <span class="node-label">EFFR</span>
                <strong>4.83%</strong>
              </div>
              <div class="corridor-node">
                <span class="node-label">ON RRP (Floor)</span>
                <strong>4.80%</strong>
              </div>
              <div class="corridor-node">
                <span class="node-label"><span data-lang="en">Lower Target</span><span data-lang="zh">下限</span></span>
                <strong>4.75%</strong>
              </div>
            </div>
          </div>

          <!-- Meeting Countdown -->
          <div class="meeting-box">
            <div class="meeting-date-wrap">
              <span class="meeting-label"><span data-lang="en">Next FOMC Meeting</span><span data-lang="zh">下一次 FOMC 决议</span></span>
              <span class="meeting-date">Dec 17–18, 2026 · SEP / Dot Plot</span>
            </div>
            <div class="countdown-chip" id="countdown-fed">--d --h --m</div>
          </div>

          <!-- Market Implied Probability -->
          <div class="market-pricing">
            <div class="prob-head">
              <span><span data-lang="en">Market Implied Next Action (FedWatch / OIS):</span><span data-lang="zh">市场定价概率 (FedWatch / OIS):</span></span>
              <strong>72.4% Cut 25bps | 27.6% Hold</strong>
            </div>
            <div class="prob-bar">
              <div class="prob-segment cut" style="width: 72.4%;" title="72.4% Probability of 25 bps cut"></div>
              <div class="prob-segment hold" style="width: 27.6%;" title="27.6% Probability of Hold"></div>
            </div>
          </div>

          <!-- QT & Stance Stats -->
          <div style="font-size:11.5px;color:var(--text-secondary);display:flex;justify-content:space-between;padding-top:4px;border-top:1px solid var(--border-subtle);">
            <span>Real Policy Rate: <strong style="color:var(--fg);font-family:var(--font-mono);">+0.76%</strong></span>
            <span>Net Liquidity: <strong style="color:var(--teal);font-family:var(--font-mono);">$5,741.5B</strong></span>
            <span>ON RRP: <strong style="color:var(--accent);font-family:var(--font-mono);">$4.38B</strong></span>
          </div>
        </div>
      </div>

      <!-- 2. European Central Bank -->
      <div class="cb-card">
        <div class="cb-card-header">
          <div class="cb-name-wrap">
            <span class="cb-flag">🇪🇺</span>
            <div>
              <div class="cb-name"><span data-lang="en">European Central Bank</span><span data-lang="zh">欧洲央行 (ECB)</span></div>
              <div class="cb-inst">Governing Council</div>
            </div>
          </div>
          <span class="cb-badge easing"><span data-lang="en">Easing (-75 bps)</span><span data-lang="zh">降息周期 (-75 bps)</span></span>
        </div>
        <div class="cb-card-body">
          <div class="cb-rate-hero">
            <div>
              <div class="cb-rate-val">3.25%</div>
              <div class="cb-rate-label"><span data-lang="en">Deposit Facility Rate (DFR)</span><span data-lang="zh">存款便利利率 (核心锚)</span></div>
            </div>
            <div class="cb-rate-meta">
              <div class="cb-rate-delta neg">-25 bps</div>
              <div class="cb-rate-label"><span data-lang="en">Oct 17 Decision</span><span data-lang="zh">10月17日决议</span></div>
            </div>
          </div>

          <!-- Corridor Breakdown -->
          <div class="corridor-box">
            <div class="corridor-title">
              <span><span data-lang="en">Operational Framework (Post-Sep 2024)</span><span data-lang="zh">新操作框架 (MRO-DFR缩窄至15bp)</span></span>
              <span>ESTR: 3.16%</span>
            </div>
            <div class="corridor-tiers">
              <div class="corridor-node">
                <span class="node-label">MLF (Ceiling)</span>
                <strong>3.65%</strong>
              </div>
              <div class="corridor-node">
                <span class="node-label">MRO (Refi)</span>
                <strong>3.40%</strong>
              </div>
              <div class="corridor-node current">
                <span class="node-label">DFR (Anchor)</span>
                <strong>3.25%</strong>
              </div>
              <div class="corridor-node">
                <span class="node-label">€STR Rate</span>
                <strong>3.16%</strong>
              </div>
            </div>
          </div>

          <!-- Meeting Countdown -->
          <div class="meeting-box">
            <div class="meeting-date-wrap">
              <span class="meeting-label"><span data-lang="en">Next Governing Council</span><span data-lang="zh">下一次管委会决议</span></span>
              <span class="meeting-date">Dec 11–12, 2026 · Staff Projections</span>
            </div>
            <div class="countdown-chip" id="countdown-ecb">--d --h --m</div>
          </div>

          <!-- Market Implied Probability -->
          <div class="market-pricing">
            <div class="prob-head">
              <span><span data-lang="en">Market Implied Next Action (OIS Forward):</span><span data-lang="zh">市场定价概率 (OIS 远期):</span></span>
              <strong>85.0% Cut 25bps | 15.0% Hold</strong>
            </div>
            <div class="prob-bar">
              <div class="prob-segment cut" style="width: 85%;" title="85% Probability of 25 bps cut"></div>
              <div class="prob-segment hold" style="width: 15%;" title="15% Probability of Hold"></div>
            </div>
          </div>

          <!-- Balance Sheet & Stance Stats -->
          <div style="font-size:11.5px;color:var(--text-secondary);display:flex;justify-content:space-between;padding-top:4px;border-top:1px solid var(--border-subtle);">
            <span>Real Policy Rate: <strong style="color:var(--fg);font-family:var(--font-mono);">+0.50%</strong></span>
            <span>Total Assets: <strong style="color:var(--teal);font-family:var(--font-mono);">€5,935.0B</strong></span>
            <span>PEPP Runoff: <strong style="color:var(--slate);font-family:var(--font-mono);">-€7.5B/mo</strong></span>
          </div>
        </div>
      </div>

      <!-- 3. People's Bank of China -->
      <div class="cb-card">
        <div class="cb-card-header">
          <div class="cb-name-wrap">
            <span class="cb-flag">🇨🇳</span>
            <div>
              <div class="cb-name"><span data-lang="en">People's Bank of China</span><span data-lang="zh">中国人民银行 (PBOC)</span></div>
              <div class="cb-inst">Monetary Policy Committee</div>
            </div>
          </div>
          <span class="cb-badge easing"><span data-lang="en">Counter-Cyclical Easing</span><span data-lang="zh">逆周期大幅宽松</span></span>
        </div>
        <div class="cb-card-body">
          <div class="cb-rate-hero">
            <div>
              <div class="cb-rate-val">1.50%</div>
              <div class="cb-rate-label"><span data-lang="en">7-Day Reverse Repo (Core Anchor)</span><span data-lang="zh">7天逆回购利率 (基准政策利率)</span></div>
            </div>
            <div class="cb-rate-meta">
              <div class="cb-rate-delta neg">-20 bps</div>
              <div class="cb-rate-label"><span data-lang="en">Sep Package</span><span data-lang="zh">一揽子宽松政策</span></div>
            </div>
          </div>

          <!-- Corridor Breakdown -->
          <div class="corridor-box">
            <div class="corridor-title">
              <span><span data-lang="en">Multi-Tier Transmission Matrix</span><span data-lang="zh">多层次利率传导矩阵</span></span>
              <span>DR007: 1.55%</span>
            </div>
            <div class="corridor-tiers">
              <div class="corridor-node">
                <span class="node-label">5Y LPR (Mortgage)</span>
                <strong>3.60%</strong>
              </div>
              <div class="corridor-node">
                <span class="node-label">1Y LPR (Loan)</span>
                <strong>3.10%</strong>
              </div>
              <div class="corridor-node">
                <span class="node-label">1Y MLF</span>
                <strong>2.00%</strong>
              </div>
              <div class="corridor-node current">
                <span class="node-label">7D OMO</span>
                <strong>1.50%</strong>
              </div>
            </div>
          </div>

          <!-- Meeting Countdown -->
          <div class="meeting-box">
            <div class="meeting-date-wrap">
              <span class="meeting-label"><span data-lang="en">Next LPR / MLF Fixings</span><span data-lang="zh">下一次 LPR 报价与 MLF 续做</span></span>
              <span class="meeting-date">Nov 20 & Dec 20, 2026 · Monthly Fixing</span>
            </div>
            <div class="countdown-chip" id="countdown-pboc">--d --h --m</div>
          </div>

          <!-- Liquidity Injections -->
          <div class="market-pricing">
            <div class="prob-head">
              <span><span data-lang="en">Structural Policy Toolkit:</span><span data-lang="zh">结构性货币政策工具箱:</span></span>
              <strong>RRR: 6.60% (-50bp) | CGB Trading Active</strong>
            </div>
            <div class="prob-bar">
              <div class="prob-segment cut" style="width: 100%;" title="Accommodative Liquidity Bias"></div>
            </div>
          </div>

          <!-- Balance Sheet & Stance Stats -->
          <div style="font-size:11.5px;color:var(--text-secondary);display:flex;justify-content:space-between;padding-top:4px;border-top:1px solid var(--border-subtle);">
            <span>Real Policy Rate: <strong style="color:var(--fg);font-family:var(--font-mono);">+2.10%</strong></span>
            <span>Total Assets: <strong style="color:var(--teal);font-family:var(--font-mono);">¥49.86T</strong></span>
            <span>Base Money: <strong style="color:var(--slate);font-family:var(--font-mono);">¥40.18T</strong></span>
          </div>
        </div>
      </div>

      <!-- 4. Bank of Japan -->
      <div class="cb-card">
        <div class="cb-card-header">
          <div class="cb-name-wrap">
            <span class="cb-flag">🇯🇵</span>
            <div>
              <div class="cb-name"><span data-lang="en">Bank of Japan</span><span data-lang="zh">日本央行 (BoJ)</span></div>
              <div class="cb-inst">Policy Board</div>
            </div>
          </div>
          <span class="cb-badge hiking"><span data-lang="en">Normalizing (+35 bps)</span><span data-lang="zh">政策正常化 (+35 bps)</span></span>
        </div>
        <div class="cb-card-body">
          <div class="cb-rate-hero">
            <div>
              <div class="cb-rate-val">0.25%</div>
              <div class="cb-rate-label"><span data-lang="en">Uncollateralized Overnight Call Target</span><span data-lang="zh">无担保隔夜拆借利率目标</span></div>
            </div>
            <div class="cb-rate-meta">
              <div class="cb-rate-delta pos">+15 bps</div>
              <div class="cb-rate-label"><span data-lang="en">July 31 Hike</span><span data-lang="zh">7月31日加息</span></div>
            </div>
          </div>

          <!-- Corridor Breakdown -->
          <div class="corridor-box">
            <div class="corridor-title">
              <span><span data-lang="en">Post-NIRP / Post-YCC Framework</span><span data-lang="zh">退出负利率与收益率曲线控制后框架</span></span>
              <span>TONA: 0.227%</span>
            </div>
            <div class="corridor-tiers">
              <div class="corridor-node">
                <span class="node-label">Lending Facility</span>
                <strong>0.50%</strong>
              </div>
              <div class="corridor-node current">
                <span class="node-label">Policy Call Rate</span>
                <strong>0.25%</strong>
              </div>
              <div class="corridor-node">
                <span class="node-label">Comp. Deposit</span>
                <strong>0.25%</strong>
              </div>
              <div class="corridor-node">
                <span class="node-label">10Y JGB Ref</span>
                <strong>~0.95%</strong>
              </div>
            </div>
          </div>

          <!-- Meeting Countdown -->
          <div class="meeting-box">
            <div class="meeting-date-wrap">
              <span class="meeting-label"><span data-lang="en">Next BoJ Meeting</span><span data-lang="zh">下一次日央行货币政策决议</span></span>
              <span class="meeting-date">Dec 18–19, 2026 · Quarterly Outlook</span>
            </div>
            <div class="countdown-chip" id="countdown-boj">--d --h --m</div>
          </div>

          <!-- Market Implied Probability -->
          <div class="market-pricing">
            <div class="prob-head">
              <span><span data-lang="en">Market Pricing for +25bps Hike:</span><span data-lang="zh">加息25基点概率定价:</span></span>
              <strong>54.0% Hike to 0.50% | 46.0% Hold</strong>
            </div>
            <div class="prob-bar">
              <div class="prob-segment hike" style="width: 54%;" title="54% Probability of +25 bps hike"></div>
              <div class="prob-segment hold" style="width: 46%;" title="46% Probability of Hold"></div>
            </div>
          </div>

          <!-- Balance Sheet & Stance Stats -->
          <div style="font-size:11.5px;color:var(--text-secondary);display:flex;justify-content:space-between;padding-top:4px;border-top:1px solid var(--border-subtle);">
            <span>Real Policy Rate: <strong style="color:var(--fg);font-family:var(--font-mono);">-2.25%</strong></span>
            <span>Total Assets: <strong style="color:var(--teal);font-family:var(--font-mono);">¥625.0T</strong></span>
            <span>JGB Taper: <strong style="color:var(--slate);font-family:var(--font-mono);">To ¥3T/mo</strong></span>
          </div>
        </div>
      </div>

      <!-- 5. Bank of England -->
      <div class="cb-card">
        <div class="cb-card-header">
          <div class="cb-name-wrap">
            <span class="cb-flag">🇬🇧</span>
            <div>
              <div class="cb-name"><span data-lang="en">Bank of England</span><span data-lang="zh">英格兰银行 (BoE)</span></div>
              <div class="cb-inst">Monetary Policy Committee (MPC)</div>
            </div>
          </div>
          <span class="cb-badge easing"><span data-lang="en">Gradual Easing (-50 bps)</span><span data-lang="zh">审慎降息 (-50 bps)</span></span>
        </div>
        <div class="cb-card-body">
          <div class="cb-rate-hero">
            <div>
              <div class="cb-rate-val">4.75%</div>
              <div class="cb-rate-label"><span data-lang="en">Official Bank Rate</span><span data-lang="zh">官方基准利率 (Bank Rate)</span></div>
            </div>
            <div class="cb-rate-meta">
              <div class="cb-rate-delta neg">-25 bps</div>
              <div class="cb-rate-label"><span data-lang="en">Nov 7 (8-1 Vote)</span><span data-lang="zh">11月7日 (8-1 票决)</span></div>
            </div>
          </div>

          <!-- Corridor Breakdown -->
          <div class="corridor-box">
            <div class="corridor-title">
              <span><span data-lang="en">Sterling Monetary Framework (SMF)</span><span data-lang="zh">英镑货币框架 (SMF)</span></span>
              <span>SONIA: 4.70%</span>
            </div>
            <div class="corridor-tiers">
              <div class="corridor-node">
                <span class="node-label">Operational Lending</span>
                <strong>5.00%</strong>
              </div>
              <div class="corridor-node current">
                <span class="node-label">Bank Rate</span>
                <strong>4.75%</strong>
              </div>
              <div class="corridor-node">
                <span class="node-label">Repo Facility</span>
                <strong>4.75%</strong>
              </div>
              <div class="corridor-node">
                <span class="node-label">SONIA Benchmark</span>
                <strong>4.70%</strong>
              </div>
            </div>
          </div>

          <!-- Meeting Countdown -->
          <div class="meeting-box">
            <div class="meeting-date-wrap">
              <span class="meeting-label"><span data-lang="en">Next MPC Decision</span><span data-lang="zh">下一次 MPC 决议</span></span>
              <span class="meeting-date">Dec 18, 2026 · Minutes & MPR</span>
            </div>
            <div class="countdown-chip" id="countdown-boe">--d --h --m</div>
          </div>

          <!-- Market Implied Probability -->
          <div class="market-pricing">
            <div class="prob-head">
              <span><span data-lang="en">Market Pricing for Dec Action:</span><span data-lang="zh">12月决议市场预期:</span></span>
              <strong>68.0% Hold at 4.75% | 32.0% Cut 25bps</strong>
            </div>
            <div class="prob-bar">
              <div class="prob-segment hold" style="width: 68%;" title="68% Probability of Hold"></div>
              <div class="prob-segment cut" style="width: 32%;" title="32% Probability of Cut"></div>
            </div>
          </div>

          <!-- QT & Stance Stats -->
          <div style="font-size:11.5px;color:var(--text-secondary);display:flex;justify-content:space-between;padding-top:4px;border-top:1px solid var(--border-subtle);">
            <span>Real Policy Rate: <strong style="color:var(--fg);font-family:var(--font-mono);">+3.05%</strong></span>
            <span>Annual QT Pace: <strong style="color:var(--teal);font-family:var(--font-mono);">£100B/yr</strong></span>
            <span>Vote Split: <strong style="color:var(--slate);font-family:var(--font-mono);">8-1 (Mann Hold)</strong></span>
          </div>
        </div>
      </div>

    </div>

    <!-- Supplementary Central Bank Peer Matrix -->
    <div class="section-head">
      <div>
        <h2>
          <span data-lang="en">Global Developed & Emerging Market Peer Stance Matrix</span>
          <span data-lang="zh">全球主要发达与新兴市场央行矩阵</span>
        </h2>
        <p>
          <span data-lang="en">Cross-country real interest rates, Taylor rule policy gaps, and monetary stance classifications.</span>
          <span data-lang="zh">跨国实际利率、泰勒规则政策偏离度与货币政策倾向全景对照。</span>
        </p>
      </div>
    </div>

    <div class="peer-table-wrap">
      <table class="peer-table">
        <thead>
          <tr>
            <th><span data-lang="en">Economy & Central Bank</span><span data-lang="zh">经济体与中央银行</span></th>
            <th><span data-lang="en">Key Policy Rate</span><span data-lang="zh">基准政策利率</span></th>
            <th><span data-lang="en">Latest Headline CPI</span><span data-lang="zh">最新通胀率</span></th>
            <th><span data-lang="en">Real Policy Rate</span><span data-lang="zh">实际政策利率</span></th>
            <th><span data-lang="en">Taylor Rule Gap</span><span data-lang="zh">泰勒规则缺口</span></th>
            <th><span data-lang="en">Policy Stance Classification</span><span data-lang="zh">货币政策立场评估</span></th>
            <th><span data-lang="en">Last Decision</span><span data-lang="zh">最新决议</span></th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td><strong>🇨🇭 Switzerland (SNB)</strong> · Swiss National Bank</td>
            <td><strong style="font-family:var(--font-mono);">1.00%</strong> (SNB Policy Rate)</td>
            <td>0.60%</td>
            <td style="color:var(--good);font-weight:700;">+0.40%</td>
            <td>-0.50%</td>
            <td><span class="cycle-badge easing"><span data-lang="en">Accommodative</span><span data-lang="zh">适度宽松</span></span></td>
            <td>-25 bps (Sep 2024)</td>
          </tr>
          <tr>
            <td><strong>🇨🇦 Canada (BoC)</strong> · Bank of Canada</td>
            <td><strong style="font-family:var(--font-mono);">3.75%</strong> (Overnight Target)</td>
            <td>1.60%</td>
            <td style="color:var(--good);font-weight:700;">+2.15%</td>
            <td>-0.20%</td>
            <td><span class="cycle-badge easing"><span data-lang="en">Accelerated Cut (-50bp)</span><span data-lang="zh">加速降息 (-50bp)</span></span></td>
            <td>-50 bps (Oct 2024)</td>
          </tr>
          <tr>
            <td><strong>🇦🇺 Australia (RBA)</strong> · Reserve Bank of Australia</td>
            <td><strong style="font-family:var(--font-mono);">4.35%</strong> (Cash Rate Target)</td>
            <td>2.80%</td>
            <td style="color:var(--good);font-weight:700;">+1.55%</td>
            <td>+0.45%</td>
            <td><span class="cycle-badge holding"><span data-lang="en">Prolonged Pause</span><span data-lang="zh">维持高位观望</span></span></td>
            <td>Hold (Nov 2024)</td>
          </tr>
          <tr>
            <td><strong>🇿🇦 South Africa (SARB)</strong> · Reserve Bank</td>
            <td><strong style="font-family:var(--font-mono);">8.00%</strong> (Repo Rate)</td>
            <td>3.80%</td>
            <td style="color:var(--good);font-weight:700;">+4.20%</td>
            <td>+1.10%</td>
            <td><span class="cycle-badge easing"><span data-lang="en">Cautious Easing</span><span data-lang="zh">开启降息周期</span></span></td>
            <td>-25 bps (Sep 2024)</td>
          </tr>
          <tr>
            <td><strong>🇹🇷 Turkey (TCMB)</strong> · Central Bank of Republic of Turkey</td>
            <td><strong style="font-family:var(--font-mono);">50.00%</strong> (1W Repo Rate)</td>
            <td>48.58%</td>
            <td style="color:var(--good);font-weight:700;">+1.42%</td>
            <td>+6.80%</td>
            <td><span class="cycle-badge hiking"><span data-lang="en">Ultra Restrictive</span><span data-lang="zh">强力抗通胀限制</span></span></td>
            <td>Hold (Oct 2024)</td>
          </tr>
          <tr>
            <td><strong>🇵🇱 Poland (NBP)</strong> · Narodowy Bank Polski</td>
            <td><strong style="font-family:var(--font-mono);">3.75%</strong> (Reference Rate)</td>
            <td>5.00%</td>
            <td style="color:var(--bad);font-weight:700;">-1.25%</td>
            <td>-0.80%</td>
            <td><span class="cycle-badge holding"><span data-lang="en">Hawkish Hold</span><span data-lang="zh">鹰派按兵不动</span></span></td>
            <td>Hold (Nov 2024)</td>
          </tr>
          <tr>
            <td><strong>🇨🇿 Czechia (CNB)</strong> · Czech National Bank</td>
            <td><strong style="font-family:var(--font-mono);">3.50%</strong> (2W Repo Rate)</td>
            <td>2.80%</td>
            <td style="color:var(--good);font-weight:700;">+0.70%</td>
            <td>-0.10%</td>
            <td><span class="cycle-badge easing"><span data-lang="en">Nearing Neutral</span><span data-lang="zh">接近中性利率</span></span></td>
            <td>-25 bps (Nov 2024)</td>
          </tr>
          <tr>
            <td><strong>🇭🇺 Hungary (MNB)</strong> · Magyar Nemzeti Bank</td>
            <td><strong style="font-family:var(--font-mono);">6.25%</strong> (Base Rate)</td>
            <td>3.20%</td>
            <td style="color:var(--good);font-weight:700;">+3.05%</td>
            <td>+1.40%</td>
            <td><span class="cycle-badge holding"><span data-lang="en">Pause on FX Risk</span><span data-lang="zh">因汇率压力暂停降息</span></span></td>
            <td>Hold (Oct 2024)</td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>

  <!-- TAB 2: FOMC Dot Plot vs Market Pricing -->
  <div id="tab-dotplot" class="tab-pane">
    <div class="section-head">
      <div>
        <h2>
          <span data-lang="en">FOMC Dot Plot Projections vs. Market Implied Forward Curve</span>
          <span data-lang="zh">美联储 FOMC 利率点阵图与市场定价曲线对比</span>
        </h2>
        <p>
          <span data-lang="en">Tracking the distribution of 19 committee participants' appropriate policy rate paths against SOFR/Fed Funds futures pricing.</span>
          <span data-lang="zh">深度对比 19 位美联储官员在经济预测摘要 (SEP) 中提交的预期点阵与 SOFR / 联邦基金期货隐含的市场降息路径。</span>
        </p>
      </div>
      <div>
        <button class="topbar-btn" onclick="relayoutDotplot()">🔄 <span data-lang="en">Reset View</span><span data-lang="zh">重置图表</span></button>
      </div>
    </div>

    <div class="dotplot-wrap">
      <div class="dotplot-meta">
        <div>
          <span style="font-size:12px;color:var(--text-secondary);"><span data-lang="en">Projection Source:</span><span data-lang="zh">预测来源：</span></span>
          <strong style="font-size:13px;color:var(--fg);">Federal Reserve September 2024 SEP</strong>
        </div>
        <div class="divergence-callout">
          <strong><span data-lang="en">Key Policy Divergence:</span><span data-lang="zh">核心政策分歧点：</span></strong>
          <span data-lang="en">Market forward pricing for end-2025 (~3.70%) sits <strong>~32 bps above</strong> the Fed median dot (3.375%), and market terminal pricing (~3.60%) implies a higher neutral rate ($r^*$) and positive term premium (+72.5 bps above Fed long-run 2.875%).</span>
          <span data-lang="zh">市场远期定价对 2025 年末水平 (~3.70%) 较美联储中位数 (3.375%) <strong>高出约 32 个基点</strong>，且市场定价的长期中性终点 (~3.60%) 明显高于官员中性利率预期 (2.875%)，反映了市场对于财政扩张与通胀粘性带来的期限溢价溢价定价。</span>
        </div>
      </div>

      <!-- Plotly Chart Canvas -->
      <div id="dotplot-chart" style="width:100%;height:520px;"></div>
    </div>
  </div>

  <!-- TAB 3: Statement Semantic Diff & Hawk/Dove Tone -->
  <div id="tab-diff" class="tab-pane">
    <div class="section-head">
      <div>
        <h2>
          <span data-lang="en">Central Bank Statement Semantic Diff & Hawk/Dove Tone Viewer</span>
          <span data-lang="zh">央行议息声明逐字语义 Diff 与鹰鸽情绪打分</span>
        </h2>
        <p>
          <span data-lang="en">Word-by-word visual diff between consecutive meeting statements with quantified sentiment scoring and keyword annotations.</span>
          <span data-lang="zh">两期决议声明文本逐字对比：以醒目绿底标示新增词句，红底删除线标示删除词句，并实时提炼鹰鸽倾向转变。</span>
        </p>
      </div>
    </div>

    <div class="diff-container">
      <!-- Toolbar -->
      <div class="diff-toolbar">
        <div class="diff-select-group">
          <label style="font-size:11.5px;font-weight:700;color:var(--text-secondary);"><span data-lang="en">Central Bank Statement:</span><span data-lang="zh">选择议息声明：</span></label>
          <select class="diff-select" id="diff-cb-selector" onchange="renderDiffStatement()">
            <option value="fomc_nov_sep">🇺🇸 Federal Reserve (FOMC): Nov 2024 vs. Sep 2024</option>
            <option value="ecb_oct_sep">🇪🇺 European Central Bank (ECB): Oct 2024 vs. Sep 2024</option>
            <option value="boe_nov_sep">🇬🇧 Bank of England (BoE): Nov 2024 vs. Sep 2024</option>
          </select>
        </div>
        <div class="diff-select-group">
          <button class="diff-mode-btn active" id="btn-mode-inline" onclick="setDiffMode('inline')"><span data-lang="en">Unified Inline Diff</span><span data-lang="zh">单栏逐字对比</span></button>
          <button class="diff-mode-btn" id="btn-mode-keywords" onclick="toggleKeywordHighlights()"><span data-lang="en">Hawk/Dove Tags</span><span data-lang="zh">标注鹰鸽关键词</span></button>
        </div>
      </div>

      <!-- Hawk Dove Bar -->
      <div class="diff-sentiment-bar">
        <div class="gauge-wrapper">
          <span class="gauge-label"><span data-lang="en">Net Tone Shift:</span><span data-lang="zh">净基调变动：</span></span>
          <div class="gauge-meter">
            <div class="gauge-center-line"></div>
            <div class="gauge-fill dove" id="gauge-bar" style="width: 24%;"></div>
          </div>
          <strong id="gauge-score" style="font-family:var(--font-mono);font-size:12px;color:var(--teal);">-24 (Dovish Shift)</strong>
        </div>
        <div class="diff-legend">
          <div class="legend-item"><span class="legend-box add"></span> <span data-lang="en">Added Language</span><span data-lang="zh">最新增补语句</span></div>
          <div class="legend-item"><span class="legend-box del"></span> <span data-lang="en">Deleted Language</span><span data-lang="zh">前次删除语句</span></div>
          <div class="legend-item"><span class="keyword-tag dove">DOVE</span> <span data-lang="en">Dovish Signal</span><span data-lang="zh">鸽派信号</span></div>
          <div class="legend-item"><span class="keyword-tag hawk">HAWK</span> <span data-lang="en">Hawkish Signal</span><span data-lang="zh">鹰派信号</span></div>
        </div>
      </div>

      <!-- Diff Text Content -->
      <div class="diff-body" id="diff-text-area">
        <!-- Rendered via JavaScript -->
      </div>
    </div>
  </div>

  <!-- TAB 4: Macro Shock Scenario Simulator -->
  <div id="tab-simulator" class="tab-pane">
    <div class="section-head">
      <div>
        <h2>
          <span data-lang="en">Institutional Macro Shock Scenario Simulator</span>
          <span data-lang="zh">宏观冲击情景模拟器 (Macro Shock Simulator)</span>
        </h2>
        <p>
          <span data-lang="en">Parametric stress-testing: calibrate oil prices, US 10Y yield curve shifts, and trade tariffs to observe global macro transmissions in real time.</span>
          <span data-lang="zh">参数化压力测试：滑动调节原油价格、美债长端收益率与关税冲击幅度，实时模拟全球通胀、利差与央行反应函数。</span>
        </p>
      </div>
    </div>

    <div class="simulator-grid">

      <!-- Left Column: Controls -->
      <div class="sim-controls">
        <div class="sim-preset-row">
          <span class="preset-label"><span data-lang="en">Curated Macro Scenarios</span><span data-lang="zh">经典宏观预设情景</span></span>
          <div class="preset-btn-group">
            <button class="preset-btn active" onclick="applyShockPreset('baseline')">🔄 <span data-lang="en">Neutral Baseline (Status Quo)</span><span data-lang="zh">中性基准 (当前状态)</span></button>
            <button class="preset-btn" onclick="applyShockPreset('stagflation')">🛢️ <span data-lang="en">1970s Oil Supply Crunch (+40% Oil)</span><span data-lang="zh">石油供给危机 (+40% 油价)</span></button>
            <button class="preset-btn" onclick="applyShockPreset('tariff')">🛡️ <span data-lang="en">Global Trade War (+15% Universal Tariff)</span><span data-lang="zh">全球贸易壁垒升温 (+15% 关税)</span></button>
            <button class="preset-btn" onclick="applyShockPreset('tantrum')">⚡ <span data-lang="en">Bond Market Tantrum (+100 bps 10Y Yield)</span><span data-lang="zh">全球债市抛售潮 (+100bp 美债)</span></button>
            <button class="preset-btn" onclick="applyShockPreset('goldilocks')">🕊️ <span data-lang="en">Goldilocks Soft Landing (-20% Oil, -50bp)</span><span data-lang="zh">完美软着陆与深度去通胀</span></button>
          </div>
        </div>

        <hr style="border:none;border-top:1px solid var(--border-subtle);">

        <!-- Slider 1: Brent Crude Oil -->
        <div class="slider-group">
          <div class="slider-head">
            <span class="slider-title">🛢️ <span data-lang="en">Brent Crude Oil Shock</span><span data-lang="zh">布伦特原油价格变动</span></span>
            <span class="slider-value" id="val-oil">+0% ($75.0/bbl)</span>
          </div>
          <input type="range" class="range-input" id="range-oil" min="-40" max="60" value="0" step="5" oninput="updateShockSim()">
          <div style="display:flex;justify-content:space-between;font-size:10.5px;color:var(--text-secondary);">
            <span>-40% ($45)</span>
            <span>Baseline $75</span>
            <span>+60% ($120)</span>
          </div>
        </div>

        <!-- Slider 2: US 10Y Yield -->
        <div class="slider-group">
          <div class="slider-head">
            <span class="slider-title">📈 <span data-lang="en">US 10Y Treasury Yield Shift</span><span data-lang="zh">美债10年期收益率偏离</span></span>
            <span class="slider-value" id="val-yield">+0 bps (4.30%)</span>
          </div>
          <input type="range" class="range-input" id="range-yield" min="-100" max="150" value="0" step="10" oninput="updateShockSim()">
          <div style="display:flex;justify-content:space-between;font-size:10.5px;color:var(--text-secondary);">
            <span>-100 bps</span>
            <span>Baseline (4.30%)</span>
            <span>+150 bps</span>
          </div>
        </div>

        <!-- Slider 3: Universal Tariff -->
        <div class="slider-group">
          <div class="slider-head">
            <span class="slider-title">🚢 <span data-lang="en">Effective Global Tariff Rate</span><span data-lang="zh">有效全面关税税率</span></span>
            <span class="slider-value" id="val-tariff">+0.0%</span>
          </div>
          <input type="range" class="range-input" id="range-tariff" min="0" max="25" value="0" step="2.5" oninput="updateShockSim()">
          <div style="display:flex;justify-content:space-between;font-size:10.5px;color:var(--text-secondary);">
            <span>0% (Status Quo)</span>
            <span>10% Baseline</span>
            <span>25% Peak War</span>
          </div>
        </div>
      </div>

      <!-- Right Column: Results & Transmission -->
      <div class="sim-results">

        <!-- 1. Inflation Transmission -->
        <div class="impact-matrix-card">
          <div class="matrix-title">
            <span>🔥 <span data-lang="en">Headline & Core Inflation Transmission (1-Year Horizon)</span><span data-lang="zh">通胀传导影响测算 (1年周期内弹性)</span></span>
          </div>
          <div class="impact-cards-grid">
            <div class="impact-stat">
              <span class="impact-label">🇺🇸 US Headline CPI Shift</span>
              <span class="impact-val" id="impact-us-cpi">+0.00%</span>
              <span class="impact-sub">Base 3.12% &rarr; <span id="new-us-cpi">3.12%</span></span>
            </div>
            <div class="impact-stat">
              <span class="impact-label">🇪🇺 Euro Area CPI Shift</span>
              <span class="impact-val" id="impact-ea-cpi">+0.00%</span>
              <span class="impact-sub">Base 2.00% &rarr; <span id="new-ea-cpi">2.00%</span></span>
            </div>
            <div class="impact-stat">
              <span class="impact-label">🇨🇳 China PPI Impact</span>
              <span class="impact-val" id="impact-cn-ppi">+0.00%</span>
              <span class="impact-sub">Base -2.80% &rarr; <span id="new-cn-ppi">-2.80%</span></span>
            </div>
            <div class="impact-stat">
              <span class="impact-label">🇬🇧 UK Headline CPI Shift</span>
              <span class="impact-val" id="impact-uk-cpi">+0.00%</span>
              <span class="impact-sub">Base 1.70% &rarr; <span id="new-uk-cpi">1.70%</span></span>
            </div>
          </div>
        </div>

        <!-- 2. Financial Conditions & Spreads -->
        <div class="impact-matrix-card">
          <div class="matrix-title">
            <span>🌐 <span data-lang="en">Financial Conditions, FX & Sovereign Spreads Transmission</span><span data-lang="zh">金融条件、汇率与主权利差传导</span></span>
          </div>
          <div class="impact-cards-grid">
            <div class="impact-stat">
              <span class="impact-label">💵 US Dollar Index (DXY)</span>
              <span class="impact-val" id="impact-dxy">+0.0%</span>
              <span class="impact-sub">Base 104.2 &rarr; <span id="new-dxy">104.2</span></span>
            </div>
            <div class="impact-stat">
              <span class="impact-label">🇮🇹 BTP-Bund Spread (10Y)</span>
              <span class="impact-val" id="impact-btp">+0 bps</span>
              <span class="impact-sub">Base 122 bps &rarr; <span id="new-btp">122 bps</span></span>
            </div>
            <div class="impact-stat">
              <span class="impact-label">🌍 EM Sovereign Spread (EMBI)</span>
              <span class="impact-val" id="impact-embi">+0 bps</span>
              <span class="impact-sub">Base 320 bps &rarr; <span id="new-embi">320 bps</span></span>
            </div>
            <div class="impact-stat">
              <span class="impact-label">📉 Global Trade Volume</span>
              <span class="impact-val" id="impact-trade">-0.0%</span>
              <span class="impact-sub">Tariff elasticity: -0.16x</span>
            </div>
          </div>
        </div>

        <!-- 3. Policy Reaction Functions -->
        <div class="impact-matrix-card">
          <div class="matrix-title">
            <span>🏛️ <span data-lang="en">Central Bank Reaction Function Outlook</span><span data-lang="zh">央行反应函数与政策倾向预判</span></span>
          </div>
          <div style="font-size:13px;line-height:1.6;color:var(--fg);display:flex;flex-direction:column;gap:10px;" id="reaction-container">
            <!-- Dynamic reactions -->
          </div>
        </div>

      </div>
    </div>
  </div>

  <!-- TAB 5: Central Bank Calendar -->
  <div id="tab-calendar" class="tab-pane">
    <div class="section-head">
      <div>
        <h2>
          <span data-lang="en">2026/2027 Global Central Bank Decision Calendar</span>
          <span data-lang="zh">2026/2027 全球主要央行决议日历</span>
        </h2>
        <p>
          <span data-lang="en">Consolidated schedule of rate decisions, monetary policy reports (MPR), and summary of economic projections (SEP).</span>
          <span data-lang="zh">汇集美联储 FOMC、欧央行管委会、英格兰银行 MPC、日央行 Policy Board 及中国央行 LPR/MLF 决议排期。</span>
        </p>
      </div>
    </div>

    <!-- Filter Buttons -->
    <div class="cal-filter-row">
      <button class="cal-btn active" onclick="filterCal('ALL')"><span data-lang="en">All Institutions</span><span data-lang="zh">全部央行</span></button>
      <button class="cal-btn" onclick="filterCal('FED')">🇺🇸 Fed (FOMC)</button>
      <button class="cal-btn" onclick="filterCal('ECB')">🇪🇺 ECB</button>
      <button class="cal-btn" onclick="filterCal('BOE')">🇬🇧 BoE (MPC)</button>
      <button class="cal-btn" onclick="filterCal('BOJ')">🇯🇵 BoJ</button>
      <button class="cal-btn" onclick="filterCal('PBOC')">🇨🇳 PBOC (人民银行)</button>
    </div>

    <div class="cal-table-wrap">
      <table class="cal-table">
        <thead>
          <tr>
            <th><span data-lang="en">Date</span><span data-lang="zh">决议日期</span></th>
            <th><span data-lang="en">Central Bank</span><span data-lang="zh">中央银行</span></th>
            <th><span data-lang="en">Event Description</span><span data-lang="zh">事件说明</span></th>
            <th><span data-lang="en">Type & Publications</span><span data-lang="zh">会议属性与发布文件</span></th>
            <th><span data-lang="en">Consensus Expectation</span><span data-lang="zh">市场主流预期</span></th>
          </tr>
        </thead>
        <tbody id="cal-table-body">
          <!-- Rendered via JS -->
        </tbody>
      </table>
    </div>
  </div>

  <!-- Footer -->
  <footer class="footer">
    <div>
      <strong>Macro Dashboard</strong> · Institutional Central Bank Policy Tracker
      <br>
      <span style="color:var(--text-secondary);">Grounded strictly in official central bank publications (Federal Reserve, ECB, BoE, BoJ, PBOC) and market-implied OIS forwards.</span>
    </div>
    <div style="display:flex;gap:16px;">
      <a href="index.html"><span data-lang="en">Dashboard Home</span><span data-lang="zh">看板首页</span></a>
      <a href="chart_studio.html"><span data-lang="en">Chart Studio</span><span data-lang="zh">图表工坊</span></a>
      <a href="my_dashboard.html"><span data-lang="en">My Dashboard</span><span data-lang="zh">自选看板</span></a>
      <a href="output/freshness_audit.json"><span data-lang="en">Freshness Audit</span><span data-lang="zh">数据审计</span></a>
    </div>
  </footer>

</div>

<script>
/* ==============================================================================
   1. Bilingual Language Support
   ============================================================================== */
let currentLang = localStorage.getItem('macro_dashboard_lang') || 'en';

function toggleLang() {{
  currentLang = currentLang === 'en' ? 'zh' : 'en';
  localStorage.setItem('macro_dashboard_lang', currentLang);
  applyLang();
}}

function applyLang() {{
  if (currentLang === 'zh') {{
    document.body.classList.add('lang-zh');
    document.getElementById('lang-btn').innerText = 'English';
  }} else {{
    document.body.classList.remove('lang-zh');
    document.getElementById('lang-btn').innerText = '中文';
  }}
  // Re-render components with language sensitive text
  renderCal();
  renderDiffStatement();
  updateShockSim();
}}

/* ==============================================================================
   2. Tab Switching Engine
   ============================================================================== */
function switchTab(tabId) {{
  document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
  document.querySelectorAll('.tab-pane').forEach(pane => pane.classList.remove('active'));

  event.currentTarget.classList.add('active');
  const targetPane = document.getElementById('tab-' + tabId);
  if (targetPane) targetPane.classList.add('active');

  if (tabId === 'dotplot') {{
    setTimeout(relayoutDotplot, 50);
  }}
}}

/* ==============================================================================
   3. Live Countdown Timers for Major Central Banks
   ============================================================================== */
const MEETING_DATES = {{
  fed: new Date('2026-12-18T19:00:00Z'),
  ecb: new Date('2026-12-12T13:15:00Z'),
  boe: new Date('2026-12-18T12:00:00Z'),
  boj: new Date('2026-12-19T03:30:00Z'),
  pboc: new Date('2026-11-20T01:15:00Z')
}};

function updateCountdowns() {{
  const now = new Date();
  for (const [key, targetDate] of Object.entries(MEETING_DATES)) {{
    const el = document.getElementById('countdown-' + key);
    if (!el) continue;
    const diff = targetDate - now;
    if (diff <= 0) {{
      el.innerText = currentLang === 'zh' ? '决议中' : 'Decision Live';
      continue;
    }}
    const days = Math.floor(diff / (1000 * 60 * 60 * 24));
    const hours = Math.floor((diff % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
    const mins = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60));
    el.innerText = `${{days}}d ${{hours}}h ${{mins}}m`;
  }}
}}
setInterval(updateCountdowns, 60000);
updateCountdowns();

/* ==============================================================================
   4. Interactive FOMC Dot Plot vs Market Pricing (Plotly)
   ============================================================================== */
// September 2024 SEP Dots (19 participants)
const DOT_DATA = [
  // 2024
  {{ year: '2024', rate: 4.375, count: 9 }},
  {{ year: '2024', rate: 4.625, count: 7 }},
  {{ year: '2024', rate: 4.875, count: 2 }},
  {{ year: '2024', rate: 5.125, count: 1 }},

  // 2025
  {{ year: '2025', rate: 2.875, count: 1 }},
  {{ year: '2025', rate: 3.125, count: 2 }},
  {{ year: '2025', rate: 3.375, count: 9 }},
  {{ year: '2025', rate: 3.625, count: 4 }},
  {{ year: '2025', rate: 3.875, count: 3 }},

  // 2026
  {{ year: '2026', rate: 2.375, count: 1 }},
  {{ year: '2026', rate: 2.625, count: 2 }},
  {{ year: '2026', rate: 2.875, count: 7 }},
  {{ year: '2026', rate: 3.125, count: 5 }},
  {{ year: '2026', rate: 3.375, count: 3 }},
  {{ year: '2026', rate: 3.625, count: 1 }},

  // 2027
  {{ year: '2027', rate: 2.625, count: 2 }},
  {{ year: '2027', rate: 2.875, count: 9 }},
  {{ year: '2027', rate: 3.125, count: 5 }},
  {{ year: '2027', rate: 3.375, count: 2 }},
  {{ year: '2027', rate: 3.625, count: 1 }},

  // Longer Run (Neutral r*)
  {{ year: 'Longer Run', rate: 2.375, count: 1 }},
  {{ year: 'Longer Run', rate: 2.500, count: 3 }},
  {{ year: 'Longer Run', rate: 2.625, count: 4 }},
  {{ year: 'Longer Run', rate: 2.875, count: 5 }},
  {{ year: 'Longer Run', rate: 3.000, count: 3 }},
  {{ year: 'Longer Run', rate: 3.250, count: 2 }},
  {{ year: 'Longer Run', rate: 3.750, count: 1 }}
];

// Expand dots with horizontal jitter
const jitterX = [];
const jitterY = [];
const hoverTexts = [];

const YEAR_INDEX = {{
  '2024': 0,
  '2025': 1,
  '2026': 2,
  '2027': 3,
  'Longer Run': 4
}};

DOT_DATA.forEach(group => {{
  const baseX = YEAR_INDEX[group.year];
  const count = group.count;
  for (let i = 0; i < count; i++) {{
    // Offset evenly centered around baseX
    const offset = count === 1 ? 0 : ((i - (count - 1) / 2) * 0.045);
    jitterX.push(baseX + offset);
    jitterY.push(group.rate);
    hoverTexts.push(`<b>Horizon:</b> ${{group.year}}<br><b>Rate:</b> ${{group.rate.toFixed(3)}}%<br><b>Participants:</b> ${{group.count}} dots`);
  }}
}});

// Median Line
const mediansX = [0, 1, 2, 3, 4];
const mediansY = [4.375, 3.375, 2.875, 2.875, 2.875];

// Market Implied SOFR Forward Curve
const marketX = [0, 1, 2, 3, 4];
const marketY = [4.45, 3.70, 3.65, 3.62, 3.60];

function initDotplot() {{
  const traceDots = {{
    x: jitterX,
    y: jitterY,
    mode: 'markers',
    type: 'scatter',
    name: 'FOMC Participants (Dots)',
    text: hoverTexts,
    hoverinfo: 'text',
    marker: {{
      size: 9,
      color: '#364b61',
      opacity: 0.85,
      line: {{ color: '#1a2733', width: 1 }}
    }}
  }};

  const traceMedian = {{
    x: mediansX,
    y: mediansY,
    mode: 'lines+markers',
    type: 'scatter',
    name: 'Fed Median Dot Path',
    line: {{ color: '#d97706', width: 3 }},
    marker: {{ symbol: 'diamond', size: 10, color: '#d97706' }}
  }};

  const traceMarket = {{
    x: marketX,
    y: marketY,
    mode: 'lines+markers',
    type: 'scatter',
    name: 'Market Implied Curve (SOFR/OIS)',
    line: {{ color: '#0d7680', width: 3, dash: 'dash' }},
    marker: {{ symbol: 'circle', size: 9, color: '#0d7680' }}
  }};

  const layout = {{
    margin: {{ l: 50, r: 30, t: 30, b: 50 }},
    paper_bgcolor: 'transparent',
    plot_bgcolor: '#fffdfa',
    showlegend: true,
    legend: {{
      orientation: 'h',
      x: 0.05,
      y: 1.08,
      font: {{ family: '-apple-system, sans-serif', size: 11 }}
    }},
    xaxis: {{
      tickvals: [0, 1, 2, 3, 4],
      ticktext: ['End 2024', 'End 2025', 'End 2026', 'End 2027', 'Longer Run (r*)'],
      gridcolor: '#f0ebe4',
      linecolor: '#e8e4df',
      tickfont: {{ family: '-apple-system, sans-serif', size: 12, color: '#12151a' }}
    }},
    yaxis: {{
      title: 'Target Policy Rate (%)',
      titlefont: {{ family: '-apple-system, sans-serif', size: 12 }},
      tickvals: [2.0, 2.5, 3.0, 3.5, 4.0, 4.5, 5.0, 5.5],
      ticksuffix: '%',
      gridcolor: '#f0ebe4',
      linecolor: '#e8e4df',
      range: [2.0, 5.5],
      tickfont: {{ family: 'ui-monospace, monospace', size: 11 }}
    }},
    annotations: [
      {{
        x: 1,
        y: 3.70,
        xref: 'x',
        yref: 'y',
        text: 'Market +32bp vs Fed',
        showarrow: true,
        arrowhead: 2,
        ax: 20,
        ay: -25,
        font: {{ size: 10.5, color: '#0d7680', family: 'ui-monospace, monospace' }},
        bgcolor: '#e6f4ea',
        bordercolor: '#0d7680',
        borderwidth: 1
      }},
      {{
        x: 4,
        y: 3.60,
        xref: 'x',
        yref: 'y',
        text: 'Terminal Divergence: +72.5bp',
        showarrow: true,
        arrowhead: 2,
        ax: -40,
        ay: -25,
        font: {{ size: 10.5, color: '#990f3d', family: 'ui-monospace, monospace' }},
        bgcolor: '#fce8e6',
        bordercolor: '#990f3d',
        borderwidth: 1
      }}
    ]
  }};

  const config = {{ responsive: true, displayModeBar: false }};
  Plotly.newPlot('dotplot-chart', [traceDots, traceMedian, traceMarket], layout, config);
}}

function relayoutDotplot() {{
  const chartEl = document.getElementById('dotplot-chart');
  if (chartEl && chartEl.data) {{
    Plotly.Plots.resize(chartEl);
  }} else {{
    initDotplot();
  }}
}}

/* ==============================================================================
   5. Word-by-Word Statement Semantic Diff & Hawk/Dove Engine
   ============================================================================== */
const STATEMENTS = {{
  fomc_nov_sep: {{
    cb: 'Federal Reserve (FOMC)',
    period: 'November 7, 2024 vs. September 18, 2024',
    tone_score: -24,
    tone_label: 'Dovish Shift (-24)',
    hawk_count: 5,
    dove_count: 9,
    paragraphs: [
      `Recent indicators suggest that economic activity has continued to expand at a <span class="keyword-tag hawk">solid pace</span>. <del class="diff-del">Job gains have slowed</del><ins class="diff-add">Since earlier in the year, labor market conditions have generally eased</ins>, and the unemployment rate has moved up but remains low. Inflation has made <del class="diff-del">further </del>progress toward the Committee's 2 percent objective but <span class="keyword-tag hawk">remains somewhat elevated</span>.`,

      `The Committee seeks to achieve maximum employment and inflation at the rate of 2 percent over the longer run. <del class="diff-del">The Committee has gained greater confidence that inflation is moving sustainably toward 2 percent, and judges</del><ins class="diff-add">The Committee judges</ins> that the risks to achieving its employment and inflation goals are <span class="keyword-tag dove">roughly in balance</span>. The economic outlook is uncertain, and the Committee is attentive to the risks to both sides of its dual mandate.`,

      `<del class="diff-del">In light of the progress on inflation and the balance of risks</del><ins class="diff-add">In support of its goals</ins>, the Committee decided to lower the target range for the federal funds rate by <del class="diff-del">1/2 percentage point to 4-3/4 to 5 percent</del><ins class="diff-add">1/4 percentage point to 4-1/2 to 4-3/4 percent</ins>. In considering additional adjustments to the target range for the federal funds rate, the Committee will carefully assess incoming data, the evolving outlook, and the balance of risks. The Committee will continue reducing its holdings of Treasury securities and agency debt and agency mortgage-backed securities. The Committee is strongly committed to supporting maximum employment and returning inflation to its 2 percent objective.`,

      `Voting for the monetary policy action were Jerome H. Powell, Chair; John C. Williams, Vice Chair; Thomas I. Barkin; Michael S. Barr; Raphael W. Bostic; <ins class="diff-add">Michelle W. Bowman; </ins>Lisa D. Cook; Mary C. Daly; Beth M. Hammack; Philip N. Jefferson; Alberto G. Musalem; and Christopher J. Waller. <del class="diff-del">Voting against this action was Michelle W. Bowman, who preferred to lower the target range for the federal funds rate by 1/4 percentage point at this meeting.</del><ins class="diff-add">(Unanimous 12-0 vote, no dissents).</ins>`
    ]
  }},

  ecb_oct_sep: {{
    cb: 'European Central Bank (ECB)',
    period: 'October 17, 2024 vs. September 12, 2024',
    tone_score: -35,
    tone_label: 'Substantial Dovish Pivot (-35)',
    hawk_count: 4,
    dove_count: 11,
    paragraphs: [
      `The Governing Council today decided to lower the <del class="diff-del">deposit facility rate – the rate through which the Governing Council steers the monetary policy stance – by 25 basis points</del><ins class="diff-add">three key ECB interest rates by 25 basis points</ins>. In particular, the decision to lower the deposit facility rate <del class="diff-del">– based on its updated assessment of the inflation outlook, the dynamics of underlying inflation and the strength of monetary policy transmission, it is now appropriate to take another step in moderating the degree of monetary policy restriction</del><ins class="diff-add">is based on its updated assessment of the inflation outlook, the dynamics of underlying inflation and the strength of monetary policy transmission. The incoming information on inflation shows that the <span class="keyword-tag dove">disinflationary process</span> is well on track</ins>.`,

      `<ins class="diff-add">The inflation outlook is also affected by recent <span class="keyword-tag dove">downside surprises</span> in indicators of economic activity. Meanwhile, financing conditions remain <span class="keyword-tag hawk">restrictive</span>.</ins>`,

      `Domestic inflation remains high, as wages are still rising at an <span class="keyword-tag hawk">elevated pace</span>. At the same time, labour cost pressures are expected to continue <span class="keyword-tag dove">easing gradually</span>, with profits partially buffering the impact of higher wages on inflation.`,

      `The Governing Council is determined to ensure that inflation returns to its 2% medium-term target in a timely manner. It will keep policy rates sufficiently restrictive for as long as necessary to achieve this aim. The Governing Council will continue to follow a data-dependent and meeting-by-meeting approach. <ins class="diff-add">The Governing Council is <span class="keyword-tag dove">not pre-committing</span> to a particular rate path.</ins>`
    ]
  }},

  boe_nov_sep: {{
    cb: 'Bank of England (BoE)',
    period: 'November 7, 2024 vs. September 19, 2024',
    tone_score: -18,
    tone_label: 'Cautious Dovish Cut (-18)',
    hawk_count: 6,
    dove_count: 8,
    paragraphs: [
      `The Bank of England's Monetary Policy Committee (MPC) voted by a majority of <del class="diff-del">8–1 to maintain Bank Rate at 5%</del><ins class="diff-add">8–1 to reduce Bank Rate by 0.25 percentage points, to 4.75%</ins>. One member preferred to <del class="diff-del">reduce Bank Rate by 0.25 percentage points, to 4.75%</del><ins class="diff-add">maintain Bank Rate at 5%</ins>.`,

      `There has been continued progress on disinflation, particularly as previous external shocks have abated, though remaining domestic inflationary pressures are resolving more slowly. CPI inflation fell to 1.7% in September but is expected to increase to around 2½% by the end of the year as energy prices fall out of the annual comparison.`,

      `<ins class="diff-add">Based on the evolving evidence, a <span class="keyword-tag dove">gradual approach</span> to removing policy restraint remains appropriate. Monetary policy will need to continue to remain <span class="keyword-tag hawk">restrictive</span> for sufficiently long until the risks to inflation returning sustainably to the 2% target in the medium term have dissipated further.</ins>`,

      `<ins class="diff-add">The MPC noted the measures announced in the UK Autumn Budget, which are provisionally estimated to boost the level of GDP by around ¾% at their peak, whilst pushing up CPI inflation by just under ½ of a percentage point.</ins>`
    ]
  }}
}};

let showKeywords = true;

function renderDiffStatement() {{
  const key = document.getElementById('diff-cb-selector').value;
  const data = STATEMENTS[key] || STATEMENTS.fomc_nov_sep;

  // Update Sentiment Gauge
  const gaugeFill = document.getElementById('gauge-bar');
  const gaugeScore = document.getElementById('gauge-score');
  const absScore = Math.abs(data.tone_score);
  gaugeFill.style.width = absScore + '%';
  if (data.tone_score < 0) {{
    gaugeFill.className = 'gauge-fill dove';
    gaugeScore.style.color = 'var(--teal)';
    gaugeScore.innerText = `${{data.tone_score}} (${{currentLang === 'zh' ? '鸽派转向' : 'Dovish Shift'}})`;
  }} else {{
    gaugeFill.className = 'gauge-fill hawk';
    gaugeScore.style.color = 'var(--accent)';
    gaugeScore.innerText = `+${{data.tone_score}} (${{currentLang === 'zh' ? '鹰派强化' : 'Hawkish Shift'}})`;
  }}

  // Render paragraphs
  const container = document.getElementById('diff-text-area');
  container.innerHTML = data.paragraphs.map(p => `<p class="diff-paragraph">${{p}}</p>`).join('');

  if (!showKeywords) {{
    container.querySelectorAll('.keyword-tag').forEach(tag => tag.style.display = 'none');
  }}
}}

function toggleKeywordHighlights() {{
  showKeywords = !showKeywords;
  const btn = document.getElementById('btn-mode-keywords');
  if (showKeywords) {{
    btn.classList.add('active');
  }} else {{
    btn.classList.remove('active');
  }}
  renderDiffStatement();
}}

function setDiffMode(mode) {{
  // Simple toggle
  renderDiffStatement();
}}

/* ==============================================================================
   6. Macro Shock Scenario Simulator Engine
   ============================================================================== */
const SHOCK_PRESETS = {{
  baseline: {{ oil: 0, yield: 0, tariff: 0 }},
  stagflation: {{ oil: 40, yield: 50, tariff: 5 }},
  tariff: {{ oil: -10, yield: 30, tariff: 15 }},
  tantrum: {{ oil: 10, yield: 100, tariff: 0 }},
  goldilocks: {{ oil: -20, yield: -50, tariff: 0 }}
}};

function applyShockPreset(presetKey) {{
  const p = SHOCK_PRESETS[presetKey];
  if (!p) return;
  document.getElementById('range-oil').value = p.oil;
  document.getElementById('range-yield').value = p.yield;
  document.getElementById('range-tariff').value = p.tariff;

  // Active state
  document.querySelectorAll('.preset-btn').forEach(b => b.classList.remove('active'));
  if (event && event.currentTarget) event.currentTarget.classList.add('active');

  updateShockSim();
}}

function updateShockSim() {{
  const dOil = parseFloat(document.getElementById('range-oil').value);
  const dYield = parseFloat(document.getElementById('range-yield').value);
  const dTariff = parseFloat(document.getElementById('range-tariff').value);

  // Update slider text displays
  const brentPrice = 75.0 * (1 + dOil / 100);
  document.getElementById('val-oil').innerText = `${{dOil >= 0 ? '+' : ''}}${{dOil}}% ($${{brentPrice.toFixed(1)}}/bbl)`;
  
  const yield10Y = 4.30 + (dYield / 100);
  document.getElementById('val-yield').innerText = `${{dYield >= 0 ? '+' : ''}}${{dYield}} bps (${{yield10Y.toFixed(2)}}%)`;
  
  document.getElementById('val-tariff').innerText = `+${{dTariff.toFixed(1)}}%`;

  // 1. Inflation Impacts (Parametric IMF / BIS elasticities)
  // Oil pass-through: US ~0.022 per 1% oil, EA ~0.035, China PPI ~0.075, UK ~0.028
  // Tariff pass-through: US Core PCE ~0.042 per 1% tariff
  const usCpiDelta = (dOil * 0.022) + (dTariff * 0.042);
  const eaCpiDelta = (dOil * 0.035) + (dTariff * 0.015);
  const cnPpiDelta = (dOil * 0.075) - (dTariff * 0.025); // Tariff suppresses export industrial prices
  const ukCpiDelta = (dOil * 0.028) + (dTariff * 0.018);

  document.getElementById('impact-us-cpi').innerText = `${{usCpiDelta >= 0 ? '+' : ''}}${{usCpiDelta.toFixed(2)}}%`;
  document.getElementById('impact-us-cpi').style.color = usCpiDelta > 0.5 ? 'var(--bad)' : (usCpiDelta < -0.3 ? 'var(--good)' : 'var(--fg)');
  document.getElementById('new-us-cpi').innerText = `${{(3.12 + usCpiDelta).toFixed(2)}}%`;

  document.getElementById('impact-ea-cpi').innerText = `${{eaCpiDelta >= 0 ? '+' : ''}}${{eaCpiDelta.toFixed(2)}}%`;
  document.getElementById('impact-ea-cpi').style.color = eaCpiDelta > 0.5 ? 'var(--bad)' : (eaCpiDelta < -0.3 ? 'var(--good)' : 'var(--fg)');
  document.getElementById('new-ea-cpi').innerText = `${{(2.00 + eaCpiDelta).toFixed(2)}}%`;

  document.getElementById('impact-cn-ppi').innerText = `${{cnPpiDelta >= 0 ? '+' : ''}}${{cnPpiDelta.toFixed(2)}}%`;
  document.getElementById('new-cn-ppi').innerText = `${{(-2.80 + cnPpiDelta).toFixed(2)}}%`;

  document.getElementById('impact-uk-cpi').innerText = `${{ukCpiDelta >= 0 ? '+' : ''}}${{ukCpiDelta.toFixed(2)}}%`;
  document.getElementById('new-uk-cpi').innerText = `${{(1.70 + ukCpiDelta).toFixed(2)}}%`;

  // 2. Financial Conditions & Spreads
  // DXY shift: ~0.03% per bp of US yield + flight to safety
  const dxyShift = (dYield * 0.03) + (dTariff * 0.18);
  const btpShift = Math.round(Math.max(0, dYield * 0.36 + (dOil > 20 ? 15 : 0)));
  const embiShift = Math.round(Math.max(0, dYield * 0.56 + dTariff * 3.5));
  const tradeVolumeDelta = -(dTariff * 0.16) - (Math.max(0, dOil) * 0.04);

  document.getElementById('impact-dxy').innerText = `${{dxyShift >= 0 ? '+' : ''}}${{dxyShift.toFixed(1)}}%`;
  document.getElementById('new-dxy').innerText = (104.2 * (1 + dxyShift / 100)).toFixed(1);

  document.getElementById('impact-btp').innerText = `+${{btpShift}} bps`;
  document.getElementById('new-btp').innerText = `${{122 + btpShift}} bps`;

  document.getElementById('impact-embi').innerText = `+${{embiShift}} bps`;
  document.getElementById('new-embi').innerText = `${{320 + embiShift}} bps`;

  document.getElementById('impact-trade').innerText = `${{tradeVolumeDelta.toFixed(1)}}%`;

  // 3. Central Bank Reactions Synthesis
  const reactionContainer = document.getElementById('reaction-container');
  let fedReaction = '';
  let ecbReaction = '';
  let pbocReaction = '';

  if (usCpiDelta > 0.6 || dYield > 60) {{
    fedReaction = currentLang === 'zh' ? 
      '🇺🇸 <strong>美联储 (Fed):</strong> 通胀上行或长端收益率飙升将迫使美联储<strong>暂停降息周期</strong>，重提更高的中性利率 ($r^*$)，甚至在滞胀情景下保留加息期权。' :
      '🇺🇸 <strong>Federal Reserve:</strong> Elevated inflation pass-through or surging long yields will force the Fed to <strong>pause the easing cycle</strong>, upwardly revise r* estimates, or risk hawkish talk.';
  }} else if (usCpiDelta < -0.3 && dYield < -30) {{
    fedReaction = currentLang === 'zh' ?
      '🇺🇸 <strong>美联储 (Fed):</strong> 通胀迅速向2%目标回落，就业市场风险主导，促使美联储<strong>加速降息至中性利率以下</strong>以防经济衰退。' :
      '🇺🇸 <strong>Federal Reserve:</strong> Rapid disinflation frees the Fed to <strong>front-load rate cuts towards neutral</strong> to defend employment.';
  }} else {{
    fedReaction = currentLang === 'zh' ?
      '🇺🇸 <strong>美联储 (Fed):</strong> 维持基准渐进式降息步伐 (每次会议 25 bps)，兼顾双重使命平衡。' :
      '🇺🇸 <strong>Federal Reserve:</strong> Baseline gradual easing intact (~25 bps per meeting) as risks remain balanced.';
  }}

  if (eaCpiDelta > 0.7 && dOil > 25) {{
    ecbReaction = currentLang === 'zh' ?
      '🇪🇺 <strong>欧洲央行 (ECB):</strong> 陷入能源冲击型<strong>滞胀困境</strong>：一方面经济增长脆弱要求降息，另一方面输入型通胀压抑消费，政策降息空间受到显著挤压。' :
      '🇪🇺 <strong>European Central Bank:</strong> Trapped in an energy-driven <strong>stagflation pinch</strong>: weak growth urges easing, but imported inflation constrains rate cuts.';
  }} else if (dTariff > 10) {{
    ecbReaction = currentLang === 'zh' ?
      '🇪🇺 <strong>欧洲央行 (ECB):</strong> 关税冲击严重损害德国等出口核心国，欧央行将采取<strong>更加积极的防护性降息</strong>以支撑制造业投资。' :
      '🇪🇺 <strong>European Central Bank:</strong> Export drag on core Germany necessitates <strong>aggressive defensive rate cuts</strong> to buffer manufacturing recession.';
  }} else {{
    ecbReaction = currentLang === 'zh' ?
      '🇪🇺 <strong>欧洲央行 (ECB):</strong> 稳步向 2.00%-2.50% 的中性利率走廊推进，抗通胀成果基本巩固。' :
      '🇪🇺 <strong>European Central Bank:</strong> Steady path towards the 2.00%-2.50% neutral corridor as domestic disinflation consolidates.';
  }}

  if (dTariff > 8 || cnPpiDelta < -0.5) {{
    pbocReaction = currentLang === 'zh' ?
      '🇨🇳 <strong>中国人民银行 (PBOC):</strong> 启动更大幅度的<strong>总量与结构性对冲</strong>：降准 50bp、降息 20-30bp 并加大国债二级市场买入力度，同时通过逆周期因子稳定人民币中间价。' :
      '🇨🇳 <strong>People\'s Bank of China:</strong> Aggressive <strong>counter-cyclical easing</strong>: further 50bp RRR cuts, 20-30bp LPR cuts, and expanded secondary market bond purchases with FX stabilization.';
  }} else {{
    pbocReaction = currentLang === 'zh' ?
      '🇨🇳 <strong>中国人民银行 (PBOC):</strong> 保持充裕流动性投放，引导综合融资成本稳中有降，维持适度宽松的货币金融环境。' :
      '🇨🇳 <strong>People\'s Bank of China:</strong> Ample structural liquidity support, maintaining moderately accommodative financial conditions.';
  }}

  reactionContainer.innerHTML = `
    <div>${{fedReaction}}</div>
    <div>${{ecbReaction}}</div>
    <div>${{pbocReaction}}</div>
  `;
}}

/* ==============================================================================
   7. 2026/2027 Central Bank Calendar Data & Filter
   ============================================================================== */
const CALENDAR_EVENTS = [
  {{ date: '2026-11-20', cb: 'PBOC', name: 'LPR Monthly Fixing', type: 'Loan Prime Rate', exp: 'Hold 1Y at 3.10%, 5Y at 3.60%' }},
  {{ date: '2026-12-11', cb: 'ECB', name: 'Governing Council Monetary Policy', type: 'Rate Decision & Staff Projections', exp: '-25 bps cut (DFR to 3.00%)' }},
  {{ date: '2026-12-17', cb: 'FED', name: 'FOMC Meeting (Day 1)', type: 'Policy Deliberations', exp: 'Review Labor & Inflation Data' }},
  {{ date: '2026-12-18', cb: 'FED', name: 'FOMC Statement, Press Conference & SEP', type: 'Rate Decision & Dot Plot', exp: '-25 bps cut (4.50%-4.75%)' }},
  {{ date: '2026-12-18', cb: 'BOE', name: 'Monetary Policy Committee Decision', type: 'Bank Rate & Minutes', exp: 'Hold at 4.75% (8-1 Split)' }},
  {{ date: '2026-12-19', cb: 'BOJ', name: 'Monetary Policy Meeting', type: 'Call Rate & Quarterly Outlook', exp: 'High probability of +25 bps hike to 0.50%' }},
  {{ date: '2026-12-20', cb: 'PBOC', name: 'LPR Monthly Fixing', type: 'Loan Prime Rate', exp: 'Year-end Liquidity Support' }},
  {{ date: '2027-01-28', cb: 'FED', name: 'FOMC Rate Decision', type: 'Policy Statement', exp: 'Pause / Assess Cumulative Cuts' }},
  {{ date: '2027-01-29', cb: 'ECB', name: 'Governing Council Meeting', type: 'Rate Decision', exp: '-25 bps cut (DFR to 2.75%)' }},
  {{ date: '2027-02-05', cb: 'BOE', name: 'MPC Decision & Monetary Policy Report', type: 'Rate Decision & MPR', exp: '-25 bps cut to 4.50%' }},
  {{ date: '2027-03-18', cb: 'FED', name: 'FOMC Statement & Updated SEP', type: 'Rate Decision & Dot Plot', exp: '-25 bps cut to 4.25%-4.50%' }},
  {{ date: '2027-03-19', cb: 'BOJ', name: 'Monetary Policy Meeting', type: 'Rate Decision', exp: 'Hold / Assess Normalization' }}
];

let calFilter = 'ALL';

function filterCal(filter) {{
  calFilter = filter;
  document.querySelectorAll('.cal-btn').forEach(b => b.classList.remove('active'));
  if (event && event.currentTarget) event.currentTarget.classList.add('active');
  renderCal();
}}

function renderCal() {{
  const tbody = document.getElementById('cal-table-body');
  const filtered = calFilter === 'ALL' ? CALENDAR_EVENTS : CALENDAR_EVENTS.filter(e => e.cb === calFilter);

  tbody.innerHTML = filtered.map(e => `
    <tr>
      <td style="font-family:var(--font-mono);font-weight:700;white-space:nowrap;">${{e.date}}</td>
      <td><strong>${{e.cb === 'FED' ? '🇺🇸 Fed' : (e.cb === 'ECB' ? '🇪🇺 ECB' : (e.cb === 'BOE' ? '🇬🇧 BoE' : (e.cb === 'BOJ' ? '🇯🇵 BoJ' : '🇨🇳 PBOC')))}}</strong></td>
      <td>${{e.name}}</td>
      <td><span style="color:var(--text-secondary);">${{e.type}}</span>${{e.type.includes('SEP') || e.type.includes('Dot Plot') ? '<span class="tag-sep">SEP / DOTS</span>' : ''}}</td>
      <td><strong style="color:var(--teal);">${{e.exp}}</strong></td>
    </tr>
  `).join('');
}}

/* ==============================================================================
   Initialization
   ============================================================================== */
window.addEventListener('DOMContentLoaded', () => {{
  applyLang();
  initDotplot();
  renderDiffStatement();
  updateShockSim();
  renderCal();
}});
</script>
</body>
</html>
"""


def build() -> Path:
    """Compile and write policy_tracker.html in both output/ and root directories."""
    OUTPUT.mkdir(parents=True, exist_ok=True)
    html_content = build_policy_tracker_html()

    out_file = OUTPUT / "policy_tracker.html"
    out_file.write_text(html_content, encoding="utf-8")
    print(f"Wrote {out_file} ({len(html_content):,} bytes)")

    root_file = ROOT / "policy_tracker.html"
    root_file.write_text(html_content, encoding="utf-8")
    print(f"Wrote {root_file} ({len(html_content):,} bytes)")

    return out_file


if __name__ == "__main__":
    build()
