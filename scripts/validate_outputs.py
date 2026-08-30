#!/usr/bin/env python3
"""Validate committed dashboard artefacts without refetching live data."""
from __future__ import annotations

import json
import re
from collections import Counter
from datetime import date
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "output"
COUNTRY_FILES = {
    "HU": "hungary.html",
    "PL": "poland.html",
    "CZ": "czechia.html",
    "RO": "romania.html",
    "CN": "china.html",
    "JP": "japan.html",
    "ZA": "south_africa.html",
    "UK": "uk.html",
    "US": "us.html",
}
DATA_FIRST_CODES = {"CN", "JP", "ZA", "UK", "US"}
DATA_FIRST_NAMES = ("china", "japan", "south_africa", "uk", "us")

# Display names as they appear in output/freshness_audit.json's "dashboard"
# field and in the archive index cards' <h2> headings.
DASHBOARD_DISPLAY_NAMES = {
    "HU": "Hungary",
    "PL": "Poland",
    "CZ": "Czechia",
    "RO": "Romania",
    "CN": "China",
    "JP": "Japan",
    "ZA": "South Africa",
    "UK": "United Kingdom",
    "US": "United States",
}

# Transforms that step back a fixed number of calendar periods from a base
# observation (yoy/qoq/mom/pct_change/diff) -- see build_us_dashboard.py and
# build_uk_dashboard.py. These are the transforms finding #2 broke.
LAG_TRANSFORMS = {"yoy", "yoy_pct", "qoq_pct", "mom_pct", "pct_change", "diff"}

# Expected calendar gap between consecutive observations, keyed by declared
# frequency: (unit, canonical gap, gaps accepted as "still this frequency").
# Only frequencies with a genuinely fixed cadence are covered; "daily" /
# "irregular"/etc. are deliberately not asserted on here.
#
# "quarterly" accepts a 6-month gap as well as 3: Japan's IMF Financial
# Soundness Indicators series (bank_capital_ratio, bank_npl_ratio) are
# dimensioned quarterly ("...Q") in IMF SDMX, but Japan has only ever
# submitted them twice a year, permanently, across their full history — a
# real cross-country reporting-cadence fact, not a mislabel. "monthly" gets
# no such allowance: a monthly badge promises monthly data, and that
# distinction is exactly finding #1 (UK's Monthly GDP badged verified while
# every observation actually sat on quarter-ends).
_NOMINAL_GAP = {
    "weekly": ("days", 7, (7,)),
    "monthly": ("months", 1, (1,)),
    "quarterly": ("months", 3, (3, 6)),
    "annual": ("months", 12, (12,)),
}


def _load_json(path: Path) -> dict:
    if not path.exists():
        raise AssertionError(f"Missing generated artefact: {path}")
    return json.loads(path.read_text())


def _parse_iso_date(value: object) -> date | None:
    try:
        return date.fromisoformat(str(value)[:10])
    except (TypeError, ValueError):
        return None


def _observation_dates(series: dict) -> list[date]:
    """Sorted, parsed dates from a canonical series' [date, value] pairs."""
    dates: list[date] = []
    for observation in series.get("observations") or []:
        raw_date = observation[0] if isinstance(observation, (list, tuple)) else observation.get("date")
        parsed = _parse_iso_date(raw_date)
        if parsed is not None:
            dates.append(parsed)
    return sorted(dates)


def _gap(unit: str, earlier: date, later: date) -> int:
    if unit == "days":
        return (later - earlier).days
    return (later.year * 12 + later.month) - (earlier.year * 12 + earlier.month)


# How many of the most recent observation-to-observation gaps to judge a
# series' cadence by. Some series genuinely change sampling granularity over
# a long history without being mislabeled (e.g. China's 1Y LPR was reported
# near-daily before the August 2019 LPR reform and monthly afterward) — using
# the *recent* window keeps this check about "does today's badge match
# today's data", the actual finding #1 failure mode, rather than penalizing
# an honest historical methodology change.
_RECENT_GAP_WINDOW = 12


