#!/usr/bin/env python3
"""Build data-first scope pages from the scope registry.

    build_scope.py TR                 # one scope (id or slug)
    build_scope.py CN US --snapshot   # several scopes from the committed canonical frames
    build_scope.py --all              # every data_first scope in config/scopes.yaml

Data mode comes from ``--snapshot`` or ``COUNTRY_PRIMER_DATA_MODE`` (``refresh``
by default). A refresh fetches every indicator through the global fetcher
registry, keeps the last known good observations for anything that failed and
tracks revisions; a snapshot rebuild re-renders from the canonical frame without
network access.

This replaces the fourteen ``build_<country>_dashboard.py`` scripts, which
differed only in the values now held in ``config/scopes.yaml`` and the indicator
YAMLs.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = ROOT / "scripts"
for path in (SCRIPTS_DIR, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from dashboard_summary_utils import (  # noqa: E402
    load_canonical_data_first_frame,
    retain_last_known_good_series,
    track_revisions_and_vintages,
)
from country_primer.data_first_pipeline import fetch_all  # noqa: E402
from country_primer.fetchers import build_registry  # noqa: E402
from country_primer.indicator_templates import load_indicator_config  # noqa: E402
from country_primer.page_renderer import _latest, build_country_page  # noqa: E402
from country_primer.scopes import Scope, data_first_scopes, get_scope  # noqa: E402
from country_primer.source_health import SOURCE_HEALTH  # noqa: E402


def load_config(scope: Scope) -> dict[str, Any]:
    assert scope.indicators_path is not None
    return load_indicator_config(scope.indicators_path)


def _snapshot_cards(scope: Scope, config: dict[str, Any]) -> list[dict[str, Any]]:
    """Latest-value cards are only fetched on refresh; a snapshot keeps the last ones."""
    previous = json.loads(scope.summary_path.read_text()) if scope.summary_path.exists() else {}
    if previous.get("latest_cards"):
        return list(previous["latest_cards"])
    return [{**card, "value": "n/a", "updated": "n/a"} for card in config.get("latest_cards", [])]


def _headline(scope: Scope, charted: list[dict[str, Any]]) -> str:
    assert scope.headline is not None
    by_id = {item["id"]: item for item in charted}
    item = next((by_id[i] for i in scope.headline.indicators if i in by_id), None)
    return scope.headline.render(_latest(item) if item else None)


def build(scope: Scope, data_mode: str) -> Path:
    if not scope.is_data_first:
        raise ValueError(f"{scope.id} uses the {scope.pipeline} pipeline; build it with build_v4.py")
    scope.html_path.parent.mkdir(parents=True, exist_ok=True)
    config = load_config(scope)

    if data_mode == "snapshot":
        series_list = load_canonical_data_first_frame(scope.canonical_path, config)
        cards = _snapshot_cards(scope, config)
    else:
        SOURCE_HEALTH.reset()
        series_list, cards = fetch_all(config, build_registry(), max_workers=scope.fetch_workers, country=scope.id)
        series_list = retain_last_known_good_series(series_list, scope.canonical_path, config)
        series_list = track_revisions_and_vintages(series_list, scope.canonical_path, config)

    charted = [item for item in series_list if item.get("observations")]
    min_chart_count = config.get("min_chart_count")
    if min_chart_count is not None and len(charted) < int(min_chart_count):
        unavailable = [item["id"] for item in series_list if not item.get("observations")]
        raise RuntimeError(
            f"{scope.id}: only {len(charted)} charts, below min_chart_count {min_chart_count}; "
            f"page not written. Unavailable: {', '.join(unavailable[:12])}{'...' if len(unavailable) > 12 else ''}"
        )

    assert scope.headline is not None
    build_country_page(
        country_code=scope.id,
        config=config,
        series_list=series_list,
        out_html=scope.html_path,
        summary_json=scope.summary_path,
        canonical_json=scope.canonical_path,
        data_mode=data_mode,
        summary_key_ids=list(config.get("summary_key_ids") or []),
        extra_cards=cards,
        latest_value_key=scope.headline.key,
        latest_value_display=_headline(scope, charted),
    )
    return scope.html_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("scopes", nargs="*", help="scope ids or slugs (see config/scopes.yaml)")
    parser.add_argument("--all", action="store_true", help="build every data_first scope")
    parser.add_argument("--snapshot", action="store_true", help="rebuild from committed canonical frames")
    args = parser.parse_args(argv)

    if args.all == bool(args.scopes):
        parser.error("name one or more scopes, or pass --all")
    selected = data_first_scopes() if args.all else [get_scope(code) for code in args.scopes]
    data_mode = "snapshot" if args.snapshot else (os.environ.get("COUNTRY_PRIMER_DATA_MODE") or "refresh").strip().lower()

    failures: list[str] = []
    for scope in selected:
        started = time.monotonic()
        try:
            path = build(scope, data_mode)
        except Exception as exc:  # keep building the other scopes; report at the end
            failures.append(f"{scope.id}: {exc}")
            print(f"FAILED {scope.id}: {exc}", file=sys.stderr)
            continue
        print(f"Wrote {path} ({path.stat().st_size:,} bytes, {time.monotonic() - started:.1f}s)")

    if not os.environ.get("COUNTRY_PRIMER_SKIP_ARCHIVE"):
        from build_dashboard_archive import build_archive
        build_archive()
    if failures:
        print(f"{len(failures)} scope(s) failed: " + "; ".join(failures), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
