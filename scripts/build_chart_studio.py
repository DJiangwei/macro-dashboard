#!/usr/bin/env python3
"""Build the Macro Chart Studio page and indicator catalog in Financial Times (FT) & Claude UI style.

Outputs:
  output/chart_studio_catalog.json
  output/chart_studio.html
  chart_studio.html
  chart_studio_catalog.json
"""
from __future__ import annotations

import json
from pathlib import Path
import shutil
import sys

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

# FT High-Contrast Multi-Series Palette
FT_PALETTE = [
    "#990f3d",  # 1. FT Claret / Burgundy
    "#0d7680",  # 2. FT Teal / Petrol Blue
    "#d97706",  # 3. Claude Terracotta / Warm Amber
    "#364b61",  # 4. FT Slate Navy
    "#593380",  # 5. FT Plum / Deep Violet
]

PRESETS = [
    {
        "id": "us_cn_10y_spread",
        "title_en": "US vs China 10Y Sovereign Yield & Spread",
        "title_zh": "中美 10 年期国债收益率与利差对比",
        "description_zh": "全球两大经济体基准无风险利率与跨境利差走势对比。",
        "description_en": "Benchmark 10Y sovereign yields for US and China with capital flow spread dynamics.",
        "transform": "raw",
        "date_range": "5y",
        "series": [
            {"country": "US", "id": "sovereign_yield_10y", "axis": "left", "color": "#990f3d", "label": "US 10Y Treasury"},
            {"country": "CN", "id": "gov_bond_yield_10y_akshare", "axis": "left", "color": "#0d7680", "label": "China 10Y Gov Bond"}
        ]
    },
    {
        "id": "central_bank_rates",
        "title_en": "Major Central Bank Policy Rates (Fed, ECB, BOJ, BOE)",
        "title_zh": "主要央行基准政策利率对比 (美联储/欧央行/日银/英格兰银行)",
        "description_zh": "全球核心央行货币政策周期、加息与降息节奏同屏对比。",
        "description_en": "Global major central bank benchmark policy rates and monetary easing cycles.",
        "transform": "raw",
        "date_range": "5y",
        "series": [
            {"country": "US", "id": "policy_rate", "axis": "left", "color": "#990f3d", "label": "Fed Funds Target Rate"},
            {"country": "EA", "id": "deposit_facility_rate", "axis": "left", "color": "#0d7680", "label": "ECB Deposit Facility Rate"},
            {"country": "UK", "id": "policy_rate", "axis": "left", "color": "#364b61", "label": "BOE Official Bank Rate"},
            {"country": "JP", "id": "overnight_call_rate", "axis": "left", "color": "#d97706", "label": "BOJ Overnight Rate"}
        ]
    },
    {
        "id": "kr_tw_tech_momentum",
        "title_en": "Korea KOSPI vs Taiwan TAIEX Equity Momentum (Base = 100)",
        "title_zh": "韩国 KOSPI vs 台湾 TAIEX 股指走势 (基期归一化 = 100)",
        "description_zh": "东亚半导体与科技出口核心股指累计收益率走势归一化对比。",
        "description_en": "Normalized equity return comparison for East Asian semiconductor powerhouses.",
        "transform": "rebase",
        "date_range": "3y",
        "series": [
            {"country": "KR", "id": "kospi_stock_index", "axis": "left", "color": "#990f3d", "label": "Korea KOSPI Composite"},
            {"country": "TW", "id": "taiex_index", "axis": "left", "color": "#0d7680", "label": "Taiwan TAIEX Index"}
        ]
    },
    {
        "id": "em_inflation_defense",
        "title_en": "EM Monetary Defense: Turkey vs Egypt vs Nigeria Policy Rates",
        "title_zh": "新兴市场利率防线：土耳其 vs 埃及 vs 尼日利亚 政策利率",
        "description_zh": "高通胀新兴市场央行基准借贷与回购政策利率横向对比。",
        "description_en": "Central bank policy rate defense across high-inflation emerging markets.",
        "transform": "raw",
        "date_range": "5y",
        "series": [
            {"country": "TR", "id": "policy_rate", "axis": "left", "color": "#990f3d", "label": "Turkey One-Week Repo Rate"},
            {"country": "EG", "id": "policy_rate", "axis": "left", "color": "#0d7680", "label": "Egypt CBE Corridor Rate"},
            {"country": "NG", "id": "policy_rate", "axis": "left", "color": "#d97706", "label": "Nigeria Monetary Policy Rate"}
        ]
    },
    {
        "id": "oil_producers_brent",
        "title_en": "Kazakhstan & Nigeria Oil Production (Left) vs Brent Crude (Right)",
        "title_zh": "哈萨克与尼日利亚原油月产 (左轴) vs 布伦特油价 (右轴)",
        "description_zh": "主要产油国原油日产量（千桶/日）与国际现货油价双轴联动对比。",
        "description_en": "Crude oil output for key producers compared against Brent crude spot price.",
        "transform": "raw",
        "date_range": "5y",
        "series": [
            {"country": "KZ", "id": "crude_oil_production_eia", "axis": "left", "color": "#990f3d", "label": "Kazakhstan Crude Output"},
            {"country": "NG", "id": "crude_oil_production_eia", "axis": "left", "color": "#0d7680", "label": "Nigeria Crude Output"},
            {"country": "KZ", "id": "brent_crude_oil_spot_eia", "axis": "right", "color": "#364b61", "label": "Brent Crude Price ($/bbl)"}
        ]
    }
]


