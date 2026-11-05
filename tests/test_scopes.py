"""Scope registry and global fetcher registry contracts (F1)."""
from __future__ import annotations

import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT / "src", ROOT / "scripts"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from country_primer import fetchers  # noqa: E402
from country_primer.indicator_templates import load_indicator_config  # noqa: E402
from country_primer.scopes import Headline, all_scopes, data_first_scopes, get_scope, validate_registry  # noqa: E402

US_TRANSFORMS = {"yoy_pct", "yoy", "diff", "pct_change"}


def _configs():
    for scope in data_first_scopes(include_markets=True):
        yield scope, load_indicator_config(scope.indicators_path)


def test_registry_is_valid_and_ordered():
    scopes = all_scopes()
    assert validate_registry(scopes) == []
    assert [s.id for s in scopes][:4] == ["HU", "PL", "CZ", "RO"]
    assert get_scope("uk").id == "UK" and get_scope("TR").slug == "turkey"


def test_every_configured_fetcher_is_registered():
    missing = []
    for scope, config in _configs():
        for item in [*config.get("indicators", []), *config.get("latest_cards", [])]:
            name = item.get("fetcher") or "pbc_card"
            if name not in fetchers.FETCHERS and name not in {"manual", "derived"}:
                missing.append(f"{scope.id}:{item.get('id')} -> {name}")
    assert not missing, "Unregistered fetchers: " + ", ".join(missing)


def test_every_registered_fetcher_resolves_to_an_adapter():
    import importlib
    for name, d in fetchers.FETCHERS.items():
        module = importlib.import_module(f"country_primer.{d.module}")
        assert callable(getattr(module, d.function, None)), name


def test_transform_names_are_understood():
    """Non-raw fetchers wipe a series whose transform name is unknown; catch typos here instead."""
    allowed = US_TRANSFORMS | fetchers.NATIVE_TRANSFORMS
    bad = []
    for scope, config in _configs():
        for item in config.get("indicators", []):
            definition = fetchers.FETCHERS.get(item.get("fetcher"))
            transform = item.get("transform")
            if definition and definition.post != fetchers.RAW and transform and transform not in allowed:
                bad.append(f"{scope.id}:{item['id']} transform={transform}")
            # fetch_fred applies a UK-style "yoy" itself when FRED_API_KEY is set,
            # so the registry would apply it a second time.
            if item.get("fetcher") == "fred" and transform == "yoy":
                bad.append(f"{scope.id}:{item['id']} uses 'yoy' with fred; use 'yoy_pct'")
    assert not bad, "; ".join(bad)


def test_every_data_first_scope_has_summary_ids_and_a_headline_series():
    problems = []
    for scope, config in _configs():
        ids = {str(item.get("id")) for item in config.get("indicators", [])}
        if not config.get("summary_key_ids"):
            problems.append(f"{scope.id}: no summary_key_ids")
        if not any(i in ids for i in scope.headline.indicators):
            problems.append(f"{scope.id}: headline {scope.headline.indicators} not in indicator config")
    assert not problems, "; ".join(problems)


def test_headline_render():
    headline = Headline(indicators=("usd_ngn",), key="usd_ngn_latest", label="", format="{value:,.2f} ({date})")
    assert headline.render({"date": "2026-10-31", "value": 1462.5}) == "1,462.50 (2026-10-31)"
    assert headline.render(None) == "n/a"


def test_postprocess_keeps_native_transforms_and_wipes_unknown_ones():
    series = {"transform": "usd_trn", "observations": [{"date": "2025", "value": 1.5}]}
    assert fetchers.postprocess(series, fetchers.TRANSFORM) == series
    wiped = fetchers.postprocess({"transform": "yoyy", "observations": [{"date": "2025-01-01", "value": 1.0}]}, fetchers.TRANSFORM)
    assert wiped["observations"] == [] and wiped["quality_status"] == "unavailable"
    scaled = fetchers.postprocess({"scale": 1000, "observations": [{"date": "2025-01-01", "value": 5000.0}]}, fetchers.SCALE_TRANSFORM)
    assert scaled["observations"][0]["value"] == 5.0
