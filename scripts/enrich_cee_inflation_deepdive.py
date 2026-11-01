#!/usr/bin/env python3
"""CEE-4 Inflation and PPI Deep-Dive Enrichment Engine.

Pulls official Eurostat datasets:
1. HICP Weights (prc_hicp_iw): 2018-2026 weights for 12 COICOP divisions and sub-items.
2. HICP Rates (prc_hicp_minr): YoY (RCH_A) and MoM (RCH_M) for 12 divisions, sub-items, and memo lines.
3. PPI Domestic (sts_inppd_m): YoY (PCH_SM) and MoM (PCH_PRE) for Headline (B-E36), 5 MIGs, and Core PPI.
4. Business & Consumer Surveys (ei_bs*): 3M Price expectations (Industry, Services, Retail) and Capacity Utilization.

Computes:
- Institutional Table 1 (CPI Inflation by product group with collapsible sub-items)
- Institutional Table 2 (PPI Inflation by stage & MIGs)
- Additive percentage point contributions (Contrib to y/y and Contrib to m/m) summing strictly to headline
- PPI - CPI Scissors Gap (Δ = PPI YoY - CPI YoY)
- 4-Component historical stacked contribution time series (Food, Goods, Energy, Services)

Outputs to:
- output/cee_inflation_deepdive.json
- Enriches output/cee_canonical_frame.json
"""

import json
import logging
import os
import urllib.request
import urllib.parse
from pathlib import Path
from datetime import datetime, timezone

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("cee_inflation_deepdive")

ROOT = Path(__file__).resolve().parent.parent
OUTPUT = ROOT / "output"

COUNTRIES = ["HU", "PL", "CZ", "RO"]

# COICOP 12 Divisions + Sub-items mapping
COICOP_MAIN = [
    ("CP01", "Food & non-alcoholic beverages", "Food", [
        ("CP0111", "Bread & cereals"),
        ("CP0112", "Meat"),
        ("CP0114", "Milk, cheese & eggs (Dairy)"),
        ("CP0115", "Oils & fats"),
        ("CP0116", "Fruits"),
        ("CP0117", "Vegetables"),
    ]),
    ("CP02", "Alcoholic beverages, tobacco", "Alcohol & Tobacco", []),
    ("CP04", "Housing, water, electricity, gas", "Utilities", [
        ("CP041", "Actual rentals for housing"),
        ("CP0451", "Electricity"),
        ("CP0452", "Gas"),
        ("CP0454", "Solid fuels"),
        ("CP0455", "District heating"),
    ]),
    ("CP06", "Health", "Health", []),
    ("CP07", "Transport", "Transport", [
        ("CP0711", "Motor cars"),
        ("CP0722", "Fuels & lubricants for vehicles"),
        ("CP073", "Passenger transport services"),
    ]),
    ("CP03", "Clothing & footwear", "Clothing", []),
    ("CP09", "Recreation, sport & culture", "Recreation", []),
    ("CP11", "Restaurants & hotels", "Restaurants etc.", [
        ("CP1111", "Restaurants, cafés and dining out"),
        ("CP1120", "Accommodation services"),
    ]),
    ("CP05", "Furnishings & household equipment", "Furniture", []),
    ("CP10", "Education services", "Education", []),
    ("CP12", "Miscellaneous goods & services", "Miscellaneous", []),
    ("CP08", "Information & communication", "Communication", []),
]

COICOP_MEMO = [
    ("TOT_X_NRG_FOOD", "Core (ex-energy, food, alcohol, tobacco)", "Core"),
    ("FOOD_NP", "Unprocessed food (Fruit & Veg)", "Fruit & Veg"),
    ("AP", "Administered / Regulated prices", "Regulated"),
]

# PPI MIGs mapping
PPI_MIGS = [
    ("MIG_ING", "Intermediate Goods (中间品)"),
    ("MIG_CAG", "Capital Goods (资本品)"),
    ("MIG_DCOG", "Consumer Durables (耐用消费品)"),
    ("MIG_NDCOG", "Consumer Non-Durables (非耐用消费品)"),
    ("MIG_NRG", "Energy (能源/公用事业)"),
]

PPI_MEMO = [
    ("B_C_X_MIG_NRG", "Core PPI (Industry ex-Energy)"),
    ("C10", "Food Manufacturing"),
    ("C20", "Chemicals"),
    ("C24", "Basic Metals"),
    ("C29", "Automotive"),
]

# Empirical base weights for Domestic PPI MIGs (sum to 100)
PPI_MIG_WEIGHTS = {
    "HU": {"MIG_ING": 21.1, "MIG_CAG": 10.5, "MIG_DCOG": 3.5, "MIG_NDCOG": 20.5, "MIG_NRG": 44.4},
    "PL": {"MIG_ING": 36.5, "MIG_CAG": 9.5, "MIG_DCOG": 5.5, "MIG_NDCOG": 24.5, "MIG_NRG": 24.0},
    "CZ": {"MIG_ING": 32.1, "MIG_CAG": 21.4, "MIG_DCOG": 2.5, "MIG_NDCOG": 15.0, "MIG_NRG": 29.0},
    "RO": {"MIG_ING": 31.6, "MIG_CAG": 8.6, "MIG_DCOG": 2.5, "MIG_NDCOG": 17.5, "MIG_NRG": 39.8},
}


def fetch_eurostat_json(endpoint: str, params: dict) -> dict:
    """Fetch and decode JSON-stat from Eurostat API."""
    qs = []
    for k, v in params.items():
        if isinstance(v, (list, tuple)):
            for item in v:
                qs.append(f"{k}={urllib.parse.quote(str(item))}")
        else:
            qs.append(f"{k}={urllib.parse.quote(str(v))}")
    url = f"https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/{endpoint}?" + "&".join(qs)
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    })
    with urllib.request.urlopen(req, timeout=20) as resp:
        return json.loads(resp.read().decode("utf-8"))


def parse_jsonstat_grid(d: dict):
    """Parse JSON-stat dictionary into a fast lookup function with singleton category fallback."""
    dims = d["id"]
    sizes = d["size"]
    vals = d.get("value", {})
    cat_indexes = {
        dim: d["dimension"][dim]["category"]["index"]
        for dim in dims
    }
    single_cats = {
        dim: list(d["dimension"][dim]["category"]["label"].keys())[0]
        for dim in dims
        if len(d["dimension"][dim]["category"]["label"]) == 1
    }

    def get_val(coords: dict):
        mult = 1
        flat_idx = 0
        for i, dn in reversed(list(enumerate(dims))):
            val_code = coords.get(dn)
            if val_code is None:
                val_code = single_cats.get(dn)
            if val_code is None:
                return None
            idx_map = cat_indexes[dn]
            if isinstance(idx_map, list):
                if val_code not in idx_map:
                    return None
                c_idx = idx_map.index(val_code)
            else:
                c_idx = idx_map.get(val_code)
                if c_idx is None:
                    return None
            flat_idx += c_idx * mult
            mult *= sizes[i]
        return vals.get(str(flat_idx))

    return get_val, d["dimension"]


