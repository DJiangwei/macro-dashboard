#!/usr/bin/env python3
"""Build script for My Dashboard (Personal Macro Watchlist & Executive Briefing).

Generates output/my_dashboard.html and copies it to my_dashboard.html in the root.
Fully persistent in localStorage with curated institutional starter set,
interactive Plotly historical charts, editable personal notes, full catalog search modal,
CSV timeseries data export, and JSON configuration backup/restore.
"""
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "output"

COUNTRY_MAP = {
    "US": ("United States", "美国", "us_canonical_frame.json", "🇺🇸"),
    "CN": ("China", "中国", "china_canonical_frame.json", "🇨🇳"),
    "EA": ("Euro Area", "欧元区", "euro_area_canonical_frame.json", "🇪🇺"),
    "UK": ("United Kingdom", "英国", "uk_canonical_frame.json", "🇬🇧"),
    "JP": ("Japan", "日本", "japan_canonical_frame.json", "🇯🇵"),
    "ZA": ("South Africa", "南非", "south_africa_canonical_frame.json", "🇿🇦"),
    "TR": ("Turkey", "土耳其", "turkey_canonical_frame.json", "🇹🇷"),
    "HK": ("Hong Kong", "中国香港", "hong_kong_canonical_frame.json", "🇭🇰"),
    "KR": ("South Korea", "韩国", "south_korea_canonical_frame.json", "🇰🇷"),
    "TW": ("Taiwan", "中国台湾", "taiwan_canonical_frame.json", "🇹🇼"),
    "KZ": ("Kazakhstan", "哈萨克斯坦", "kazakhstan_canonical_frame.json", "🇰🇿"),
    "UZ": ("Uzbekistan", "乌兹别克斯坦", "uzbekistan_canonical_frame.json", "🇺🇿"),
    "EG": ("Egypt", "埃及", "egypt_canonical_frame.json", "🇪🇬"),
    "NG": ("Nigeria", "尼日利亚", "nigeria_canonical_frame.json", "🇳🇬"),
    "HU": ("Hungary", "匈牙利", "cee_canonical_frame.json", "🇭🇺"),
    "PL": ("Poland", "波兰", "cee_canonical_frame.json", "🇵🇱"),
    "CZ": ("Czechia", "捷克", "cee_canonical_frame.json", "🇨🇿"),
    "RO": ("Romania", "罗马尼亚", "cee_canonical_frame.json", "🇷🇴"),
}

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

STARTER_WATCHLIST = [
    {
        "type": "indicator",
        "country": "US",
        "id": "treasury_10y_yield",
        "notes": "Global risk-free rate anchor & term premium barometer. Critical benchmark for global duration and mortgage rates."
    },
    {
        "type": "indicator",
        "country": "US",
        "id": "fed_total_assets",
        "notes": "Federal Reserve Balance Sheet level ($6.75T). Tracks Quantitative Tightening (QT) runoff and bank reserve plumbing."
    },
    {
        "type": "indicator",
        "country": "EA",
        "id": "aaa_yield_10y",
        "notes": "Eurozone 10Y AAA Bund Yield benchmark. Reflects European safe-haven duration and ECB policy easing expectations."
    },
    {
        "type": "indicator",
        "country": "CN",
        "id": "cgb_yield_10y",
        "notes": "China 10Y Sovereign CGB benchmark yield. Tracking domestic credit demand, PBOC monetary stance, and US-China spread."
    },
    {
        "type": "indicator",
        "country": "JP",
        "id": "boj_total_assets",
        "notes": "Bank of Japan Total Assets (¥625T). Monitors post-YCC quantitative normalization and JGB purchase reductions."
    },
    {
        "type": "indicator",
        "country": "TR",
        "id": "short_term_external_debt_pct_reserves",
        "notes": "Guidotti-Greenspan Ratio (114.5% of reserves). Emerging market short-term foreign debt rollover threshold (<100%)."
    },
    {
        "type": "indicator",
        "country": "KZ",
        "id": "brent_crude_oil",
        "notes": "Brent Crude Spot Price. Upstream commodity terms of trade, global energy demand, and headline cost-push inflation."
    },
    {
        "type": "indicator",
        "country": "US",
        "id": "initial_jobless_claims_4w_ma",
        "notes": "US Initial Jobless Claims 4-Week Moving Average. High-frequency US labor market leading pulse & layoff friction."
    }
]


