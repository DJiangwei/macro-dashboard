"""Enrichment script for US Institutional Inflation, Momentum & Industrial Pricing Studio.

Pulls official BLS CPI & PPI series, BEA PCE, and Federal Reserve survey/market metrics:
1. Table 1: CPI Inflation by product group (8 BLS categories + Food/Energy/Shelter sub-items)
2. Short-Term Inflation Momentum Monitor (1M, 3M, 6M annualized vs 12M YoY across Headline, Core, Supercore, PCE)
3. Table 2: Final Demand PPI breakdown (Goods, Services, Construction) & Intermediate Demand
4. PPI - CPI Margin Scissors Pipeline & pass-through transmission
5. Inflation Expectations & Capacity Studio (Michigan 1Y/5Y, TIPS 5Y/10Y breakevens, Capacity Utilization)

Saves output to: output/us_inflation_deepdive.json
"""

import json
import os
import sys
import math
import logging
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
OUTPUT = ROOT / "output"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from country_primer.adapters import fetch_fred, _get_fred_api_key

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

# BLS CPI Relative Importance Weights (Dec 2024 / 2025 BLS release)
US_CPI_WEIGHTS_RAW = {
    "FOOD": 13.4,
    "FOOD_HOME": 8.1,
    "FOOD_AWAY": 5.3,
    "ENERGY": 6.7,
    "ENERGY_COMM": 3.4,
    "ENERGY_SERV": 3.3,
    "CORE_GOODS": 18.8,
    "APPAREL": 2.5,
    "NEW_VEHICLES": 4.2,
    "USED_VEHICLES": 2.1,
    "SHELTER": 36.2,
    "RENT": 7.7,
    "OER": 26.8,
    "TRANS_SERV": 6.5,
    "MED_SERV": 6.4,
    "EDU_COMM": 5.5,
    "RECREATION": 5.4,
    "OTHER_SERV": 2.8,
}

# 8 Major Categories + Sub-items structure for Table 1
US_CPI_STRUCTURE = [
    {
        "code": "FOOD",
        "name_en": "Food",
        "name_zh": "食品与饮料",
        "raw_weight": 13.4,
        "series_id": "CPIUFDSL",
        "sub_items": [
            {"code": "FOOD_HOME", "name_en": "Food at home (Groceries)", "name_zh": "家庭自用食品", "raw_weight": 8.1, "series_id": "CUSR0000SAF11"},
            {"code": "FOOD_AWAY", "name_en": "Food away from home (Dining)", "name_zh": "外出就餐与餐饮", "raw_weight": 5.3, "series_id": "CUSR0000SEFV"},
        ],
    },
    {
        "code": "ENERGY",
        "name_en": "Energy",
        "name_zh": "能源分项",
        "raw_weight": 6.7,
        "series_id": "CPIENGSL",
        "sub_items": [
            {"code": "ENERGY_COMM", "name_en": "Energy commodities (Gasoline/Fuel)", "name_zh": "能源商品(汽油燃油)", "raw_weight": 3.4, "series_id": "CUSR0000SACE"},
            {"code": "ENERGY_SERV", "name_en": "Energy services (Electricity/Gas)", "name_zh": "能源服务(电力燃气)", "raw_weight": 3.3, "series_id": "CUSR0000SEHF"},
        ],
    },
    {
        "code": "CORE_GOODS",
        "name_en": "Core Goods (ex Food & Energy)",
        "name_zh": "核心非能源商品",
        "raw_weight": 18.8,
        "series_id": "CUSR0000SACL1E",
        "sub_items": [
            {"code": "APPAREL", "name_en": "Apparel", "name_zh": "服装鞋帽", "raw_weight": 2.5, "series_id": "CPIAPPSL"},
            {"code": "NEW_VEHICLES", "name_en": "New vehicles", "name_zh": "新车价格", "raw_weight": 4.2, "series_id": "CUSR0000SETA01"},
            {"code": "USED_VEHICLES", "name_en": "Used cars and trucks", "name_zh": "二手汽车与卡车", "raw_weight": 2.1, "series_id": "CUSR0000SETA02"},
        ],
    },
    {
        "code": "SHELTER",
        "name_en": "Shelter",
        "name_zh": "住房居住成本",
        "raw_weight": 36.2,
        "series_id": "CUSR0000SAH1",
        "sub_items": [
            {"code": "RENT", "name_en": "Rent of primary residence", "name_zh": "主要居所租金", "raw_weight": 7.7, "series_id": "CUSR0000SEHA"},
            {"code": "OER", "name_en": "Owners' equivalent rent (OER)", "name_zh": "业主等价租金(OER)", "raw_weight": 26.8, "series_id": "CUSR0000SEHC"},
        ],
    },
    {
        "code": "TRANS_SERV",
        "name_en": "Transportation services",
        "name_zh": "交通运输服务",
        "raw_weight": 6.5,
        "series_id": "CUSR0000SAS4",
        "sub_items": [],
    },
    {
        "code": "MED_SERV",
        "name_en": "Medical care services",
        "name_zh": "医疗保健服务",
        "raw_weight": 6.4,
        "series_id": "CUSR0000SAM2",
        "sub_items": [],
    },
    {
        "code": "EDU_COMM",
        "name_en": "Education & communication",
        "name_zh": "教育与通信支出",
        "raw_weight": 5.5,
        "series_id": "CPIEDUSL",
        "sub_items": [],
    },
    {
        "code": "RECREATION",
        "name_en": "Recreation",
        "name_zh": "娱乐文化消费",
        "raw_weight": 5.4,
        "series_id": "CPIRECSL",
        "sub_items": [],
    },
    {
        "code": "OTHER_SERV",
        "name_en": "Other goods & services",
        "name_zh": "其他商品与个人服务",
        "raw_weight": 2.8,
        "series_id": "CPIOGSSL",
        "sub_items": [],
    },
]