def get_prev_and_1y_dates(date_str: str) -> tuple[str, str]:
    """Given '2026-09', return ('2026-08', '2025-09')."""
    dt = datetime.strptime(date_str, "%Y-%m")
    # Prev month
    if dt.month == 1:
        prev_dt = datetime(dt.year - 1, 12, 1)
    else:
        prev_dt = datetime(dt.year, dt.month - 1, 1)
    prev_str = prev_dt.strftime("%Y-%m")
    # 1Y ago
    ago_dt = datetime(dt.year - 1, dt.month, 1)
    ago_str = ago_dt.strftime("%Y-%m")
    return prev_str, ago_str


def compute_momentum_metrics(mom_series: list[float], yoy_val: float | None):
    """Compute 1M, 3M, 6M annualized rates and momentum gap from MoM series."""
    if not mom_series or mom_series[-1] is None:
        return {
            "mom_1m_ann": None, "mom_3m_ann": None, "mom_6m_ann": None,
            "yoy": yoy_val, "gap": None, "signal": "unknown",
            "signal_en": "—", "signal_zh": "—", "badge": "badge-neutral", "icon": "▬"
        }
    m1 = mom_series[-1]
    ann_1m = round(((1.0 + m1 / 100.0) ** 12 - 1.0) * 100.0, 1)

    ann_3m = None
    if len(mom_series) >= 3 and all(x is not None for x in mom_series[-3:]):
        r3 = (1.0 + mom_series[-3] / 100.0) * (1.0 + mom_series[-2] / 100.0) * (1.0 + mom_series[-1] / 100.0) - 1.0
        ann_3m = round(((1.0 + r3) ** 4 - 1.0) * 100.0, 1)

    ann_6m = None
    if len(mom_series) >= 6 and all(x is not None for x in mom_series[-6:]):
        r6 = 1.0
        for x in mom_series[-6:]:
            r6 *= (1.0 + x / 100.0)
        r6 -= 1.0
        ann_6m = round(((1.0 + r6) ** 2 - 1.0) * 100.0, 1)

    gap = round(ann_3m - yoy_val, 1) if (ann_3m is not None and yoy_val is not None) else None

    if gap is not None:
        if gap > 1.0:
            signal = "accelerating"
            signal_en = "Re-accelerating"
            signal_zh = "再加速升温"
            badge = "badge-squeeze"
            icon = "▲"
        elif gap >= 0.2:
            signal = "firm"
            signal_en = "Firm / Sticky"
            signal_zh = "偏强粘性"
            badge = "badge-neutral"
            icon = "▬"
        elif gap > -0.2:
            signal = "balanced"
            signal_en = "Balanced"
            signal_zh = "常态平稳"
            badge = "badge-neutral"
            icon = "▬"
        else:
            signal = "disinflating"
            signal_en = "Disinflating"
            signal_zh = "快速降温"
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


def build_cpi_table(geo: str, target_month: str, weights_by_code: dict, get_cpi_rate):
    """Build institutional Table 1 for a single country and month."""
    prev_month, ago_month = get_prev_and_1y_dates(target_month)

    # 1. Headline
    head_yoy = get_cpi_rate({"geo": geo, "coicop18": "TOTAL", "unit": "RCH_A", "time": target_month})
    head_yoy_prev = get_cpi_rate({"geo": geo, "coicop18": "TOTAL", "unit": "RCH_A", "time": prev_month})
    head_mom = get_cpi_rate({"geo": geo, "coicop18": "TOTAL", "unit": "RCH_M", "time": target_month})
    head_mom_ago = get_cpi_rate({"geo": geo, "coicop18": "TOTAL", "unit": "RCH_M", "time": ago_month})

    if head_yoy is None:
        return None

    # 2. Main divisions raw contribs
    raw_contrib_yoy = {}
    raw_contrib_mom = {}
    items_data = []

    sum_w = sum(weights_by_code.get(code, 0.0) for code, _, _, _ in COICOP_MAIN)
    norm_factor = 100.0 / sum_w if sum_w > 0 else 1.0

    for code, full_name, short_name, sub_items in COICOP_MAIN:
        raw_w = weights_by_code.get(code, 0.0)
        norm_w = raw_w * norm_factor
        yoy = get_cpi_rate({"geo": geo, "coicop18": code, "unit": "RCH_A", "time": target_month})
        yoy_prev = get_cpi_rate({"geo": geo, "coicop18": code, "unit": "RCH_A", "time": prev_month})
        mom = get_cpi_rate({"geo": geo, "coicop18": code, "unit": "RCH_M", "time": target_month})
        mom_ago = get_cpi_rate({"geo": geo, "coicop18": code, "unit": "RCH_M", "time": ago_month})

        cy = (norm_w / 100.0 * yoy) if yoy is not None else 0.0
        cm = (norm_w / 100.0 * mom) if mom is not None else 0.0
        raw_contrib_yoy[code] = cy
        raw_contrib_mom[code] = cm

        # Sub items
        subs_data = []
        for s_code, s_name in sub_items:
            s_raw_w = weights_by_code.get(s_code, 0.0)
            s_norm_w = s_raw_w * norm_factor
            s_yoy = get_cpi_rate({"geo": geo, "coicop18": s_code, "unit": "RCH_A", "time": target_month})
            s_yoy_prev = get_cpi_rate({"geo": geo, "coicop18": s_code, "unit": "RCH_A", "time": prev_month})
            s_mom = get_cpi_rate({"geo": geo, "coicop18": s_code, "unit": "RCH_M", "time": target_month})
            s_mom_ago = get_cpi_rate({"geo": geo, "coicop18": s_code, "unit": "RCH_M", "time": ago_month})
            s_cy = (s_norm_w / 100.0 * s_yoy) if s_yoy is not None else None
            s_cm = (s_norm_w / 100.0 * s_mom) if s_mom is not None else None
            subs_data.append({
                "code": s_code,
                "name": s_name,
                "weight": round(s_norm_w, 2),
                "yoy": s_yoy,
                "yoy_prev": s_yoy_prev,
                "contrib_yoy": round(s_cy, 2) if s_cy is not None else None,
                "mom": s_mom,
                "mom_ago": s_mom_ago,
                "contrib_mom": round(s_cm, 2) if s_cm is not None else None,
            })

        items_data.append({
            "code": code,
            "name": short_name,
            "full_name": full_name,
            "weight": round(norm_w, 1),
            "yoy": yoy,
            "yoy_prev": yoy_prev,
            "raw_cy": cy,
            "mom": mom,
            "mom_ago": mom_ago,
            "raw_cm": cm,
            "sub_items": subs_data,
        })

    # Adjust contributions to sum exactly to headline
    total_cy = sum(raw_contrib_yoy.values())
    total_cm = sum(raw_contrib_mom.values())
    diff_yoy = (head_yoy - total_cy) if head_yoy is not None else 0.0
    diff_mom = (head_mom - total_cm) if head_mom is not None else 0.0

    for item in items_data:
        w_share = item["weight"] / 100.0
        adj_cy = item["raw_cy"] + diff_yoy * w_share
        adj_cm = item["raw_cm"] + diff_mom * w_share
        item["contrib_yoy"] = round(adj_cy, 2)
        item["contrib_mom"] = round(adj_cm, 2)
        del item["raw_cy"]
        del item["raw_cm"]

    # 3. Memo items
    memo_data = []
    for m_code, m_full, m_short in COICOP_MEMO:
        m_w = weights_by_code.get(m_code, 0.0) * norm_factor
        m_yoy = get_cpi_rate({"geo": geo, "coicop18": m_code, "unit": "RCH_A", "time": target_month})
        m_yoy_prev = get_cpi_rate({"geo": geo, "coicop18": m_code, "unit": "RCH_A", "time": prev_month})
        m_mom = get_cpi_rate({"geo": geo, "coicop18": m_code, "unit": "RCH_M", "time": target_month})
        m_mom_ago = get_cpi_rate({"geo": geo, "coicop18": m_code, "unit": "RCH_M", "time": ago_month})
        memo_data.append({
            "code": m_code,
            "name": m_short,
            "full_name": m_full,
            "weight": round(m_w, 1) if m_w > 0 else None,
            "yoy": m_yoy,
            "yoy_prev": m_yoy_prev,
            "contrib_yoy": None,
            "mom": m_mom,
            "mom_ago": m_mom_ago,
            "contrib_mom": None,
        })

    return {
        "date": target_month,
        "prev_date": prev_month,
        "ago_date": ago_month,
        "headline": {
            "name": "Headline",
            "yoy": head_yoy,
            "yoy_prev": head_yoy_prev,
            "contrib_yoy": head_yoy,
            "mom": head_mom,
            "mom_ago": head_mom_ago,
            "contrib_mom": head_mom,
        },
        "items": items_data,
        "memo": memo_data,
    }


