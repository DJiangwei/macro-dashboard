"""Derived series from whitelisted operators (spec §2.6).

An indicator with ``derivation: derived`` names an ``op`` and its ``inputs``;
no free-form code is evaluated. Inputs are ids in the same scope, optionally
``<SCOPE>:<id>`` for another scope's canonical frame, and may carry a
``@monthly_mean`` resample suffix. Every output records its formula and the
last observation date of each input, and is computed only on dates where all
inputs are observed: missing data stays missing.

Operators
---------
spread                a - b
linear                sum(weights[i] * x_i)            (weights: [...])
ratio                 a / b * factor                   (factor: 1)
rolling_mean          trailing mean over `window` observations
zscore                (x - trailing mean) / trailing std over `window` observations
dev_from_5y_seasonal  x minus the mean of the same ISO week (or month) in the
                      previous five years (at least three years required)
yoy_pct               percent change versus the same period a year earlier
"""
from __future__ import annotations

import json
import math
from collections import defaultdict
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any, Callable

OPERATORS = {"spread", "linear", "ratio", "rolling_mean", "zscore", "dev_from_5y_seasonal", "yoy_pct"}
RESAMPLERS = {"monthly_mean"}


def _points(observations: list[Any]) -> list[tuple[str, float]]:
    out = []
    for row in observations or []:
        if isinstance(row, dict):
            d, v = row.get("date"), row.get("value")
        elif isinstance(row, (list, tuple)) and len(row) >= 2:
            d, v = row[0], row[1]
        else:
            continue
        if v is None:
            continue
        try:
            out.append((str(d)[:10], float(v)))
        except (TypeError, ValueError):
            continue
    return sorted(out)


def monthly_mean(points: list[tuple[str, float]]) -> list[tuple[str, float]]:
    """Calendar-month means; the current (incomplete) month is left out."""
    current = datetime.now(UTC).strftime("%Y-%m")
    buckets: dict[str, list[float]] = defaultdict(list)
    for d, v in points:
        buckets[d[:7]].append(v)
    return [(f"{m}-01", sum(vs) / len(vs)) for m, vs in sorted(buckets.items()) if m < current]


def _aligned(series: list[list[tuple[str, float]]]) -> list[tuple[str, list[float]]]:
    maps = [dict(s) for s in series]
    common = sorted(set(maps[0]).intersection(*maps[1:])) if maps else []
    return [(d, [m[d] for m in maps]) for d in common]


def _period_key(d: str, weekly: bool) -> tuple[int, int]:
    day = date.fromisoformat(d)
    return (day.isocalendar()[0], day.isocalendar()[1]) if weekly else (day.year, day.month)