def _assert_frequency_matches_observed_spacing(name: str, canonical_series: list[dict]) -> None:
    """Catch finding #1's defect class: a declared frequency that does not
    match the data's actual cadence (UK YBEZ/PN2 declared "monthly" while
    every observation sat at quarter-ends, three months apart).

    Uses the *modal* gap over the most recent observations rather than
    requiring every gap to match, so a handful of honest missing periods
    (e.g. BLS never published October 2025 CPI) does not trip this — only a
    systematically wrong label does.
    """
    for series in canonical_series:
        nominal = _NOMINAL_GAP.get(str(series.get("frequency") or "").lower())
        if nominal is None:
            continue
        unit, expected, accepted = nominal
        dates = _observation_dates(series)
        if len(dates) < 4:
            continue
        gaps = [_gap(unit, dates[i - 1], dates[i]) for i in range(1, len(dates))]
        recent_gaps = gaps[-_RECENT_GAP_WINDOW:]
        modal_gap, modal_count = Counter(recent_gaps).most_common(1)[0]
        if modal_gap not in accepted:
            raise AssertionError(
                f"{name}:{series.get('indicator_id')} declares frequency "
                f"{series.get('frequency')!r} (expected {expected} {unit}/observation) "
                f"but its most common recent observation spacing is {modal_gap} {unit} "
                f"({modal_count}/{len(recent_gaps)} of the last {len(recent_gaps)} gaps) — "
                f"the label does not match the data."
            )


def _assert_lag_transform_series_are_contiguous(name: str, canonical_series: list[dict]) -> None:
    """Catch finding #2's defect class: a lag-based transform (yoy/qoq/mom/
    pct_change/diff) silently drifting off its declared cadence.

    Tolerates a single honestly-skipped period (a gap of up to 2x the
    nominal cadence) since real data can have an isolated missing
    observation. A gap any wider than that indicates either multiple
    consecutive missing periods (worth a human look) or a reintroduced
    index-offset misalignment bug, so it fails the build rather than
    shipping a `verified` badge on data nobody re-checked.
    """
    for series in canonical_series:
        transform = str(series.get("transform") or "level")
        if transform not in LAG_TRANSFORMS:
            continue
        nominal = _NOMINAL_GAP.get(str(series.get("frequency") or "").lower())
        if nominal is None:
            continue
        unit, expected, _accepted = nominal
        dates = _observation_dates(series)
        for earlier, later in zip(dates, dates[1:]):
            gap = _gap(unit, earlier, later)
            if gap > expected * 2:
                raise AssertionError(
                    f"{name}:{series.get('indicator_id')} ({transform}) has a "
                    f"{gap}-{unit} gap between {earlier.isoformat()} and {later.isoformat()}, "
                    f"more than one missed period at its declared "
                    f"{series.get('frequency')!r} cadence — check for a reintroduced "
                    f"index-offset misalignment (finding #2) rather than an honest gap."
                )


def _first_ratio_stat_after(text: str, heading: str) -> tuple[int, int] | None:
    """Find the first `<strong>N/N</strong>` stat after an `<h2>{heading}</h2>`
    card heading -- the "Rendered charts"/"Rendered indicators" stat is
    always the first stat rendered in a card (see build_dashboard_archive.py).
    """
    match = re.search(re.escape(f"<h2>{heading}</h2>") + r".*?<strong>(\d+)/(\d+)</strong>", text, flags=re.S)
    if not match:
        return None
    return int(match.group(1)), int(match.group(2))


def _assert_cross_checks(name: str, summary: dict) -> None:
    """Fail the build if any declared cross-check pair has diverged.

    Gates on the windowed `status` field alone (see evaluate_cross_checks) —
    never on raw `n_breaches` / `max_abs_diff` directly, since full-history
    breach counts include documented historical events (e.g. CPI rebasing)
    that are real economics, not adapter defects. A country with no declared
    cross-checks (an absent or empty list) is a no-op.
    """
    for check in summary.get("cross_checks") or []:
        if check.get("status") == "diverged":
            raise AssertionError(
                f"{name} cross-check '{check.get('label_en')}' diverged: "
                f"{check.get('n_breaches')} breaches beyond {check.get('tolerance')}, "
                f"latest {check.get('last_breach_date')}"
            )