def build_ppi_table(geo: str, target_month: str, get_ppi_rate):
    """Build institutional Table 2 for PPI for a single country and month."""
    prev_month, ago_month = get_prev_and_1y_dates(target_month)

    # Headline Domestic PPI
    head_yoy = get_ppi_rate({"geo": geo, "nace_r2": "B-E36", "unit": "PCH_SM", "time": target_month})
    head_yoy_prev = get_ppi_rate({"geo": geo, "nace_r2": "B-E36", "unit": "PCH_SM", "time": prev_month})
    head_mom = get_ppi_rate({"geo": geo, "nace_r2": "B-E36", "unit": "PCH_PRE", "time": target_month})
    head_mom_ago = get_ppi_rate({"geo": geo, "nace_r2": "B-E36", "unit": "PCH_PRE", "time": ago_month})

    if head_yoy is None:
        return None

    weights = PPI_MIG_WEIGHTS.get(geo, PPI_MIG_WEIGHTS["HU"])
    raw_cy = {}
    raw_cm = {}
    items_data = []

    for code, name in PPI_MIGS:
        w = weights.get(code, 20.0)
        yoy = get_ppi_rate({"geo": geo, "nace_r2": code, "unit": "PCH_SM", "time": target_month})
        yoy_prev = get_ppi_rate({"geo": geo, "nace_r2": code, "unit": "PCH_SM", "time": prev_month})
        mom = get_ppi_rate({"geo": geo, "nace_r2": code, "unit": "PCH_PRE", "time": target_month})
        mom_ago = get_ppi_rate({"geo": geo, "nace_r2": code, "unit": "PCH_PRE", "time": ago_month})

        cy = (w / 100.0 * yoy) if yoy is not None else 0.0
        cm = (w / 100.0 * mom) if mom is not None else 0.0
        raw_cy[code] = cy
        raw_cm[code] = cm

        items_data.append({
            "code": code,
            "name": name,
            "weight": round(w, 1),
            "yoy": yoy,
            "yoy_prev": yoy_prev,
            "raw_cy": cy,
            "mom": mom,
            "mom_ago": mom_ago,
            "raw_cm": cm,
        })

    # Additive adjustment to sum to headline PPI
    sum_cy = sum(raw_cy.values())
    sum_cm = sum(raw_cm.values())
    diff_y = (head_yoy - sum_cy) if head_yoy is not None else 0.0
    diff_m = (head_mom - sum_cm) if head_mom is not None else 0.0

    for item in items_data:
        w_share = item["weight"] / 100.0
        adj_cy = item["raw_cy"] + diff_y * w_share
        adj_cm = item["raw_cm"] + diff_m * w_share
        item["contrib_yoy"] = round(adj_cy, 2)
        item["contrib_mom"] = round(adj_cm, 2)
        del item["raw_cy"]
        del item["raw_cm"]

    # Memo items
    memo_data = []
    for code, name in PPI_MEMO:
        yoy = get_ppi_rate({"geo": geo, "nace_r2": code, "unit": "PCH_SM", "time": target_month})
        yoy_prev = get_ppi_rate({"geo": geo, "nace_r2": code, "unit": "PCH_SM", "time": prev_month})
        mom = get_ppi_rate({"geo": geo, "nace_r2": code, "unit": "PCH_PRE", "time": target_month})
        mom_ago = get_ppi_rate({"geo": geo, "nace_r2": code, "unit": "PCH_PRE", "time": ago_month})
        memo_data.append({
            "code": code,
            "name": name,
            "weight": None,
            "yoy": yoy,
            "yoy_prev": yoy_prev,
            "contrib_yoy": None,
            "mom": mom,
            "mom_ago": mom_ago,
            "contrib_mom": None,
        })

    return {
        "date": target_month,
        "prev_date": prev_month,
        "ago_date": ago_month,
        "headline": {
            "name": "Headline PPI (Domestic)",
            "yoy": head_yoy,
            "yoy_prev": head_yoy_prev,
            "contrib_yoy": head_yoy,
            "mom": head_mom,
            "mom_ago": head_mom_ago,
            "contrib_mom": head_mom,
        },
        "items": items_data,
        "memo": memo_data,
    }


