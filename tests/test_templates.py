"""Indicator templates (F1): expansion contract and the two-file scope add."""
from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from country_primer.framework import load_macro_framework  # noqa: E402
from country_primer.indicator_templates import TEMPLATES_DIR, expand, load_indicator_config  # noqa: E402
from country_primer.scopes import data_first_scopes  # noqa: E402

REQUIRED = {"id", "section", "label_en", "label_zh", "unit", "fetcher", "source_name", "source_url", "frequency"}


def _templated():
    for scope in data_first_scopes():
        raw = (scope.indicators_path.read_text())
        if "templates:" in raw:
            yield scope, load_indicator_config(scope.indicators_path)


def test_templated_specs_are_complete_and_resolved():
    concepts = load_macro_framework().concept_ids
    problems = []
    for scope, config in _templated():
        sections = set(config.get("sections") or {})
        for spec in config["indicators"]:
            missing = REQUIRED - set(spec)
            if missing:
                problems.append(f"{scope.id}:{spec.get('id')} missing {sorted(missing)}")
            if spec.get("section") not in sections:
                problems.append(f"{scope.id}:{spec['id']} unknown section {spec.get('section')}")
            if spec.get("concept") and spec["concept"] not in concepts:
                problems.append(f"{scope.id}:{spec['id']} unknown concept {spec['concept']}")
            leftovers = [v for v in spec.values() if isinstance(v, str) and re.search(r"\{[a-z_0-9]+\}", v)]
            if leftovers:
                problems.append(f"{scope.id}:{spec['id']} unresolved placeholders {leftovers}")
    assert not problems, "; ".join(problems)


def test_native_indicator_replaces_template_entry_and_drop_removes():
    config = {
        "templates": ["fred_fx"],
        "params": {"fred_fx": "DEXINUS", "ccy": "inr", "currency": "INR"},
        "indicators": [{"id": "usd_inr", "fetcher": "bis_fx", "series": "IN"}],
    }
    expanded = expand(config)
    assert [s["fetcher"] for s in expanded["indicators"]] == ["bis_fx"]
    assert expand({**config, "indicators": [], "drop": ["usd_inr"]})["indicators"] == []


def test_missing_parameter_is_an_error():
    with pytest.raises(KeyError):
        expand({"templates": ["imf_baseline"], "params": {}})


def test_templates_declare_their_parameters():
    import yaml
    for path in TEMPLATES_DIR.glob("*.yaml"):
        payload = yaml.safe_load(path.read_text()) or {}
        used = set(re.findall(r"\{([a-z_0-9]+)\}", path.read_text())) - {"weo_actual_through"}
        assert used <= set(payload.get("params") or []), f"{path.name} uses undeclared params {used - set(payload.get('params') or [])}"


def test_templated_scope_needs_no_code_changes():
    """A templated scope is one registry entry plus its YAML: no code names it."""
    sources = [*ROOT.glob("scripts/*.py"), *ROOT.glob("src/country_primer/*.py"), ROOT / "build_v4.py"]
    for scope, _ in _templated():
        slug = re.escape(scope.slug)
        # Identifiers, file names and quoted codes; prose mentions are fine.
        pattern = re.compile(rf"[\"']{slug}[\"']|\b{slug}(_canonical|_dashboard|_indicators|\.html)")
        hits = [p.name for p in sources if pattern.search(p.read_text())]
        assert not hits, f"{scope.id} ({scope.slug}) is hard-coded in {hits}"