def validate_output_contract(root: Path = ROOT) -> list[str]:
    output = root / "output"
    messages: list[str] = []
    chart_counts: dict[str, int] = {}

    for code, filename in COUNTRY_FILES.items():
        path = output / filename
        if not path.exists():
            raise AssertionError(f"Missing stable country route: {path}")
        text = path.read_text()
        if 'data-dashboard-view="core"' not in text or "Core 48" not in text:
            raise AssertionError(f"{filename} is missing the core/deep chart view")
        if "cp-dashboard-view" not in text:
            raise AssertionError(f"{filename} does not persist the chart-view preference")
        if text.count(" Dashboard Dashboard"):
            raise AssertionError(f"{filename} contains a duplicated dashboard title")
        chart_count = (
            len(re.findall(r'class="chart-card(?:\s|\")', text))
            if code in DATA_FIRST_CODES
            else text.count('class="chart-cell chart-shell"')
        )
        if chart_count and text.count("data-latest-reading") != chart_count:
            raise AssertionError(f"{filename} does not show a latest reading for every chart")
        chart_counts[code] = chart_count
        messages.append(f"{code}: stable route and view contract ok")

    for name in DATA_FIRST_NAMES:
        text = (output / f"{name}.html").read_text()
        cards = len(re.findall(r'class="chart-card', text))
        divs = re.findall(r'id="(chart-[^"]+)" class="plotly-chart"', text)
        plots = re.findall(r'Plotly\.newPlot\("(chart-[^"]+)"', text)
        if not cards or cards != len(divs) or set(divs) != set(plots):
            raise AssertionError(f"{name}.html has mismatched chart cards, divs, or Plotly calls")
        if text.count('meta": "cp-latest-marker"') != cards:
            raise AssertionError(f"{name}.html is missing one endpoint marker per chart")
        canonical = _load_json(output / f"{name}_canonical_frame.json")
        if canonical.get("schema_version") != "data-first-canonical-v2":
            raise AssertionError(f"{name} canonical output is not v2")
        if len(canonical.get("series") or []) != cards:
            raise AssertionError(f"{name} canonical series count does not match rendered charts")
        if not all("quality" in item and "concept_id" in item for item in canonical["series"]):
            raise AssertionError(f"{name} canonical metadata is incomplete")
        for item in canonical.get("series") or []:
            quality = item.get("quality") or {}
            missing = [f for f in ("source_authority", "freshness", "derivation") if not quality.get(f)]
            if missing:
                raise AssertionError(f"{name}:{item.get('indicator_id')} missing quality fields {missing}")
            if quality.get("source_authority") == "public_secondary":
                raise AssertionError(
                    f"{name}:{item.get('indicator_id')} classified public_secondary; declare source_authority in config"
                )
        _assert_frequency_matches_observed_spacing(name, canonical["series"])
        _assert_lag_transform_series_are_contiguous(name, canonical["series"])
        summary = _load_json(output / f"{name}_dashboard_summary.json")
        if summary.get("data_mode") not in {"refresh", "snapshot"}:
            raise AssertionError(f"{name} summary is missing its data mode")
        if summary.get("canonical_frame", {}).get("series_count") != cards:
            raise AssertionError(f"{name} summary canonical count does not match rendered charts")
        _assert_cross_checks(name, summary)

    cee_canonical = _load_json(output / "cee_canonical_frame.json")
    if cee_canonical.get("schema_version") != "cee-canonical-v2":
        raise AssertionError("CEE canonical history schema mismatch")
    if {item.get("country") for item in cee_canonical.get("series") or []} != {"HU", "PL", "CZ", "RO"}:
        raise AssertionError("CEE canonical history must contain all four countries")

    snapshot = _load_json(output / "cee_build_snapshot.json")
    if snapshot.get("schema_version") != "cee-build-snapshot-v1":
        raise AssertionError("CEE snapshot schema mismatch")
    if set((snapshot.get("countries") or {})) != {"HU", "PL", "CZ", "RO"}:
        raise AssertionError("CEE snapshot must contain all four countries")
    for code, payload in snapshot["countries"].items():
        indicators = payload.get("indicators") or {}
        if not indicators:
            raise AssertionError(f"CEE snapshot has no indicators for {code}")
        if any(bool(item.get("is_proxy")) for item in indicators.values()):
            raise AssertionError(f"CEE snapshot contains a proxy row for {code}")

    source_health = _load_json(output / "source_health.json")
    if source_health.get("schema_version") != "source-health-v1":
        raise AssertionError("Source-health schema mismatch")
    if set((source_health.get("countries") or {})) != set(COUNTRY_FILES):
        raise AssertionError("Source-health report must contain every dashboard country")
    if any(payload.get("circuit_open") for payload in source_health["countries"].values()):
        raise AssertionError("Source-health report contains an open source circuit")

    coverage = _load_json(output / "core_coverage_matrix.json")
    if coverage.get("schema_version") != "core-coverage-v1":
        raise AssertionError("Core coverage matrix schema mismatch")
    if coverage.get("concept_count") != 48 or len(coverage.get("concepts") or []) != 48:
        raise AssertionError("Core coverage matrix must contain 48 concepts")
    if coverage.get("countries") != list(COUNTRY_FILES):
        raise AssertionError("Core coverage matrix country order mismatch")

    archive = _load_json(output / "dashboard_archive_summary.json")
    cards = archive.get("cards") or []
    if len(cards) != len(COUNTRY_FILES):
        raise AssertionError(f"Archive expected {len(COUNTRY_FILES)} countries, found {len(cards)}")
    if {card.get("file") for card in cards} != set(COUNTRY_FILES.values()):
        raise AssertionError("Archive country routes do not match stable output routes")
    cards_by_code = {card.get("code"): card for card in cards}
    for code in DATA_FIRST_CODES:
        card = cards_by_code.get(code)
        if card is None:
            raise AssertionError(f"Archive is missing a card for {code}")
        if int(card.get("charts") or -1) != chart_counts.get(code):
            raise AssertionError(
                f"Archive card for {code} advertises {card.get('charts')} charts but "
                f"{COUNTRY_FILES[code]} actually renders {chart_counts.get(code)} — "
                f"the archive was not rebuilt after the page changed (run scripts/build_dashboard_archive.py)"
            )

    for index_path in (root / "index.html", output / "index.html"):
        text = index_path.read_text()
        # For the root index, cards link to "output/<file>"; for output/index.html
        # they link to "<file>" directly (see build_dashboard_archive.py's
        # `prefix` argument). A count other than exactly one per country means
        # either a missing card or a stale duplicate left behind by a partial
        # rebuild (see finding #3: South Africa shipped with two cards after
        # a single-page rebuild skipped the site-wide archive step).
        href_prefix = "output/" if index_path == root / "index.html" else ""
        for filename in COUNTRY_FILES.values():
            occurrences = text.count(f'href="{href_prefix}{filename}"')
            if occurrences == 0:
                raise AssertionError(f"{index_path} is missing {filename}")
            if occurrences > 1:
                raise AssertionError(
                    f"{index_path} links to {filename} {occurrences} times — a stale "
                    "duplicate card was left behind by a partial rebuild"
                )
        for code in DATA_FIRST_CODES:
            display_name = DASHBOARD_DISPLAY_NAMES[code]
            stat = _first_ratio_stat_after(text, display_name)
            if stat is None:
                raise AssertionError(f"{index_path} has no 'Rendered charts' stat for {display_name}")
            rendered, expected = stat
            actual = chart_counts.get(code)
            if rendered != actual or expected != actual:
                raise AssertionError(
                    f"{index_path} advertises {rendered}/{expected} charts for {display_name} "
                    f"but {COUNTRY_FILES[code]} actually renders {actual} — index card is stale"
                )

    audit = _load_json(output / "freshness_audit.json")
    audit_counts: dict[str, int] = Counter(row.get("dashboard") for row in audit.get("records") or [])
    if set(audit_counts) != set(DASHBOARD_DISPLAY_NAMES.values()):
        raise AssertionError(
            f"Freshness audit covers {sorted(audit_counts)}, expected all "
            f"{sorted(DASHBOARD_DISPLAY_NAMES.values())} dashboards"
        )
    for code, display_name in DASHBOARD_DISPLAY_NAMES.items():
        expected = chart_counts.get(code)
        actual = audit_counts.get(display_name)
        if actual != expected:
            raise AssertionError(
                f"Freshness audit has {actual} records for {display_name} ({code}) but "
                f"{COUNTRY_FILES[code]} actually renders {expected} charts — audit is stale "
                "(run scripts/freshness_audit.py after rebuilding the page)"
            )
    messages.append("pipeline outcome contract ok")

    return messages


def main() -> int:
    for message in validate_output_contract():
        print(message)
    print("Generated output contract passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