def _dev_from_5y(points: list[tuple[str, float]]) -> list[tuple[str, float]]:
    if len(points) < 2:
        return []
    gaps = [(date.fromisoformat(b[0]) - date.fromisoformat(a[0])).days for a, b in zip(points, points[1:])]
    weekly = sorted(gaps)[len(gaps) // 2] <= 10
    by_key = {_period_key(d, weekly): v for d, v in points}
    out = []
    for d, v in points:
        year, sub = _period_key(d, weekly)
        history = [by_key[(year - k, sub)] for k in range(1, 6) if (year - k, sub) in by_key]
        if len(history) >= 3:
            out.append((d, v - sum(history) / len(history)))
    return out


def _rolling(points: list[tuple[str, float]], window: int, fn: Callable[[list[float]], float | None]) -> list[tuple[str, float]]:
    out = []
    values = [v for _, v in points]
    for i in range(window - 1, len(points)):
        result = fn(values[i - window + 1:i + 1])
        if result is not None:
            out.append((points[i][0], result))
    return out


def _zscore(window_values: list[float]) -> float | None:
    n = len(window_values)
    mean = sum(window_values) / n
    var = sum((x - mean) ** 2 for x in window_values) / (n - 1) if n > 1 else 0.0
    return (window_values[-1] - mean) / math.sqrt(var) if var > 0 else None


def _yoy(points: list[tuple[str, float]]) -> list[tuple[str, float]]:
    by_date = dict(points)
    out = []
    for d, v in points:
        base = by_date.get(f"{int(d[:4]) - 1:04d}{d[4:]}")
        if base:
            out.append((d, (v / base - 1.0) * 100.0))
    return out


def apply_op(op: str, inputs: list[list[tuple[str, float]]], spec: dict[str, Any]) -> list[tuple[str, float]]:
    if op not in OPERATORS:
        raise ValueError(f"Operator {op!r} is not whitelisted ({sorted(OPERATORS)})")
    if op == "spread":
        return [(d, a - b) for d, (a, b) in _aligned(inputs)]
    if op == "linear":
        weights = [float(w) for w in spec["weights"]]
        if len(weights) != len(inputs):
            raise ValueError("linear: one weight per input")
        return [(d, sum(w * x for w, x in zip(weights, xs))) for d, xs in _aligned(inputs)]
    if op == "ratio":
        factor = float(spec.get("factor", 1.0))
        return [(d, a / b * factor) for d, (a, b) in _aligned(inputs) if b]
    if op == "rolling_mean":
        return _rolling(inputs[0], int(spec["window"]), lambda xs: sum(xs) / len(xs))
    if op == "zscore":
        return _rolling(inputs[0], int(spec["window"]), _zscore)
    if op == "dev_from_5y_seasonal":
        return _dev_from_5y(inputs[0])
    return _yoy(inputs[0])


def _resolve_input(ref: str, local: dict[str, dict[str, Any]], frames: Callable[[str], dict[str, Any]]) -> tuple[list[tuple[str, float]], str] | None:
    name, _, resample = ref.partition("@")
    if resample and resample not in RESAMPLERS:
        raise ValueError(f"Resampler {resample!r} is not whitelisted")
    if ":" in name:
        scope, indicator = name.split(":", 1)
        series = frames(scope).get(indicator)
    else:
        series = local.get(name)
    if not series:
        return None
    points = _points(series.get("observations") or [])
    if resample == "monthly_mean":
        points = monthly_mean(points)
    return (points, points[-1][0]) if points else None


def _frame_loader(output_dir: Path) -> Callable[[str], dict[str, Any]]:
    from .scopes import get_scope

    cache: dict[str, dict[str, Any]] = {}

    def load(scope_code: str) -> dict[str, Any]:
        if scope_code not in cache:
            scope = get_scope(scope_code)
            path = output_dir / scope.canonical_file
            payload = json.loads(path.read_text()) if path.exists() else {}
            cache[scope_code] = {
                str(s.get("indicator_id")): s for s in payload.get("series") or []
                if scope.pipeline != "cee_v4" or str(s.get("country") or "").upper() == scope_code
            }
        return cache[scope_code]

    return load


def formula(spec: dict[str, Any]) -> str:
    op, inputs = spec["op"], list(spec.get("inputs") or [])
    if op == "linear":
        return " + ".join(f"{w}×{i}" for w, i in zip(spec["weights"], inputs))
    if op in {"rolling_mean", "zscore"}:
        return f"{op}({inputs[0]}, window={spec['window']})"
    if op == "ratio" and spec.get("factor", 1) != 1:
        return f"{inputs[0]} / {inputs[1]} × {spec['factor']}"
    if op == "spread":
        return f"{inputs[0]} − {inputs[1]}"
    return f"{op}({', '.join(inputs)})"


AUTHORITY_ORDER = ["official_primary", "official_mirror", "public_secondary", "public_wrapper", "manual_curated"]


def _provenance(refs: list[str], local: dict[str, dict[str, Any]]) -> tuple[str, str, str]:
    """Source names, first URL and the weakest authority of the inputs on this page."""
    from .data_quality import source_authority

    names, urls, authorities = [], [], []
    for ref in refs:
        name = ref.partition("@")[0]
        item = local.get(name)
        if item is None:
            continue
        names.append(str(item.get("source_name") or name))
        urls.append(str(item.get("source_url") or ""))
        authorities.append(source_authority(item.get("source_name"), item.get("source_url"), item.get("source_authority")))
    worst = max(authorities, key=lambda a: AUTHORITY_ORDER.index(a) if a in AUTHORITY_ORDER else 2, default="public_secondary")
    unique = list(dict.fromkeys(names))
    return ("Derived from " + "; ".join(unique)) if unique else "Derived", next((u for u in urls if u), ""), worst


def apply_derivations(series_list: list[dict[str, Any]], output_dir: Path) -> list[dict[str, Any]]:
    """Compute every ``derivation: derived`` spec; iterate until dependencies settle."""
    by_id = {str(item.get("id")): item for item in series_list}
    pending = [item for item in series_list if item.get("derivation") == "derived" and item.get("op")]
    frames = _frame_loader(output_dir)
    computed: dict[str, dict[str, Any]] = {}
    for _ in range(len(pending) + 1):
        progressed = False
        for spec in pending:
            sid = str(spec["id"])
            if sid in computed:
                continue
            refs = [str(r) for r in spec.get("inputs") or []]
            local_deps = [r.partition("@")[0] for r in refs if ":" not in r.partition("@")[0]]
            if any(dep in {str(p["id"]) for p in pending} and dep not in computed for dep in local_deps):
                continue  # wait for a derived input
            current = {**by_id, **computed}
            resolved = [_resolve_input(r, current, frames) for r in refs]
            vintages = {r: (res[1] if res else None) for r, res in zip(refs, resolved)}
            points = apply_op(spec["op"], [res[0] for res in resolved], spec) if all(resolved) else []
            note = f"Derived: {formula(spec)}. Inputs (last observation): " + ", ".join(f"{r} @ {v or 'missing'}" for r, v in vintages.items()) + "."
            source_name, source_url, authority = _provenance(refs, current)
            computed[sid] = {
                **spec,
                "observations": [{"date": d, "value": round(v, 6)} for d, v in points],
                "provider_updated": max((v for v in vintages.values() if v), default=""),
                # Provenance always comes from the inputs (a snapshot rebuild would
                # otherwise carry a stale name forward); never above the weakest input.
                "source_name": source_name,
                "source_url": source_url,
                "source_authority": authority,
                "derivation_formula": formula(spec),
                "series": formula(spec),
                "derivation_inputs": vintages,
                "quality_notes": [note],
                "quality_status": None if points else "unavailable",
            }
            if computed[sid]["quality_status"] is None:
                computed[sid].pop("quality_status")
            progressed = True
        if not progressed:
            break
    unresolved = [str(s["id"]) for s in pending if str(s["id"]) not in computed]
    if unresolved:
        raise ValueError(f"Derived series with circular or missing derived inputs: {unresolved}")
    return [computed.get(str(item.get("id")), item) for item in series_list]
