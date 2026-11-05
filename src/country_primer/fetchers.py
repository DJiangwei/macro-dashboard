"""Global fetcher registry for data-first scopes.

Every indicator YAML names a ``fetcher``; this module maps that name to an
adapter function plus the post-processing the adapter's output needs. Before
F1 each country builder kept its own copy of this table and the copies had
drifted (the same name meant different post-processing in different scopes).
One table now serves every scope, so a source added here is available to all
of them.

Post-processing modes
---------------------
``raw``              the adapter returns final values (it applies its own units
                     and transforms, e.g. ONS/BoE/GOV.UK and the China adapters).
``transform``        apply the spec's ``transform`` (yoy_pct, yoy, diff,
                     pct_change) to the adapter's levels.
``scale_transform``  divide by ``spec['scale']`` first, then transform.

Transforms that an adapter already applied while parsing (the China unit
conversions in ``_apply_china_transform``) are never applied a second time.
Any other unknown transform name empties the series and marks it unavailable,
so a typo can never put untransformed levels on a page under a growth label.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

import importlib

import requests

from . import adapters

RAW = "raw"
TRANSFORM = "transform"
SCALE_TRANSFORM = "scale_transform"

SESSION = "session"  # fn(requests.Session(), spec)
SPEC = "spec"        # fn(spec)
CACHE = "cache"      # fn(spec, cache)

# Unit conversions applied inside adapters by ``adapters._apply_china_transform``.
NATIVE_TRANSFORMS = frozenset({
    "per_100_to_per_unit", "usd_trn", "usd_mn_to_trn", "usd_100mn_to_trn", "usd_thousand_to_bn",
    "cny_100mn_to_trn", "cny_100mn_to_bn", "cny_10k_to_bn", "cny_yuan_to_trn", "index_100_to_yoy",
    "people_billion",
})


@dataclass(frozen=True)
class FetcherDef:
    function: str
    call: str
    post: str
    note: str = ""
    module: str = "adapters"


FETCHERS: dict[str, FetcherDef] = {
    # Cross-country official/IFI sources
    "bis_policy_rate": FetcherDef("fetch_bis_policy_rate", SPEC, RAW, "BIS WS_CBPOL daily policy rates as decision events"),
    "bis_credit_gap": FetcherDef("fetch_bis_credit_gap", SPEC, RAW, "BIS credit-to-GDP gap"),
    "bis_fx": FetcherDef("fetch_bis_fx", SPEC, RAW, "BIS WS_XRU monthly exchange rates"),
    "imf_sdmx": FetcherDef("fetch_imf_sdmx", SESSION, SCALE_TRANSFORM),
    "imf_datamapper": FetcherDef("fetch_imf_datamapper", SESSION, TRANSFORM),
    "world_bank": FetcherDef("fetch_world_bank", SPEC, SCALE_TRANSFORM),
    "dbnomics": FetcherDef("fetch_dbnomics", SPEC, TRANSFORM),
    "bruegel_reer": FetcherDef("fetch_bruegel_reer", SPEC, TRANSFORM),
    "eia": FetcherDef("fetch_eia", SPEC, TRANSFORM),
    "fred": FetcherDef("fetch_fred_us", SESSION, SCALE_TRANSFORM, "FRED API when FRED_API_KEY is set, else graph CSV"),
    "fred_graph": FetcherDef("fetch_fred_graph", SPEC, TRANSFORM),
    "fred_graph_csv": FetcherDef("fetch_fred_graph", SPEC, TRANSFORM),
    "spread": FetcherDef("fetch_spread", SESSION, SCALE_TRANSFORM, "primary minus secondary leg"),
    "ecb_sdmx": FetcherDef("fetch_ecb_sdmx", SESSION, SCALE_TRANSFORM),
    "eurostat": FetcherDef("fetch_eurostat_jsonstat", SESSION, SCALE_TRANSFORM),
    "eurostat_jsonstat": FetcherDef("fetch_eurostat_jsonstat", SESSION, SCALE_TRANSFORM),
    # United States
    "bls_api": FetcherDef("fetch_bls_api", SESSION, RAW),
    "treasury_auctions": FetcherDef("fetch_treasury_auctions", SESSION, RAW),
    # United Kingdom
    "ons_timeseries": FetcherDef("fetch_ons_timeseries", SESSION, RAW),
    "ons_xlsx_table": FetcherDef("fetch_ons_xlsx_table", SESSION, RAW),
    "ons_horizontal_csv_table": FetcherDef("fetch_ons_horizontal_csv_table", SESSION, RAW),
    "boe_iadb": FetcherDef("fetch_boe_iadb", SESSION, RAW),
    "boe_bank_rate": FetcherDef("fetch_boe_bank_rate", SESSION, RAW),
    "govuk_road_fuel": FetcherDef("fetch_govuk_road_fuel", SESSION, RAW),
    "govuk_xlsx_table": FetcherDef("fetch_govuk_xlsx_table", SESSION, RAW),
    "govuk_ods_table": FetcherDef("fetch_govuk_ods_table", SESSION, RAW),
    "obr_xlsx_row": FetcherDef("fetch_obr_xlsx_row", SESSION, RAW),
    # Japan
    "boj_flatfile": FetcherDef("fetch_boj_flatfile", SESSION, SCALE_TRANSFORM),
    "estat": FetcherDef("fetch_estat", SESSION, SCALE_TRANSFORM),
    # China
    "akshare_table": FetcherDef("fetch_akshare_table", CACHE, RAW),
    "akshare_wide_year_month": FetcherDef("fetch_akshare_wide_year_month", CACHE, RAW),
    "eastmoney_api": FetcherDef("fetch_eastmoney", SESSION, RAW),
    "eastmoney_industry_indicator": FetcherDef("fetch_eastmoney_industry_indicator", SPEC, RAW),
    "nbs_api": FetcherDef("fetch_nbs_api", SESSION, RAW),
    "bond_zh_us_rate": FetcherDef("fetch_bond_zh_us_rate", SPEC, RAW),
    "pbc_card": FetcherDef("fetch_pbc_card", SPEC, RAW),
    "safe_rmb_midpoint": FetcherDef("fetch_safe_midpoint", "safe_rows", RAW),
    # Other national sources
    "sarb": FetcherDef("fetch_sarb", SESSION, TRANSFORM),
    "tcmb_xml": FetcherDef("fetch_tcmb_xml", SPEC, TRANSFORM),
    "tcmb_evds": FetcherDef("fetch_tcmb_evds", SPEC, SCALE_TRANSFORM),
    "hk_csd": FetcherDef("fetch_hk_csd", SPEC, SCALE_TRANSFORM),
    "bok_ecos": FetcherDef("fetch_bok_ecos", SPEC, SCALE_TRANSFORM),
    "tw_cbc": FetcherDef("fetch_tw_cbc", SPEC, SCALE_TRANSFORM),
    "tw_dgbas": FetcherDef("fetch_tw_dgbas", SPEC, SCALE_TRANSFORM),
    "tw_mof_customs": FetcherDef("fetch_tw_mof_customs", SPEC, SCALE_TRANSFORM),
    "finmind": FetcherDef("fetch_finmind", SPEC, SCALE_TRANSFORM),
    "nbk_xml": FetcherDef("fetch_nbk_xml", SPEC, TRANSFORM),
    "nbk_base_rate": FetcherDef("fetch_nbk_base_rate", SPEC, RAW, "NBK base-rate decisions from the official schedule, event-dated"),
    "cbn_fx": FetcherDef("fetch_cbn_fx", SPEC, SCALE_TRANSFORM),
    "cbn_money_market": FetcherDef("fetch_cbn_money_market", SPEC, RAW, "CBN money-market indicators API, one monthly field"),
    # Energy markets (src/country_primer/energy_adapters.py)
    "eia_xls": FetcherDef("fetch_eia_xls", SPEC, SCALE_TRANSFORM, "EIA dnav history spreadsheets", "energy_adapters"),
    "cftc_positions": FetcherDef("fetch_cftc_positions", SPEC, RAW, "CFTC disaggregated COT by contract code", "energy_adapters"),
    "energy_charts_price": FetcherDef("fetch_energy_charts_price", SPEC, RAW, "Day-ahead power, daily mean", "energy_adapters"),
    "foreign_futures": FetcherDef("fetch_foreign_futures", SPEC, RAW, "Sina front-month futures via AKShare", "energy_adapters"),
    "sge_spot": FetcherDef("fetch_sge_spot", SPEC, RAW, "Shanghai Gold Exchange close / benchmark via AKShare", "energy_adapters"),
    "cn_futures_main": FetcherDef("fetch_cn_futures_main", SPEC, RAW, "SHFE/DCE/GFEX main contract via Sina/AKShare", "energy_adapters"),
    "cn_futures_inventory": FetcherDef("fetch_cn_futures_inventory", SPEC, RAW, "Exchange warehouse stocks via Eastmoney/AKShare", "energy_adapters"),
    "gie_agsi": FetcherDef("fetch_gie_agsi", SPEC, RAW, "GIE AGSI+ gas storage per gas day (GIE_AGSI_API_KEY)", "energy_adapters"),
    "eia_steo": FetcherDef("fetch_eia_steo", SPEC, RAW, "EIA STEO history months via API v2 (EIA_API_KEY)", "energy_adapters"),
    "ember_generation": FetcherDef("fetch_ember_generation", SPEC, RAW, "Ember monthly generation by source (EMBER_API_KEY)", "energy_adapters"),
}


def apply_transform(series: dict[str, Any]) -> dict[str, Any]:
    if series.get("transform") in NATIVE_TRANSFORMS:
        return series
    return adapters._apply_us_transform(series)


def postprocess(series: dict[str, Any], mode: str) -> dict[str, Any]:
    if mode == RAW:
        return series
    if mode == SCALE_TRANSFORM:
        series = adapters.apply_scale(series)
    return apply_transform(series)


def _invoke(definition: FetcherDef, spec: dict[str, Any], cache: dict[str, Any]) -> dict[str, Any]:
    # Resolved at call time so tests can substitute adapter functions.
    module = adapters if definition.module == "adapters" else importlib.import_module(f"{__package__}.{definition.module}")
    function = getattr(module, definition.function)
    if definition.call == SESSION:
        return function(requests.Session(), spec)
    if definition.call == CACHE:
        return function(spec, cache)
    if definition.call == "safe_rows":
        return function(spec, cache.setdefault("safe_rows", []))
    return function(spec)


def fetch_series(name: str, spec: dict[str, Any], cache: dict[str, Any] | None = None) -> dict[str, Any]:
    """Fetch one indicator through the registry."""
    definition = FETCHERS[name]
    return postprocess(_invoke(definition, spec, {} if cache is None else cache), definition.post)


def build_registry() -> dict[str, Callable[[dict[str, Any], dict[str, Any]], dict[str, Any]]]:
    """Registry in the shape ``data_first_pipeline.fetch_all`` expects."""
    return {
        name: (lambda spec, cache, _name=name: fetch_series(_name, spec, cache))
        for name in FETCHERS
    }
