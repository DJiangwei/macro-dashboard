"""Fetchers shared by every data-first scope.

Each builder merges ``SHARED_FETCHERS`` into its registry, so a source added
here becomes available to all country configs at once. This is the first
step towards the single global fetcher registry described in
docs/superpowers/specs/2026-11-04-scope-framework-and-markets-design.md.
"""
from __future__ import annotations

from typing import Any, Callable

from .adapters import fetch_bis_credit_gap, fetch_bis_fx, fetch_bis_policy_rate

SHARED_FETCHERS: dict[str, Callable[[dict[str, Any], dict[str, Any]], dict[str, Any]]] = {
    "bis_policy_rate": lambda spec, cache: fetch_bis_policy_rate(spec),
    "bis_credit_gap": lambda spec, cache: fetch_bis_credit_gap(spec),
    "bis_fx": lambda spec, cache: fetch_bis_fx(spec),
}
