import json

import pytest

from validate_outputs import (
    validate_output_contract,
    _assert_cross_checks,
    COUNTRY_FILES,
    DASHBOARD_DISPLAY_NAMES,
    DATA_FIRST_NAMES,
)


def test_generated_output_contract() -> None:
    validate_output_contract()


def test_every_dashboard_produces_freshness_records():
    audit = json.loads(open("output/freshness_audit.json").read())
    dashboards = {r.get("dashboard") for r in audit.get("records", [])}
    assert len(dashboards) == len(DASHBOARD_DISPLAY_NAMES), f"only {sorted(dashboards)} produced records"


def test_cross_checks_are_present_and_within_tolerance() -> None:
    for name in ("japan", "south_africa", "us"):
        summary = json.loads(open(f"output/{name}_dashboard_summary.json").read())
        checks = summary.get("cross_checks")
        assert checks, f"{name} declares no cross-checks"
        bad = [c for c in checks if c["status"] == "diverged"]
        assert not bad, f"{name} cross-checks diverged: {[c['label_en'] for c in bad]}"


def test_assert_cross_checks_raises_on_diverged_status() -> None:
    # Synthetic summary standing in for a committed dashboard summary; only
    # the fields _assert_cross_checks reads are populated.
    summary = {
        "cross_checks": [
            {
                "label_en": "Fake CPI check",
                "status": "diverged",
                "n_breaches": 99,
                "tolerance": 0.15,
                "last_breach_date": "2024-01-01",
            }
        ]
    }
    with pytest.raises(AssertionError, match="japan.*diverged"):
        _assert_cross_checks("japan", summary)


def test_assert_cross_checks_allows_minor_and_agree_status() -> None:
    summary = {
        "cross_checks": [
            {"label_en": "Fake check A", "status": "minor"},
            {"label_en": "Fake check B", "status": "agree"},
        ]
    }
    _assert_cross_checks("japan", summary)  # must not raise


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


def test_source_health_report_lists_failing_sources_with_reasons() -> None:
    import importlib.util
    from pathlib import Path

    spec = importlib.util.spec_from_file_location("source_health_report", Path(__file__).resolve().parents[1] / "scripts/source_health_report.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    report = {"countries": {
        "EN": {"failed": 5, "circuit_open": 1, "events": [
            {"source_id": "ember_generation", "reason": "rate_limit", "outcome": "failed", "indicator_id": "eu_gas_power_share", "message": "Ember returned HTTP 429"},
            {"source_id": "ember_generation", "reason": "rate_limit", "outcome": "failed", "indicator_id": "eu_coal_power_share", "message": "Ember returned HTTP 429"},
            {"source_id": "ember_generation", "reason": "circuit_open", "outcome": "failed", "indicator_id": "x", "message": "Circuit open"},
        ]},
        "US": {"failed": 0, "events": [{"source_id": "fred", "outcome": "success"}]},
    }}
    lines = module.failing_sources(report)
    assert lines[0] == "EN: 5 failed CIRCUIT OPEN"
    assert lines[1].startswith("  ember_generation [rate_limit] x2 e.g. eu_gas_power_share: Ember returned HTTP 429")
    assert any("[circuit_open] x1" in line for line in lines)
    assert not any(line.startswith("US") for line in lines)
