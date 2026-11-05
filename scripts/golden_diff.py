#!/usr/bin/env python3
"""Compare generated outputs with a git revision, ignoring build timestamps.

Used to prove that a refactor of the build pipeline leaves every generated page
and data artifact unchanged. Run `make rebuild-ui` first, then:

    scripts/uv_project.sh run python scripts/golden_diff.py [REV]

Exit status is 1 when any generated file differs beyond timestamps.
"""
from __future__ import annotations

import difflib
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GENERATED = ["output", "index.html", "my_dashboard.html", "policy_tracker.html", "chart_studio.html",
             "chart_studio_catalog.json", "CORE_COVERAGE_MATRIX.md", "DATA_FRESHNESS_AUDIT.md",
             "DATA_SOURCE_CATALOG.md", "MACRO_WORKBENCH_BRIEFING.md"]
TIMESTAMP = re.compile(
    r"\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}(:\d{2}(\.\d+)?)?\s?(\+00:00|Z|UTC)?"
)


def _normalise(text: str) -> str:
    return TIMESTAMP.sub("<TS>", text)


def _git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=ROOT, check=True, capture_output=True, text=True).stdout


def main() -> int:
    rev = sys.argv[1] if len(sys.argv) > 1 else "HEAD"
    changed = set(_git("diff", "--name-only", rev, "--", *GENERATED).split())
    changed |= set(_git("ls-files", "--others", "--exclude-standard", "--", *GENERATED).split())
    real = []
    for name in sorted(changed):
        path = ROOT / name
        try:
            before = _git("show", f"{rev}:{name}")
        except subprocess.CalledProcessError:
            before = None
        after = path.read_text() if path.exists() else None
        if before is None or after is None:
            real.append((name, ["added" if before is None else "deleted"]))
            continue
        if _normalise(before) == _normalise(after):
            continue
        diff = list(difflib.unified_diff(
            _normalise(before).splitlines(), _normalise(after).splitlines(), lineterm="", n=0,
        ))
        real.append((name, [line[:220] for line in diff[2:14]]))
    for name, lines in real:
        print(f"== {name}")
        for line in lines:
            print(f"   {line}")
    print(f"{len(changed)} files touched, {len(real)} differ beyond timestamps")
    return 1 if real else 0


if __name__ == "__main__":
    raise SystemExit(main())
