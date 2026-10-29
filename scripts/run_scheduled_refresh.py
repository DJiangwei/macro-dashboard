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

COUNTRY_SCRIPTS = {
    "CN": SCRIPTS_DIR / "build_china_dashboard.py",
    "EA": SCRIPTS_DIR / "build_euro_area_dashboard.py",
    "UK": SCRIPTS_DIR / "build_uk_dashboard.py",
    "US": SCRIPTS_DIR / "build_us_dashboard.py",
    "JP": SCRIPTS_DIR / "build_japan_dashboard.py",
    "ZA": SCRIPTS_DIR / "build_south_africa_dashboard.py",
    "TR": SCRIPTS_DIR / "build_turkey_dashboard.py",
    "HK": SCRIPTS_DIR / "build_hong_kong_dashboard.py",
    "KR": SCRIPTS_DIR / "build_south_korea_dashboard.py",
    "TW": SCRIPTS_DIR / "build_taiwan_dashboard.py",
    "KZ": SCRIPTS_DIR / "build_kazakhstan_dashboard.py",
    "UZ": SCRIPTS_DIR / "build_uzbekistan_dashboard.py",
    "EG": SCRIPTS_DIR / "build_egypt_dashboard.py",
    "NG": SCRIPTS_DIR / "build_nigeria_dashboard.py",
}

# High-frequency focus countries for weekday quick refresh (FX/rates/commodities/daily equity)
QUICK_COUNTRIES = ["US", "EA", "CN", "JP", "UK", "TR", "TW", "KR", "ZA"]


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
        help="Refresh mode: full (all 18 countries), quick (high-frequency priority countries), auto (weekday=quick, weekend=full).",
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

    # 1. Execute country dashboards
    target = args.country.upper()
    if target == "ALL":
        if mode == "full":
            # CEE-4
            run_cmd([py, str(ROOT / "build_v4.py"), "ALL"], env=build_env)
            # Other 14 countries
            for code, script_path in COUNTRY_SCRIPTS.items():
                run_cmd([py, str(script_path)], env=build_env)
        else:
            # Quick mode: refresh high-frequency countries with live data, others use snapshot
            print("Quick mode: Refreshing priority market countries...")
            for code in QUICK_COUNTRIES:
                script_path = COUNTRY_SCRIPTS.get(code)
                if script_path:
                    run_cmd([py, str(script_path)], env=build_env)
    elif target in ("HU", "PL", "CZ", "RO"):
        run_cmd([py, str(ROOT / "build_v4.py"), target], env=build_env)
    elif target in COUNTRY_SCRIPTS:
        run_cmd([py, str(COUNTRY_SCRIPTS[target])], env=build_env)
    else:
        print(f"Error: Unknown country code '{target}'.")
        return 1

    # 2. Rebuild cross-country synchronizations & metadata
    print("\n--> Rebuilding cross-country coverage, catalog, freshness & archive...")
    run_cmd([py, str(SCRIPTS_DIR / "core_coverage_matrix.py")])
    run_cmd([py, str(SCRIPTS_DIR / "data_source_catalog.py")])
    run_cmd([py, str(SCRIPTS_DIR / "freshness_audit.py")])
    run_cmd([py, str(SCRIPTS_DIR / "build_dashboard_archive.py")])
    run_cmd([py, str(SCRIPTS_DIR / "macro_workbench.py")])

    print("\n[SUCCESS] Refresh runner completed successfully.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
