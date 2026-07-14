"""Source-level diagnostics and conservative circuit breaking for refreshes."""
from __future__ import annotations

from collections import Counter, defaultdict
from datetime import UTC, datetime, timedelta
import json
from pathlib import Path
import re
from threading import Lock
from typing import Any, Callable, TypeVar

import requests


T = TypeVar("T")
TRIPPING_REASONS = {"timeout", "rate_limit", "authentication", "connection"}


class SourceCircuitOpen(RuntimeError):
    pass


def _safe_message(value: object) -> str:
    text = " ".join(str(value or "").split())
    text = re.sub(
        r"(?i)(api[_-]?key|access[_-]?token|token|key)(=|%3D)[^&\s]+",
        r"\1\2[redacted]",
        text,
    )
    return text[:500]


def classify_failure(exc: BaseException) -> str:
    status = getattr(getattr(exc, "response", None), "status_code", None)
    if status == 429:
        return "rate_limit"
    if status in {401, 403}:
        return "authentication"
    if isinstance(exc, requests.Timeout) or "timed out" in str(exc).lower():
        return "timeout"
    if isinstance(exc, requests.ConnectionError):
        return "connection"
    if isinstance(exc, (json.JSONDecodeError, UnicodeDecodeError)):
        return "parse_error"
    if isinstance(exc, (KeyError, TypeError, ValueError)):
        return "schema_error"
    if isinstance(exc, SourceCircuitOpen):
        return "circuit_open"
    if status is not None:
        return "http_error"
    return "unexpected_error"


class SourceHealthRegistry:
    def __init__(self, *, failure_threshold: int = 4, reset_after_seconds: int = 300) -> None:
        self.failure_threshold = failure_threshold
        self.reset_after = timedelta(seconds=reset_after_seconds)
        self._lock = Lock()
        self._states: dict[str, dict[str, Any]] = {}
        self._events: list[dict[str, Any]] = []

    def reset(self) -> None:
        with self._lock:
            self._states.clear()
            self._events.clear()

    def _state(self, source_id: str) -> dict[str, Any]:
        return self._states.setdefault(source_id, {
            "consecutive_network_failures": 0,
            "opened_at": None,
        })

    def is_open(self, source_id: str) -> bool:
        with self._lock:
            state = self._state(source_id)
            opened_at = state.get("opened_at")
            if not opened_at:
                return False
            if datetime.now(UTC) - opened_at >= self.reset_after:
                state["opened_at"] = None
                state["consecutive_network_failures"] = 0
                return False
            return True

    def record(
        self,
        *,
        country: str,
        indicator_id: str,
        source_id: str,
        outcome: str,
        reason: str = "",
        message: str = "",
    ) -> None:
        with self._lock:
            state = self._state(source_id)
            if outcome in {"success", "empty"}:
                state["consecutive_network_failures"] = 0
                state["opened_at"] = None
            elif reason in TRIPPING_REASONS:
                state["consecutive_network_failures"] += 1
                if state["consecutive_network_failures"] >= self.failure_threshold:
                    state["opened_at"] = datetime.now(UTC)
            self._events.append({
                "timestamp": datetime.now(UTC).isoformat(),
                "country": country,
                "indicator_id": indicator_id,
                "source_id": source_id,
                "outcome": outcome,
                "reason": reason,
                "message": _safe_message(message),
            })

    def country_report(self, country: str) -> dict[str, Any]:
        with self._lock:
            events = [dict(item) for item in self._events if item["country"] == country]
        reasons = Counter(
            item["reason"] for item in events
            if item["outcome"] == "failed" and item["reason"]
        )
        empty_reasons = Counter(
            item["reason"] for item in events
            if item["outcome"] == "empty" and item["reason"]
        )
        sources: dict[str, Counter[str]] = defaultdict(Counter)
        for event in events:
            sources[event["source_id"]][event["outcome"]] += 1
        return {
            "calls": len(events),
            "success": sum(item["outcome"] == "success" for item in events),
            "empty": sum(item["outcome"] == "empty" for item in events),
            "failed": sum(item["outcome"] == "failed" for item in events),
            "circuit_open": sum(item["reason"] == "circuit_open" for item in events),
            "failure_reasons": dict(sorted(reasons.items())),
            "empty_reasons": dict(sorted(empty_reasons.items())),
            "sources": {
                source: dict(sorted(counts.items()))
                for source, counts in sorted(sources.items())
            },
            "events": [
                item for item in events
                if item["outcome"] == "failed"
            ][-200:],
        }


SOURCE_HEALTH = SourceHealthRegistry()


def guarded_source_call(
    *,
    country: str,
    indicator_id: str,
    source_id: str,
    operation: Callable[[], T],
    record_empty: bool = True,
) -> T:
    if SOURCE_HEALTH.is_open(source_id):
        exc = SourceCircuitOpen(f"Circuit open for source {source_id}")
        SOURCE_HEALTH.record(
            country=country,
            indicator_id=indicator_id,
            source_id=source_id,
            outcome="failed",
            reason="circuit_open",
            message=str(exc),
        )
        raise exc
    try:
        result = operation()
    except Exception as exc:
        SOURCE_HEALTH.record(
            country=country,
            indicator_id=indicator_id,
            source_id=source_id,
            outcome="failed",
            reason=classify_failure(exc),
            message=str(exc),
        )
        raise

    is_empty = False
    if record_empty:
        if isinstance(result, dict) and "observations" in result:
            is_empty = not result.get("observations")
        elif isinstance(result, list):
            is_empty = not result
    SOURCE_HEALTH.record(
        country=country,
        indicator_id=indicator_id,
        source_id=source_id,
        outcome="empty" if is_empty else "success",
        reason="empty_response" if is_empty else "",
        message="Source returned no observations." if is_empty else "",
    )
    return result


def failure_series(spec: dict[str, Any], exc: BaseException) -> dict[str, Any]:
    reason = classify_failure(exc)
    return {
        **spec,
        "observations": [],
        "quality_status": "unavailable",
        "quality_notes": [f"Fetch failed [{reason}]: {_safe_message(exc)}"],
        "failure_reason": reason,
    }


def write_source_health_report(path: Path, countries: list[str]) -> Path:
    existing: dict[str, Any] = {}
    if path.exists():
        try:
            existing = json.loads(path.read_text())
        except (json.JSONDecodeError, OSError):
            existing = {}
    country_payload = dict(existing.get("countries") or {})
    for country in countries:
        country_payload[country] = SOURCE_HEALTH.country_report(country)
    payload = {
        "schema_version": "source-health-v1",
        "generated": datetime.now(UTC).isoformat(),
        "circuit_breaker": {
            "failure_threshold": SOURCE_HEALTH.failure_threshold,
            "reset_after_seconds": int(SOURCE_HEALTH.reset_after.total_seconds()),
            "tripping_reasons": sorted(TRIPPING_REASONS),
        },
        "countries": country_payload,
    }
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")
    return path
