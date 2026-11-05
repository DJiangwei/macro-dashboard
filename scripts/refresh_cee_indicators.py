"""Partial live refresh for the CEE canonical snapshot.

Refetches only the named indicators for HU/PL/CZ/RO through the normal CEE
adapter chain and merges them into ``output/cee_canonical_frame.json``. Every
other series stays byte-for-byte as it was, so a targeted source change (for
example moving policy rates to BIS) can be shipped without a full refresh.

Usage:
    scripts/uv_project.sh run python scripts/refresh_cee_indicators.py policy_rate real_policy_rate
    make rebuild-ui   # re-render pages from the updated snapshot
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from country_primer.data_fetcher import (  # noqa: E402
    CANONICAL_COLUMNS,
    INDICATOR_MANIFEST_48,
    DataPipeline,
    is_dropped_proxy_indicator,
)
from country_primer.snapshots import (  # noqa: E402
    load_cee_canonical_snapshot,
    write_cee_canonical_snapshot,
)

CEE_CANONICAL = ROOT / "output" / "cee_canonical_frame.json"
CEE_CODES = ("HU", "PL", "CZ", "RO")


def refresh(indicator_ids: list[str], countries: tuple[str, ...] = CEE_CODES) -> dict[str, dict[str, int]]:
    specs = [spec for spec in INDICATOR_MANIFEST_48 if spec.indicator_id in set(indicator_ids)]
    unknown = sorted(set(indicator_ids) - {spec.indicator_id for spec in specs})
    if unknown:
        raise SystemExit(f"Unknown CEE manifest indicator(s): {', '.join(unknown)}")
    frames = load_cee_canonical_snapshot(CEE_CANONICAL)
    pipeline = DataPipeline()
    report: dict[str, dict[str, int]] = {}
    for country in countries:
        live = []
        for spec in specs:
            if is_dropped_proxy_indicator(country, spec.indicator_id):
                continue
            rows = pipeline.fetch_country(country, specs=[spec])
            if not rows:
                print(f"{country}:{spec.indicator_id}: live fetch empty; keeping prior snapshot rows")
                continue
            live.extend(rows)
            report.setdefault(country, {})[spec.indicator_id] = len(rows)
        refreshed_ids = {row["indicator_id"] for row in live}
        kept = [row for row in frames.get(country, []) if row.get("indicator_id") not in refreshed_ids]
        merged = kept + [{column: row.get(column) for column in CANONICAL_COLUMNS} | {"country": country} for row in live]
        frames[country] = sorted(
            merged,
            key=lambda r: (str(r.get("section_id")), str(r.get("indicator_id")), str(r.get("date"))),
        )
    write_cee_canonical_snapshot(CEE_CANONICAL, frames)
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("indicator_ids", nargs="+")
    parser.add_argument("--countries", default=",".join(CEE_CODES))
    args = parser.parse_args()
    countries = tuple(code.strip().upper() for code in args.countries.split(",") if code.strip())
    report = refresh(args.indicator_ids, countries)
    for country, counts in report.items():
        print(country, counts)
    print(f"Wrote {CEE_CANONICAL}")


if __name__ == "__main__":
    main()