# Memo items for Table 1
US_CPI_MEMO = [
    {"code": "CORE_CPI", "name_en": "Core CPI (ex Food & Energy)", "name_zh": "核心 CPI (剔食品能源)", "raw_weight": 79.9, "series_id": "CPILFESL"},
    {"code": "SUPERCORE", "name_en": "Supercore Services (Services ex Rent of Shelter)", "name_zh": "超级核心通胀 (核心服务剔住房)", "raw_weight": 24.1, "series_id": "CUSR0000SASL2RS"},
    {"code": "CORE_PCE", "name_en": "Core PCE Price Index (Fed Target 2.0%)", "name_zh": "核心 PCE 物价指数 (美联储官定目标 2.0%)", "raw_weight": 82.5, "series_id": "PCEPILFE"},
    {"code": "MEDIAN_CPI", "name_en": "Cleveland Fed Median CPI", "name_zh": "克利夫兰联储加权中位数 CPI", "raw_weight": None, "series_id": "MEDCPIM158SFRBCLE"},
    {"code": "TRIMMED_PCE", "name_en": "Dallas Fed Trimmed Mean PCE", "name_zh": "达拉斯联储截尾均值 PCE", "raw_weight": None, "series_id": "PCETRIM12M159SFRBDAL"},
]

# PPI Final Demand & Intermediate Stages Structure
US_PPI_STRUCTURE = [
    {"code": "FD_GOODS", "name_en": "Final Demand Goods", "name_zh": "最终需求：商品出厂", "weight": 32.2, "series_id": "PPIDGS"},
    {"code": "FD_SERVICES", "name_en": "Final Demand Services", "name_zh": "最终需求：服务出厂", "weight": 64.6, "series_id": "PPIDSS"},
    {"code": "FD_CONST", "name_en": "Final Demand Construction", "name_zh": "最终需求：建筑营造", "weight": 3.2, "series_id": "PPIDCS"},
]

US_PPI_MEMO = [
    {"code": "INTERMEDIATE", "name_en": "Processed Goods for Intermediate Demand (Stage 4)", "name_zh": "中间需求加工品 (第4阶段生产资料)", "series_id": "PPIITM"},
    {"code": "COMMODITIES", "name_en": "PPI All Commodities (Raw & Bulk Inputs)", "name_zh": "全部初级大宗商品物价指数", "series_id": "PPIACO"},
]


def fetch_fred_series_data(series_id: str, session) -> dict[str, float]:
    """Fetch raw index observations from FRED and return {YYYY-MM: value}."""
    spec = {"series": series_id, "start_date": "2020-01-01"}
    try:
        res = fetch_fred(session, spec)
        obs = res.get("observations", [])
        out = {}
        for item in obs:
            d_str = str(item.get("date", ""))[:7]
            val = item.get("value")
            if d_str and val is not None:
                try:
                    out[d_str] = float(val)
                except (ValueError, TypeError):
                    pass
        return out
    except Exception as e:
        logging.warning(f"Error fetching FRED series {series_id}: {e}")
        return {}


def compute_rates(idx_dict: dict[str, float], dates: list[str]) -> tuple[dict[str, float], dict[str, float]]:
    """Compute YoY and MoM rates from index levels."""
    yoy_dict = {}
    mom_dict = {}
    for d in dates:
        dt = datetime.strptime(d, "%Y-%m")
        # Prev month
        p_m = dt.month - 1
        p_y = dt.year
        if p_m == 0:
            p_m = 12
            p_y -= 1
        prev_d = f"{p_y:04d}-{p_m:02d}"

        # 1Y ago month
        ago_d = f"{dt.year - 1:04d}-{dt.month:02d}"

        cur_v = idx_dict.get(d)
        prev_v = idx_dict.get(prev_d)
        ago_v = idx_dict.get(ago_d)

        if cur_v is not None and ago_v is not None and ago_v > 0:
            yoy_dict[d] = round((cur_v / ago_v - 1.0) * 100.0, 2)
        elif cur_v is not None and d in yoy_dict:
            pass  # keep if already rate

        if cur_v is not None and prev_v is not None and prev_v > 0:
            mom_dict[d] = round((cur_v / prev_v - 1.0) * 100.0, 2)

    return yoy_dict, mom_dict


