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
        "id": "us_ea_10y_spread",
        "title_en": "US vs Euro Area 10Y Sovereign Yield & Spread",
        "title_zh": "欧美 10 年期基准国债收益率与跨大西洋利差对比",
        "description_zh": "全球核心无风险利率：美债 10 年期收益率 vs 欧元区 AAA 基准 10 年期公债收益率及跨大西洋利差走势。",
        "description_en": "Global benchmark 10Y sovereign yields for US and Euro Area AAA benchmark with transatlantic spread dynamics.",
        "transform": "raw",
        "date_range": "5y",
        "series": [
            {"country": "US", "id": "treasury_10y_yield", "axis": "left", "color": "#990f3d", "label": "US 10Y Treasury Yield (%)"},
            {"country": "EA", "id": "aaa_yield_10y", "axis": "left", "color": "#0d7680", "label": "Euro Area AAA 10Y Yield (%)"}
        ]
    },
    {
        "id": "central_bank_rates",
        "title_en": "Major Central Bank Policy Rates (Fed, ECB, BOE, BOJ)",
        "title_zh": "主要央行基准政策利率走廊对比 (美联储/欧央行/英格兰银行/日银)",
        "description_zh": "全球核心央行货币政策周期、加息见顶与降息节奏同屏横向对比。",
        "description_en": "Global major central bank benchmark policy rates and monetary easing cycles.",
        "transform": "raw",
        "date_range": "5y",
        "series": [
            {"country": "US", "id": "effective_fed_funds", "axis": "left", "color": "#990f3d", "label": "Fed Effective Funds Rate (%)"},
            {"country": "EA", "id": "policy_rate", "axis": "left", "color": "#0d7680", "label": "ECB Deposit Facility Rate (%)"},
            {"country": "UK", "id": "bank_rate", "axis": "left", "color": "#364b61", "label": "BOE Bank Rate (%)"},
            {"country": "JP", "id": "policy_rate", "axis": "left", "color": "#d97706", "label": "BOJ Overnight Call Rate (%)"}
        ]
    },
    {
        "id": "global_inflation_battle",
        "title_en": "Inflation Battle: US vs Euro Area vs China CPI",
        "title_zh": "全球三大经济体通胀去向：美欧中 CPI 同比路径对比",
        "description_zh": "美欧抗通胀与去通胀进程 vs 中国温和通胀格局全景对比。",
        "description_en": "Disinflation and price stability dynamics across US, Euro Area and China.",
        "transform": "raw",
        "date_range": "5y",
        "series": [
            {"country": "US", "id": "cpi_inflation", "axis": "left", "color": "#990f3d", "label": "US Headline CPI Inflation (% y/y)"},
            {"country": "EA", "id": "hicp_inflation", "axis": "left", "color": "#0d7680", "label": "Euro Area HICP Inflation (% y/y)"},
            {"country": "CN", "id": "cpi_yoy_akshare", "axis": "left", "color": "#d97706", "label": "China CPI Inflation (% y/y)"}
        ]
    },
    {
        "id": "kr_tw_tech_momentum",
        "title_en": "Korea KOSPI vs Taiwan TAIEX Equity Momentum (Base = 100)",
        "title_zh": "韩国 KOSPI vs 台湾 TAIEX 科技股指走势 (基期归一化 = 100)",
        "description_zh": "东亚半导体与科技出口双雄核心股指累计收益率走势归一化发散度对比。",
        "description_en": "Normalized equity return comparison for East Asian semiconductor powerhouses.",
        "transform": "rebase",
        "date_range": "3y",
        "series": [
            {"country": "KR", "id": "kospi_stock_index", "axis": "left", "color": "#990f3d", "label": "Korea KOSPI Composite"},
            {"country": "TW", "id": "taiex_index", "axis": "left", "color": "#0d7680", "label": "Taiwan TAIEX Index"}
        ]
    },
    {
        "id": "crude_oil_production_brent",
        "title_en": "Crude Oil Output & Spot Price: Kazakhstan & Nigeria vs Brent",
        "title_zh": "产油国供给与油价：哈萨克斯坦与尼日利亚日产 (左轴) vs 布伦特油价 (右轴)",
        "description_zh": "产油国日产水平（千桶/日）与国际现货油价（美元/桶）双 Y 轴联动。",
        "description_en": "Crude oil output for key producers compared against Brent crude spot price.",
        "transform": "raw",
        "date_range": "5y",
        "series": [
            {"country": "KZ", "id": "crude_oil_production", "axis": "left", "color": "#990f3d", "label": "Kazakhstan Crude Output (TBPD)"},
            {"country": "NG", "id": "crude_oil_production", "axis": "left", "color": "#0d7680", "label": "Nigeria Crude Output (TBPD)"},
            {"country": "KZ", "id": "brent_crude_oil", "axis": "right", "color": "#364b61", "label": "Brent Crude Price ($/bbl)"}
        ]
    },
    {
        "id": "em_inflation_defense",
        "title_en": "EM Monetary Defense: Turkey vs Egypt vs Nigeria Policy Rates",
        "title_zh": "新兴市场利率防线：土耳其 vs 埃及 vs 尼日利亚 政策利率",
        "description_zh": "高通胀新兴市场央行基准借贷与回购政策利率横向防线对比。",
        "description_en": "Central bank policy rate defense across high-inflation emerging markets.",
        "transform": "raw",
        "date_range": "5y",
        "series": [
            {"country": "TR", "id": "policy_rate", "axis": "left", "color": "#990f3d", "label": "Turkey One-Week Repo Rate (%)"},
            {"country": "EG", "id": "policy_rate", "axis": "left", "color": "#0d7680", "label": "Egypt CBE Corridor Rate (%)"},
            {"country": "NG", "id": "policy_rate", "axis": "left", "color": "#d97706", "label": "Nigeria Monetary Policy Rate (%)"}
        ]
    },
    {
        "id": "cgb_yield_curve_and_us_spread",
        "title_en": "China Sovereign Yield Curve & US-China 10Y Spread",
        "title_zh": "中国国债收益率曲线关键期限与中美10年期利差走势",
        "description_zh": "中国国债 2 年、10 年期基准收益率走势（左轴）与中美 10 年期国债利差（右轴）联动对比。",
        "description_en": "China 2Y & 10Y Sovereign CGB benchmark yields (left axis) with US-China 10Y sovereign yield spread dynamics (right axis).",
        "transform": "raw",
        "date_range": "5y",
        "series": [
            {"country": "CN", "id": "cgb_yield_2y", "axis": "left", "color": "#2563eb", "label": "China 2Y CGB Yield (%)"},
            {"country": "CN", "id": "cgb_yield_10y", "axis": "left", "color": "#990f3d", "label": "China 10Y CGB Yield (%)"},
            {"country": "CN", "id": "us_cn_spread_10y", "axis": "right", "color": "#0d7680", "label": "US-China 10Y Spread (% pts)"}
        ]
    },
    {
        "id": "em_guidotti_greenspan_safety",
        "title_en": "EM External Debt Solvency: Guidotti-Greenspan Ratio Comparison",
        "title_zh": "新兴市场外部债务防线：格林斯潘-吉多蒂流动性安全垫对比",
        "description_zh": "短期外债占总外储比重（%）：低于100%为安全阈值（格林斯潘-吉多蒂法则），横向追踪土耳其、南非、埃及、尼日利亚、哈萨克斯坦与乌兹别克斯坦外部清偿安全垫。",
        "description_en": "Short-Term External Debt as % of Total Reserves across emerging markets; <100% represents the Guidotti-Greenspan safety cushion.",
        "transform": "raw",
        "date_range": "max",
        "series": [
            {"country": "TR", "id": "short_term_external_debt_pct_reserves", "axis": "left", "color": "#990f3d", "label": "Turkey Short-Term Debt / Reserves (%)"},
            {"country": "ZA", "id": "short_term_external_debt_pct_reserves", "axis": "left", "color": "#0d7680", "label": "South Africa Short-Term Debt / Reserves (%)"},
            {"country": "EG", "id": "short_term_external_debt_pct_reserves", "axis": "left", "color": "#d97706", "label": "Egypt Short-Term Debt / Reserves (%)"},
            {"country": "NG", "id": "short_term_external_debt_pct_reserves", "axis": "left", "color": "#16a34a", "label": "Nigeria Short-Term Debt / Reserves (%)"},
            {"country": "KZ", "id": "short_term_external_debt_pct_reserves", "axis": "left", "color": "#2563eb", "label": "Kazakhstan Short-Term Debt / Reserves (%)"},
            {"country": "UZ", "id": "short_term_external_debt_pct_reserves", "axis": "left", "color": "#7c3aed", "label": "Uzbekistan Short-Term Debt / Reserves (%)"}
        ]
    },
    {
        "id": "em_current_account_and_solvency",
        "title_en": "EM Structural External Balance: Current Account % GDP (Surplus vs Deficit)",
        "title_zh": "新兴市场外部收支分化：经常账户占GDP比重 (逆差承压 vs 顺差安全垫)",
        "description_zh": "对比新兴市场与前沿经济体经常账户占GDP比重（%）：监控从罗马尼亚(-8.2%)、乌兹别克斯坦(-4.8%)、土耳其(-1.8%)的外部融资依赖，到波兰(+0.3%)、尼日利亚(+3.8%)与中国台湾(+19.8%)的顺差安全垫。",
        "description_en": "Current Account Balance as % of GDP across emerging and frontier markets: highlighting external financing vulnerability (Romania, Uzbekistan, Turkey) versus structural surplus cushions (Nigeria, Poland, Taiwan).",
        "transform": "raw",
        "date_range": "max",
        "series": [
            {"country": "RO", "id": "current_account_pct_gdp", "axis": "left", "color": "#990f3d", "label": "Romania Current Account (% GDP)"},
            {"country": "TR", "id": "current_account_gdp", "axis": "left", "color": "#ea580c", "label": "Turkey Current Account (% GDP)"},
            {"country": "EG", "id": "current_account_gdp", "axis": "left", "color": "#d97706", "label": "Egypt Current Account (% GDP)"},
            {"country": "PL", "id": "current_account_pct_gdp", "axis": "left", "color": "#0d7680", "label": "Poland Current Account (% GDP)"},
            {"country": "NG", "id": "current_account_gdp", "axis": "left", "color": "#16a34a", "label": "Nigeria Current Account (% GDP)"},
            {"country": "TW", "id": "current_account_gdp", "axis": "left", "color": "#2563eb", "label": "Taiwan Current Account (% GDP)"}
        ]
    },
    {
        "id": "us_treasury_curve_matrix",
        "title_en": "US Treasury Yield Curve Structure (2Y, 5Y, 10Y, 30Y & 10s2s Slope)",
        "title_zh": "美国国债收益率期限结构与利差形态 (2Y/5Y/10Y/30Y & 10s2s利差)",
        "description_zh": "覆盖2年、5年、10年与30年期美债基准利率形态（左轴），结合10Y-2Y期限利差（右轴）监测收益率曲线倒挂与陡峭化走势。",
        "description_en": "Benchmark US Treasury yields across 2Y, 5Y, 10Y, and 30Y tenors (left axis) alongside the 10Y-2Y term spread (right axis).",
        "transform": "raw",
        "date_range": "5y",
        "series": [
            {"country": "US", "id": "treasury_2y_yield", "axis": "left", "color": "#2563eb", "label": "US 2Y Treasury Yield (%)"},
            {"country": "US", "id": "treasury_5y_yield", "axis": "left", "color": "#0d7680", "label": "US 5Y Treasury Yield (%)"},
            {"country": "US", "id": "treasury_10y_yield", "axis": "left", "color": "#990f3d", "label": "US 10Y Treasury Yield (%)"},
            {"country": "US", "id": "treasury_30y_yield", "axis": "left", "color": "#7c3aed", "label": "US 30Y Treasury Yield (%)"},
            {"country": "US", "id": "yield_curve_10y2y", "axis": "right", "color": "#d97706", "label": "10Y-2Y Term Spread (% pts)"}
        ]
    },
    {
        "id": "us_inflation_expectations_matrix",
        "title_en": "US Inflation Expectations: Market TIPS Breakevens vs Michigan Survey",
        "title_zh": "美国通胀预期网络：TIPS市场盈亏平衡通胀 vs 密歇根消费者预期",
        "description_zh": "对比5年/10年期TIPS市场隐含通胀预期与密歇根大学消费者1年/5年期通胀预期，监控通胀预期锚定状态。",
        "description_en": "Market-implied 5Y and 10Y TIPS breakeven inflation rates alongside University of Michigan 1Y and 5Y survey expectations.",
        "transform": "raw",
        "date_range": "5y",
        "series": [
            {"country": "US", "id": "five_year_breakeven", "axis": "left", "color": "#0d7680", "label": "5Y TIPS Breakeven Inflation (%)"},
            {"country": "US", "id": "ten_year_breakeven", "axis": "left", "color": "#990f3d", "label": "10Y TIPS Breakeven Inflation (%)"},
            {"country": "US", "id": "michigan_inflation_expectation", "axis": "left", "color": "#d97706", "label": "Michigan 1Y Inflation Exp (%)"},
            {"country": "US", "id": "michigan_5y_inflation_expectation", "axis": "left", "color": "#2563eb", "label": "Michigan 5Y Inflation Exp (%)"}
        ]
    },
    {
        "id": "euro_area_sovereign_fragmentation",
        "title_en": "Euro Area Sovereign Risk Fragmentation (BTP, Bonos, OAT vs Bund)",
        "title_zh": "欧元区核心与外围主权利差监控 (意/西/法/希 vs 德国公债基准利差)",
        "description_zh": "追踪欧元区金融碎片化与主权信用风险：意大利BTP、法国OAT、西班牙Bonos与希腊GGB对德国10年期公债利差 (基点)。",
        "description_en": "Monitors sovereign spread fragmentation in the Euro Area: Italy BTP, France OAT, Spain Bonos, and Greece GGB 10Y spreads vs German Bund (bps).",
        "transform": "raw",
        "date_range": "5y",
        "series": [
            {"country": "EA", "id": "it_de_spread_10y", "axis": "left", "color": "#990f3d", "label": "Italy BTP - Bund 10Y Spread (bps)"},
            {"country": "EA", "id": "fr_de_spread_10y", "axis": "left", "color": "#0d7680", "label": "France OAT - Bund 10Y Spread (bps)"},
            {"country": "EA", "id": "es_de_spread_10y", "axis": "left", "color": "#d97706", "label": "Spain Bonos - Bund 10Y Spread (bps)"},
            {"country": "EA", "id": "gr_de_spread_10y", "axis": "left", "color": "#7c3aed", "label": "Greece GGB - Bund 10Y Spread (bps)"}
        ]
    },
    {
        "id": "global_10y_yields_convergence",
        "title_en": "Global Major 10Y Sovereign Yields (US, Germany, UK, Japan, China)",
        "title_zh": "全球核心经济体10年期国债收益率联动 (美/德/英/日/中)",
        "description_zh": "全球五大经济体10年期基准国债无风险收益率横向联动走势。",
        "description_en": "Global cross-market sovereign yields: US 10Y Treasury, German 10Y Bund, UK 10Y Gilt, Japan 10Y JGB, and China 10Y CGB.",
        "transform": "raw",
        "date_range": "5y",
        "series": [
            {"country": "US", "id": "treasury_10y_yield", "axis": "left", "color": "#990f3d", "label": "US 10Y Treasury (%)"},
            {"country": "EA", "id": "aaa_yield_10y", "axis": "left", "color": "#0d7680", "label": "Germany Bund 10Y (%)"},
            {"country": "UK", "id": "long_rate_10y", "axis": "left", "color": "#364b61", "label": "UK Gilt 10Y (%)"},
            {"country": "JP", "id": "sovereign_yield_10y", "axis": "left", "color": "#d97706", "label": "Japan JGB 10Y (%)"},
            {"country": "CN", "id": "cgb_yield_10y", "axis": "left", "color": "#dc2626", "label": "China CGB 10Y (%)"}
        ]
    },
    {
        "id": "us_high_frequency_pulse",
        "title_en": "US High-Frequency Growth Pulse: WEI vs Jobless Claims 4W-MA",
        "title_zh": "美国高频经济景气脉搏：纽约联储周度经济指数 vs 初请失业金4周均线",
        "description_zh": "高频追踪美国经济增长与劳动力市场动能：纽约联储周度经济指数(WEI，左轴)与初请失业金4周移动均线(右轴)，反映实际产出与裁员拐点。",
        "description_en": "Tracks high-frequency US economic momentum: NY Fed Weekly Economic Index (left axis) against 4-Week Moving Average Initial Jobless Claims (right axis).",
        "transform": "raw",
        "date_range": "5y",
        "series": [
            {"country": "US", "id": "weekly_economic_index", "axis": "left", "color": "#0d7680", "label": "NY Fed Weekly Economic Index"},
            {"country": "US", "id": "initial_jobless_claims_4w_ma", "axis": "right", "color": "#990f3d", "label": "Initial Jobless Claims 4W-MA (persons)"}
        ]
    },
    {
        "id": "us_regional_fed_manufacturing_outlook",
        "title_en": "US Regional Fed Manufacturing: Philly Fed vs Empire State vs Chicago CFNAI",
        "title_zh": "美国地区联储制造业先行扩散对比 (费城联储 / 纽约帝国州 / 芝加哥联储)",
        "description_zh": "每月月中率先公布的区域制造业活动扩散指数：费城联储商业前景(左轴)、纽约联储帝国州(左轴)与芝加哥联储全国活动指数(CFNAI，右轴)同屏交叉验证。",
        "description_en": "Early-month manufacturing diffusion indicators: Philadelphia Fed and NY Fed Empire State (left axis) with Chicago Fed CFNAI (right axis).",
        "transform": "raw",
        "date_range": "5y",
        "series": [
            {"country": "US", "id": "philadelphia_fed_mfg_index", "axis": "left", "color": "#2563eb", "label": "Philadelphia Fed Mfg Index"},
            {"country": "US", "id": "empire_state_mfg_index", "axis": "left", "color": "#990f3d", "label": "Empire State Mfg Index"},
            {"country": "US", "id": "chicago_fed_national_activity_index", "axis": "right", "color": "#0d7680", "label": "Chicago Fed CFNAI (index)"}
        ]
    },
    {
        "id": "global_tech_and_export_bellwether",
        "title_en": "Global Tech & Trade Cycle: Korea Exports, Taiwan Customs & China Exports",
        "title_zh": "全球科技与贸易出口晴雨表：韩国出口 vs 台湾出口 vs 中国海关出口",
        "description_zh": "全球外需与半导体资本品周期敏感前哨：韩国货物出口（百万美元，左轴）、中国台湾海关出口同比（右轴）与中国海关出口同比（右轴）联动追踪。",
        "description_en": "Leading global trade cycle indicators across East Asian manufacturing powerhouses: South Korea goods exports (USD mn, left axis), Taiwan customs exports YoY (right axis), and China customs exports YoY (right axis).",
        "transform": "raw",
        "date_range": "5y",
        "series": [
            {"country": "KR", "id": "goods_exports", "axis": "left", "color": "#2563eb", "label": "South Korea Goods Exports (USD mn)"},
            {"country": "TW", "id": "customs_exports_yoy", "axis": "right", "color": "#0d7680", "label": "Taiwan Customs Exports (% y/y)"},
            {"country": "CN", "id": "customs_exports_yoy_akshare", "axis": "right", "color": "#990f3d", "label": "China Customs Exports (% y/y)"}
        ]
    },
    {
        "id": "us_net_liquidity_transmission",
        "title_en": "US Central Bank Plumbing: Fed Assets, TGA, ON RRP & Reserve Balances",
        "title_zh": "美国央行流动性管道与资产负债表拆解 (美联储总资产 / 国债持仓 / MBS / TGA / 逆回购 / 准备金)",
        "description_zh": "监控美元流动性核心管道：资产端美联储总资产规模、国债与MBS持仓（左轴，百万美元）与负债端准备金余额、财政部一般账户(TGA)以及隔夜逆回购(ON RRP)（右轴）拆解联动。",
        "description_en": "Monitors the mechanics of US dollar liquidity transmission: Fed Total Assets, Treasury holdings, and MBS on the asset side (left axis, USD mn) against Treasury General Account (TGA) cash drain, ON RRP, and commercial bank reserve balances (right axis, USD mn).",
        "transform": "raw",
        "date_range": "5y",
        "series": [
            {"country": "US", "id": "fed_total_assets", "axis": "left", "color": "#0d7680", "label": "Fed Total Assets ($M)"},
            {"country": "US", "id": "fed_treasury_holdings", "axis": "left", "color": "#2563eb", "label": "Fed Treasury Holdings ($M)"},
            {"country": "US", "id": "fed_mbs_holdings", "axis": "left", "color": "#7c3aed", "label": "Fed MBS Holdings ($M)"},
            {"country": "US", "id": "reserve_balances", "axis": "right", "color": "#990f3d", "label": "Bank Reserve Balances ($M)"},
            {"country": "US", "id": "treasury_general_account", "axis": "right", "color": "#d97706", "label": "Treasury General Account ($M)"}
        ]
    },
    {
        "id": "global_central_bank_balance_sheets",
        "title_en": "Global Central Bank Balance Sheets: Fed vs ECB vs BoJ Total Assets",
        "title_zh": "全球核心央行资产负债表扩张与收缩 (美联储 vs 欧洲央行 vs 日本央行)",
        "description_zh": "全球主要央行量化宽松与紧缩(QT/QE)总规模对比：美联储总资产（百万美元，左轴）、欧洲央行欧元系统资产（百万欧元，左轴）与日本央行总资产（百亿日元，右轴）联动对比。",
        "description_en": "Comparative quantitative tightening and easing across major central banks: US Federal Reserve (USD mn, left axis), Eurosystem ECB (EUR mn, left axis), and Bank of Japan (JPY 100mn, right axis).",
        "transform": "rebase",
        "date_range": "5y",
        "series": [
            {"country": "US", "id": "fed_total_assets", "axis": "left", "color": "#0d7680", "label": "Fed Total Assets (USD mn)"},
            {"country": "EA", "id": "eurosystem_total_assets", "axis": "left", "color": "#2563eb", "label": "ECB Eurosystem Assets (EUR mn)"},
            {"country": "JP", "id": "boj_total_assets", "axis": "right", "color": "#990f3d", "label": "BoJ Total Assets (JPY 100mn)"}
        ]
    },
    {
        "id": "us_tips_breakeven_regression",
        "title_en": "US 10Y Nominal vs TIPS Breakeven: Inflation Expectation Sensitivity (OLS)",
        "title_zh": "美国10年期名义国债 vs 10年期TIPS通胀预期：敏感度与OLS线性回归",
        "description_zh": "分析美国10年期名义国债收益率与10年期TIPS盈亏平衡通胀预期的联动关系与回归弹性系数(Beta)。",
        "description_en": "Scatter and OLS linear regression between US 10Y nominal Treasury yields and 10Y TIPS breakeven inflation expectations.",
        "transform": "raw",
        "date_range": "5y",
        "view": "scatter_ols",
        "series": [
            {"country": "US", "id": "ten_year_breakeven", "axis": "left", "color": "#0d7680", "label": "10Y TIPS Breakeven Inflation (%)"},
            {"country": "US", "id": "treasury_10y_yield", "axis": "left", "color": "#990f3d", "label": "US 10Y Treasury Yield (%)"}
        ]
    },
    {
        "id": "us_wei_jobless_claims_lead_lag",
        "title_en": "US Real Activity Pulse: Weekly Economic Index vs Jobless Claims (Lead-Lag)",
        "title_zh": "美国高频经济动能脉搏：纽约联储WEI vs 初请失业金 领先-滞后时序分析",
        "description_zh": "高频先行指标交叉相关：纽约联储周度经济指数(WEI)与初请失业金4周均线在不同期数滞后下的相关系数曲线与最佳领先期数探测。",
        "description_en": "Lead-lag cross-correlation between NY Fed Weekly Economic Index and 4-week moving average initial jobless claims.",
        "transform": "zscore",
        "date_range": "5y",
        "view": "lead_lag",
        "series": [
            {"country": "US", "id": "weekly_economic_index", "axis": "left", "color": "#0d7680", "label": "NY Fed Weekly Economic Index"},
            {"country": "US", "id": "initial_jobless_claims_4w_ma", "axis": "right", "color": "#990f3d", "label": "Initial Jobless Claims 4W-MA (persons)"}
        ]
    },
    {
        "id": "global_yield_cross_correlation_matrix",
        "title_en": "Global Sovereign 10Y Yields: Cross-Country Correlation Matrix & Rolling Linkage",
        "title_zh": "全球主要经济体10年期国债收益率：跨国相关性矩阵与滚动联动分析",
        "description_zh": "美、德、英、日、中五国基准10年期国债收益率全景相关性矩阵热力图与跨大西洋利差滚动相关性。",
        "description_en": "Pairwise correlation matrix heatmap across benchmark 10Y sovereign yields for US, Germany, UK, Japan, and China.",
        "transform": "raw",
        "date_range": "5y",
        "view": "correlation",
        "series": [
            {"country": "US", "id": "treasury_10y_yield", "axis": "left", "color": "#990f3d", "label": "US 10Y Treasury (%)"},
            {"country": "EA", "id": "aaa_yield_10y", "axis": "left", "color": "#0d7680", "label": "Germany Bund 10Y (%)"},
            {"country": "UK", "id": "long_rate_10y", "axis": "left", "color": "#364b61", "label": "UK Gilt 10Y (%)"},
            {"country": "JP", "id": "sovereign_yield_10y", "axis": "left", "color": "#d97706", "label": "Japan JGB 10Y (%)"},
            {"country": "CN", "id": "cgb_yield_10y", "axis": "left", "color": "#dc2626", "label": "China CGB 10Y (%)"}
        ]
    },
    {
        "id": "kr_tw_semiconductor_zscore",
        "title_en": "East Asia Tech Cycle: Korea KOSPI vs Taiwan TAIEX Normalized Z-Scores",
        "title_zh": "东亚半导体出口双雄：韩国 KOSPI vs 台湾 TAIEX Z-Score 标准化动能对比",
        "description_zh": "通过 Z-Score 标准化去除基数差异，同屏评估韩国 KOSPI 与台湾 TAIEX 股指在科技周期中的相对超买超卖与周期极值位置。",
        "description_en": "Standardized Z-score momentum comparison of Korea KOSPI and Taiwan TAIEX equity benchmarks.",
        "transform": "zscore",
        "date_range": "5y",
        "view": "timeseries",
        "series": [
            {"country": "KR", "id": "kospi_stock_index", "axis": "left", "color": "#990f3d", "label": "Korea KOSPI Index"},
            {"country": "TW", "id": "taiex_index", "axis": "left", "color": "#0d7680", "label": "Taiwan TAIEX Index"}
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


def get_initial_embedded_frames() -> dict:
    """Pre-extract default preset indicators so the initial chart renders with zero network latency."""
    embedded = {}
    try:
        # 1. US treasury_10y_yield
        us_file = OUTPUT / "us_canonical_frame.json"
        if us_file.exists():
            with open(us_file, "r", encoding="utf-8") as f:
                us_data = json.load(f)
            us_series = {s.get("indicator_id"): s for s in us_data.get("series", [])}
            if "treasury_10y_yield" in us_series:
                embedded.setdefault("US", {})["treasury_10y_yield"] = us_series["treasury_10y_yield"]

        # 2. EA aaa_yield_10y
        ea_file = OUTPUT / "euro_area_canonical_frame.json"
        if ea_file.exists():
            with open(ea_file, "r", encoding="utf-8") as f:
                ea_data = json.load(f)
            ea_series = {s.get("indicator_id"): s for s in ea_data.get("series", [])}
            if "aaa_yield_10y" in ea_series:
                embedded.setdefault("EA", {})["aaa_yield_10y"] = ea_series["aaa_yield_10y"]
    except Exception as e:
        print(f"Warning: could not prepare embedded initial frames: {e}", file=sys.stderr)
    return embedded


def render_html(catalog: dict) -> str:
    nav_links = []
    for code, name, name_zh, cfile in COUNTRY_NAV:
        nav_links.append(f'<a href="{cfile}" title="{name} ({name_zh})">{code}</a>')
    country_nav_html = "\n    ".join(nav_links)

    embedded_catalog_json = json.dumps(catalog, ensure_ascii=False)
    initial_frames_json = json.dumps(get_initial_embedded_frames(), ensure_ascii=False)

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
    .segmented-grid {{
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      gap: 3px;
      background: #f7f5f0;
      border: 1px solid var(--border);
      border-radius: var(--radius);
      padding: 3px;
      width: 100%;
    }}
    .segmented-grid .segmented-btn {{
      text-align: center;
      padding: 5px 3px;
      font-size: 10.5px;
      line-height: 1.2;
      border-radius: 3px;
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
    .segmented-btn.btn-axis-left.active {{
      background: var(--accent);
      color: #ffffff;
    }}
    .segmented-btn.btn-axis-right.active {{
      background: var(--teal);
      color: #ffffff;
    }}

    /* Analytical Canvas View Tabs */
    .canvas-view-nav {{
      display: flex;
      align-items: center;
      gap: 4px;
      background: #f7f5f0;
      border: 1px solid var(--border);
      border-radius: var(--radius);
      padding: 3px;
      margin-bottom: 10px;
      overflow-x: auto;
    }}
    .view-tab-btn {{
      flex: 1;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      gap: 6px;
      padding: 7px 12px;
      background: transparent;
      border: none;
      border-radius: 3px;
      font-family: var(--font-body);
      font-size: 11.5px;
      font-weight: 500;
      color: var(--text-secondary);
      cursor: pointer;
      white-space: nowrap;
      transition: all 0.15s ease;
      user-select: none;
    }}
    .view-tab-btn:hover {{
      color: var(--fg);
      background: rgba(18, 21, 26, 0.04);
    }}
    .view-tab-btn.active {{
      background: var(--fg);
      color: #ffffff;
      font-weight: 600;
      box-shadow: 0 1px 2px rgba(0, 0, 0, 0.08);
    }}
    .view-tab-btn .tab-icon {{
      font-size: 13px;
    }}

    /* Quant Analytics Contextual Toolbar */
    .quant-context-bar {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
      flex-wrap: wrap;
      background: #fcfaf7;
      border: 1px solid var(--border);
      border-radius: var(--radius);
      padding: 8px 12px;
      margin-bottom: 10px;
    }}
    .quant-select-group {{
      display: inline-flex;
      align-items: center;
      gap: 12px;
      font-size: 11.5px;
      color: var(--text-secondary);
      flex-wrap: wrap;
    }}
    .quant-select {{
      padding: 4px 8px;
      font-size: 11px;
      border: 1px solid var(--border);
      border-radius: var(--radius);
      background: #ffffff;
      color: var(--fg);
      outline: none;
      max-width: 240px;
    }}
    .quant-chips-row {{
      display: inline-flex;
      align-items: center;
      gap: 6px;
      flex-wrap: wrap;
    }}
    .quant-chip {{
      display: inline-flex;
      align-items: center;
      gap: 4px;
      padding: 3px 8px;
      background: #ffffff;
      border: 1px solid var(--border);
      border-radius: 4px;
      font-size: 11px;
      font-variant-numeric: tabular-nums;
      color: var(--text-secondary);
    }}
    .quant-chip strong {{
      color: var(--fg);
    }}
    .quant-chip.accent {{
      border-color: rgba(153, 15, 61, 0.25);
      background: rgba(153, 15, 61, 0.04);
      color: var(--accent);
    }}
    .quant-chip.teal {{
      border-color: rgba(13, 118, 128, 0.25);
      background: rgba(13, 118, 128, 0.04);
      color: var(--teal);
    }}

    /* Percentile progress track in summary table */
    .percentile-cell {{
      display: flex;
      align-items: center;
      gap: 6px;
      width: 90px;
    }}
    .pct-track {{
      flex: 1;
      height: 5px;
      background: rgba(18, 21, 26, 0.08);
      border-radius: 3px;
      overflow: hidden;
      position: relative;
    }}
    .pct-fill {{
      height: 100%;
      border-radius: 3px;
      transition: width 0.3s ease;
    }}
    .zscore-tag {{
      display: inline-block;
      font-weight: 700;
      font-size: 11px;
      font-variant-numeric: tabular-nums;
      padding: 1px 5px;
      border-radius: 3px;
    }}

    .card-axis-pill {{
      display: inline-flex;
      align-items: center;
      font-size: 10px;
      font-weight: 600;
      padding: 1px 6px;
      border-radius: 3px;
      letter-spacing: 0.2px;
      margin-left: 6px;
    }}
    .card-axis-pill.badge-left {{
      background: rgba(153, 15, 61, 0.08);
      color: var(--accent);
      border: 1px solid rgba(153, 15, 61, 0.22);
    }}
    .card-axis-pill.badge-right {{
      background: rgba(13, 118, 128, 0.08);
      color: var(--teal);
      border: 1px solid rgba(13, 118, 128, 0.22);
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
      white-space: nowrap;
    }}
    .action-button:hover {{
      background: #fcfaf7;
      border-color: var(--border-strong);
    }}
    .action-button.action-accent {{
      background: var(--accent);
      color: #ffffff;
      border-color: var(--accent);
    }}
    .action-button.action-accent:hover {{
      background: #7d0c32;
    }}
    .action-button.action-teal {{
      background: var(--teal);
      color: #ffffff;
      border-color: var(--teal);
    }}
    .action-button.action-teal:hover {{
      background: #095860;
    }}

    /* Chart Header Bar */
    .chart-header-bar {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 16px;
      background: #fcfaf7;
      border: 1px solid var(--border);
      border-radius: var(--radius);
      padding: 10px 14px;
    }}
    .chart-title-input {{
      width: 100%;
      font-family: var(--font-display);
      font-size: 16px;
      font-weight: 600;
      color: var(--fg);
      background: transparent;
      border: 1px solid transparent;
      padding: 4px 6px;
      border-radius: var(--radius);
      outline: none;
      transition: all 0.15s ease;
    }}
    .chart-title-input:hover {{
      background: #ffffff;
      border-color: var(--border);
    }}
    .chart-title-input:focus {{
      background: #ffffff;
      border-color: var(--accent);
    }}
    .chart-title-hint {{
      font-size: 11px;
      color: var(--muted);
      padding-left: 6px;
    }}

    /* Indicator Inline Search Input */
    .indicator-search-input {{
      width: 100%;
      padding: 5px 8px;
      background: #f7f5f0;
      border: 1px solid var(--border);
      border-bottom: none;
      border-radius: var(--radius) var(--radius) 0 0;
      font-size: 11px;
      color: var(--fg);
      font-family: var(--font-body);
      outline: none;
      transition: all 0.15s ease;
    }}
    .indicator-search-input:focus {{
      background: #ffffff;
      border-color: var(--accent);
    }}
    select.searchable-select {{
      border-radius: 0 0 var(--radius) var(--radius) !important;
    }}

    /* Presets Panel Groupings */
    .presets-section {{
      display: flex;
      flex-direction: column;
      gap: 12px;
    }}
    .presets-group-title {{
      font-size: 11px;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      color: var(--muted);
      display: flex;
      align-items: center;
      gap: 6px;
    }}
    .preset-del-btn {{
      background: transparent;
      border: none;
      color: var(--muted);
      font-size: 11px;
      padding: 0 2px;
      margin-left: 4px;
      cursor: pointer;
      border-radius: 2px;
      line-height: 1;
      transition: color 0.15s ease;
    }}
    .preset-del-btn:hover {{
      color: var(--accent);
    }}
    .empty-custom-note {{
      font-size: 12px;
      color: var(--muted);
      font-style: italic;
      padding: 4px 0;
    }}

    /* FT/Claude Toast Notifications */
    .toast-container {{
      position: fixed;
      bottom: 24px;
      right: 24px;
      z-index: 9999;
      display: flex;
      flex-direction: column;
      gap: 8px;
      pointer-events: none;
    }}
    .toast {{
      background: #12151a;
      color: #ffffff;
      padding: 11px 18px;
      border-radius: 4px;
      font-size: 12px;
      font-weight: 500;
      box-shadow: 0 4px 16px rgba(0, 0, 0, 0.20);
      display: flex;
      align-items: center;
      gap: 8px;
      pointer-events: auto;
      opacity: 0;
      transform: translateY(12px);
      transition: all 0.25s cubic-bezier(0.16, 1, 0.3, 1);
      border-left: 3px solid var(--accent);
    }}
    .toast.show {{
      opacity: 1;
      transform: translateY(0);
    }}
    .toast-icon {{
      font-size: 14px;
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
  <a href="index.html" class="brand">East Meridian <span>/ Macro Dashboard</span></a>
  <nav class="country-nav" aria-label="country dashboards">
    {country_nav_html}
    <a href="chart_studio.html" class="active" title="Macro Chart Studio · 宏观图表工坊">📈 Studio</a>
    <a href="my_dashboard.html" title="My Dashboard · 我的自选宏观看板">⭐ My Dashboard</a>
    <a href="policy_tracker.html" title="Central Bank Policy & Event Tracker · 全球央行与宏观事件追踪">🏛️ Policy</a>
  </nav>
  <div class="topbar-actions">
    <a href="index.html" class="topbar-btn">← <span data-lang="en">Home</span><span data-lang="zh">首页</span></a>
    <button class="topbar-btn" onclick="toggleLang()" id="lang-btn">中文</button>
  </div>
</div>

<main class="container">

  <!-- Editorial Header -->
  <header class="studio-header">
    <p class="eyebrow"><span data-lang="en">Macro Chart Studio · Cross-Country Workbench</span><span data-lang="zh">宏观专业图表工坊 · 跨国多序列画板</span></p>
    <h1><span data-lang="en">Interactive Macro Chart Studio</span><span data-lang="zh">多指标自定义对比图表工坊</span></h1>
    <p class="subtitle">
      <span data-lang="en">Overlay up to 5 macroeconomic time series across 18 economies onto a unified canvas. Supports dual Y-axis scaling, base-100 re-indexing, cross-country spread calculation, and publication-quality PNG / SVG exports with full CSV dataset download.</span>
      <span data-lang="zh">在统一画布上自由叠加对比 18 个经济体的至多 5 条宏观时间序列。支持左/右双 Y 轴自由指派、基期 100 归一化发散度对比、跨国跨序列利差差值分析，以及出版级高清图表 (PNG/SVG) 与完整 CSV/JSON 数据导出。</span>
    </p>
    <div class="meta-row">
      <span class="meta-chip"><strong>18</strong> <span data-lang="en">Economies</span><span data-lang="zh">覆盖经济体</span></span>
      <span class="meta-chip"><strong>{catalog['total_indicators']}</strong> <span data-lang="en">Standardized Series</span><span data-lang="zh">标准化序列</span></span>
      <span class="meta-chip"><strong style="color:var(--accent);">Dual Y-Axis</strong> <span data-lang="en">Independent Scaling</span><span data-lang="zh">双 Y 轴支持</span></span>
      <span class="meta-chip"><strong style="color:var(--teal);">Spread & Rebase</strong> <span data-lang="en">Macro Transforms</span><span data-lang="zh">利差与归一化</span></span>
    </div>
  </header>

  <!-- Curated & Custom Presets Panel -->
  <section class="section-card">
    <div class="card-header">
      <div class="card-title">
        <span>★</span>
        <span data-lang="en">Analysis Presets & Saved Views</span><span data-lang="zh">经典专题预设与个人视角</span>
      </div>
      <div class="card-desc">
        <span data-lang="en">Click any preset to instantly load multi-series setups, or save your current view</span>
        <span data-lang="zh">点击一键加载跨境利差、核心央行政策利率与增长动能对比，亦可保存个人专属视角</span>
      </div>
    </div>
    <div class="presets-section">
      <div class="presets-group-title">
        <span>★</span>
        <span data-lang="en">Curated Macro Presets</span><span data-lang="zh">经典宏观专题预设</span>
      </div>
      <div class="presets-list" id="curated-presets-container">
        <!-- Injected via JS -->
      </div>
      <div class="presets-group-title" style="margin-top: 6px;">
        <span>⭐</span>
        <span data-lang="en">My Saved Views (Browser LocalStorage)</span><span data-lang="zh">我的保存视图 (本地持久化)</span>
      </div>
      <div class="presets-list" id="custom-presets-container">
        <!-- Injected via JS -->
      </div>
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
        <div class="segmented-grid" id="transform-group">
          <button type="button" class="segmented-btn active" data-transform="raw" onclick="setTransform('raw')">
            <span data-lang="en">Raw Level</span>
            <span data-lang="zh">原始数值</span>
          </button>
          <button type="button" class="segmented-btn" data-transform="rebase" onclick="setTransform('rebase')">
            <span data-lang="en">Base = 100</span>
            <span data-lang="zh">基期归一</span>
          </button>
          <button type="button" class="segmented-btn" data-transform="spread" onclick="setTransform('spread')">
            <span data-lang="en">Spread S1-S2</span>
            <span data-lang="zh">利差分析</span>
          </button>
          <button type="button" class="segmented-btn" data-transform="zscore" onclick="setTransform('zscore')">
            <span data-lang="en">Z-Score</span>
            <span data-lang="zh">Z-Score</span>
          </button>
          <button type="button" class="segmented-btn" data-transform="yoy" onclick="setTransform('yoy')">
            <span data-lang="en">YoY Δ</span>
            <span data-lang="zh">同比变化</span>
          </button>
          <button type="button" class="segmented-btn" data-transform="pct_change" onclick="setTransform('pct_change')">
            <span data-lang="en">% Return</span>
            <span data-lang="zh">区间涨跌</span>
          </button>
        </div>
      </div>
    </div>

    <!-- Right Chart Canvas Panel -->
    <div class="canvas-panel">
      <div id="canvas-loading" class="loading-veil" style="display: none;">
        <span>Loading observations & rendering...</span>
      </div>

      <!-- Analytical View Switcher Tabs -->
      <div class="canvas-view-nav" id="canvas-view-nav">
        <button type="button" class="view-tab-btn active" data-view="timeseries" onclick="switchCanvasView('timeseries')">
          <span class="tab-icon">📈</span>
          <span data-lang="en">Time Series Canvas</span><span data-lang="zh">多维时序主画板</span>
        </button>
        <button type="button" class="view-tab-btn" data-view="scatter_ols" onclick="switchCanvasView('scatter_ols')">
          <span class="tab-icon">🎯</span>
          <span data-lang="en">Scatter & OLS Regression</span><span data-lang="zh">散点分布与 OLS 回归</span>
        </button>
        <button type="button" class="view-tab-btn" data-view="correlation" onclick="switchCanvasView('correlation')">
          <span class="tab-icon">🔥</span>
          <span data-lang="en">Correlation Matrix & Rolling</span><span data-lang="zh">相关性矩阵与滚动相关</span>
        </button>
        <button type="button" class="view-tab-btn" data-view="lead_lag" onclick="switchCanvasView('lead_lag')">
          <span class="tab-icon">⏱️</span>
          <span data-lang="en">Lead-Lag Cross-Correlation</span><span data-lang="zh">领先-滞后时序分析</span>
        </button>
      </div>

      <!-- Quant Analytics Contextual Toolbar (Dynamic based on active view) -->
      <div id="quant-context-bar" class="quant-context-bar" style="display: none;"></div>

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
            <span data-lang="en">PNG</span><span data-lang="zh">PNG</span>
          </button>
          <button type="button" class="action-button" onclick="exportSVG()" title="Export vector SVG graphic">
            <span>📐</span>
            <span data-lang="en">SVG</span><span data-lang="zh">SVG</span>
          </button>
          <button type="button" class="action-button" onclick="exportCSV()" title="Export aligned CSV dataset">
            <span>📥</span>
            <span data-lang="en">CSV</span><span data-lang="zh">CSV</span>
          </button>
          <button type="button" class="action-button" onclick="exportJSON()" title="Export structured JSON dataset">
            <span>💾</span>
            <span data-lang="en">JSON</span><span data-lang="zh">JSON</span>
          </button>
          <button type="button" class="action-button action-accent" onclick="promptSavePreset()" title="Save current view to My Presets">
            <span>⭐</span>
            <span data-lang="en">Save View</span><span data-lang="zh">保存视图</span>
          </button>
          <button type="button" class="action-button action-teal" onclick="pinToMyDashboard()" title="Pin active series to My Dashboard">
            <span>📌</span>
            <span data-lang="en">Pin to Dashboard</span><span data-lang="zh">钉选到自选</span>
          </button>
          <button type="button" class="action-button action-teal" onclick="copyShareURL()" title="Copy shareable link with current view state">
            <span>🔗</span>
            <span data-lang="en">Share</span><span data-lang="zh">分享链接</span>
          </button>
        </div>
      </div>

      <!-- Chart Header Bar (Editable Custom Title) -->
      <div class="chart-header-bar">
        <div style="flex: 1; display: flex; flex-direction: column; gap: 4px;">
          <input type="text" id="chart-title-input" class="chart-title-input"
                 placeholder="输入自定义图表标题 (如: 欧美10年期基准国债收益率与利差对比)..."
                 oninput="onTitleInput(this.value)"
                 onblur="refreshChart()">
          <span class="chart-title-hint">
            <span data-lang="en">Custom title and official source watermark are embedded directly into canvas and exported images (PNG/SVG).</span>
            <span data-lang="zh">自定义标题与官方权威数据源水印将实时嵌入画布及导出的出版级高清图像 (PNG/SVG)。</span>
          </span>
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
                <th><span data-lang="en">Percentile</span><span data-lang="zh">历史分位数</span></th>
                <th><span data-lang="en">Z-Score</span><span data-lang="zh">当前 Z 值</span></th>
                <th><span data-lang="en">Mean ± Std</span><span data-lang="zh">均值 ± 标准差</span></th>
                <th><span data-lang="en">Min ~ Max</span><span data-lang="zh">极值范围</span></th>
                <th><span data-lang="en">Period Δ (%)</span><span data-lang="zh">区间变动</span></th>
                <th><span data-lang="en">Skew</span><span data-lang="zh">偏度</span></th>
                <th><span data-lang="en">Axis</span><span data-lang="zh">坐标轴</span></th>
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
    <div>East Meridian Macro Dashboard · Macro Chart Studio · Financial Times & Claude UI Design System.</div>
    <div>Research artefact only, not investment advice.</div>
  </footer>

  <div class="toast-container" id="toast-container"></div>
</main>

<script>
// Embedded Catalog & Initial Frames Cache for Fail-Safe Instant Rendering
const EMBEDDED_CATALOG = {embedded_catalog_json};
const INITIAL_EMBEDDED_FRAMES = {initial_frames_json};

// State Management
let CATALOG = EMBEDDED_CATALOG;
let FRAME_CACHE = Object.assign({{}}, INITIAL_EMBEDDED_FRAMES);
let ACTIVE_SERIES = [];
let CURRENT_TRANSFORM = 'raw';
let CURRENT_RANGE = '5y';
let CURRENT_LANG = 'en';
let CURRENT_CANVAS_VIEW = 'timeseries';
let SCATTER_X_IDX = 0;
let SCATTER_Y_IDX = 1;

const FT_PALETTE = ["#990f3d", "#0d7680", "#d97706", "#364b61", "#593380"];

// Initialization
async function init() {{
  try {{
    // If embedded catalog is missing, fetch remotely
    if (!CATALOG || !CATALOG.countries) {{
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
    }}
    renderPresets();

    // Check URL parameters or hash
    if (window.location.hash && window.location.hash.length > 3) {{
      loadFromHash(window.location.hash);
    }} else {{
      loadPreset(CATALOG.presets[0]);
    }}
  }} catch (err) {{
    console.error("Failed to initialize catalog:", err);
  }}
}}

let CHART_CUSTOM_TITLE = '';
const STORAGE_KEY = 'macro_chart_studio_custom_presets_v1';

function showToast(message, icon = '✓') {{
  const container = document.getElementById('toast-container');
  if (!container) return;
  const toast = document.createElement('div');
  toast.className = 'toast';
  toast.innerHTML = `<span class="toast-icon">${{icon}}</span><span>${{message}}</span>`;
  container.appendChild(toast);
  setTimeout(() => toast.classList.add('show'), 15);
  setTimeout(() => {{
    toast.classList.remove('show');
    setTimeout(() => toast.remove(), 350);
  }}, 3200);
}}

function getEffectiveTitle() {{
  if (CHART_CUSTOM_TITLE && CHART_CUSTOM_TITLE.trim()) {{
    return CHART_CUSTOM_TITLE.trim();
  }}
  if (window._CURRENT_PRESET_TITLE && window._CURRENT_PRESET_TITLE.trim()) {{
    return window._CURRENT_PRESET_TITLE.trim();
  }}
  if (ACTIVE_SERIES.length > 0) {{
    const names = ACTIVE_SERIES.map(s => {{
      const frame = FRAME_CACHE[s.country] || {{}};
      const raw = frame[s.indicatorId];
      const meta = raw ? (raw.metadata || raw) : {{}};
      const lbl = (CURRENT_LANG === 'zh' ? meta.label_zh : meta.label_en) || s.indicatorId;
      return `${{s.country}} ${{lbl}}`;
    }});
    if (CURRENT_TRANSFORM === 'spread' && names.length >= 2) {{
      return `Spread: ${{names[0]}} vs ${{names[1]}}`;
    }}
    return names.slice(0, 2).join(' vs ') + (names.length > 2 ? ` (+${{names.length - 2}})` : '');
  }}
  return CURRENT_LANG === 'zh' ? '宏观图表工坊 · 多指标对比' : 'Macro Chart Studio · Multi-Series View';
}}

function onTitleInput(val) {{
  CHART_CUSTOM_TITLE = val;
  clearTimeout(window._titleTimer);
  window._titleTimer = setTimeout(() => {{
    syncHash();
  }}, 500);
}}

function getCustomPresets() {{
  try {{
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? JSON.parse(raw) : [];
  }} catch (e) {{
    console.warn("Could not read custom presets from localStorage:", e);
    return [];
  }}
}}

function saveCustomPresets(list) {{
  try {{
    localStorage.setItem(STORAGE_KEY, JSON.stringify(list));
  }} catch (e) {{
    console.warn("Could not save custom presets to localStorage:", e);
  }}
}}

function promptSavePreset() {{
  const currentTitle = CHART_CUSTOM_TITLE || getEffectiveTitle();
  const promptText = CURRENT_LANG === 'zh' ? '请输入自定义视图名称：' : 'Enter a name for this custom view:';
  const name = prompt(promptText, currentTitle);
  if (!name || !name.trim()) return;

  const newPreset = {{
    id: 'user_' + Date.now(),
    title_en: name.trim(),
    title_zh: name.trim(),
    custom_title: name.trim(),
    transform: CURRENT_TRANSFORM,
    date_range: CURRENT_RANGE,
    series: ACTIVE_SERIES.map(s => ({{
      country: s.country,
      id: s.indicatorId,
      axis: s.axis || 'left'
    }}))
  }};

  const list = getCustomPresets();
  list.unshift(newPreset);
  saveCustomPresets(list);
  renderPresets();
  showToast(CURRENT_LANG === 'zh' ? `已保存自定义预设：「${{name.trim()}}」` : `Saved custom view: "${{name.trim()}}"`, '⭐');
}}

function pinToMyDashboard() {{
  if (!ACTIVE_SERIES.length) {{
    alert(CURRENT_LANG === 'zh' ? '当前没有加载任何时间序列' : 'No series currently active.');
    return;
  }}
  const storageKey = 'macro_my_dashboard_watchlist_v1';
  let list = [];
  try {{
    const raw = localStorage.getItem(storageKey);
    if (raw) list = JSON.parse(raw);
  }} catch(e) {{}}

  let addedCount = 0;
  ACTIVE_SERIES.forEach(s => {{
    if (!list.some(item => item.country === s.country && item.id === s.indicatorId)) {{
      list.push({{
        type: 'indicator',
        country: s.country,
        id: s.indicatorId,
        notes: `Pinned from Chart Studio (${{getEffectiveTitle()}})`
      }});
      addedCount++;
    }}
  }});

  if (addedCount > 0) {{
    localStorage.setItem(storageKey, JSON.stringify(list));
    showToast(CURRENT_LANG === 'zh' ? `已成功将 ${{addedCount}} 个指标钉选到自选看板！` : `Pinned ${{addedCount}} indicator(s) to My Dashboard!`, '⭐');
  }} else {{
    showToast(CURRENT_LANG === 'zh' ? '所选指标已全部在自选看板中！' : 'Selected indicator(s) already in My Dashboard!', '✓');
  }}
}}

function deleteCustomPreset(e, id) {{
  e.stopPropagation();
  const confirmMsg = CURRENT_LANG === 'zh' ? '确定删除此自定义预设吗？' : 'Delete this custom view?';
  if (!confirm(confirmMsg)) return;

  let list = getCustomPresets();
  list = list.filter(p => p.id !== id);
  saveCustomPresets(list);
  renderPresets();
  showToast(CURRENT_LANG === 'zh' ? '已删除该自定义预设' : 'Preset deleted', '🗑️');
}}

function renderPresets() {{
  const curatedContainer = document.getElementById('curated-presets-container');
  const customContainer = document.getElementById('custom-presets-container');
  if (curatedContainer) {{
    curatedContainer.innerHTML = '';
    CATALOG.presets.forEach(p => {{
      const btn = document.createElement('div');
      btn.className = 'preset-pill';
      const title = CURRENT_LANG === 'zh' ? p.title_zh : p.title_en;
      btn.innerHTML = `<span class="star">★</span><span>${{title}}</span>`;
      btn.onclick = () => loadPreset(p);
      curatedContainer.appendChild(btn);
    }});
  }}

  if (customContainer) {{
    customContainer.innerHTML = '';
    const customs = getCustomPresets();
    if (customs.length === 0) {{
      const emptyNote = document.createElement('span');
      emptyNote.className = 'empty-custom-note';
      emptyNote.textContent = CURRENT_LANG === 'zh'
        ? '暂无保存的自定义视图。配置完指标后，点击右侧工具栏「⭐ 保存视图」即可存入浏览器。'
        : 'No saved views yet. Configure series and click "⭐ Save View" in the toolbar to save here.';
      customContainer.appendChild(emptyNote);
    }} else {{
      customs.forEach(p => {{
        const btn = document.createElement('div');
        btn.className = 'preset-pill custom-preset-pill';
        const title = CURRENT_LANG === 'zh' ? p.title_zh : p.title_en;
        btn.innerHTML = `
          <span class="star" style="color:var(--accent);">⭐</span>
          <span>${{title}}</span>
          <button type="button" class="preset-del-btn" title="${{CURRENT_LANG === 'zh' ? '删除预设' : 'Delete preset'}}" onclick="deleteCustomPreset(event, '${{p.id}}')">✕</button>
        `;
        btn.onclick = () => loadPreset(p);
        customContainer.appendChild(btn);
      }});
    }}
  }}
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
  CURRENT_CANVAS_VIEW = preset.view || 'timeseries';
  SCATTER_X_IDX = 0;
  SCATTER_Y_IDX = ACTIVE_SERIES.length > 1 ? 1 : 0;
  CHART_CUSTOM_TITLE = (CURRENT_LANG === 'zh' ? preset.title_zh : preset.title_en) || preset.custom_title || '';
  window._CURRENT_PRESET_TITLE = CHART_CUSTOM_TITLE;

  const titleInput = document.getElementById('chart-title-input');
  if (titleInput) {{
    titleInput.value = CHART_CUSTOM_TITLE;
  }}

  updateControlsUI();
  refreshChart();
}}

function updateControlsUI() {{
  // Update view navigation tabs
  document.querySelectorAll('#canvas-view-nav .view-tab-btn').forEach(btn => {{
    btn.classList.toggle('active', btn.dataset.view === CURRENT_CANVAS_VIEW);
  }});
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

function filterIndicatorDropdown(idx, query) {{
  const select = document.getElementById(`select-ind-${{idx}}`);
  if (!select) return;
  const q = (query || '').toLowerCase().trim();
  const cData = CATALOG.countries.find(c => c.code === ACTIVE_SERIES[idx].country);
  if (!cData) return;

  const optgroups = select.querySelectorAll('optgroup');
  let firstVisibleVal = null;
  let matchesCount = 0;

  optgroups.forEach(group => {{
    let groupHasVisible = false;
    group.querySelectorAll('option').forEach(opt => {{
      const text = opt.textContent.toLowerCase();
      const val = opt.value.toLowerCase();
      const match = !q || text.includes(q) || val.includes(q);
      if (match) {{
        opt.hidden = false;
        opt.disabled = false;
        groupHasVisible = true;
        matchesCount++;
        if (!firstVisibleVal) firstVisibleVal = opt.value;
      }} else {{
        opt.hidden = true;
        opt.disabled = true;
      }}
    }});
    group.hidden = !groupHasVisible;
  }});

  const countBadge = document.getElementById(`ind-count-${{idx}}`);
  if (countBadge) {{
    countBadge.textContent = q
      ? `${{matchesCount}} ${{CURRENT_LANG === 'zh' ? '个匹配' : 'matches'}}`
      : `${{cData.indicators.length}} ${{CURRENT_LANG === 'zh' ? '个序列' : 'series'}}`;
  }}
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

    // Validate that indicatorId exists in this country; fallback to first indicator if not
    if (cData && cData.indicators && cData.indicators.length > 0) {{
      const exists = cData.indicators.some(ind => ind.id === item.indicatorId);
      if (!exists) {{
        item.indicatorId = cData.indicators[0].id;
      }}
    }}

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

    const isRightAxis = (item.axis === 'right');
    const axisPillClass = isRightAxis ? 'badge-right' : 'badge-left';
    const axisPillText = isRightAxis ? (CURRENT_LANG === 'zh' ? '右轴 · Y2' : 'Right · Y2') : (CURRENT_LANG === 'zh' ? '左轴 · Y1' : 'Left · Y1');

    card.innerHTML = `
      <div class="series-card-top">
        <div class="series-tag">
          <span class="series-color-bullet" style="background: ${{item.color}};"></span>
          <span>S${{idx + 1}} · ${{cData ? cData.flag : ''}} ${{item.country}}</span>
          <span class="card-axis-pill ${{axisPillClass}}">${{axisPillText}}</span>
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
            <button type="button" class="segmented-btn btn-axis-left ${{!isRightAxis ? 'active' : ''}}" onclick="setSeriesAxis(${{idx}}, 'left')">
              ← Y1 (${{CURRENT_LANG === 'zh' ? '左' : 'Left'}})
            </button>
            <button type="button" class="segmented-btn btn-axis-right ${{isRightAxis ? 'active' : ''}}" onclick="setSeriesAxis(${{idx}}, 'right')">
              Y2 (${{CURRENT_LANG === 'zh' ? '右' : 'Right'}}) →
            </button>
          </div>
        </div>
      </div>
      <div class="form-group">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px;">
          <span class="form-label" style="margin-bottom:0;">${{CURRENT_LANG === 'zh' ? '选择指标' : 'Indicator'}}</span>
          <span id="ind-count-${{idx}}" style="font-size: 10px; color: var(--muted); font-weight: 500;">
            ${{cData ? cData.indicators.length : 0}} ${{CURRENT_LANG === 'zh' ? '个序列' : 'series'}}
          </span>
        </div>
        <input type="text" class="indicator-search-input" id="search-ind-${{idx}}"
               placeholder="${{CURRENT_LANG === 'zh' ? '🔍 过滤指标 (输入名称/单位)...' : '🔍 Filter indicators (name/id)...'}}"
               oninput="filterIndicatorDropdown(${{idx}}, this.value)">
        <select id="select-ind-${{idx}}" class="searchable-select" onchange="onIndicatorChange(${{idx}}, this.value)">
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
  CURRENT_CANVAS_VIEW = 'timeseries';
  updateControlsUI();
  refreshChart();
}}

function switchCanvasView(viewName) {{
  CURRENT_CANVAS_VIEW = viewName;
  updateControlsUI();
  refreshChart();
}}

function onScatterVarChange(varType, val) {{
  const idx = parseInt(val, 10);
  if (isNaN(idx)) return;
  if (varType === 'x') SCATTER_X_IDX = idx;
  if (varType === 'y') SCATTER_Y_IDX = idx;
  refreshChart();
}}

// Mathematical & Statistical Analytics Engine
function alignTwoSeries(s1Obs, s2Obs) {{
  if (!s1Obs || !s2Obs || s1Obs.length === 0 || s2Obs.length === 0) return [];
  const map2 = new Map(s2Obs.map(o => [o.date, o.value]));
  const matched = [];
  s1Obs.forEach(o1 => {{
    if (map2.has(o1.date)) {{
      matched.push({{ date: o1.date, x: o1.value, y: map2.get(o1.date) }});
    }}
  }});
  if (matched.length >= 8) return matched;

  // Month-level alignment fallback (daily vs monthly or cross-frequency)
  const s1Month = new Map();
  s1Obs.forEach(o => s1Month.set(o.date.slice(0, 7), o.value));
  const s2Month = new Map();
  s2Obs.forEach(o => s2Month.set(o.date.slice(0, 7), o.value));
  const commonMonths = [...s1Month.keys()].filter(m => s2Month.has(m)).sort();
  return commonMonths.map(m => ({{ date: m, x: s1Month.get(m), y: s2Month.get(m) }}));
}}

function computeStats(obsList) {{
  if (!obsList || obsList.length === 0) return null;
  const vals = obsList.map(o => o.value).filter(v => typeof v === 'number' && !isNaN(v));
  if (vals.length === 0) return null;
  const N = vals.length;
  const sum = vals.reduce((a, b) => a + b, 0);
  const mean = sum / N;
  const sqDiffs = vals.map(v => (v - mean) ** 2);
  const variance = N > 1 ? sqDiffs.reduce((a, b) => a + b, 0) / (N - 1) : 0;
  const std = Math.sqrt(variance);
  const min = Math.min(...vals);
  const max = Math.max(...vals);
  const latestObs = obsList[obsList.length - 1];
  const latest = latestObs.value;
  const first = vals[0];
  const periodDelta = latest - first;
  const periodPct = first !== 0 ? ((latest - first) / Math.abs(first)) * 100 : 0;
  const countLessEqual = vals.filter(v => v <= latest).length;
  const percentile = (countLessEqual / N) * 100;
  const zScore = std > 0 ? (latest - mean) / std : 0;
  const cubeDiffs = vals.map(v => (v - mean) ** 3);
  const skewness = (std > 0 && N > 2) ? (cubeDiffs.reduce((a, b) => a + b, 0) / N) / (std ** 3) : 0;
  return {{
    count: N,
    mean: mean,
    std: std,
    min: min,
    max: max,
    latest: latest,
    latestDate: latestObs.date,
    periodDelta: periodDelta,
    periodPct: periodPct,
    percentile: Math.min(100, Math.max(0, percentile)),
    zScore: zScore,
    skewness: skewness
  }};
}}

function computeOLS(points) {{
  if (!points || points.length < 3) return null;
  const N = points.length;
  const xs = points.map(p => p.x);
  const ys = points.map(p => p.y);
  const xMean = xs.reduce((a, b) => a + b, 0) / N;
  const yMean = ys.reduce((a, b) => a + b, 0) / N;

  let cov = 0;
  let varX = 0;
  let varY = 0;
  for (let i = 0; i < N; i++) {{
    const dx = xs[i] - xMean;
    const dy = ys[i] - yMean;
    cov += dx * dy;
    varX += dx * dx;
    varY += dy * dy;
  }}

  if (varX === 0 || varY === 0) return null;
  const beta = cov / varX;
  const alpha = yMean - beta * xMean;
  const r = cov / Math.sqrt(varX * varY);
  const r2 = r * r;

  const minX = Math.min(...xs);
  const maxX = Math.max(...xs);
  return {{
    beta: beta,
    alpha: alpha,
    r: r,
    r2: r2,
    count: N,
    lineX: [minX, maxX],
    lineY: [beta * minX + alpha, beta * maxX + alpha]
  }};
}}

function computeCrossCorrelation(points, maxLag = 12) {{
  if (!points || points.length < 8) return null;
  const N = points.length;
  const xs = points.map(p => p.x);
  const ys = points.map(p => p.y);
  const lags = [];
  const corrs = [];

  for (let lag = -maxLag; lag <= maxLag; lag++) {{
    lags.push(lag);
    let curX = [];
    let curY = [];
    if (lag < 0) {{
      const absLag = Math.abs(lag);
      for (let i = 0; i < N - absLag; i++) {{
        curX.push(xs[i + absLag]);
        curY.push(ys[i]);
      }}
    }} else if (lag > 0) {{
      for (let i = 0; i < N - lag; i++) {{
        curX.push(xs[i]);
        curY.push(ys[i + lag]);
      }}
    }} else {{
      curX = xs;
      curY = ys;
    }}

    if (curX.length < 5) {{
      corrs.push(0);
      continue;
    }}
    const xM = curX.reduce((a, b) => a + b, 0) / curX.length;
    const yM = curY.reduce((a, b) => a + b, 0) / curY.length;
    let cov = 0, vx = 0, vy = 0;
    for (let i = 0; i < curX.length; i++) {{
      const dx = curX[i] - xM;
      const dy = curY[i] - yM;
      cov += dx * dy;
      vx += dx * dx;
      vy += dy * dy;
    }}
    const r = (vx > 0 && vy > 0) ? cov / Math.sqrt(vx * vy) : 0;
    corrs.push(r);
  }}

  let peakLag = 0;
  let peakR = corrs[maxLag];
  let maxAbsR = Math.abs(peakR);
  for (let i = 0; i < corrs.length; i++) {{
    if (Math.abs(corrs[i]) > maxAbsR) {{
      maxAbsR = Math.abs(corrs[i]);
      peakR = corrs[i];
      peakLag = lags[i];
    }}
  }}

  return {{
    lags: lags,
    corrs: corrs,
    peakLag: peakLag,
    peakR: peakR,
    zeroLagR: corrs[maxLag]
  }};
}}

function computeRollingCorrelation(points, windowSize = 60) {{
  if (!points || points.length < 15) return [];
  const N = points.length;
  const W = Math.min(windowSize, Math.max(15, Math.floor(N / 3)));
  const rolling = [];
  for (let i = W - 1; i < N; i++) {{
    const windowSlice = points.slice(i - W + 1, i + 1);
    const xs = windowSlice.map(p => p.x);
    const ys = windowSlice.map(p => p.y);
    const xM = xs.reduce((a, b) => a + b, 0) / W;
    const yM = ys.reduce((a, b) => a + b, 0) / W;
    let cov = 0, vx = 0, vy = 0;
    for (let j = 0; j < W; j++) {{
      const dx = xs[j] - xM;
      const dy = ys[j] - yM;
      cov += dx * dy;
      vx += dx * dx;
      vy += dy * dy;
    }}
    const r = (vx > 0 && vy > 0) ? cov / Math.sqrt(vx * vy) : 0;
    rolling.push({{ date: points[i].date, r: Math.max(-1, Math.min(1, r)) }});
  }}
  return rolling;
}}

function computeCorrelationMatrix(seriesList) {{
  const K = seriesList.length;
  const matrix = Array.from({{ length: K }}, () => Array(K).fill(1.0));
  const shortLabels = seriesList.map(s => `${{s.country}}:${{s.config.indicatorId}}`);
  const offDiagCorrs = [];

  for (let i = 0; i < K; i++) {{
    for (let j = 0; j < K; j++) {{
      if (i === j) {{
        matrix[i][j] = 1.0;
      }} else if (i < j) {{
        const paired = alignTwoSeries(seriesList[i].filteredObs, seriesList[j].filteredObs);
        let r = 0;
        if (paired.length >= 3) {{
          const xs = paired.map(p => p.x);
          const ys = paired.map(p => p.y);
          const xM = xs.reduce((a, b) => a + b, 0) / xs.length;
          const yM = ys.reduce((a, b) => a + b, 0) / ys.length;
          let cov = 0, vx = 0, vy = 0;
          for (let k = 0; k < xs.length; k++) {{
            const dx = xs[k] - xM;
            const dy = ys[k] - yM;
            cov += dx * dy;
            vx += dx * dx;
            vy += dy * dy;
          }}
          r = (vx > 0 && vy > 0) ? cov / Math.sqrt(vx * vy) : 0;
        }}
        matrix[i][j] = Math.max(-1, Math.min(1, r));
        matrix[j][i] = matrix[i][j];
        offDiagCorrs.push(matrix[i][j]);
      }}
    }}
  }}

  const avgCorr = offDiagCorrs.length ? offDiagCorrs.reduce((a, b) => a + b, 0) / offDiagCorrs.length : 1.0;
  const maxCorr = offDiagCorrs.length ? Math.max(...offDiagCorrs) : 1.0;
  const minCorr = offDiagCorrs.length ? Math.min(...offDiagCorrs) : 1.0;

  return {{
    matrix: matrix,
    shortLabels: shortLabels,
    avgCorr: avgCorr,
    maxCorr: maxCorr,
    minCorr: minCorr
  }};
}}

function updateQuantContextBar(seriesData) {{
  const bar = document.getElementById('quant-context-bar');
  if (!bar) return;

  if (CURRENT_CANVAS_VIEW === 'timeseries') {{
    bar.style.display = 'none';
    bar.innerHTML = '';
    return;
  }}

  bar.style.display = 'flex';
  bar.innerHTML = '';

  if (seriesData.length < 2) {{
    bar.innerHTML = `
      <div style="font-size:12px; color:var(--muted); font-style:italic;">
        <span>${{CURRENT_LANG === 'zh' ? '⚠️ 当前选定序列不足 2 条。请在左侧添加至少 2 条指标以启用高级量化统计分析。' : '⚠️ Need at least 2 active series for quantitative cross-series analysis. Please add more series on the left.'}}</span>
      </div>
    `;
    return;
  }}

  if (SCATTER_X_IDX >= seriesData.length) SCATTER_X_IDX = 0;
  if (SCATTER_Y_IDX >= seriesData.length) SCATTER_Y_IDX = Math.min(1, seriesData.length - 1);
  if (SCATTER_X_IDX === SCATTER_Y_IDX && seriesData.length > 1) {{
    SCATTER_Y_IDX = (SCATTER_X_IDX + 1) % seriesData.length;
  }}

  if (CURRENT_CANVAS_VIEW === 'scatter_ols') {{
    const sX = seriesData[SCATTER_X_IDX];
    const sY = seriesData[SCATTER_Y_IDX];
    const paired = alignTwoSeries(sX.filteredObs, sY.filteredObs);
    const reg = computeOLS(paired);

    const xOptions = seriesData.map((s, idx) => `<option value="${{idx}}" ${{idx === SCATTER_X_IDX ? 'selected' : ''}}>X: ${{s.country}} - ${{s.label.split(': ')[1] || s.label}}</option>`).join('');
    const yOptions = seriesData.map((s, idx) => `<option value="${{idx}}" ${{idx === SCATTER_Y_IDX ? 'selected' : ''}}>Y: ${{s.country}} - ${{s.label.split(': ')[1] || s.label}}</option>`).join('');

    bar.innerHTML = `
      <div class="quant-select-group">
        <label><strong>X (Independent / 自变量):</strong> <select class="quant-select" onchange="onScatterVarChange('x', this.value)">${{xOptions}}</select></label>
        <label><strong>Y (Dependent / 因变量):</strong> <select class="quant-select" onchange="onScatterVarChange('y', this.value)">${{yOptions}}</select></label>
      </div>
      <div class="quant-chips-row">
        ${{reg ? `
          <span class="quant-chip accent" title="OLS Regression Equation"><strong>Ŷ = ${{reg.beta >= 0 ? '+' : ''}}${{reg.beta.toFixed(3)}}·X + ${{reg.alpha.toFixed(3)}}</strong></span>
          <span class="quant-chip" title="Beta (Sensitivity / Slope)">Beta (β): <strong>${{reg.beta.toFixed(3)}}</strong></span>
          <span class="quant-chip teal" title="Coefficient of Determination R²">R²: <strong>${{reg.r2.toFixed(3)}}</strong></span>
          <span class="quant-chip" title="Pearson Correlation Coefficient">Pearson r: <strong>${{reg.r >= 0 ? '+' : ''}}${{reg.r.toFixed(3)}}</strong></span>
          <span class="quant-chip" title="Paired Valid Sample Size">N: <strong>${{paired.length}}</strong></span>
        ` : `<span class="quant-chip" style="color:var(--muted);">Insufficient paired observations</span>`}}
      </div>
    `;
  }} else if (CURRENT_CANVAS_VIEW === 'lead_lag') {{
    const s1 = seriesData[SCATTER_X_IDX];
    const s2 = seriesData[SCATTER_Y_IDX];
    const paired = alignTwoSeries(s1.filteredObs, s2.filteredObs);
    const leadLag = computeCrossCorrelation(paired, 12);

    const s1Options = seriesData.map((s, idx) => `<option value="${{idx}}" ${{idx === SCATTER_X_IDX ? 'selected' : ''}}>S1 (Ref): ${{s.country}} - ${{s.label.split(': ')[1] || s.label}}</option>`).join('');
    const s2Options = seriesData.map((s, idx) => `<option value="${{idx}}" ${{idx === SCATTER_Y_IDX ? 'selected' : ''}}>S2 (Target): ${{s.country}} - ${{s.label.split(': ')[1] || s.label}}</option>`).join('');

    let leadText = '';
    if (leadLag && leadLag.peakLag !== 0) {{
      if (leadLag.peakLag < 0) {{
        leadText = CURRENT_LANG === 'zh'
          ? `⚡ 最佳相关点：S1 领先 S2 约 ${{Math.abs(leadLag.peakLag)}} 个周期 (r = ${{leadLag.peakR.toFixed(3)}})`
          : `⚡ Peak: S1 leads S2 by ${{Math.abs(leadLag.peakLag)}} periods (r = ${{leadLag.peakR.toFixed(3)}})`;
      }} else {{
        leadText = CURRENT_LANG === 'zh'
          ? `⚡ 最佳相关点：S2 领先 S1 约 ${{leadLag.peakLag}} 个周期 (r = ${{leadLag.peakR.toFixed(3)}})`
          : `⚡ Peak: S2 leads S1 by ${{leadLag.peakLag}} periods (r = ${{leadLag.peakR.toFixed(3)}})`;
      }}
    }} else if (leadLag) {{
      leadText = CURRENT_LANG === 'zh'
        ? `⚡ 同期相关最高：Lag 0 (r = ${{leadLag.peakR.toFixed(3)}})`
        : `⚡ Peak is contemporaneous: Lag 0 (r = ${{leadLag.peakR.toFixed(3)}})`;
    }}

    bar.innerHTML = `
      <div class="quant-select-group">
        <label><strong>Series 1:</strong> <select class="quant-select" onchange="onScatterVarChange('x', this.value)">${{s1Options}}</select></label>
        <label><strong>Series 2:</strong> <select class="quant-select" onchange="onScatterVarChange('y', this.value)">${{s2Options}}</select></label>
      </div>
      <div class="quant-chips-row">
        ${{leadLag ? `
          <span class="quant-chip accent" style="font-weight:600;">${{leadText}}</span>
          <span class="quant-chip" title="Contemporaneous correlation at lag 0">Lag 0 r: <strong>${{leadLag.zeroLagR >= 0 ? '+' : ''}}${{leadLag.zeroLagR.toFixed(3)}}</strong></span>
          <span class="quant-chip" title="Effective sample size">N: <strong>${{paired.length}}</strong></span>
        ` : `<span class="quant-chip" style="color:var(--muted);">Insufficient paired observations</span>`}}
      </div>
    `;
  }} else if (CURRENT_CANVAS_VIEW === 'correlation') {{
    const matrixRes = computeCorrelationMatrix(seriesData);
    bar.innerHTML = `
      <div class="quant-select-group">
        <span style="font-weight:600; color:var(--fg);">${{CURRENT_LANG === 'zh' ? '全景相关性矩阵与 60 期滚动相关曲线' : 'Full Pairwise Correlation Matrix & 60-Period Rolling Linkage'}}</span>
      </div>
      <div class="quant-chips-row">
        <span class="quant-chip teal" title="Average of off-diagonal correlations">Avg Corr: <strong>${{matrixRes.avgCorr >= 0 ? '+' : ''}}${{matrixRes.avgCorr.toFixed(3)}}</strong></span>
        <span class="quant-chip" title="Maximum correlation among different pairs">Max: <strong>${{matrixRes.maxCorr >= 0 ? '+' : ''}}${{matrixRes.maxCorr.toFixed(3)}}</strong></span>
        <span class="quant-chip" title="Minimum correlation among different pairs">Min: <strong>${{matrixRes.minCorr >= 0 ? '+' : ''}}${{matrixRes.minCorr.toFixed(3)}}</strong></span>
        <span class="quant-chip" title="Total active series in matrix">Active Series: <strong>${{seriesData.length}}</strong></span>
      </div>
    `;
  }}
}}

function setDateRange(range) {{
  CURRENT_RANGE = range;
  updateControlsUI();
  refreshChart();
}}

// Data Fetching & Caching
async function fetchCountryFrame(countryCode) {{
  if (FRAME_CACHE[countryCode] && Object.keys(FRAME_CACHE[countryCode]).length > 2) {{
    return FRAME_CACHE[countryCode];
  }}
  const cData = CATALOG.countries.find(c => c.code === countryCode);
  if (!cData) return FRAME_CACHE[countryCode] || {{}};

  const inOutputDir = window.location.pathname.includes('/output/');
  const prefix = inOutputDir ? '' : 'output/';
  let res;
  try {{
    res = await fetch(prefix + cData.canonical_file);
    if (!res.ok && prefix) {{
      res = await fetch(cData.canonical_file);
    }}
  }} catch (err) {{
    try {{
      res = await fetch(cData.canonical_file);
    }} catch (e2) {{
      console.warn("Could not fetch remote canonical frame:", e2);
      return FRAME_CACHE[countryCode] || {{}};
    }}
  }}
  if (!res || !res.ok) {{
    return FRAME_CACHE[countryCode] || {{}};
  }}
  const data = await res.json();
  const map = FRAME_CACHE[countryCode] || {{}};

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
  const loadingEl = document.getElementById('canvas-loading');
  if (loadingEl) loadingEl.style.display = 'flex';

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
      label = `${{cData ? cData.flag : ''}} ${{item.country}}: ${{label}}`;
      const unit = meta.unit || '';

      const rawObs = (rawSeries.observations || []).map(row => ({{
        date: String(row[0]),
        value: Number(row[1])
      }})).filter(r => !isNaN(r.value) && r.date);

      seriesData.push({{
        index: idx,
        config: item,
        label: label,
        unit: unit,
        country: item.country,
        observations: rawObs
      }});
    }});

    // 3. Filter by Date Range relative to latest observation available
    let latestObsDateStr = '';
    seriesData.forEach(s => {{
      if (s.observations.length > 0) {{
        const lastDate = s.observations[s.observations.length - 1].date;
        if (lastDate > latestObsDateStr) {{
          latestObsDateStr = lastDate;
        }}
      }}
    }});

    let cutoffStr = '0000-00-00';
    if (CURRENT_RANGE !== 'max' && latestObsDateStr) {{
      const parts = latestObsDateStr.split('-');
      const y = parseInt(parts[0], 10) || 2026;
      const m = parts[1] || '01';
      const d = parts[2] || '01';
      let yearsBack = 5;
      if (CURRENT_RANGE === '1y') yearsBack = 1;
      else if (CURRENT_RANGE === '3y') yearsBack = 3;
      else if (CURRENT_RANGE === '5y') yearsBack = 5;
      else if (CURRENT_RANGE === '10y') yearsBack = 10;

      const startYear = y - yearsBack;
      cutoffStr = `${{startYear}}-${{m}}-${{d}}`;
    }}

    seriesData.forEach(s => {{
      s.filteredObs = s.observations.filter(o => o.date >= cutoffStr);
      // Fallback: if range filter leaves 0 observations, show all
      if (s.filteredObs.length === 0 && s.observations.length > 0) {{
        s.filteredObs = s.observations;
      }}
    }});

    // 4. Update Contextual Quant Toolbar
    updateQuantContextBar(seriesData);

    // 5. Apply Transformations & Render Active View
    let plotTraces = [];
    let annotations = [];
    let shapes = [];
    let y1Title = '';
    let y2Title = '';
    let hasY2 = false;
    let layoutXTitle = '';
    let isFixedCorrelationRange = false;

    if (CURRENT_CANVAS_VIEW === 'scatter_ols') {{
      y1Title = CURRENT_LANG === 'zh' ? '散点分布与 OLS 线性回归' : 'Scatter & OLS Regression';
      if (seriesData.length < 2) {{
        plotTraces = [];
        annotations.push({{
          xref: 'paper', yref: 'paper',
          x: 0.5, y: 0.5,
          text: CURRENT_LANG === 'zh'
            ? '请在左侧添加至少 2 条指标以启用散点分布与 OLS 线性回归分析'
            : 'Please select at least 2 series to enable scatter plot & OLS regression.',
          showarrow: false,
          font: {{ size: 13, color: '#737c8c' }}
        }});
      }} else {{
        if (SCATTER_X_IDX >= seriesData.length) SCATTER_X_IDX = 0;
        if (SCATTER_Y_IDX >= seriesData.length) SCATTER_Y_IDX = Math.min(1, seriesData.length - 1);
        if (SCATTER_X_IDX === SCATTER_Y_IDX && seriesData.length > 1) {{
          SCATTER_Y_IDX = (SCATTER_X_IDX + 1) % seriesData.length;
        }}
        const sX = seriesData[SCATTER_X_IDX];
        const sY = seriesData[SCATTER_Y_IDX];
        const paired = alignTwoSeries(sX.filteredObs, sY.filteredObs);

        if (paired.length < 3) {{
          annotations.push({{
            xref: 'paper', yref: 'paper',
            x: 0.5, y: 0.5,
            text: CURRENT_LANG === 'zh'
              ? '选定序列在当前窗口内的有效对齐样本不足，无法生成散点图与回归方程'
              : 'Insufficient paired observations to generate scatter plot and OLS regression.',
            showarrow: false,
            font: {{ size: 13, color: '#737c8c' }}
          }});
        }} else {{
          const reg = computeOLS(paired);
          plotTraces.push({{
            name: `${{sX.country}} vs ${{sY.country}} (${{paired.length}} pairs)`,
            x: paired.map(p => p.x),
            y: paired.map(p => p.y),
            customdata: paired.map(p => p.date),
            yaxis: 'y',
            type: 'scatter',
            mode: 'markers',
            marker: {{
              size: 7.5,
              color: 'rgba(153, 15, 61, 0.65)',
              line: {{ width: 1.2, color: '#990f3d' }}
            }},
            hovertemplate: '<b>%{{customdata}}</b><br>X: %{{x:.2f}}<br>Y: %{{y:.2f}}<extra></extra>'
          }});

          if (reg) {{
            const regTitle = `OLS Fit: Ŷ = ${{reg.beta >= 0 ? '+' : ''}}${{reg.beta.toFixed(3)}}·X + ${{reg.alpha.toFixed(3)}} (R² = ${{reg.r2.toFixed(3)}})`;
            plotTraces.push({{
              name: regTitle,
              x: reg.lineX,
              y: reg.lineY,
              yaxis: 'y',
              type: 'scatter',
              mode: 'lines',
              line: {{ color: '#0d7680', width: 2.6 }}
            }});

            annotations.push({{
              xref: 'paper', yref: 'paper',
              x: 0.03, y: 0.95,
              xanchor: 'left', yanchor: 'top',
              text: `<b>OLS Linear Regression (普通最小二乘回归)</b><br>` +
                    `Model: <b>Ŷ = ${{reg.beta >= 0 ? '+' : ''}}${{reg.beta.toFixed(3)}} · X + ${{reg.alpha.toFixed(3)}}</b><br>` +
                    `Beta (敏感度/斜率): <b>${{reg.beta.toFixed(3)}}</b> | Alpha (截距): <b>${{reg.alpha.toFixed(3)}}</b><br>` +
                    `R² (决定系数): <b>${{reg.r2.toFixed(3)}}</b> | Pearson r (相关系数): <b>${{reg.r >= 0 ? '+' : ''}}${{reg.r.toFixed(3)}}</b><br>` +
                    `Sample Size (对齐有效样本): <b>${{paired.length}}</b>`,
              showarrow: false,
              font: {{ family: "-apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif", size: 11, color: '#12151a' }},
              bgcolor: 'rgba(255, 255, 255, 0.92)',
              bordercolor: '#0d7680',
              borderwidth: 1.2,
              borderpad: 6
            }});
          }}

          y1Title = `${{sY.country}} · ${{sY.label.split(': ')[1] || sY.label}} (${{sY.unit}})`;
          layoutXTitle = `${{sX.country}} · ${{sX.label.split(': ')[1] || sX.label}} (${{sX.unit}})`;
        }}
      }}
    }} else if (CURRENT_CANVAS_VIEW === 'correlation') {{
      if (seriesData.length < 2) {{
        plotTraces = [];
        annotations.push({{
          xref: 'paper', yref: 'paper',
          x: 0.5, y: 0.5,
          text: CURRENT_LANG === 'zh'
            ? '请在左侧添加至少 2 条指标以启用相关性分析'
            : 'Please select at least 2 series to enable correlation analysis.',
          showarrow: false,
          font: {{ size: 13, color: '#737c8c' }}
        }});
      }} else if (seriesData.length === 2) {{
        const s1 = seriesData[0];
        const s2 = seriesData[1];
        const paired = alignTwoSeries(s1.filteredObs, s2.filteredObs);
        const rolling = computeRollingCorrelation(paired, 60);

        if (rolling.length > 0) {{
          plotTraces.push({{
            name: `Rolling Correlation (S1 vs S2)`,
            x: rolling.map(r => r.date),
            y: rolling.map(r => r.r),
            yaxis: 'y',
            type: 'scatter',
            mode: 'lines',
            fill: 'tozeroy',
            fillcolor: 'rgba(13, 118, 128, 0.08)',
            line: {{ color: '#0d7680', width: 2.4 }}
          }});

          const lastR = rolling[rolling.length - 1];
          plotTraces.push({{
            name: 'Latest Correlation',
            x: [lastR.date],
            y: [lastR.r],
            yaxis: 'y',
            type: 'scatter',
            mode: 'markers',
            marker: {{ size: 8, color: '#0d7680', line: {{ width: 2, color: '#ffffff' }} }},
            showlegend: false,
            hoverinfo: 'skip'
          }});

          annotations.push({{
            x: lastR.date,
            y: lastR.r,
            xref: 'x', yref: 'y',
            text: `<b>Latest r = ${{lastR.r >= 0 ? '+' : ''}}${{lastR.r.toFixed(2)}}</b>`,
            showarrow: true,
            arrowhead: 0,
            arrowcolor: '#0d7680',
            ax: 32, ay: -12,
            font: {{ size: 11, color: '#0d7680' }},
            bgcolor: 'rgba(255, 255, 255, 0.92)',
            bordercolor: '#0d7680',
            borderwidth: 1.2,
            borderpad: 3
          }});
        }}
        y1Title = CURRENT_LANG === 'zh' ? '滚动相关系数 (Pearson r)' : 'Rolling Pearson r';
        isFixedCorrelationRange = true;
      }} else {{
        const matrixRes = computeCorrelationMatrix(seriesData);
        plotTraces.push({{
          type: 'heatmap',
          z: matrixRes.matrix,
          x: matrixRes.shortLabels,
          y: matrixRes.shortLabels,
          colorscale: [
            [0.0, '#990f3d'],
            [0.5, '#ffffff'],
            [1.0, '#0d7680']
          ],
          zmin: -1.0,
          zmax: 1.0,
          text: matrixRes.matrix.map(row => row.map(v => (v >= 0 ? '+' : '') + v.toFixed(2))),
          texttemplate: '<b>%{{text}}</b>',
          textfont: {{ family: "-apple-system, sans-serif", size: 12, color: '#12151a' }},
          colorbar: {{
            title: CURRENT_LANG === 'zh' ? '相关系数 (r)' : 'Pearson r',
            titleside: 'right',
            tickfont: {{ size: 10, color: '#4b525f' }}
          }},
          hoverongaps: false
        }});
        y1Title = CURRENT_LANG === 'zh' ? '相关性热力矩阵' : 'Correlation Matrix';
      }}
    }} else if (CURRENT_CANVAS_VIEW === 'lead_lag') {{
      if (seriesData.length < 2) {{
        plotTraces = [];
        annotations.push({{
          xref: 'paper', yref: 'paper',
          x: 0.5, y: 0.5,
          text: CURRENT_LANG === 'zh'
            ? '请在左侧添加至少 2 条指标以启用领先-滞后分析'
            : 'Please select at least 2 series to enable lead-lag cross-correlation.',
          showarrow: false,
          font: {{ size: 13, color: '#737c8c' }}
        }});
      }} else {{
        if (SCATTER_X_IDX >= seriesData.length) SCATTER_X_IDX = 0;
        if (SCATTER_Y_IDX >= seriesData.length) SCATTER_Y_IDX = Math.min(1, seriesData.length - 1);
        if (SCATTER_X_IDX === SCATTER_Y_IDX && seriesData.length > 1) {{
          SCATTER_Y_IDX = (SCATTER_X_IDX + 1) % seriesData.length;
        }}
        const s1 = seriesData[SCATTER_X_IDX];
        const s2 = seriesData[SCATTER_Y_IDX];
        const paired = alignTwoSeries(s1.filteredObs, s2.filteredObs);
        const leadLag = computeCrossCorrelation(paired, 12);

        if (leadLag) {{
          const barColors = leadLag.lags.map(lag => {{
            if (lag === leadLag.peakLag) return '#d97706';
            const r = leadLag.corrs[lag + 12];
            return r >= 0 ? '#0d7680' : '#990f3d';
          }});

          const xLabels = leadLag.lags.map(l => l === 0 ? (CURRENT_LANG === 'zh' ? 'Lag 0 (同期)' : 'Lag 0 (Sync)') : (l < 0 ? `t${{l}} (S1 Leads)` : `t+${{l}} (S2 Leads)`));

          plotTraces.push({{
            x: xLabels,
            y: leadLag.corrs,
            yaxis: 'y',
            type: 'bar',
            marker: {{
              color: barColors,
              line: {{ width: 1, color: 'rgba(18, 21, 26, 0.15)' }}
            }},
            hovertemplate: '<b>%{{x}}</b><br>Correlation: %{{y:.3f}}<extra></extra>'
          }});

          annotations.push({{
            xref: 'paper', yref: 'paper',
            x: 0.03, y: 0.95,
            xanchor: 'left', yanchor: 'top',
            text: `<b>Lead-Lag Cross-Correlation (领先-滞后交叉相关分析)</b><br>` +
                  `Peak Lag (最佳峰值滞后): <b>${{leadLag.peakLag >= 0 ? '+' : ''}}${{leadLag.peakLag}} periods (r = ${{leadLag.peakR.toFixed(3)}})</b><br>` +
                  `Contemporaneous (同期相关 r): <b>${{leadLag.zeroLagR >= 0 ? '+' : ''}}${{leadLag.zeroLagR.toFixed(3)}}</b><br>` +
                  `Interpretation: <b>${{leadLag.peakLag < 0 ? `S1 (${{s1.country}}) leads S2 (${{s2.country}}) by ${{Math.abs(leadLag.peakLag)}} periods` : (leadLag.peakLag > 0 ? `S2 (${{s2.country}}) leads S1 (${{s1.country}}) by ${{leadLag.peakLag}} periods` : 'Contemporaneous co-movement (synchronous)')}}</b>`,
            showarrow: false,
            font: {{ family: "-apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif", size: 11, color: '#12151a' }},
            bgcolor: 'rgba(255, 255, 255, 0.92)',
            bordercolor: '#d97706',
            borderwidth: 1.2,
            borderpad: 6
          }});
        }}
        y1Title = CURRENT_LANG === 'zh' ? '交叉相关系数 (Pearson r)' : 'Cross-Correlation (Pearson r)';
        isFixedCorrelationRange = true;
      }}
    }} else {{
      // CURRENT_CANVAS_VIEW === 'timeseries'
      if (CURRENT_TRANSFORM === 'rebase') {{
        y1Title = CURRENT_LANG === 'zh' ? '归一化指数 (基期 = 100)' : 'Rebased Index (Base = 100)';
        seriesData.forEach((s, sIdx) => {{
          if (!s.filteredObs.length) return;
          const baseVal = s.filteredObs[0].value || 1.0;
          const x = s.filteredObs.map(o => o.date);
          const y = s.filteredObs.map(o => (o.value / baseVal) * 100.0);
          const lastVal = y[y.length - 1];
          const lastDate = x[x.length - 1];
          const valFormatted = lastVal.toFixed(1);

          const legendLabel = `[Y1 · ${{CURRENT_LANG === 'zh' ? '左轴' : 'Left'}}] ${{s.label}} · ${{CURRENT_LANG === 'zh' ? '最新' : 'Latest'}}: ${{valFormatted}}`;
          plotTraces.push({{
            name: legendLabel,
            x: x, y: y, yaxis: 'y',
            type: 'scatter', mode: 'lines',
            line: {{ color: s.config.color, width: 2.3 }}
          }});

          plotTraces.push({{
            name: `${{s.label}} (${{CURRENT_LANG === 'zh' ? '最新值' : 'Latest'}})`,
            x: [lastDate], y: [lastVal], yaxis: 'y',
            type: 'scatter', mode: 'markers',
            marker: {{ size: 8, color: s.config.color, line: {{ width: 2, color: '#ffffff' }} }},
            showlegend: false, hoverinfo: 'skip'
          }});

          annotations.push({{
            x: lastDate, y: lastVal, xref: 'x', yref: 'y',
            text: `<b>${{valFormatted}}</b> <span style="font-size:9.5px; opacity:0.85;">[Y1]</span>`,
            showarrow: true, arrowhead: 0, arrowcolor: s.config.color, arrowwidth: 1.2,
            ax: 34, ay: (sIdx % 2 === 0 ? -12 : 12),
            xanchor: 'left', yanchor: 'middle',
            font: {{ family: "-apple-system, BlinkMacSystemFont, 'Segoe UI', 'PingFang SC', sans-serif", size: 11, color: s.config.color }},
            bgcolor: 'rgba(255, 255, 255, 0.92)', bordercolor: s.config.color, borderwidth: 1.2, borderpad: 3
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

        if (spreadX.length < 5) {{
          const s2MonthMap = new Map();
          s2.filteredObs.forEach(o => {{
            s2MonthMap.set(o.date.slice(0, 7), o.value);
          }});
          const mSpreadX = [];
          const mSpreadY = [];
          s1.filteredObs.forEach(o => {{
            const ym = o.date.slice(0, 7);
            if (s2MonthMap.has(ym) && !mSpreadX.includes(o.date)) {{
              mSpreadX.push(o.date);
              mSpreadY.push(o.value - s2MonthMap.get(ym));
            }}
          }});
          if (mSpreadX.length > spreadX.length) {{
            spreadX.length = 0;
            spreadY.length = 0;
            mSpreadX.forEach((x, i) => {{
              spreadX.push(x);
              spreadY.push(mSpreadY[i]);
            }});
          }}
        }}

        if (spreadX.length > 0) {{
          const lastSpreadVal = spreadY[spreadY.length - 1];
          const lastSpreadDate = spreadX[spreadX.length - 1];
          const spreadSign = lastSpreadVal > 0 ? '+' : '';
          const spreadFormatted = `${{spreadSign}}${{lastSpreadVal.toFixed(2)}}${{s1.unit ? ' ' + s1.unit : ''}}`;

          plotTraces.push({{
            name: `[Y1 · ${{CURRENT_LANG === 'zh' ? '左轴' : 'Left'}}] Spread (${{s1.config.country}} − ${{s2.config.country}}) · ${{CURRENT_LANG === 'zh' ? '最新' : 'Latest'}}: ${{spreadFormatted}}`,
            x: spreadX, y: spreadY, yaxis: 'y',
            type: 'scatter', mode: 'lines',
            fill: 'tozeroy', fillcolor: 'rgba(153, 15, 61, 0.08)',
            line: {{ color: '#990f3d', width: 2.4 }}
          }});

          plotTraces.push({{
            name: 'Spread Latest',
            x: [lastSpreadDate], y: [lastSpreadVal], yaxis: 'y',
            type: 'scatter', mode: 'markers',
            marker: {{ size: 8, color: '#990f3d', line: {{ width: 2, color: '#ffffff' }} }},
            showlegend: false, hoverinfo: 'skip'
          }});

          annotations.push({{
            x: lastSpreadDate, y: lastSpreadVal, xref: 'x', yref: 'y',
            text: `<b>${{spreadFormatted}}</b> <span style="font-size:9.5px; opacity:0.85;">[Spread]</span>`,
            showarrow: true, arrowhead: 0, arrowcolor: '#990f3d', arrowwidth: 1.2,
            ax: 34, ay: -12, xanchor: 'left', yanchor: 'middle',
            font: {{ family: "-apple-system, BlinkMacSystemFont, 'Segoe UI', 'PingFang SC', sans-serif", size: 11, color: '#990f3d' }},
            bgcolor: 'rgba(255, 255, 255, 0.92)', bordercolor: '#990f3d', borderwidth: 1.2, borderpad: 3
          }});
        }}
        plotTraces.push({{
          name: `[Y1] ${{s1.label}}`,
          x: s1.filteredObs.map(o => o.date), y: s1.filteredObs.map(o => o.value), yaxis: 'y',
          type: 'scatter', mode: 'lines',
          line: {{ color: '#0d7680', width: 1.5, dash: 'dot' }}
        }});
        plotTraces.push({{
          name: `[Y1] ${{s2.label}}`,
          x: s2.filteredObs.map(o => o.date), y: s2.filteredObs.map(o => o.value), yaxis: 'y',
          type: 'scatter', mode: 'lines',
          line: {{ color: '#737c8c', width: 1.5, dash: 'dot' }}
        }});
      }} else if (CURRENT_TRANSFORM === 'zscore') {{
        y1Title = CURRENT_LANG === 'zh' ? 'Z-Score 标准化得分 (均值=0, 标准差=1)' : 'Standardized Z-Score (Mean = 0, Std = 1)';
        seriesData.forEach((s, sIdx) => {{
          if (!s.filteredObs.length) return;
          const vals = s.filteredObs.map(o => o.value);
          const mean = vals.reduce((a, b) => a + b, 0) / vals.length;
          const variance = vals.reduce((a, b) => a + (b - mean) ** 2, 0) / (vals.length - 1 || 1);
          const std = Math.sqrt(variance);
          const x = s.filteredObs.map(o => o.date);
          const y = std > 0 ? vals.map(v => (v - mean) / std) : vals.map(() => 0);
          const lastVal = y[y.length - 1];
          const lastDate = x[x.length - 1];
          const valFormatted = `${{lastVal >= 0 ? '+' : ''}}${{lastVal.toFixed(2)}}σ`;

          const legendLabel = `[Z-Score] ${{s.label}} · ${{CURRENT_LANG === 'zh' ? '最新' : 'Latest'}}: ${{valFormatted}}`;
          plotTraces.push({{
            name: legendLabel,
            x: x, y: y, yaxis: 'y',
            type: 'scatter', mode: 'lines',
            line: {{ color: s.config.color, width: 2.3 }}
          }});

          plotTraces.push({{
            name: `${{s.label}} (${{CURRENT_LANG === 'zh' ? '最新值' : 'Latest'}})`,
            x: [lastDate], y: [lastVal], yaxis: 'y',
            type: 'scatter', mode: 'markers',
            marker: {{ size: 8, color: s.config.color, line: {{ width: 2, color: '#ffffff' }} }},
            showlegend: false, hoverinfo: 'skip'
          }});

          annotations.push({{
            x: lastDate, y: lastVal, xref: 'x', yref: 'y',
            text: `<b>${{valFormatted}}</b> <span style="font-size:9.5px; opacity:0.85;">[Z]</span>`,
            showarrow: true, arrowhead: 0, arrowcolor: s.config.color, arrowwidth: 1.2,
            ax: 34, ay: (sIdx % 2 === 0 ? -12 : 12),
            xanchor: 'left', yanchor: 'middle',
            font: {{ family: "-apple-system, sans-serif", size: 11, color: s.config.color }},
            bgcolor: 'rgba(255, 255, 255, 0.92)', bordercolor: s.config.color, borderwidth: 1.2, borderpad: 3
          }});
        }});

        shapes.push(
          {{ type: 'line', xref: 'paper', x0: 0, x1: 1, yref: 'y', y0: 2, y1: 2, line: {{ color: 'rgba(153, 15, 61, 0.4)', width: 1, dash: 'dot' }} }},
          {{ type: 'line', xref: 'paper', x0: 0, x1: 1, yref: 'y', y0: -2, y1: -2, line: {{ color: 'rgba(13, 118, 128, 0.4)', width: 1, dash: 'dot' }} }}
        );
        annotations.push(
          {{ xref: 'paper', yref: 'y', x: 0.02, y: 2, text: '+2σ (High / 过热高位)', showarrow: false, font: {{ size: 9.5, color: '#990f3d' }} }},
          {{ xref: 'paper', yref: 'y', x: 0.02, y: -2, text: '-2σ (Low / 周期低位)', showarrow: false, font: {{ size: 9.5, color: '#0d7680' }} }}
        );
      }} else if (CURRENT_TRANSFORM === 'yoy') {{
        y1Title = CURRENT_LANG === 'zh' ? '同比变动 (YoY % / 差值)' : 'YoY Change (% / Points)';
        seriesData.forEach((s, sIdx) => {{
          if (!s.filteredObs.length) return;
          const dateMap = new Map(s.observations.map(o => [o.date, o.value]));
          const isRate = s.unit.includes('%') || s.unit.includes('bps') || s.unit.includes('pts');
          const x = [];
          const y = [];
          s.filteredObs.forEach(o => {{
            const parts = o.date.split('-');
            const prevYear = parseInt(parts[0], 10) - 1;
            const targetExact = `${{prevYear}}-${{parts[1]}}-${{parts[2]}}`;
            let prevVal = dateMap.get(targetExact);
            if (prevVal === undefined) {{
              const targetMonth = `${{prevYear}}-${{parts[1]}}`;
              for (const [d, v] of dateMap.entries()) {{
                if (d.startsWith(targetMonth)) {{
                  prevVal = v;
                  break;
                }}
              }}
            }}
            if (prevVal !== undefined && !isNaN(prevVal)) {{
              x.push(o.date);
              if (isRate) {{
                y.push(o.value - prevVal);
              }} else {{
                y.push(prevVal !== 0 ? ((o.value - prevVal) / Math.abs(prevVal)) * 100 : 0);
              }}
            }}
          }});

          if (x.length > 0) {{
            const lastVal = y[y.length - 1];
            const lastDate = x[x.length - 1];
            const sign = lastVal >= 0 ? '+' : '';
            const unitSuffix = isRate ? (s.unit || '% pts') : '%';
            const valFormatted = `${{sign}}${{lastVal.toFixed(2)}} ${{unitSuffix}}`;

            const legendLabel = `[YoY] ${{s.label}} · ${{CURRENT_LANG === 'zh' ? '最新' : 'Latest'}}: ${{valFormatted}}`;
            plotTraces.push({{
              name: legendLabel,
              x: x, y: y, yaxis: 'y',
              type: 'scatter', mode: 'lines',
              line: {{ color: s.config.color, width: 2.3 }}
            }});

            plotTraces.push({{
              name: `${{s.label}} (${{CURRENT_LANG === 'zh' ? '最新值' : 'Latest'}})`,
              x: [lastDate], y: [lastVal], yaxis: 'y',
              type: 'scatter', mode: 'markers',
              marker: {{ size: 8, color: s.config.color, line: {{ width: 2, color: '#ffffff' }} }},
              showlegend: false, hoverinfo: 'skip'
            }});

            annotations.push({{
              x: lastDate, y: lastVal, xref: 'x', yref: 'y',
              text: `<b>${{valFormatted}}</b> <span style="font-size:9.5px; opacity:0.85;">[YoY]</span>`,
              showarrow: true, arrowhead: 0, arrowcolor: s.config.color, arrowwidth: 1.2,
              ax: 34, ay: (sIdx % 2 === 0 ? -12 : 12),
              xanchor: 'left', yanchor: 'middle',
              font: {{ family: "-apple-system, sans-serif", size: 11, color: s.config.color }},
              bgcolor: 'rgba(255, 255, 255, 0.92)', bordercolor: s.config.color, borderwidth: 1.2, borderpad: 3
            }});
          }}
        }});
      }} else if (CURRENT_TRANSFORM === 'pct_change') {{
        y1Title = CURRENT_LANG === 'zh' ? '区间累计涨跌幅 (%)' : 'Cumulative Change (%)';
        seriesData.forEach((s, sIdx) => {{
          if (!s.filteredObs.length) return;
          const baseVal = s.filteredObs[0].value;
          if (baseVal === 0) return;
          const x = s.filteredObs.map(o => o.date);
          const y = s.filteredObs.map(o => ((o.value - baseVal) / Math.abs(baseVal)) * 100);
          const lastVal = y[y.length - 1];
          const lastDate = x[x.length - 1];
          const sign = lastVal >= 0 ? '+' : '';
          const valFormatted = `${{sign}}${{lastVal.toFixed(1)}}%`;

          const legendLabel = `[% Δ] ${{s.label}} · ${{CURRENT_LANG === 'zh' ? '最新' : 'Latest'}}: ${{valFormatted}}`;
          plotTraces.push({{
            name: legendLabel,
            x: x, y: y, yaxis: 'y',
            type: 'scatter', mode: 'lines',
            line: {{ color: s.config.color, width: 2.3 }}
          }});

          plotTraces.push({{
            name: `${{s.label}} (${{CURRENT_LANG === 'zh' ? '最新值' : 'Latest'}})`,
            x: [lastDate], y: [lastVal], yaxis: 'y',
            type: 'scatter', mode: 'markers',
            marker: {{ size: 8, color: s.config.color, line: {{ width: 2, color: '#ffffff' }} }},
            showlegend: false, hoverinfo: 'skip'
          }});

          annotations.push({{
            x: lastDate, y: lastVal, xref: 'x', yref: 'y',
            text: `<b>${{valFormatted}}</b> <span style="font-size:9.5px; opacity:0.85;">[%]</span>`,
            showarrow: true, arrowhead: 0, arrowcolor: s.config.color, arrowwidth: 1.2,
            ax: 34, ay: (sIdx % 2 === 0 ? -12 : 12),
            xanchor: 'left', yanchor: 'middle',
            font: {{ family: "-apple-system, sans-serif", size: 11, color: s.config.color }},
            bgcolor: 'rgba(255, 255, 255, 0.92)', bordercolor: s.config.color, borderwidth: 1.2, borderpad: 3
          }});
        }});
      }} else {{
        // Raw Levels
        seriesData.forEach((s, sIdx) => {{
          if (!s.filteredObs.length) return;
          const isRight = (s.config.axis === 'right');
          if (isRight) {{
            hasY2 = true;
            if (!y2Title) y2Title = s.unit;
          }} else {{
            if (!y1Title) y1Title = s.unit;
          }}

          const latestObs = s.filteredObs[s.filteredObs.length - 1];
          const latestVal = typeof latestObs.value === 'number' ? latestObs.value.toFixed(2) : '';
          const axisTag = isRight ? (CURRENT_LANG === 'zh' ? '右轴 · Y2' : 'Right · Y2') : (CURRENT_LANG === 'zh' ? '左轴 · Y1' : 'Left · Y1');
          const axisTagShort = isRight ? (CURRENT_LANG === 'zh' ? '右轴' : 'Right') : (CURRENT_LANG === 'zh' ? '左轴' : 'Left');
          const unitSuffix = s.unit ? ` ${{s.unit}}` : '';
          const legendLabel = `[${{axisTag}}] ${{s.label}} · ${{CURRENT_LANG === 'zh' ? '最新' : 'Latest'}}: ${{latestVal}}${{unitSuffix}}`;

          plotTraces.push({{
            name: legendLabel,
            x: s.filteredObs.map(o => o.date),
            y: s.filteredObs.map(o => o.value),
            yaxis: isRight ? 'y2' : 'y',
            type: 'scatter',
            mode: 'lines',
            line: {{ color: s.config.color, width: 2.3 }}
          }});

          plotTraces.push({{
            name: `${{s.label}} (${{CURRENT_LANG === 'zh' ? '最新值' : 'Latest'}})`,
            x: [latestObs.date],
            y: [latestObs.value],
            yaxis: isRight ? 'y2' : 'y',
            type: 'scatter',
            mode: 'markers',
            marker: {{
              size: 8,
              color: s.config.color,
              line: {{ width: 2, color: '#ffffff' }}
            }},
            showlegend: false,
            hoverinfo: 'skip'
          }});

          annotations.push({{
            x: latestObs.date,
            y: latestObs.value,
            xref: 'x',
            yref: isRight ? 'y2' : 'y',
            text: `<b>${{latestVal}}${{unitSuffix}}</b> <span style="font-size:9.5px; opacity:0.85;">[${{axisTagShort}}]</span>`,
            showarrow: true,
            arrowhead: 0,
            arrowcolor: s.config.color,
            arrowwidth: 1.2,
            ax: 34,
            ay: (sIdx % 2 === 0 ? -12 : 12),
            xanchor: 'left',
            yanchor: 'middle',
            font: {{
              family: "-apple-system, BlinkMacSystemFont, 'Segoe UI', 'PingFang SC', sans-serif",
              size: 11,
              color: s.config.color
            }},
            bgcolor: 'rgba(255, 255, 255, 0.92)',
            bordercolor: s.config.color,
            borderwidth: 1.2,
            borderpad: 3
          }});
        }});
        if (!y1Title && y2Title) y1Title = y2Title;
      }}
    }}

    // 6. Layout Configuration in FT/Claude Style
    const effectiveTitle = getEffectiveTitle();
    const titleInput = document.getElementById('chart-title-input');
    if (titleInput && !titleInput.value && !CHART_CUSTOM_TITLE) {{
      titleInput.placeholder = effectiveTitle;
    }}

    const y1Label = CURRENT_LANG === 'zh' ? `← Y1 (左轴)${{y1Title ? ' · ' + y1Title : ''}}` : `← Y1 (Left)${{y1Title ? ' · ' + y1Title : ''}}`;
    const y2Label = CURRENT_LANG === 'zh' ? `Y2 (右轴) →${{y2Title ? ' · ' + y2Title : ''}}` : `Y2 (Right) →${{y2Title ? ' · ' + y2Title : ''}}`;

    annotations.push({{
      xref: 'paper',
      yref: 'paper',
      x: 1.0,
      y: -0.21,
      xanchor: 'right',
      yanchor: 'top',
      text: '<i>Source: East Meridian Macro Dashboard · Official Macro Pipeline</i>',
      showarrow: false,
      font: {{
        family: "-apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
        size: 9.5,
        color: '#737c8c'
      }}
    }});

    const layout = {{
      height: 560,
      margin: {{ l: 64, r: hasY2 ? 84 : 96, t: 56, b: 64 }},
      paper_bgcolor: '#ffffff',
      plot_bgcolor: '#ffffff',
      shapes: shapes,
      title: {{
        text: `<b>${{effectiveTitle}}</b>`,
        font: {{
          family: '"Newsreader", "Iowan Old Style", "Songti SC", Georgia, serif',
          size: 16,
          color: '#12151a'
        }},
        x: 0.02,
        y: 0.98,
        xanchor: 'left',
        yanchor: 'top'
      }},
      font: {{
        family: "-apple-system, BlinkMacSystemFont, 'Segoe UI', 'PingFang SC', 'Hiragino Sans GB', 'Noto Sans SC', sans-serif",
        size: 11,
        color: '#12151a'
      }},
      xaxis: {{
        title: layoutXTitle ? {{ text: layoutXTitle, font: {{ size: 11, color: '#4b525f' }} }} : undefined,
        gridcolor: 'rgba(18, 21, 26, 0.06)',
        showgrid: false,
        zeroline: false,
        autorange: true,
        automargin: true,
        tickfont: {{ size: 10, color: '#4b525f' }},
      }},
      yaxis: {{
        title: {{ text: y1Label, font: {{ size: 11, color: '#4b525f' }} }},
        range: isFixedCorrelationRange ? [-1.08, 1.08] : undefined,
        gridcolor: 'rgba(18, 21, 26, 0.06)',
        zeroline: true,
        zerolinewidth: 1.4,
        zerolinecolor: 'rgba(18, 21, 26, 0.40)',
        autorange: !isFixedCorrelationRange,
        automargin: true,
        tickfont: {{ size: 10, color: '#4b525f' }},
      }},
      legend: {{
        orientation: 'h',
        y: -0.22,
        x: 0,
        font: {{ size: 11, color: '#12151a' }},
        bgcolor: 'rgba(255, 255, 255, 0.85)',
      }},
      hovermode: CURRENT_CANVAS_VIEW === 'scatter_ols' ? 'closest' : 'x unified',
      hoverlabel: {{
        bgcolor: '#ffffff',
        bordercolor: 'rgba(18, 21, 26, 0.20)',
        font: {{ family: '-apple-system, sans-serif', size: 11, color: '#12151a' }},
      }},
      autosize: true,
      annotations: annotations
    }};

    if (hasY2) {{
      layout.yaxis2 = {{
        title: {{ text: y2Label, font: {{ size: 11, color: '#4b525f' }} }},
        overlaying: 'y',
        side: 'right',
        showgrid: false,
        zeroline: false,
        autorange: true,
        automargin: true,
        tickfont: {{ size: 10, color: '#4b525f' }},
      }};
    }}

    if (plotTraces.length === 0) {{
      layout.annotations = [{{
        xref: 'paper', yref: 'paper',
        x: 0.5, y: 0.5,
        text: CURRENT_LANG === 'zh' ? '暂无数据或选定序列在所选区间内无有效观测值，请尝试更换时间窗口或指标' : 'No observations found for the selected series within this range.',
        showarrow: false,
        font: {{ size: 13, color: '#737c8c' }}
      }}];
    }}

    // Use Plotly.newPlot for robust canvas rendering
    Plotly.newPlot('chart-canvas', plotTraces, layout, {{
      displayModeBar: "hover",
      displaylogo: false,
      responsive: true
    }});

    // 7. Update Summary Table
    renderSummaryTable(seriesData);

    // 8. Update URL Hash
    syncHash();

  }} catch (err) {{
    console.error("Chart refresh error:", err);
  }} finally {{
    if (loadingEl) loadingEl.style.display = 'none';
  }}
}}

function renderSummaryTable(seriesData) {{
  const tbody = document.getElementById('summary-table-body');
  if (!tbody) return;
  tbody.innerHTML = '';

  seriesData.forEach(s => {{
    const stats = computeStats(s.filteredObs);
    if (!stats) return;

    const latestFormatted = typeof stats.latest === 'number' ? `${{stats.latest.toFixed(2)}} ${{s.unit}}` : 'n/a';
    const zColor = stats.zScore > 1.5 ? '#990f3d' : (stats.zScore < -1.5 ? '#0d7680' : '#4b525f');
    const zSign = stats.zScore > 0 ? '+' : '';
    const dSign = stats.periodDelta > 0 ? '+' : '';
    const pSign = stats.periodPct > 0 ? '+' : '';

    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td>
        <span class="table-bullet" style="background: ${{s.config.color}};"></span>
        <strong>${{s.label}}</strong>
      </td>
      <td><strong>${{s.country}}</strong></td>
      <td><strong>${{latestFormatted}}</strong></td>
      <td style="color: var(--muted);">${{stats.latestDate}}</td>
      <td>
        <div class="percentile-cell" title="Percentile rank: ${{stats.percentile.toFixed(1)}}% of historical values in this window are <= latest">
          <div class="pct-track">
            <div class="pct-fill" style="width: ${{stats.percentile.toFixed(1)}}%; background: ${{s.config.color}};"></div>
          </div>
          <strong style="font-size:11px;">${{stats.percentile.toFixed(1)}}%</strong>
        </div>
      </td>
      <td>
        <span class="zscore-tag" style="color: ${{zColor}}; background: ${{zColor}}14;">
          ${{zSign}}${{stats.zScore.toFixed(2)}}σ
        </span>
      </td>
      <td>${{stats.mean.toFixed(2)}} ± ${{stats.std.toFixed(2)}}</td>
      <td>${{stats.min.toFixed(2)}} ~ ${{stats.max.toFixed(2)}}</td>
      <td>
        <span style="color: ${{stats.periodDelta >= 0 ? '#16a34a' : '#dc2626'}}; font-weight:600;">
          ${{dSign}}${{stats.periodDelta.toFixed(2)}}
        </span>
        <span style="color: var(--muted); font-size:10.5px;">(${{pSign}}${{stats.periodPct.toFixed(1)}}%)</span>
      </td>
      <td style="color: var(--text-secondary);">${{stats.skewness >= 0 ? '+' : ''}}${{stats.skewness.toFixed(2)}}</td>
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
    v: CURRENT_CANVAS_VIEW,
    title: CHART_CUSTOM_TITLE || undefined,
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
    if (payload.v) CURRENT_CANVAS_VIEW = payload.v;
    if (payload.title) {{
      CHART_CUSTOM_TITLE = payload.title;
      const titleInput = document.getElementById('chart-title-input');
      if (titleInput) titleInput.value = payload.title;
    }}
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
    showToast(CURRENT_LANG === 'zh' ? '已根据分享链接还原图表视图' : 'Chart view restored from share link', '🔗');
  }} catch (e) {{
    console.error("Failed to parse URL hash:", e);
  }}
}}

// Action Buttons
function exportPNG() {{
  const effectiveTitle = getEffectiveTitle();
  const safeFilename = effectiveTitle.toLowerCase().replace(/[^a-z0-9\u4e00-\u9fa5]+/gi, '_') + '_' + new Date().toISOString().slice(0, 10);
  Plotly.downloadImage('chart-canvas', {{
    format: 'png',
    width: 1400,
    height: 750,
    filename: safeFilename
  }}).then(() => {{
    showToast(CURRENT_LANG === 'zh' ? '高清 PNG 图表下载已启动！' : 'High-resolution PNG download started!', '📷');
  }}).catch(err => {{
    console.error("PNG export error:", err);
  }});
}}

function exportSVG() {{
  const effectiveTitle = getEffectiveTitle();
  const safeFilename = effectiveTitle.toLowerCase().replace(/[^a-z0-9\u4e00-\u9fa5]+/gi, '_') + '_' + new Date().toISOString().slice(0, 10);
  Plotly.downloadImage('chart-canvas', {{
    format: 'svg',
    width: 1400,
    height: 750,
    filename: safeFilename
  }}).then(() => {{
    showToast(CURRENT_LANG === 'zh' ? '矢量 SVG 图表下载已启动！' : 'Vector SVG download started!', '📐');
  }}).catch(err => {{
    console.error("SVG export error:", err);
  }});
}}

function exportJSON() {{
  const effectiveTitle = getEffectiveTitle();
  const payload = {{
    exported_at: new Date().toISOString(),
    chart_title: effectiveTitle,
    transform: CURRENT_TRANSFORM,
    date_range: CURRENT_RANGE,
    series: []
  }};

  ACTIVE_SERIES.forEach((item, idx) => {{
    const frame = FRAME_CACHE[item.country] || {{}};
    const rawSeries = frame[item.indicatorId];
    if (!rawSeries) return;
    const meta = rawSeries.metadata || rawSeries;
    payload.series.push({{
      country: item.country,
      indicator_id: item.indicatorId,
      label_en: meta.label_en || item.indicatorId,
      label_zh: meta.label_zh || item.indicatorId,
      unit: meta.unit || '',
      frequency: meta.frequency || '',
      axis: item.axis,
      source: meta.source || {{}},
      quality: meta.quality || {{}},
      observations: rawSeries.observations || []
    }});
  }});

  const blob = new Blob([JSON.stringify(payload, null, 2)], {{ type: 'application/json;charset=utf-8;' }});
  const link = document.createElement('a');
  link.href = URL.createObjectURL(blob);
  const safeFilename = effectiveTitle.toLowerCase().replace(/[^a-z0-9\u4e00-\u9fa5]+/gi, '_') + '_' + new Date().toISOString().slice(0, 10) + '.json';
  link.setAttribute('download', safeFilename);
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  showToast(CURRENT_LANG === 'zh' ? 'JSON 数据集下载已启动！' : 'JSON dataset downloaded!', '💾');
}}

function exportCSV() {{
  const neededCountries = [...new Set(ACTIVE_SERIES.map(s => s.country))];
  const allDates = new Set();
  const seriesCols = [];

  ACTIVE_SERIES.forEach((item, idx) => {{
    const frame = FRAME_CACHE[item.country] || {{}};
    const rawSeries = frame[item.indicatorId];
    if (!rawSeries) return;
    const meta = rawSeries.metadata || rawSeries;
    const label = (CURRENT_LANG === 'zh' ? meta.label_zh : meta.label_en) || item.indicatorId;
    const colName = `${{item.country}}_${{item.indicatorId}}`;
    const headerTitle = `${{item.country}} - ${{label}} (${{meta.unit || ''}})`;
    const dateMap = new Map((rawSeries.observations || []).map(r => [String(r[0]), Number(r[1])]));
    dateMap.forEach((_, d) => allDates.add(d));
    seriesCols.push({{
      key: colName,
      title: headerTitle,
      unit: meta.unit || '',
      source: (meta.source && meta.source.name) ? meta.source.name : '',
      axis: item.axis,
      map: dateMap
    }});
  }});

  const sortedDates = [...allDates].sort();
  const effectiveTitle = getEffectiveTitle();
  const nowStr = new Date().toISOString();

  let csv = `# East Meridian Macro Chart Studio Export\\n`;
  csv += `# Title: ${{effectiveTitle.replace(/[\\r\\n]/g, ' ')}}\\n`;
  csv += `# Exported: ${{nowStr}}\\n`;
  csv += `# View: ${{CURRENT_CANVAS_VIEW}} | Transform: ${{CURRENT_TRANSFORM}} | Range: ${{CURRENT_RANGE}}\\n`;
  seriesCols.forEach(col => {{
    csv += `# Series: ${{col.title}} | Source: ${{col.source}} | Axis: ${{col.axis.toUpperCase()}}\\n`;
  }});
  csv += 'date,' + seriesCols.map(s => `"${{s.title.replace(/"/g, '""')}}"`).join(',') + '\\n';

  sortedDates.forEach(date => {{
    const row = [date];
    seriesCols.forEach(s => {{
      const val = s.map.get(date);
      row.push(val !== undefined && !isNaN(val) ? val : '');
    }});
    csv += row.join(',') + '\\n';
  }});

  const blob = new Blob([csv], {{ type: 'text/csv;charset=utf-8;' }});
  const link = document.createElement('a');
  link.href = URL.createObjectURL(blob);
  const safeFilename = effectiveTitle.toLowerCase().replace(/[^a-z0-9\u4e00-\u9fa5]+/gi, '_') + '_' + new Date().toISOString().slice(0, 10) + '.csv';
  link.setAttribute('download', safeFilename);
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  showToast(CURRENT_LANG === 'zh' ? '包含完整元数据的 CSV 数据集已下载！' : 'CSV dataset with metadata downloaded!', '📥');
}}

function copyShareURL() {{
  syncHash();
  const url = window.location.href;
  navigator.clipboard.writeText(url).then(() => {{
    showToast(CURRENT_LANG === 'zh' ? '分享链接已复制！包含当前的图表配置与标题。' : 'Share link copied! Includes configuration and layout.', '🔗');
  }}).catch(() => {{
    prompt(CURRENT_LANG === 'zh' ? '复制此链接分享当前图表：' : 'Copy link to share chart:', url);
  }});
}}

function toggleLang() {{
  CURRENT_LANG = CURRENT_LANG === 'en' ? 'zh' : 'en';
  document.documentElement.lang = CURRENT_LANG;
  const langBtn = document.getElementById('lang-btn');
  if (langBtn) langBtn.textContent = CURRENT_LANG === 'en' ? '中文' : 'English';
  renderPresets();
  renderSeriesControls();
  refreshChart();
  showToast(CURRENT_LANG === 'zh' ? '已切换至中文界面' : 'Switched to English interface', '🌐');
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

    html_content = render_html(catalog)
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