def build_my_dashboard_html() -> str:
    # Country Nav Links
    nav_links = []
    for code, name_en, name_zh, href in COUNTRY_NAV:
        nav_links.append(f'<a href="{href}" title="{name_en} ({name_zh})">{code}</a>')
    country_nav_html = "\n    ".join(nav_links)

    starter_json = json.dumps(STARTER_WATCHLIST, ensure_ascii=False)
    country_map_json = json.dumps(COUNTRY_MAP, ensure_ascii=False)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>My Macro Dashboard · 我的自选宏观看板</title>
  <link rel="icon" href="data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 100 100%22><text y=%22.9em%22 font-size=%2290%22>⭐</text></svg>">
  <script src="https://unpkg.com/lightweight-charts@4.2.1/dist/lightweight-charts.standalone.production.js"></script>
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

    /* Topbar matching FT Institutional specification */
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
    .country-nav a.active {{
      background: rgba(153, 15, 61, 0.1);
      color: var(--accent);
      font-weight: 700;
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
      transition: all 0.15s ease;
    }}
    .topbar-btn:hover {{
      border-color: var(--text-secondary);
      background: #fbf9f5;
    }}

    .container {{
      max-width: 1380px;
      margin: 0 auto;
      padding: 24px 20px 40px;
    }}

    /* Header & Hero Section */
    .dashboard-header {{
      margin-bottom: 24px;
      border-bottom: 1px solid var(--border);
      padding-bottom: 20px;
    }}
    .eyebrow {{
      font-size: 11px;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.08em;
      color: var(--accent);
      margin-bottom: 6px;
    }}
    .header-main {{
      display: flex;
      justify-content: space-between;
      align-items: flex-end;
      gap: 20px;
      flex-wrap: wrap;
    }}
    h1 {{
      font-family: var(--font-serif);
      font-size: 32px;
      font-weight: 700;
      line-height: 1.15;
      color: var(--fg);
      margin-bottom: 6px;
    }}
    .subtitle {{
      color: var(--text-secondary);
      font-size: 13.5px;
      max-width: 880px;
      line-height: 1.5;
    }}

    /* Stats Chips Row */
    .meta-row {{
      display: flex;
      align-items: center;
      gap: 10px;
      flex-wrap: wrap;
      margin-top: 14px;
    }}
    .meta-chip {{
      font-size: 11.5px;
      background: var(--surface);
      border: 1px solid var(--border);
      padding: 4px 10px;
      border-radius: 4px;
      color: var(--text-secondary);
      display: inline-flex;
      align-items: center;
      gap: 6px;
    }}
    .meta-chip strong {{
      color: var(--fg);
      font-family: var(--font-mono);
      font-weight: 600;
    }}

    /* Control Toolbar */
    .toolbar {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 12px;
      flex-wrap: wrap;
      margin-bottom: 20px;
      background: var(--surface);
      padding: 12px 16px;
      border: 1px solid var(--border);
      border-radius: var(--radius);
      box-shadow: var(--shadow-sm);
    }}
    .toolbar-left, .toolbar-right {{
      display: flex;
      align-items: center;
      gap: 8px;
      flex-wrap: wrap;
    }}

    .btn {{
      font-size: 12px;
      font-weight: 600;
      padding: 6px 12px;
      border-radius: 4px;
      border: 1px solid var(--border);
      background: var(--surface);
      color: var(--fg);
      cursor: pointer;
      display: inline-flex;
      align-items: center;
      gap: 6px;
      transition: all 0.15s ease;
      white-space: nowrap;
    }}
    .btn:hover {{
      background: #fcfaf7;
      border-color: var(--text-secondary);
    }}
    .btn-primary {{
      background: var(--teal);
      border-color: var(--teal);
      color: #ffffff;
    }}
    .btn-primary:hover {{
      background: #095961;
      border-color: #095961;
      color: #ffffff;
    }}
    .btn-group {{
      display: inline-flex;
      border-radius: 4px;
      overflow: hidden;
      border: 1px solid var(--border);
    }}
    .btn-group .btn {{
      border: none;
      border-radius: 0;
      border-right: 1px solid var(--border);
    }}
    .btn-group .btn:last-child {{
      border-right: none;
    }}
    .btn-group .btn.active {{
      background: #f0ebe4;
      color: var(--accent);
      font-weight: 700;
    }}

    /* Watchlist Grid View */
    .watchlist-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(440px, 1fr));
      gap: 20px;
    }}
    @media (max-width: 600px) {{
      .watchlist-grid {{ grid-template-columns: 1fr; }}
    }}

    .indicator-card {{
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: var(--radius);
      box-shadow: var(--shadow-sm);
      display: flex;
      flex-direction: column;
      transition: box-shadow 0.2s, transform 0.2s;
      position: relative;
    }}
    .indicator-card:hover {{
      box-shadow: var(--shadow-md);
    }}

    .card-top {{
      padding: 12px 14px;
      border-bottom: 1px solid var(--border-subtle);
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      gap: 12px;
      background: #fdfcf9;
      border-top-left-radius: var(--radius);
      border-top-right-radius: var(--radius);
    }}
    .card-title-group {{
      flex: 1;
      min-width: 0;
    }}
    .card-badge-row {{
      display: flex;
      align-items: center;
      gap: 6px;
      margin-bottom: 4px;
    }}
    .country-tag {{
      font-size: 11px;
      font-weight: 700;
      font-family: var(--font-mono);
      background: #f0ebe4;
      padding: 2px 6px;
      border-radius: 3px;
      color: var(--fg);
    }}
    .section-tag {{
      font-size: 10.5px;
      color: var(--text-secondary);
      text-transform: capitalize;
    }}
    .card-title {{
      font-size: 14px;
      font-weight: 700;
      color: var(--fg);
      line-height: 1.3;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }}
    .card-actions {{
      display: flex;
      align-items: center;
      gap: 4px;
      flex-shrink: 0;
    }}
    .icon-btn {{
      background: transparent;
      border: 1px solid transparent;
      border-radius: 3px;
      padding: 3px 6px;
      cursor: pointer;
      font-size: 11px;
      color: var(--text-secondary);
      transition: all 0.15s;
    }}
    .icon-btn:hover {{
      background: #f0ebe4;
      border-color: var(--border);
      color: var(--fg);
    }}
    .icon-btn.remove:hover {{
      background: rgba(153, 15, 61, 0.08);
      color: var(--bad);
      border-color: rgba(153, 15, 61, 0.2);
    }}

    .card-stat-hero {{
      padding: 14px 16px 8px;
      display: flex;
      justify-content: space-between;
      align-items: baseline;
    }}
    .hero-val {{
      font-family: var(--font-mono);
      font-size: 24px;
      font-weight: 700;
      color: var(--fg);
    }}
    .hero-meta {{
      font-size: 11px;
      color: var(--text-secondary);
      text-align: right;
    }}

    .card-chart-wrap {{
      padding: 0 12px 10px;
      display: flex;
      flex-direction: column;
      gap: 4px;
      position: relative;
    }}
    .lw-card-toolbar {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 6px;
      padding: 2px 4px;
      background: #FAF8F5;
      border: 1px solid var(--border-subtle);
      border-radius: 4px;
      flex-wrap: wrap;
    }}
    .lw-range-bar, .lw-action-bar {{
      display: inline-flex;
      align-items: center;
      gap: 2px;
    }}
    .lw-range-btn, .lw-tool-btn {{
      appearance: none;
      border: 1px solid transparent;
      background: transparent;
      color: var(--text-secondary);
      font-family: var(--font-mono);
      font-size: 10px;
      font-weight: 600;
      padding: 2px 6px;
      border-radius: 3px;
      cursor: pointer;
      transition: all 0.12s ease;
    }}
    .lw-range-btn:hover, .lw-tool-btn:hover {{
      background: #EFECE6;
      color: var(--fg);
    }}
    .lw-range-btn.active {{
      background: #12151a;
      color: #ffffff;
    }}
    .lw-tool-btn.active {{
      background: rgba(13, 118, 128, 0.14);
      border-color: var(--teal);
      color: var(--teal);
    }}
    .lw-delta-banner {{
      display: none;
      align-items: center;
      justify-content: space-between;
      gap: 8px;
      padding: 4px 8px;
      background: #F4F9F9;
      border: 1px solid rgba(13, 118, 128, 0.28);
      border-radius: 4px;
      font-family: var(--font-mono);
      font-size: 10.5px;
      color: var(--fg);
    }}
    .lw-delta-banner.active {{
      display: flex;
    }}
    .lw-plot-box {{
      width: 100%;
      height: 215px;
      position: relative;
      cursor: grab;
    }}
    .lw-plot-box:active {{
      cursor: grabbing;
    }}
    .lw-plot-box.box-zoom-cursor {{
      cursor: crosshair !important;
    }}
    .lw-tooltip {{
      position: absolute;
      top: 8px;
      left: 10px;
      z-index: 15;
      pointer-events: none;
      background: rgba(255, 253, 250, 0.95);
      border: 1px solid #D9D2C7;
      border-radius: 4px;
      padding: 5px 8px;
      box-shadow: 0 2px 8px rgba(18, 21, 26, 0.08);
      font-size: 10.5px;
      line-height: 1.35;
      display: none;
    }}
    .lw-select-overlay {{
      position: absolute;
      top: 0;
      bottom: 22px;
      background: rgba(13, 118, 128, 0.15);
      border-left: 1.5px dashed #0d7680;
      border-right: 1.5px dashed #0d7680;
      pointer-events: none;
      z-index: 14;
      display: none;
    }}
    .indicator-card.lw-fullscreen {{
      position: fixed !important;
      inset: 24px !important;
      z-index: 9999 !important;
      background: #FFFDFA !important;
      box-shadow: 0 24px 64px rgba(18, 21, 26, 0.38) !important;
      padding: 16px !important;
      overflow-y: auto !important;
    }}
    .indicator-card.lw-fullscreen .lw-plot-box {{
      height: calc(100vh - 280px) !important;
      min-height: 420px !important;
    }}

    .card-notes-wrap {{
      padding: 10px 14px;
      background: #fbf9f5;
      border-top: 1px solid var(--border-subtle);
      border-bottom-left-radius: var(--radius);
      border-bottom-right-radius: var(--radius);
      display: flex;
      flex-direction: column;
      gap: 4px;
    }}
    .notes-label {{
      font-size: 10px;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      color: var(--text-secondary);
      display: flex;
      justify-content: space-between;
      align-items: center;
    }}
    .notes-saved-indicator {{
      font-size: 9.5px;
      color: var(--teal);
      display: none;
    }}
    .notes-textarea {{
      width: 100%;
      font-family: var(--font-main);
      font-size: 12px;
      color: var(--fg);
      background: transparent;
      border: 1px solid transparent;
      border-radius: 4px;
      padding: 4px 6px;
      resize: vertical;
      min-height: 38px;
      line-height: 1.4;
      transition: all 0.15s;
    }}
    .notes-textarea:focus {{
      outline: none;
      background: #ffffff;
      border-color: var(--teal);
      box-shadow: 0 0 0 2px rgba(13, 118, 128, 0.1);
    }}

    /* Table View */
    .table-view-wrap {{
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: var(--radius);
      box-shadow: var(--shadow-sm);
      overflow-x: auto;
      display: none;
    }}
    .watchlist-table {{
      width: 100%;
      border-collapse: collapse;
      font-size: 12px;
      text-align: left;
    }}
    .watchlist-table th {{
      background: #fcfaf7;
      color: var(--text-secondary);
      font-weight: 700;
      padding: 10px 14px;
      border-bottom: 1px solid var(--border);
      font-size: 11px;
      text-transform: uppercase;
      letter-spacing: 0.03em;
    }}
    .watchlist-table td {{
      padding: 10px 14px;
      border-bottom: 1px solid var(--border-subtle);
      vertical-align: middle;
    }}
    .watchlist-table tr:hover {{
      background: #fdfcf9;
    }}

    /* Modal for Adding Indicators */
    .modal-backdrop {{
      position: fixed;
      top: 0; left: 0; right: 0; bottom: 0;
      background: rgba(18, 21, 26, 0.45);
      backdrop-filter: blur(2px);
      z-index: 200;
      display: none;
      align-items: center;
      justify-content: center;
      padding: 20px;
    }}
    .modal-card {{
      background: var(--surface);
      border-radius: 8px;
      box-shadow: var(--shadow-lg);
      width: 100%;
      max-width: 680px;
      max-height: 85vh;
      display: flex;
      flex-direction: column;
      overflow: hidden;
      border: 1px solid var(--border);
    }}
    .modal-header {{
      padding: 16px 20px;
      border-bottom: 1px solid var(--border);
      display: flex;
      justify-content: space-between;
      align-items: center;
      background: #fdfcf9;
    }}
    .modal-title {{
      font-family: var(--font-serif);
      font-size: 18px;
      font-weight: 700;
    }}
    .modal-body {{
      padding: 16px 20px;
      overflow-y: auto;
      flex: 1;
    }}
    .search-inputs {{
      display: flex;
      gap: 10px;
      margin-bottom: 16px;
    }}
    .search-input {{
      flex: 1;
      padding: 8px 12px;
      font-size: 13px;
      border: 1px solid var(--border);
      border-radius: 4px;
      outline: none;
    }}
    .search-input:focus {{
      border-color: var(--teal);
      box-shadow: 0 0 0 2px rgba(13, 118, 128, 0.1);
    }}
    .country-select {{
      padding: 8px 10px;
      font-size: 13px;
      border: 1px solid var(--border);
      border-radius: 4px;
      background: var(--surface);
      outline: none;
    }}
    .results-list {{
      display: flex;
      flex-direction: column;
      gap: 6px;
      max-height: 420px;
      overflow-y: auto;
    }}
    .result-item {{
      padding: 10px 12px;
      border: 1px solid var(--border-subtle);
      border-radius: 4px;
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 12px;
      transition: background 0.15s;
    }}
    .result-item:hover {{
      background: #fdfcf9;
      border-color: var(--border);
    }}
    .result-info {{
      flex: 1;
      min-width: 0;
    }}
    .result-title {{
      font-weight: 600;
      font-size: 13px;
      color: var(--fg);
    }}
    .result-sub {{
      font-size: 11px;
      color: var(--text-secondary);
      display: flex;
      gap: 8px;
      margin-top: 2px;
    }}

    /* Toast Notification */
    .toast {{
      position: fixed;
      bottom: 24px;
      right: 24px;
      background: #12151a;
      color: #ffffff;
      padding: 10px 18px;
      border-radius: 6px;
      font-size: 12.5px;
      font-weight: 500;
      box-shadow: var(--shadow-md);
      z-index: 300;
      opacity: 0;
      transform: translateY(10px);
      transition: all 0.25s ease;
      pointer-events: none;
    }}
    .toast.show {{
      opacity: 1;
      transform: translateY(0);
    }}

    /* Empty State */
    .empty-state {{
      padding: 60px 20px;
      text-align: center;
      background: var(--surface);
      border: 1px dashed var(--border);
      border-radius: var(--radius);
      display: none;
    }}
    .empty-icon {{ font-size: 40px; margin-bottom: 12px; }}
    .empty-title {{ font-size: 18px; font-weight: 700; margin-bottom: 6px; }}
    .empty-desc {{ color: var(--text-secondary); font-size: 13px; margin-bottom: 20px; }}

    /* Print styles */
    @media print {{
      .topbar, .toolbar, .modal-backdrop, .icon-btn, .notes-label span:last-child {{
        display: none !important;
      }}
      body {{ background: #ffffff; padding: 0; }}
      .container {{ max-width: 100%; padding: 0; }}
      .indicator-card {{
        break-inside: avoid;
        border: 1px solid #ccc;
        box-shadow: none;
        margin-bottom: 20px;
      }}
      .card-notes-wrap {{ background: #fff; border-top: 1px solid #eee; }}
      .notes-textarea {{ border: none; resize: none; }}
    }}
  </style>
</head>
<body data-lang="en">

<!-- Topbar Navigation -->
<div class="topbar">
  <a href="index.html" class="brand">East Meridian <span>/ Macro Dashboard</span></a>
  <nav class="country-nav" aria-label="country dashboards">
    {country_nav_html}
    <a href="chart_studio.html" title="Macro Chart Studio · 宏观图表工坊">📈 Studio</a>
    <a href="my_dashboard.html" class="active" title="My Dashboard · 我的自选宏观看板">⭐ My Dashboard</a>
    <a href="policy_tracker.html" title="Central Bank Policy & Event Tracker · 全球央行与宏观事件追踪">🏛️ Policy</a>
  </nav>
  <div class="topbar-actions">
    <a href="index.html" class="topbar-btn">← <span data-lang="en">Home</span><span data-lang="zh">首页</span></a>
    <button class="topbar-btn" onclick="toggleLang()" id="lang-btn">中文</button>
  </div>
</div>

<main class="container">

  <!-- Header -->
  <header class="dashboard-header">
    <p class="eyebrow"><span data-lang="en">Personalized Macro Intelligence Desk</span><span data-lang="zh">专属宏观投研工作台 · 自选看板</span></p>
    <div class="header-main">
      <div>
        <h1><span data-lang="en">My Macro Dashboard</span><span data-lang="zh">我的自选宏观看板</span></h1>
        <p class="subtitle">
          <span data-lang="en">Curate, monitor, and annotate your high-conviction macro indicators across 18 economies. Persisted automatically in your browser with full CSV timeseries download, JSON configuration backup, and print-ready executive briefing views.</span>
          <span data-lang="zh">自由钉选、持续跟踪并批注 18 个核心经济体的自选宏观指标。基于浏览器本地存储持久化保存，支持多图表画板与紧凑清单双视图、个人研究笔记、一键导出全量时序 CSV 与配置备份。</span>
        </p>
      </div>
      <div class="meta-row">
        <span class="meta-chip"><strong>18</strong> <span data-lang="en">Economies</span><span data-lang="zh">经济体数据池</span></span>
        <span class="meta-chip"><strong id="stat-pinned-count">8</strong> <span data-lang="en">Pinned Items</span><span data-lang="zh">自选指标数</span></span>
        <span class="meta-chip"><strong style="color:var(--teal);">Client Persistent</strong> <span data-lang="en">localStorage</span><span data-lang="zh">本地持久化</span></span>
      </div>
    </div>
  </header>

  <!-- Controls Toolbar -->
  <section class="toolbar">
    <div class="toolbar-left">
      <button class="btn btn-primary" onclick="openAddModal()">
        <span>➕</span>
        <span data-lang="en">Add Indicator</span><span data-lang="zh">添加指标</span>
      </button>

      <div class="btn-group">
        <button class="btn active" id="view-grid-btn" onclick="switchView('grid')">
          <span>🔲</span>
          <span data-lang="en">Grid</span><span data-lang="zh">图表看板</span>
        </button>
        <button class="btn" id="view-table-btn" onclick="switchView('table')">
          <span>📋</span>
          <span data-lang="en">Table</span><span data-lang="zh">紧凑清单</span>
        </button>
      </div>

      <div class="btn-group" aria-label="Global chart time range">
        <button class="btn mydash-global-range" onclick="applyGlobalMyDashRange('1Y', this)">1Y</button>
        <button class="btn mydash-global-range" onclick="applyGlobalMyDashRange('3Y', this)">3Y</button>
        <button class="btn mydash-global-range" onclick="applyGlobalMyDashRange('5Y', this)">5Y</button>
        <button class="btn mydash-global-range" onclick="applyGlobalMyDashRange('10Y', this)">10Y</button>
        <button class="btn mydash-global-range active" onclick="applyGlobalMyDashRange('ALL', this)">All</button>
      </div>
    </div>

    <div class="toolbar-right">
      <button class="btn" onclick="exportWatchlistCSV()" title="Download CSV dataset of all pinned indicators">
        <span>📊</span>
        <span data-lang="en">Export CSV</span><span data-lang="zh">导出数据</span>
      </button>
      <button class="btn" onclick="exportWatchlistJSON()" title="Backup configuration file">
        <span>📥</span>
        <span data-lang="en">Backup JSON</span><span data-lang="zh">导出配置</span>
      </button>
      <button class="btn" onclick="document.getElementById('import-file-input').click()" title="Restore configuration">
        <span>📤</span>
        <span data-lang="en">Restore</span><span data-lang="zh">导入配置</span>
      </button>
      <input type="file" id="import-file-input" accept=".json" style="display:none;" onchange="importWatchlistJSON(event)">

      <button class="btn" onclick="window.print()" title="Print executive briefing">
        <span>🖨️</span>
        <span data-lang="en">Print</span><span data-lang="zh">打印报告</span>
      </button>
      <button class="btn" onclick="resetToStarterSet()" title="Reset to standard institutional starter watchlist" style="color:var(--text-secondary);">
        <span>↺</span>
        <span data-lang="en">Reset</span><span data-lang="zh">恢复推荐</span>
      </button>
    </div>
  </section>

  <!-- Empty State -->
  <div class="empty-state" id="empty-state">
    <div class="empty-icon">⭐</div>
    <div class="empty-title"><span data-lang="en">Your Watchlist is Empty</span><span data-lang="zh">自选看板暂无指标</span></div>
    <div class="empty-desc">
      <span data-lang="en">Click "Add Indicator" above or explore Country Dashboards to pin series.</span>
      <span data-lang="zh">点击上方“添加指标”按钮，或从各国家主页与图表工坊将核心时间序列加入自选。</span>
    </div>
    <button class="btn btn-primary" onclick="resetToStarterSet()">
      <span data-lang="en">Load Institutional Starter Set</span><span data-lang="zh">加载精选机构自选推荐包</span>
    </button>
  </div>

  <!-- View 1: Card Grid View -->
  <section class="watchlist-grid" id="watchlist-grid"></section>

  <!-- View 2: Executive Table View -->
  <section class="table-view-wrap" id="table-view-wrap">
    <table class="watchlist-table">
      <thead>
        <tr>
          <th><span data-lang="en">Country</span><span data-lang="zh">国家/经济体</span></th>
          <th><span data-lang="en">Indicator Name</span><span data-lang="zh">指标名称</span></th>
          <th><span data-lang="en">Freq</span><span data-lang="zh">频率</span></th>
          <th><span data-lang="en">Latest Date</span><span data-lang="zh">最新期数</span></th>
          <th><span data-lang="en">Latest Reading</span><span data-lang="zh">最新读数</span></th>
          <th><span data-lang="en">Personal Thesis & Notes</span><span data-lang="zh">个人研判观点 / 备忘</span></th>
          <th><span data-lang="en">Actions</span><span data-lang="zh">操作</span></th>
        </tr>
      </thead>
      <tbody id="table-view-tbody"></tbody>
    </table>
  </section>

</main>

<!-- Add Indicator Search Modal -->
<div class="modal-backdrop" id="add-modal" onclick="if(event.target === this) closeAddModal()">
  <div class="modal-card">
    <div class="modal-header">
      <div class="modal-title"><span data-lang="en">Add Macro Indicator</span><span data-lang="zh">添加宏观自选指标</span></div>
      <button class="icon-btn" onclick="closeAddModal()" style="font-size:16px;">✕</button>
    </div>
    <div class="modal-body">
      <div class="search-inputs">
        <select class="country-select" id="modal-country-select" onchange="filterModalResults()">
          <option value="ALL">🌐 All 18 Economies / 全部经济体</option>
        </select>
        <input type="text" class="search-input" id="modal-search-input" placeholder="Search indicator name, series ID, concept..." oninput="filterModalResults()">
      </div>
      <div class="results-list" id="modal-results-list">
        <div style="text-align:center; padding:30px; color:var(--text-secondary); font-size:12px;">Loading catalog...</div>
      </div>
    </div>
  </div>
</div>

<!-- Floating Toast -->
<div class="toast" id="toast"></div>

<script>
// --- Configuration & Global State ---
const STORAGE_KEY = 'macro_my_dashboard_watchlist_v1';
const STARTER_SET = {starter_json};
const COUNTRY_MAP = {country_map_json};

let CURRENT_LANG = 'en';
let CURRENT_VIEW = 'grid'; // 'grid' or 'table'
let CURRENT_GLOBAL_RANGE = 'ALL';
let WATCHLIST = [];
let CATALOG = null;
const FRAME_CACHE = {{}};
const MYDASH_CHARTS = {{}};

function formatVal(v, decimals = 2) {{
  if (v === null || v === undefined || isNaN(v)) return '—';
  const num = Number(v);
  const abs = Math.abs(num);
  let d = decimals;
  if (abs >= 100 && decimals > 1) d = 1;
  return num.toLocaleString('en-US', {{
    minimumFractionDigits: d,
    maximumFractionDigits: d
  }});
}}

function resolveDisplayScale(indicatorId, rawUnit, values) {{
  const unit = (rawUnit || '').trim();
  const valid = (values || []).filter(v => v !== null && v !== undefined && !isNaN(v)).map(v => Math.abs(Number(v)));
  if (!valid.length) return {{ factor: 1.0, unit }};
  const maxAbs = Math.max(...valid);
  const uLow = unit.toLowerCase();

  if (uLow.includes('%') || uLow.includes('bps') || uLow.includes('index') || uLow.includes('ratio') || uLow.includes('months')) {{
    return {{ factor: 1.0, unit }};
  }}
  if (uLow === 'jpy 100mn' || uLow === '100 million yen') {{
    if (maxAbs >= 10000) return {{ factor: 1.0 / 10000.0, unit: 'JPY tn' }};
    if (maxAbs >= 10) return {{ factor: 1.0 / 10.0, unit: 'JPY bn' }};
  }}
  if (uLow === 'cny 100mn') {{
    if (maxAbs >= 10000) return {{ factor: 1.0 / 10000.0, unit: 'CNY tn' }};
    if (maxAbs >= 10) return {{ factor: 1.0 / 10.0, unit: 'CNY bn' }};
  }}
  const mnMatch = unit.match(/^([A-Za-z€$£¥]{1,5})\\s*(mn|million|millions|m)$/i) || (unit === '$M' ? [null, 'USD', 'mn'] : null);
  if (mnMatch && maxAbs >= 1000) {{
    const ccy = mnMatch[1].toUpperCase();
    if (maxAbs >= 1e6) return {{ factor: 1.0 / 1e6, unit: `${{ccy}} tn` }};
    return {{ factor: 1.0 / 1000.0, unit: `${{ccy}} bn` }};
  }}
  const bnMatch = unit.match(/^([A-Za-z€$£¥]{1,5})\\s*(bn|billion|billions)$/i);
  if (bnMatch && maxAbs >= 1000) {{
    const ccy = bnMatch[1].toUpperCase();
    return {{ factor: 1.0 / 1000.0, unit: `${{ccy}} tn` }};
  }}
  if (['persons', 'person', 'people', 'headcount', 'claims', 'units'].includes(uLow)) {{
    if (maxAbs >= 1e6) return {{ factor: 1.0 / 1e6, unit: 'millions' }};
    if (maxAbs >= 1e3) return {{ factor: 1.0 / 1e3, unit: 'thousands' }};
  }}
  if (['thousand persons', 'thousands', '000s', 'thousand'].includes(uLow) && maxAbs >= 1000) {{
    return {{ factor: 1.0 / 1000.0, unit: 'millions' }};
  }}
  const ccyMatch = unit.match(/^([A-Z]{3})$/);
  if (ccyMatch && maxAbs >= 1e5 && !indicatorId.includes('fx') && !indicatorId.includes('usd')) {{
    const ccy = ccyMatch[1];
    if (maxAbs >= 1e12) return {{ factor: 1.0 / 1e12, unit: `${{ccy}} tn` }};
    if (maxAbs >= 1e9) return {{ factor: 1.0 / 1e9, unit: `${{ccy}} bn` }};
    if (maxAbs >= 1e6) return {{ factor: 1.0 / 1e6, unit: `${{ccy}} mn` }};
    return {{ factor: 1.0 / 1e3, unit: `${{ccy}} thousands` }};
  }}
  if (maxAbs >= 1e9) return {{ factor: 1.0 / 1e9, unit: unit ? `${{unit}} (billions)` : 'billions' }};
  if (maxAbs >= 1e6) return {{ factor: 1.0 / 1e6, unit: unit ? `${{unit}} (millions)` : 'millions' }};
  if (maxAbs >= 1e5) return {{ factor: 1.0 / 1e3, unit: unit ? `${{unit}} (thousands)` : 'thousands' }};
  return {{ factor: 1.0, unit }};
}}

function normalizeLwTime(rawDate) {{
  const s = String(rawDate || '').trim();
  const qm = s.match(/^(\\d{{4}})-Q([1-4])$/i);
  if (qm) {{
    const yr = qm[1];
    const q = parseInt(qm[2], 10);
    const mo = String((q - 1) * 3 + 1).padStart(2, '0');
    return `${{yr}}-${{mo}}-01`;
  }}
  if (/^\\d{{4}}-\\d{{2}}$/.test(s)) return `${{s}}-01`;
  if (/^\\d{{4}}$/.test(s)) return `${{s}}-01-01`;
  return s.slice(0, 10);
}}

// --- Initialization ---
document.addEventListener('DOMContentLoaded', async () => {{
  initLanguage();
  loadWatchlistFromStorage();
  populateCountrySelect();
  await loadCatalog();
  await renderDashboard();
}});

function initLanguage() {{
  const saved = localStorage.getItem('macro_dashboard_lang');
  if (saved && (saved === 'zh' || saved === 'en')) {{
    CURRENT_LANG = saved;
  }}
  applyLang();
}}

function toggleLang() {{
  CURRENT_LANG = (CURRENT_LANG === 'en' ? 'zh' : 'en');
  localStorage.setItem('macro_dashboard_lang', CURRENT_LANG);
  applyLang();
  renderDashboard();
}}

function applyLang() {{
  document.body.setAttribute('data-lang', CURRENT_LANG);
  document.getElementById('lang-btn').textContent = (CURRENT_LANG === 'en' ? '中文' : 'EN');
  document.querySelectorAll('[data-lang]').forEach(el => {{
    const lang = el.getAttribute('data-lang');
    el.style.display = (lang === CURRENT_LANG ? '' : 'none');
  }});
}}

// --- LocalStorage Management ---
function loadWatchlistFromStorage() {{
  try {{
    const raw = localStorage.getItem(STORAGE_KEY);
    if (raw) {{
      WATCHLIST = JSON.parse(raw);
    }} else {{
      WATCHLIST = JSON.parse(JSON.stringify(STARTER_SET));
      saveWatchlistToStorage();
    }}
  }} catch (e) {{
    console.error('Could not load watchlist, falling back to starter set:', e);
    WATCHLIST = JSON.parse(JSON.stringify(STARTER_SET));
  }}
}}

function saveWatchlistToStorage() {{
  try {{
    localStorage.setItem(STORAGE_KEY, JSON.stringify(WATCHLIST));
    document.getElementById('stat-pinned-count').textContent = WATCHLIST.length;
  }} catch (e) {{
    console.error('Failed to save to localStorage:', e);
  }}
}}

function resetToStarterSet() {{
  if (confirm(CURRENT_LANG === 'zh' ? '确定要恢复为推荐的机构自选组合吗？' : 'Reset watchlist to default institutional starter set?')) {{
    WATCHLIST = JSON.parse(JSON.stringify(STARTER_SET));
    saveWatchlistToStorage();
    renderDashboard();
    showToast(CURRENT_LANG === 'zh' ? '已恢复为推荐自选组合' : 'Watchlist reset to starter set');
  }}
}}

// --- Catalog & Canonical Frame Fetching ---
async function loadCatalog() {{
  try {{
    let res = await fetch('chart_studio_catalog.json');
    if (!res.ok) res = await fetch('output/chart_studio_catalog.json');
    if (res.ok) {{
      CATALOG = await res.json();
    }}
  }} catch (e) {{
    console.warn('Could not fetch chart_studio_catalog.json:', e);
  }}
}}

async function getCanonicalFrame(cfile) {{
  if (FRAME_CACHE[cfile]) return FRAME_CACHE[cfile];
  try {{
    let res = await fetch(cfile);
    if (!res.ok) res = await fetch('output/' + cfile);
    if (res.ok) {{
      const data = await res.json();
      FRAME_CACHE[cfile] = data;
      return data;
    }}
  }} catch (e) {{
    console.warn('Could not load frame ' + cfile, e);
  }}
  return null;
}}

async function resolveIndicatorData(country, indicatorId) {{
  const cMeta = COUNTRY_MAP[country];
  if (!cMeta) return null;
  const frame = await getCanonicalFrame(cMeta[2]);
  if (!frame) return null;

  let series = null;
  if (cMeta[2] === 'cee_canonical_frame.json') {{
    series = (frame.series || []).find(s => s.country === country && (s.indicator_id === indicatorId || s.id === indicatorId));
  }} else {{
    series = (frame.series || []).find(s => s.indicator_id === indicatorId || s.id === indicatorId);
  }}
  return series;
}}

// --- Rendering Dashboard (Grid & Table) ---
async function renderDashboard() {{
  const gridContainer = document.getElementById('watchlist-grid');
  const tableTbody = document.getElementById('table-view-tbody');
  const emptyState = document.getElementById('empty-state');
  const pinnedCountEl = document.getElementById('stat-pinned-count');

  pinnedCountEl.textContent = WATCHLIST.length;

  if (!WATCHLIST.length) {{
    gridContainer.innerHTML = '';
    tableTbody.innerHTML = '';
    emptyState.style.display = 'block';
    return;
  }}
  emptyState.style.display = 'none';

  if (CURRENT_VIEW === 'grid') {{
    document.getElementById('watchlist-grid').style.display = 'grid';
    document.getElementById('table-view-wrap').style.display = 'none';
  }} else {{
    document.getElementById('watchlist-grid').style.display = 'none';
    document.getElementById('table-view-wrap').style.display = 'block';
  }}

  gridContainer.innerHTML = '<div style="grid-column: 1/-1; text-align:center; padding:40px; color:var(--text-secondary);"><span data-lang="en">Loading observations...</span><span data-lang="zh">正在同步官方时序数据...</span></div>';
  applyLang();

  const renderedCards = [];
  const renderedTableRows = [];

  for (let idx = 0; idx < WATCHLIST.length; idx++) {{
    const item = WATCHLIST[idx];
    const series = await resolveIndicatorData(item.country, item.id);
    const cMeta = COUNTRY_MAP[item.country] || [item.country, item.country, '', '🏳️'];
    const cName = CURRENT_LANG === 'zh' ? cMeta[1] : cMeta[0];
    const flag = cMeta[3];

    let title = item.id;
    let unit = '';
    let freq = '';
    let latestValStr = 'n/a';
    let latestDateStr = '';
    let observations = [];

    if (series) {{
      title = CURRENT_LANG === 'zh' ? (series.label_zh || series.label_en || item.id) : (series.label_en || item.id);
      const rawUnit = series.unit || '';
      freq = series.frequency || '';
      const rawObs = (series.observations || []).map(o => {{
        if (Array.isArray(o)) return {{ date: o[0], value: parseFloat(o[1]) }};
        if (typeof o === 'object') return {{ date: o.date, value: parseFloat(o.value) }};
        return null;
      }}).filter(o => o && !isNaN(o.value));

      const scaleInfo = resolveDisplayScale(item.id, rawUnit, rawObs.map(o => o.value));
      unit = scaleInfo.unit;
      observations = rawObs.map(o => ({{
        date: o.date,
        time: normalizeLwTime(o.date),
        value: Math.round((o.value * scaleInfo.factor) * 10000) / 10000
      }}));

      if (observations.length) {{
        const last = observations[observations.length - 1];
        latestValStr = formatVal(last.value, 2);
        latestDateStr = last.date;
      }}
    }}

    // Grid Card HTML
    const cardId = `chart-card-${{idx}}`;
    const cardHtml = `
      <div class="indicator-card" id="card-box-${{idx}}">
        <div class="card-top">
          <div class="card-title-group">
            <div class="card-badge-row">
              <span class="country-tag">${{flag}} ${{item.country}}</span>
              <span class="section-tag">${{cName}} · ${{freq}}</span>
            </div>
            <div class="card-title" title="${{title}}">${{title}}</div>
          </div>
          <div class="card-actions">
            <button class="icon-btn" onclick="moveItem(${{idx}}, -1)" title="Move Up">▲</button>
            <button class="icon-btn" onclick="moveItem(${{idx}}, 1)" title="Move Down">▼</button>
            <a href="chart_studio.html" class="icon-btn" title="Open in Chart Studio">📈</a>
            <button class="icon-btn remove" onclick="removeItem(${{idx}})" title="Remove from Watchlist">✕</button>
          </div>
        </div>

        <div class="card-stat-hero">
          <div class="hero-val">${{latestValStr}} <span style="font-size:12px; font-weight:500; color:var(--text-secondary);">${{unit}}</span></div>
          <div class="hero-meta">${{latestDateStr}}<br><span style="text-transform:capitalize;">${{freq}}</span></div>
        </div>

        <div class="card-chart-wrap" id="wrap-${{cardId}}">
          <div class="lw-card-toolbar">
            <div class="lw-range-bar" role="group" aria-label="Time range">
              <button type="button" class="lw-range-btn" data-range="1Y" onclick="setMyDashRange('${{cardId}}', '1Y', this)">1Y</button>
              <button type="button" class="lw-range-btn" data-range="3Y" onclick="setMyDashRange('${{cardId}}', '3Y', this)">3Y</button>
              <button type="button" class="lw-range-btn" data-range="5Y" onclick="setMyDashRange('${{cardId}}', '5Y', this)">5Y</button>
              <button type="button" class="lw-range-btn" data-range="10Y" onclick="setMyDashRange('${{cardId}}', '10Y', this)">10Y</button>
              <button type="button" class="lw-range-btn active" data-range="ALL" onclick="setMyDashRange('${{cardId}}', 'ALL', this)">All</button>
            </div>
            <div class="lw-action-bar">
              <button type="button" class="lw-tool-btn" id="boxbtn-${{cardId}}" title="Box-zoom time range & calculate delta (or hold Shift + drag)" onclick="toggleMyDashBoxZoom('${{cardId}}', this)">🔍</button>
              <button type="button" class="lw-tool-btn" title="Reset zoom (or double-click chart)" onclick="resetMyDashZoom('${{cardId}}')">↺</button>
              <button type="button" class="lw-tool-btn" title="Export card CSV" onclick="exportMyDashCardCSV('${{cardId}}')">CSV</button>
              <button type="button" class="lw-tool-btn" title="Download PNG chart image" onclick="exportMyDashCardPNG('${{cardId}}')">PNG</button>
              <button type="button" class="lw-tool-btn" title="Expand fullscreen" onclick="toggleMyDashFullscreen('${{cardId}}', ${{idx}})">⛶</button>
            </div>
          </div>
          <div class="lw-delta-banner" id="delta-${{cardId}}"></div>
          <div id="${{cardId}}" class="lw-plot-box"></div>
        </div>

        <div class="card-notes-wrap">
          <div class="notes-label">
            <span>${{CURRENT_LANG === 'zh' ? '个人研判 / 观点备忘' : 'Personal Thesis & Trigger Notes'}}</span>
            <span class="notes-saved-indicator" id="saved-badge-${{idx}}">✓ Saved</span>
          </div>
          <textarea class="notes-textarea" id="notes-input-${{idx}}" placeholder="${{CURRENT_LANG === 'zh' ? '记录宏观逻辑、拐点阈值或调仓触发点...' : 'Add macro thesis, inflection trigger, or notes...'}}" oninput="updateItemNotes(${{idx}}, this.value)">${{item.notes || ''}}</textarea>
        </div>
      </div>
    `;
    renderedCards.push({{ html: cardHtml, cardId, idx, country: item.country, id: item.id, observations, title, unit }});

    // Table Row HTML
    const tableRowHtml = `
      <tr>
        <td><strong>${{flag}} ${{item.country}}</strong> <span style="color:var(--text-secondary); font-size:11px;">(${{cName}})</span></td>
        <td><strong>${{title}}</strong></td>
        <td><span style="font-size:11px; text-transform:uppercase;">${{freq}}</span></td>
        <td><code>${{latestDateStr}}</code></td>
        <td><strong style="font-family:var(--font-mono); font-size:13px; color:var(--teal);">${{latestValStr}}</strong> <em style="font-size:10px; color:var(--text-secondary);">${{unit}}</em></td>
        <td style="max-width:320px;">
          <input type="text" class="notes-textarea" style="min-height:28px;" value="${{item.notes || ''}}" placeholder="Add note..." oninput="updateItemNotes(${{idx}}, this.value)">
        </td>
        <td>
          <button class="icon-btn remove" onclick="removeItem(${{idx}})" title="Remove">✕</button>
        </td>
      </tr>
    `;
    renderedTableRows.push(tableRowHtml);
  }}

  Object.keys(MYDASH_CHARTS).forEach(k => {{
    try {{ MYDASH_CHARTS[k].chart.remove(); }} catch (e) {{}}
    delete MYDASH_CHARTS[k];
  }});

  gridContainer.innerHTML = renderedCards.map(c => c.html).join('');
  tableTbody.innerHTML = renderedTableRows.join('');

  renderedCards.forEach(c => {{
    initMyDashCardChart(c);
  }});
}}

function initMyDashCardChart(c) {{
  const plotEl = document.getElementById(c.cardId);
  if (!plotEl || !c.observations.length || typeof LightweightCharts === 'undefined') return;

  // Deduplicate and sort ascending by normalized time
  const byTime = new Map();
  c.observations.forEach(o => {{
    if (o.time && !isNaN(o.value)) byTime.set(o.time, {{ time: o.time, value: o.value, rawDate: o.date }});
  }});
  const data = Array.from(byTime.values()).sort((a, b) => a.time.localeCompare(b.time));
  if (!data.length) return;

  const tooltip = document.createElement('div');
  tooltip.className = 'lw-tooltip';
  plotEl.appendChild(tooltip);

  const selectOverlay = document.createElement('div');
  selectOverlay.className = 'lw-select-overlay';
  plotEl.appendChild(selectOverlay);

  const chart = LightweightCharts.createChart(plotEl, {{
    width: plotEl.clientWidth || 380,
    height: plotEl.clientHeight || 215,
    layout: {{
      background: {{ type: 'solid', color: 'transparent' }},
      textColor: '#737c8c',
      fontFamily: "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif",
      fontSize: 10,
      attributionLogo: false
    }},
    grid: {{
      vertLines: {{ visible: false }},
      horzLines: {{ color: 'rgba(18, 21, 26, 0.06)', style: 0 }}
    }},
    rightPriceScale: {{
      borderVisible: false,
      scaleMargins: {{ top: 0.12, bottom: 0.10 }}
    }},
    timeScale: {{
      borderColor: 'rgba(18, 21, 26, 0.12)',
      rightOffset: 2,
      fixLeftEdge: true,
      fixRightEdge: true
    }},
    localization: {{
      priceFormatter: (val) => formatVal(val, 2)
    }},
    crosshair: {{
      mode: 0,
      vertLine: {{ color: 'rgba(18, 21, 26, 0.25)', width: 1, style: 2, labelBackgroundColor: '#12151a' }},
      horzLine: {{ color: 'rgba(18, 21, 26, 0.25)', width: 1, style: 2, labelBackgroundColor: '#12151a' }}
    }},
    handleScroll: {{
      mouseWheel: false,
      pressedMouseMove: true,
      horzTouchDrag: true,
      vertTouchDrag: false
    }},
    handleScale: {{
      mouseWheel: false,
      pinch: true,
      axisPressedMouseMove: {{ time: true, price: true }},
      axisDoubleClickReset: {{ time: true, price: true }}
    }}
  }});

  const mainSeries = chart.addAreaSeries({{
    lineColor: '#0d7680',
    topColor: 'rgba(13, 118, 128, 0.16)',
    bottomColor: 'rgba(13, 118, 128, 0.01)',
    lineWidth: 2,
    priceLineVisible: false,
    lastValueVisible: true
  }});
  mainSeries.setData(data.map(d => ({{ time: d.time, value: d.value }})));

  // Mean & zero reference lines
  const vals = data.map(d => d.value);
  const avg = vals.reduce((a, b) => a + b, 0) / vals.length;
  mainSeries.createPriceLine({{
    price: avg,
    color: '#6E665B',
    lineWidth: 1,
    lineStyle: 2,
    axisLabelVisible: false,
    title: `Avg ${{formatVal(avg, 1)}}`
  }});
  if (Math.min(...vals) < 0 && Math.max(...vals) > 0) {{
    mainSeries.createPriceLine({{
      price: 0,
      color: '#12151a',
      lineWidth: 1,
      lineStyle: 0,
      axisLabelVisible: false,
      title: ''
    }});
  }}

  chart.timeScale().fitContent();

  // Crosshair tooltip
  chart.subscribeCrosshairMove(param => {{
    if (!param.time || !param.point || param.point.x < 0 || param.point.y < 0) {{
      tooltip.style.display = 'none';
      return;
    }}
    const sv = param.seriesData.get(mainSeries);
    if (!sv || sv.value === undefined) {{
      tooltip.style.display = 'none';
      return;
    }}
    const tStr = typeof param.time === 'string'
      ? param.time
      : `${{param.time.year}}-${{String(param.time.month).padStart(2, '0')}}-${{String(param.time.day).padStart(2, '0')}}`;
    tooltip.innerHTML = `<div style="font-weight:700;color:#12151a;">${{tStr}}</div>` +
      `<div style="color:#0d7680;font-family:var(--font-mono);font-weight:700;">${{formatVal(sv.value, 2)}} ${{c.unit}}</div>`;
    tooltip.style.display = 'block';
  }});

  // Ctrl/Cmd + wheel zoom
  plotEl.addEventListener('wheel', e => {{
    if (!(e.ctrlKey || e.metaKey)) return;
    e.preventDefault();
    const vr = chart.timeScale().getVisibleLogicalRange();
    if (!vr) return;
    const span = vr.to - vr.from;
    if (span <= 2 && e.deltaY < 0) return;
    const factor = e.deltaY < 0 ? 0.82 : 1.22;
    const center = (vr.from + vr.to) / 2;
    const half = (span * factor) / 2;
    chart.timeScale().setVisibleLogicalRange({{ from: center - half, to: center + half }});
  }}, {{ passive: false }});

  // Shift + drag or 🔍 box-zoom with Range Delta
  let dragStartX = null;
  plotEl.addEventListener('mousedown', e => {{
    const st = MYDASH_CHARTS[c.cardId];
    if (!st || !(st.boxZoomActive || e.shiftKey)) return;
    const rect = plotEl.getBoundingClientRect();
    dragStartX = e.clientX - rect.left;
    chart.applyOptions({{ handleScroll: {{ pressedMouseMove: false }} }});
    selectOverlay.style.left = `${{dragStartX}}px`;
    selectOverlay.style.width = '0px';
    selectOverlay.style.display = 'block';
  }});
  window.addEventListener('mousemove', e => {{
    if (dragStartX === null) return;
    const rect = plotEl.getBoundingClientRect();
    const curX = Math.max(0, Math.min(rect.width, e.clientX - rect.left));
    selectOverlay.style.left = `${{Math.min(dragStartX, curX)}}px`;
    selectOverlay.style.width = `${{Math.abs(curX - dragStartX)}}px`;
  }});
  window.addEventListener('mouseup', e => {{
    if (dragStartX === null) return;
    const rect = plotEl.getBoundingClientRect();
    const endX = Math.max(0, Math.min(rect.width, e.clientX - rect.left));
    const x1 = Math.min(dragStartX, endX);
    const x2 = Math.max(dragStartX, endX);
    dragStartX = null;
    selectOverlay.style.display = 'none';
    const st = MYDASH_CHARTS[c.cardId];
    if (!st || !st.boxZoomActive) {{
      chart.applyOptions({{ handleScroll: {{ pressedMouseMove: true }} }});
    }}
    if (x2 - x1 < 12) return;
    const l1 = chart.timeScale().coordinateToLogical(x1);
    const l2 = chart.timeScale().coordinateToLogical(x2);
    if (l1 !== null && l2 !== null && l2 > l1) {{
      chart.timeScale().setVisibleLogicalRange({{ from: l1, to: l2 }});
      updateMyDashDeltaBanner(c.cardId, l1, l2);
    }}
  }});

  plotEl.addEventListener('dblclick', () => resetMyDashZoom(c.cardId));

  const ro = new ResizeObserver(entries => {{
    for (const entry of entries) {{
      if (entry.contentRect.width > 0) {{
        chart.applyOptions({{
          width: entry.contentRect.width,
          height: plotEl.clientHeight || 215
        }});
      }}
    }}
  }});
  ro.observe(plotEl);

  MYDASH_CHARTS[c.cardId] = {{
    chart,
    mainSeries,
    data,
    meta: c,
    boxZoomActive: false
  }};

  if (CURRENT_GLOBAL_RANGE && CURRENT_GLOBAL_RANGE !== 'ALL') {{
    const btn = document.querySelector(`#wrap-${{c.cardId}} .lw-range-btn[data-range="${{CURRENT_GLOBAL_RANGE}}"]`);
    setMyDashRange(c.cardId, CURRENT_GLOBAL_RANGE, btn);
  }}
}}

function setMyDashRange(cardId, rangeKey, btnEl) {{
  const st = MYDASH_CHARTS[cardId];
  if (!st || !st.data.length) return;
  const wrap = document.getElementById(`wrap-${{cardId}}`);
  if (wrap && btnEl) {{
    wrap.querySelectorAll('.lw-range-btn').forEach(b => b.classList.remove('active'));
    btnEl.classList.add('active');
  }}
  if (rangeKey === 'ALL') {{
    st.chart.timeScale().fitContent();
    const banner = document.getElementById(`delta-${{cardId}}`);
    if (banner) banner.classList.remove('active');
    return;
  }}
  const yearsMap = {{ '1Y': 1, '3Y': 3, '5Y': 5, '10Y': 10 }};
  const yrs = yearsMap[rangeKey] || 5;
  const maxIso = st.data[st.data.length - 1].time;
  const parts = maxIso.split('-').map(Number);
  const fromIso = `${{parts[0] - yrs}}-${{String(parts[1] || 1).padStart(2, '0')}}-${{String(parts[2] || 1).padStart(2, '0')}}`;
  try {{
    st.chart.timeScale().setVisibleRange({{ from: fromIso, to: maxIso }});
    const vr = st.chart.timeScale().getVisibleLogicalRange();
    if (vr) updateMyDashDeltaBanner(cardId, vr.from, vr.to);
  }} catch (e) {{
    st.chart.timeScale().fitContent();
  }}
}}

function applyGlobalMyDashRange(rangeKey, btnEl) {{
  CURRENT_GLOBAL_RANGE = rangeKey;
  document.querySelectorAll('.mydash-global-range').forEach(b => b.classList.remove('active'));
  if (btnEl) btnEl.classList.add('active');
  Object.keys(MYDASH_CHARTS).forEach(cardId => {{
    const cardBtn = document.querySelector(`#wrap-${{cardId}} .lw-range-btn[data-range="${{rangeKey}}"]`);
    setMyDashRange(cardId, rangeKey, cardBtn);
  }});
}}

function toggleMyDashBoxZoom(cardId, btnEl) {{
  const st = MYDASH_CHARTS[cardId];
  if (!st) return;
  st.boxZoomActive = !st.boxZoomActive;
  if (btnEl) btnEl.classList.toggle('active', st.boxZoomActive);
  const plotEl = document.getElementById(cardId);
  if (plotEl) plotEl.classList.toggle('box-zoom-cursor', st.boxZoomActive);
  st.chart.applyOptions({{ handleScroll: {{ pressedMouseMove: !st.boxZoomActive }} }});
}}

function resetMyDashZoom(cardId) {{
  const st = MYDASH_CHARTS[cardId];
  if (!st) return;
  st.boxZoomActive = false;
  const boxBtn = document.getElementById(`boxbtn-${{cardId}}`);
  if (boxBtn) boxBtn.classList.remove('active');
  const plotEl = document.getElementById(cardId);
  if (plotEl) plotEl.classList.remove('box-zoom-cursor');
  st.chart.applyOptions({{ handleScroll: {{ pressedMouseMove: true }} }});
  st.chart.timeScale().fitContent();
  const banner = document.getElementById(`delta-${{cardId}}`);
  if (banner) banner.classList.remove('active');
  const wrap = document.getElementById(`wrap-${{cardId}}`);
  if (wrap) {{
    wrap.querySelectorAll('.lw-range-btn').forEach(b => b.classList.toggle('active', b.getAttribute('data-range') === 'ALL'));
  }}
}}

function updateMyDashDeltaBanner(cardId, fromLogical, toLogical) {{
  const st = MYDASH_CHARTS[cardId];
  const banner = document.getElementById(`delta-${{cardId}}`);
  if (!st || !banner || !st.data.length) return;
  const i1 = Math.max(0, Math.min(st.data.length - 1, Math.round(fromLogical)));
  const i2 = Math.max(0, Math.min(st.data.length - 1, Math.round(toLogical)));
  if (i2 <= i1) return;
  const p1 = st.data[i1];
  const p2 = st.data[i2];
  const diff = p2.value - p1.value;
  const sign = diff > 0 ? '+' : '';
  const pct = p1.value !== 0 ? ` (${{diff > 0 ? '+' : ''}}${{((diff / Math.abs(p1.value)) * 100).toFixed(1)}}%)` : '';
  const col = diff >= 0 ? '#0d7680' : '#990f3d';
  banner.innerHTML = `<span><strong>Δ ${{p1.time}} → ${{p2.time}}</strong>: ${{formatVal(p1.value, 2)}} → ${{formatVal(p2.value, 2)}} ` +
    `<strong style="color:${{col}}">${{sign}}${{formatVal(diff, 2)}} ${{st.meta.unit}}${{pct}}</strong></span>` +
    `<button type="button" class="lw-tool-btn" onclick="resetMyDashZoom('${{cardId}}')">✕</button>`;
  banner.classList.add('active');
}}

function exportMyDashCardCSV(cardId) {{
  const st = MYDASH_CHARTS[cardId];
  if (!st) return;
  const rows = [['Date', `${{st.meta.country}}_${{st.meta.id}} (${{st.meta.unit}})`]];
  st.data.forEach(d => rows.push([d.rawDate || d.time, d.value]));
  const csv = rows.map(r => r.join(',')).join('\\n');
  const blob = new Blob([csv], {{ type: 'text/csv;charset=utf-8;' }});
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = `${{st.meta.country}}_${{st.meta.id}}.csv`;
  a.click();
}}

function exportMyDashCardPNG(cardId) {{
  const st = MYDASH_CHARTS[cardId];
  if (!st) return;
  try {{
    const canvas = st.chart.takeScreenshot();
    const out = document.createElement('canvas');
    const padTop = 44;
    out.width = canvas.width;
    out.height = canvas.height + padTop;
    const ctx = out.getContext('2d');
    ctx.fillStyle = '#FFFDFA';
    ctx.fillRect(0, 0, out.width, out.height);
    ctx.fillStyle = '#12151a';
    ctx.font = 'bold 14px -apple-system, BlinkMacSystemFont, sans-serif';
    ctx.fillText(`${{st.meta.country}} · ${{st.meta.title}} (${{st.meta.unit}})`, 14, 26);
    ctx.drawImage(canvas, 0, padTop);
    const a = document.createElement('a');
    a.href = out.toDataURL('image/png');
    a.download = `${{st.meta.country}}_${{st.meta.id}}.png`;
    a.click();
  }} catch (e) {{
    console.error('Screenshot failed:', e);
  }}
}}

function toggleMyDashFullscreen(cardId, idx) {{
  const card = document.getElementById(`card-box-${{idx}}`);
  const plotEl = document.getElementById(cardId);
  const st = MYDASH_CHARTS[cardId];
  if (!card || !plotEl || !st) return;
  card.classList.toggle('lw-fullscreen');
  setTimeout(() => {{
    st.chart.applyOptions({{
      width: plotEl.clientWidth || 380,
      height: plotEl.clientHeight || 215
    }});
    st.chart.timeScale().fitContent();
  }}, 60);
}}

function switchView(view) {{
  CURRENT_VIEW = view;
  document.getElementById('view-grid-btn').classList.toggle('active', view === 'grid');
  document.getElementById('view-table-btn').classList.toggle('active', view === 'table');
  if (view === 'grid') {{
    document.getElementById('watchlist-grid').style.display = 'grid';
    document.getElementById('table-view-wrap').style.display = 'none';
    window.dispatchEvent(new Event('resize'));
  }} else {{
    document.getElementById('watchlist-grid').style.display = 'none';
    document.getElementById('table-view-wrap').style.display = 'block';
  }}
}}

// --- Item Mutations ---
function updateItemNotes(idx, notes) {{
  if (WATCHLIST[idx]) {{
    WATCHLIST[idx].notes = notes;
    saveWatchlistToStorage();
    const badge = document.getElementById(`saved-badge-${{idx}}`);
    if (badge) {{
      badge.style.display = 'inline';
      setTimeout(() => {{ badge.style.display = 'none'; }}, 1200);
    }}
  }}
}}

function moveItem(idx, direction) {{
  const target = idx + direction;
  if (target < 0 || target >= WATCHLIST.length) return;
  const temp = WATCHLIST[idx];
  WATCHLIST[idx] = WATCHLIST[target];
  WATCHLIST[target] = temp;
  saveWatchlistToStorage();
  renderDashboard();
}}

function removeItem(idx) {{
  WATCHLIST.splice(idx, 1);
  saveWatchlistToStorage();
  renderDashboard();
  showToast(CURRENT_LANG === 'zh' ? '已从自选看板移除' : 'Removed from Watchlist');
}}

// --- Modal Add Indicator ---
function openAddModal() {{
  document.getElementById('add-modal').style.display = 'flex';
  filterModalResults();
}}

function closeAddModal() {{
  document.getElementById('add-modal').style.display = 'none';
}}

function populateCountrySelect() {{
  const select = document.getElementById('modal-country-select');
  COUNTRY_NAV.forEach(([code, nameEn, nameZh]) => {{
    const opt = document.createElement('option');
    opt.value = code;
    opt.textContent = `${{code}} · ${{nameEn}} (${{nameZh}})`;
    select.appendChild(opt);
  }});
}}

function filterModalResults() {{
  const resultsContainer = document.getElementById('modal-results-list');
  if (!CATALOG || !CATALOG.countries) {{
    resultsContainer.innerHTML = '<div style="text-align:center; padding:30px; color:var(--text-secondary);">Catalog not available.</div>';
    return;
  }}

  const countryFilter = document.getElementById('modal-country-select').value;
  const keyword = (document.getElementById('modal-search-input').value || '').trim().toLowerCase();

  let matches = [];
  CATALOG.countries.forEach(c => {{
    if (countryFilter !== 'ALL' && c.code !== countryFilter) return;
    (c.indicators || []).forEach(ind => {{
      const matchKey = (ind.label_en + ' ' + (ind.label_zh || '') + ' ' + ind.id + ' ' + (ind.section || '')).toLowerCase();
      if (!keyword || matchKey.includes(keyword)) {{
        matches.push({{
          country: c.code,
          countryName: c.name_en,
          flag: c.flag,
          id: ind.id,
          label_en: ind.label_en,
          label_zh: ind.label_zh,
          latest_val: ind.latest_val,
          latest_date: ind.latest_date,
          unit: ind.unit,
          frequency: ind.frequency
        }});
      }}
    }});
  }});

  if (!matches.length) {{
    resultsContainer.innerHTML = `<div style="text-align:center; padding:30px; color:var(--text-secondary); font-size:12px;">${{CURRENT_LANG === 'zh' ? '无匹配指标' : 'No matching indicators found.'}}</div>`;
    return;
  }}

  // Render first 60 matches
  const html = matches.slice(0, 60).map(m => {{
    const isPinned = WATCHLIST.some(item => item.country === m.country && item.id === m.id);
    const title = CURRENT_LANG === 'zh' ? (m.label_zh || m.label_en) : m.label_en;
    const btnHtml = isPinned
      ? `<span style="font-size:11px; color:var(--teal); font-weight:600;">✓ ${{CURRENT_LANG === 'zh' ? '已在自选' : 'Pinned'}}</span>`
      : `<button class="btn btn-primary" style="padding:3px 8px; font-size:11px;" onclick="addIndicatorFromModal('${{m.country}}', '${{m.id}}')">+ ${{CURRENT_LANG === 'zh' ? '添加' : 'Pin'}}</button>`;

    return `
      <div class="result-item">
        <div class="result-info">
          <div class="result-title">${{m.flag}} ${{title}} <span style="font-size:10.5px; font-weight:400; color:var(--text-secondary);">(${'{'}m.country{'}'} · ${{m.id}})</span></div>
          <div class="result-sub">
            <span>${{CURRENT_LANG === 'zh' ? '最新值' : 'Latest'}}: <strong>${{m.latest_val != null ? m.latest_val : 'n/a'}} ${{m.unit || ''}}</strong></span>
            <span>· ${{m.latest_date || ''}}</span>
            <span>· ${{m.frequency || ''}}</span>
          </div>
        </div>
        <div>${{btnHtml}}</div>
      </div>
    `;
  }}).join('');

  resultsContainer.innerHTML = html;
}}

function addIndicatorFromModal(country, id) {{
  if (WATCHLIST.some(item => item.country === country && item.id === id)) return;
  WATCHLIST.push({{
    type: 'indicator',
    country: country,
    id: id,
    notes: ''
  }});
  saveWatchlistToStorage();
  filterModalResults();
  renderDashboard();
  showToast(CURRENT_LANG === 'zh' ? '已成功添加到自选看板！' : 'Indicator pinned to your Dashboard!');
}}

// --- Export & Import ---
function exportWatchlistJSON() {{
  const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(WATCHLIST, null, 2));
  const a = document.createElement('a');
  a.setAttribute("href", dataStr);
  a.setAttribute("download", `macro_dashboard_watchlist_${{new Date().toISOString().slice(0,10)}}.json`);
  document.body.appendChild(a);
  a.click();
  a.remove();
  showToast(CURRENT_LANG === 'zh' ? '自选配置已导出' : 'Watchlist config exported');
}}

function importWatchlistJSON(event) {{
  const file = event.target.files[0];
  if (!file) return;
  const reader = new FileReader();
  reader.onload = (e) => {{
    try {{
      const imported = JSON.parse(e.target.result);
      if (Array.isArray(imported)) {{
        WATCHLIST = imported;
        saveWatchlistToStorage();
        renderDashboard();
        showToast(CURRENT_LANG === 'zh' ? '自选配置导入成功！' : 'Watchlist restored successfully!');
      }} else {{
        alert('Invalid watchlist format.');
      }}
    }} catch (err) {{
      alert('Failed to parse JSON file.');
    }}
  }};
  reader.readAsText(file);
}}

async function exportWatchlistCSV() {{
  showToast(CURRENT_LANG === 'zh' ? '正在准备 CSV 数据导出...' : 'Preparing CSV timeseries export...');
  let csv = '# East Meridian Macro Dashboard - Pinned Watchlist Export\\n';
  csv += '# Generated: ' + new Date().toISOString() + '\\n';
  csv += 'Country,Indicator_ID,Indicator_Name,Date,Value,Unit\\n';

  for (const item of WATCHLIST) {{
    const s = await resolveIndicatorData(item.country, item.id);
    if (s && s.observations) {{
      const label = (s.label_en || item.id).replace(/,/g, ' ');
      const unit = (s.unit || '').replace(/,/g, ' ');
      s.observations.forEach(o => {{
        const dt = Array.isArray(o) ? o[0] : o.date;
        const val = Array.isArray(o) ? o[1] : o.value;
        if (dt && val != null) {{
          csv += `${{item.country}},${{item.id}},"${{label}}",${{dt}},${{val}},"${{unit}}"\\n`;
        }}
      }});
    }}
  }}

  const blob = new Blob([csv], {{ type: 'text/csv;charset=utf-8;' }});
  const link = document.createElement("a");
  const url = URL.createObjectURL(blob);
  link.setAttribute("href", url);
  link.setAttribute("download", `macro_watchlist_data_${{new Date().toISOString().slice(0,10)}}.csv`);
  document.body.appendChild(link);
  link.click();
  link.remove();
  showToast(CURRENT_LANG === 'zh' ? 'CSV 导出完成！' : 'CSV download completed!');
}}

function showToast(msg) {{
  const t = document.getElementById('toast');
  t.textContent = msg;
  t.classList.add('show');
  setTimeout(() => {{ t.classList.remove('show'); }}, 2500);
}}
</script>
</body>
</html>
"""


def build() -> Path:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    html_content = build_my_dashboard_html()
    
    out_file = OUTPUT / "my_dashboard.html"
    out_file.write_text(html_content, encoding="utf-8")
    print(f"Wrote {out_file} ({len(html_content):,} bytes)")

    root_file = ROOT / "my_dashboard.html"
    root_file.write_text(html_content, encoding="utf-8")
    print(f"Wrote {root_file} ({len(html_content):,} bytes)")

    return out_file


if __name__ == "__main__":
    build()
