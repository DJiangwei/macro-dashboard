"""Indicator templates: parameterised baseline coverage for a new scope.

A scope's indicator YAML may list templates and the parameters they need:

    templates: [sections_core, imf_baseline, bis_baseline]
    params: {iso2: IN, iso3: IND, currency: INR}
    drop: [cpi_inflation_mom]          # optional: template ids to leave out
    indicators: [...]                  # native series; same id replaces the template's

Each ``config/templates/<name>.yaml`` holds ``params`` (required names),
optional ``sections`` and ``summary_key_ids``, and ``indicators`` whose string
fields may contain ``{param}`` placeholders. Expansion only fills identifiers
(country codes, series keys, labels); every value on a page still comes from
the source the spec names.

Indicators may declare ``concept: <core concept id>``; those declarations are
merged into the framework mappings (see ``framework.load_macro_framework``),
so a templated country gets core-coverage credit without editing
``config/framework_v2.yaml``.
"""
from __future__ import annotations

import copy
import re
from datetime import date
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[2]
TEMPLATES_DIR = ROOT / "config" / "templates"
PLACEHOLDER = re.compile(r"\{([a-z_0-9]+)\}")


def default_params() -> dict[str, str]:
    # IMF WEO values after this year are projections; WEO vintages publish
    # actuals through the previous calendar year for most economies.
    return {"weo_actual_through": str(date.today().year - 1)}


def _substitute(value: Any, params: dict[str, Any], where: str) -> Any:
    if isinstance(value, str):
        def repl(match: re.Match[str]) -> str:
            name = match.group(1)
            if name not in params:
                raise KeyError(f"{where}: template parameter {{{name}}} is not set")
            return str(params[name])
        return PLACEHOLDER.sub(repl, value)
    if isinstance(value, list):
        return [_substitute(item, params, where) for item in value]
    if isinstance(value, dict):
        return {key: _substitute(item, params, where) for key, item in value.items()}
    return value


@lru_cache(maxsize=32)
def _template(name: str) -> dict[str, Any]:
    path = TEMPLATES_DIR / f"{name}.yaml"
    if not path.exists():
        raise FileNotFoundError(f"Unknown indicator template {name!r} ({path})")
    return yaml.safe_load(path.read_text()) or {}


def expand(config: dict[str, Any]) -> dict[str, Any]:
    """Return ``config`` with its templates expanded (a no-op without templates)."""
    names = list(config.get("templates") or [])
    if not names:
        return config
    params = {**default_params(), **(config.get("params") or {})}
    sections: dict[str, Any] = {}
    indicators: dict[str, dict[str, Any]] = {}
    summary_ids: list[str] = []
    for name in names:
        template = copy.deepcopy(_template(name))
        missing = [p for p in template.get("params") or [] if p not in params]
        if missing:
            raise KeyError(f"template {name!r} needs params {missing}")
        sections.update(_substitute(template.get("sections") or {}, params, name))
        for spec in template.get("indicators") or []:
            item = _substitute(spec, params, f"{name}:{spec.get('id')}")
            item["template"] = name
            indicators[str(item["id"])] = item
        summary_ids += [i for i in _substitute(template.get("summary_key_ids") or [], params, name) if i not in summary_ids]
    for spec in config.get("indicators") or []:
        indicators[str(spec["id"])] = spec  # native series override template entries
    drop = set(config.get("drop") or [])
    expanded = {k: v for k, v in config.items() if k not in {"templates", "params", "drop"}}
    expanded["sections"] = {**sections, **(config.get("sections") or {})}
    expanded["indicators"] = [spec for key, spec in indicators.items() if key not in drop]
    if not config.get("summary_key_ids"):
        expanded["summary_key_ids"] = [i for i in summary_ids if i in indicators and i not in drop]
    expanded["template_params"] = params
    expanded["templates_used"] = names
    return expanded


def load_indicator_config(path: Path) -> dict[str, Any]:
    """Read an indicator YAML and expand any templates it lists."""
    return expand(yaml.safe_load(path.read_text()) or {})


def declared_concepts() -> dict[str, dict[str, list[str]]]:
    """``concept`` tags on data-first indicator specs: {concept: {scope: [ids]}}."""
    from .scopes import data_first_scopes

    out: dict[str, dict[str, list[str]]] = {}
    for scope in data_first_scopes():
        if not scope.indicators_path or not scope.indicators_path.exists():
            continue
        for spec in load_indicator_config(scope.indicators_path).get("indicators") or []:
            concept = spec.get("concept")
            if concept:
                out.setdefault(str(concept), {}).setdefault(scope.id, []).append(str(spec["id"]))
    return out