def compute_annualized_momentum(mom_dict: dict[str, float], yoy_dict: dict[str, float], target_month: str) -> dict:
    """Compute 1M, 3M, 6M annualized rates and momentum gap vs 12M YoY."""
    dt = datetime.strptime(target_month, "%Y-%m")
    past_months = []
    for i in range(6):
        m = dt.month - i
        y = dt.year
        while m <= 0:
            m += 12
            y -= 1
        past_months.append(f"{y:04d}-{m:02d}")

    # 1. 1M Annualized
    m1 = mom_dict.get(past_months[0])
    ann_1m = round(((1.0 + m1 / 100.0) ** 12 - 1.0) * 100.0, 1) if m1 is not None else None

    # 2. 3M Annualized
    m3_vals = [mom_dict.get(past_months[i]) for i in range(3)]
    if all(v is not None for v in m3_vals):
        prod3 = 1.0
        for v in m3_vals:
            prod3 *= (1.0 + v / 100.0)
        ann_3m = round((prod3 ** 4 - 1.0) * 100.0, 1)
    else:
        ann_3m = None

    # 3. 6M Annualized
    m6_vals = [mom_dict.get(past_months[i]) for i in range(6)]
    if all(v is not None for v in m6_vals):
        prod6 = 1.0
        for v in m6_vals:
            prod6 *= (1.0 + v / 100.0)
        ann_6m = round((prod6 ** 2 - 1.0) * 100.0, 1)
    else:
        ann_6m = None

    # 4. 12M YoY & Gap
    yoy_val = yoy_dict.get(target_month)
    gap = round(ann_3m - yoy_val, 1) if (ann_3m is not None and yoy_val is not None) else None

    # 5. Signal classification
    if gap is not None:
        if gap > 1.0:
            signal = "reaccelerating"
            signal_en = "Re-accelerating"
            signal_zh = "显著再通胀"
            badge = "badge-squeeze"
            icon = "▲"
        elif gap >= 0.2:
            signal = "firm"
            signal_en = "Sticky / Firm"
            signal_zh = "粘性偏高"
            badge = "badge-neutral"
            icon = "△"
        elif gap >= -0.2:
            signal = "balanced"
            signal_en = "Balanced"
            signal_zh = "常态平稳"
            badge = "badge-neutral"
            icon = "▬"
        else:
            signal = "disinflating"
            signal_en = "Disinflating"
            signal_zh = "持续去通胀"
            badge = "badge-expand"
            icon = "▼"
    else:
        signal = "unknown"
        signal_en = "—"
        signal_zh = "—"
        badge = "badge-neutral"
        icon = "▬"

    return {
        "mom_1m_ann": ann_1m,
        "mom_3m_ann": ann_3m,
        "mom_6m_ann": ann_6m,
        "yoy": yoy_val,
        "gap": gap,
        "signal": signal,
        "signal_en": signal_en,
        "signal_zh": signal_zh,
        "badge": badge,
        "icon": icon,
    }


