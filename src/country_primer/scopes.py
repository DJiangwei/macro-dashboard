"""Scope registry loader (`config/scopes.yaml`).

A *scope* is one generated page: a country, a region such as the euro area, or
(later) a market page such as Energy. The registry is the only place that lists
scopes; builders, navigation, archive, audits and validation all iterate it.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[2]
SCOPES_PATH = ROOT / "config" / "scopes.yaml"
OUTPUT = ROOT / "output"

KINDS = {"country", "region", "market"}
REGIONS = {"dm", "em", "cee", "frontier", "markets"}
DEFAULT_ROLES: dict[str, tuple[str, ...]] = {
    "policy_rate": ("policy_rate",),
    "cpi_yoy": ("cpi_inflation",),
}
PIPELINES = {"data_first", "cee_v4"}
CEE_CANONICAL = "cee_canonical_frame.json"


@dataclass(frozen=True)
class Headline:
    indicators: tuple[str, ...]
    key: str
    label: str
    format: str

    def render(self, observation: dict[str, Any] | None) -> str:
        if not observation:
            return "n/a"
        return self.format.format(value=float(observation["value"]), date=observation["date"])


@dataclass(frozen=True)
class Scope:
    id: str
    kind: str
    slug: str
    name_en: str
    name_zh: str
    flag: str
    region: str
    pipeline: str
    currency: str
    institution: str
    indicators: str | None = None
    framework_label: str = ""
    headline: Headline | None = None
    fetch_workers: int = 4
    central_bank: dict[str, Any] = field(default_factory=dict, compare=False, hash=False)
    roles: dict[str, tuple[str, ...]] = field(default_factory=dict, compare=False, hash=False)
    extra: dict[str, Any] = field(default_factory=dict, compare=False, hash=False)

    def role(self, name: str) -> tuple[str, ...]:
        """Candidate indicator ids for a cross-country role (first observed wins)."""
        return self.roles.get(name) or DEFAULT_ROLES.get(name, ())

    @property
    def market_policy_rate(self) -> tuple[str, ...]:
        """Rate used for ex-post real rates: a market rate when declared, else the policy rate."""
        return self.roles.get("policy_rate_market") or self.role("policy_rate")

    @property
    def html_file(self) -> str:
        return f"{self.slug}.html"

    @property
    def html_path(self) -> Path:
        return OUTPUT / self.html_file

    @property
    def canonical_file(self) -> str:
        return CEE_CANONICAL if self.pipeline == "cee_v4" else f"{self.slug}_canonical_frame.json"

    @property
    def canonical_path(self) -> Path:
        return OUTPUT / self.canonical_file

    @property
    def summary_file(self) -> str:
        return f"{self.slug}_dashboard_summary.json"

    @property
    def summary_path(self) -> Path:
        return OUTPUT / self.summary_file

    @property
    def indicators_path(self) -> Path | None:
        return ROOT / self.indicators if self.indicators else None

    @property
    def is_data_first(self) -> bool:
        return self.pipeline == "data_first"

    @property
    def is_market(self) -> bool:
        return self.kind == "market"


def _parse(entry: dict[str, Any]) -> Scope:
    known = {
        "id", "kind", "slug", "name", "flag", "region", "pipeline", "currency", "institution",
        "indicators", "framework_label", "headline", "fetch_workers", "central_bank", "roles",
    }
    headline = entry.get("headline")
    return Scope(
        id=str(entry["id"]),
        kind=str(entry["kind"]),
        slug=str(entry["slug"]),
        name_en=str(entry["name"]["en"]),
        name_zh=str(entry["name"].get("zh") or entry["name"]["en"]),
        flag=str(entry.get("flag") or ""),
        region=str(entry.get("region") or ""),
        pipeline=str(entry["pipeline"]),
        currency=str(entry.get("currency") or ""),
        institution=str(entry.get("institution") or ""),
        indicators=entry.get("indicators"),
        framework_label=str(entry.get("framework_label") or ""),
        headline=Headline(
            indicators=tuple(headline["indicators"]),
            key=str(headline["key"]),
            label=str(headline.get("label") or ""),
            format=str(headline.get("format") or "{value} ({date})"),
        ) if headline else None,
        fetch_workers=int(entry.get("fetch_workers") or 4),
        central_bank=dict(entry.get("central_bank") or {}),
        roles={str(k): tuple(v if isinstance(v, list) else [v]) for k, v in (entry.get("roles") or {}).items()},
        extra={k: v for k, v in entry.items() if k not in known},
    )


def validate_registry(scopes: list[Scope]) -> list[str]:
    problems: list[str] = []
    for attr in ("id", "slug"):
        values = [getattr(s, attr) for s in scopes]
        dupes = sorted({v for v in values if values.count(v) > 1})
        if dupes:
            problems.append(f"duplicate {attr}: {', '.join(dupes)}")
    for s in scopes:
        if s.kind not in KINDS:
            problems.append(f"{s.id}: unknown kind {s.kind!r}")
        if s.region not in REGIONS:
            problems.append(f"{s.id}: unknown region {s.region!r}")
        if s.pipeline not in PIPELINES:
            problems.append(f"{s.id}: unknown pipeline {s.pipeline!r}")
        if s.is_market and not s.is_data_first:
            problems.append(f"{s.id}: market scopes use the data_first pipeline")
        if s.is_data_first:
            if not s.indicators_path or not s.indicators_path.exists():
                problems.append(f"{s.id}: indicator config {s.indicators!r} not found")
            if not s.headline:
                problems.append(f"{s.id}: data_first scope needs a headline")
    return problems


@lru_cache(maxsize=4)
def _load(path: str) -> tuple[Scope, ...]:
    payload = yaml.safe_load(Path(path).read_text()) or {}
    scopes = [_parse(entry) for entry in payload.get("scopes") or []]
    problems = validate_registry(scopes)
    if problems:
        raise ValueError(f"Invalid scope registry {path}: " + "; ".join(problems))
    return tuple(scopes)


def all_scopes(path: Path = SCOPES_PATH, *, include_markets: bool = False) -> list[Scope]:
    """Registered scopes in navigation order.

    Economies (countries and regions) only by default: most consumers are
    country analytics (coverage, policy, workbench). Page-level consumers
    (builds, navigation, audits, smoke checks) pass ``include_markets=True``.
    """
    return [s for s in _load(str(path)) if include_markets or not s.is_market]


def data_first_scopes(path: Path = SCOPES_PATH, *, include_markets: bool = False) -> list[Scope]:
    return [s for s in all_scopes(path, include_markets=include_markets) if s.is_data_first]


def market_scopes(path: Path = SCOPES_PATH) -> list[Scope]:
    return [s for s in _load(str(path)) if s.is_market]


def cee_scopes(path: Path = SCOPES_PATH) -> list[Scope]:
    return [s for s in all_scopes(path) if s.pipeline == "cee_v4"]


def get_scope(code: str, path: Path = SCOPES_PATH) -> Scope:
    wanted = code.strip().upper()
    for scope in all_scopes(path, include_markets=True):
        if scope.id == wanted or scope.slug == code.strip().lower():
            return scope
    raise KeyError(f"Unknown scope {code!r}; registered: {', '.join(s.id for s in all_scopes(path, include_markets=True))}")
