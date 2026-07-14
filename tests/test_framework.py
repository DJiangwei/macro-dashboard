from country_primer.data_fetcher import INDICATOR_MANIFEST_48
from country_primer.framework import canonical_indicator_id, concept_id_for, framework_summary


def test_framework_v2_has_nine_pillars_and_48_concepts() -> None:
    assert framework_summary() == {
        "version": 2,
        "pillars": 9,
        "core_concepts": 48,
        "legacy_aliases": 7,
    }


def test_legacy_semantic_aliases_resolve_to_accurate_ids() -> None:
    assert canonical_indicator_id("manufacturing_pmi") == "industry_confidence"
    assert canonical_indicator_id("truck_km_index") == "road_freight_activity"
    assert concept_id_for("PL", "cpi_yoy") == "headline_inflation"


def test_cee_manifest_is_yaml_backed_and_proxy_free() -> None:
    ids = {spec.indicator_id for spec in INDICATOR_MANIFEST_48}
    assert len(ids) == len(INDICATOR_MANIFEST_48)
    assert "industry_confidence" in ids
    assert "manufacturing_pmi" not in ids
    assert all("ProxyFetcher" not in spec.adapter_order for spec in INDICATOR_MANIFEST_48)
