"""Print failing and circuit-open sources from output/source_health.json.

Runs in the scheduled refresh with ``if: always()`` so a failed run shows
which source tripped the circuit breaker. Messages are already redacted by
``source_health._safe_message``; only source ids, reasons and counts are new.
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def failing_sources(report: dict) -> list[str]:
    lines = []
    for code, payload in sorted((report.get("countries") or {}).items()):
        reasons = Counter((e.get("source_id"), e.get("reason")) for e in payload.get("events") or [] if e.get("outcome") == "failed")
        if not reasons:
            continue
        samples = {}
        for event in payload.get("events") or []:
            key = (event.get("source_id"), event.get("reason"))
            if event.get("outcome") == "failed" and key not in samples:
                samples[key] = f"{event.get('indicator_id')}: {str(event.get('message') or '')[:160]}"
        flag = " CIRCUIT OPEN" if payload.get("circuit_open") else ""
        lines.append(f"{code}: {payload.get('failed', 0)} failed{flag}")
        for (source, reason), count in reasons.most_common():
            lines.append(f"  {source} [{reason}] x{count} e.g. {samples[(source, reason)]}")
    return lines


def main() -> int:
    path = ROOT / "output" / "source_health.json"
    if not path.exists():
        print("No output/source_health.json")
        return 0
    lines = failing_sources(json.loads(path.read_text()))
    print("\n".join(lines) if lines else "No failed source calls.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
