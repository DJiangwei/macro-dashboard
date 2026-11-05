"""Eurostat datasets and aggregates that stopped updating must not come back.

A frozen source passes every other check: the series keeps its last value and
only the freshness date gives it away. Found 2026-11-05.
"""
from __future__ import annotations

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]

# Discontinued dataset -> successor.
DISCONTINUED = {"jvs_q_nace2": "jvs_q_r21 (NACE Rev. 2.1, aggregate B-T)"}

# Datasets whose EA20 aggregate stopped after 2025 while EA21 continues.
EA20_FROZEN = {"ei_bsin_q_r2", "ei_bssi_m_r2", "ei_bsee_m_r2", "bop_gdp6_q"}


def _sources() -> list[Path]:
    return sorted(ROOT.glob("config/**/*.yaml")) + [ROOT / "src/country_primer/data_fetcher.py"]


def test_no_source_uses_a_discontinued_eurostat_dataset() -> None:
    hits = [
        f"{path.relative_to(ROOT)} uses {dataset}; use {successor}"
        for path in _sources()
        for dataset, successor in DISCONTINUED.items()
        if f'"{dataset}"' in path.read_text(encoding="utf-8")
    ]
    assert not hits, hits


def test_negotiated_wages_use_the_ecb_inw_dataflow() -> None:
    # STS.Q.*.N.INWR.000000.3.ANR ends at 2025-Q3; the ECB moved the indicator to INW.
    hits = [str(path.relative_to(ROOT)) for path in _sources() if ".INWR.000000.3.ANR" in path.read_text(encoding="utf-8")]
    assert not hits, hits


def test_euro_area_series_use_the_ea21_aggregate() -> None:
    # EA20 froze for EA20_FROZEN after 2025; every series is on EA21 so the page has one composition.
    config = yaml.safe_load((ROOT / "config/euro_area_indicators.yaml").read_text(encoding="utf-8"))
    ea20 = [
        spec["id"]
        for spec in config["indicators"]
        if {"EA20", "EXT_EA20"} & {str(v) for v in (spec.get("filters") or {}).values()}
    ]
    assert not ea20, f"use EA21 (EXT_EA21 for partners): {ea20}"