def generate_catalog() -> dict:
    """Scan all canonical frames and compile a compact, search-optimized catalog."""
    countries = []

    for code, (name_en, name_zh, cfile, flag) in COUNTRY_MAP.items():
        frame_path = OUTPUT / cfile
        if not frame_path.exists():
            continue

        try:
            with open(frame_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            print(f"Warning: could not read {frame_path}: {e}", file=sys.stderr)
            continue

        c_indicators = []
        if cfile == "cee_canonical_frame.json":
            series_list = [s for s in data.get("series", []) if s.get("country") == code]
        else:
            series_list = data.get("series", [])

        for s in series_list:
            iid = s.get("indicator_id") or s.get("id")
            if not iid:
                continue

            meta = s.get("metadata", {}) or s
            label_en = s.get("label_en") or meta.get("label_en") or s.get("label") or iid
            label_zh = s.get("label_zh") or meta.get("label_zh") or label_en
            unit = s.get("unit") or meta.get("unit") or ""
            section = s.get("section") or meta.get("section") or "macro"
            freq = s.get("frequency") or meta.get("frequency") or "M"

            obs = s.get("observations", [])
            latest_date = obs[-1][0] if obs else ""
            latest_val = obs[-1][1] if obs else None

            c_indicators.append({
                "id": str(iid),
                "label_en": label_en,
                "label_zh": label_zh,
                "unit": unit,
                "section": section,
                "frequency": freq,
                "obs_count": len(obs),
                "latest_date": str(latest_date),
                "latest_val": latest_val,
            })
        countries.append({
            "code": code,
            "name_en": name_en,
            "name_zh": name_zh,
            "flag": flag,
            "canonical_file": cfile,
            "indicator_count": len(c_indicators),
            "indicators": c_indicators,
        })

    return {
        "generated": "2026-10-29",
        "total_countries": len(countries),
        "total_indicators": sum(c["indicator_count"] for c in countries),
        "countries": countries,
        "presets": PRESETS,
    }


def render_html() -> str:
    nav_links = []
    for code, name, name_zh, cfile in COUNTRY_NAV:
        nav_links.append(f'<a href="{cfile}" title="{name} ({name_zh})">{code}</a>')
    country_nav_html = "\n    ".join(nav_links)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Macro Chart Studio · 宏观多指标对比工坊</title>
  <script src="https://cdn.plot.ly/plotly-2.32.0.min.js"></script>
  <style>
    :root {{
      --bg-canvas: #fcfaf7;
      --bg-surface: #ffffff;
      --bg-deep: #f7f5f0;
      --bg-muted: #f4efe7;
      --fg: #12151a;
      --text-secondary: #4b525f;
      --muted: #737c8c;
      --accent: #990f3d;
      --accent-soft: rgba(153, 15, 61, 0.08);
      --claude-accent: #8a593d;
      --claude-soft: rgba(138, 89, 61, 0.10);
      --teal: #0d7680;
      --teal-soft: rgba(13, 118, 128, 0.08);
      --border: rgba(18, 21, 26, 0.08);
      --border-strong: rgba(18, 21, 26, 0.16);
      --border-focus: #990f3d;
      --font-display: "Newsreader", "Iowan Old Style", "Songti SC", "Noto Serif SC", Georgia, serif;
      --font-body: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", "Hiragino Sans GB", "Noto Sans SC", "Helvetica Neue", Arial, sans-serif;
      --radius: 4px;
      --shadow-sm: 0 1px 2px 0 rgba(0, 0, 0, 0.03);
    }}
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    html {{ scroll-behavior: smooth; }}
    html[lang="en"] [data-lang="zh"] {{ display: none !important; }}
    html[lang="zh"] [data-lang="en"] {{ display: none !important; }}
    body {{
      font-family: var(--font-body);
      background: var(--bg-canvas);
      color: var(--fg);
      font-size: 14px;
      line-height: 1.6;
      -webkit-font-smoothing: antialiased;
      padding-bottom: 60px;
    }}
    a {{ color: inherit; }}

    /* Topbar Navigation (FT/Claude Specification) */
    .topbar {{
      position: sticky;
      top: 0;
      z-index: 50;
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 16px;
      padding: 10px 32px;
      background: rgba(252, 250, 247, 0.95);
      border-bottom: 1px solid var(--border);
      backdrop-filter: blur(12px);
      font-size: 12px;
    }}
    .brand {{
      font-family: var(--font-display);
      font-size: 16px;
      font-weight: 600;
      letter-spacing: -0.01em;
      white-space: nowrap;
      text-decoration: none;
    }}
    .brand span {{ color: var(--accent); }}
    .country-nav {{ display: flex; gap: 4px; flex-wrap: wrap; align-items: center; }}
    .country-nav a {{
      text-decoration: none;
      color: var(--muted);
      border: 1px solid transparent;
      border-radius: var(--radius);
      padding: 3px 8px;
      font-size: 11px;
      font-weight: 500;
      transition: all 0.15s ease;
    }}
    .country-nav a:hover {{ background: rgba(18, 21, 26, 0.04); color: var(--fg); }}
    .country-nav a.active {{ background: var(--fg); color: #ffffff; border-color: var(--fg); font-weight: 600; }}
    .topbar-actions {{ display: flex; align-items: center; gap: 8px; }}
    .topbar-btn {{
      border: 1px solid var(--border);
      background: #ffffff;
      color: var(--fg);
      padding: 4px 10px;
      border-radius: var(--radius);
      font-size: 11px;
      font-weight: 500;
      cursor: pointer;
      text-decoration: none;
      transition: all 0.15s ease;
    }}
    .topbar-btn:hover {{ border-color: var(--border-strong); background: #fcfaf7; }}

    /* Layout Container */
    .container {{
      max-width: 1400px;
      margin: 0 auto;
      padding: 32px 24px;
    }}

    /* Studio Editorial Header */
    .studio-header {{
      border-bottom: 1px solid var(--border);
      padding-bottom: 24px;
      margin-bottom: 24px;
    }}
    .eyebrow {{
      color: var(--accent);
      font-size: 11px;
      font-weight: 600;
      letter-spacing: 0.05em;
      text-transform: uppercase;
      margin-bottom: 6px;
    }}
    h1 {{
      font-family: var(--font-display);
      font-size: clamp(30px, 4vw, 44px);
      font-weight: 600;
      line-height: 1.1;
      letter-spacing: -0.025em;
      margin: 0 0 10px;
    }}
    .subtitle {{
      color: var(--text-secondary);
      font-size: 15px;
      max-width: 900px;
      line-height: 1.6;
      margin-bottom: 16px;
    }}
    .meta-row {{
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
    }}
    .meta-chip {{
      background: #ffffff;
      border: 1px solid var(--border);
      border-radius: var(--radius);
      padding: 6px 12px;
      font-size: 12px;
      color: var(--text-secondary);
      box-shadow: var(--shadow-sm);
      display: inline-flex;
      align-items: center;
      gap: 6px;
    }}
    .meta-chip strong {{ color: var(--fg); font-weight: 700; }}

    /* Presets Panel (FT Curated Topics) */
    .section-card {{
      background: #ffffff;
      border: 1px solid var(--border);
      border-top: 3px solid var(--border-strong);
      border-radius: var(--radius);
      padding: 18px 20px;
      margin-bottom: 24px;
      box-shadow: var(--shadow-sm);
    }}
    .card-header {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 14px;
      flex-wrap: wrap;
      gap: 8px;
    }}
    .card-title {{
      font-family: var(--font-display);
      font-size: 18px;
      font-weight: 600;
      color: var(--fg);
      display: flex;
      align-items: center;
      gap: 8px;
    }}
    .card-desc {{
      font-size: 12px;
      color: var(--muted);
    }}
    .presets-list {{
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
    }}
    .preset-pill {{
      background: #fcfaf7;
      border: 1px solid var(--border);
      padding: 6px 12px;
      border-radius: 3px;
      font-size: 12px;
      font-weight: 500;
      cursor: pointer;
      display: inline-flex;
      align-items: center;
      gap: 6px;
      transition: all 0.15s ease;
      user-select: none;
      color: var(--fg);
    }}
    .preset-pill:hover {{
      background: var(--accent-soft);
      border-color: rgba(153, 15, 61, 0.3);
      color: var(--accent);
      transform: translateY(-1px);
    }}
    .preset-pill span.star {{ color: var(--claude-accent); font-size: 11px; }}

    /* Workspace Grid */
    .studio-workspace {{
      display: grid;
      grid-template-columns: 380px 1fr;
      gap: 24px;
      align-items: start;
    }}
    @media (max-width: 1080px) {{
      .studio-workspace {{ grid-template-columns: 1fr; }}
    }}

    /* Sidebar Controls Panel */
    .controls-panel {{
      background: #ffffff;
      border: 1px solid var(--border);
      border-top: 3px solid var(--accent);
      border-radius: var(--radius);
      padding: 18px;
      box-shadow: var(--shadow-sm);
      display: flex;
      flex-direction: column;
      gap: 18px;
    }}
    .series-list {{ display: flex; flex-direction: column; gap: 12px; }}
    .series-card {{
      background: #fcfaf7;
      border: 1px solid var(--border);
      border-radius: var(--radius);
      padding: 12px 14px;
      transition: border-color 0.15s ease;
    }}
    .series-card:hover {{ border-color: var(--border-strong); }}
    .series-card-top {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 8px;
    }}
    .series-tag {{
      display: inline-flex;
      align-items: center;
      gap: 6px;
      font-size: 11px;
      font-weight: 600;
      letter-spacing: 0.02em;
    }}
    .series-color-bullet {{
      width: 10px;
      height: 10px;
      border-radius: 50%;
      display: inline-block;
    }}
    .remove-btn {{
      background: transparent;
      border: none;
      color: var(--muted);
      cursor: pointer;
      font-size: 15px;
      line-height: 1;
      padding: 2px 4px;
      border-radius: 3px;
      transition: color 0.15s ease;
    }}
    .remove-btn:hover {{ color: var(--accent); }}

    .form-row {{ display: grid; grid-template-columns: 1fr 1fr; gap: 8px; margin-bottom: 8px; }}
    .form-group {{ margin-bottom: 8px; }}
    .form-label {{
      display: block;
      font-size: 11px;
      font-weight: 600;
      color: var(--text-secondary);
      margin-bottom: 4px;
      text-transform: uppercase;
      letter-spacing: 0.03em;
    }}
    select, input[type="text"] {{
      width: 100%;
      padding: 6px 9px;
      background: #ffffff;
      border: 1px solid var(--border);
      border-radius: var(--radius);
      font-size: 12px;
      color: var(--fg);
      font-family: var(--font-body);
      outline: none;
      transition: border-color 0.15s ease;
    }}
    select:focus, input:focus {{ border-color: var(--accent); }}

    /* Segmented Button Group (FT Style) */
    .segmented-group {{
      display: inline-flex;
      background: #f7f5f0;
      border: 1px solid var(--border);
      border-radius: var(--radius);
      padding: 2px;
      width: 100%;
    }}
    .segmented-btn {{
      flex: 1;
      text-align: center;
      padding: 4px 6px;
      font-size: 11px;
      font-weight: 500;
      cursor: pointer;
      border: none;
      background: transparent;
      color: var(--muted);
      border-radius: 3px;
      user-select: none;
      transition: all 0.15s ease;
    }}
    .segmented-btn.active {{
      background: var(--fg);
      color: #ffffff;
      font-weight: 600;
      box-shadow: 0 1px 2px rgba(0,0,0,0.05);
    }}

    .add-btn {{
      width: 100%;
      padding: 9px;
      background: #ffffff;
      border: 1px dashed var(--border-strong);
      border-radius: var(--radius);
      color: var(--accent);
      font-size: 12px;
      font-weight: 600;
      cursor: pointer;
      transition: all 0.15s ease;
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 6px;
    }}
    .add-btn:hover {{
      background: var(--accent-soft);
      border-color: var(--accent);
    }}
    .add-btn:disabled {{ opacity: 0.4; cursor: not-allowed; }}

    /* Canvas Panel */
    .canvas-panel {{
      background: #ffffff;
      border: 1px solid var(--border);
      border-top: 3px solid var(--border-strong);
      border-radius: var(--radius);
      padding: 18px 20px;
      box-shadow: var(--shadow-sm);
      display: flex;
      flex-direction: column;
      gap: 16px;
      position: relative;
    }}
    .canvas-toolbar {{
      display: flex;
      flex-wrap: wrap;
      justify-content: space-between;
      align-items: center;
      gap: 12px;
      border-bottom: 1px solid var(--border);
      padding-bottom: 14px;
    }}
    .toolbar-group {{
      display: flex;
      align-items: center;
      gap: 8px;
    }}
    .tool-label {{
      font-size: 11px;
      font-weight: 600;
      color: var(--text-secondary);
      text-transform: uppercase;
      letter-spacing: 0.03em;
    }}
    .range-group {{
      display: inline-flex;
      background: #f7f5f0;
      border: 1px solid var(--border);
      border-radius: var(--radius);
      padding: 2px;
    }}
    .range-btn {{
      padding: 4px 10px;
      font-size: 11px;
      font-weight: 500;
      color: var(--muted);
      background: transparent;
      border: none;
      border-radius: 3px;
      cursor: pointer;
      transition: all 0.15s ease;
    }}
    .range-btn.active {{
      background: var(--fg);
      color: #ffffff;
      font-weight: 600;
    }}
    .action-button {{
      display: inline-flex;
      align-items: center;
      gap: 5px;
      padding: 5px 11px;
      font-size: 11px;
      font-weight: 500;
      color: var(--fg);
      background: #ffffff;
      border: 1px solid var(--border);
      border-radius: var(--radius);
      cursor: pointer;
      transition: all 0.15s ease;
    }}
    .action-button:hover {{
      background: #fcfaf7;
      border-color: var(--border-strong);
    }}

    #chart-canvas {{
      width: 100%;
      height: 560px;
      min-height: 560px;
    }}

    /* FT Summary Statistics Table */
    .summary-section {{
      margin-top: 10px;
      border-top: 1px solid var(--border);
      padding-top: 14px;
    }}
    .summary-table-wrap {{
      overflow-x: auto;
      border: 1px solid var(--border);
      border-radius: var(--radius);
      background: #ffffff;
    }}
    table.stats-table {{
      width: 100%;
      border-collapse: collapse;
      font-size: 12px;
      font-variant-numeric: tabular-nums;
    }}
    table.stats-table th {{
      text-align: left;
      color: var(--text-secondary);
      font-size: 11px;
      font-weight: 600;
      background: #fcfaf7;
      padding: 8px 12px;
      border-bottom: 1px solid var(--border);
    }}
    table.stats-table td {{
      padding: 9px 12px;
      border-bottom: 1px solid var(--border);
      color: var(--fg);
    }}
    table.stats-table tr:last-child td {{ border-bottom: none; }}
    .table-bullet {{
      display: inline-block;
      width: 8px;
      height: 8px;
      border-radius: 50%;
      margin-right: 6px;
    }}

    .loading-veil {{
      position: absolute;
      top: 0; left: 0; right: 0; bottom: 0;
      background: rgba(252, 250, 247, 0.75);
      backdrop-filter: blur(2px);
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 13px;
      font-weight: 600;
      color: var(--accent);
      z-index: 20;
      border-radius: var(--radius);
    }}

    footer {{
      margin-top: 32px;
      padding-top: 20px;
      border-top: 1px solid var(--border);
      color: var(--muted);
      font-size: 12px;
      display: flex;
      justify-content: space-between;
      flex-wrap: wrap;
      gap: 8px;
    }}
  </style>
</head>
<body data-lang="en">

<!-- Topbar (FT/Claude Specification) -->
<div class="topbar">
  <a href="index.html" class="brand">East Meridian <span>/ Country Primer</span></a>
  <nav class="country-nav" aria-label="country dashboards">
    {country_nav_html}
    <a href="chart_studio.html" class="active" title="Macro Chart Studio · 宏观图表工坊">📈 Studio</a>
  </nav>
  <div class="topbar-actions">
    <a href="index.html" class="topbar-btn">← <span data-lang="en">Archive</span><span data-lang="zh">返回归档</span></a>
    <button class="topbar-btn" onclick="toggleLang()" id="lang-btn">中文</button>
  </div>
</div>

<main class="container">

  <!-- Editorial Header -->
  <header class="studio-header">
    <p class="eyebrow"><span data-lang="en">Macro Chart Studio · Cross-Country Workbench</span><span data-lang="zh">宏观专业图表工坊 · 跨国多序列画板</span></p>
    <h1><span data-lang="en">Interactive Macro Chart Studio</span><span data-lang="zh">多指标自定义对比图表工坊</span></h1>
    <p class="subtitle">
      <span data-lang="en">Overlay up to 5 macroeconomic time series across 18 economies onto a unified canvas. Supports dual Y-axis scaling, base-100 re-indexing, cross-country spread calculation, and publication-quality PNG / CSV exports.</span>
      <span data-lang="zh">在统一画布上自由叠加对比 18 个经济体的至多 5 条宏观时间序列。支持左/右双 Y 轴自由指派、基期 100 归一化发散度对比、跨国跨序列利差差值分析，以及出版级高清图表与 CSV 数据导出。</span>
    </p>
    <div class="meta-row">
      <span class="meta-chip"><strong>18</strong> <span data-lang="en">Economies</span><span data-lang="zh">覆盖经济体</span></span>
      <span class="meta-chip"><strong>1,307</strong> <span data-lang="en">Standardized Series</span><span data-lang="zh">标准化序列</span></span>
      <span class="meta-chip"><strong style="color:var(--accent);">Dual Y-Axis</strong> <span data-lang="en">Independent Scaling</span><span data-lang="zh">双 Y 轴支持</span></span>
      <span class="meta-chip"><strong style="color:var(--teal);">Spread & Rebase</strong> <span data-lang="en">Macro Transforms</span><span data-lang="zh">利差与归一化</span></span>
    </div>
  </header>

  <!-- Curated Presets Bar -->
  <section class="section-card">
    <div class="card-header">
      <div class="card-title">
        <span>★</span>
        <span data-lang="en">Curated Macro Analysis Presets</span><span data-lang="zh">经典宏观专题预设</span>
      </div>
      <div class="card-desc">
        <span data-lang="en">Click any template to instantly load cross-country multi-series configurations</span>
        <span data-lang="zh">点击一键加载典型跨境利差、核心央行政策利率与增长动能对比</span>
      </div>
    </div>
    <div class="presets-list" id="presets-container">
      <!-- Injected via JS -->
    </div>
  </section>

  <!-- Studio Workspace -->
  <div class="studio-workspace">

    <!-- Left Controls Sidebar -->
    <div class="controls-panel">
      <div class="card-header" style="margin-bottom: 0;">
        <div style="font-weight: 600; font-size: 13px;">
          <span data-lang="en">Series Setup (Up to 5)</span>
          <span data-lang="zh">指标配置 (最多 5 条)</span>
        </div>
        <span id="series-counter" style="font-size: 11px; font-weight: 700; color: var(--accent);">2/5</span>
      </div>

      <div class="series-list" id="series-list">
        <!-- Series Cards dynamically rendered -->
      </div>

      <button type="button" class="add-btn" id="add-series-btn" onclick="addSeries()">
        <span>+</span>
        <span data-lang="en">Add Comparison Series</span>
        <span data-lang="zh">添加对比指标</span>
      </button>

      <div style="border-top: 1px solid var(--border); padding-top: 14px;">
        <span class="form-label">
          <span data-lang="en">Transform / Calculation</span>
          <span data-lang="zh">图表计算与变换模式</span>
        </span>
        <div class="segmented-group" id="transform-group">
          <button type="button" class="segmented-btn active" data-transform="raw" onclick="setTransform('raw')">
            <span data-lang="en">Raw Level</span>
            <span data-lang="zh">原始数值</span>
          </button>
          <button type="button" class="segmented-btn" data-transform="rebase" onclick="setTransform('rebase')">
            <span data-lang="en">Base = 100</span>
            <span data-lang="zh">基期归一化</span>
          </button>
          <button type="button" class="segmented-btn" data-transform="spread" onclick="setTransform('spread')">
            <span data-lang="en">Spread (S1-S2)</span>
            <span data-lang="zh">利差分析</span>
          </button>
        </div>
      </div>
    </div>

    <!-- Right Chart Canvas Panel -->
    <div class="canvas-panel">
      <div id="canvas-loading" class="loading-veil" style="display: none;">
        <span>Loading observations & rendering...</span>
      </div>

      <div class="canvas-toolbar">
        <div class="toolbar-group">
          <span class="tool-label"><span data-lang="en">Window:</span><span data-lang="zh">时间窗口:</span></span>
          <div class="range-group" id="range-group">
            <button type="button" class="range-btn" data-range="1y" onclick="setDateRange('1y')">1Y</button>
            <button type="button" class="range-btn" data-range="3y" onclick="setDateRange('3y')">3Y</button>
            <button type="button" class="range-btn active" data-range="5y" onclick="setDateRange('5y')">5Y</button>
            <button type="button" class="range-btn" data-range="10y" onclick="setDateRange('10y')">10Y</button>
            <button type="button" class="range-btn" data-range="max" onclick="setDateRange('max')">Max</button>
          </div>
        </div>

        <div class="toolbar-group">
          <button type="button" class="action-button" onclick="exportPNG()" title="Export high-resolution PNG">
            <span>📷</span>
            <span data-lang="en">Download PNG</span><span data-lang="zh">下载高清图</span>
          </button>
          <button type="button" class="action-button" onclick="exportCSV()" title="Export aligned CSV dataset">
            <span>📥</span>
            <span data-lang="en">Export CSV</span><span data-lang="zh">导出 CSV</span>
          </button>
          <button type="button" class="action-button" onclick="copyShareURL()" title="Copy shareable link with current view state">
            <span>🔗</span>
            <span data-lang="en">Share Link</span><span data-lang="zh">分享链接</span>
          </button>
        </div>
      </div>

      <!-- Plotly Graph Div -->
      <div id="chart-canvas"></div>

      <!-- Statistics Table -->
      <div class="summary-section">
        <div class="card-header">
          <div style="font-weight: 600; font-size: 13px;">
            <span data-lang="en">Active Series Observations & Statistics</span>
            <span data-lang="zh">选定序列关键读数与区间统计</span>
          </div>
        </div>
        <div class="summary-table-wrap">
          <table class="stats-table" id="summary-table">
            <thead>
              <tr>
                <th><span data-lang="en">Series</span><span data-lang="zh">序列 / 指标</span></th>
                <th><span data-lang="en">Country</span><span data-lang="zh">国家</span></th>
                <th><span data-lang="en">Latest Value</span><span data-lang="zh">最新读数</span></th>
                <th><span data-lang="en">Date</span><span data-lang="zh">发布日期</span></th>
                <th><span data-lang="en">Min</span><span data-lang="zh">区间最低</span></th>
                <th><span data-lang="en">Max</span><span data-lang="zh">区间最高</span></th>
                <th><span data-lang="en">Mean</span><span data-lang="zh">区间均值</span></th>
                <th><span data-lang="en">Axis</span><span data-lang="zh">对应坐标轴</span></th>
              </tr>
            </thead>
            <tbody id="summary-table-body">
              <!-- Injected via JS -->
            </tbody>
          </table>
        </div>
      </div>

    </div>

  </div>

  <footer>
    <div>East Meridian Country Primer · Macro Chart Studio · Financial Times & Claude UI Design System.</div>
    <div>Research artefact only, not investment advice.</div>
  </footer>

</main>

<script>
// State Management
let CATALOG = null;
let FRAME_CACHE = {{}};
let ACTIVE_SERIES = [];
let CURRENT_TRANSFORM = 'raw';
let CURRENT_RANGE = '5y';
let CURRENT_LANG = 'en';

const FT_PALETTE = ["#990f3d", "#0d7680", "#d97706", "#364b61", "#593380"];

// Initialization
async function init() {{
  try {{
    const inOutputDir = window.location.pathname.includes('/output/');
    const prefix = inOutputDir ? '' : 'output/';
    let res;
    try {{
      res = await fetch('chart_studio_catalog.json');
      if (!res.ok) res = await fetch(prefix + 'chart_studio_catalog.json');
    }} catch (e) {{
      res = await fetch(prefix + 'chart_studio_catalog.json');
    }}
    CATALOG = await res.json();
    renderPresets();

    // Check URL parameters or hash
    if (window.location.hash && window.location.hash.length > 3) {{
      loadFromHash(window.location.hash);
    }} else {{
      loadPreset(CATALOG.presets[0]);
    }}
  }} catch (err) {{
    console.error("Failed to load catalog:", err);
  }}
}}

function renderPresets() {{
  const container = document.getElementById('presets-container');
  container.innerHTML = '';
  CATALOG.presets.forEach(p => {{
    const btn = document.createElement('div');
    btn.className = 'preset-pill';
    const title = CURRENT_LANG === 'zh' ? p.title_zh : p.title_en;
    btn.innerHTML = `<span class="star">★</span><span>${{title}}</span>`;
    btn.onclick = () => loadPreset(p);
    container.appendChild(btn);
  }});
}}

function loadPreset(preset) {{
  ACTIVE_SERIES = [];
  preset.series.forEach((s, idx) => {{
    ACTIVE_SERIES.push({{
      country: s.country,
      indicatorId: s.id,
      axis: s.axis || 'left',
      color: FT_PALETTE[idx % FT_PALETTE.length],
    }});
  }});
  CURRENT_TRANSFORM = preset.transform || 'raw';
  CURRENT_RANGE = preset.date_range || '5y';

  updateControlsUI();
  refreshChart();
}}

function updateControlsUI() {{
  // Update transform buttons
  document.querySelectorAll('#transform-group .segmented-btn').forEach(btn => {{
    btn.classList.toggle('active', btn.dataset.transform === CURRENT_TRANSFORM);
  }});
  // Update range buttons
  document.querySelectorAll('#range-group .range-btn').forEach(btn => {{
    btn.classList.toggle('active', btn.dataset.range === CURRENT_RANGE);
  }});
  renderSeriesControls();
}}

function renderSeriesControls() {{
  const container = document.getElementById('series-list');
  container.innerHTML = '';
  document.getElementById('series-counter').textContent = `${{ACTIVE_SERIES.length}}/5`;
  document.getElementById('add-series-btn').disabled = ACTIVE_SERIES.length >= 5;

  ACTIVE_SERIES.forEach((item, idx) => {{
    const card = document.createElement('div');
    card.className = 'series-card';
    card.style.borderLeft = `4px solid ${{item.color}}`;

    const cData = CATALOG.countries.find(c => c.code === item.country);
    const countryName = cData ? (CURRENT_LANG === 'zh' ? cData.name_zh : cData.name_en) : item.country;

    // Build country options
    const countryOpts = CATALOG.countries.map(c => {{
      const name = CURRENT_LANG === 'zh' ? c.name_zh : c.name_en;
      return `<option value="${{c.code}}"${{c.code === item.country ? ' selected' : ''}}>${{c.flag}} ${{c.code}} - ${{name}}</option>`;
    }}).join('');

    // Build indicator options
    let indicatorOpts = '';
    if (cData) {{
      const grouped = {{}};
      cData.indicators.forEach(ind => {{
        const sec = ind.section || 'General';
        if (!grouped[sec]) grouped[sec] = [];
        grouped[sec].push(ind);
      }});
      for (const [sec, list] of Object.entries(grouped)) {{
        indicatorOpts += `<optgroup label="${{sec.toUpperCase()}}">`;
        list.forEach(ind => {{
          const label = CURRENT_LANG === 'zh' ? ind.label_zh : ind.label_en;
          indicatorOpts += `<option value="${{ind.id}}"${{ind.id === item.indicatorId ? ' selected' : ''}}>${{label}} (${{ind.unit}})</option>`;
        }});
        indicatorOpts += `</optgroup>`;
      }}
    }}

    card.innerHTML = `
      <div class="series-card-top">
        <div class="series-tag">
          <span class="series-color-bullet" style="background: ${{item.color}};"></span>
          <span>S${{idx + 1}} · ${{cData ? cData.flag : ''}} ${{item.country}}</span>
        </div>
        ${{ACTIVE_SERIES.length > 1 ? `<button type="button" class="remove-btn" onclick="removeSeries(${{idx}})" title="Remove series">✕</button>` : ''}}
      </div>
      <div class="form-row">
        <div>
          <span class="form-label">${{CURRENT_LANG === 'zh' ? '选择国家' : 'Country'}}</span>
          <select onchange="onCountryChange(${{idx}}, this.value)">
            ${{countryOpts}}
          </select>
        </div>
        <div>
          <span class="form-label">${{CURRENT_LANG === 'zh' ? '指派坐标轴' : 'Y-Axis'}}</span>
          <div class="segmented-group">
            <button type="button" class="segmented-btn ${{item.axis === 'left' ? 'active' : ''}}" onclick="setSeriesAxis(${{idx}}, 'left')">Y1 (${{CURRENT_LANG === 'zh' ? '左' : 'Left'}})</button>
            <button type="button" class="segmented-btn ${{item.axis === 'right' ? 'active' : ''}}" onclick="setSeriesAxis(${{idx}}, 'right')">Y2 (${{CURRENT_LANG === 'zh' ? '右' : 'Right'}})</button>
          </div>
        </div>
      </div>
      <div class="form-group">
        <span class="form-label">${{CURRENT_LANG === 'zh' ? '选择指标' : 'Indicator'}}</span>
        <select onchange="onIndicatorChange(${{idx}}, this.value)">
          ${{indicatorOpts}}
        </select>
      </div>
    `;
    container.appendChild(card);
  }});
}}

function onCountryChange(idx, newCountry) {{
  ACTIVE_SERIES[idx].country = newCountry;
  const cData = CATALOG.countries.find(c => c.code === newCountry);
  if (cData && cData.indicators.length > 0) {{
    ACTIVE_SERIES[idx].indicatorId = cData.indicators[0].id;
  }}
  renderSeriesControls();
  refreshChart();
}}

function onIndicatorChange(idx, newIndicatorId) {{
  ACTIVE_SERIES[idx].indicatorId = newIndicatorId;
  refreshChart();
}}

function setSeriesAxis(idx, axis) {{
  ACTIVE_SERIES[idx].axis = axis;
  renderSeriesControls();
  refreshChart();
}}

function addSeries() {{
  if (ACTIVE_SERIES.length >= 5) return;
  const defCountry = ACTIVE_SERIES.length > 0 ? (ACTIVE_SERIES[0].country === 'US' ? 'EA' : 'US') : 'US';
  const cData = CATALOG.countries.find(c => c.code === defCountry) || CATALOG.countries[0];
  const indId = cData && cData.indicators.length > 0 ? cData.indicators[0].id : '';

  ACTIVE_SERIES.push({{
    country: cData.code,
    indicatorId: indId,
    axis: 'left',
    color: FT_PALETTE[ACTIVE_SERIES.length % FT_PALETTE.length],
  }});
  renderSeriesControls();
  refreshChart();
}}

function removeSeries(idx) {{
  if (ACTIVE_SERIES.length <= 1) return;
  ACTIVE_SERIES.splice(idx, 1);
  ACTIVE_SERIES.forEach((s, i) => {{
    s.color = FT_PALETTE[i % FT_PALETTE.length];
  }});
  renderSeriesControls();
  refreshChart();
}}

function setTransform(tf) {{
  CURRENT_TRANSFORM = tf;
  updateControlsUI();
  refreshChart();
}}

function setDateRange(range) {{
  CURRENT_RANGE = range;
  updateControlsUI();
  refreshChart();
}}

// Data Fetching & Caching
async function fetchCountryFrame(countryCode) {{
  if (FRAME_CACHE[countryCode]) return FRAME_CACHE[countryCode];
  const cData = CATALOG.countries.find(c => c.code === countryCode);
  if (!cData) return {{}};

  const inOutputDir = window.location.pathname.includes('/output/');
  const prefix = inOutputDir ? '' : 'output/';
  let res;
  try {{
    res = await fetch(prefix + cData.canonical_file);
    if (!res.ok && prefix) {{
      res = await fetch(cData.canonical_file);
    }}
  }} catch (err) {{
    res = await fetch(cData.canonical_file);
  }}
  const data = await res.json();
  const map = {{}};

  if (cData.canonical_file === 'cee_canonical_frame.json') {{
    (data.series || []).forEach(s => {{
      if (s.country === countryCode) {{
        map[s.indicator_id] = s;
      }}
    }});
  }} else {{
    (data.series || []).forEach(s => {{
      map[s.indicator_id] = s;
    }});
  }}
  FRAME_CACHE[countryCode] = map;
  return map;
}}

// Chart Rendering Logic (FT Graphic Specification)
async function refreshChart() {{
  document.getElementById('canvas-loading').style.display = 'flex';

  try {{
    // 1. Ensure all active countries are cached
    const neededCountries = [...new Set(ACTIVE_SERIES.map(s => s.country))];
    await Promise.all(neededCountries.map(fetchCountryFrame));

    // 2. Extract series observations
    const seriesData = [];
    ACTIVE_SERIES.forEach((item, idx) => {{
      const cData = CATALOG.countries.find(c => c.code === item.country);
      const frame = FRAME_CACHE[item.country] || {{}};
      const rawSeries = frame[item.indicatorId];
      if (!rawSeries) return;

      const meta = rawSeries.metadata || rawSeries;
      let label = (CURRENT_LANG === 'zh' ? meta.label_zh : meta.label_en) || item.indicatorId;
      label = `${{cData.flag}} ${{item.country}}: ${{label}}`;
      const unit = meta.unit || '';

      const rawObs = (rawSeries.observations || []).map(row => ({{
        date: String(row[0]),
        value: Number(row[1])
      }})).filter(r => !isNaN(r.value));

      seriesData.push({{
        index: idx,
        config: item,
        label: label,
        unit: unit,
        country: item.country,
        observations: rawObs
      }});
    }});

    // 3. Filter by Date Range
    const now = new Date();
    let cutoff = null;
    if (CURRENT_RANGE === '1y') cutoff = new Date(now.getFullYear() - 1, now.getMonth(), now.getDate());
    else if (CURRENT_RANGE === '3y') cutoff = new Date(now.getFullYear() - 3, now.getMonth(), now.getDate());
    else if (CURRENT_RANGE === '5y') cutoff = new Date(now.getFullYear() - 5, now.getMonth(), now.getDate());
    else if (CURRENT_RANGE === '10y') cutoff = new Date(now.getFullYear() - 10, now.getMonth(), now.getDate());

    const cutoffStr = cutoff ? cutoff.toISOString().slice(0, 10) : '0000-00-00';
    seriesData.forEach(s => {{
      s.filteredObs = s.observations.filter(o => o.date >= cutoffStr);
    }});

    // 4. Apply Transformations
    let plotTraces = [];
    let y1Title = seriesData[0] ? seriesData[0].unit : '';
    let y2Title = '';
    let hasY2 = false;

    if (CURRENT_TRANSFORM === 'rebase') {{
      y1Title = CURRENT_LANG === 'zh' ? '归一化指数 (基期 = 100)' : 'Rebased Index (Base = 100)';
      seriesData.forEach(s => {{
        if (!s.filteredObs.length) return;
        const baseVal = s.filteredObs[0].value || 1.0;
        const x = s.filteredObs.map(o => o.date);
        const y = s.filteredObs.map(o => (o.value / baseVal) * 100.0);
        plotTraces.push({{
          name: s.label,
          x: x,
          y: y,
          type: 'scatter',
          mode: 'lines',
          line: {{ color: s.config.color, width: 2.3 }}
        }});
      }});
    }} else if (CURRENT_TRANSFORM === 'spread' && seriesData.length >= 2) {{
      const s1 = seriesData[0];
      const s2 = seriesData[1];
      y1Title = s1.unit ? `${{s1.unit}} (Spread)` : 'Spread';

      const s2Map = new Map(s2.filteredObs.map(o => [o.date, o.value]));
      const spreadX = [];
      const spreadY = [];
      s1.filteredObs.forEach(o => {{
        if (s2Map.has(o.date)) {{
          spreadX.push(o.date);
          spreadY.push(o.value - s2Map.get(o.date));
        }}
      }});
      plotTraces.push({{
        name: `Spread (${{s1.config.country}} − ${{s2.config.country}})`,
        x: spreadX,
        y: spreadY,
        type: 'scatter',
        mode: 'lines',
        fill: 'tozeroy',
        fillcolor: 'rgba(153, 15, 61, 0.08)',
        line: {{ color: '#990f3d', width: 2.4 }}
      }});
      // Also display underlying series as fine dashed lines
      plotTraces.push({{
        name: `${{s1.label}}`,
        x: s1.filteredObs.map(o => o.date),
        y: s1.filteredObs.map(o => o.value),
        type: 'scatter',
        mode: 'lines',
        line: {{ color: '#0d7680', width: 1.5, dash: 'dot' }}
      }});
      plotTraces.push({{
        name: `${{s2.label}}`,
        x: s2.filteredObs.map(o => o.date),
        y: s2.filteredObs.map(o => o.value),
        type: 'scatter',
        mode: 'lines',
        line: {{ color: '#737c8c', width: 1.5, dash: 'dot' }}
      }});
    }} else {{
      // Raw Levels
      seriesData.forEach(s => {{
        if (!s.filteredObs.length) return;
        const isRight = (s.config.axis === 'right');
        if (isRight) {{
          hasY2 = true;
          if (!y2Title) y2Title = s.unit;
        }} else {{
          if (!y1Title) y1Title = s.unit;
        }}
        plotTraces.push({{
          name: s.label,
          x: s.filteredObs.map(o => o.date),
          y: s.filteredObs.map(o => o.value),
          yaxis: isRight ? 'y2' : 'y',
          type: 'scatter',
          mode: 'lines',
          line: {{ color: s.config.color, width: 2.3 }}
        }});
      }});
    }}

    // 5. Layout Configuration in FT/Claude Style
    const layout = {{
      height: 560,
      margin: {{ l: 56, r: hasY2 ? 56 : 24, t: 24, b: 54 }},
      paper_bgcolor: '#ffffff',
      plot_bgcolor: '#ffffff',
      font: {{
        family: "-apple-system, BlinkMacSystemFont, 'Segoe UI', 'PingFang SC', 'Hiragino Sans GB', 'Noto Sans SC', sans-serif",
        size: 11,
        color: '#12151a'
      }},
      xaxis: {{
        gridcolor: 'rgba(18, 21, 26, 0.06)',
        showgrid: false,
        zeroline: false,
        autorange: true,
        automargin: true,
        tickfont: {{ size: 10, color: '#4b525f' }},
      }},
      yaxis: {{
        title: {{ text: y1Title, font: {{ size: 11, color: '#4b525f' }} }},
        gridcolor: 'rgba(18, 21, 26, 0.06)',
        zeroline: true,
        zerolinewidth: 1.4,
        zerolinecolor: 'rgba(18, 21, 26, 0.40)',
        autorange: true,
        automargin: true,
        tickfont: {{ size: 10, color: '#4b525f' }},
      }},
      yaxis2: hasY2 ? {{
        title: {{ text: y2Title, font: {{ size: 11, color: '#4b525f' }} }},
        overlaying: 'y',
        side: 'right',
        showgrid: false,
        zeroline: false,
        autorange: true,
        automargin: true,
        tickfont: {{ size: 10, color: '#4b525f' }},
      }} : undefined,
      legend: {{
        orientation: 'h',
        y: -0.22,
        x: 0,
        font: {{ size: 11, color: '#12151a' }},
        bgcolor: 'rgba(255, 255, 255, 0.85)',
      }},
      hovermode: 'x unified',
      hoverlabel: {{
        bgcolor: '#ffffff',
        bordercolor: 'rgba(18, 21, 26, 0.20)',
        font: {{ family: '-apple-system, sans-serif', size: 11, color: '#12151a' }},
      }},
      autosize: true,
    }};

    Plotly.react('chart-canvas', plotTraces, layout, {{
      displayModeBar: "hover",
      displaylogo: false,
      responsive: true
    }});

    // 6. Update Summary Table
    renderSummaryTable(seriesData);

    // 7. Update URL Hash
    syncHash();

  }} catch (err) {{
    console.error("Chart refresh error:", err);
  }} finally {{
    document.getElementById('canvas-loading').style.display = 'none';
  }}
}}

function renderSummaryTable(seriesData) {{
  const tbody = document.getElementById('summary-table-body');
  tbody.innerHTML = '';

  seriesData.forEach(s => {{
    const vals = s.filteredObs.map(o => o.value);
    const minVal = vals.length ? Math.min(...vals).toFixed(2) : 'n/a';
    const maxVal = vals.length ? Math.max(...vals).toFixed(2) : 'n/a';
    const meanVal = vals.length ? (vals.reduce((a, b) => a + b, 0) / vals.length).toFixed(2) : 'n/a';
    const latestObs = s.filteredObs.length ? s.filteredObs[s.filteredObs.length - 1] : {{ date: 'n/a', value: 'n/a' }};
    const latestFormatted = typeof latestObs.value === 'number' ? `${{latestObs.value.toFixed(2)}} ${{s.unit}}` : 'n/a';

    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td>
        <span class="table-bullet" style="background: ${{s.config.color}};"></span>
        <strong>${{s.label}}</strong>
      </td>
      <td><strong>${{s.country}}</strong></td>
      <td><strong>${{latestFormatted}}</strong></td>
      <td style="color: var(--muted);">${{latestObs.date}}</td>
      <td>${{minVal}}</td>
      <td>${{maxVal}}</td>
      <td>${{meanVal}}</td>
      <td><span style="font-weight:600; color: ${{s.config.axis === 'right' ? 'var(--teal)' : 'var(--accent)'}};">${{s.config.axis.toUpperCase()}}</span></td>
    `;
    tbody.appendChild(tr);
  }});
}}

// URL Hash Persistence
function syncHash() {{
  const payload = {{
    t: CURRENT_TRANSFORM,
    r: CURRENT_RANGE,
    s: ACTIVE_SERIES.map(item => `${{item.country}}:${{item.indicatorId}}:${{item.axis}}`).join(';')
  }};
  const hash = `#state=${{encodeURIComponent(JSON.stringify(payload))}}`;
  history.replaceState(null, '', hash);
}}

function loadFromHash(hash) {{
  try {{
    const match = hash.match(/#state=([^&]+)/);
    if (!match) return;
    const payload = JSON.parse(decodeURIComponent(match[1]));
    if (payload.t) CURRENT_TRANSFORM = payload.t;
    if (payload.r) CURRENT_RANGE = payload.r;
    if (payload.s) {{
      ACTIVE_SERIES = [];
      payload.s.split(';').forEach((chunk, idx) => {{
        const [c, id, ax] = chunk.split(':');
        if (c && id) {{
          ACTIVE_SERIES.push({{
            country: c,
            indicatorId: id,
            axis: ax || 'left',
            color: FT_PALETTE[idx % FT_PALETTE.length]
          }});
        }}
      }});
    }}
    updateControlsUI();
    refreshChart();
  }} catch (e) {{
    console.error("Failed to parse URL hash:", e);
  }}
}}

// Action Buttons
function exportPNG() {{
  Plotly.downloadImage('chart-canvas', {{
    format: 'png',
    width: 1400,
    height: 750,
    filename: `macro_chart_studio_${{Date.now()}}`
  }});
}}

function exportCSV() {{
  const neededCountries = [...new Set(ACTIVE_SERIES.map(s => s.country))];
  const allDates = new Set();
  const seriesMap = [];

  ACTIVE_SERIES.forEach((item, idx) => {{
    const frame = FRAME_CACHE[item.country] || {{}};
    const rawSeries = frame[item.indicatorId];
    if (!rawSeries) return;
    const meta = rawSeries.metadata || rawSeries;
    const colName = `${{item.country}}_${{item.indicatorId}}_${{meta.unit || ''}}`.replace(/,/g, '');
    const dateMap = new Map((rawSeries.observations || []).map(r => [String(r[0]), Number(r[1])]));
    dateMap.forEach((_, d) => allDates.add(d));
    seriesMap.push({{ name: colName, map: dateMap }});
  }});

  const sortedDates = [...allDates].sort();
  let csv = 'date,' + seriesMap.map(s => `"${{s.name}}"`).join(',') + '\\n';

  sortedDates.forEach(date => {{
    const row = [date];
    seriesMap.forEach(s => {{
      const val = s.map.get(date);
      row.push(val !== undefined && !isNaN(val) ? val : '');
    }});
    csv += row.join(',') + '\\n';
  }});

  const blob = new Blob([csv], {{ type: 'text/csv;charset=utf-8;' }});
  const link = document.createElement('a');
  link.href = URL.createObjectURL(blob);
  link.setAttribute('download', `macro_chart_data_${{Date.now()}}.csv`);
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
}}

function copyShareURL() {{
  navigator.clipboard.writeText(window.location.href).then(() => {{
    alert(CURRENT_LANG === 'zh' ? '已复制分享链接！包含当前的指标配置与变换模式。' : 'Share link copied to clipboard! Contains your series setup and layout.');
  }}).catch(() => {{
    prompt(CURRENT_LANG === 'zh' ? '复制此链接分享当前图表：' : 'Copy link to share chart:', window.location.href);
  }});
}}

function toggleLang() {{
  CURRENT_LANG = CURRENT_LANG === 'en' ? 'zh' : 'en';
  document.documentElement.lang = CURRENT_LANG;
  document.getElementById('lang-btn').textContent = CURRENT_LANG === 'en' ? '中文' : 'English';
  renderPresets();
  renderSeriesControls();
  refreshChart();
}}

window.addEventListener('DOMContentLoaded', init);
</script>
</body>
</html>
"""


def build_studio() -> tuple[Path, Path, Path, Path]:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    catalog = generate_catalog()

    catalog_path = OUTPUT / "chart_studio_catalog.json"
    with open(catalog_path, "w", encoding="utf-8") as f:
        json.dump(catalog, f, indent=2, ensure_ascii=False)
    print(f"Wrote {catalog_path} ({catalog_path.stat().st_size:,} bytes)")

    html_content = render_html()
    html_path = OUTPUT / "chart_studio.html"
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html_content)
    print(f"Wrote {html_path} ({html_path.stat().st_size:,} bytes)")

    root_html = ROOT / "chart_studio.html"
    shutil.copy2(html_path, root_html)
    print(f"Wrote {root_html} ({root_html.stat().st_size:,} bytes)")

    root_catalog = ROOT / "chart_studio_catalog.json"
    shutil.copy2(catalog_path, root_catalog)
    print(f"Wrote {root_catalog} ({root_catalog.stat().st_size:,} bytes)")

    return catalog_path, html_path, root_html, root_catalog


if __name__ == "__main__":
    build_studio()
