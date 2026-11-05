#!/usr/bin/env python3
"""Unified scheduled refresh runner for Macro Dashboard.

Usage:
  python scripts/run_scheduled_refresh.py --mode auto
  python scripts/run_scheduled_refresh.py --mode full
  python scripts/run_scheduled_refresh.py --mode quick
  python scripts/run_scheduled_refresh.py --country KR
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = ROOT / "scripts"
OUTPUT_DIR = ROOT / "output"

if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from country_primer.scopes import all_scopes  # noqa: E402

BUILD_SCOPE = SCRIPTS_DIR / "build_scope.py"


def run_cmd(cmd: list[str], env: dict[str, str] | None = None) -> None:
    merged_env = os.environ.copy()
    if env:
        merged_env.update(env)
    print(f"--> Running: {' '.join(str(c) for c in cmd)}")
    t0 = time.time()
    res = subprocess.run(cmd, cwd=ROOT, env=merged_env)
    elapsed = time.time() - t0
    if res.returncode != 0:
        print(f"xx Command failed with code {res.returncode} ({elapsed:.1f}s)")
        raise RuntimeError(f"Command failed: {' '.join(str(c) for c in cmd)}")
    print(f"ok Completed in {elapsed:.1f}s")


def main() -> int:
    parser = argparse.ArgumentParser(description="Macro dashboard scheduled refresh runner.")
    parser.add_argument(
        "--mode",
        choices=["auto", "full", "quick"],
        default="auto",
        help="Refresh mode: full (every scope), quick (scopes flagged quick_refresh in config/scopes.yaml), auto (weekday=quick, weekend=full).",
    )
    parser.add_argument(
        "--country",
        default="ALL",
        help="Target country code (e.g., KR, TW, TR, ALL). Defaults to ALL.",
    )
    args = parser.parse_args()

    now_utc = datetime.now(timezone.utc)
    mode = args.mode
    if mode == "auto":
        # 5 is Saturday, 6 is Sunday
        mode = "full" if now_utc.weekday() in (5, 6) else "quick"

    print(f"=== Macro Dashboard Refresh Runner ===")
    print(f"Timestamp (UTC): {now_utc.isoformat()}")
    print(f"Selected mode:   {mode}")
    print(f"Target country:  {args.country}")

    build_env = {"COUNTRY_PRIMER_SKIP_ARCHIVE": "1"}
    py = sys.executable

    # 0. BIS policy-rate snapshot (cross-check reference for every covered scope)
    run_cmd([py, str(SCRIPTS_DIR / "refresh_bis_policy_snapshot.py")])

    # 1. Execute scope builds (registry: config/scopes.yaml)
    scopes = all_scopes()
    data_first = [s.id for s in scopes if s.is_data_first]
    cee = [s.id for s in scopes if s.pipeline == "cee_v4"]
    target = args.country.upper()
    if target == "ALL":
        if mode == "full":
            run_cmd([py, str(ROOT / "build_v4.py"), "ALL"], env=build_env)
            run_cmd([py, str(BUILD_SCOPE), "--all"], env=build_env)
        else:
            # Quick mode: refresh the scopes flagged `quick_refresh` (daily markets
            # data); every other page is re-rendered from its snapshot below.
            quick = [s.id for s in scopes if s.is_data_first and s.extra.get("quick_refresh")]
            print(f"Quick mode: refreshing {', '.join(quick)}")
            run_cmd([py, str(BUILD_SCOPE), *quick], env=build_env)
    elif target in cee:
        run_cmd([py, str(ROOT / "build_v4.py"), target], env=build_env)
    elif target in data_first:
        run_cmd([py, str(BUILD_SCOPE), target], env=build_env)
    else:
        print(f"Error: Unknown scope code '{target}'. Registered: {', '.join(cee + data_first)}")
        return 1

    # 2. Rebuild cross-country synchronizations & metadata
    # Same offline sequence as local `make rebuild-ui`: derivations, deepdive
    # views, every page, coverage, catalog, freshness, archive, workbench,
    # Chart Studio, My Dashboard and Policy Tracker — so CI and local builds
    # produce identical outputs from the refreshed canonical frames.
    print("\n--> Rebuilding derived series, deepdive views and all pages from snapshots...")
    run_cmd(["make", "rebuild-ui"])

    print("\n[SUCCESS] Refresh runner completed successfully.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
