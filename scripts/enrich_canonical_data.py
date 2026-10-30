"""Enrich canonical data frames with new yield curves, liquidity, and external debt indicators."""
from __future__ import annotations

import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import requests
import yaml

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from country_primer.adapters import (
    fetch_bond_zh_us_rate,
    fetch_world_bank,
    fetch_fred_us,
    fetch_ecb_sdmx,
    fetch_boe_iadb,
)
from country_primer.data_quality import assess_series_quality


def _format_canonical_entry(spec: dict[str, Any], result: dict[str, Any], concept_id: str | None = None) -> dict[str, Any]:
    obs_raw = result.get("observations", [])
    obs_list = [[item["date"], item["value"]] for item in obs_raw]
    latest_date = obs_list[-1][0] if obs_list else ""
    now_iso = datetime.now(UTC).isoformat()
    cid = concept_id or spec.get("concept_id") or f"{spec.get('id')}"

    item_for_assessment = {
        **spec,
        "observations": obs_raw,
        "source_name": spec.get("source_name", "Official / Standard"),
        "source_url": spec.get("source_url", ""),
        "source_authority": spec.get("source_authority", ""),
        "frequency": spec.get("frequency", "daily"),
        "transform": spec.get("transform", "level"),
    }
    quality = assess_series_quality(item_for_assessment)
    quality.setdefault("quality_tier", "tier_1")
    quality.setdefault("relevance", "core_macro")
    quality.setdefault("reporting_lag_days", 1)
    quality.setdefault("revision_risk", "low")
    quality.setdefault("validation_note", spec.get("caveat_en", "Standard primary official observation series."))

    return {
        "indicator_id": spec["id"],
        "concept_id": cid,
        "section": spec.get("section", "monetary_financial"),
        "label_en": spec.get("label_en", spec["id"]),
        "label_zh": spec.get("label_zh", spec["id"]),
        "unit": spec.get("unit", "%"),
        "frequency": spec.get("frequency", "daily"),
        "transform": spec.get("transform", "level"),
        "source": {
            "name": spec.get("source_name", "Official / Standard"),
            "series": str(spec.get("series", spec["id"])),
            "url": spec.get("source_url", ""),
        },
        "quality": quality,
        "quality_notes": [spec.get("caveat_en", "")] if spec.get("caveat_en") else [],
        "actual_through": str(spec.get("actual_through") or ""),
        "provider_updated": result.get("provider_updated") or latest_date,
        "refresh_fallback": False,
        "fetch_timestamp": now_iso,
        "has_revisions": False,
        "prior_vintage": None,
        "observations": obs_list,
    }


def _upsert_series(frame_path: Path, new_entries: list[dict[str, Any]]) -> None:
    data = json.loads(frame_path.read_text())
    existing = {s["indicator_id"]: s for s in data.get("series", [])}
    for entry in new_entries:
        existing[entry["indicator_id"]] = entry
    # Keep deterministic sort by indicator_id
    data["series"] = [existing[k] for k in sorted(existing.keys())]
    data["generated"] = datetime.now(UTC).isoformat()
    frame_path.write_text(json.dumps(data, indent=2, ensure_ascii=False))
    print(f"Updated {frame_path.name}: {len(data['series'])} total series (+{len(new_entries)} upserted)")


def enrich_china() -> None:
    print("--- Enriching China CGB Curve & Spreads ---")
    cgb_specs = [
        {"id": "cgb_yield_2y", "value_column": "中国国债收益率2年", "label_en": "China 2Y Sovereign CGB Yield", "label_zh": "中国2年期国债收益率", "section": "money_credit"},
        {"id": "cgb_yield_5y", "value_column": "中国国债收益率5年", "label_en": "China 5Y Sovereign CGB Yield", "label_zh": "中国5年期国债收益率", "section": "money_credit"},
        {"id": "cgb_yield_10y", "value_column": "中国国债收益率10年", "label_en": "China 10Y Sovereign CGB Yield", "label_zh": "中国10年期国债收益率", "section": "money_credit"},
        {"id": "cgb_yield_30y", "value_column": "中国国债收益率30年", "label_en": "China 30Y Sovereign CGB Yield", "label_zh": "中国30年期国债收益率", "section": "money_credit"},
        {"id": "cgb_curve_10y2y", "value_column": "中国国债收益率10年-2年", "label_en": "China CGB 10Y-2Y Term Spread", "label_zh": "中国国债10Y-2Y期限利差", "section": "money_credit"},
        {"id": "us_cn_spread_10y", "is_us_cn_spread": True, "label_en": "US-China 10Y Sovereign Spread", "label_zh": "中美10年期国债利差", "section": "money_credit"},
    ]
    entries = []
    for spec in cgb_specs:
        full_spec = {
            **spec,
            "fetcher": "bond_zh_us_rate",
            "series": f"bond_zh_us_rate:{spec.get('value_column', 'spread')}",
            "source_name": "AKShare / ChinaBond Sovereign Yield Curve",
            "source_url": "https://finance.sina.com.cn",
            "frequency": "daily",
            "start_date": "2015-01-01",
        }
        res = fetch_bond_zh_us_rate(full_spec)
        entries.append(_format_canonical_entry(full_spec, res, f"cn:{spec['id']}"))
    _upsert_series(ROOT / "output" / "china_canonical_frame.json", entries)