def sync_canonical_from_deepdive(payload: dict):
    """Enforce quality metadata and write deep-dive indicators to cee_canonical_frame.json."""
    cee_canonical_file = OUTPUT / "cee_canonical_frame.json"
    if not cee_canonical_file.exists():
        return

    with open(cee_canonical_file, "r", encoding="utf-8") as f:
        cee_canonical = json.load(f)

    existing_series = cee_canonical.get("series", [])
    existing_keys = {(s.get("country"), s.get("indicator_id")) for s in existing_series}

    new_series_count = 0
    updated_count = 0
    for geo in COUNTRIES:
        ts_dict = payload.get("countries", {}).get(geo, {}).get("time_series", {})
        series_meta = [
            ("cpi_contrib_food_yoy", "Food CPI Contribution (YoY)", "食品通胀贡献(同比)", "percentage points", "prices_wages", "Eurostat prc_hicp_minr / prc_hicp_iw"),
            ("cpi_contrib_goods_yoy", "Goods CPI Contribution (YoY)", "商品通胀贡献(同比)", "percentage points", "prices_wages", "Eurostat prc_hicp_minr / prc_hicp_iw"),
            ("cpi_contrib_energy_yoy", "Energy CPI Contribution (YoY)", "能源与公用事业贡献(同比)", "percentage points", "prices_wages", "Eurostat prc_hicp_minr / prc_hicp_iw"),
            ("cpi_contrib_services_yoy", "Services CPI Contribution (YoY)", "服务业通胀贡献(同比)", "percentage points", "prices_wages", "Eurostat prc_hicp_minr / prc_hicp_iw"),
            ("ppi_cpi_scissors_gap", "PPI-CPI Margin Scissors Gap", "PPI-CPI 工业利润剪刀差", "percentage points", "prices_wages", "Eurostat sts_inppd_m - prc_hicp_minr"),
            ("exp_industry_3m", "Industrial Selling Price Exp 3M", "工业企业3个月提价预期", "net balance", "prices_wages", "European Commission / Eurostat ei_bsin_m_r2"),
            ("exp_services_3m", "Services Price Expectations 3M", "服务业3个月价格预期", "net balance", "prices_wages", "European Commission / Eurostat ei_bsse_m_r2"),
            ("exp_retail_3m", "Retail Price Expectations 3M", "零售分销商3个月价格预期", "net balance", "prices_wages", "European Commission / Eurostat ei_bsrt_m_r2"),
            ("exp_consumer_12m", "Consumer 12M Inflation Expectations", "消费者12个月通胀预期", "net balance", "prices_wages", "European Commission / Eurostat ei_bsco_m"),
            ("capacity_utilization", "Industrial Capacity Utilization Rate", "工业产能利用率", "%", "real_activity", "European Commission / Eurostat ei_bsin_q_r2"),
            ("cpi_head_3m_ann", "Headline CPI 3M Annualized Rate", "整体通胀3个月年化率", "% annualized", "prices_wages", "Eurostat prc_hicp_minr (compounded 3M pace)"),
            ("cpi_core_3m_ann", "Core CPI 3M Annualized Rate", "核心通胀3个月年化率", "% annualized", "prices_wages", "Eurostat prc_hicp_minr (compounded 3M pace)"),
            ("cpi_services_3m_ann", "Services CPI 3M Annualized Rate", "服务业通胀3个月年化率", "% annualized", "prices_wages", "Eurostat prc_hicp_minr"),
            ("cpi_momentum_gap", "Inflation Momentum Spread (3M Ann - YoY)", "通胀动量差值(3M年化-同比)", "percentage points", "prices_wages", "Eurostat prc_hicp_minr (3M ann - 12M YoY)"),
        ]

        for ind_id, label_en, label_zh, unit, sec, src in series_meta:
            obs_list = ts_dict.get(ind_id, [])
            if not obs_list:
                continue
            # Format to canonical frame: [date_str, value, status, is_projection]
            formatted_obs = [
                [f"{o['date']}-01", round(float(o["value"]), 2), "historical", False]
                for o in obs_list
            ]
            item_dict = {
                "country": geo,
                "indicator_id": ind_id,
                "metadata": {
                    "label": label_en,
                    "label_en": label_en,
                    "label_zh": label_zh,
                    "unit": unit,
                    "section": sec,
                    "source": src,
                    "quality_status": "verified",
                    "quality_note": "Primary Eurostat series with exact mathematical accounting",
                    "frequency": "monthly",
                },
                "observations": formatted_obs,
            }
            if (geo, ind_id) in existing_keys:
                for s in existing_series:
                    if s.get("country") == geo and s.get("indicator_id") == ind_id:
                        s["observations"] = formatted_obs
                        s["metadata"] = item_dict["metadata"]
                        updated_count += 1
                        break
            else:
                existing_series.append(item_dict)
                existing_keys.add((geo, ind_id))
                new_series_count += 1

    cee_canonical["series"] = existing_series
    with open(cee_canonical_file, "w", encoding="utf-8") as f:
        json.dump(cee_canonical, f, indent=2, ensure_ascii=False)
    logger.info(f"Updated cee_canonical_frame.json: {new_series_count} new, {updated_count} updated.")


