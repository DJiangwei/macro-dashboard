"""Compare two independent publication paths for the same concept.

This is primarily a regression test on the adapters: if a parser mis-scales a
series or selects the wrong column, the paired source diverges immediately.

``status`` is judged over a recent window (24 months by default, or an
explicit ``since`` date per pair), not full history. The reason: this check's
purpose is catching adapter defects, and those show up in *current* data — a
systematic parser error (wrong column, wrong scale, wrong geography) produces
breaches continuously, so a 24-month window catches it easily. Two
independently-compiled multi-decade series can also carry genuine, documented
historical breaks (a statistics agency restating a series, a periodic
CPI-base-year rebasing) that show up as large full-history divergence without
indicating any code defect. Gating the build on full-history status would
make ``status`` permanently ``diverged`` for those pairs regardless of
whether today's adapters are correct, training everyone to ignore the check.
The full-history fields (``n_common``, ``max_abs_diff``, ``n_breaches``,
``last_breach_date``) are kept in the output unchanged, because they are
genuinely informative context even though they no longer drive ``status``.
"""
from __future__ import annotations

from calendar import monthrange
from datetime import date
from typing import Any

DEFAULT_TOLERANCE = 0.15
MINOR_MULTIPLE = 2.0
DEFAULT_WINDOW_MONTHS = 24


def _by_date(series: dict[str, Any]) -> dict[str, float]:
    out: dict[str, float] = {}
    for item in series.get("observations") or []:
        try:
            out[str(item["date"])] = float(item["value"])
        except (KeyError, TypeError, ValueError):
            continue
    return out


def _shift_months(d: date, months: int) -> date:
    """Return ``d`` shifted back by ``months`` calendar months, day-clamped."""
    total = d.year * 12 + (d.month - 1) - months
    year, month0 = divmod(total, 12)
    month = month0 + 1
    day = min(d.day, monthrange(year, month)[1])
    return date(year, month, day)


def _parse_date(value: Any) -> date | None:
    try:
        return date.fromisoformat(str(value)[:10])
    except (TypeError, ValueError):
        return None


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

        # Resolve the recent window that actually drives `status`. An explicit
        # `since` per pair wins; otherwise it's a rolling window ending at the
        # latest common observation.
        window_since: str | None = None
        window_months: int | None = None
        since_cfg = pair.get("since")
        if since_cfg:
            window_since = str(since_cfg)
        elif diffs:
            latest_common = _parse_date(common[-1])
            if latest_common is not None:
                window_months = DEFAULT_WINDOW_MONTHS
                window_since = _shift_months(latest_common, window_months).isoformat()

        if window_since is not None:
            window_diffs = [(d, v) for d, v in diffs if d >= window_since]
        else:
            # No resolvable boundary (e.g. no common observations at all, or
            # an unparsable latest date) — fall back to the full history so a
            # genuinely empty pair still reports `insufficient` rather than a
            # silently different status.
            window_diffs = diffs

        window_breaches = [(d, v) for d, v in window_diffs if abs(v) > tolerance]
        window_max_abs = max((abs(v) for _, v in window_diffs), default=0.0)

        if not window_diffs:
            status = "insufficient"
        elif window_breaches:
            status = "diverged"
        elif window_max_abs > tolerance / MINOR_MULTIPLE:
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
            "window_since": window_since,
            "window_months": window_months,
            "window_n_common": len(window_diffs),
            "window_max_abs_diff": window_max_abs,
            "window_n_breaches": len(window_breaches),
            "status": status,
        })
    return results
