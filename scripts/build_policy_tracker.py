#!/usr/bin/env python3
"""Build script for the Central Bank Policy & Monetary Cycle Tracker.

Generates output/policy_tracker.html and policy_tracker.html in the root.
Covers ALL 18 economies across:
  1. Global Policy Stance Matrix & Cycle Radar (18-economy master table with sorting and regional filtering)
  2. Real Policy Rate & Carry/Neutrality Studio (Plotly horizontal real rate ranking & Taylor stance scatter)
  3. 2026/2027 Global Central Bank Decision Calendar (60+ meetings across 18 central banks with days-to-meeting)
  4. Core Operational Corridors & Institutional Stance Cards (G4 + high-beta EMs: Fed, ECB, BoE, BoJ, PBOC, TCMB, MNB, SARB, BOK)
  5. Forward Guidance & Statement Diff Studio (FOMC Dot Plot vs SOFR curve, Word-level statement diff with sentiment scores)
  6. FT & Claude UI design system tokens, responsive layout, and complete bilingual support (EN/ZH).
"""
from __future__ import annotations

import json
from datetime import datetime, date
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

# Static metadata for all 18 economies
ECONOMY_METADATA = {
    "US": {
        "flag": "🇺🇸",
        "name_en": "United States",
        "name_zh": "美国",
        "region": "dm",
        "region_en": "Developed Markets (G4)",
        "region_zh": "发达成体系 (G4)",
        "cb_name_en": "Federal Reserve (Fed)",
        "cb_name_zh": "美联储 (Federal Reserve)",
        "cb_short": "FED",
        "policy_tool_en": "Fed Funds Target Upper",
        "policy_tool_zh": "联邦基金利率目标上限",
        "corridor_ceiling_name": "Discount Window Primary Credit",
        "corridor_ceiling_rate": 4.00,
        "corridor_floor_name": "Overnight Reverse Repo (ON RRP)",
        "corridor_floor_rate": 3.80,
        "secondary_tool_en": "IORB 3.90% · QT $60B/mo Runoff Cap",
        "secondary_tool_zh": "准备金利率 3.90% · 每月缩表上限 600 亿美元",
        "balance_sheet_display_en": "$6,745.6B (23.4% of GDP)",
        "balance_sheet_display_zh": "67,456 亿美元 (占GDP 23.4%)",
        "operational_signal_en": "Quantitative Tightening continues; ample reserves buffer with ON RRP near exhaustion ($4.4B).",
        "operational_signal_zh": "缩表持续进行；准备金充裕缓冲，隔夜逆回购基本见底（44 亿美元）。",
        "rate_change_12m": -150,
        "cycle_phase_en": "Easing / Plateau Hold",
        "cycle_phase_zh": "降息观望 / 高位平稳",
        "cycle_badge": "plateau",
        "next_meeting_date": "2026-12-18",
        "next_meeting_name_en": "FOMC Statement, Press Conf & SEP",
        "next_meeting_name_zh": "FOMC 利率决议、新闻发布会与季度经济预测(点阵图)",
        "consensus_action_en": "Hold at 3.88% (85% prob)",
        "consensus_action_zh": "维持 3.88% 按兵不动 (85% 概率)",
        "has_corridor_card": True,
    },
    "EA": {
        "flag": "🇪🇺",
        "name_en": "Euro Area",
        "name_zh": "欧元区",
        "region": "dm",
        "region_en": "Developed Markets (G4)",
        "region_zh": "发达成体系 (G4)",
        "cb_name_en": "European Central Bank (ECB)",
        "cb_name_zh": "欧洲中央银行 (ECB)",
        "cb_short": "ECB",
        "policy_tool_en": "Deposit Facility Rate (DFR)",
        "policy_tool_zh": "存款便利利率 (DFR)",
        "corridor_ceiling_name": "Marginal Lending Facility (MLF)",
        "corridor_ceiling_rate": 2.75,
        "corridor_floor_name": "Deposit Facility Rate (DFR)",
        "corridor_floor_rate": 2.50,
        "secondary_tool_en": "Main Refinancing Operations (MRO) 2.65%",
        "secondary_tool_zh": "主要再融资利率 (MRO) 2.65%",
        "balance_sheet_display_en": "€5,935.0B (38.8% of GDP)",
        "balance_sheet_display_zh": "59,350 亿欧元 (占GDP 38.8%)",
        "operational_signal_en": "APP passive runoff underway; PEPP reinvestments tapering by €7.5B/month towards year-end phaseout.",
        "operational_signal_zh": "APP 完全停止再投资；PEPP 每月缩减 75 亿欧元再投资，年底前平稳结束。",
        "rate_change_12m": -150,
        "cycle_phase_en": "Calibrated Easing",
        "cycle_phase_zh": "中性校准 / 渐进宽松",
        "cycle_badge": "easing",
        "next_meeting_date": "2026-12-11",
        "next_meeting_name_en": "Governing Council & Staff Projections",
        "next_meeting_name_zh": "管理委员会利率决议与宏观经济预测",
        "consensus_action_en": "Cut 25 bps to 2.25%",
        "consensus_action_zh": "降息 25 个基点至 2.25%",
        "has_corridor_card": True,
    },
    "UK": {
        "flag": "🇬🇧",
        "name_en": "United Kingdom",
        "name_zh": "英国",
        "region": "dm",
        "region_en": "Developed Markets (G4)",
        "region_zh": "发达成体系 (G4)",
        "cb_name_en": "Bank of England (BoE)",
        "cb_name_zh": "英格兰银行 (BoE)",
        "cb_short": "BOE",
        "policy_tool_en": "Official Bank Rate",
        "policy_tool_zh": "官方银行基准利率",
        "corridor_ceiling_name": "Short-Term Repo / Operational Standing",
        "corridor_ceiling_rate": 3.75,
        "corridor_floor_name": "Operational Standing Deposit",
        "corridor_floor_rate": 3.50,
        "secondary_tool_en": "Active Gilt Runoff £100B/year Target",
        "secondary_tool_zh": "主动减持国债目标 1,000 亿英镑/年",
        "balance_sheet_display_en": "£820.5B (29.2% of GDP)",
        "balance_sheet_display_zh": "8,205 亿英镑 (占GDP 29.2%)",
        "operational_signal_en": "Gradual loosening stance balanced against persistent services inflation and wage inertia.",
        "operational_signal_zh": "渐进降息姿态，在服务业通胀粘性与工资增速之间寻求平衡。",
        "rate_change_12m": -125,
        "cycle_phase_en": "Gradual Easing",
        "cycle_phase_zh": "渐进降息 / 谨慎观察",
        "cycle_badge": "easing",
        "next_meeting_date": "2026-12-18",
        "next_meeting_name_en": "MPC Bank Rate Decision & Minutes",
        "next_meeting_name_zh": "MPC 利率决议与会议纪要",
        "consensus_action_en": "Hold at 3.75% (80% prob)",
        "consensus_action_zh": "维持 3.75% 按兵不动 (80% 概率)",
        "has_corridor_card": True,
    },
    "JP": {
        "flag": "🇯🇵",
        "name_en": "Japan",
        "name_zh": "日本",
        "region": "dm",
        "region_en": "Developed Markets (G4)",
        "region_zh": "发达成体系 (G4)",
        "cb_name_en": "Bank of Japan (BoJ)",
        "cb_name_zh": "日本银行 (BoJ)",
        "cb_short": "BOJ",
        "policy_tool_en": "Uncollateralized O/N Call Rate Target",
        "policy_tool_zh": "无担保隔夜拆借利率目标",
        "corridor_ceiling_name": "Complementary Lending Facility",
        "corridor_ceiling_rate": 1.25,
        "corridor_floor_name": "Complementary Deposit Facility",
        "corridor_floor_rate": 0.90,
        "secondary_tool_en": "Planned JGB Purchases ~¥3T/month",
        "secondary_tool_zh": "缩减国债月度购买规模至约 3 万亿日元",
        "balance_sheet_display_en": "¥625.0T (103.5% of GDP)",
        "balance_sheet_display_zh": "625.0 万亿日元 (占GDP 103.5%)",
        "operational_signal_en": "Normalization cycle in progress; positive wage-price spiral anchoring rate hiking pathway.",
        "operational_signal_zh": "货币政策正常化稳步推进；春斗薪资与物价良性循环支撑加息路径。",
        "rate_change_12m": 75,
        "cycle_phase_en": "Tightening / Normalizing",
        "cycle_phase_zh": "紧缩加息 / 政策正常化",
        "cycle_badge": "hiking",
        "next_meeting_date": "2026-12-19",
        "next_meeting_name_en": "Monetary Policy Meeting (MPM) Decision",
        "next_meeting_name_zh": "货币政策会议 (MPM) 利率决议",
        "consensus_action_en": "Hike 25 bps to 1.25%",
        "consensus_action_zh": "加息 25 个基点至 1.25%",
        "has_corridor_card": True,
    },
    "CN": {
        "flag": "🇨🇳",
        "name_en": "China",
        "name_zh": "中国",
        "region": "em",
        "region_en": "Major Emerging Markets",
        "region_zh": "重要新兴市场",
        "cb_name_en": "People's Bank of China (PBC)",
        "cb_name_zh": "中国人民银行 (PBC)",
        "cb_short": "PBC",
        "policy_tool_en": "1Y Loan Prime Rate (LPR)",
        "policy_tool_zh": "一年期贷款市场报价利率 (1Y LPR)",
        "corridor_ceiling_name": "Standing Lending Facility (SLF 7D)",
        "corridor_ceiling_rate": 2.30,
        "corridor_floor_name": "7D Reverse Repo Policy Rate",
        "corridor_floor_rate": 1.50,
        "secondary_tool_en": "5Y LPR 3.60% · 1Y MLF 2.00% · RRR 6.6%",
        "secondary_tool_zh": "5年期LPR 3.60% · 1年期MLF 2.00% · 降准空间充裕",
        "balance_sheet_display_en": "¥49.86T (37.2% of GDP)",
        "balance_sheet_display_zh": "49.86 万亿元人民币 (占GDP 37.2%)",
        "operational_signal_en": "Secondary market government bond trading active; supportive monetary policy stance reinforced.",
        "operational_signal_zh": "国债买卖常态化操作；坚持支持性货币政策立场，引导综合融资成本下行。",
        "rate_change_12m": -35,
        "cycle_phase_en": "Supportive / Structural Ease",
        "cycle_phase_zh": "支持性宽松 / 结构性降息",
        "cycle_badge": "easing",
        "next_meeting_date": "2026-12-20",
        "next_meeting_name_en": "Monthly LPR Fixing & Liquidity Window",
        "next_meeting_name_zh": "月度 LPR 报价发布与年末流动性投放",
        "consensus_action_en": "Maintain 1Y 3.10% / 5Y 3.60%",
        "consensus_action_zh": "维持 1年期 3.10% / 5年期 3.60% 平稳",
        "has_corridor_card": True,
    },
    "TR": {
        "flag": "🇹🇷",
        "name_en": "Turkey",
        "name_zh": "土耳其",
        "region": "em",
        "region_en": "Major Emerging Markets",
        "region_zh": "重要新兴市场",
        "cb_name_en": "Central Bank of the Republic of Turkey (TCMB)",
        "cb_name_zh": "土耳其共和国中央银行 (TCMB)",
        "cb_short": "TCMB",
        "policy_tool_en": "1-Week Repo Auction Rate",
        "policy_tool_zh": "一周回购拍卖利率 (1-Week Repo)",
        "corridor_ceiling_name": "Overnight Lending / Late Liquidity",
        "corridor_ceiling_rate": 39.00,
        "corridor_floor_name": "Overnight Borrowing Rate",
        "corridor_floor_rate": 33.00,
        "secondary_tool_en": "Lira Deposit Share Mandate & Sterilization",
        "secondary_tool_zh": "本币存款占比考核与超额里拉流动性冲销",
        "balance_sheet_display_en": "TRY 6.84T (18.5% of GDP)",
        "balance_sheet_display_zh": "6.84 万亿里拉 (占GDP 18.5%)",
        "operational_signal_en": "Orthodox monetary disinflation track; high positive real rate (+6.27%) disciplining FX expectations.",
        "operational_signal_zh": "正统货币紧缩与反通胀轨道；高达 +6.27% 实际正利率强力锚定通胀预期与汇率。",
        "rate_change_12m": -1400,
        "cycle_phase_en": "Calibrated Disinflation Easing",
        "cycle_phase_zh": "限制性降息 / 抗通胀延续",
        "cycle_badge": "easing",
        "next_meeting_date": "2026-12-24",
        "next_meeting_name_en": "PPK Monetary Policy Committee Rate Decision",
        "next_meeting_name_zh": "PPK 货币政策委员会利率决议",
        "consensus_action_en": "Cut 150 bps to 34.50%",
        "consensus_action_zh": "有序降息 150 个基点至 34.50%",
        "has_corridor_card": True,
    },
    "ZA": {
        "flag": "🇿🇦",
        "name_en": "South Africa",
        "name_zh": "南非",
        "region": "em",
        "region_en": "Major Emerging Markets",
        "region_zh": "重要新兴市场",
        "cb_name_en": "South African Reserve Bank (SARB)",
        "cb_name_zh": "南非储备银行 (SARB)",
        "cb_short": "SARB",
        "policy_tool_en": "SARB Main Repo Rate",
        "policy_tool_zh": "SARB 官方回购基准利率",
        "corridor_ceiling_name": "Standing Facility Lending Ceiling",
        "corridor_ceiling_rate": 8.25,
        "corridor_floor_name": "Standing Facility Deposit Floor",
        "corridor_floor_rate": 6.25,
        "secondary_tool_en": "Inflation Target Midpoint 4.50% Anchor",
        "secondary_tool_zh": "锚定通胀目标区间中值 4.50%",
        "balance_sheet_display_en": "ZAR 1,280B (17.8% of GDP)",
        "balance_sheet_display_zh": "12,800 亿兰特 (占GDP 17.8%)",
        "operational_signal_en": "Headline inflation returned to 4.5% target midpoint; cautious 25bps easing cycle underway.",
        "operational_signal_zh": "头寸通胀回落至 4.5% 目标中值；开启每次 25 个基点的稳妥降息周期。",
        "rate_change_12m": -75,
        "cycle_phase_en": "Calibrated Easing Cycle",
        "cycle_phase_zh": "稳步降息周期 / 中性回归",
        "cycle_badge": "easing",
        "next_meeting_date": "2027-01-21",
        "next_meeting_name_en": "Monetary Policy Committee (MPC) Statement",
        "next_meeting_name_zh": "MPC 货币政策委员会决议与声明",
        "consensus_action_en": "Cut 25 bps to 7.00%",
        "consensus_action_zh": "降息 25 个基点至 7.00%",
        "has_corridor_card": True,
    },
    "KR": {
        "flag": "🇰🇷",
        "name_en": "South Korea",
        "name_zh": "韩国",
        "region": "em",
        "region_en": "Major Emerging Markets",
        "region_zh": "重要新兴市场",
        "cb_name_en": "Bank of Korea (BOK)",
        "cb_name_zh": "韩国银行 (BOK)",
        "cb_short": "BOK",
        "policy_tool_en": "BOK Base Rate",
        "policy_tool_zh": "韩国银行基准利率",
        "corridor_ceiling_name": "Liquidity Support Lending Window",
        "corridor_ceiling_rate": 4.00,
        "corridor_floor_name": "Overnight Deposit Facility",
        "corridor_floor_rate": 2.00,
        "secondary_tool_en": "Household Debt Macroprudential Tightening",
        "secondary_tool_zh": "家庭债务宏观审慎调控加强",
        "balance_sheet_display_en": "KRW 580.4T (24.6% of GDP)",
        "balance_sheet_display_zh": "580.4 万亿韩元 (占GDP 24.6%)",
        "operational_signal_en": "Gradual pivot to support domestic demand while closely capping Seoul real estate leverage.",
        "operational_signal_zh": "转向支持内需复苏，同时配合宏观审慎严防首尔房地产债务杠杆反弹。",
        "rate_change_12m": -50,
        "cycle_phase_en": "Cautious Easing Pivot",
        "cycle_phase_zh": "审慎转向 / 渐进降息",
        "cycle_badge": "easing",
        "next_meeting_date": "2027-01-14",
        "next_meeting_name_en": "Monetary Policy Board Base Rate Decision",
        "next_meeting_name_zh": "金融货币委员会基准利率裁决",
        "consensus_action_en": "Hold at 3.00% (75% prob)",
        "consensus_action_zh": "维持 3.00% 观望 (75% 概率)",
        "has_corridor_card": True,
    },
    "TW": {
        "flag": "🇹🇼",
        "name_en": "Taiwan",
        "name_zh": "中国台湾",
        "region": "em",
        "region_en": "Major Emerging Markets",
        "region_zh": "重要新兴市场",
        "cb_name_en": "Central Bank of the Republic of China (CBC)",
        "cb_name_zh": "中央银行 (CBC)",
        "cb_short": "CBC",
        "policy_tool_en": "CBC Discount Rate",
        "policy_tool_zh": "重贴现率 (Discount Rate)",
        "corridor_ceiling_name": "Accommodated Loan Secured",
        "corridor_ceiling_rate": 2.375,
        "corridor_floor_name": "Accommodated Loan Unsecured",
        "corridor_floor_rate": 1.625,
        "secondary_tool_en": "Selective Real Estate Credit Controls",
        "secondary_tool_zh": "第七波不动产选择性信用管制措施",
        "balance_sheet_display_en": "TWD 19.8T (82.1% of GDP)",
        "balance_sheet_display_zh": "19.8 万亿新台币 (占GDP 82.1%)",
        "operational_signal_en": "Mild tightening bias maintained via real estate credit restrictions and liquidity freeze.",
        "operational_signal_zh": "透过紧缩房市信用管制与外汇冲销，维持温和紧缩姿态不变。",
        "rate_change_12m": 0,
        "cycle_phase_en": "Tight Hold / Macroprudential",
        "cycle_phase_zh": "高位坚守 / 审慎信用紧缩",
        "cycle_badge": "plateau",
        "next_meeting_date": "2026-12-17",
        "next_meeting_name_en": "Q4 Board Meeting & Rate Decision",
        "next_meeting_name_zh": "第四季理监事联席会议利率决议",
        "consensus_action_en": "Hold at 2.00%",
        "consensus_action_zh": "维持 2.00% 按兵不动",
        "has_corridor_card": False,
    },
    "HU": {
        "flag": "🇭🇺",
        "name_en": "Hungary",
        "name_zh": "匈牙利",
        "region": "cee",
        "region_en": "CEE-4 Economies",
        "region_zh": "中东欧核心四国",
        "cb_name_en": "Magyar Nemzeti Bank (MNB)",
        "cb_name_zh": "匈牙利国家银行 (MNB)",
        "cb_short": "MNB",
        "policy_tool_en": "MNB Base Rate",
        "policy_tool_zh": "MNB 基准利率 (Base Rate)",
        "corridor_ceiling_name": "O/N Collateralized Lending Ceiling",
        "corridor_ceiling_rate": 7.25,
        "corridor_floor_name": "O/N Deposit Facility Floor",
        "corridor_floor_rate": 5.25,
        "secondary_tool_en": "Symmetric ±100 bps Interest Rate Corridor",
        "secondary_tool_zh": "对称 ±100 基点利率走廊",
        "balance_sheet_display_en": "HUF 26,450B (31.5% of GDP)",
        "balance_sheet_display_zh": "26.45 万亿福林 (占GDP 31.5%)",
        "operational_signal_en": "Maintaining restrictive stance to anchor EUR/HUF stability and insulate against global risk spikes.",
        "operational_signal_zh": "维持限制性高实际利率 (+4.15%)，捍卫福林汇率稳定并抵御地缘风险外溢。",
        "rate_change_12m": -375,
        "cycle_phase_en": "Restrictive Hold / Plateau",
        "cycle_phase_zh": "限制性高台 / 汇率防守",
        "cycle_badge": "plateau",
        "next_meeting_date": "2026-12-15",
        "next_meeting_name_en": "Monetary Council Rate Decision & Inflation Report",
        "next_meeting_name_zh": "货币委员会利率决议与季度通胀报告",
        "consensus_action_en": "Hold at 6.25%",
        "consensus_action_zh": "维持 6.25% 按兵不动",
        "has_corridor_card": True,
    },
    "PL": {
        "flag": "🇵🇱",
        "name_en": "Poland",
        "name_zh": "波兰",
        "region": "cee",
        "region_en": "CEE-4 Economies",
        "region_zh": "中东欧核心四国",
        "cb_name_en": "Narodowy Bank Polski (NBP)",
        "cb_name_zh": "波兰国家银行 (NBP)",
        "cb_short": "NBP",
        "policy_tool_en": "NBP Reference Rate",
        "policy_tool_zh": "NBP 参考基准利率",
        "corridor_ceiling_name": "Lombard Rate Ceiling",
        "corridor_ceiling_rate": 4.25,
        "corridor_floor_name": "Deposit Rate Floor",
        "corridor_floor_rate": 3.25,
        "secondary_tool_en": "7D NBP Bills Open Market Operations",
        "secondary_tool_zh": "7天期央行票据公开市场操作",
        "balance_sheet_display_en": "PLN 890.2B (24.8% of GDP)",
        "balance_sheet_display_zh": "8,902 亿兹罗提 (占GDP 24.8%)",
        "operational_signal_en": "Prolonged hold stance maintained due to energy subsidy unwinding and persistent wage growth.",
        "operational_signal_zh": "能源补贴退出推高通胀背景下，货币政策委员会维持长期按兵不动姿态。",
        "rate_change_12m": 0,
        "cycle_phase_en": "Vigilant Hold / Defensive",
        "cycle_phase_zh": "观望防守 / 警惕通胀反弹",
        "cycle_badge": "plateau",
        "next_meeting_date": "2026-12-09",
        "next_meeting_name_en": "Monetary Policy Council (RPP) Rate Decision",
        "next_meeting_name_zh": "货币政策委员会 (RPP) 利率决议",
        "consensus_action_en": "Hold at 3.75%",
        "consensus_action_zh": "维持 3.75% 坚定不动",
        "has_corridor_card": False,
    },
    "CZ": {
        "flag": "🇨🇿",
        "name_en": "Czechia",
        "name_zh": "捷克",
        "region": "cee",
        "region_en": "CEE-4 Economies",
        "region_zh": "中东欧核心四国",
        "cb_name_en": "Czech National Bank (CNB)",
        "cb_name_zh": "捷克国家银行 (CNB)",
        "cb_short": "CNB",
        "policy_tool_en": "2-Week Repo Rate",
        "policy_tool_zh": "两周回购基准利率 (2W Repo)",
        "corridor_ceiling_name": "Lombard Facility Ceiling",
        "corridor_ceiling_rate": 4.50,
        "corridor_floor_name": "Discount Facility Floor",
        "corridor_floor_rate": 2.50,
        "secondary_tool_en": "Symmetric ±100 bps Operational Corridor",
        "secondary_tool_zh": "对称 ±100 基点准备金走廊",
        "balance_sheet_display_en": "CZK 2,980B (38.2% of GDP)",
        "balance_sheet_display_zh": "2.98 万亿克朗 (占GDP 38.2%)",
        "operational_signal_en": "Inflation stabilized around 2.0% target; rate cuts paused to assess service inflation persistence.",
        "operational_signal_zh": "通胀重回 2.0% 目标靶心；降息步伐暂歇以评估服务业价格韧性。",
        "rate_change_12m": -275,
        "cycle_phase_en": "Neutral Plateau / Paused",
        "cycle_phase_zh": "中性平稳 / 降息暂停",
        "cycle_badge": "neutral",
        "next_meeting_date": "2026-12-17",
        "next_meeting_name_en": "Bank Board Monetary Policy Decision",
        "next_meeting_name_zh": "银行理事会货币政策决议",
        "consensus_action_en": "Hold at 3.50%",
        "consensus_action_zh": "维持 3.50% 保持观望",
        "has_corridor_card": False,
    },
    "RO": {
        "flag": "🇷🇴",
        "name_en": "Romania",
        "name_zh": "罗马尼亚",
        "region": "cee",
        "region_en": "CEE-4 Economies",
        "region_zh": "中东欧核心四国",
        "cb_name_en": "National Bank of Romania (BNR)",
        "cb_name_zh": "罗马尼亚国家银行 (BNR)",
        "cb_short": "BNR",
        "policy_tool_en": "Monetary Policy Rate",
        "policy_tool_zh": "货币政策基准利率",
        "corridor_ceiling_name": "Lending Facility (Lombard)",
        "corridor_ceiling_rate": 7.50,
        "corridor_floor_name": "Deposit Facility Floor",
        "corridor_floor_rate": 5.50,
        "secondary_tool_en": "RON FX Managed Float & Minimum Reserves",
        "secondary_tool_zh": "列伊管理浮动与较高法定准备金率",
        "balance_sheet_display_en": "RON 340B (20.5% of GDP)",
        "balance_sheet_display_zh": "3,400 亿列伊 (占GDP 20.5%)",
        "operational_signal_en": "High twin deficits and fiscal uncertainty require keeping nominal rates high at 6.50%.",
        "operational_signal_zh": "高双赤字与财政不确定性迫使基准利率坚守 6.50% 限制性高位。",
        "rate_change_12m": -50,
        "cycle_phase_en": "Restrictive Vigilance",
        "cycle_phase_zh": "限制性观望 / 防范赤字冲击",
        "cycle_badge": "plateau",
        "next_meeting_date": "2027-01-15",
        "next_meeting_name_en": "Board Monetary Policy Meeting",
        "next_meeting_name_zh": "理事会货币政策会议",
        "consensus_action_en": "Hold at 6.50%",
        "consensus_action_zh": "维持 6.50% 不变",
        "has_corridor_card": False,
    },
    "KZ": {
        "flag": "🇰🇿",
        "name_en": "Kazakhstan",
        "name_zh": "哈萨克斯坦",
        "region": "frontier",
        "region_en": "Frontier & Regional Anchors",
        "region_zh": "前沿与离岸锚点",
        "cb_name_en": "National Bank of Kazakhstan (NBK)",
        "cb_name_zh": "哈萨克斯坦国家银行 (NBK)",
        "cb_short": "NBK",
        "policy_tool_en": "NBK Base Rate",
        "policy_tool_zh": "NBK 基准利率",
        "corridor_ceiling_name": "Liquidity Providing Standing Facility",
        "corridor_ceiling_rate": 15.25,
        "corridor_floor_name": "Liquidity Absorbing Standing Facility",
        "corridor_floor_rate": 13.25,
        "secondary_tool_en": "Symmetric ±100 bps Corridor",
        "secondary_tool_zh": "对称 ±100 基点走廊",
        "balance_sheet_display_en": "KZT 32,800B (26.5% of GDP)",
        "balance_sheet_display_zh": "32.8 万亿坚戈 (占GDP 26.5%)",
        "operational_signal_en": "Prudent monetary stance maintained; real rate (+5.01%) supporting disinflation and tenge stability.",
        "operational_signal_zh": "坚持审慎政策立场；+5.01% 的高实际正利率助力通胀回落与坚戈汇率平稳。",
        "rate_change_12m": -150,
        "cycle_phase_en": "Prudent Restrictive Hold",
        "cycle_phase_zh": "审慎高台 / 稳固抗通胀成果",
        "cycle_badge": "plateau",
        "next_meeting_date": "2026-12-11",
        "next_meeting_name_en": "Monetary Policy Base Rate Decision",
        "next_meeting_name_zh": "货币政策基准利率决议",
        "consensus_action_en": "Hold at 14.25%",
        "consensus_action_zh": "维持 14.25% 按兵不动",
        "has_corridor_card": False,
    },
    "UZ": {
        "flag": "🇺🇿",
        "name_en": "Uzbekistan",
        "name_zh": "乌兹别克斯坦",
        "region": "frontier",
        "region_en": "Frontier & Regional Anchors",
        "region_zh": "前沿与离岸锚点",
        "cb_name_en": "Central Bank of Uzbekistan (CBU)",
        "cb_name_zh": "乌兹别克斯坦中央银行 (CBU)",
        "cb_short": "CBU",
        "policy_tool_en": "CBU Policy Rate",
        "policy_tool_zh": "CBU 政策利率",
        "corridor_ceiling_name": "Overnight Repo Facility",
        "corridor_ceiling_rate": 14.50,
        "corridor_floor_name": "Overnight Deposit Facility",
        "corridor_floor_rate": 12.50,
        "secondary_tool_en": "Tariff Liberalization Compensation",
        "secondary_tool_zh": "能源公用事业调价对冲操作",
        "balance_sheet_display_en": "UZS 148,000B (12.4% of GDP)",
        "balance_sheet_display_zh": "148 万亿苏姆 (占GDP 12.4%)",
        "operational_signal_en": "High real rate (+7.27%) actively suppressing secondary inflationary effects of utility tariff reforms.",
        "operational_signal_zh": "高达 +7.27% 实际政策利率有效压制公用事业价格改革引发的二级通胀外溢。",
        "rate_change_12m": -50,
        "cycle_phase_en": "High Real Yield Cushion",
        "cycle_phase_zh": "高实际正收益 / 限制性吸收",
        "cycle_badge": "plateau",
        "next_meeting_date": "2026-12-17",
        "next_meeting_name_en": "Board Monetary Policy Review Meeting",
        "next_meeting_name_zh": "理事会货币政策审议会议",
        "consensus_action_en": "Hold at 13.50%",
        "consensus_action_zh": "维持 13.50% 坚决防守",
        "has_corridor_card": False,
    },
    "EG": {
        "flag": "🇪🇬",
        "name_en": "Egypt",
        "name_zh": "埃及",
        "region": "frontier",
        "region_en": "Frontier & Regional Anchors",
        "region_zh": "前沿与离岸锚点",
        "cb_name_en": "Central Bank of Egypt (CBE)",
        "cb_name_zh": "埃及中央银行 (CBE)",
        "cb_short": "CBE",
        "policy_tool_en": "Overnight Deposit Rate",
        "policy_tool_zh": "隔夜存款基准利率",
        "corridor_ceiling_name": "Overnight Lending Facility",
        "corridor_ceiling_rate": 25.50,
        "corridor_floor_name": "Overnight Deposit Facility",
        "corridor_floor_rate": 24.50,
        "secondary_tool_en": "Main Operation 7D Repo 25.00%",
        "secondary_tool_zh": "主要操作 7 天期回购利率 25.00%",
        "balance_sheet_display_en": "EGP 5,200B (38.0% of GDP)",
        "balance_sheet_display_zh": "5.2 万亿埃镑 (占GDP 38.0%)",
        "operational_signal_en": "Massive disinflation progress allows high real rate (+9.96%) to re-anchor FX reserves ($46B+).",
        "operational_signal_zh": "显著去通胀进展使得 +9.96% 极高实际利率助力外储强劲回升至 460 亿美元以上。",
        "rate_change_12m": 0,
        "cycle_phase_en": "Disinflationary Easing Preparation",
        "cycle_phase_zh": "高息抗通胀 / 降息预备期",
        "cycle_badge": "plateau",
        "next_meeting_date": "2026-12-24",
        "next_meeting_name_en": "Monetary Policy Committee (MPC) Rate Decision",
        "next_meeting_name_zh": "MPC 货币政策委员会利率决议",
        "consensus_action_en": "Cut 100 bps to 23.50%",
        "consensus_action_zh": "下调 100 个基点至 23.50%",
        "has_corridor_card": False,
    },
    "NG": {
        "flag": "🇳🇬",
        "name_en": "Nigeria",
        "name_zh": "尼日利亚",
        "region": "frontier",
        "region_en": "Frontier & Regional Anchors",
        "region_zh": "前沿与离岸锚点",
        "cb_name_en": "Central Bank of Nigeria (CBN)",
        "cb_name_zh": "尼日利亚中央银行 (CBN)",
        "cb_short": "CBN",
        "policy_tool_en": "Monetary Policy Rate (MPR)",
        "policy_tool_zh": "货币政策基准利率 (MPR)",
        "corridor_ceiling_name": "Standing Lending Facility (SLF +500bps)",
        "corridor_ceiling_rate": 32.25,
        "corridor_floor_name": "Standing Deposit Facility (SDF -100bps)",
        "corridor_floor_rate": 26.25,
        "secondary_tool_en": "Asymmetric Corridor (+500/-100 bps) · CRR 50.0%",
        "secondary_tool_zh": "不对称走廊 (+500/-100 基点) · 存款准备金率 50.0%",
        "balance_sheet_display_en": "NGN 38,500B (15.2% of GDP)",
        "balance_sheet_display_zh": "38.5 万亿奈拉 (占GDP 15.2%)",
        "operational_signal_en": "Deeply restrictive stance (+11.86% real rate) battling FX pass-through and food inflation shocks.",
        "operational_signal_zh": "全球最高实际利率 (+11.86%)，以激进正统紧缩反制汇率贬值与食品通胀冲击。",
        "rate_change_12m": 450,
        "cycle_phase_en": "Aggressive Restrictive Fight",
        "cycle_phase_zh": "激进抗通胀 / 极端限制性",
        "cycle_badge": "hiking",
        "next_meeting_date": "2027-01-26",
        "next_meeting_name_en": "Monetary Policy Committee (MPC) Meeting",
        "next_meeting_name_zh": "MPC 货币政策委员会决议",
        "consensus_action_en": "Hold at 27.25%",
        "consensus_action_zh": "维持 27.25% 坚守紧缩",
        "has_corridor_card": False,
    },
    "HK": {
        "flag": "🇭🇰",
        "name_en": "Hong Kong",
        "name_zh": "中国香港",
        "region": "frontier",
        "region_en": "Frontier & Regional Anchors",
        "region_zh": "前沿与离岸锚点",
        "cb_name_en": "Hong Kong Monetary Authority (HKMA)",
        "cb_name_zh": "香港金融管理局 (HKMA)",
        "cb_short": "HKMA",
        "policy_tool_en": "HKMA Base Rate (Fed Anchor)",
        "policy_tool_zh": "金管局基本利率 (盯住美联储)",
        "corridor_ceiling_name": "Discount Window Base Rate",
        "corridor_ceiling_rate": 3.75,
        "corridor_floor_name": "Overnight HIBOR / Aggregate Balance",
        "corridor_floor_rate": 3.50,
        "secondary_tool_en": "Currency Board Linked Exchange Rate (7.75-7.85)",
        "secondary_tool_zh": "联系汇率制度保证兑换区间 (7.75-7.85)",
        "balance_sheet_display_en": "HKD 4,050B (134.5% of GDP)",
        "balance_sheet_display_zh": "4.05 万亿港元 (占GDP 134.5%)",
        "operational_signal_en": "LERS automated mechanism transmits US rate moves into Hong Kong monetary conditions.",
        "operational_signal_zh": "联系汇率制度自动传导机制：基准利率即时跟随美联储政策目标同步调整。",
        "rate_change_12m": -150,
        "cycle_phase_en": "Pegged Synchronization",
        "cycle_phase_zh": "联汇同步 / 跟随降息",
        "cycle_badge": "easing",
        "next_meeting_date": "2026-12-18",
        "next_meeting_name_en": "Base Rate Adjustment Following US FOMC",
        "next_meeting_name_zh": "跟随美联储 FOMC 决议即时调整基本利率",
        "consensus_action_en": "Follow Fed (Hold at 3.75%)",
        "consensus_action_zh": "跟随美联储维持 3.75% 联汇基准",
        "has_corridor_card": False,
    },
}