def enrich_em_guidotti() -> None:
    print("--- Enriching Emerging Markets Guidotti-Greenspan Ratio ---")
    em_countries = [
        ("TUR", ROOT / "output" / "turkey_canonical_frame.json"),
        ("EGY", ROOT / "output" / "egypt_canonical_frame.json"),
        ("NGA", ROOT / "output" / "nigeria_canonical_frame.json"),
        ("KAZ", ROOT / "output" / "kazakhstan_canonical_frame.json"),
        ("UZB", ROOT / "output" / "uzbekistan_canonical_frame.json"),
        ("ZAF", ROOT / "output" / "south_africa_canonical_frame.json"),
    ]
    for iso, path in em_countries:
        spec = {
            "id": "short_term_external_debt_pct_reserves",
            "section": "external_fx",
            "label_en": "Short-Term External Debt (% of Reserves)",
            "label_zh": "短期外债占外汇储备比重 (Guidotti-Greenspan比率)",
            "unit": "% reserves",
            "fetcher": "world_bank",
            "series": "DT.DOD.DSTC.IR.ZS",
            "country_iso3": iso,
            "source_name": "World Bank International Debt Statistics",
            "source_url": f"https://data.worldbank.org/indicator/DT.DOD.DSTC.IR.ZS?locations={iso}",
            "frequency": "annual",
            "start_date": "2000-01-01",
            "caveat_en": "Guidotti-Greenspan rule indicator; ratios above 100% indicate short-term external debt exceeding gross international reserves.",
        }
        try:
            res = fetch_world_bank(spec)
            entry = _format_canonical_entry(spec, res, "short_term_external_debt")
            _upsert_series(path, [entry])
        except Exception as e:
            print(f"Failed {iso} World Bank pull: {e}")


def enrich_us() -> None:
    print("--- Enriching US Curves & Liquidity ---")
    session = requests.Session()
    specs = [
        {
            "id": "treasury_5y_yield",
            "section": "monetary_financial",
            "label_en": "5Y Treasury Yield",
            "label_zh": "5年期美国国债收益率",
            "unit": "%",
            "frequency": "daily",
            "series": "DGS5",
            "source_name": "FRED / US Treasury",
            "source_url": "https://fred.stlouisfed.org/series/DGS5",
            "concept_id": "treasury_5y_yield",
        },
        {
            "id": "fed_total_assets",
            "section": "fed_policy",
            "label_en": "Fed Total Assets (Balance Sheet)",
            "label_zh": "美联储总资产规模 (资产负债表)",
            "unit": "USD mn",
            "frequency": "weekly",
            "series": "WALCL",
            "source_name": "FRED / Federal Reserve",
            "source_url": "https://fred.stlouisfed.org/series/WALCL",
            "concept_id": "central_bank_assets",
        },
        {
            "id": "em_corporate_spread_oas",
            "section": "monetary_financial",
            "label_en": "Emerging Markets Corporate Option-Adjusted Spread",
            "label_zh": "新兴市场企业债期权调整利差 (ICE BofA EM OAS)",
            "unit": "%",
            "frequency": "daily",
            "series": "BAMLEMCBPIOAS",
            "source_name": "FRED / ICE Benchmark Administration",
            "source_url": "https://fred.stlouisfed.org/series/BAMLEMCBPIOAS",
            "concept_id": "em_spread_oas",
        },
    ]
    entries = []
    for spec in specs:
        res = fetch_fred_us(session, spec)
        entries.append(_format_canonical_entry(spec, res, spec["concept_id"]))
    _upsert_series(ROOT / "output" / "us_canonical_frame.json", entries)


