"""Indicator catalog — loads YAML, resolves placeholders, lists all queries to prefetch."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

CONFIG_DIR = Path(__file__).resolve().parents[2] / "config"


def load_yaml(name: str) -> Any:
    return yaml.safe_load((CONFIG_DIR / name).read_text())


@dataclass
class Indicator:
    key: str
    label: str
    mcp_query: str
    chart: str
    section_id: str
    cycle_role: str = ""
    peers: bool = False
    target_band: bool = False
    derived_yoy: bool = False
    special: str = ""
    unit: str = ""
    quality: dict[str, Any] | None = None


@dataclass
class Section:
    id: str
    title: str
    kind: str
    indicators: list[Indicator]
    blurb: str = ""


def load_countries() -> dict:
    return load_yaml("countries.yaml")


def load_sections() -> list[Section]:
    raw = load_yaml("indicators.yaml")
    sections: list[Section] = []
    for s in raw["sections"]:
        inds = []
        for i in s.get("indicators", []) or []:
            inds.append(Indicator(
                key=i["key"],
                label=i["label"],
                mcp_query=i["mcp_query"],
                chart=i["chart"],
                section_id=s["id"],
                cycle_role=i.get("cycle_role", ""),
                peers=i.get("peers", False),
                target_band=i.get("target_band", False),
                derived_yoy=i.get("derived_yoy", False),
                special=i.get("special", ""),
                unit=i.get("unit", ""),
                quality=i.get("quality"),
            ))
        sections.append(Section(
            id=s["id"], title=s["title"], kind=s["kind"],
            indicators=inds, blurb=s.get("blurb", ""),
        ))
    return sections


def resolve_query(template: str, country_meta: dict) -> str:
    return template.format(
        country=country_meta["name"],
        iso2=country_meta["iso2"],
        currency=country_meta["currency"],
        equity_index=country_meta.get("equity_index", ""),
    )


def all_queries(country_iso: str, peers: list[str], countries: dict) -> list[tuple[str, str, str]]:
    """Return list of (query_string, indicator_key, country_iso) to prefetch."""
    sections = load_sections()
    out: list[tuple[str, str, str]] = []
    for s in sections:
        for ind in s.indicators:
            for c in [country_iso, *(peers if ind.peers else [])]:
                meta = countries.get(c)
                if not meta:
                    continue
                q = resolve_query(ind.mcp_query, meta)
                out.append((q, ind.key, c))
    return out