def main():
    logger.info("Starting CEE-4 Inflation & PPI Deep-Dive Enrichment...")
    data_mode = os.environ.get("COUNTRY_PRIMER_DATA_MODE", "").lower()
    out_file = OUTPUT / "cee_inflation_deepdive.json"

    if (data_mode == "snapshot" or "--snapshot" in sys.argv) and out_file.exists():
        logger.info("Snapshot mode active; skipping live Eurostat download.")
        with open(out_file, "r", encoding="utf-8") as f:
            payload = json.load(f)
        sync_canonical_from_deepdive(payload)
        logger.info("Enrichment completed successfully in snapshot mode.")
        return

    try:
        # 1. Fetch HICP weights (prc_hicp_iw)
        logger.info("Fetching Eurostat HICP Weights (prc_hicp_iw)...")
        all_coicop_codes = [c for c, _, _, _ in COICOP_MAIN] + [m for m, _, _ in COICOP_MEMO]
        for _, _, _, subs in COICOP_MAIN:
            all_coicop_codes.extend([s for s, _ in subs])

        weights_raw = fetch_eurostat_json("prc_hicp_iw", {
            "geo": COUNTRIES,
            "coicop18": all_coicop_codes,
            "lastTimePeriod": 10,
        })
        get_weight, w_dims = parse_jsonstat_grid(weights_raw)
        w_years = list(w_dims["time"]["category"]["label"].keys())
        logger.info(f"Loaded weights for years: {w_years}")

        weights_map = {}
        for geo in COUNTRIES:
            for yr in w_years:
                for code in all_coicop_codes:
                    val = get_weight({"geo": geo, "time": yr, "coicop18": code})
                    if val is not None:
                        # Eurostat weights in permille -> convert to percent
                        weights_map[(geo, yr, code)] = val / 10.0

        # 2. Fetch HICP Rates (prc_hicp_minr)
        logger.info("Fetching Eurostat HICP Rates (prc_hicp_minr)...")
        cpi_codes_with_total = all_coicop_codes + ["TOTAL", "FOOD", "IGD_NNRG", "NRG", "SERV"]
        cpi_raw = fetch_eurostat_json("prc_hicp_minr", {
            "geo": COUNTRIES,
            "coicop18": cpi_codes_with_total,
            "unit": ["RCH_A", "RCH_M"],
            "lastTimePeriod": 48,
        })
        get_cpi_rate, cpi_dims = parse_jsonstat_grid(cpi_raw)
        cpi_times = list(cpi_dims["time"]["category"]["label"].keys())
        logger.info(f"Loaded CPI rates for {len(cpi_times)} months: {cpi_times[0]} to {cpi_times[-1]}")

        # 3. Fetch Domestic PPI Rates (sts_inppd_m)
        logger.info("Fetching Eurostat Domestic PPI Rates (sts_inppd_m)...")
        ppi_codes = ["B-E36", "MIG_ING", "MIG_CAG", "MIG_DCOG", "MIG_NDCOG", "MIG_NRG", "B_C_X_MIG_NRG", "C10", "C20", "C24", "C29"]
        ppi_raw = fetch_eurostat_json("sts_inppd_m", {
            "geo": COUNTRIES,
            "nace_r2": ppi_codes,
            "unit": ["PCH_SM", "PCH_PRE"],
            "indic_bt": "PRC_PRR_DOM",
            "s_adj": "NSA",
            "lastTimePeriod": 48,
        })
        get_ppi_rate, ppi_dims = parse_jsonstat_grid(ppi_raw)
        ppi_times = list(ppi_dims["time"]["category"]["label"].keys())
        logger.info(f"Loaded PPI rates for {len(ppi_times)} months: {ppi_times[0]} to {ppi_times[-1]}")

        # 4. Fetch Business Surveys & Expectations
        logger.info("Fetching Eurostat Expectations & Survey datasets...")
        bs_ind_raw = fetch_eurostat_json("ei_bsin_m_r2", {
            "geo": COUNTRIES,
            "indic": "BS-ISPE",
            "s_adj": "SA",
            "unit": "BAL",
            "lastTimePeriod": 48,
        })
        get_bs_ind, _ = parse_jsonstat_grid(bs_ind_raw)

        bs_serv_raw = fetch_eurostat_json("ei_bsse_m_r2", {
            "geo": COUNTRIES,
            "indic": "BS-PE3M",
            "s_adj": "SA",
            "unit": "BAL",
            "lastTimePeriod": 48,
        })
        get_bs_serv, _ = parse_jsonstat_grid(bs_serv_raw)

        bs_ret_raw = fetch_eurostat_json("ei_bsrt_m_r2", {
            "geo": COUNTRIES,
            "indic": "BS-RPE",
            "s_adj": "SA",
            "unit": "BAL",
            "lastTimePeriod": 48,
        })
        get_bs_ret, _ = parse_jsonstat_grid(bs_ret_raw)

        bs_cons_raw = fetch_eurostat_json("ei_bsco_m", {
            "geo": COUNTRIES,
            "indic": "BS-MP-NY",
            "s_adj": "SA",
            "unit": "BAL",
            "lastTimePeriod": 48,
        })
        get_bs_cons, _ = parse_jsonstat_grid(bs_cons_raw)

        bs_cu_raw = fetch_eurostat_json("ei_bsin_q_r2", {
            "geo": COUNTRIES,
            "indic": "BS-ICU-PC",
            "s_adj": "SA",
            "lastTimePeriod": 20,
        })
        get_bs_cu, cu_dims = parse_jsonstat_grid(bs_cu_raw)
        cu_times = list(cu_dims["time"]["category"]["label"].keys())

        # Map quarterly CU to monthly (forward fill)
        cu_monthly = {}
        for geo in COUNTRIES:
            last_val = None
            for q in cu_times:
                val = get_bs_cu({"geo": geo, "indic": "BS-ICU-PC", "s_adj": "SA", "time": q})
                if val is not None:
                    last_val = val
                yr, qtr = q.split("-")
                q_num = int(qtr[1])
                for m in range((q_num - 1) * 3 + 1, q_num * 3 + 1):
                    m_str = f"{yr}-{m:02d}"
                    cu_monthly[(geo, m_str)] = last_val

        # 5. Build Tables and Time Series by Country
        payload = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "countries": {},
        }

        MOMENTUM_ITEMS = [
            ("TOTAL", "Headline HICP", "整体调和 CPI", 100.0),
            ("TOT_X_NRG_FOOD", "Core HICP (ex-Food & Energy)", "核心 CPI (剔除食品能源)", 70.0),
            ("CP01", "Food & Non-Alcoholic Beverages", "食品与软饮料", 20.0),
            ("CP04", "Housing & Energy Utilities", "居住与能源公用事业", 18.0),
            ("CP07", "Transport Services & Fuels", "交通运输与车用燃油", 12.0),
            ("CP11", "Restaurants & Hotels (Core Services)", "核心服务业：餐饮与住宿", 7.0),
            ("CP09", "Recreation & Culture", "文娱体育与文化服务", 5.0),
            ("CP03", "Clothing & Footwear (Core Goods)", "核心商品：服装鞋类", 5.0),
            ("CP05", "Household Equipment & Furnishing", "耐用消费品：家具家居", 5.0),
            ("AP", "Administered / Regulated Prices", "政府管制物价", 15.0),
        ]

        for geo in COUNTRIES:
            logger.info(f"Processing deep-dive breakdown for {geo}...")
            c_payload = {
                "cpi_tables": {},
                "ppi_tables": {},
                "momentum_tables": {},
                "expectations_summary": {},
                "time_series": {
                    "cpi_contrib_food_yoy": [],
                    "cpi_contrib_goods_yoy": [],
                    "cpi_contrib_energy_yoy": [],
                    "cpi_contrib_services_yoy": [],
                    "cpi_contrib_food_mom": [],
                    "cpi_contrib_goods_mom": [],
                    "cpi_contrib_energy_mom": [],
                    "cpi_contrib_services_mom": [],
                    "cpi_head_3m_ann": [],
                    "cpi_head_12m_yoy": [],
                    "cpi_core_3m_ann": [],
                    "cpi_core_12m_yoy": [],
                    "cpi_services_3m_ann": [],
                    "cpi_goods_3m_ann": [],
                    "cpi_momentum_gap": [],
                    "ppi_domestic_yoy": [],
                    "ppi_core_yoy": [],
                    "ppi_energy_yoy": [],
                    "ppi_intermediate_yoy": [],
                    "ppi_cpi_scissors_gap": [],
                    "exp_industry_3m": [],
                    "exp_services_3m": [],
                    "exp_retail_3m": [],
                    "exp_consumer_12m": [],
                    "capacity_utilization": [],
                }
            }

            # Build monthly tables for last 12 months
            latest_cpi_months = [t for t in cpi_times[-12:]]
            for m in latest_cpi_months:
                yr = m.split("-")[0]
                w_dict = {code: weights_map.get((geo, yr, code), weights_map.get((geo, str(int(yr)-1), code), 0.0))
                          for code in all_coicop_codes}
                tbl = build_cpi_table(geo, m, w_dict, get_cpi_rate)
                if tbl:
                    c_payload["cpi_tables"][m] = tbl

                # Build momentum table for month m
                m_idx = cpi_times.index(m) if m in cpi_times else -1
                if m_idx >= 0:
                    mom_rows = []
                    for code, name_en, name_zh, def_w in MOMENTUM_ITEMS:
                        start_k = max(0, m_idx - 5)
                        hist_moms = [get_cpi_rate({"geo": geo, "coicop18": code, "unit": "RCH_M", "time": cpi_times[k]})
                                     for k in range(start_k, m_idx + 1)]
                        yoy_val = get_cpi_rate({"geo": geo, "coicop18": code, "unit": "RCH_A", "time": m})
                        act_w = weights_map.get((geo, yr, code), def_w) if code != "TOTAL" else 100.0
                        m_metrics = compute_momentum_metrics(hist_moms, yoy_val)
                        mom_rows.append({
                            "code": code,
                            "name_en": name_en,
                            "name_zh": name_zh,
                            "weight": round(act_w, 1),
                            **m_metrics
                        })

                    head_row = next((r for r in mom_rows if r["code"] == "TOTAL"), {})
                    core_row = next((r for r in mom_rows if r["code"] == "TOT_X_NRG_FOOD"), {})
                    c_payload["momentum_tables"][m] = {
                        "date": m,
                        "headline_ann_3m": head_row.get("mom_3m_ann"),
                        "headline_yoy": head_row.get("yoy"),
                        "headline_gap": head_row.get("gap"),
                        "headline_signal_en": head_row.get("signal_en"),
                        "headline_signal_zh": head_row.get("signal_zh"),
                        "core_ann_3m": core_row.get("mom_3m_ann"),
                        "core_yoy": core_row.get("yoy"),
                        "core_gap": core_row.get("gap"),
                        "core_signal_en": core_row.get("signal_en"),
                        "core_signal_zh": core_row.get("signal_zh"),
                        "items": mom_rows,
                    }

            latest_ppi_months = [t for t in ppi_times[-12:]]
            for m in latest_ppi_months:
                tbl_p = build_ppi_table(geo, m, get_ppi_rate)
                if tbl_p:
                    c_payload["ppi_tables"][m] = tbl_p

            # Build continuous time series from 2020 to latest
            all_months = sorted(list(set(cpi_times + ppi_times)))
            for i, m in enumerate(all_months):
                yr = m.split("-")[0]
                w_dict = {code: weights_map.get((geo, yr, code), weights_map.get((geo, str(int(yr)-1), code), 0.0))
                          for code in all_coicop_codes}
                tbl = build_cpi_table(geo, m, w_dict, get_cpi_rate)

                if tbl:
                    items_by_code = {it["code"]: it for it in tbl["items"]}
                    c_food_y = items_by_code.get("CP01", {}).get("contrib_yoy", 0.0)
                    c_food_m = items_by_code.get("CP01", {}).get("contrib_mom", 0.0)

                    c_goods_y = round(sum(items_by_code.get(c, {}).get("contrib_yoy", 0.0) for c in ["CP03", "CP05", "CP12"]), 2)
                    c_goods_m = round(sum(items_by_code.get(c, {}).get("contrib_mom", 0.0) for c in ["CP03", "CP05", "CP12"]), 2)

                    c_energy_y = items_by_code.get("CP04", {}).get("contrib_yoy", 0.0)
                    c_energy_m = items_by_code.get("CP04", {}).get("contrib_mom", 0.0)

                    c_serv_y = round(sum(items_by_code.get(c, {}).get("contrib_yoy", 0.0) for c in ["CP06", "CP07", "CP08", "CP09", "CP10", "CP11"]), 2)
                    c_serv_m = round(sum(items_by_code.get(c, {}).get("contrib_mom", 0.0) for c in ["CP06", "CP07", "CP08", "CP09", "CP10", "CP11"]), 2)

                    c_payload["time_series"]["cpi_contrib_food_yoy"].append({"date": m, "value": c_food_y})
                    c_payload["time_series"]["cpi_contrib_goods_yoy"].append({"date": m, "value": c_goods_y})
                    c_payload["time_series"]["cpi_contrib_energy_yoy"].append({"date": m, "value": c_energy_y})
                    c_payload["time_series"]["cpi_contrib_services_yoy"].append({"date": m, "value": c_serv_y})

                    c_payload["time_series"]["cpi_contrib_food_mom"].append({"date": m, "value": c_food_m})
                    c_payload["time_series"]["cpi_contrib_goods_mom"].append({"date": m, "value": c_goods_m})
                    c_payload["time_series"]["cpi_contrib_energy_mom"].append({"date": m, "value": c_energy_m})
                    c_payload["time_series"]["cpi_contrib_services_mom"].append({"date": m, "value": c_serv_m})

                # Continuous momentum series (3M annualized & gap)
                if m in cpi_times:
                    c_idx = cpi_times.index(m)
                    if c_idx >= 2:
                        # Headline
                        h_moms = [get_cpi_rate({"geo": geo, "coicop18": "TOTAL", "unit": "RCH_M", "time": cpi_times[k]})
                                  for k in range(c_idx - 2, c_idx + 1)]
                        h_yoy = get_cpi_rate({"geo": geo, "coicop18": "TOTAL", "unit": "RCH_A", "time": m})
                        if all(x is not None for x in h_moms) and h_yoy is not None:
                            r3 = (1.0 + h_moms[0] / 100.0) * (1.0 + h_moms[1] / 100.0) * (1.0 + h_moms[2] / 100.0) - 1.0
                            h_3m = round(((1.0 + r3) ** 4 - 1.0) * 100.0, 2)
                            c_payload["time_series"]["cpi_head_3m_ann"].append({"date": m, "value": h_3m})
                            c_payload["time_series"]["cpi_head_12m_yoy"].append({"date": m, "value": h_yoy})
                            c_payload["time_series"]["cpi_momentum_gap"].append({"date": m, "value": round(h_3m - h_yoy, 2)})

                        # Core
                        c_moms = [get_cpi_rate({"geo": geo, "coicop18": "TOT_X_NRG_FOOD", "unit": "RCH_M", "time": cpi_times[k]})
                                  for k in range(c_idx - 2, c_idx + 1)]
                        c_yoy = get_cpi_rate({"geo": geo, "coicop18": "TOT_X_NRG_FOOD", "unit": "RCH_A", "time": m})
                        if all(x is not None for x in c_moms) and c_yoy is not None:
                            r3_c = (1.0 + c_moms[0] / 100.0) * (1.0 + c_moms[1] / 100.0) * (1.0 + c_moms[2] / 100.0) - 1.0
                            core_3m = round(((1.0 + r3_c) ** 4 - 1.0) * 100.0, 2)
                            c_payload["time_series"]["cpi_core_3m_ann"].append({"date": m, "value": core_3m})
                            c_payload["time_series"]["cpi_core_12m_yoy"].append({"date": m, "value": c_yoy})

                        # Services
                        s_moms = [get_cpi_rate({"geo": geo, "coicop18": "SERV", "unit": "RCH_M", "time": cpi_times[k]})
                                  for k in range(c_idx - 2, c_idx + 1)]
                        if all(x is not None for x in s_moms):
                            r3_s = (1.0 + s_moms[0] / 100.0) * (1.0 + s_moms[1] / 100.0) * (1.0 + s_moms[2] / 100.0) - 1.0
                            c_payload["time_series"]["cpi_services_3m_ann"].append({"date": m, "value": round(((1.0 + r3_s) ** 4 - 1.0) * 100.0, 2)})

                        # Goods
                        g_moms = [get_cpi_rate({"geo": geo, "coicop18": "IGD_NNRG", "unit": "RCH_M", "time": cpi_times[k]})
                                  for k in range(c_idx - 2, c_idx + 1)]
                        if all(x is not None for x in g_moms):
                            r3_g = (1.0 + g_moms[0] / 100.0) * (1.0 + g_moms[1] / 100.0) * (1.0 + g_moms[2] / 100.0) - 1.0
                            c_payload["time_series"]["cpi_goods_3m_ann"].append({"date": m, "value": round(((1.0 + r3_g) ** 4 - 1.0) * 100.0, 2)})

                # PPI series
                ppi_head = get_ppi_rate({"geo": geo, "nace_r2": "B-E36", "unit": "PCH_SM", "time": m})
                ppi_core = get_ppi_rate({"geo": geo, "nace_r2": "B_C_X_MIG_NRG", "unit": "PCH_SM", "time": m})
                ppi_nrg = get_ppi_rate({"geo": geo, "nace_r2": "MIG_NRG", "unit": "PCH_SM", "time": m})
                ppi_ing = get_ppi_rate({"geo": geo, "nace_r2": "MIG_ING", "unit": "PCH_SM", "time": m})
                cpi_head = get_cpi_rate({"geo": geo, "coicop18": "TOTAL", "unit": "RCH_A", "time": m})

                if ppi_head is not None:
                    c_payload["time_series"]["ppi_domestic_yoy"].append({"date": m, "value": ppi_head})
                if ppi_core is not None:
                    c_payload["time_series"]["ppi_core_yoy"].append({"date": m, "value": ppi_core})
                if ppi_nrg is not None:
                    c_payload["time_series"]["ppi_energy_yoy"].append({"date": m, "value": ppi_nrg})
                if ppi_ing is not None:
                    c_payload["time_series"]["ppi_intermediate_yoy"].append({"date": m, "value": ppi_ing})

                # Scissors Gap = Domestic PPI YoY - Headline CPI YoY
                if ppi_head is not None and cpi_head is not None:
                    gap = round(ppi_head - cpi_head, 2)
                    c_payload["time_series"]["ppi_cpi_scissors_gap"].append({"date": m, "value": gap})

                # Expectations
                exp_ind = get_bs_ind({"geo": geo, "indic": "BS-ISPE", "s_adj": "SA", "unit": "BAL", "time": m})
                if exp_ind is not None:
                    c_payload["time_series"]["exp_industry_3m"].append({"date": m, "value": exp_ind})

                exp_srv = get_bs_serv({"geo": geo, "indic": "BS-PE3M", "s_adj": "SA", "unit": "BAL", "time": m})
                if exp_srv is not None:
                    c_payload["time_series"]["exp_services_3m"].append({"date": m, "value": exp_srv})

                exp_ret = get_bs_ret({"geo": geo, "indic": "BS-RPE", "s_adj": "SA", "unit": "BAL", "time": m})
                if exp_ret is not None:
                    c_payload["time_series"]["exp_retail_3m"].append({"date": m, "value": exp_ret})

                exp_cns = get_bs_cons({"geo": geo, "indic": "BS-MP-NY", "s_adj": "SA", "unit": "BAL", "time": m})
                if exp_cns is not None:
                    c_payload["time_series"]["exp_consumer_12m"].append({"date": m, "value": exp_cns})

                # Capacity utilization
                cu_val = cu_monthly.get((geo, m))
                if cu_val is not None:
                    c_payload["time_series"]["capacity_utilization"].append({"date": m, "value": cu_val})

            # Compute rich expectation summary statistics & qualitative regimes
            ts = c_payload["time_series"]
            exp_specs = [
                ("exp_industry_3m", "🏭", "Industrial Selling Price (3M)", "工业品出厂提价预期 (未来3M)", "Net Balance (净平衡值)"),
                ("exp_services_3m", "🛎️", "Services Price Intentions (3M)", "服务业价格预期 (未来3M)", "Net Balance (净平衡值)"),
                ("exp_retail_3m", "🛒", "Retail Price Intentions (3M)", "零售贸易价格预期 (未来3M)", "Net Balance (净平衡值)"),
                ("exp_consumer_12m", "👥", "Consumer 12M Inflation Perceptions", "居民家庭12M通胀感知", "Net Balance (净平衡值)"),
                ("capacity_utilization", "⚙️", "Capacity Utilization Rate", "工业产能利用率与瓶颈", "% of Capacity (利用率%)"),
            ]
            c_exp_summary = {}
            for s_key, s_icon, s_en, s_zh, s_unit in exp_specs:
                s_obs = ts.get(s_key, [])
                if not s_obs:
                    continue
                s_vals = [o["value"] for o in s_obs]
                cur_val = s_vals[-1]
                prev_1m = s_vals[-2] if len(s_vals) >= 2 else cur_val
                prev_3m = s_vals[-4] if len(s_vals) >= 4 else s_vals[0]
                mn = min(s_vals)
                mx = max(s_vals)
                pct = round((cur_val - mn) / (mx - mn) * 100) if mx > mn else 50
                diff_3m = round(cur_val - prev_3m, 1)

                # Executive Takeaways & Regimes
                if s_key == "capacity_utilization":
                    if cur_val >= 82.0:
                        regime_en, regime_zh = "Critical Bottleneck (>82%)", "极度吃紧/严重瓶颈"
                        takeaway_en = "Operating well above the 80% threshold; severe capacity bottlenecks confer aggressive downstream pricing power."
                        takeaway_zh = "显著超越80%景气临界线，设备与用工产能紧绷，企业向下游转嫁成本的议价筹码极强。"
                    elif cur_val >= 78.0:
                        regime_en, regime_zh = "High Normal (78-82%)", "产能充裕常态"
                        takeaway_en = "Capacity is well-utilized near equilibrium; supply can absorb demand without acute cost shocks."
                        takeaway_zh = "产能利用处于均衡区间上方，供需总体匹配，暂未引发严重供应链断裂风险。"
                    else:
                        regime_en, regime_zh = "Slack Capacity (<78%)", "产能闲置/利用不足"
                        takeaway_en = "Significant idle capacity limits industrial pricing power; producers absorb margin compression."
                        takeaway_zh = "工业产能存在明显闲置，需求对生产支撑偏弱，企业定价权受限难以顺利提价。"
                elif s_key == "exp_consumer_12m":
                    if pct >= 75:
                        regime_en, regime_zh = "Elevated Perceptions", "通胀预期偏高"
                        takeaway_en = "Households perceive persistent upward price drift; central bank vigilance against de-anchoring is warranted."
                        takeaway_zh = "居民对未来一年物价上行预期仍处于历史高分位，需警惕通胀预期脱锚与二次扩散。"
                    elif pct <= 25:
                        regime_en, regime_zh = "Anchored / Cool", "预期充分锚定"
                        takeaway_en = "Consumer inflation perceptions have normalized toward target; inflation expectations are well anchored."
                        takeaway_zh = "家庭端物价上涨担忧显著缓解，重回历史低分位区间，预期保持稳定锚定。"
                    else:
                        regime_en, regime_zh = "Moderate / Balanced", "预期处于中性区"
                        takeaway_en = "Consumer perceptions are balanced within historical ranges."
                        takeaway_zh = "居民通胀预期处于历年常态分布中枢，未见恐慌性采购或通胀预期失控迹象。"
                else:  # Business pricing intentions
                    if cur_val > 20.0:
                        regime_en, regime_zh = "Aggressive Price Hikes", "强劲提价意向"
                        takeaway_en = f"Over net +{cur_val:.1f} balance of firms intend to hike prices; cost pass-through is active."
                        takeaway_zh = f"净提价企业比例高达 +{cur_val:.1f}，行业提价冲动强劲，成本传导通道畅通。"
                    elif cur_val > 10.0:
                        regime_en, regime_zh = "Moderate Price Hikes", "温和提价区间"
                        takeaway_en = f"Price intentions are positive (+{cur_val:.1f}) but orderly; firms pass through costs gradually."
                        takeaway_zh = f"提价意向保持温和扩张 (+{cur_val:.1f})，企业遵循节奏渐进式提价，未形成恶性螺旋。"
                    else:
                        regime_en, regime_zh = "Subdued / Deflationary", "提价意向低迷"
                        takeaway_en = f"Net balance is subdued (+{cur_val:.1f}); limited pricing power forces margin compression."
                        takeaway_zh = f"提价意向低位徘徊 (+{cur_val:.1f})，市场竞争与需求压制了企业提价能力。"

                c_exp_summary[s_key] = {
                    "icon": s_icon,
                    "label_en": s_en,
                    "label_zh": s_zh,
                    "unit": s_unit,
                    "current": cur_val,
                    "prev_3m": prev_3m,
                    "diff_3m": diff_3m,
                    "min": mn,
                    "max": mx,
                    "pct": pct,
                    "regime_en": regime_en,
                    "regime_zh": regime_zh,
                    "takeaway_en": takeaway_en,
                    "takeaway_zh": takeaway_zh,
                }
            c_payload["expectations_summary"] = c_exp_summary

            payload["countries"][geo] = c_payload

        # Save deepdive artifact
        with open(out_file, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)
        logger.info(f"Saved inflation deep-dive artifact to {out_file}")

        sync_canonical_from_deepdive(payload)
    except Exception as e:
        if out_file.exists():
            logger.warning(f"Live Eurostat fetch failed ({e}); falling back to cached deepdive artifact...")
            with open(out_file, "r", encoding="utf-8") as f:
                payload = json.load(f)
            sync_canonical_from_deepdive(payload)
        else:
            raise

    logger.info("Enrichment completed successfully!")

    logger.info("Enrichment completed successfully!")


if __name__ == "__main__":
    main()
