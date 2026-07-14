import requests

from country_primer.source_health import (
    SourceCircuitOpen,
    SourceHealthRegistry,
    classify_failure,
)


def test_failure_classification_distinguishes_network_and_schema() -> None:
    assert classify_failure(requests.Timeout("slow")) == "timeout"
    assert classify_failure(requests.ConnectionError("offline")) == "connection"
    assert classify_failure(ValueError("bad value")) == "schema_error"
    assert classify_failure(SourceCircuitOpen("open")) == "circuit_open"


def test_circuit_breaker_opens_only_after_repeated_network_failures() -> None:
    registry = SourceHealthRegistry(failure_threshold=2, reset_after_seconds=300)
    registry.record(
        country="US", indicator_id="one", source_id="fred", outcome="failed",
        reason="schema_error", message="bad field",
    )
    assert not registry.is_open("fred")
    for indicator_id in ("two", "three"):
        registry.record(
            country="US", indicator_id=indicator_id, source_id="fred", outcome="failed",
            reason="timeout", message="slow",
        )
    assert registry.is_open("fred")
    report = registry.country_report("US")
    assert report["failed"] == 3
    assert report["failure_reasons"] == {"schema_error": 1, "timeout": 2}


def test_success_resets_consecutive_network_failures() -> None:
    registry = SourceHealthRegistry(failure_threshold=2, reset_after_seconds=300)
    registry.record(
        country="UK", indicator_id="one", source_id="ons", outcome="failed",
        reason="timeout", message="slow",
    )
    registry.record(
        country="UK", indicator_id="two", source_id="ons", outcome="success",
    )
    registry.record(
        country="UK", indicator_id="three", source_id="ons", outcome="failed",
        reason="timeout", message="slow again",
    )
    assert not registry.is_open("ons")


def test_empty_responses_are_not_reported_as_failures() -> None:
    registry = SourceHealthRegistry()
    registry.record(
        country="CZ", indicator_id="one", source_id="ecb", outcome="empty",
        reason="empty_response", message="none",
    )
    report = registry.country_report("CZ")
    assert report["empty"] == 1
    assert report["failed"] == 0
    assert report["failure_reasons"] == {}
    assert report["empty_reasons"] == {"empty_response": 1}