def enrich_us_inflation_deepdive():
    """Main execution engine for US inflation enrichment."""
    data_mode = os.environ.get("COUNTRY_PRIMER_DATA_MODE", "").lower()
    out_file = OUTPUT / "us_inflation_deepdive.json"

    if data_mode == "snapshot" and out_file.exists():
        logging.info("Snapshot mode active; using existing us_inflation_deepdive.json.")
        return

    import requests
    session = requests.Session()
    session.headers.update({"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"})

    # Normalized BLS relative importance weights
    sum_w = sum(cat["raw_weight"] for cat in US_CPI_STRUCTURE)
    norm_factor = 100.0 / sum_w

    weights_by_code = {}
    for cat in US_CPI_STRUCTURE:
        weights_by_code[cat["code"]] = round(cat["raw_weight"] * norm_factor, 1)
        for sub in cat.get("sub_items", []):
            weights_by_code[sub["code"]] = round(sub["raw_weight"] * norm_factor, 2)
    for m in US_CPI_MEMO:
        if m.get("raw_weight"):
            weights_by_code[m["code"]] = round(m["raw_weight"] * norm_factor, 1)

    logging.info("Fetching US CPI, PCE and PPI series from FRED...")
    series_cache = {}

    # All series to fetch
    all_sids = [
        "CPIAUCSL", "CPILFESL", "PCEPI", "PCEPILFE", "CUSR0000SASL2RS",
        "MEDCPIM158SFRBCLE", "PCETRIM12M159SFRBDAL",
        "CPIUFDSL", "CUSR0000SAF11", "CUSR0000SEFV",
        "CPIENGSL", "CUSR0000SACE", "CUSR0000SEHF",
        "CUSR0000SACL1E", "CPIAPPSL", "CUSR0000SETA01", "CUSR0000SETA02",
        "CUSR0000SAH1", "CUSR0000SEHA", "CUSR0000SEHC",
        "CUSR0000SAS4", "CUSR0000SAM2", "CPIEDUSL", "CPIRECSL", "CPIOGSSL",
        "PPIFIS", "PPIDGS", "PPIDSS", "PPIDCS", "PPIITM", "PPIACO",
        "MICH", "EXPINF5YR", "T5YIE", "T10YIE", "TCU"
    ]

    for sid in all_sids:
        series_cache[sid] = fetch_fred_series_data(sid, session)

    # Determine available months from Headline CPI
    head_obs = series_cache.get("CPIAUCSL", {})
    if not head_obs:
        logging.error("Failed to fetch CPIAUCSL from FRED. Aborting.")
        return

    all_months = sorted(list(head_obs.keys()), reverse=True)
    # Filter to recent 24 months
    target_months = [m for m in all_months if m >= "2024-01"][:24]

    # Precompute YoY and MoM for all series
    yoy_cache = {}
    mom_cache = {}
    for sid, idx_dict in series_cache.items():
        if sid in ["MEDCPIM158SFRBCLE", "PCETRIM12M159SFRBDAL", "MICH", "EXPINF5YR", "T5YIE", "T10YIE", "TCU"]:
            # Already rates/levels
            yoy_cache[sid] = idx_dict
            mom_cache[sid] = {}
        else:
            y, m = compute_rates(idx_dict, all_months)
            yoy_cache[sid] = y
            mom_cache[sid] = m

    # 1. Build Table 1 (CPI Breakdown) for each month
    cpi_tables = {}
    for m in target_months:
        dt = datetime.strptime(m, "%Y-%m")
        p_m = dt.month - 1
        p_y = dt.year
        if p_m == 0:
            p_m = 12
            p_y -= 1
        prev_m = f"{p_y:04d}-{p_m:02d}"
        ago_m = f"{dt.year - 1:04d}-{dt.month:02d}"

        h_yoy = yoy_cache.get("CPIAUCSL", {}).get(m)
        h_yoy_prev = yoy_cache.get("CPIAUCSL", {}).get(prev_m)
        h_mom = mom_cache.get("CPIAUCSL", {}).get(m)
        h_mom_ago = mom_cache.get("CPIAUCSL", {}).get(ago_m)

        if h_yoy is None or h_mom is None:
            continue

        items_data = []
        raw_cy = {}
        raw_cm = {}

        for cat in US_CPI_STRUCTURE:
            code = cat["code"]
            sid = cat["series_id"]
            w = weights_by_code.get(code, 0.0)
            y = yoy_cache.get(sid, {}).get(m)
            yp = yoy_cache.get(sid, {}).get(prev_m)
            mo = mom_cache.get(sid, {}).get(m)
            ma = mom_cache.get(sid, {}).get(ago_m)

            cy = (w / 100.0 * y) if y is not None else None
            cm = (w / 100.0 * mo) if mo is not None else None
            raw_cy[code] = cy
            raw_cm[code] = cm

            subs_data = []
            for sub in cat.get("sub_items", []):
                s_code = sub["code"]
                s_sid = sub["series_id"]
                s_w = weights_by_code.get(s_code, 0.0)
                s_y = yoy_cache.get(s_sid, {}).get(m)
                s_yp = yoy_cache.get(s_sid, {}).get(prev_m)
                s_mo = mom_cache.get(s_sid, {}).get(m)
                s_ma = mom_cache.get(s_sid, {}).get(ago_m)
                s_cy = (s_w / 100.0 * s_y) if s_y is not None else None
                s_cm = (s_w / 100.0 * s_mo) if s_mo is not None else None

                subs_data.append({
                    "code": s_code,
                    "name": sub["name_en"],
                    "name_zh": sub["name_zh"],
                    "weight": s_w,
                    "yoy": s_y,
                    "yoy_prev": s_yp,
                    "contrib_yoy": round(s_cy, 1) if s_cy is not None else None,
                    "mom": s_mo,
                    "mom_ago": s_ma,
                    "contrib_mom": round(s_cm, 1) if s_cm is not None else None,
                })

            items_data.append({
                "code": code,
                "name": cat["name_en"],
                "name_zh": cat["name_zh"],
                "weight": w,
                "yoy": y,
                "yoy_prev": yp,
                "raw_cy": cy,
                "mom": mo,
                "mom_ago": ma,
                "raw_cm": cm,
                "sub_items": subs_data,
            })

        # Adjust main items to sum exactly to headline
        tot_cy = sum(raw_cy.values())
        tot_cm = sum(raw_cm.values())
        diff_y = h_yoy - tot_cy
        diff_m = h_mom - tot_cm

        # Exact weight x rate; the gap to headline is not spread across components.
        for it in items_data:
            it["contrib_yoy"] = round(it["raw_cy"], 1) if it["raw_cy"] is not None else None
            it["contrib_mom"] = round(it["raw_cm"], 1) if it["raw_cm"] is not None else None
            del it["raw_cy"]
            del it["raw_cm"]

        memo_data = []
        for mem in US_CPI_MEMO:
            m_code = mem["code"]
            m_sid = mem["series_id"]
            m_w = weights_by_code.get(m_code)
            m_y = yoy_cache.get(m_sid, {}).get(m)
            m_yp = yoy_cache.get(m_sid, {}).get(prev_m)
            m_mo = mom_cache.get(m_sid, {}).get(m)
            m_ma = mom_cache.get(m_sid, {}).get(ago_m)

            memo_data.append({
                "code": m_code,
                "name": mem["name_en"],
                "name_zh": mem["name_zh"],
                "weight": m_w,
                "yoy": m_y,
                "yoy_prev": m_yp,
                "contrib_yoy": None,
                "mom": m_mo,
                "mom_ago": m_ma,
                "contrib_mom": None,
            })

        cpi_tables[m] = {
            "date": m,
            "prev_date": prev_m,
            "ago_date": ago_m,
            "headline": {
                "name": "Headline CPI",
                "yoy": h_yoy,
                "yoy_prev": h_yoy_prev,
                "contrib_yoy": None,
                "mom": h_mom,
                "mom_ago": h_mom_ago,
                "contrib_mom": h_mom,
            },
            "items": items_data,
            "memo": memo_data,
        }

    # 2. Build Momentum Monitor Tables (Last 12 Months)
    mom_mon_targets = [
        ("TOTAL", "Headline CPI", "整体居民 CPI", 100.0, "CPIAUCSL"),
        ("CPILFESL", "Core CPI (ex Food & Energy)", "核心 CPI (剔除食品能源)", weights_by_code["CORE_CPI"], "CPILFESL"),
        ("SUPERCORE", "Supercore Services (ex Shelter)", "超级核心通胀 (核心服务剔住房)", weights_by_code["SUPERCORE"], "CUSR0000SASL2RS"),
        ("PCEPILFE", "Core PCE Price Index", "核心 PCE 物价指数", weights_by_code["CORE_PCE"], "PCEPILFE"),
        ("SHELTER", "Shelter (Rent & OER)", "住房及业主等价租金", weights_by_code["SHELTER"], "CUSR0000SAH1"),
        ("TRANS_SERV", "Transportation Services", "交通运输服务", weights_by_code["TRANS_SERV"], "CUSR0000SAS4"),
        ("FOOD", "Food & Beverages", "食品与饮料", weights_by_code["FOOD"], "CPIUFDSL"),
        ("ENERGY", "Energy Commodities & Services", "能源商品与公用事业", weights_by_code["ENERGY"], "CPIENGSL"),
        ("CORE_GOODS", "Core Goods (Vehicles & Apparel)", "核心耐用品及商品", weights_by_code["CORE_GOODS"], "CUSR0000SACL1E"),
        ("MEDIAN_CPI", "Cleveland Fed Median CPI", "克利夫兰联储中位数 CPI", 100.0, "MEDCPIM158SFRBCLE"),
    ]

    mom_tables = {}
    for m in target_months[:12]:
        items_mom = []
        for code, name_en, name_zh, w, sid in mom_mon_targets:
            res = compute_annualized_momentum(mom_cache.get(sid, {}), yoy_cache.get(sid, {}), m)
            res["code"] = code
            res["name_en"] = name_en
            res["name_zh"] = name_zh
            res["weight"] = w
            items_mom.append(res)

        head_res = next((it for it in items_mom if it["code"] == "TOTAL"), {})
        core_res = next((it for it in items_mom if it["code"] == "CPILFESL"), {})

        mom_tables[m] = {
            "date": m,
            "headline_ann_3m": head_res.get("mom_3m_ann"),
            "headline_yoy": head_res.get("yoy"),
            "headline_gap": head_res.get("gap"),
            "headline_signal_en": head_res.get("signal_en", "Stable"),
            "headline_signal_zh": head_res.get("signal_zh", "常态平稳"),
            "core_ann_3m": core_res.get("mom_3m_ann"),
            "core_yoy": core_res.get("yoy"),
            "core_gap": core_res.get("gap"),
            "items": items_mom,
        }

    # 3. Build Table 2 (PPI Final Demand & Intermediate Stages)
    ppi_tables = {}
    for m in target_months:
        dt = datetime.strptime(m, "%Y-%m")
        p_m = dt.month - 1
        p_y = dt.year
        if p_m == 0:
            p_m = 12
            p_y -= 1
        prev_m = f"{p_y:04d}-{p_m:02d}"
        ago_m = f"{dt.year - 1:04d}-{dt.month:02d}"

        h_y = yoy_cache.get("PPIFIS", {}).get(m)
        h_yp = yoy_cache.get("PPIFIS", {}).get(prev_m)
        h_mo = mom_cache.get("PPIFIS", {}).get(m)
        h_ma = mom_cache.get("PPIFIS", {}).get(ago_m)

        if h_y is None or h_mo is None:
            continue

        items_ppi = []
        raw_p_cy = {}
        raw_p_cm = {}

        for p_row in US_PPI_STRUCTURE:
            code = p_row["code"]
            sid = p_row["series_id"]
            w = p_row["weight"]
            y = yoy_cache.get(sid, {}).get(m)
            yp = yoy_cache.get(sid, {}).get(prev_m)
            mo = mom_cache.get(sid, {}).get(m)
            ma = mom_cache.get(sid, {}).get(ago_m)

            cy = (w / 100.0 * y) if y is not None else None
            cm = (w / 100.0 * mo) if mo is not None else None
            raw_p_cy[code] = cy
            raw_p_cm[code] = cm

            items_ppi.append({
                "code": code,
                "name": p_row["name_en"],
                "name_zh": p_row["name_zh"],
                "weight": w,
                "yoy": y,
                "yoy_prev": yp,
                "raw_cy": cy,
                "mom": mo,
                "mom_ago": ma,
                "raw_cm": cm,
            })

        tot_p_cy = sum(v for v in raw_p_cy.values() if v is not None)
        tot_p_cm = sum(v for v in raw_p_cm.values() if v is not None)
        diff_p_y = h_y - tot_p_cy
        diff_p_m = h_mo - tot_p_cm

        for it in items_ppi:
            it["contrib_yoy"] = round(it["raw_cy"], 1) if it["raw_cy"] is not None else None
            it["contrib_mom"] = round(it["raw_cm"], 1) if it["raw_cm"] is not None else None
            del it["raw_cy"]
            del it["raw_cm"]

        memo_ppi = []
        for p_mem in US_PPI_MEMO:
            sid = p_mem["series_id"]
            memo_ppi.append({
                "code": p_mem["code"],
                "name": p_mem["name_en"],
                "name_zh": p_mem["name_zh"],
                "yoy": yoy_cache.get(sid, {}).get(m),
                "yoy_prev": yoy_cache.get(sid, {}).get(prev_m),
                "contrib_yoy": None,
                "mom": mom_cache.get(sid, {}).get(m),
                "mom_ago": mom_cache.get(sid, {}).get(ago_m),
                "contrib_mom": None,
            })

        ppi_tables[m] = {
            "date": m,
            "prev_date": prev_m,
            "ago_date": ago_m,
            "headline": {
                "name": "Headline PPI Final Demand",
                "yoy": h_y,
                "yoy_prev": h_yp,
                "contrib_yoy": None,
                "mom": h_mo,
                "mom_ago": h_ma,
                "contrib_mom": h_mo,
            },
            "items": items_ppi,
            "memo": memo_ppi,
        }

    # 4. Expectations Summary & Percentile Ranges
    exp_defs = [
        ("exp_michigan_1y", "Univ of Michigan 1Y Inflation Expectation", "密歇根大学 1Y 通胀预期", "%", "MICH", "👥"),
        ("exp_michigan_5y", "Univ of Michigan 5Y Inflation Expectation", "密歇根大学 5Y 远期通胀预期", "%", "EXPINF5YR", "🎯"),
        ("exp_tips_5y", "5Y TIPS Breakeven Inflation Rate", "5年期 TIPS 盈亏平衡通胀率", "%", "T5YIE", "📈"),
        ("exp_tips_10y", "10Y TIPS Breakeven Inflation Rate", "10年期 TIPS 盈亏平衡通胀率", "%", "T10YIE", "🏛️"),
        ("capacity_utilization", "Fed Total Capacity Utilization", "美联储工业产能利用率与瓶颈指数", "%", "TCU", "⚙️"),
    ]

    exp_summary = {}
    for key, name_en, name_zh, unit, sid, icon in exp_defs:
        s_dict = series_cache.get(sid, {})
        # Filter to 2022-2026 for percentile
        recent_vals = [v for d, v in s_dict.items() if d >= "2022-01"]
        if not recent_vals:
            continue
        cur_d = max(s_dict.keys())
        cur_v = s_dict[cur_d]

        # 3M ago
        dt = datetime.strptime(cur_d, "%Y-%m")
        m3 = dt.month - 3
        y3 = dt.year
        if m3 <= 0:
            m3 += 12
            y3 -= 1
        d_3m = f"{y3:04d}-{m3:02d}"
        v_3m = s_dict.get(d_3m, cur_v)
        diff_3m = round(cur_v - v_3m, 2)

        min_v = min(recent_vals)
        max_v = max(recent_vals)
        pct = int(round((cur_v - min_v) / (max_v - min_v) * 100)) if max_v > min_v else None
        pct = max(0, min(100, pct)) if pct is not None else None

        if key == "capacity_utilization":
            regime_en = "Bottleneck Alert" if cur_v >= 80.0 else ("Tight / Full" if cur_v >= 77.5 else "Slack / Spare Capacity")
            regime_zh = "存在产能瓶颈溢价" if cur_v >= 80.0 else ("产能紧平衡" if cur_v >= 77.5 else "供给产能充裕")
            takeaway_en = f"Operating at {cur_v:.1f}% ({pct}th percentile). {'Supply constraints enhance manufacturer pricing power.' if cur_v >= 78.0 else 'Spare capacity restrains upstream goods pass-through.'}"
            takeaway_zh = f"当前处于 {cur_v:.1f}%（历史 {pct}% 分位）。{'工业产线紧俏增强企业成本转嫁溢价底气。' if cur_v >= 78.0 else '富余产能有效平抑上游向消费端的顺风涨价。'}"
        elif "tips" in key:
            regime_en = "Anchored" if cur_v <= 2.3 else ("Firm Pricing" if cur_v <= 2.6 else "De-anchoring Risk")
            regime_zh = "稳固锚定" if cur_v <= 2.3 else ("中枢偏高" if cur_v <= 2.6 else "脱锚预警")
            takeaway_en = f"TIPS pricing at {cur_v:.2f}% ({pct}th percentile). {'Market breakevens well anchored near Fed 2% target.' if cur_v <= 2.4 else 'Elevated term premium reflects persistent inflation hedging.'}"
            takeaway_zh = f"国债隐含通胀率 {cur_v:.2f}%（历史 {pct}% 分位）。{'金融衍生品定价牢牢锚定美联储2%长期中枢。' if cur_v <= 2.4 else '期限溢价高企反映机构防范二次通胀风险。'}"
        else:
            regime_en = "Cooling" if diff_3m < -0.3 else ("Sticky Plateau" if diff_3m <= 0.3 else "Re-heating")
            regime_zh = "预期回落" if diff_3m < -0.3 else ("粘性高台" if diff_3m <= 0.3 else "预期升温")
            takeaway_en = f"Consumer survey reads {cur_v:.1f}% ({pct}th percentile, 3M Δ {diff_3m:+.1f} pts). Household expectations remain sticky."
            takeaway_zh = f"居民调查读数 {cur_v:.1f}%（历史 {pct}% 分位，3个月变化 {diff_3m:+.1f}）。家庭端通胀心理预期仍有一定黏性。"

        exp_summary[key] = {
            "key": key,
            "label_en": name_en,
            "label_zh": name_zh,
            "unit": unit,
            "icon": icon,
            "current": cur_v,
            "prev_3m": v_3m,
            "diff_3m": diff_3m,
            "min": round(min_v, 1),
            "max": round(max_v, 1),
            "pct": pct,
            "regime_en": regime_en,
            "regime_zh": regime_zh,
            "takeaway_en": takeaway_en,
            "takeaway_zh": takeaway_zh,
        }

    # 5. Continuous Time Series (2022–2026) for Interactive Charts
    chart_dates = sorted([d for d in all_months if d >= "2022-01"])

    ts_data = {
        # Stacked Contributions
        "cpi_contrib_food_yoy": [],
        "cpi_contrib_energy_yoy": [],
        "cpi_contrib_shelter_yoy": [],
        "cpi_contrib_core_ex_shelter_yoy": [],
        # Momentum Trajectory
        "cpi_head_3m_ann": [],
        "cpi_head_12m_yoy": [],
        "cpi_core_3m_ann": [],
        "cpi_core_12m_yoy": [],
        "cpi_supercore_3m_ann": [],
        # Scissors Gap
        "ppi_cpi_scissors_gap": [],
        "ppi_final_demand_yoy": [],
        "cpi_headline_yoy": [],
        # Expectations Multi-Track
        "exp_michigan_1y": [],
        "exp_michigan_5y": [],
        "exp_tips_5y": [],
        "exp_tips_10y": [],
        "capacity_utilization": [],
    }

    for d in chart_dates:
        # Stacked components
        y_food = yoy_cache.get("CPIUFDSL", {}).get(d)
        y_energy = yoy_cache.get("CPIENGSL", {}).get(d)
        y_shelter = yoy_cache.get("CUSR0000SAH1", {}).get(d)
        y_core_goods = yoy_cache.get("CUSR0000SACL1E", {}).get(d)
        y_trans = yoy_cache.get("CUSR0000SAS4", {}).get(d)
        y_med = yoy_cache.get("CUSR0000SAM2", {}).get(d)
        y_other = yoy_cache.get("CPIOGSSL", {}).get(d)
        if None not in (y_food, y_energy, y_shelter, y_core_goods, y_trans, y_med, y_other):
            # A missing component month is a gap, not a zero contribution.

            c_food = round(weights_by_code["FOOD"] / 100.0 * y_food, 2)
            c_energy = round(weights_by_code["ENERGY"] / 100.0 * y_energy, 2)
            c_shelter = round(weights_by_code["SHELTER"] / 100.0 * y_shelter, 2)
            c_core_ex = round((weights_by_code["CORE_GOODS"] * y_core_goods +
                               weights_by_code["TRANS_SERV"] * y_trans +
                               weights_by_code["MED_SERV"] * y_med +
                               weights_by_code["OTHER_SERV"] * y_other) / 100.0, 2)

            ts_data["cpi_contrib_food_yoy"].append({"date": d, "value": c_food})
            ts_data["cpi_contrib_energy_yoy"].append({"date": d, "value": c_energy})
            ts_data["cpi_contrib_shelter_yoy"].append({"date": d, "value": c_shelter})
            ts_data["cpi_contrib_core_ex_shelter_yoy"].append({"date": d, "value": c_core_ex})

        # Momentum
        m_head = compute_annualized_momentum(mom_cache.get("CPIAUCSL", {}), yoy_cache.get("CPIAUCSL", {}), d)
        m_core = compute_annualized_momentum(mom_cache.get("CPILFESL", {}), yoy_cache.get("CPILFESL", {}), d)
        m_super = compute_annualized_momentum(mom_cache.get("CUSR0000SASL2RS", {}), yoy_cache.get("CUSR0000SASL2RS", {}), d)

        if m_head.get("mom_3m_ann") is not None:
            ts_data["cpi_head_3m_ann"].append({"date": d, "value": m_head["mom_3m_ann"]})
        if m_head.get("yoy") is not None:
            ts_data["cpi_head_12m_yoy"].append({"date": d, "value": m_head["yoy"]})
        if m_core.get("mom_3m_ann") is not None:
            ts_data["cpi_core_3m_ann"].append({"date": d, "value": m_core["mom_3m_ann"]})
        if m_core.get("yoy") is not None:
            ts_data["cpi_core_12m_yoy"].append({"date": d, "value": m_core["yoy"]})
        if m_super.get("mom_3m_ann") is not None:
            ts_data["cpi_supercore_3m_ann"].append({"date": d, "value": m_super["mom_3m_ann"]})

        # Scissors gap
        y_ppi = yoy_cache.get("PPIFIS", {}).get(d)
        y_cpi = yoy_cache.get("CPIAUCSL", {}).get(d)
        if y_ppi is not None and y_cpi is not None:
            ts_data["ppi_final_demand_yoy"].append({"date": d, "value": y_ppi})
            ts_data["cpi_headline_yoy"].append({"date": d, "value": y_cpi})
            ts_data["ppi_cpi_scissors_gap"].append({"date": d, "value": round(y_ppi - y_cpi, 2)})

        # Expectations
        if d in series_cache.get("MICH", {}):
            ts_data["exp_michigan_1y"].append({"date": d, "value": series_cache["MICH"][d]})
        if d in series_cache.get("EXPINF5YR", {}):
            ts_data["exp_michigan_5y"].append({"date": d, "value": series_cache["EXPINF5YR"][d]})
        if d in series_cache.get("T5YIE", {}):
            ts_data["exp_tips_5y"].append({"date": d, "value": series_cache["T5YIE"][d]})
        if d in series_cache.get("T10YIE", {}):
            ts_data["exp_tips_10y"].append({"date": d, "value": series_cache["T10YIE"][d]})
        if d in series_cache.get("TCU", {}):
            ts_data["capacity_utilization"].append({"date": d, "value": series_cache["TCU"][d]})

    out_payload = {
        "country": "US",
        "currency": "USD",
        "updated_at": datetime.now().isoformat(),
        "weights": weights_by_code,
        "cpi_tables": cpi_tables,
        "momentum_tables": mom_tables,
        "ppi_tables": ppi_tables,
        "expectations_summary": exp_summary,
        "time_series": ts_data,
    }

    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(out_payload, f, indent=2, ensure_ascii=False)
    logging.info(f"Successfully generated US Inflation Deepdive: {out_file} ({out_file.stat().st_size:,} bytes).")


if __name__ == "__main__":
    enrich_us_inflation_deepdive()
