"""Refuse a data-branch push that would lose accumulated history.

    python3 scripts/accumulated_guard.py BRANCH_DIR LOCAL_DIR

BRANCH_DIR is data/accumulated as it stands on the data branch, LOCAL_DIR the
copy about to replace it. Exits 1 when a branch file is missing locally or
has dates the local copy lacks: those dates cannot be refetched, because the
sources keep only a short window. Standard library only, so CI can run it
with plain python3.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path


def _dates(path: Path) -> set[str]:
    payload = json.loads(path.read_text())
    return {str(item["date"]) for item in payload.get("observations") or []}


def shrinking_files(branch_dir: Path, local_dir: Path) -> list[str]:
    shrinking = []
    for branch_file in sorted(Path(branch_dir).glob("*.json")):
        local_file = Path(local_dir) / branch_file.name
        if not local_file.exists() or not _dates(branch_file) <= _dates(local_file):
            shrinking.append(branch_file.name)
    return shrinking


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(__doc__.strip(), file=sys.stderr)
        return 2
    shrinking = shrinking_files(Path(argv[0]), Path(argv[1]))
    if shrinking:
        print("Refusing to push: the data branch has accumulated dates this checkout lacks:", file=sys.stderr)
        for name in shrinking:
            print(f"  data/accumulated/{name}", file=sys.stderr)
        print("Run `make pull-data` first (or set ALLOW_ACCUMULATED_SHRINK=1 to drop them on purpose).", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
