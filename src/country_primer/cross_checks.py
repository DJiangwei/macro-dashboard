"""Compare two independent publication paths for the same concept.

This is primarily a regression test on the adapters: if a parser mis-scales a
series or selects the wrong column, the paired source diverges immediately.
"""
from __future__ import annotations

from typing import Any

DEFAULT_TOLERANCE = 0.15
MINOR_MULTIPLE = 2.0


def _by_date(series: dict[str, Any]) -> dict[str, float]:
    out: dict[str, float] = {}
    for item in series.get("observations") or []:
        try:
            out[str(item["date"])] = float(item["value"])
        except (KeyError, TypeError, ValueError):
            continue
    return out


def evaluate_cross_checks(config: dict[str, Any], series_list: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_id = {str(item.get("id")): item for item in series_list}
    results: list[dict[str, Any]] = []
    for pair in config.get("cross_checks") or []:
        primary = by_id.get(str(pair.get("primary")))
        secondary = by_id.get(str(pair.get("secondary")))
        if not primary or not secondary:
            continue
        tolerance = float(pair.get("tolerance") or DEFAULT_TOLERANCE)
        left, right = _by_date(primary), _by_date(secondary)
        common = sorted(set(left) & set(right))
        diffs = [(d, left[d] - right[d]) for d in common]
        breaches = [(d, v) for d, v in diffs if abs(v) > tolerance]
        max_abs = max((abs(v) for _, v in diffs), default=0.0)
        if not diffs:
            status = "insufficient"
        elif breaches:
            status = "diverged"
        elif max_abs > tolerance / MINOR_MULTIPLE:
            status = "minor"
        else:
            status = "agree"
        results.append({
            "concept": str(pair.get("concept") or ""),
            "primary": str(pair.get("primary")),
            "secondary": str(pair.get("secondary")),
            "label_en": str(pair.get("label_en") or ""),
            "n_common": len(common),
            "latest_diff": diffs[-1][1] if diffs else None,
            "max_abs_diff": max_abs,
            "n_breaches": len(breaches),
            "last_breach_date": breaches[-1][0] if breaches else "",
            "tolerance": tolerance,
            "status": status,
        })
    return results
