import json

from validate_outputs import validate_output_contract, COUNTRY_FILES, DATA_FIRST_NAMES


def test_generated_output_contract() -> None:
    validate_output_contract()


def test_every_dashboard_produces_freshness_records():
    audit = json.loads(open("output/freshness_audit.json").read())
    dashboards = {r.get("dashboard") for r in audit.get("records", [])}
    assert len(dashboards) == len(COUNTRY_FILES), f"only {sorted(dashboards)} produced records"


def test_every_canonical_series_carries_trust_dimensions():
    # Scoped to the data-first canonical frames (china/japan/south_africa/uk/us).
    # cee_canonical_frame.json uses a different schema (cee-canonical-v2) that
    # keeps trust dimensions inside each series' "metadata" dict rather than a
    # sibling "quality" dict, so it is intentionally out of scope here.
    for name in DATA_FIRST_NAMES:
        path = f"output/{name}_canonical_frame.json"
        for s in json.loads(open(path).read()).get("series", []):
            q = s.get("quality") or {}
            for field in ("source_authority", "freshness", "derivation"):
                assert q.get(field), f"{path}:{s.get('indicator_id')} missing {field}"