# 60+ Scheduled 2026/2027 Central Bank Meetings across all 18 economies
CALENDAR_EVENTS = [
    # Late 2026
    {"date": "2026-11-05", "code": "US", "cb_en": "Federal Reserve (Fed)", "cb_zh": "美联储", "region": "dm", "event_en": "FOMC Statement & Press Conference", "event_zh": "FOMC 利率决议与新闻发布会", "type": "decision", "tier": 1, "rate": "3.88%", "consensus_en": "Hold 3.88%", "consensus_zh": "维持 3.88%"},
    {"date": "2026-11-05", "code": "PL", "cb_en": "Narodowy Bank Polski (NBP)", "cb_zh": "波兰央行", "region": "cee", "event_en": "Monetary Policy Council (RPP) Rate Decision", "event_zh": "RPP 利率决议", "type": "decision", "tier": 2, "rate": "3.75%", "consensus_en": "Hold 3.75%", "consensus_zh": "维持 3.75%"},
    {"date": "2026-11-06", "code": "CZ", "cb_en": "Czech National Bank (CNB)", "cb_zh": "捷克央行", "region": "cee", "event_en": "Bank Board Monetary Decision & MPR", "event_zh": "银行理事会利率决议与货币政策报告", "type": "projection", "tier": 1, "rate": "3.50%", "consensus_en": "Hold 3.50%", "consensus_zh": "维持 3.50%"},
    {"date": "2026-11-10", "code": "RO", "cb_en": "National Bank of Romania (BNR)", "cb_zh": "罗马尼亚央行", "region": "cee", "event_en": "Board Monetary Policy Meeting & Inflation Report", "event_zh": "理事会利率决议与通胀报告", "type": "projection", "tier": 1, "rate": "6.50%", "consensus_en": "Hold 6.50%", "consensus_zh": "维持 6.50%"},
    {"date": "2026-11-20", "code": "CN", "cb_en": "People's Bank of China (PBC)", "cb_zh": "中国央行", "region": "em", "event_en": "Monthly Loan Prime Rate (LPR) Fixing", "event_zh": "月度贷款市场报价利率 (LPR) 报价", "type": "decision", "tier": 2, "rate": "3.10%", "consensus_en": "Maintain 3.10% / 3.60%", "consensus_zh": "维持 3.10% / 3.60%"},
    {"date": "2026-11-24", "code": "HU", "cb_en": "Magyar Nemzeti Bank (MNB)", "cb_zh": "匈牙利央行", "region": "cee", "event_en": "Monetary Council Rate-Setting Meeting", "event_zh": "货币委员会利率决议", "type": "decision", "tier": 2, "rate": "6.25%", "consensus_en": "Hold 6.25%", "consensus_zh": "维持 6.25%"},
    {"date": "2026-11-24", "code": "NG", "cb_en": "Central Bank of Nigeria (CBN)", "cb_zh": "尼日利亚央行", "region": "frontier", "event_en": "Monetary Policy Committee (MPC) Meeting", "event_zh": "MPC 货币政策决议", "type": "decision", "tier": 2, "rate": "27.25%", "consensus_en": "Hold 27.25%", "consensus_zh": "维持 27.25%"},
    {"date": "2026-11-26", "code": "TR", "cb_en": "Central Bank of Turkey (TCMB)", "cb_zh": "土耳其央行", "region": "em", "event_en": "PPK Monetary Policy Committee Rate Decision", "event_zh": "PPK 货币政策委员会决议", "type": "decision", "tier": 1, "rate": "36.00%", "consensus_en": "Hold 36.00%", "consensus_zh": "维持 36.00%"},
    {"date": "2026-11-26", "code": "ZA", "cb_en": "South African Reserve Bank (SARB)", "cb_zh": "南非央行", "region": "em", "event_en": "MPC Repo Rate Decision & Statement", "event_zh": "MPC 回购利率决议与政策声明", "type": "decision", "tier": 2, "rate": "7.25%", "consensus_en": "Cut 25 bps to 7.00%", "consensus_zh": "降息 25 个基点至 7.00%"},
    {"date": "2026-11-26", "code": "KR", "cb_en": "Bank of Korea (BOK)", "cb_zh": "韩国央行", "region": "em", "event_en": "Monetary Policy Board Base Rate Decision", "event_zh": "金融货币委员会基准利率裁决", "type": "decision", "tier": 2, "rate": "3.00%", "consensus_en": "Hold 3.00%", "consensus_zh": "维持 3.00%"},
    {"date": "2026-11-27", "code": "KZ", "cb_en": "National Bank of Kazakhstan (NBK)", "cb_zh": "哈萨克斯坦央行", "region": "frontier", "event_en": "Monetary Policy Base Rate Decision", "event_zh": "货币政策基准利率决议", "type": "decision", "tier": 2, "rate": "14.25%", "consensus_en": "Hold 14.25%", "consensus_zh": "维持 14.25%"},
    {"date": "2026-12-09", "code": "PL", "cb_en": "Narodowy Bank Polski (NBP)", "cb_zh": "波兰央行", "region": "cee", "event_en": "Monetary Policy Council (RPP) Rate Decision", "event_zh": "RPP 利率决议", "type": "decision", "tier": 2, "rate": "3.75%", "consensus_en": "Hold 3.75%", "consensus_zh": "维持 3.75%"},
    {"date": "2026-12-11", "code": "EA", "cb_en": "European Central Bank (ECB)", "cb_zh": "欧洲央行", "region": "dm", "event_en": "Governing Council Decision & Staff Projections", "event_zh": "管理委员会利率决议与宏观经济预测", "type": "projection", "tier": 1, "rate": "2.50%", "consensus_en": "Cut 25 bps to 2.25%", "consensus_zh": "降息 25 个基点至 2.25%"},
    {"date": "2026-12-11", "code": "KZ", "cb_en": "National Bank of Kazakhstan (NBK)", "cb_zh": "哈萨克斯坦央行", "region": "frontier", "event_en": "Monetary Policy Base Rate Decision", "event_zh": "货币政策基准利率决议", "type": "decision", "tier": 2, "rate": "14.25%", "consensus_en": "Hold 14.25%", "consensus_zh": "维持 14.25%"},
    {"date": "2026-12-15", "code": "HU", "cb_en": "Magyar Nemzeti Bank (MNB)", "cb_zh": "匈牙利央行", "region": "cee", "event_en": "Monetary Council Rate Decision & Inflation Report", "event_zh": "货币委员会利率决议与季度通胀报告", "type": "projection", "tier": 1, "rate": "6.25%", "consensus_en": "Hold 6.25%", "consensus_zh": "维持 6.25%"},
    {"date": "2026-12-17", "code": "CZ", "cb_en": "Czech National Bank (CNB)", "cb_zh": "捷克央行", "region": "cee", "event_en": "Bank Board Monetary Policy Decision", "event_zh": "银行理事会利率决议", "type": "decision", "tier": 2, "rate": "3.50%", "consensus_en": "Hold 3.50%", "consensus_zh": "维持 3.50%"},
    {"date": "2026-12-17", "code": "TW", "cb_en": "Central Bank of China (Taiwan)", "cb_zh": "中国台湾央行", "region": "em", "event_en": "Q4 Board Meeting & Rate Decision", "event_zh": "第四季理监事联席会议利率决议", "type": "decision", "tier": 2, "rate": "2.00%", "consensus_en": "Hold 2.00%", "consensus_zh": "维持 2.00%"},
    {"date": "2026-12-17", "code": "UZ", "cb_en": "Central Bank of Uzbekistan (CBU)", "cb_zh": "乌兹别克斯坦央行", "region": "frontier", "event_en": "Board Monetary Policy Review Meeting", "event_zh": "理事会货币政策审议会议", "type": "decision", "tier": 2, "rate": "13.50%", "consensus_en": "Hold 13.50%", "consensus_zh": "维持 13.50%"},
    {"date": "2026-12-18", "code": "US", "cb_en": "Federal Reserve (Fed)", "cb_zh": "美联储", "region": "dm", "event_en": "FOMC Statement, Press Conf & SEP (Dot Plot)", "event_zh": "FOMC 利率决议、新闻发布会与季度经济预测(点阵图)", "type": "projection", "tier": 1, "rate": "3.88%", "consensus_en": "Hold at 3.88% (85% prob)", "consensus_zh": "维持 3.88% 按兵不动 (85% 概率)"},
    {"date": "2026-12-18", "code": "UK", "cb_en": "Bank of England (BoE)", "cb_zh": "英格兰银行", "region": "dm", "event_en": "MPC Bank Rate Decision & Minutes", "event_zh": "MPC 利率决议与会议纪要", "type": "decision", "tier": 1, "rate": "3.75%", "consensus_en": "Hold at 3.75% (80% prob)", "consensus_zh": "维持 3.75% 按兵不动 (80% 概率)"},
    {"date": "2026-12-18", "code": "HK", "cb_en": "Hong Kong Monetary Authority (HKMA)", "cb_zh": "香港金管局", "region": "frontier", "event_en": "Base Rate Adjustment Following US FOMC", "event_zh": "跟随美联储 FOMC 决议即时调整基本利率", "type": "decision", "tier": 2, "rate": "3.75%", "consensus_en": "Follow Fed (Hold at 3.75%)", "consensus_zh": "跟随美联储维持 3.75%"},
    {"date": "2026-12-19", "code": "JP", "cb_en": "Bank of Japan (BoJ)", "cb_zh": "日本银行", "region": "dm", "event_en": "Monetary Policy Meeting (MPM) Decision", "event_zh": "货币政策会议 (MPM) 利率决议", "type": "decision", "tier": 1, "rate": "1.04%", "consensus_en": "Hike 25 bps to 1.25%", "consensus_zh": "加息 25 个基点至 1.25%"},
    {"date": "2026-12-20", "code": "CN", "cb_en": "People's Bank of China (PBC)", "cb_zh": "中国央行", "region": "em", "event_en": "Monthly LPR Fixing & Year-end Operations", "event_zh": "月度 LPR 报价发布与年末流动性投放", "type": "decision", "tier": 2, "rate": "3.10%", "consensus_en": "Maintain 3.10% / 3.60%", "consensus_zh": "维持 3.10% / 3.60%"},
    {"date": "2026-12-24", "code": "TR", "cb_en": "Central Bank of Turkey (TCMB)", "cb_zh": "土耳其央行", "region": "em", "event_en": "PPK Monetary Policy Committee Rate Decision", "event_zh": "PPK 货币政策委员会决议", "type": "decision", "tier": 1, "rate": "36.00%", "consensus_en": "Cut 150 bps to 34.50%", "consensus_zh": "降息 150 个基点至 34.50%"},
    {"date": "2026-12-24", "code": "EG", "cb_en": "Central Bank of Egypt (CBE)", "cb_zh": "埃及央行", "region": "frontier", "event_en": "Monetary Policy Committee (MPC) Rate Decision", "event_zh": "MPC 利率决议", "type": "decision", "tier": 1, "rate": "24.50%", "consensus_en": "Cut 100 bps to 23.50%", "consensus_zh": "下调 100 个基点至 23.50%"},

    # Early 2027
    {"date": "2027-01-13", "code": "PL", "cb_en": "Narodowy Bank Polski (NBP)", "cb_zh": "波兰央行", "region": "cee", "event_en": "Monetary Policy Council (RPP) Rate Decision", "event_zh": "RPP 利率决议", "type": "decision", "tier": 2, "rate": "3.75%", "consensus_en": "Hold 3.75%", "consensus_zh": "维持 3.75%"},
    {"date": "2027-01-14", "code": "KR", "cb_en": "Bank of Korea (BOK)", "cb_zh": "韩国央行", "region": "em", "event_en": "Monetary Policy Board Base Rate Decision", "event_zh": "金融货币委员会基准利率裁决", "type": "decision", "tier": 2, "rate": "3.00%", "consensus_en": "Hold 3.00%", "consensus_zh": "维持 3.00%"},
    {"date": "2027-01-15", "code": "RO", "cb_en": "National Bank of Romania (BNR)", "cb_zh": "罗马尼亚央行", "region": "cee", "event_en": "Board Monetary Policy Meeting", "event_zh": "理事会利率决议", "type": "decision", "tier": 2, "rate": "6.50%", "consensus_en": "Hold 6.50%", "consensus_zh": "维持 6.50%"},
    {"date": "2027-01-20", "code": "CN", "cb_en": "People's Bank of China (PBC)", "cb_zh": "中国央行", "region": "em", "event_en": "Monthly Loan Prime Rate (LPR) Fixing", "event_zh": "月度 LPR 报价", "type": "decision", "tier": 2, "rate": "3.10%", "consensus_en": "Maintain 3.10%", "consensus_zh": "维持 3.10%"},
    {"date": "2027-01-21", "code": "ZA", "cb_en": "South African Reserve Bank (SARB)", "cb_zh": "南非央行", "region": "em", "event_en": "Monetary Policy Committee (MPC) Statement", "event_zh": "MPC 利率决议与政策评估", "type": "decision", "tier": 2, "rate": "7.00%", "consensus_en": "Cut 25 bps to 6.75%", "consensus_zh": "降息 25 个基点至 6.75%"},
    {"date": "2027-01-22", "code": "KZ", "cb_en": "National Bank of Kazakhstan (NBK)", "cb_zh": "哈萨克斯坦央行", "region": "frontier", "event_en": "Monetary Policy Base Rate Decision", "event_zh": "货币政策基准利率决议", "type": "decision", "tier": 2, "rate": "14.25%", "consensus_en": "Hold 14.25%", "consensus_zh": "维持 14.25%"},
    {"date": "2027-01-23", "code": "JP", "cb_en": "Bank of Japan (BoJ)", "cb_zh": "日本银行", "region": "dm", "event_en": "MPM Decision & Outlook Report", "event_zh": "MPM 利率决议与经济展望报告", "type": "projection", "tier": 1, "rate": "1.25%", "consensus_en": "Hold 1.25%", "consensus_zh": "维持 1.25%"},
    {"date": "2027-01-26", "code": "HU", "cb_en": "Magyar Nemzeti Bank (MNB)", "cb_zh": "匈牙利央行", "region": "cee", "event_en": "Monetary Council Rate Decision", "event_zh": "货币委员会利率决议", "type": "decision", "tier": 2, "rate": "6.25%", "consensus_en": "Hold 6.25%", "consensus_zh": "维持 6.25%"},
    {"date": "2027-01-26", "code": "NG", "cb_en": "Central Bank of Nigeria (CBN)", "cb_zh": "尼日利亚央行", "region": "frontier", "event_en": "Monetary Policy Committee (MPC) Meeting", "event_zh": "MPC 利率决议", "type": "decision", "tier": 2, "rate": "27.25%", "consensus_en": "Hold 27.25%", "consensus_zh": "维持 27.25%"},
    {"date": "2027-01-28", "code": "US", "cb_en": "Federal Reserve (Fed)", "cb_zh": "美联储", "region": "dm", "event_en": "FOMC Statement & Press Conference", "event_zh": "FOMC 利率决议与新闻发布会", "type": "decision", "tier": 1, "rate": "3.88%", "consensus_en": "Cut 25 bps to 3.63% (60%)", "consensus_zh": "降息 25 个基点至 3.63% (60%概率)"},
    {"date": "2027-01-28", "code": "TR", "cb_en": "Central Bank of Turkey (TCMB)", "cb_zh": "土耳其央行", "region": "em", "event_en": "PPK Rate Decision", "event_zh": "PPK 利率决议", "type": "decision", "tier": 1, "rate": "34.50%", "consensus_en": "Cut 150 bps to 33.00%", "consensus_zh": "降息 150 个基点至 33.00%"},
    {"date": "2027-01-28", "code": "UZ", "cb_en": "Central Bank of Uzbekistan (CBU)", "cb_zh": "乌兹别克斯坦央行", "region": "frontier", "event_en": "Board Monetary Policy Meeting", "event_zh": "理事会利率决议", "type": "decision", "tier": 2, "rate": "13.50%", "consensus_en": "Hold 13.50%", "consensus_zh": "维持 13.50%"},
    {"date": "2027-01-29", "code": "EA", "cb_en": "European Central Bank (ECB)", "cb_zh": "欧洲央行", "region": "dm", "event_en": "Governing Council Monetary Policy Decision", "event_zh": "管理委员会利率决议", "type": "decision", "tier": 1, "rate": "2.25%", "consensus_en": "Hold 2.25%", "consensus_zh": "维持 2.25%"},
    {"date": "2027-01-29", "code": "HK", "cb_en": "Hong Kong Monetary Authority (HKMA)", "cb_zh": "香港金管局", "region": "frontier", "event_en": "Base Rate Adjustment Following US FOMC", "event_zh": "跟随美联储 FOMC 决议即时调整基本利率", "type": "decision", "tier": 2, "rate": "3.75%", "consensus_en": "Follow Fed (Cut 25 bps)", "consensus_zh": "跟随美联储下调 25 个基点"},
    {"date": "2027-02-04", "code": "EG", "cb_en": "Central Bank of Egypt (CBE)", "cb_zh": "埃及央行", "region": "frontier", "event_en": "Monetary Policy Committee (MPC) Meeting", "event_zh": "MPC 利率决议", "type": "decision", "tier": 1, "rate": "23.50%", "consensus_en": "Cut 100 bps to 22.50%", "consensus_zh": "降息 100 个基点至 22.50%"},
    {"date": "2027-02-05", "code": "UK", "cb_en": "Bank of England (BoE)", "cb_zh": "英格兰银行", "region": "dm", "event_en": "MPC Bank Rate Decision & MPR", "event_zh": "MPC 利率决议与货币政策报告 (MPR)", "type": "projection", "tier": 1, "rate": "3.75%", "consensus_en": "Cut 25 bps to 3.50%", "consensus_zh": "降息 25 个基点至 3.50%"},
    {"date": "2027-02-05", "code": "CZ", "cb_en": "Czech National Bank (CNB)", "cb_zh": "捷克央行", "region": "cee", "event_en": "Bank Board Monetary Decision & MPR", "event_zh": "银行理事会利率决议与货币政策报告", "type": "projection", "tier": 1, "rate": "3.50%", "consensus_en": "Hold 3.50%", "consensus_zh": "维持 3.50%"},
    {"date": "2027-02-10", "code": "PL", "cb_en": "Narodowy Bank Polski (NBP)", "cb_zh": "波兰央行", "region": "cee", "event_en": "Monetary Policy Council (RPP) Rate Decision", "event_zh": "RPP 利率决议", "type": "decision", "tier": 2, "rate": "3.75%", "consensus_en": "Hold 3.75%", "consensus_zh": "维持 3.75%"},
    {"date": "2027-02-12", "code": "RO", "cb_en": "National Bank of Romania (BNR)", "cb_zh": "罗马尼亚央行", "region": "cee", "event_en": "Board Monetary Policy Meeting & Inflation Report", "event_zh": "理事会利率决议与通胀报告", "type": "projection", "tier": 1, "rate": "6.50%", "consensus_en": "Hold 6.50%", "consensus_zh": "维持 6.50%"},
    {"date": "2027-02-20", "code": "CN", "cb_en": "People's Bank of China (PBC)", "cb_zh": "中国央行", "region": "em", "event_en": "Monthly Loan Prime Rate (LPR) Fixing", "event_zh": "月度 LPR 报价", "type": "decision", "tier": 2, "rate": "3.10%", "consensus_en": "Cut 10 bps to 3.00%", "consensus_zh": "调降 10 个基点至 3.00%"},
    {"date": "2027-02-23", "code": "HU", "cb_en": "Magyar Nemzeti Bank (MNB)", "cb_zh": "匈牙利央行", "region": "cee", "event_en": "Monetary Council Rate Decision", "event_zh": "货币委员会利率决议", "type": "decision", "tier": 2, "rate": "6.25%", "consensus_en": "Hold 6.25%", "consensus_zh": "维持 6.25%"},
    {"date": "2027-02-25", "code": "KR", "cb_en": "Bank of Korea (BOK)", "cb_zh": "韩国央行", "region": "em", "event_en": "Monetary Policy Board Base Rate Decision", "event_zh": "金融货币委员会基准利率裁决", "type": "decision", "tier": 2, "rate": "3.00%", "consensus_en": "Cut 25 bps to 2.75%", "consensus_zh": "降息 25 个基点至 2.75%"},
    {"date": "2027-02-25", "code": "TR", "cb_en": "Central Bank of Turkey (TCMB)", "cb_zh": "土耳其央行", "region": "em", "event_en": "PPK Rate Decision", "event_zh": "PPK 利率决议", "type": "decision", "tier": 1, "rate": "33.00%", "consensus_en": "Cut 100 bps to 32.00%", "consensus_zh": "降息 100 个基点至 32.00%"},
    {"date": "2027-03-05", "code": "KZ", "cb_en": "National Bank of Kazakhstan (NBK)", "cb_zh": "哈萨克斯坦央行", "region": "frontier", "event_en": "Monetary Policy Base Rate Decision", "event_zh": "货币政策基准利率决议", "type": "decision", "tier": 2, "rate": "14.25%", "consensus_en": "Cut 25 bps to 14.00%", "consensus_zh": "降息 25 个基点至 14.00%"},
    {"date": "2027-03-10", "code": "PL", "cb_en": "Narodowy Bank Polski (NBP)", "cb_zh": "波兰央行", "region": "cee", "event_en": "RPP Rate Decision & Inflation Projection", "event_zh": "RPP 利率决议与宏观通胀预测", "type": "projection", "tier": 1, "rate": "3.75%", "consensus_en": "Cut 25 bps to 3.50%", "consensus_zh": "启动降息 25 个基点至 3.50%"},
    {"date": "2027-03-12", "code": "EA", "cb_en": "European Central Bank (ECB)", "cb_zh": "欧洲央行", "region": "dm", "event_en": "Governing Council Decision & Staff Projections", "event_zh": "管理委员会决议与宏观经济预测", "type": "projection", "tier": 1, "rate": "2.25%", "consensus_en": "Cut 25 bps to 2.00%", "consensus_zh": "降息 25 个基点至 2.00%"},
    {"date": "2027-03-18", "code": "US", "cb_en": "Federal Reserve (Fed)", "cb_zh": "美联储", "region": "dm", "event_en": "FOMC Statement, Press Conf & SEP (Dot Plot)", "event_zh": "FOMC 利率决议、发布会与点阵图更新", "type": "projection", "tier": 1, "rate": "3.63%", "consensus_en": "Cut 25 bps to 3.38%", "consensus_zh": "降息 25 个基点至 3.38%"},
    {"date": "2027-03-18", "code": "TW", "cb_en": "Central Bank of China (Taiwan)", "cb_zh": "中国台湾央行", "region": "em", "event_en": "Q1 Board Meeting & Rate Decision", "event_zh": "第一季理监事联席会议利率决议", "type": "decision", "tier": 2, "rate": "2.00%", "consensus_en": "Hold 2.00%", "consensus_zh": "维持 2.00%"},
    {"date": "2027-03-18", "code": "UZ", "cb_en": "Central Bank of Uzbekistan (CBU)", "cb_zh": "乌兹别克斯坦央行", "region": "frontier", "event_en": "Board Monetary Policy Review Meeting", "event_zh": "理事会利率决议", "type": "decision", "tier": 2, "rate": "13.50%", "consensus_en": "Hold 13.50%", "consensus_zh": "维持 13.50%"},
    {"date": "2027-03-19", "code": "UK", "cb_en": "Bank of England (BoE)", "cb_zh": "英格兰银行", "region": "dm", "event_en": "MPC Bank Rate Decision & Minutes", "event_zh": "MPC 利率决议与会议纪要", "type": "decision", "tier": 1, "rate": "3.50%", "consensus_en": "Hold 3.50%", "consensus_zh": "维持 3.50%"},
    {"date": "2027-03-19", "code": "JP", "cb_en": "Bank of Japan (BoJ)", "cb_zh": "日本银行", "region": "dm", "event_en": "Monetary Policy Meeting (MPM) Decision", "event_zh": "货币政策会议 (MPM) 利率决议", "type": "decision", "tier": 1, "rate": "1.25%", "consensus_en": "Hold 1.25%", "consensus_zh": "维持 1.25%"},
    {"date": "2027-03-19", "code": "HK", "cb_en": "Hong Kong Monetary Authority (HKMA)", "cb_zh": "香港金管局", "region": "frontier", "event_en": "Base Rate Adjustment Following US FOMC", "event_zh": "跟随美联储 FOMC 决议调整基本利率", "type": "decision", "tier": 2, "rate": "3.50%", "consensus_en": "Follow Fed (Cut 25 bps)", "consensus_zh": "跟随美联储下调 25 个基点至 3.25%"},
    {"date": "2027-03-20", "code": "CN", "cb_en": "People's Bank of China (PBC)", "cb_zh": "中国央行", "region": "em", "event_en": "Monthly Loan Prime Rate (LPR) Fixing", "event_zh": "月度 LPR 报价", "type": "decision", "tier": 2, "rate": "3.00%", "consensus_en": "Maintain 3.00%", "consensus_zh": "维持 3.00%"},
    {"date": "2027-03-23", "code": "HU", "cb_en": "Magyar Nemzeti Bank (MNB)", "cb_zh": "匈牙利央行", "region": "cee", "event_en": "Monetary Council Rate Decision & Inflation Report", "event_zh": "货币委员会决议与季度通胀报告", "type": "projection", "tier": 1, "rate": "6.25%", "consensus_en": "Cut 25 bps to 6.00%", "consensus_zh": "下调 25 个基点至 6.00%"},
    {"date": "2027-03-23", "code": "NG", "cb_en": "Central Bank of Nigeria (CBN)", "cb_zh": "尼日利亚央行", "region": "frontier", "event_en": "Monetary Policy Committee (MPC) Meeting", "event_zh": "MPC 利率决议", "type": "decision", "tier": 2, "rate": "27.25%", "consensus_en": "Hold 27.25%", "consensus_zh": "维持 27.25%"},
    {"date": "2027-03-25", "code": "CZ", "cb_en": "Czech National Bank (CNB)", "cb_zh": "捷克央行", "region": "cee", "event_en": "Bank Board Monetary Policy Decision", "event_zh": "银行理事会利率决议", "type": "decision", "tier": 2, "rate": "3.50%", "consensus_en": "Hold 3.50%", "consensus_zh": "维持 3.50%"},
    {"date": "2027-03-25", "code": "SARB", "cb_en": "South African Reserve Bank (SARB)", "cb_zh": "南非央行", "region": "em", "event_en": "MPC Repo Rate Decision & Statement", "event_zh": "MPC 回购利率决议与声明", "type": "decision", "tier": 2, "rate": "6.75%", "consensus_en": "Hold 6.75%", "consensus_zh": "维持 6.75%"},
    {"date": "2027-03-25", "code": "TR", "cb_en": "Central Bank of Turkey (TCMB)", "cb_zh": "土耳其央行", "region": "em", "event_en": "PPK Rate Decision & Q1 Review", "event_zh": "PPK 利率决议与首季评估", "type": "decision", "tier": 1, "rate": "32.00%", "consensus_en": "Cut 100 bps to 31.00%", "consensus_zh": "降息 100 个基点至 31.00%"},
    {"date": "2027-03-25", "code": "EG", "cb_en": "Central Bank of Egypt (CBE)", "cb_zh": "埃及央行", "region": "frontier", "event_en": "Monetary Policy Committee (MPC) Meeting", "event_zh": "MPC 利率决议", "type": "decision", "tier": 1, "rate": "22.50%", "consensus_en": "Cut 100 bps to 21.50%", "consensus_zh": "降息 100 个基点至 21.50%"},

    # Q2 2027 Key Global Anchors
    {"date": "2027-04-09", "code": "RO", "cb_en": "National Bank of Romania (BNR)", "cb_zh": "罗马尼亚央行", "region": "cee", "event_en": "Board Monetary Policy Meeting", "event_zh": "理事会利率决议", "type": "decision", "tier": 2, "rate": "6.50%", "consensus_en": "Cut 25 bps to 6.25%", "consensus_zh": "降息 25 个基点至 6.25%"},
    {"date": "2027-04-15", "code": "KR", "cb_en": "Bank of Korea (BOK)", "cb_zh": "韩国央行", "region": "em", "event_en": "Monetary Policy Board Base Rate Decision", "event_zh": "金融货币委员会基准利率裁决", "type": "decision", "tier": 2, "rate": "2.75%", "consensus_en": "Hold 2.75%", "consensus_zh": "维持 2.75%"},
    {"date": "2027-04-24", "code": "JP", "cb_en": "Bank of Japan (BoJ)", "cb_zh": "日本银行", "region": "dm", "event_en": "MPM Decision & Outlook Report", "event_zh": "MPM 决议与经济物价展望报告", "type": "projection", "tier": 1, "rate": "1.25%", "consensus_en": "Hike 25 bps to 1.50%", "consensus_zh": "加息 25 个基点至 1.50%"},
    {"date": "2027-04-30", "code": "EA", "cb_en": "European Central Bank (ECB)", "cb_zh": "欧洲央行", "region": "dm", "event_en": "Governing Council Monetary Policy Decision", "event_zh": "管理委员会利率决议", "type": "decision", "tier": 1, "rate": "2.00%", "consensus_en": "Hold 2.00%", "consensus_zh": "维持 2.00%"},
    {"date": "2027-05-06", "code": "US", "cb_en": "Federal Reserve (Fed)", "cb_zh": "美联储", "region": "dm", "event_en": "FOMC Statement & Press Conference", "event_zh": "FOMC 利率决议与新闻发布会", "type": "decision", "tier": 1, "rate": "3.38%", "consensus_en": "Hold 3.38%", "consensus_zh": "维持 3.38%"},
    {"date": "2027-05-07", "code": "UK", "cb_en": "Bank of England (BoE)", "cb_zh": "英格兰银行", "region": "dm", "event_en": "MPC Bank Rate Decision & MPR", "event_zh": "MPC 利率决议与货币政策报告 (MPR)", "type": "projection", "tier": 1, "rate": "3.50%", "consensus_en": "Cut 25 bps to 3.25%", "consensus_zh": "降息 25 个基点至 3.25%"},
    {"date": "2027-05-20", "code": "ZA", "cb_en": "South African Reserve Bank (SARB)", "cb_zh": "南非央行", "region": "em", "event_en": "MPC Repo Rate Decision & Statement", "event_zh": "MPC 回购利率决议与声明", "type": "decision", "tier": 2, "rate": "6.75%", "consensus_en": "Cut 25 bps to 6.50%", "consensus_zh": "降息 25 个基点至 6.50%"},
    {"date": "2027-06-11", "code": "EA", "cb_en": "European Central Bank (ECB)", "cb_zh": "欧洲央行", "region": "dm", "event_en": "Governing Council Decision & Staff Projections", "event_zh": "管理委员会决议与宏观经济预测", "type": "projection", "tier": 1, "rate": "2.00%", "consensus_en": "Hold 2.00%", "consensus_zh": "维持 2.00%"},
    {"date": "2027-06-17", "code": "US", "cb_en": "Federal Reserve (Fed)", "cb_zh": "美联储", "region": "dm", "event_en": "FOMC Statement, Press Conf & SEP (Dot Plot)", "event_zh": "FOMC 利率决议、发布会与点阵图更新", "type": "projection", "tier": 1, "rate": "3.38%", "consensus_en": "Cut 25 bps to 3.13%", "consensus_zh": "降息 25 个基点至 3.13%"},
    {"date": "2027-06-17", "code": "TW", "cb_en": "Central Bank of China (Taiwan)", "cb_zh": "中国台湾央行", "region": "em", "event_en": "Q2 Board Meeting & Rate Decision", "event_zh": "第二季理监事联席会议利率决议", "type": "decision", "tier": 2, "rate": "2.00%", "consensus_en": "Hold 2.00%", "consensus_zh": "维持 2.00%"},
    {"date": "2027-06-18", "code": "UK", "cb_en": "Bank of England (BoE)", "cb_zh": "英格兰银行", "region": "dm", "event_en": "MPC Bank Rate Decision & Minutes", "event_zh": "MPC 利率决议与会议纪要", "type": "decision", "tier": 1, "rate": "3.25%", "consensus_en": "Hold 3.25%", "consensus_zh": "维持 3.25%"},
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


def load_historical_policy_cycles() -> dict:
    """Extract monthly historical nominal & real policy rate trajectories for the 18 economies."""
    frame_map = {
        "US": ("us_canonical_frame.json", "effective_fed_funds", "real_policy_rate"),
        "EA": ("euro_area_canonical_frame.json", "policy_rate", "real_policy_rate"),
        "UK": ("uk_canonical_frame.json", "bank_rate", "real_policy_rate"),
        "JP": ("japan_canonical_frame.json", "policy_rate", "real_policy_rate"),
        "CN": ("china_canonical_frame.json", "lpr_1y_akshare", "real_policy_rate"),
        "TR": ("turkey_canonical_frame.json", "policy_rate", "real_policy_rate"),
        "ZA": ("south_africa_canonical_frame.json", "policy_rate", "real_policy_rate"),
        "KR": ("south_korea_canonical_frame.json", "policy_rate", "real_policy_rate"),
        "TW": ("taiwan_canonical_frame.json", "policy_rate", "real_policy_rate"),
        "HK": ("hong_kong_canonical_frame.json", "fed_funds_anchor", "real_policy_rate"),
        "KZ": ("kazakhstan_canonical_frame.json", "policy_rate", "real_policy_rate"),
        "UZ": ("uzbekistan_canonical_frame.json", "policy_rate", "real_policy_rate"),
        "EG": ("egypt_canonical_frame.json", "policy_rate", "real_policy_rate"),
        "NG": ("nigeria_canonical_frame.json", "policy_rate", "real_policy_rate"),
        "HU": ("cee_canonical_frame.json", "policy_rate", "real_policy_rate"),
        "PL": ("cee_canonical_frame.json", "policy_rate", "real_policy_rate"),
        "CZ": ("cee_canonical_frame.json", "policy_rate", "real_policy_rate"),
        "RO": ("cee_canonical_frame.json", "policy_rate", "real_policy_rate"),
    }
    frame_cache: dict = {}
    out: dict = {}

    def _norm_month(raw_dt: str) -> str:
        s = str(raw_dt).strip()
        if len(s) == 4 and s.isdigit():
            return f"{s}-12-01"
        if "-Q" in s:
            yr, q = s.split("-Q")
            mo = int(q) * 3
            return f"{yr}-{mo:02d}-01"
        if len(s) >= 7 and s[4] == "-":
            return f"{s[:7]}-01"
        return s[:10]

    for code, (fn, nom_id, real_id) in frame_map.items():
        fpath = OUTPUT / fn
        if fn not in frame_cache and fpath.exists():
            try:
                frame_cache[fn] = json.loads(fpath.read_text(encoding="utf-8"))
            except Exception:
                frame_cache[fn] = {}
        frame = frame_cache.get(fn, {})
        series_list = frame.get("series", [])

        def _extract(ind_id: str) -> list:
            for s in series_list:
                if fn == "cee_canonical_frame.json" and s.get("country") != code:
                    continue
                if (s.get("indicator_id") or s.get("id")) == ind_id:
                    by_mo: dict = {}
                    for o in s.get("observations", []):
                        dt_raw = o[0] if isinstance(o, list) else o.get("date")
                        val_raw = o[1] if isinstance(o, list) else o.get("value")
                        if dt_raw is None or val_raw is None:
                            continue
                        try:
                            v = round(float(val_raw), 3)
                        except (ValueError, TypeError):
                            continue
                        mo = _norm_month(str(dt_raw))
                        if mo >= "2000-01-01":
                            by_mo[mo] = v
                    return [{"time": k, "value": by_mo[k]} for k in sorted(by_mo.keys())]
            return []

        out[code] = {
            "nominal": _extract(nom_id),
            "real": _extract(real_id),
        }
    return out


def build_policy_tracker_html() -> str:
    """Generate the complete standalone Policy Tracker HTML application."""
    wb = load_macro_workbench_summary()
    stances = wb.get("monetary_stance_monitor", {})
    ref_date = date(2026, 11, 2)

    country_nav_links = "\n    ".join(
        f'<a href="{href}" title="{name_en} ({name_zh})">{code}</a>'
        for code, name_en, name_zh, href in COUNTRY_NAV
    )

    # Compile enriched master table data for all 18 economies
    table_rows_data = []
    real_rate_chart_data = []
    taylor_chart_data = []

    for code, name_en, name_zh, href in COUNTRY_NAV:
        meta = ECONOMY_METADATA.get(code, {})
        stance = stances.get(code, {})

        policy_rate = stance.get("policy_rate", 0.0)
        cpi = stance.get("inflation_rate", 0.0)
        real_rate = stance.get("real_policy_rate", round(policy_rate - cpi, 2))
        target = stance.get("inflation_target", 2.0)
        target_gap = round(cpi - target, 2)
        taylor_rate = stance.get("taylor_implied_rate", policy_rate)
        policy_gap = stance.get("policy_gap_deviation", round(policy_rate - taylor_rate, 2))

        # Classify real rate badge
        if real_rate >= 5.0:
            rr_class = "rr-deep-restr"
            rr_tag_en = "Deep Restrictive"
            rr_tag_zh = "深度限制性"
        elif real_rate >= 2.0:
            rr_class = "rr-restr"
            rr_tag_en = "Restrictive"
            rr_tag_zh = "限制性适度"
        elif real_rate >= 0.0:
            rr_class = "rr-neutral"
            rr_tag_en = "Calibrated / Neutral"
            rr_tag_zh = "中性微正"
        else:
            rr_class = "rr-accomm"
            rr_tag_en = "Negative / Accommodative"
            rr_tag_zh = "负利率宽松"

        # Days to next meeting
        next_dt_str = meta.get("next_meeting_date", "2026-12-18")
        try:
            next_dt = datetime.strptime(next_dt_str, "%Y-%m-%d").date()
            days_diff = (next_dt - ref_date).days
            days_label = f"in {days_diff}d" if days_diff > 0 else f"{days_diff}d ago"
            days_label_zh = f"{days_diff}天后" if days_diff > 0 else f"{abs(days_diff)}天前"
        except Exception:
            days_label = next_dt_str
            days_label_zh = next_dt_str

        rate_change_12m = meta.get("rate_change_12m", 0)
        chg_sign = "+" if rate_change_12m > 0 else ""
        chg_class = "pos-delta" if rate_change_12m > 0 else ("neg-delta" if rate_change_12m < 0 else "zero-delta")

        row_item = {
            "code": code,
            "flag": meta.get("flag", ""),
            "name_en": name_en,
            "name_zh": name_zh,
            "region": meta.get("region", "dm"),
            "region_en": meta.get("region_en", ""),
            "region_zh": meta.get("region_zh", ""),
            "cb_name_en": meta.get("cb_name_en", ""),
            "cb_name_zh": meta.get("cb_name_zh", ""),
            "cb_short": meta.get("cb_short", code),
            "tool_en": meta.get("policy_tool_en", ""),
            "tool_zh": meta.get("policy_tool_zh", ""),
            "policy_rate": policy_rate,
            "cpi": cpi,
            "real_rate": real_rate,
            "target": target,
            "target_gap": target_gap,
            "taylor_rate": taylor_rate,
            "policy_gap": policy_gap,
            "rate_change_12m": rate_change_12m,
            "chg_display": f"{chg_sign}{rate_change_12m} bps",
            "chg_class": chg_class,
            "rr_class": rr_class,
            "rr_tag_en": rr_tag_en,
            "rr_tag_zh": rr_tag_zh,
            "cycle_phase_en": meta.get("cycle_phase_en", "Neutral"),
            "cycle_phase_zh": meta.get("cycle_phase_zh", "中性"),
            "cycle_badge": meta.get("cycle_badge", "neutral"),
            "next_date": next_dt_str,
            "days_label": days_label,
            "days_label_zh": days_label_zh,
            "next_meeting_en": meta.get("next_meeting_name_en", ""),
            "next_meeting_zh": meta.get("next_meeting_name_zh", ""),
            "consensus_en": meta.get("consensus_action_en", ""),
            "consensus_zh": meta.get("consensus_action_zh", ""),
            "href": href,
        }
        table_rows_data.append(row_item)

        real_rate_chart_data.append({
            "code": code,
            "flag": meta.get("flag", ""),
            "name_en": name_en,
            "name_zh": name_zh,
            "policy_rate": policy_rate,
            "cpi": cpi,
            "real_rate": real_rate,
        })

        taylor_chart_data.append({
            "code": code,
            "flag": meta.get("flag", ""),
            "name_en": name_en,
            "name_zh": name_zh,
            "actual_rate": policy_rate,
            "taylor_rate": taylor_rate,
            "policy_gap": policy_gap,
            "stance_label": stance.get("stance_label", "neutral"),
        })

    # Sort real rate data descending for horizontal chart
    real_rate_chart_data.sort(key=lambda x: x["real_rate"], reverse=True)

    # Corridor Cards (9 core anchor institutions)
    corridor_cards_html = []
    nav_href_map = {item[0]: item[3] for item in COUNTRY_NAV}
    for code in ["US", "EA", "UK", "JP", "CN", "TR", "ZA", "KR", "HU"]:
        meta = ECONOMY_METADATA[code]
        card_href = nav_href_map.get(code, "index.html")
        stance = stances.get(code, {})
        policy_rate = stance.get("policy_rate", 0.0)
        cpi = stance.get("inflation_rate", 0.0)
        real_rate = stance.get("real_policy_rate", round(policy_rate - cpi, 2))
        taylor_rate = stance.get("taylor_implied_rate", policy_rate)
        ceil_rate = meta.get("corridor_ceiling_rate", policy_rate + 0.5)
        floor_rate = meta.get("corridor_floor_rate", policy_rate - 0.5)

        # Scale bar percentage: min floor - 0.5, max ceil + 0.5
        min_scale = max(0.0, floor_rate - 0.75)
        max_scale = max(ceil_rate + 0.75, min_scale + 2.0)
        span = max_scale - min_scale

        def calc_pct(val: float) -> float:
            return round(max(2.0, min(98.0, ((val - min_scale) / span) * 100)), 1)

        pct_floor = calc_pct(floor_rate)
        pct_policy = calc_pct(policy_rate)
        pct_ceil = calc_pct(ceil_rate)

        card_html = f"""
        <div class="corridor-card" data-region="{meta['region']}">
          <div class="card-top">
            <div class="card-id">
              <span class="card-flag">{meta['flag']}</span>
              <div>
                <div class="card-title">{meta['cb_name_en']}</div>
                <div class="card-sub zh-only">{meta['cb_name_zh']} · {meta['name_zh']}</div>
                <div class="card-sub en-only">{meta['name_en']} · {meta['cb_short']}</div>
              </div>
            </div>
            <span class="cycle-pill {meta['cycle_badge']}">
              <span class="en-only">{meta['cycle_phase_en']}</span>
              <span class="zh-only">{meta['cycle_phase_zh']}</span>
            </span>
          </div>

          <!-- Key Rates Grid -->
          <div class="corridor-metric-grid">
            <div class="metric-item">
              <span class="metric-label en-only">Policy Benchmark</span>
              <span class="metric-label zh-only">政策基准利率</span>
              <span class="metric-val primary-val">{policy_rate:.2f}%</span>
              <span class="metric-sub en-only">{meta['policy_tool_en']}</span>
              <span class="metric-sub zh-only">{meta['policy_tool_zh']}</span>
            </div>
            <div class="metric-item">
              <span class="metric-label en-only">Headline CPI</span>
              <span class="metric-label zh-only">最新CPI通胀</span>
              <span class="metric-val">{cpi:.2f}%</span>
              <span class="metric-sub en-only">Target: {stance.get('inflation_target', 2.0):.1f}%</span>
              <span class="metric-sub zh-only">目标: {stance.get('inflation_target', 2.0):.1f}%</span>
            </div>
            <div class="metric-item">
              <span class="metric-label en-only">Real Policy Rate</span>
              <span class="metric-label zh-only">实际政策利率</span>
              <span class="metric-val {'pos' if real_rate >= 0 else 'neg'}">{real_rate:+.2f}%</span>
              <span class="metric-sub en-only">{"+" if real_rate >= 0 else ""}Carry Yield</span>
              <span class="metric-sub zh-only">真实收益利差</span>
            </div>
            <div class="metric-item">
              <span class="metric-label en-only">Taylor Implied</span>
              <span class="metric-label zh-only">泰勒中性推算</span>
              <span class="metric-val">{taylor_rate:.2f}%</span>
              <span class="metric-sub en-only">Gap: {policy_rate - taylor_rate:+.2f}%</span>
              <span class="metric-sub zh-only">偏离: {policy_rate - taylor_rate:+.2f}%</span>
            </div>
          </div>

          <!-- Operational Corridor Visualizer -->
          <div class="corridor-visualizer-box">
            <div class="corridor-track-labels">
              <span class="node-label floor">Floor: {meta['corridor_floor_name'][:20]} ({floor_rate:.2f}%)</span>
              <span class="node-label center">Policy Target: {policy_rate:.2f}%</span>
              <span class="node-label ceil">Ceiling: {meta['corridor_ceiling_name'][:20]} ({ceil_rate:.2f}%)</span>
            </div>
            <div class="corridor-bar-track">
              <div class="corridor-fill" style="left: {pct_floor}%; width: {max(2.0, pct_ceil - pct_floor)}%;"></div>
              <div class="corridor-marker floor" style="left: {pct_floor}%;" title="{meta['corridor_floor_name']}: {floor_rate:.2f}%"></div>
              <div class="corridor-marker center" style="left: {pct_policy}%;" title="Policy Target: {policy_rate:.2f}%"></div>
              <div class="corridor-marker ceil" style="left: {pct_ceil}%;" title="{meta['corridor_ceiling_name']}: {ceil_rate:.2f}%"></div>
            </div>
          </div>

          <!-- Secondary Liquidity & Balance Sheet Line -->
          <div class="card-context-line">
            <div class="context-item">
              <span class="ctx-title en-only">Balance Sheet:</span>
              <span class="ctx-title zh-only">资产负债表:</span>
              <span class="ctx-val en-only">{meta['balance_sheet_display_en']}</span>
              <span class="ctx-val zh-only">{meta['balance_sheet_display_zh']}</span>
            </div>
            <div class="context-item">
              <span class="ctx-title en-only">Secondary Stance:</span>
              <span class="ctx-title zh-only">配套机制:</span>
              <span class="ctx-val en-only">{meta['secondary_tool_en']}</span>
              <span class="ctx-val zh-only">{meta['secondary_tool_zh']}</span>
            </div>
          </div>

          <!-- Meeting & Consensus Banner -->
          <div class="card-decision-banner">
            <div class="next-decision-label">
              <span class="en-only">Next Decision:</span><span class="zh-only">下次议息:</span>
              <strong>{meta['next_meeting_date']}</strong>
            </div>
            <div class="consensus-badge">
              <span class="en-only">Consensus: {meta['consensus_action_en']}</span>
              <span class="zh-only">市场共识: {meta['consensus_action_zh']}</span>
            </div>
            <a href="{card_href}" class="card-deep-link" title="Open {meta['name_en']} Dashboard">
              <span class="en-only">View {code} →</span><span class="zh-only">深入研报 →</span>
            </a>
          </div>
        </div>
        """
        corridor_cards_html.append(card_html)

    all_corridor_cards = "\n".join(corridor_cards_html)

    # Master Table HTML generation
    table_rows_html = []
    for r in table_rows_data:
        row_html = f"""
        <tr class="table-row" data-region="{r['region']}" data-search="{r['code']} {r['name_en']} {r['name_zh']} {r['cb_short']} {r['cb_name_en']} {r['cb_name_zh']}">
          <td class="col-entity">
            <a href="{r['href']}" class="entity-link" title="View {r['name_en']} macro dashboard">
              <span class="entity-flag">{r['flag']}</span>
              <div class="entity-names">
                <span class="entity-code">{r['code']}</span>
                <span class="entity-title en-only">{r['name_en']}</span>
                <span class="entity-title zh-only">{r['name_zh']}</span>
                <span class="entity-cb en-only">{r['cb_short']}</span>
                <span class="entity-cb zh-only">{r['cb_name_zh'][:14]}</span>
              </div>
            </a>
          </td>
          <td class="col-tool">
            <div class="tool-name en-only">{r['tool_en']}</div>
            <div class="tool-name zh-only">{r['tool_zh']}</div>
          </td>
          <td class="col-num col-policy" data-sort="{r['policy_rate']}">
            <strong>{r['policy_rate']:.2f}%</strong>
          </td>
          <td class="col-num col-cpi" data-sort="{r['cpi']}">
            <span>{r['cpi']:.2f}%</span>
          </td>
          <td class="col-num col-real" data-sort="{r['real_rate']}">
            <span class="rr-pill {r['rr_class']}">
              <strong>{r['real_rate']:+.2f}%</strong>
            </span>
          </td>
          <td class="col-num col-gap" data-sort="{r['target_gap']}">
            <span class="gap-display {'gap-pos' if r['target_gap'] > 0 else 'gap-neg'}">
              {r['target_gap']:+.2f}%
            </span>
            <span class="target-sub en-only">(Target {r['target']:.1f}%)</span>
            <span class="target-sub zh-only">(目标 {r['target']:.1f}%)</span>
          </td>
          <td class="col-cycle">
            <span class="cycle-pill {r['cycle_badge']}">
              <span class="en-only">{r['cycle_phase_en']}</span>
              <span class="zh-only">{r['cycle_phase_zh']}</span>
            </span>
          </td>
          <td class="col-num col-delta" data-sort="{r['rate_change_12m']}">
            <span class="{r['chg_class']}">{r['chg_display']}</span>
          </td>
          <td class="col-next" data-sort="{r['next_date']}">
            <div class="next-date-box">
              <span class="next-date-text">{r['next_date']}</span>
              <span class="days-badge">{r['days_label']}</span>
            </div>
          </td>
          <td class="col-consensus">
            <span class="consensus-tag en-only">{r['consensus_en']}</span>
            <span class="consensus-tag zh-only">{r['consensus_zh']}</span>
          </td>
          <td class="col-action">
            <a href="{r['href']}" class="table-action-btn">
              <span class="en-only">Open →</span><span class="zh-only">看板 →</span>
            </a>
          </td>
        </tr>
        """
        table_rows_html.append(row_html)

    all_table_rows = "\n".join(table_rows_html)

    # Calendar Rows HTML generation
    calendar_rows_html = []
    for ev in CALENDAR_EVENTS:
        ev_date = ev["date"]
        try:
            dt = datetime.strptime(ev_date, "%Y-%m-%d").date()
            diff = (dt - ref_date).days
            days_str_en = f"in {diff} days" if diff > 0 else (f"{abs(diff)} days ago" if diff < 0 else "Today")
            days_str_zh = f"{diff}天后" if diff > 0 else (f"{abs(diff)}天前" if diff < 0 else "今日")
        except Exception:
            days_str_en = ev_date
            days_str_zh = ev_date

        tier_class = "tier-1-badge" if ev["tier"] == 1 else "tier-2-badge"
        tier_label_en = "Tier-1 Critical" if ev["tier"] == 1 else "Tier-2 Standard"
        tier_label_zh = "一级关键(点阵/预测)" if ev["tier"] == 1 else "二级常规决议"

        flag = ECONOMY_METADATA.get(ev["code"], {}).get("flag", "🏛️")

        cal_row = f"""
        <tr class="cal-row" data-region="{ev['region']}" data-type="{ev['type']}" data-search="{ev['code']} {ev['cb_en']} {ev['cb_zh']} {ev['event_en']} {ev['event_zh']}">
          <td class="cal-date-col">
            <div class="cal-date-main">{ev_date}</div>
            <div class="cal-days-sub en-only">{days_str_en}</div>
            <div class="cal-days-sub zh-only">{days_str_zh}</div>
          </td>
          <td class="cal-cb-col">
            <div class="cal-cb-info">
              <span class="cal-flag">{flag}</span>
              <div>
                <strong class="en-only">{ev['cb_en']}</strong>
                <strong class="zh-only">{ev['cb_zh']} ({ev['code']})</strong>
                <div class="cal-event-desc en-only">{ev['event_en']}</div>
                <div class="cal-event-desc zh-only">{ev['event_zh']}</div>
              </div>
            </div>
          </td>
          <td class="cal-tier-col">
            <span class="cal-badge {tier_class}">
              <span class="en-only">{tier_label_en}</span>
              <span class="zh-only">{tier_label_zh}</span>
            </span>
          </td>
          <td class="cal-rate-col">
            <span class="rate-current">{ev['rate']}</span>
          </td>
          <td class="cal-consensus-col">
            <span class="cal-consensus-text en-only">{ev['consensus_en']}</span>
            <span class="cal-consensus-text zh-only">{ev['consensus_zh']}</span>
          </td>
          <td class="cal-action-col">
            <a href="{nav_href_map.get(ev['code'], 'index.html')}" class="cal-link">
              <span class="en-only">Profile →</span><span class="zh-only">主页 →</span>
            </a>
          </td>
        </tr>
        """
        calendar_rows_html.append(cal_row)

    all_calendar_rows = "\n".join(calendar_rows_html)

    # JSON payloads for Lightweight Charts & FT Studio Canvas charts
    real_rate_json = json.dumps(real_rate_chart_data, ensure_ascii=False)
    taylor_json = json.dumps(taylor_chart_data, ensure_ascii=False)
    historical_cycles_json = json.dumps(load_historical_policy_cycles(), ensure_ascii=False)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Central Bank Policy & Monetary Cycle Tracker · 全球央行与货币政策周期追踪器</title>
  <link rel="icon" href="data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 100 100%22><text y=%22.9em%22 font-size=%2290%22>🏛️</text></svg>">
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
      --radius-sm: 4px;
      --radius-md: 6px;
      --radius-lg: 8px;
      --shadow-sm: 0 1px 2px rgba(0,0,0,0.04);
      --shadow-md: 0 2px 6px rgba(0,0,0,0.06);
    }}

    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      background-color: var(--bg);
      color: var(--fg);
      font-family: var(--font-main);
      line-height: 1.45;
      -webkit-font-smoothing: antialiased;
    }}

    /* Topbar */
    .topbar {{
      background: #1a1e24;
      color: #e0e4eb;
      padding: 9px 18px;
      font-size: 12px;
      display: flex;
      justify-content: space-between;
      align-items: center;
      position: sticky;
      top: 0;
      z-index: 100;
      border-bottom: 1px solid rgba(255,255,255,0.08);
    }}
    .topbar a {{ color: inherit; text-decoration: none; }}
    .brand {{ font-weight: 700; letter-spacing: 0.04em; display: flex; align-items: center; gap: 8px; }}
    .brand span {{ color: #9da8b6; font-weight: 400; }}
    .topbar-nav {{ display: flex; align-items: center; gap: 14px; overflow-x: auto; padding: 2px 0; }}
    .country-nav {{ display: flex; gap: 4px; align-items: center; }}
    .country-nav a {{
      padding: 2px 6px;
      border-radius: var(--radius-sm);
      color: #b8c2cc;
      font-size: 11px;
      font-family: var(--font-mono);
      transition: all 0.15s ease;
    }}
    .country-nav a:hover {{ background: rgba(255,255,255,0.12); color: #ffffff; }}
    .topbar-actions {{ display: flex; gap: 8px; align-items: center; flex-shrink: 0; }}
    .topbar-btn {{
      padding: 4px 10px;
      border-radius: var(--radius-sm);
      font-size: 11px;
      font-weight: 600;
      cursor: pointer;
      text-decoration: none;
      display: inline-flex;
      align-items: center;
      gap: 4px;
      border: 1px solid rgba(255,255,255,0.15);
      background: rgba(255,255,255,0.06);
      color: #e0e4eb;
      transition: all 0.15s;
    }}
    .topbar-btn:hover {{ background: rgba(255,255,255,0.14); color: #fff; }}
    .topbar-btn.active {{ background: var(--accent); border-color: var(--accent); color: #fff; }}

    /* Layout Container */
    .container {{
      max-width: 1440px;
      margin: 0 auto;
      padding: 24px 20px 48px;
    }}

    /* Header Header */
    .page-header {{
      margin-bottom: 24px;
      border-bottom: 1px solid var(--border);
      padding-bottom: 20px;
      display: flex;
      justify-content: space-between;
      align-items: flex-end;
      flex-wrap: wrap;
      gap: 16px;
    }}
    .header-main h1 {{
      font-family: var(--font-serif);
      font-size: 28px;
      font-weight: 700;
      color: var(--fg);
      letter-spacing: -0.01em;
      margin-bottom: 6px;
      display: flex;
      align-items: center;
      gap: 10px;
    }}
    .header-subtitle {{
      color: var(--text-secondary);
      font-size: 13.5px;
      max-width: 820px;
    }}
    .header-badges {{
      display: flex;
      gap: 8px;
      align-items: center;
      flex-wrap: wrap;
    }}
    .stat-badge {{
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: var(--radius-sm);
      padding: 6px 12px;
      font-size: 12px;
      display: flex;
      flex-direction: column;
      box-shadow: var(--shadow-sm);
    }}
    .stat-badge-num {{
      font-weight: 700;
      font-family: var(--font-mono);
      color: var(--accent);
      font-size: 15px;
    }}
    .stat-badge-desc {{
      color: var(--text-secondary);
      font-size: 10.5px;
    }}

    /* Tab Navigation */
    .tab-bar {{
      display: flex;
      gap: 8px;
      border-bottom: 2px solid var(--border);
      margin-bottom: 24px;
      overflow-x: auto;
      padding-bottom: 0;
    }}
    .tab-btn {{
      padding: 10px 18px;
      border: none;
      background: transparent;
      color: var(--text-secondary);
      font-size: 13.5px;
      font-weight: 600;
      cursor: pointer;
      border-bottom: 3px solid transparent;
      margin-bottom: -2px;
      transition: all 0.2s;
      white-space: nowrap;
      display: inline-flex;
      align-items: center;
      gap: 6px;
    }}
    .tab-btn:hover {{ color: var(--fg); }}
    .tab-btn.active {{
      color: var(--accent);
      border-bottom-color: var(--accent);
    }}

    /* Filter Controls Bar */
    .filter-bar {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      flex-wrap: wrap;
      gap: 12px;
      margin-bottom: 18px;
      background: var(--surface);
      padding: 12px 16px;
      border: 1px solid var(--border);
      border-radius: var(--radius-md);
      box-shadow: var(--shadow-sm);
    }}
    .filter-chips {{
      display: flex;
      gap: 6px;
      align-items: center;
      flex-wrap: wrap;
    }}
    .filter-chip {{
      padding: 5px 12px;
      font-size: 12px;
      font-weight: 500;
      border: 1px solid var(--border);
      background: var(--bg);
      color: var(--text-secondary);
      border-radius: 20px;
      cursor: pointer;
      transition: all 0.15s;
    }}
    .filter-chip:hover {{ color: var(--fg); border-color: var(--text-secondary); }}
    .filter-chip.active {{
      background: var(--slate);
      color: #ffffff;
      border-color: var(--slate);
      font-weight: 600;
    }}
    .search-box {{
      position: relative;
      display: flex;
      align-items: center;
    }}
    .search-input {{
      padding: 6px 12px 6px 28px;
      font-size: 12px;
      border: 1px solid var(--border);
      border-radius: var(--radius-sm);
      width: 220px;
      background: #ffffff;
      color: var(--fg);
    }}
    .search-input:focus {{
      outline: none;
      border-color: var(--accent);
    }}
    .search-icon {{
      position: absolute;
      left: 8px;
      font-size: 12px;
      color: var(--text-secondary);
    }}

    /* Tab Panes */
    .tab-pane {{ display: none; }}
    .tab-pane.active {{ display: block; }}

    /* ==============================================================================
       TAB 1: Master Policy Matrix Table
       ============================================================================== */
    .table-responsive {{
      overflow-x: auto;
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: var(--radius-md);
      box-shadow: var(--shadow-sm);
    }}
    .matrix-table {{
      width: 100%;
      border-collapse: collapse;
      font-size: 13px;
      text-align: left;
    }}
    .matrix-table th {{
      background: #fbf9f6;
      padding: 10px 14px;
      border-bottom: 1px solid var(--border);
      color: var(--text-secondary);
      font-weight: 600;
      font-size: 11.5px;
      letter-spacing: 0.03em;
      text-transform: uppercase;
      white-space: nowrap;
      cursor: pointer;
      user-select: none;
    }}
    .matrix-table th:hover {{ color: var(--fg); background: #f3efe9; }}
    .matrix-table th.sorted-asc::after {{ content: " ▲"; font-size: 9px; }}
    .matrix-table th.sorted-desc::after {{ content: " ▼"; font-size: 9px; }}
    .matrix-table td {{
      padding: 10px 14px;
      border-bottom: 1px solid var(--border-subtle);
      vertical-align: middle;
    }}
    .matrix-table tr:hover {{ background: #faf8f5; }}
    .col-entity {{ min-width: 170px; }}
    .entity-link {{
      display: flex;
      align-items: center;
      gap: 10px;
      text-decoration: none;
      color: var(--fg);
    }}
    .entity-flag {{ font-size: 20px; }}
    .entity-names {{ display: flex; flex-direction: column; }}
    .entity-code {{ font-weight: 700; font-family: var(--font-mono); font-size: 12px; color: var(--accent); }}
    .entity-title {{ font-weight: 600; font-size: 13px; }}
    .entity-cb {{ font-size: 11px; color: var(--text-secondary); }}
    .col-tool {{ max-width: 180px; font-size: 11.5px; color: var(--text-secondary); }}
    .col-num {{ font-family: var(--font-mono); text-align: right; }}
    .matrix-table th.col-num {{ text-align: right; }}

    /* Badges */
    .rr-pill {{
      display: inline-block;
      padding: 3px 8px;
      border-radius: var(--radius-sm);
      font-size: 12px;
      font-weight: 700;
    }}
    .rr-deep-restr {{ background: rgba(13, 118, 128, 0.18); color: #085259; border: 1px solid rgba(13, 118, 128, 0.3); }}
    .rr-restr {{ background: rgba(13, 118, 128, 0.10); color: #0d7680; }}
    .rr-neutral {{ background: rgba(115, 124, 140, 0.12); color: #364b61; }}
    .rr-accomm {{ background: rgba(153, 15, 61, 0.12); color: #990f3d; }}

    .gap-display {{ font-weight: 600; }}
    .gap-pos {{ color: var(--bad); }}
    .gap-neg {{ color: var(--good); }}
    .target-sub {{ display: block; font-size: 10.5px; color: var(--text-secondary); }}

    .cycle-pill {{
      display: inline-block;
      padding: 3px 9px;
      border-radius: 12px;
      font-size: 11px;
      font-weight: 600;
      white-space: nowrap;
    }}
    .cycle-pill.easing {{ background: rgba(13, 118, 128, 0.12); color: #0d7680; }}
    .cycle-pill.plateau {{ background: rgba(217, 119, 6, 0.12); color: #b45309; }}
    .cycle-pill.hiking {{ background: rgba(153, 15, 61, 0.12); color: #990f3d; }}
    .cycle-pill.neutral {{ background: rgba(54, 75, 97, 0.12); color: #364b61; }}

    .pos-delta {{ color: var(--bad); font-weight: 600; }}
    .neg-delta {{ color: var(--good); font-weight: 600; }}
    .zero-delta {{ color: var(--text-secondary); }}

    .next-date-box {{ display: flex; flex-direction: column; }}
    .next-date-text {{ font-weight: 600; font-family: var(--font-mono); font-size: 12px; }}
    .days-badge {{
      display: inline-block;
      background: #f0ebe4;
      color: #555e6d;
      padding: 1px 6px;
      border-radius: 3px;
      font-size: 10px;
      width: fit-content;
      margin-top: 2px;
    }}
    .consensus-tag {{ font-size: 11.5px; color: #444b58; }}
    .table-action-btn {{
      display: inline-block;
      padding: 3px 8px;
      background: #f4efe9;
      color: var(--accent);
      border-radius: var(--radius-sm);
      font-size: 11.5px;
      font-weight: 600;
      text-decoration: none;
      transition: all 0.15s;
    }}
    .table-action-btn:hover {{ background: var(--accent); color: #fff; }}

    /* ==============================================================================
       TAB 2: Real Rate Studio & Charts
       ============================================================================== */
    .studio-grid {{
      display: grid;
      grid-template-columns: 1fr;
      gap: 20px;
      margin-bottom: 24px;
    }}
    @media (min-width: 1024px) {{
      .studio-grid {{ grid-template-columns: 3fr 2fr; }}
    }}
    .chart-card {{
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: var(--radius-md);
      padding: 20px;
      box-shadow: var(--shadow-sm);
    }}
    .chart-card-header {{
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      margin-bottom: 16px;
    }}
    .chart-title {{
      font-size: 16px;
      font-weight: 700;
      color: var(--fg);
      display: flex;
      align-items: center;
      gap: 6px;
    }}
    .chart-desc {{
      color: var(--text-secondary);
      font-size: 12px;
      margin-top: 2px;
    }}
    .chart-plot-area {{
      min-height: 480px;
      width: 100%;
      position: relative;
    }}
    .lw-toolbar-row {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      flex-wrap: wrap;
      gap: 8px;
      margin-bottom: 10px;
      padding: 6px 10px;
      background: #FAF8F5;
      border: 1px solid var(--border-subtle);
      border-radius: var(--radius-sm);
    }}
    .lw-btn-group {{
      display: inline-flex;
      align-items: center;
      gap: 3px;
      flex-wrap: wrap;
    }}
    .lw-ctrl-btn {{
      appearance: none;
      border: 1px solid transparent;
      background: transparent;
      color: var(--text-secondary);
      font-family: var(--font-mono);
      font-size: 11px;
      font-weight: 600;
      padding: 3px 8px;
      border-radius: 3px;
      cursor: pointer;
      transition: all 0.12s ease;
    }}
    .lw-ctrl-btn:hover {{
      background: #EFECE6;
      color: var(--fg);
    }}
    .lw-ctrl-btn.active {{
      background: #12151a;
      color: #ffffff;
    }}
    .lw-ctrl-btn.tool-active {{
      background: rgba(13, 118, 128, 0.14);
      border-color: var(--teal);
      color: var(--teal);
    }}
    .lw-legend-row {{
      display: flex;
      flex-wrap: wrap;
      gap: 6px 12px;
      margin-bottom: 8px;
      font-size: 11.5px;
    }}
    .lw-legend-pill {{
      display: inline-flex;
      align-items: center;
      gap: 5px;
      padding: 2px 7px;
      border-radius: 4px;
      border: 1px solid var(--border-subtle);
      background: #ffffff;
      cursor: pointer;
      user-select: none;
      transition: opacity 0.15s, border-color 0.15s;
    }}
    .lw-legend-pill:hover {{
      border-color: var(--text-secondary);
    }}
    .lw-legend-pill.muted {{
      opacity: 0.35;
      text-decoration: line-through;
    }}
    .lw-delta-box {{
      display: none;
      align-items: center;
      justify-content: space-between;
      gap: 8px;
      padding: 5px 10px;
      margin-bottom: 8px;
      background: #F4F9F9;
      border: 1px solid rgba(13, 118, 128, 0.3);
      border-radius: 4px;
      font-family: var(--font-mono);
      font-size: 11px;
    }}
    .lw-delta-box.active {{
      display: flex;
    }}
    .chart-card.lw-fullscreen {{
      position: fixed !important;
      inset: 24px !important;
      z-index: 9999 !important;
      background: #FFFDFA !important;
      box-shadow: 0 24px 64px rgba(18, 21, 26, 0.38) !important;
      overflow-y: auto !important;
    }}
    .chart-card.lw-fullscreen .chart-plot-area {{
      height: calc(100vh - 220px) !important;
      min-height: 500px !important;
    }}

    /* Carry Insight Cards */
    .insight-row {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
      gap: 14px;
      margin-top: 18px;
    }}
    .insight-card {{
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: var(--radius-md);
      padding: 14px 16px;
      border-left: 4px solid var(--teal);
    }}
    .insight-card.warning {{ border-left-color: var(--accent); }}
    .insight-card.neutral {{ border-left-color: var(--slate); }}
    .insight-title {{
      font-size: 13px;
      font-weight: 700;
      color: var(--fg);
      margin-bottom: 4px;
      display: flex;
      justify-content: space-between;
    }}
    .insight-text {{
      font-size: 12px;
      color: var(--text-secondary);
      line-height: 1.45;
    }}

    /* ==============================================================================
       TAB 3: 2026/2027 Central Bank Calendar
       ============================================================================== */
    .cal-table {{
      width: 100%;
      border-collapse: collapse;
      font-size: 13px;
    }}
    .cal-table th {{
      background: #fbf9f6;
      padding: 10px 14px;
      border-bottom: 1px solid var(--border);
      color: var(--text-secondary);
      font-size: 11.5px;
      text-transform: uppercase;
    }}
    .cal-table td {{
      padding: 11px 14px;
      border-bottom: 1px solid var(--border-subtle);
      vertical-align: middle;
    }}
    .cal-table tr:hover {{ background: #faf8f5; }}
    .cal-date-col {{ min-width: 120px; }}
    .cal-date-main {{ font-family: var(--font-mono); font-weight: 700; color: var(--fg); }}
    .cal-days-sub {{ font-size: 11px; color: var(--text-secondary); }}
    .cal-cb-info {{ display: flex; align-items: center; gap: 10px; }}
    .cal-flag {{ font-size: 20px; }}
    .cal-event-desc {{ font-size: 12px; color: var(--text-secondary); }}
    .cal-badge {{
      display: inline-block;
      padding: 2px 8px;
      border-radius: var(--radius-sm);
      font-size: 11px;
      font-weight: 600;
    }}
    .tier-1-badge {{ background: rgba(153, 15, 61, 0.1); color: var(--accent); border: 1px solid rgba(153, 15, 61, 0.2); }}
    .tier-2-badge {{ background: rgba(54, 75, 97, 0.08); color: var(--slate); }}
    .cal-rate-col {{ font-family: var(--font-mono); font-weight: 600; }}
    .cal-consensus-text {{ font-size: 12px; font-weight: 500; color: var(--fg); }}
    .cal-link {{
      color: var(--teal);
      text-decoration: none;
      font-weight: 600;
      font-size: 12px;
    }}
    .cal-link:hover {{ text-decoration: underline; }}

    /* ==============================================================================
       TAB 4: Corridor Cards Grid
       ============================================================================== */
    .corridor-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(420px, 1fr));
      gap: 18px;
    }}
    .corridor-card {{
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: var(--radius-md);
      padding: 18px;
      box-shadow: var(--shadow-sm);
      display: flex;
      flex-direction: column;
      gap: 14px;
      transition: transform 0.15s, box-shadow 0.15s;
    }}
    .corridor-card:hover {{
      transform: translateY(-2px);
      box-shadow: var(--shadow-md);
    }}
    .card-top {{
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
    }}
    .card-id {{ display: flex; align-items: center; gap: 10px; }}
    .card-flag {{ font-size: 26px; }}
    .card-title {{ font-size: 15px; font-weight: 700; color: var(--fg); }}
    .card-sub {{ font-size: 12px; color: var(--text-secondary); }}

    .corridor-metric-grid {{
      display: grid;
      grid-template-columns: repeat(4, 1fr);
      gap: 8px;
      background: #faf8f5;
      padding: 10px;
      border-radius: var(--radius-sm);
      border: 1px solid var(--border-subtle);
    }}
    .metric-item {{ display: flex; flex-direction: column; }}
    .metric-label {{ font-size: 10.5px; color: var(--text-secondary); }}
    .metric-val {{ font-family: var(--font-mono); font-size: 15px; font-weight: 700; margin: 1px 0; }}
    .metric-val.primary-val {{ color: var(--accent); }}
    .metric-val.pos {{ color: var(--good); }}
    .metric-val.neg {{ color: var(--bad); }}
    .metric-sub {{ font-size: 10px; color: var(--text-secondary); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }}

    /* Corridor visual bar */
    .corridor-visualizer-box {{
      display: flex;
      flex-direction: column;
      gap: 4px;
    }}
    .corridor-track-labels {{
      display: flex;
      justify-content: space-between;
      font-size: 10.5px;
      color: var(--text-secondary);
      font-family: var(--font-mono);
    }}
    .corridor-bar-track {{
      position: relative;
      height: 14px;
      background: #e8e4df;
      border-radius: 7px;
      margin: 4px 0;
    }}
    .corridor-fill {{
      position: absolute;
      top: 0;
      bottom: 0;
      background: rgba(13, 118, 128, 0.25);
      border-radius: 7px;
    }}
    .corridor-marker {{
      position: absolute;
      top: -3px;
      width: 6px;
      height: 20px;
      border-radius: 3px;
      transform: translateX(-50%);
    }}
    .corridor-marker.floor {{ background: var(--slate); }}
    .corridor-marker.center {{ background: var(--accent); width: 8px; z-index: 2; }}
    .corridor-marker.ceil {{ background: var(--slate); }}

    .card-context-line {{
      display: flex;
      flex-direction: column;
      gap: 3px;
      font-size: 11.5px;
      border-top: 1px dashed var(--border);
      padding-top: 10px;
    }}
    .context-item {{ display: flex; gap: 6px; }}
    .ctx-title {{ color: var(--text-secondary); font-weight: 600; min-width: 90px; }}
    .ctx-val {{ color: var(--fg); font-family: var(--font-mono); }}

    .card-decision-banner {{
      background: #fbf9f6;
      border-radius: var(--radius-sm);
      padding: 8px 12px;
      display: flex;
      justify-content: space-between;
      align-items: center;
      font-size: 12px;
      border: 1px solid var(--border-subtle);
    }}
    .next-decision-label strong {{ font-family: var(--font-mono); margin-left: 4px; color: var(--fg); }}
    .consensus-badge {{ font-weight: 500; color: #475569; }}
    .card-deep-link {{
      color: var(--accent);
      text-decoration: none;
      font-weight: 600;
      font-size: 11.5px;
    }}
    .card-deep-link:hover {{ text-decoration: underline; }}

    /* ==============================================================================
       TAB 5: Guidance & Statement Diff
       ============================================================================== */
    .diff-container {{
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: var(--radius-md);
      padding: 22px;
      margin-top: 20px;
      box-shadow: var(--shadow-sm);
    }}
    .diff-controls {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      flex-wrap: wrap;
      gap: 14px;
      margin-bottom: 20px;
      padding-bottom: 16px;
      border-bottom: 1px solid var(--border);
    }}
    .diff-selector {{
      display: flex;
      align-items: center;
      gap: 10px;
    }}
    .diff-select {{
      padding: 6px 12px;
      border: 1px solid var(--border);
      border-radius: var(--radius-sm);
      font-size: 13px;
      background: #ffffff;
      color: var(--fg);
    }}
    .diff-body {{
      font-size: 14px;
      line-height: 1.8;
      color: #2b303a;
    }}
    .diff-paragraph {{ margin-bottom: 16px; text-align: justify; }}
    .diff-del {{
      background-color: #fee2e2;
      color: #991b1b;
      text-decoration: line-through;
      padding: 1px 4px;
      border-radius: 2px;
    }}
    .diff-add {{
      background-color: #dcfce7;
      color: #166534;
      text-decoration: none;
      font-weight: 500;
      padding: 1px 4px;
      border-radius: 2px;
    }}
    .keyword-tag {{
      display: inline-block;
      padding: 0 4px;
      border-radius: 2px;
      font-weight: 600;
      font-size: 12.5px;
    }}
    .keyword-tag.hawk {{ background: rgba(153, 15, 61, 0.15); color: #990f3d; }}
    .keyword-tag.dove {{ background: rgba(13, 118, 128, 0.15); color: #0d7680; }}

    /* Sentiment Meter */
    .sentiment-meter-box {{
      display: flex;
      align-items: center;
      gap: 10px;
      background: #faf8f5;
      padding: 8px 14px;
      border-radius: var(--radius-sm);
      border: 1px solid var(--border);
    }}
    .meter-label {{ font-size: 12px; font-weight: 600; color: var(--text-secondary); }}
    .gauge-track {{
      width: 120px;
      height: 10px;
      background: #e2e8f0;
      border-radius: 5px;
      position: relative;
      overflow: hidden;
    }}
    .gauge-fill {{
      position: absolute;
      top: 0;
      bottom: 0;
      border-radius: 5px;
    }}
    .gauge-fill.dove {{ background: var(--teal); left: 0; }}
    .gauge-fill.hawk {{ background: var(--accent); right: 0; }}
    .meter-score {{ font-family: var(--font-mono); font-weight: 700; font-size: 12px; }}

    /* Language toggles */
    .zh-only {{ display: none; }}
    .en-only {{ display: inline; }}
    html[lang="zh"] .zh-only {{ display: inline; }}
    html[lang="zh"] .en-only {{ display: none; }}
    div.zh-only {{ display: none; }}
    div.en-only {{ display: block; }}
    html[lang="zh"] div.zh-only {{ display: block; }}
    html[lang="zh"] div.en-only {{ display: none; }}
    span.zh-only {{ display: none; }}
    span.en-only {{ display: inline; }}
    html[lang="zh"] span.zh-only {{ display: inline; }}
    html[lang="zh"] span.en-only {{ display: none; }}

    /* Responsive */
    @media (max-width: 768px) {{
      .corridor-grid {{ grid-template-columns: 1fr; }}
      .topbar-nav {{ display: none; }}
      .matrix-table th, .matrix-table td {{ padding: 8px 10px; }}
      .header-main h1 {{ font-size: 22px; }}
    }}
  </style>
</head>
<body>

<!-- Top Navigation -->
<div class="topbar">
  <div class="brand">
    <span>East Meridian / Macro Dashboard</span>
  </div>
  <div class="topbar-nav">
    <nav class="country-nav" aria-label="country dashboards">
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
  <!-- Header Section -->
  <header class="page-header">
    <div class="header-main">
      <h1>
        <span>🏛️</span>
        <span class="en-only">Central Bank Policy & Monetary Cycle Tracker</span>
        <span class="zh-only">全球央行与货币政策周期追踪器</span>
      </h1>
      <div class="header-subtitle en-only">
        Institutional cross-sectional monitoring across all 18 economies: nominal & real policy rates, Taylor rule stances, 2026/2027 decision calendars, and official guidance.
      </div>
      <div class="header-subtitle zh-only">
        全景监控 18 家主要经济体与货币当局：名义与实际政策利率、泰勒中性立场、2026/2027 议息日程与央行前瞻指引。
      </div>
    </div>
    <div class="header-badges">
      <div class="stat-badge">
        <span class="stat-badge-num">18</span>
        <span class="stat-badge-desc en-only">Central Banks Tracked</span>
        <span class="stat-badge-desc zh-only">覆盖央行总数</span>
      </div>
      <div class="stat-badge">
        <span class="stat-badge-num">60+</span>
        <span class="stat-badge-desc en-only">2026/27 Meetings</span>
        <span class="stat-badge-desc zh-only">全年前瞻议息日程</span>
      </div>
      <div class="stat-badge">
        <span class="stat-badge-num">+11.9% ~ -1.2%</span>
        <span class="stat-badge-desc en-only">Real Policy Rate Spread</span>
        <span class="stat-badge-desc zh-only">全球实际利率跨度</span>
      </div>
    </div>
  </header>

  <!-- Main Tabs Navigation -->
  <div class="tab-bar">
    <button class="tab-btn active" onclick="switchTab('matrix')">
      🏛️ <span class="en-only">Global Policy Matrix</span><span class="zh-only">全景政策矩阵与周期雷达</span>
    </button>
    <button class="tab-btn" onclick="switchTab('realrate')">
      📊 <span class="en-only">Real Rate & Carry Studio</span><span class="zh-only">实际利率与利差套息工作室</span>
    </button>
    <button class="tab-btn" onclick="switchTab('calendar')">
      📅 <span class="en-only">Decision Calendar (60+)</span><span class="zh-only">全球央行议息日程 (60+ 场)</span>
    </button>
    <button class="tab-btn" onclick="switchTab('corridors')">
      📐 <span class="en-only">Operational Corridors</span><span class="zh-only">核心央行准备金走廊</span>
    </button>
    <button class="tab-btn" onclick="switchTab('guidance')">
      🔍 <span class="en-only">Statement Guidance & Dot Plot</span><span class="zh-only">前瞻指引与点阵图对比</span>
    </button>
  </div>

  <!-- TAB 1: Global Policy Stance Matrix -->
  <div id="tab-matrix" class="tab-pane active">
    <!-- Filter Chips & Search Bar -->
    <div class="filter-bar">
      <div class="filter-chips" id="matrix-region-filters">
        <button class="filter-chip active" onclick="filterMatrix('all')">
          <span class="en-only">All Economies (18)</span><span class="zh-only">全部经济体 (18)</span>
        </button>
        <button class="filter-chip" onclick="filterMatrix('dm')">
          <span class="en-only">Developed G4 (4)</span><span class="zh-only">发达成体系 G4</span>
        </button>
        <button class="filter-chip" onclick="filterMatrix('cee')">
          <span class="en-only">CEE-4 Economies (4)</span><span class="zh-only">中东欧核心四国</span>
        </button>
        <button class="filter-chip" onclick="filterMatrix('em')">
          <span class="en-only">Major Emerging (5)</span><span class="zh-only">重要新兴市场</span>
        </button>
        <button class="filter-chip" onclick="filterMatrix('frontier')">
          <span class="en-only">Frontier & Anchors (5)</span><span class="zh-only">前沿与离岸锚点</span>
        </button>
      </div>
      <div class="search-box">
        <span class="search-icon">🔍</span>
        <input type="text" id="matrix-search-input" class="search-input" placeholder="Search economy or CB..." onkeyup="searchMatrix()">
      </div>
    </div>

    <!-- Master Table -->
    <div class="table-responsive">
      <table class="matrix-table" id="master-policy-table">
        <thead>
          <tr>
            <th onclick="sortTable(0, 'text')"><span class="en-only">Economy / CB</span><span class="zh-only">经济体 / 机构</span></th>
            <th><span class="en-only">Primary Tool</span><span class="zh-only">核心政策工具</span></th>
            <th class="col-num" onclick="sortTable(2, 'num')"><span class="en-only">Policy Rate</span><span class="zh-only">名义基准</span></th>
            <th class="col-num" onclick="sortTable(3, 'num')"><span class="en-only">CPI YoY</span><span class="zh-only">最新CPI</span></th>
            <th class="col-num" onclick="sortTable(4, 'num')"><span class="en-only">Real Rate</span><span class="zh-only">实际政策利率</span></th>
            <th class="col-num" onclick="sortTable(5, 'num')"><span class="en-only">Target Gap</span><span class="zh-only">通胀目标差</span></th>
            <th><span class="en-only">Cycle Phase</span><span class="zh-only">周期阶段</span></th>
            <th class="col-num" onclick="sortTable(7, 'num')"><span class="en-only">12M Delta</span><span class="zh-only">12M变动</span></th>
            <th onclick="sortTable(8, 'date')"><span class="en-only">Next Decision</span><span class="zh-only">下次决议</span></th>
            <th><span class="en-only">Consensus</span><span class="zh-only">市场预期</span></th>
            <th><span class="en-only">Report</span><span class="zh-only">研报</span></th>
          </tr>
        </thead>
        <tbody id="matrix-tbody">
          {all_table_rows}
        </tbody>
      </table>
    </div>
  </div>

  <!-- TAB 2: Real Rate Studio -->
  <div id="tab-realrate" class="tab-pane">
    <!-- Interactive Historical Policy & Real Rate Cycle Explorer (Lightweight Charts) -->
    <div class="chart-card" id="card-policy-cycle-lw" style="margin-bottom: 20px;">
      <div class="chart-card-header">
        <div>
          <div class="chart-title">
            <span>⏱️</span>
            <span class="en-only">Global Central Bank Policy & Real Rate Cycle Trajectories (2000–2026)</span>
            <span class="zh-only">全球核心央行名义与实际政策利率历史周期演进 (2000–2026)</span>
          </div>
          <div class="chart-desc en-only">
            Interactive multi-country monetary cycle comparison. Click legend pills to toggle, double-click to solo, drag to pan, or hold Shift + drag (🔍) to measure cycle rate adjustments (Δ).
          </div>
          <div class="chart-desc zh-only">
            跨国货币周期联动与分化对比。单击图例隐藏/显示，双击图例单独聚焦某国央行，拖拽平移，按住 Shift 或点击 🔍 框选时间段自动计算加降息累计幅度 (Δ)。
          </div>
        </div>
      </div>

      <div class="lw-toolbar-row">
        <div class="lw-btn-group" id="cycle-cohort-btns">
          <button type="button" class="lw-ctrl-btn active" onclick="setPolicyCycleCohort('g4', this)">G4 (US·EA·UK·JP)</button>
          <button type="button" class="lw-ctrl-btn" onclick="setPolicyCycleCohort('em', this)">Major EM (CN·KR·ZA·TW)</button>
          <button type="button" class="lw-ctrl-btn" onclick="setPolicyCycleCohort('cee', this)">CEE-4 (PL·CZ·HU·RO)</button>
          <button type="button" class="lw-ctrl-btn" onclick="setPolicyCycleCohort('frontier', this)">High-Carry (TR·KZ·UZ·EG·NG)</button>
        </div>
        <div class="lw-btn-group" id="cycle-metric-btns">
          <button type="button" class="lw-ctrl-btn active" onclick="setPolicyCycleMetric('nominal', this)">
            <span class="en-only">Nominal Policy Rate (%)</span><span class="zh-only">名义政策利率 (%)</span>
          </button>
          <button type="button" class="lw-ctrl-btn" onclick="setPolicyCycleMetric('real', this)">
            <span class="en-only">Real Policy Rate (i − π)</span><span class="zh-only">实际政策利率 (i − π)</span>
          </button>
        </div>
        <div class="lw-btn-group" id="cycle-range-btns">
          <button type="button" class="lw-ctrl-btn" data-range="1Y" onclick="setPolicyCycleRange('1Y', this)">1Y</button>
          <button type="button" class="lw-ctrl-btn" data-range="3Y" onclick="setPolicyCycleRange('3Y', this)">3Y</button>
          <button type="button" class="lw-ctrl-btn" data-range="5Y" onclick="setPolicyCycleRange('5Y', this)">5Y</button>
          <button type="button" class="lw-ctrl-btn" data-range="10Y" onclick="setPolicyCycleRange('10Y', this)">10Y</button>
          <button type="button" class="lw-ctrl-btn active" data-range="ALL" onclick="setPolicyCycleRange('ALL', this)">All</button>
          <button type="button" class="lw-ctrl-btn" id="cycle-boxzoom-btn" title="Box-zoom time range & calculate delta (or Shift + drag)" onclick="togglePolicyCycleBoxZoom(this)">🔍</button>
          <button type="button" class="lw-ctrl-btn" title="Reset view" onclick="resetPolicyCycleZoom()">↺</button>
          <button type="button" class="lw-ctrl-btn" title="Export CSV" onclick="exportPolicyCycleCSV()">CSV</button>
          <button type="button" class="lw-ctrl-btn" title="Download PNG" onclick="exportPolicyCyclePNG()">PNG</button>
          <button type="button" class="lw-ctrl-btn" title="Expand fullscreen" onclick="toggleCardFullscreen('card-policy-cycle-lw', () => resizePolicyCycleLw())">⛶</button>
        </div>
      </div>

      <div class="lw-legend-row" id="policy-cycle-legend"></div>
      <div class="lw-delta-box" id="policy-cycle-delta"></div>
      <div id="policy-cycle-lw-chart" class="chart-plot-area" style="min-height: 360px; height: 360px;"></div>
    </div>

    <div class="studio-grid">
      <!-- Horizontal Real Rate Chart -->
      <div class="chart-card" id="card-real-rate-bar">
        <div class="chart-card-header">
          <div>
            <div class="chart-title">
              <span>📊</span>
              <span class="en-only">Global Real Policy Rate Ranking (18 Economies)</span>
              <span class="zh-only">全球 18 国实际政策利率横向排行</span>
            </div>
            <div class="chart-desc en-only">
              Net real policy yield ($i - \\pi$) ranked from deepest restrictive carry down to negative real rates.
            </div>
            <div class="chart-desc zh-only">
              名义政策利率减去最新头寸 CPI 通胀率，衡量真实紧缩力度与跨国套息收益护城河。
            </div>
          </div>
          <div class="lw-btn-group">
            <button type="button" class="lw-ctrl-btn" onclick="exportRealRateCSV()">CSV</button>
            <button type="button" class="lw-ctrl-btn" onclick="exportCanvasCardPNG('real-rate-canvas', 'global_real_policy_rate_ranking.png')">PNG</button>
            <button type="button" class="lw-ctrl-btn" onclick="toggleCardFullscreen('card-real-rate-bar', () => initRealRateChart())">⛶</button>
          </div>
        </div>
        <div id="real-rate-plot" class="chart-plot-area"></div>
      </div>

      <!-- Taylor Stance Deviation Studio -->
      <div class="chart-card" id="card-taylor-scatter">
        <div class="chart-card-header">
          <div>
            <div class="chart-title">
              <span>🎯</span>
              <span class="en-only">Policy Rate vs. Taylor Rule Implied Benchmark</span>
              <span class="zh-only">政策利率 vs. 泰勒中性推算偏离度</span>
            </div>
            <div class="chart-desc en-only">
              Actual policy rates plotted against standard Taylor Rule specifications (neutral $r^*$, trend growth, target gap).
            </div>
            <div class="chart-desc zh-only">
              各央行实际政策基准与泰勒规则理论中性利率对比（衡量政策是否走在曲线前面或过度紧缩）。
            </div>
          </div>
          <div class="lw-btn-group">
            <button type="button" class="lw-ctrl-btn" onclick="exportTaylorCSV()">CSV</button>
            <button type="button" class="lw-ctrl-btn" onclick="exportCanvasCardPNG('taylor-scatter-canvas', 'taylor_rule_stance_scatter.png')">PNG</button>
            <button type="button" class="lw-ctrl-btn" onclick="toggleCardFullscreen('card-taylor-scatter', () => initTaylorChart())">⛶</button>
          </div>
        </div>
        <div id="taylor-scatter-plot" class="chart-plot-area"></div>
      </div>
    </div>

    <!-- Institutional Analytical Commentary Cards -->
    <div class="insight-row">
      <div class="insight-card">
        <div class="insight-title">
          <span class="en-only">🏆 Top Real Carry Yield Champions</span>
          <span class="zh-only">🏆 高实际正收益护城河</span>
          <span class="rr-pill rr-deep-restr">+5.0% ~ +11.9%</span>
        </div>
        <div class="insight-text en-only">
          Nigeria (+11.86%), Egypt (+9.96%), Uzbekistan (+7.27%), Turkey (+6.27%), Kazakhstan (+5.01%), and Hungary (+4.15%) offer massive positive real yields. These aggressive restrictive stances are anchoring FX reserves and providing substantial cushion against currency depreciation.
        </div>
        <div class="insight-text zh-only">
          尼日利亚 (+11.86%)、埃及 (+9.96%)、乌兹别克斯坦 (+7.27%)、土耳其 (+6.27%)、哈萨克斯坦 (+5.01%) 与匈牙利 (+4.15%) 提供强劲的实际正收益。极高的正利差不仅为本币汇率提供充足防护垫，也强力推动通胀下行。
        </div>
      </div>

      <div class="insight-card neutral">
        <div class="insight-title">
          <span class="en-only">⚖️ Calibrated Neutrality & Plateau Anchor</span>
          <span class="zh-only">⚖️ 中性平稳与高位观望梯队</span>
          <span class="rr-pill rr-neutral">0.0% ~ +2.8%</span>
        </div>
        <div class="insight-text en-only">
          China (+2.80%), South Africa (+2.75%), Hong Kong (+1.45%), Czechia (+1.30%), the United States (+0.76%), Euro Area (+0.50%), and United Kingdom (+0.25%) operate with modest positive real buffers, calibrating easing steps meeting-by-meeting.
        </div>
        <div class="insight-text zh-only">
          中国 (+2.80%)、南非 (+2.75%)、香港 (+1.45%)、捷克 (+1.30%)、美国 (+0.76%)、欧元区 (+0.50%) 及英国 (+0.25%) 处于温和正实际利率区间，政策姿态偏向中性校准或逐次会议审慎观察。
        </div>
      </div>

      <div class="insight-card warning">
        <div class="insight-title">
          <span class="en-only">⚠️ Negative Real Rate Zones</span>
          <span class="zh-only">⚠️ 负实际利率宽松区</span>
          <span class="rr-pill rr-accomm">< 0.0%</span>
        </div>
        <div class="insight-text en-only">
          Japan (-1.19%), Taiwan (-0.73%), and Poland (-0.25%) exhibit negative real policy rates. Japan continues normalizing out of negative rates, while Poland maintains a defensive hold despite CPI hovering above its 2.5% inflation target.
        </div>
        <div class="insight-text zh-only">
          日本 (-1.19%)、中国台湾 (-0.73%) 与波兰 (-0.25%) 的政策利率仍低于当期 CPI 通胀。日本银行处在紧缩正常化加息周期中；波兰则在能源补贴取消推高通胀背景下继续坚守观望。
        </div>
      </div>
    </div>
  </div>

  <!-- TAB 3: 2026/2027 Central Bank Calendar -->
  <div id="tab-calendar" class="tab-pane">
    <div class="filter-bar">
      <div class="filter-chips" id="calendar-region-filters">
        <button class="filter-chip active" onclick="filterCalendar('all')">
          <span class="en-only">All Decisions (60+)</span><span class="zh-only">全部议息日程 (60+)</span>
        </button>
        <button class="filter-chip" onclick="filterCalendar('dm')">
          <span class="en-only">Developed G4</span><span class="zh-only">发达 G4</span>
        </button>
        <button class="filter-chip" onclick="filterCalendar('cee')">
          <span class="en-only">CEE-4</span><span class="zh-only">中东欧 CEE-4</span>
        </button>
        <button class="filter-chip" onclick="filterCalendar('em')">
          <span class="en-only">Major EM</span><span class="zh-only">新兴市场</span>
        </button>
        <button class="filter-chip" onclick="filterCalendar('frontier')">
          <span class="en-only">Frontier</span><span class="zh-only">前沿与离岸</span>
        </button>
        <button class="filter-chip" onclick="filterCalendarTier('projection')">
          <span class="en-only">⭐ SEP / Projections Only</span><span class="zh-only">⭐ 仅看重大预测/点阵图</span>
        </button>
      </div>
      <div class="search-box">
        <span class="search-icon">🔍</span>
        <input type="text" id="calendar-search-input" class="search-input" placeholder="Filter meetings..." onkeyup="searchCalendar()">
      </div>
    </div>

    <div class="table-responsive">
      <table class="cal-table" id="calendar-master-table">
        <thead>
          <tr>
            <th><span class="en-only">Date / Horizon</span><span class="zh-only">议息日期 / 倒计时</span></th>
            <th><span class="en-only">Central Bank & Event</span><span class="zh-only">央行与会议类型</span></th>
            <th><span class="en-only">Significance</span><span class="zh-only">重要程度</span></th>
            <th><span class="en-only">Current Rate</span><span class="zh-only">当前基准</span></th>
            <th><span class="en-only">Market Consensus</span><span class="zh-only">市场共识预期</span></th>
            <th><span class="en-only">Profile</span><span class="zh-only">主页</span></th>
          </tr>
        </thead>
        <tbody id="calendar-tbody">
          {all_calendar_rows}
        </tbody>
      </table>
    </div>
  </div>

  <!-- TAB 4: Core Operational Corridors -->
  <div id="tab-corridors" class="tab-pane">
    <div class="filter-bar">
      <div class="filter-chips">
        <button class="filter-chip active" onclick="filterCorridors('all')">
          <span class="en-only">All Key Anchors (9)</span><span class="zh-only">核心大行与走廊 (9)</span>
        </button>
        <button class="filter-chip" onclick="filterCorridors('dm')">
          <span class="en-only">Developed G4 (Fed, ECB, BoE, BoJ)</span><span class="zh-only">发达成体系 G4</span>
        </button>
        <button class="filter-chip" onclick="filterCorridors('em')">
          <span class="en-only">Emerging Anchors (PBC, TCMB, SARB, BOK)</span><span class="zh-only">新兴核心央行</span>
        </button>
        <button class="filter-chip" onclick="filterCorridors('cee')">
          <span class="en-only">CEE Anchor (MNB)</span><span class="zh-only">中东欧对称走廊</span>
        </button>
      </div>
    </div>

    <div class="corridor-grid" id="corridor-cards-container">
      {all_corridor_cards}
    </div>
  </div>

  <!-- TAB 5: Guidance & Statement Diff -->
  <div id="tab-guidance" class="tab-pane">
    <!-- Sub-section A: FOMC Dot Plot vs SOFR Curve -->
    <div class="chart-card" id="card-fomc-dotplot" style="margin-bottom: 24px;">
      <div class="chart-card-header">
        <div>
          <div class="chart-title">
            <span>📈</span>
            <span class="en-only">FOMC Dot Plot Projections vs. Market Implied Forward Curve</span>
            <span class="zh-only">美联储 FOMC 点阵图预测 vs. 市场隐含远期定价曲线</span>
          </div>
          <div class="chart-desc en-only">
            Individual Federal Open Market Committee member rate projections vs. SOFR futures forward curve across 2024-2027 and Longer Run ($r^*$).
          </div>
          <div class="chart-desc zh-only">
            美联储 19 位官员利率预测散点、中位数路径与联邦基金期货/SOFR市场隐含远期利率走势对比。
          </div>
        </div>
        <div class="lw-btn-group">
          <button type="button" class="lw-ctrl-btn" onclick="exportDotplotCSV()">CSV</button>
          <button type="button" class="lw-ctrl-btn" onclick="exportCanvasCardPNG('fomc-dotplot-canvas', 'fomc_dotplot_sofr_curve.png')">PNG</button>
          <button type="button" class="lw-ctrl-btn" onclick="toggleCardFullscreen('card-fomc-dotplot', () => initDotplot())">⛶</button>
        </div>
      </div>
      <div id="fomc-dotplot-plot" class="chart-plot-area" style="min-height: 440px;"></div>
    </div>

    <!-- Sub-section B: Statement Word-by-Word Diff -->
    <div class="diff-container">
      <div class="diff-controls">
        <div class="diff-selector">
          <label for="diff-cb-selector" style="font-weight:600; font-size:13px;">
            <span class="en-only">Select Decision Statement:</span>
            <span class="zh-only">选择议息声明对比样本:</span>
          </label>
          <select id="diff-cb-selector" class="diff-select" onchange="renderDiffStatement()">
            <option value="fomc_nov_sep">Federal Reserve (FOMC): Nov 2024 vs. Sep 2024</option>
            <option value="ecb_oct_sep">European Central Bank (ECB): Oct 2024 vs. Sep 2024</option>
            <option value="boe_nov_sep">Bank of England (BoE): Nov 2024 vs. Sep 2024</option>
          </select>
        </div>

        <div class="sentiment-meter-box">
          <span class="meter-label en-only">Net Tone Shift:</span>
          <span class="meter-label zh-only">净基调转向指数:</span>
          <div class="gauge-track">
            <div id="gauge-bar" class="gauge-fill dove" style="width: 24%;"></div>
          </div>
          <span id="gauge-score" class="meter-score" style="color: var(--teal);">-24 (Dovish Shift)</span>
        </div>
      </div>

      <div id="diff-content" class="diff-body">
        <!-- Rendered dynamically by JavaScript -->
      </div>
    </div>
  </div>
</div>

<script>
/* ==============================================================================
   State Management & Language Toggle
   ============================================================================== */
let currentLang = 'en';

function formatVal(v, decimals = 2) {{
  if (v === null || v === undefined || isNaN(v)) return '—';
  const num = Number(v);
  return num.toLocaleString('en-US', {{
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals
  }});
}}

function toggleLang() {{
  currentLang = currentLang === 'en' ? 'zh' : 'en';
  document.documentElement.lang = currentLang;
  document.getElementById('lang-btn').innerText = currentLang === 'en' ? '中文' : 'English';

  // Re-render language-dependent components
  renderDiffStatement();
  initPolicyCycleLwChart();
  initRealRateChart();
  initTaylorChart();
  initDotplot();
}}

function switchTab(tabId) {{
  document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
  document.querySelectorAll('.tab-pane').forEach(pane => pane.classList.remove('active'));

  event.currentTarget.classList.add('active');
  const target = document.getElementById('tab-' + tabId);
  if (target) {{
    target.classList.add('active');
    window.dispatchEvent(new Event('resize'));
    if (tabId === 'realrate') {{
      initPolicyCycleLwChart();
      initRealRateChart();
      initTaylorChart();
    }} else if (tabId === 'guidance') {{
      initDotplot();
      renderDiffStatement();
    }}
  }}
}}

function toggleCardFullscreen(cardId, onResize) {{
  const card = document.getElementById(cardId);
  if (!card) return;
  card.classList.toggle('lw-fullscreen');
  setTimeout(() => {{
    if (typeof onResize === 'function') onResize();
  }}, 60);
}}

/* ==============================================================================
   Table Sorting & Filtering Engine
   ============================================================================== */
function filterMatrix(region) {{
  document.querySelectorAll('#matrix-region-filters .filter-chip').forEach(c => c.classList.remove('active'));
  event.currentTarget.classList.add('active');

  const rows = document.querySelectorAll('#matrix-tbody tr');
  rows.forEach(r => {{
    if (region === 'all' || r.getAttribute('data-region') === region) {{
      r.style.display = '';
    }} else {{
      r.style.display = 'none';
    }}
  }});
}}

function searchMatrix() {{
  const query = document.getElementById('matrix-search-input').value.toLowerCase().trim();
  const rows = document.querySelectorAll('#matrix-tbody tr');
  rows.forEach(r => {{
    const text = (r.getAttribute('data-search') || '').toLowerCase();
    r.style.display = text.includes(query) ? '' : 'none';
  }});
}}

let sortState = {{ col: -1, asc: true }};

function sortTable(colIndex, type) {{
  const table = document.getElementById('master-policy-table');
  const tbody = document.getElementById('matrix-tbody');
  const rows = Array.from(tbody.querySelectorAll('tr'));
  const th = table.querySelectorAll('th')[colIndex];

  if (sortState.col === colIndex) {{
    sortState.asc = !sortState.asc;
  }} else {{
    sortState.col = colIndex;
    sortState.asc = true;
  }}

  table.querySelectorAll('th').forEach(h => h.classList.remove('sorted-asc', 'sorted-desc'));
  th.classList.add(sortState.asc ? 'sorted-asc' : 'sorted-desc');

  rows.sort((a, b) => {{
    let valA, valB;
    if (type === 'num') {{
      valA = parseFloat(a.children[colIndex].getAttribute('data-sort')) || 0;
      valB = parseFloat(b.children[colIndex].getAttribute('data-sort')) || 0;
    }} else if (type === 'date') {{
      valA = a.children[colIndex].getAttribute('data-sort') || '';
      valB = b.children[colIndex].getAttribute('data-sort') || '';
    }} else {{
      valA = a.children[colIndex].innerText.trim().toLowerCase();
      valB = b.children[colIndex].innerText.trim().toLowerCase();
    }}

    if (valA < valB) return sortState.asc ? -1 : 1;
    if (valA > valB) return sortState.asc ? 1 : -1;
    return 0;
  }});

  rows.forEach(r => tbody.appendChild(r));
}}

/* ==============================================================================
   Calendar Filtering & Search
   ============================================================================== */
function filterCalendar(region) {{
  document.querySelectorAll('#calendar-region-filters .filter-chip').forEach(c => c.classList.remove('active'));
  event.currentTarget.classList.add('active');

  const rows = document.querySelectorAll('#calendar-tbody tr');
  rows.forEach(r => {{
    if (region === 'all' || r.getAttribute('data-region') === region) {{
      r.style.display = '';
    }} else {{
      r.style.display = 'none';
    }}
  }});
}}

function filterCalendarTier(tierType) {{
  document.querySelectorAll('#calendar-region-filters .filter-chip').forEach(c => c.classList.remove('active'));
  event.currentTarget.classList.add('active');

  const rows = document.querySelectorAll('#calendar-tbody tr');
  rows.forEach(r => {{
    if (r.getAttribute('data-type') === tierType) {{
      r.style.display = '';
    }} else {{
      r.style.display = 'none';
    }}
  }});
}}

function searchCalendar() {{
  const query = document.getElementById('calendar-search-input').value.toLowerCase().trim();
  const rows = document.querySelectorAll('#calendar-tbody tr');
  rows.forEach(r => {{
    const text = (r.getAttribute('data-search') || '').toLowerCase();
    r.style.display = text.includes(query) ? '' : 'none';
  }});
}}

function filterCorridors(region) {{
  document.querySelectorAll('#tab-corridors .filter-chip').forEach(c => c.classList.remove('active'));
  event.currentTarget.classList.add('active');

  const cards = document.querySelectorAll('#corridor-cards-container .corridor-card');
  cards.forEach(c => {{
    if (region === 'all' || c.getAttribute('data-region') === region) {{
      c.style.display = '';
    }} else {{
      c.style.display = 'none';
    }}
  }});
}}

/* ==============================================================================
   Lightweight Charts: Historical Policy & Real Rate Cycle Explorer
   ============================================================================== */
const HISTORICAL_CYCLES = {historical_cycles_json};
const REAL_RATE_DATA = {real_rate_json};
const TAYLOR_DATA = {taylor_json};

const COHORT_MAP = {{
  g4: [
    {{ code: 'US', color: '#0d7680', label_en: '🇺🇸 Fed (US)', label_zh: '🇺🇸 美联储 (US)' }},
    {{ code: 'EA', color: '#990f3d', label_en: '🇪🇺 ECB (EA)', label_zh: '🇪🇺 欧央行 (EA)' }},
    {{ code: 'UK', color: '#364b61', label_en: '🇬🇧 BoE (UK)', label_zh: '🇬🇧 英格兰银行 (UK)' }},
    {{ code: 'JP', color: '#d97706', label_en: '🇯🇵 BoJ (JP)', label_zh: '🇯🇵 日本银行 (JP)' }}
  ],
  em: [
    {{ code: 'CN', color: '#990f3d', label_en: '🇨🇳 PBC (CN)', label_zh: '🇨🇳 中国央行 (CN)' }},
    {{ code: 'KR', color: '#0d7680', label_en: '🇰🇷 BOK (KR)', label_zh: '🇰🇷 韩国银行 (KR)' }},
    {{ code: 'ZA', color: '#d97706', label_en: '🇿🇦 SARB (ZA)', label_zh: '🇿🇦 南非央行 (ZA)' }},
    {{ code: 'TW', color: '#364b61', label_en: '🇹🇼 CBC (TW)', label_zh: '🇹🇼 台湾央行 (TW)' }}
  ],
  cee: [
    {{ code: 'PL', color: '#0d7680', label_en: '🇵🇱 NBP (PL)', label_zh: '🇵🇱 波兰央行 (PL)' }},
    {{ code: 'CZ', color: '#364b61', label_en: '🇨🇿 CNB (CZ)', label_zh: '🇨🇿 捷克央行 (CZ)' }},
    {{ code: 'HU', color: '#990f3d', label_en: '🇭🇺 MNB (HU)', label_zh: '🇭🇺 匈牙利央行 (HU)' }},
    {{ code: 'RO', color: '#d97706', label_en: '🇷🇴 BNR (RO)', label_zh: '🇷🇴 罗马尼亚央行 (RO)' }}
  ],
  frontier: [
    {{ code: 'TR', color: '#990f3d', label_en: '🇹🇷 TCMB (TR)', label_zh: '🇹🇷 土耳其央行 (TR)' }},
    {{ code: 'KZ', color: '#0d7680', label_en: '🇰🇿 NBK (KZ)', label_zh: '🇰🇿 哈萨克斯坦央行 (KZ)' }},
    {{ code: 'UZ', color: '#364b61', label_en: '🇺🇿 CBU (UZ)', label_zh: '🇺🇿 乌兹别克斯坦央行 (UZ)' }},
    {{ code: 'EG', color: '#d97706', label_en: '🇪🇬 CBE (EG)', label_zh: '🇪🇬 埃及央行 (EG)' }},
    {{ code: 'NG', color: '#6b21a8', label_en: '🇳🇬 CBN (NG)', label_zh: '🇳🇬 尼日利亚央行 (NG)' }}
  ]
}};

let cycleCohort = 'g4';
let cycleMetric = 'nominal';
let cycleRange = 'ALL';
let cycleLwChart = null;
let cycleSeriesEntries = [];
let cycleBoxZoom = false;

function initPolicyCycleLwChart() {{
  const plotEl = document.getElementById('policy-cycle-lw-chart');
  if (!plotEl || typeof LightweightCharts === 'undefined') return;

  if (cycleLwChart) {{
    try {{ cycleLwChart.remove(); }} catch (e) {{}}
    cycleLwChart = null;
  }}
  plotEl.innerHTML = '';

  const tooltip = document.createElement('div');
  tooltip.style.cssText = 'position:absolute;top:10px;left:12px;z-index:15;pointer-events:none;background:rgba(255,253,250,0.95);border:1px solid #d9d2c7;border-radius:4px;padding:6px 10px;font-size:11px;display:none;box-shadow:0 2px 8px rgba(0,0,0,0.08);';
  plotEl.appendChild(tooltip);

  const selectOverlay = document.createElement('div');
  selectOverlay.style.cssText = 'position:absolute;top:0;bottom:24px;background:rgba(13,118,128,0.15);border-left:1.5px dashed #0d7680;border-right:1.5px dashed #0d7680;pointer-events:none;z-index:14;display:none;';
  plotEl.appendChild(selectOverlay);

  const chart = LightweightCharts.createChart(plotEl, {{
    width: plotEl.clientWidth || 900,
    height: plotEl.clientHeight || 360,
    layout: {{
      background: {{ type: 'solid', color: 'transparent' }},
      textColor: '#737c8c',
      fontFamily: "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif",
      fontSize: 11,
      attributionLogo: false
    }},
    grid: {{
      vertLines: {{ visible: false }},
      horzLines: {{ color: 'rgba(18, 21, 26, 0.06)', style: 0 }}
    }},
    rightPriceScale: {{
      borderVisible: false,
      scaleMargins: {{ top: 0.10, bottom: 0.10 }}
    }},
    timeScale: {{
      borderColor: 'rgba(18, 21, 26, 0.14)',
      rightOffset: 2,
      fixLeftEdge: true,
      fixRightEdge: true
    }},
    localization: {{
      priceFormatter: (val) => `${{formatVal(val, 2)}}%`
    }},
    crosshair: {{
      mode: 0,
      vertLine: {{ color: 'rgba(18, 21, 26, 0.25)', width: 1, style: 2, labelBackgroundColor: '#12151a' }},
      horzLine: {{ color: 'rgba(18, 21, 26, 0.25)', width: 1, style: 2, labelBackgroundColor: '#12151a' }}
    }},
    handleScroll: {{
      mouseWheel: false,
      pressedMouseMove: !cycleBoxZoom,
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

  cycleLwChart = chart;
  cycleSeriesEntries = [];
  const members = COHORT_MAP[cycleCohort] || COHORT_MAP.g4;
  const legendEl = document.getElementById('policy-cycle-legend');
  if (legendEl) legendEl.innerHTML = '';

  members.forEach((m, idx) => {{
    const rawPts = ((HISTORICAL_CYCLES[m.code] || {{}})[cycleMetric] || []).filter(p => p && p.time && !isNaN(p.value));
    if (!rawPts.length) return;
    const s = chart.addLineSeries({{
      color: m.color,
      lineWidth: 2.2,
      priceLineVisible: false,
      lastValueVisible: true
    }});
    s.setData(rawPts);
    if (idx === 0) {{
      s.createPriceLine({{
        price: 0,
        color: '#12151a',
        lineWidth: 1,
        lineStyle: 2,
        axisLabelVisible: false,
        title: '0%'
      }});
    }}
    const label = currentLang === 'zh' ? m.label_zh : m.label_en;
    const lastVal = rawPts[rawPts.length - 1].value;
    const entry = {{ code: m.code, color: m.color, label, series: s, data: rawPts, visible: true }};
    cycleSeriesEntries.push(entry);

    if (legendEl) {{
      const pill = document.createElement('span');
      pill.className = 'lw-legend-pill';
      pill.dataset.idx = String(cycleSeriesEntries.length - 1);
      pill.title = 'Click to show/hide · Double-click to solo';
      pill.innerHTML = `<span style="width:10px;height:3px;background:${{m.color}};display:inline-block;border-radius:1px;"></span>` +
        `<strong>${{label}}</strong> <span style="font-family:var(--font-mono);color:var(--text-secondary);">${{formatVal(lastVal, 2)}}%</span>`;
      const sIdx = cycleSeriesEntries.length - 1;
      pill.addEventListener('click', (e) => {{
        if (e.altKey || e.metaKey) soloPolicyCycleSeries(sIdx);
        else togglePolicyCycleSeries(sIdx);
      }});
      pill.addEventListener('dblclick', (e) => {{
        e.preventDefault();
        soloPolicyCycleSeries(sIdx);
      }});
      legendEl.appendChild(pill);
    }}
  }});

  chart.timeScale().fitContent();

  chart.subscribeCrosshairMove(param => {{
    if (!param.time || !param.point || param.point.x < 0 || param.point.y < 0) {{
      tooltip.style.display = 'none';
      return;
    }}
    const tStr = typeof param.time === 'string'
      ? param.time
      : `${{param.time.year}}-${{String(param.time.month).padStart(2, '0')}}-${{String(param.time.day).padStart(2, '0')}}`;
    const rows = [];
    cycleSeriesEntries.forEach(en => {{
      if (!en.visible) return;
      const sv = param.seriesData.get(en.series);
      if (sv && sv.value !== undefined) {{
        rows.push(`<div><span style="color:${{en.color}};font-weight:700;">● ${{en.label}}:</span> <strong>${{formatVal(sv.value, 2)}}%</strong></div>`);
      }}
    }});
    if (!rows.length) {{
      tooltip.style.display = 'none';
      return;
    }}
    tooltip.innerHTML = `<div style="font-weight:700;margin-bottom:2px;color:#12151a;">${{tStr}}</div>` + rows.join('');
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

  // Shift + drag or 🔍 box-zoom
  let dragStartX = null;
  plotEl.addEventListener('mousedown', e => {{
    if (!(cycleBoxZoom || e.shiftKey)) return;
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
    if (!cycleBoxZoom) {{
      chart.applyOptions({{ handleScroll: {{ pressedMouseMove: true }} }});
    }}
    if (x2 - x1 < 12) return;
    const l1 = chart.timeScale().coordinateToLogical(x1);
    const l2 = chart.timeScale().coordinateToLogical(x2);
    if (l1 !== null && l2 !== null && l2 > l1) {{
      chart.timeScale().setVisibleLogicalRange({{ from: l1, to: l2 }});
      updatePolicyCycleDelta(l1, l2);
    }}
  }});

  plotEl.addEventListener('dblclick', () => resetPolicyCycleZoom());

  if (cycleRange !== 'ALL') {{
    setPolicyCycleRange(cycleRange, document.querySelector(`#cycle-range-btns [data-range="${{cycleRange}}"]`));
  }}
}}

function resizePolicyCycleLw() {{
  const plotEl = document.getElementById('policy-cycle-lw-chart');
  if (!plotEl || !cycleLwChart) return;
  cycleLwChart.applyOptions({{
    width: plotEl.clientWidth || 900,
    height: plotEl.clientHeight || 360
  }});
  cycleLwChart.timeScale().fitContent();
}}

function setPolicyCycleCohort(cohort, btnEl) {{
  cycleCohort = cohort;
  document.querySelectorAll('#cycle-cohort-btns .lw-ctrl-btn').forEach(b => b.classList.remove('active'));
  if (btnEl) btnEl.classList.add('active');
  initPolicyCycleLwChart();
}}

function setPolicyCycleMetric(metric, btnEl) {{
  cycleMetric = metric;
  document.querySelectorAll('#cycle-metric-btns .lw-ctrl-btn').forEach(b => b.classList.remove('active'));
  if (btnEl) btnEl.classList.add('active');
  initPolicyCycleLwChart();
}}

function setPolicyCycleRange(rangeKey, btnEl) {{
  cycleRange = rangeKey;
  document.querySelectorAll('#cycle-range-btns [data-range]').forEach(b => b.classList.remove('active'));
  if (btnEl) btnEl.classList.add('active');
  if (!cycleLwChart || !cycleSeriesEntries.length) return;
  if (rangeKey === 'ALL') {{
    cycleLwChart.timeScale().fitContent();
    const dBox = document.getElementById('policy-cycle-delta');
    if (dBox) dBox.classList.remove('active');
    return;
  }}
  const yrs = {{ '1Y': 1, '3Y': 3, '5Y': 5, '10Y': 10 }}[rangeKey] || 5;
  const primary = cycleSeriesEntries.find(e => e.visible && e.data.length) || cycleSeriesEntries[0];
  if (!primary || !primary.data.length) return;
  const maxIso = primary.data[primary.data.length - 1].time;
  const parts = maxIso.split('-').map(Number);
  const fromIso = `${{parts[0] - yrs}}-${{String(parts[1] || 1).padStart(2, '0')}}-01`;
  try {{
    cycleLwChart.timeScale().setVisibleRange({{ from: fromIso, to: maxIso }});
    const vr = cycleLwChart.timeScale().getVisibleLogicalRange();
    if (vr) updatePolicyCycleDelta(vr.from, vr.to);
  }} catch (e) {{
    cycleLwChart.timeScale().fitContent();
  }}
}}

function togglePolicyCycleBoxZoom(btnEl) {{
  cycleBoxZoom = !cycleBoxZoom;
  if (btnEl) btnEl.classList.toggle('tool-active', cycleBoxZoom);
  const plotEl = document.getElementById('policy-cycle-lw-chart');
  if (plotEl) plotEl.style.cursor = cycleBoxZoom ? 'crosshair' : 'grab';
  if (cycleLwChart) cycleLwChart.applyOptions({{ handleScroll: {{ pressedMouseMove: !cycleBoxZoom }} }});
}}

function resetPolicyCycleZoom() {{
  cycleBoxZoom = false;
  const btn = document.getElementById('cycle-boxzoom-btn');
  if (btn) btn.classList.remove('tool-active');
  const plotEl = document.getElementById('policy-cycle-lw-chart');
  if (plotEl) plotEl.style.cursor = 'grab';
  if (cycleLwChart) {{
    cycleLwChart.applyOptions({{ handleScroll: {{ pressedMouseMove: true }} }});
    cycleLwChart.timeScale().fitContent();
  }}
  const dBox = document.getElementById('policy-cycle-delta');
  if (dBox) dBox.classList.remove('active');
  document.querySelectorAll('#cycle-range-btns [data-range]').forEach(b => b.classList.toggle('active', b.getAttribute('data-range') === 'ALL'));
}}

function togglePolicyCycleSeries(idx) {{
  const target = cycleSeriesEntries[idx];
  if (!target) return;
  target.visible = !target.visible;
  target.series.applyOptions({{ visible: target.visible }});
  document.querySelectorAll('#policy-cycle-legend .lw-legend-pill').forEach((p, i) => {{
    p.classList.toggle('muted', !cycleSeriesEntries[i].visible);
  }});
}}

function soloPolicyCycleSeries(idx) {{
  const onlyThis = cycleSeriesEntries.every((e, i) => i === idx ? e.visible : !e.visible);
  cycleSeriesEntries.forEach((e, i) => {{
    e.visible = onlyThis ? true : (i === idx);
    e.series.applyOptions({{ visible: e.visible }});
  }});
  document.querySelectorAll('#policy-cycle-legend .lw-legend-pill').forEach((p, i) => {{
    p.classList.toggle('muted', !cycleSeriesEntries[i].visible);
  }});
}}

function updatePolicyCycleDelta(fromLogical, toLogical) {{
  const dBox = document.getElementById('policy-cycle-delta');
  const primary = cycleSeriesEntries.find(e => e.visible && e.data.length);
  if (!dBox || !primary) return;
  const i1 = Math.max(0, Math.min(primary.data.length - 1, Math.round(fromLogical)));
  const i2 = Math.max(0, Math.min(primary.data.length - 1, Math.round(toLogical)));
  if (i2 <= i1) return;
  const p1 = primary.data[i1];
  const p2 = primary.data[i2];
  const diffBps = Math.round((p2.value - p1.value) * 100);
  const sign = diffBps > 0 ? '+' : '';
  const col = diffBps >= 0 ? '#990f3d' : '#0d7680';
  dBox.innerHTML = `<span><strong>${{primary.label}} Δ (${{p1.time}} → ${{p2.time}})</strong>: ${{formatVal(p1.value, 2)}}% → ${{formatVal(p2.value, 2)}}% ` +
    `<strong style="color:${{col}}">(${{sign}}${{formatVal(diffBps, 0)}} bps)</strong></span>` +
    `<button type="button" class="lw-ctrl-btn" onclick="resetPolicyCycleZoom()">✕</button>`;
  dBox.classList.add('active');
}}

function exportPolicyCycleCSV() {{
  if (!cycleSeriesEntries.length) return;
  const datesSet = new Set();
  cycleSeriesEntries.forEach(e => e.data.forEach(p => datesSet.add(p.time)));
  const dates = Array.from(datesSet).sort();
  const header = ['Date', ...cycleSeriesEntries.map(e => `${{e.code}}_${{cycleMetric}}_pct`)];
  const maps = cycleSeriesEntries.map(e => new Map(e.data.map(p => [p.time, p.value])));
  const rows = [header.join(',')];
  dates.forEach(dt => {{
    rows.push([dt, ...maps.map(m => m.has(dt) ? m.get(dt) : '')].join(','));
  }});
  const blob = new Blob([rows.join('\\n')], {{ type: 'text/csv;charset=utf-8;' }});
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = `policy_cycle_${{cycleCohort}}_${{cycleMetric}}.csv`;
  a.click();
}}

function exportPolicyCyclePNG() {{
  if (!cycleLwChart) return;
  try {{
    const canvas = cycleLwChart.takeScreenshot();
    const a = document.createElement('a');
    a.href = canvas.toDataURL('image/png');
    a.download = `policy_cycle_${{cycleCohort}}_${{cycleMetric}}.png`;
    a.click();
  }} catch (e) {{
    console.error(e);
  }}
}}

/* ==============================================================================
   High-DPI Interactive FT Canvas Charts (Real Rate Ranking, Taylor Rule, Dot Plot)
   ============================================================================== */
function setupHiDPICanvas(container, canvasId, heightPx) {{
  container.innerHTML = '';
  const dpr = window.devicePixelRatio || 1;
  const w = Math.max(360, container.clientWidth || 560);
  const h = Math.max(380, container.clientHeight || heightPx);
  const canvas = document.createElement('canvas');
  canvas.id = canvasId;
  canvas.width = w * dpr;
  canvas.height = h * dpr;
  canvas.style.width = w + 'px';
  canvas.style.height = h + 'px';
  canvas.style.display = 'block';
  container.appendChild(canvas);

  const tip = document.createElement('div');
  tip.style.cssText = 'position:absolute;pointer-events:none;background:rgba(255,253,250,0.96);border:1px solid #d9d2c7;border-radius:4px;padding:6px 10px;font-size:11px;line-height:1.4;box-shadow:0 2px 8px rgba(0,0,0,0.1);display:none;z-index:20;';
  container.appendChild(tip);

  const ctx = canvas.getContext('2d');
  ctx.scale(dpr, dpr);
  return {{ canvas, ctx, w, h, tip }};
}}

function exportCanvasCardPNG(canvasId, filename) {{
  const c = document.getElementById(canvasId);
  if (!c) return;
  const a = document.createElement('a');
  a.href = c.toDataURL('image/png');
  a.download = filename;
  a.click();
}}

function exportRealRateCSV() {{
  const rows = [['Code,Economy,Policy_Rate_Pct,CPI_YoY_Pct,Real_Policy_Rate_Pct']];
  REAL_RATE_DATA.forEach(d => rows.push(`${{d.code}},"${{d.name_en}}",${{d.policy_rate}},${{d.cpi}},${{d.real_rate}}`));
  const blob = new Blob([rows.join('\\n')], {{ type: 'text/csv;charset=utf-8;' }});
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = 'global_real_policy_rates.csv';
  a.click();
}}

function exportTaylorCSV() {{
  const rows = [['Code,Economy,Actual_Policy_Rate_Pct,Taylor_Implied_Rate_Pct,Policy_Gap_Pct,Stance']];
  TAYLOR_DATA.forEach(d => rows.push(`${{d.code}},"${{d.name_en}}",${{d.actual_rate}},${{d.taylor_rate}},${{d.policy_gap}},${{d.stance_label}}`));
  const blob = new Blob([rows.join('\\n')], {{ type: 'text/csv;charset=utf-8;' }});
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = 'taylor_rule_stance.csv';
  a.click();
}}

function exportDotplotCSV() {{
  const rows = [['Horizon,Rate_Pct,Participant_Count']];
  DOT_DATA.forEach(d => rows.push(`"${{d.year}}",${{d.rate}},${{d.count}}`));
  const blob = new Blob([rows.join('\\n')], {{ type: 'text/csv;charset=utf-8;' }});
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = 'fomc_dotplot_projections.csv';
  a.click();
}}

function initRealRateChart() {{
  const elem = document.getElementById('real-rate-plot');
  if (!elem) return;

  const sorted = [...REAL_RATE_DATA]; // descending from highest real rate to lowest
  const {{ canvas, ctx, w, h, tip }} = setupHiDPICanvas(elem, 'real-rate-canvas', 480);

  const padL = 158, padR = 58, padT = 16, padB = 38;
  const plotW = w - padL - padR;
  const plotH = h - padT - padB;

  const vals = sorted.map(d => d.real_rate);
  const minX = Math.min(-2.5, Math.floor(Math.min(...vals) - 1));
  const maxX = Math.max(13.0, Math.ceil(Math.max(...vals) + 1.5));
  const xToPx = (v) => padL + ((v - minX) / (maxX - minX)) * plotW;

  ctx.fillStyle = '#FFFDFA';
  ctx.fillRect(0, 0, w, h);

  // Gridlines
  ctx.strokeStyle = '#e8e4df';
  ctx.lineWidth = 1;
  ctx.fillStyle = '#737c8c';
  ctx.font = '10.5px -apple-system, BlinkMacSystemFont, sans-serif';
  ctx.textAlign = 'center';
  for (let gx = Math.ceil(minX / 2) * 2; gx <= maxX; gx += 2) {{
    const px = xToPx(gx);
    ctx.beginPath();
    ctx.moveTo(px, padT);
    ctx.lineTo(px, padT + plotH);
    ctx.stroke();
    ctx.fillText(`${{gx >= 0 ? '+' : ''}}${{gx}}%`, px, padT + plotH + 16);
  }}

  // Zero reference line
  const zeroPx = xToPx(0);
  ctx.strokeStyle = '#12151a';
  ctx.lineWidth = 1.6;
  ctx.beginPath();
  ctx.moveTo(zeroPx, padT);
  ctx.lineTo(zeroPx, padT + plotH);
  ctx.stroke();

  const rowH = plotH / sorted.length;
  const barH = Math.max(10, rowH * 0.66);
  const hitBoxes = [];

  sorted.forEach((d, i) => {{
    const yCenter = padT + i * rowH + rowH / 2;
    const yTop = yCenter - barH / 2;
    const x0 = xToPx(0);
    const x1 = xToPx(d.real_rate);
    const bx = Math.min(x0, x1);
    const bw = Math.max(2, Math.abs(x1 - x0));

    const color = d.real_rate >= 2.0 ? '#0d7680' : (d.real_rate >= 0.0 ? '#364b61' : '#990f3d');
    ctx.fillStyle = color;
    ctx.fillRect(bx, yTop, bw, barH);

    // Y label
    ctx.fillStyle = '#12151a';
    ctx.font = '600 11px -apple-system, BlinkMacSystemFont, sans-serif';
    ctx.textAlign = 'right';
    const name = currentLang === 'zh' ? d.name_zh : d.name_en;
    ctx.fillText(`${{d.flag}} ${{name}} (${{d.code}})`, padL - 8, yCenter + 4);

    // Value label
    ctx.fillStyle = color;
    ctx.font = '700 10.5px ui-monospace, SFMono-Regular, monospace';
    ctx.textAlign = d.real_rate >= 0 ? 'left' : 'right';
    const valStr = `${{d.real_rate >= 0 ? '+' : ''}}${{formatVal(d.real_rate, 2)}}%`;
    ctx.fillText(valStr, d.real_rate >= 0 ? (x1 + 5) : (x1 - 5), yCenter + 3.5);

    hitBoxes.push({{ yTop: yCenter - rowH / 2, yBot: yCenter + rowH / 2, d }});
  }});

  canvas.onmousemove = (e) => {{
    const rect = canvas.getBoundingClientRect();
    const my = e.clientY - rect.top;
    const mx = e.clientX - rect.left;
    const hit = hitBoxes.find(b => my >= b.yTop && my <= b.yBot);
    if (!hit) {{
      tip.style.display = 'none';
      return;
    }}
    const d = hit.d;
    const name = currentLang === 'zh' ? d.name_zh : d.name_en;
    tip.innerHTML = `<strong>${{d.flag}} ${{name}} (${{d.code}})</strong><br>` +
      `${{currentLang === 'zh' ? '实际政策利率' : 'Real Policy Rate'}}: <strong>${{d.real_rate >= 0 ? '+' : ''}}${{formatVal(d.real_rate, 2)}}%</strong><br>` +
      `${{currentLang === 'zh' ? '名义政策利率' : 'Nominal Policy Rate'}}: ${{formatVal(d.policy_rate, 2)}}%<br>` +
      `${{currentLang === 'zh' ? '最新CPI通胀' : 'Headline CPI YoY'}}: ${{formatVal(d.cpi, 2)}}%`;
    tip.style.left = Math.min(w - 190, mx + 14) + 'px';
    tip.style.top = Math.max(8, my - 28) + 'px';
    tip.style.display = 'block';
  }};
  canvas.onmouseleave = () => {{ tip.style.display = 'none'; }};
}}

function initTaylorChart() {{
  const elem = document.getElementById('taylor-scatter-plot');
  if (!elem) return;

  const {{ canvas, ctx, w, h, tip }} = setupHiDPICanvas(elem, 'taylor-scatter-canvas', 480);
  const padL = 52, padR = 24, padT = 20, padB = 46;
  const plotW = w - padL - padR;
  const plotH = h - padT - padB;

  const actuals = TAYLOR_DATA.map(d => d.actual_rate);
  const taylors = TAYLOR_DATA.map(d => d.taylor_rate);
  const minVal = Math.min(0, ...actuals, ...taylors);
  const maxVal = Math.ceil(Math.max(...actuals, ...taylors) + 2);

  const xToPx = (v) => padL + ((v - minVal) / (maxVal - minVal)) * plotW;
  const yToPx = (v) => padT + plotH - ((v - minVal) / (maxVal - minVal)) * plotH;

  ctx.fillStyle = '#FFFDFA';
  ctx.fillRect(0, 0, w, h);

  // Grid
  ctx.strokeStyle = '#e8e4df';
  ctx.lineWidth = 1;
  ctx.fillStyle = '#737c8c';
  ctx.font = '10.5px -apple-system, BlinkMacSystemFont, sans-serif';
  const step = maxVal > 25 ? 5 : 2;
  for (let gv = 0; gv <= maxVal; gv += step) {{
    const px = xToPx(gv);
    const py = yToPx(gv);
    ctx.beginPath(); ctx.moveTo(px, padT); ctx.lineTo(px, padT + plotH); ctx.stroke();
    ctx.beginPath(); ctx.moveTo(padL, py); ctx.lineTo(padL + plotW, py); ctx.stroke();
    ctx.textAlign = 'center';
    ctx.fillText(`${{gv}}%`, px, padT + plotH + 16);
    ctx.textAlign = 'right';
    ctx.fillText(`${{gv}}%`, padL - 6, py + 3.5);
  }}

  // 45-degree Taylor Parity dashed line
  ctx.save();
  ctx.strokeStyle = '#9da8b6';
  ctx.lineWidth = 1.5;
  ctx.setLineDash([5, 4]);
  ctx.beginPath();
  ctx.moveTo(xToPx(minVal), yToPx(minVal));
  ctx.lineTo(xToPx(maxVal), yToPx(maxVal));
  ctx.stroke();
  ctx.restore();

  // Axis titles
  ctx.fillStyle = '#364b61';
  ctx.font = '600 11px -apple-system, BlinkMacSystemFont, sans-serif';
  ctx.textAlign = 'center';
  ctx.fillText(currentLang === 'zh' ? '泰勒规则理论中性利率 (%)' : 'Taylor Rule Implied Benchmark (%)', padL + plotW / 2, h - 10);

  const pts = [];
  TAYLOR_DATA.forEach(d => {{
    const px = xToPx(d.taylor_rate);
    const py = yToPx(d.actual_rate);
    const col = d.policy_gap >= 1.0 ? '#0d7680' : (d.policy_gap <= -1.0 ? '#990f3d' : '#364b61');

    ctx.beginPath();
    ctx.arc(px, py, 6, 0, Math.PI * 2);
    ctx.fillStyle = col;
    ctx.fill();
    ctx.lineWidth = 1.5;
    ctx.strokeStyle = '#ffffff';
    ctx.stroke();

    ctx.fillStyle = '#12151a';
    ctx.font = '700 10px ui-monospace, SFMono-Regular, monospace';
    ctx.textAlign = 'center';
    ctx.fillText(d.code, px, py - 9);

    pts.push({{ px, py, d }});
  }});

  canvas.onmousemove = (e) => {{
    const rect = canvas.getBoundingClientRect();
    const mx = e.clientX - rect.left;
    const my = e.clientY - rect.top;
    let best = null, bestDist = 18;
    pts.forEach(p => {{
      const dist = Math.hypot(mx - p.px, my - p.py);
      if (dist < bestDist) {{ bestDist = dist; best = p; }}
    }});
    if (!best) {{ tip.style.display = 'none'; return; }}
    const d = best.d;
    const name = currentLang === 'zh' ? d.name_zh : d.name_en;
    tip.innerHTML = `<strong>${{d.flag}} ${{name}} (${{d.code}})</strong><br>` +
      `${{currentLang === 'zh' ? '实际政策利率' : 'Actual Policy Rate'}}: <strong>${{formatVal(d.actual_rate, 2)}}%</strong><br>` +
      `${{currentLang === 'zh' ? '泰勒中性推算' : 'Taylor Implied'}}: ${{formatVal(d.taylor_rate, 2)}}%<br>` +
      `${{currentLang === 'zh' ? '政策偏离度' : 'Stance Gap'}}: <strong>${{d.policy_gap >= 0 ? '+' : ''}}${{formatVal(d.policy_gap, 2)}}%</strong>`;
    tip.style.left = Math.min(w - 190, best.px + 12) + 'px';
    tip.style.top = Math.max(8, best.py - 32) + 'px';
    tip.style.display = 'block';
  }};
  canvas.onmouseleave = () => {{ tip.style.display = 'none'; }};
}}

/* ==============================================================================
   FOMC Dot Plot vs SOFR Curve (High-DPI Interactive Canvas)
   ============================================================================== */
const DOT_DATA = [
  {{ year: '2024', rate: 4.375, count: 9 }},
  {{ year: '2024', rate: 4.625, count: 7 }},
  {{ year: '2024', rate: 4.875, count: 2 }},
  {{ year: '2024', rate: 5.125, count: 1 }},
  {{ year: '2025', rate: 2.875, count: 1 }},
  {{ year: '2025', rate: 3.125, count: 2 }},
  {{ year: '2025', rate: 3.375, count: 9 }},
  {{ year: '2025', rate: 3.625, count: 4 }},
  {{ year: '2025', rate: 3.875, count: 3 }},
  {{ year: '2026', rate: 2.375, count: 1 }},
  {{ year: '2026', rate: 2.625, count: 2 }},
  {{ year: '2026', rate: 2.875, count: 7 }},
  {{ year: '2026', rate: 3.125, count: 5 }},
  {{ year: '2026', rate: 3.375, count: 3 }},
  {{ year: '2026', rate: 3.625, count: 1 }},
  {{ year: '2027', rate: 2.625, count: 2 }},
  {{ year: '2027', rate: 2.875, count: 9 }},
  {{ year: '2027', rate: 3.125, count: 5 }},
  {{ year: '2027', rate: 3.375, count: 2 }},
  {{ year: '2027', rate: 3.625, count: 1 }},
  {{ year: 'Longer Run', rate: 2.375, count: 1 }},
  {{ year: 'Longer Run', rate: 2.500, count: 3 }},
  {{ year: 'Longer Run', rate: 2.625, count: 4 }},
  {{ year: 'Longer Run', rate: 2.875, count: 5 }},
  {{ year: 'Longer Run', rate: 3.000, count: 3 }},
  {{ year: 'Longer Run', rate: 3.250, count: 2 }},
  {{ year: 'Longer Run', rate: 3.750, count: 1 }}
];

function initDotplot() {{
  const elem = document.getElementById('fomc-dotplot-plot');
  if (!elem) return;

  const {{ canvas, ctx, w, h, tip }} = setupHiDPICanvas(elem, 'fomc-dotplot-canvas', 440);
  const padL = 56, padR = 36, padT = 24, padB = 54;
  const plotW = w - padL - padR;
  const plotH = h - padT - padB;

  const minY = 2.0, maxY = 5.5;
  const xToPx = (idx) => padL + ((idx + 0.5) / 5) * plotW;
  const yToPx = (v) => padT + plotH - ((v - minY) / (maxY - minY)) * plotH;

  ctx.fillStyle = '#FFFDFA';
  ctx.fillRect(0, 0, w, h);

  // Horizontal grid
  ctx.strokeStyle = '#e8e4df';
  ctx.lineWidth = 1;
  ctx.fillStyle = '#737c8c';
  ctx.font = '11px -apple-system, BlinkMacSystemFont, sans-serif';
  for (let yv = 2.0; yv <= 5.5; yv += 0.5) {{
    const py = yToPx(yv);
    ctx.beginPath(); ctx.moveTo(padL, py); ctx.lineTo(padL + plotW, py); ctx.stroke();
    ctx.textAlign = 'right';
    ctx.fillText(`${{formatVal(yv, 2)}}%`, padL - 8, py + 4);
  }}

  const xLabels = ['2024 Year-End', '2025 Year-End', '2026 Year-End', '2027 Year-End', 'Longer Run (r*)'];
  ctx.textAlign = 'center';
  xLabels.forEach((lbl, i) => {{
    const px = xToPx(i);
    ctx.beginPath(); ctx.moveTo(px, padT); ctx.lineTo(px, padT + plotH); ctx.stroke();
    ctx.fillStyle = '#12151a';
    ctx.font = '600 11px -apple-system, BlinkMacSystemFont, sans-serif';
    ctx.fillText(lbl, px, padT + plotH + 20);
  }});

  const YEAR_INDEX = {{ '2024': 0, '2025': 1, '2026': 2, '2027': 3, 'Longer Run': 4 }};
  const hitDots = [];

  // Participant Dots
  DOT_DATA.forEach(group => {{
    const baseIdx = YEAR_INDEX[group.year];
    const centerPx = xToPx(baseIdx);
    const py = yToPx(group.rate);
    for (let i = 0; i < group.count; i++) {{
      const offsetPx = group.count === 1 ? 0 : (i - (group.count - 1) / 2) * 11;
      const px = centerPx + offsetPx;
      ctx.beginPath();
      ctx.arc(px, py, 4.5, 0, Math.PI * 2);
      ctx.fillStyle = 'rgba(13, 118, 128, 0.85)';
      ctx.fill();
      ctx.lineWidth = 1;
      ctx.strokeStyle = '#085259';
      ctx.stroke();
      hitDots.push({{ px, py, year: group.year, rate: group.rate, count: group.count, kind: 'FOMC Participant Dot' }});
    }}
  }});

  // FOMC SEP Median Path
  const mediansY = [4.375, 3.375, 2.875, 2.875, 2.875];
  ctx.strokeStyle = '#990f3d';
  ctx.lineWidth = 2.6;
  ctx.beginPath();
  mediansY.forEach((v, i) => {{
    const px = xToPx(i), py = yToPx(v);
    if (i === 0) ctx.moveTo(px, py); else ctx.lineTo(px, py);
  }});
  ctx.stroke();
  mediansY.forEach((v, i) => {{
    const px = xToPx(i), py = yToPx(v);
    ctx.beginPath(); ctx.arc(px, py, 5, 0, Math.PI * 2);
    ctx.fillStyle = '#990f3d'; ctx.fill();
    hitDots.push({{ px, py, year: xLabels[i], rate: v, count: 19, kind: 'FOMC SEP Median' }});
  }});

  // SOFR Futures Forward Curve
  const marketY = [4.580, 3.820, 3.450, 3.400, 3.380];
  ctx.save();
  ctx.strokeStyle = '#d97706';
  ctx.lineWidth = 2.2;
  ctx.setLineDash([5, 4]);
  ctx.beginPath();
  marketY.forEach((v, i) => {{
    const px = xToPx(i), py = yToPx(v);
    if (i === 0) ctx.moveTo(px, py); else ctx.lineTo(px, py);
  }});
  ctx.stroke();
  ctx.restore();
  marketY.forEach((v, i) => {{
    const px = xToPx(i), py = yToPx(v);
    ctx.beginPath(); ctx.arc(px, py, 4.5, 0, Math.PI * 2);
    ctx.fillStyle = '#d97706'; ctx.fill();
    hitDots.push({{ px, py, year: xLabels[i], rate: v, count: null, kind: 'SOFR Futures Implied' }});
  }});

  canvas.onmousemove = (e) => {{
    const rect = canvas.getBoundingClientRect();
    const mx = e.clientX - rect.left;
    const my = e.clientY - rect.top;
    let best = null, bestDist = 14;
    hitDots.forEach(p => {{
      const dist = Math.hypot(mx - p.px, my - p.py);
      if (dist <= bestDist) {{ bestDist = dist; best = p; }}
    }});
    if (!best) {{ tip.style.display = 'none'; return; }}
    tip.innerHTML = `<strong>${{best.kind}} (${{best.year}})</strong><br>` +
      `Rate: <strong>${{formatVal(best.rate, 3)}}%</strong>` +
      (best.count ? ` (${{best.count}} participants)` : '');
    tip.style.left = Math.min(w - 200, best.px + 12) + 'px';
    tip.style.top = Math.max(8, best.py - 28) + 'px';
    tip.style.display = 'block';
  }};
  canvas.onmouseleave = () => {{ tip.style.display = 'none'; }};
}}

/* ==============================================================================
   Statement Semantic Diff Engine
   ============================================================================== */
const STATEMENTS = {{
  fomc_nov_sep: {{
    cb: 'Federal Reserve (FOMC)',
    period: 'November 7, 2024 vs. September 18, 2024',
    tone_score: -24,
    paragraphs: [
      `Recent indicators suggest that economic activity has continued to expand at a <span class="keyword-tag hawk">solid pace</span>. <del class="diff-del">Job gains have slowed</del><ins class="diff-add">Since earlier in the year, labor market conditions have generally eased</ins>, and the unemployment rate has moved up but remains low. Inflation has made <del class="diff-del">further </del>progress toward the Committee's 2 percent objective but <span class="keyword-tag hawk">remains somewhat elevated</span>.`,
      `The Committee seeks to achieve maximum employment and inflation at the rate of 2 percent over the longer run. <del class="diff-del">The Committee has gained greater confidence that inflation is moving sustainably toward 2 percent, and judges</del><ins class="diff-add">The Committee judges</ins> that the risks to achieving its employment and inflation goals are <span class="keyword-tag dove">roughly in balance</span>. The economic outlook is uncertain, and the Committee is attentive to the risks to both sides of its dual mandate.`,
      `<del class="diff-del">In light of the progress on inflation and the balance of risks</del><ins class="diff-add">In support of its goals</ins>, the Committee decided to lower the target range for the federal funds rate by <del class="diff-del">1/2 percentage point to 4-3/4 to 5 percent</del><ins class="diff-add">1/4 percentage point to 4-1/2 to 4-3/4 percent</ins>. In considering additional adjustments to the target range for the federal funds rate, the Committee will carefully assess incoming data, the evolving outlook, and the balance of risks.`
    ]
  }},
  ecb_oct_sep: {{
    cb: 'European Central Bank (ECB)',
    period: 'October 17, 2024 vs. September 12, 2024',
    tone_score: -35,
    paragraphs: [
      `The Governing Council today decided to lower the <del class="diff-del">deposit facility rate by 25 basis points</del><ins class="diff-add">three key ECB interest rates by 25 basis points</ins>. The decision to lower the deposit facility rate is based on its updated assessment of the inflation outlook. The incoming information on inflation shows that the <span class="keyword-tag dove">disinflationary process</span> is well on track.`,
      `<ins class="diff-add">The inflation outlook is also affected by recent <span class="keyword-tag dove">downside surprises</span> in indicators of economic activity. Meanwhile, financing conditions remain <span class="keyword-tag hawk">restrictive</span>.</ins>`,
      `Domestic inflation remains high, as wages are still rising at an elevated pace. At the same time, labour cost pressures are expected to continue <span class="keyword-tag dove">easing gradually</span>, with profits partially buffering the impact of higher wages on inflation.`
    ]
  }},
  boe_nov_sep: {{
    cb: 'Bank of England (BoE)',
    period: 'November 7, 2024 vs. September 19, 2024',
    tone_score: -18,
    paragraphs: [
      `The Bank of England's Monetary Policy Committee (MPC) voted by a majority of <del class="diff-del">8–1 to maintain Bank Rate at 5%</del><ins class="diff-add">8–1 to reduce Bank Rate by 0.25 percentage points, to 4.75%</ins>. One member preferred to maintain Bank Rate at 5%.`,
      `There has been continued progress on disinflation, particularly as previous external shocks have abated, though remaining domestic inflationary pressures are resolving more slowly.`,
      `<ins class="diff-add">Based on the evolving evidence, a <span class="keyword-tag dove">gradual approach</span> to removing policy restraint remains appropriate. Monetary policy will need to continue to remain <span class="keyword-tag hawk">restrictive</span> for sufficiently long until the risks to inflation returning sustainably to the 2% target have dissipated.</ins>`
    ]
  }}
}};

function renderDiffStatement() {{
  const selector = document.getElementById('diff-cb-selector');
  if (!selector) return;
  const key = selector.value;
  const data = STATEMENTS[key] || STATEMENTS.fomc_nov_sep;

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
    gaugeScore.innerText = `+${{data.tone_score}} (${{currentLang === 'zh' ? '鹰派偏向' : 'Hawkish Shift'}})`;
  }}

  const contentElem = document.getElementById('diff-content');
  contentElem.innerHTML = data.paragraphs.map(p => `<p class="diff-paragraph">${{p}}</p>`).join('');
}}

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {{
  initPolicyCycleLwChart();
  initRealRateChart();
  initTaylorChart();
  initDotplot();
  renderDiffStatement();
}});
window.addEventListener('resize', () => {{
  if (document.getElementById('tab-realrate')?.classList.contains('active')) {{
    resizePolicyCycleLw();
    initRealRateChart();
    initTaylorChart();
  }}
  if (document.getElementById('tab-guidance')?.classList.contains('active')) {{
    initDotplot();
  }}
}});
</script>
</body>
</html>
"""


def build() -> Path:
    """Compile and write policy_tracker.html in both output/ and root directories."""
    OUTPUT.mkdir(parents=True, exist_ok=True)
    html_content = build_policy_tracker_html()
    clean_html = "\n".join(line.rstrip() for line in html_content.splitlines()) + "\n"

    out_file = OUTPUT / "policy_tracker.html"
    out_file.write_text(clean_html, encoding="utf-8")
    print(f"Wrote {out_file} ({len(clean_html):,} bytes)")

    root_file = ROOT / "policy_tracker.html"
    root_file.write_text(clean_html, encoding="utf-8")
    print(f"Wrote {root_file} ({len(clean_html):,} bytes)")

    return out_file


if __name__ == "__main__":
    build()
