"""Shared macro-framework ontology and compatibility mappings."""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml


ROOT = Path(__file__).resolve().parents[2]
FRAMEWORK_PATH = ROOT / "config" / "framework_v2.yaml"
CEE_CODES = frozenset({"HU", "PL", "CZ", "RO"})


@dataclass(frozen=True)
class CoreConcept:
    concept_id: str
    pillar: str
    label_en: str
    label_zh: str
    unit: str
    mappings: dict[str, tuple[str, ...]]


@dataclass(frozen=True)
class MacroFramework:
    version: int
    pillars: dict[str, dict[str, Any]]
    concepts: tuple[CoreConcept, ...]
    legacy_aliases: dict[str, str]

    @property
    def concept_ids(self) -> frozenset[str]:
        return frozenset(item.concept_id for item in self.concepts)


def _validate_payload(payload: dict[str, Any]) -> MacroFramework:
    version = int(payload.get("version") or 0)
    if version != 2:
        raise ValueError(f"Unsupported macro framework version: {version}")

    pillars = payload.get("pillars") or {}
    if not isinstance(pillars, dict) or not pillars:
        raise ValueError("framework_v2.yaml must define pillars")

    concepts: list[CoreConcept] = []
    seen: set[str] = set()
    for raw in payload.get("concepts") or []:
        concept_id = str(raw["id"])
        if concept_id in seen:
            raise ValueError(f"Duplicate core concept: {concept_id}")
        pillar = str(raw["pillar"])
        if pillar not in pillars:
            raise ValueError(f"Unknown pillar {pillar!r} for {concept_id}")
        mappings = {
            str(scope): tuple(str(item) for item in (ids or []))
            for scope, ids in (raw.get("mappings") or {}).items()
        }
        concepts.append(CoreConcept(
            concept_id=concept_id,
            pillar=pillar,
            label_en=str(raw.get("label_en") or concept_id),
            label_zh=str(raw.get("label_zh") or raw.get("label_en") or concept_id),
            unit=str(raw.get("unit") or ""),
            mappings=mappings,
        ))
        seen.add(concept_id)

    expected = int(payload.get("core_concept_count") or len(concepts))
    if len(concepts) != expected:
        raise ValueError(f"Expected {expected} core concepts, found {len(concepts)}")

    aliases = {str(key): str(value) for key, value in (payload.get("legacy_aliases") or {}).items()}
    return MacroFramework(version=version, pillars=pillars, concepts=tuple(concepts), legacy_aliases=aliases)


@lru_cache(maxsize=1)
def load_macro_framework() -> MacroFramework:
    payload = yaml.safe_load(FRAMEWORK_PATH.read_text()) or {}
    return _validate_payload(payload)


def canonical_indicator_id(indicator_id: str) -> str:
    """Return the economically accurate ID while accepting legacy callers."""
    framework = load_macro_framework()
    return framework.legacy_aliases.get(str(indicator_id), str(indicator_id))


@lru_cache(maxsize=256)
def concept_id_for(country_code: str, indicator_id: str) -> str:
    """Map a country series to a shared core concept or a country extension."""
    framework = load_macro_framework()
    country = str(country_code).upper()
    normalized = canonical_indicator_id(indicator_id)
    scopes = (country, "CEE") if country in CEE_CODES else (country,)
    for concept in framework.concepts:
        for scope in scopes:
            mapped = {canonical_indicator_id(item) for item in concept.mappings.get(scope, ())}
            if normalized in mapped:
                return concept.concept_id
    return f"{country.lower()}:{normalized}"


def framework_summary() -> dict[str, Any]:
    framework = load_macro_framework()
    return {
        "version": framework.version,
        "pillars": len(framework.pillars),
        "core_concepts": len(framework.concepts),
        "legacy_aliases": len(framework.legacy_aliases),
    }