def enrich_euro_area() -> None:
    print("--- Enriching Euro Area 5Y Yield ---")
    session = requests.Session()
    spec = {
        "id": "aaa_yield_5y",
        "section": "fiscal_sovereign",
        "label_en": "Euro Area AAA Benchmark 5Y Yield",
        "label_zh": "欧元区AAA级基准5年期国债收益率",
        "unit": "%",
        "frequency": "daily",
        "flow": "YC",
        "series": "B.U2.EUR.4F.G_N_A.SV_C_YM.SR_5Y",
        "source_name": "ECB",
        "source_url": "https://data.ecb.europa.eu/data/datasets/YC",
        "start_date": "2004-09-01",
        "concept_id": "sovereign_yield_5y",
    }
    res = fetch_ecb_sdmx(session, spec)
    entry = _format_canonical_entry(spec, res, spec["concept_id"])
    _upsert_series(ROOT / "output" / "euro_area_canonical_frame.json", [entry])


def enrich_uk() -> None:
    print("--- Enriching UK Gilt 20Y Yield & Slope ---")
    session = requests.Session()
    spec_20y = {
        "id": "gilt_20y_nominal_par_yield",
        "section": "monetary_financial",
        "label_en": "20Y Nominal Gilt Par Yield",
        "label_zh": "20年期名义英国国债平价收益率",
        "unit": "%",
        "frequency": "daily",
        "series": "IUDLNPY",
        "source_name": "Bank of England IADB",
        "source_url": "https://www.bankofengland.co.uk/boeapps/database/iadb/Bank-Database",
        "start_date": "1997-01-01",
        "concept_id": "gilt_20y_nominal_par_yield",
    }
    res_20y = fetch_boe_iadb(session, spec_20y)
    entry_20y = _format_canonical_entry(spec_20y, res_20y, spec_20y["concept_id"])

    # Pull 5Y for slope
    spec_5y = {
        "id": "gilt_5y_nominal_par_yield",
        "series": "IUDSNPY",
        "start_date": "1997-01-01",
    }
    res_5y = fetch_boe_iadb(session, spec_5y)
    obs_5y = {item["date"]: item["value"] for item in res_5y.get("observations", [])}
    slope_obs = []
    for item in res_20y.get("observations", []):
        d = item["date"]
        if d in obs_5y:
            slope_obs.append({"date": d, "value": round((item["value"] - obs_5y[d]) * 100, 2)})

    spec_slope = {
        "id": "yield_curve_slope_20y5y",
        "section": "monetary_financial",
        "label_en": "20Y-5Y Gilt Par Yield Slope",
        "label_zh": "20年-5年期英国国债收益率曲线斜率",
        "unit": "bps",
        "frequency": "daily",
        "series": "spread:IUDLNPY-IUDSNPY",
        "source_name": "Bank of England IADB",
        "source_url": "https://www.bankofengland.co.uk/boeapps/database/iadb/Bank-Database",
        "observations": slope_obs,
        "provider_updated": slope_obs[-1]["date"] if slope_obs else "",
        "concept_id": "yield_curve_slope_20y5y",
    }
    entry_slope = _format_canonical_entry(spec_slope, spec_slope, spec_slope["concept_id"])
    _upsert_series(ROOT / "output" / "uk_canonical_frame.json", [entry_20y, entry_slope])


def enrich_japan() -> None:
    print("--- Enriching Japan BOJ Total Assets ---")
    session = requests.Session()
    spec = {
        "id": "boj_total_assets",
        "section": "monetary_financial",
        "label_en": "Bank of Japan Total Assets",
        "label_zh": "日本央行总资产规模 (资产负债表)",
        "unit": "JPY 100mn",
        "frequency": "monthly",
        "series": "JPNASSETS",
        "source_name": "FRED / Bank of Japan",
        "source_url": "https://fred.stlouisfed.org/series/JPNASSETS",
        "concept_id": "central_bank_assets",
    }
    res = fetch_fred_us(session, spec)
    entry = _format_canonical_entry(spec, res, spec["concept_id"])
    _upsert_series(ROOT / "output" / "japan_canonical_frame.json", [entry])


def main() -> None:
    enrich_china()
    enrich_em_guidotti()
    enrich_us()
    enrich_euro_area()
    enrich_uk()
    enrich_japan()
    print("\nAll canonical frames successfully enriched!")


if __name__ == "__main__":
    main()
