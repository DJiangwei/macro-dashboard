"""Build the root and output dashboard archive pages from generated data.

The archive is intentionally generated after country pages so the top-level
cards stay in sync with the latest dashboard summaries and the CE4 canonical
pipeline. It also writes a small JSON summary that future agents can inspect
without scraping HTML.
"""
from __future__ import annotations

import json
from datetime import UTC, datetime
from html import escape
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
OUTPUT = ROOT / "output"
ARCHIVE_JSON = OUTPUT / "dashboard_archive_summary.json"

for path in (ROOT, SRC):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from build_v4 import _latest_value, _source_mix  # noqa: E402
from country_primer.data_fetcher import (  # noqa: E402
    DataPipeline,
    INDICATOR_MANIFEST_48,
    is_dropped_proxy_indicator,
)


CE4_COUNTRIES = [
    {
        "code": "HU",
        "name": "Hungary",
        "file": "hungary_2026Q2_v4.html",
        "currency": "HUF",
        "institution": "MNB",
    },
    {
        "code": "PL",
        "name": "Poland",
        "file": "poland_2026Q2_v4.html",
        "currency": "PLN",
        "institution": "NBP",
    },
    {
        "code": "CZ",
        "name": "Czechia",
        "file": "czechia_2026Q2_v4.html",
        "currency": "CZK",
        "institution": "CNB",
    },
    {
        "code": "RO",
        "name": "Romania",
        "file": "romania_2026Q2_v4.html",
        "currency": "RON",
        "institution": "BNR",
    },
]

DATA_FIRST_COUNTRIES = [
    {
        "code": "CN",
        "name": "China",
        "file": "china_2026Q2_v1.html",
        "currency": "CNY",
        "institution": "PBC",
        "summary": "china_dashboard_summary.json",
        "headline_label": "Latest USD/CNY fixing",
        "headline_key": "usd_cny_latest",
        "framework": "GS China statistics logic",
    },
    {
        "code": "UK",
        "name": "United Kingdom",
        "file": "uk_2026Q2_v1.html",
        "currency": "GBP",
        "institution": "BoE",
        "summary": "uk_dashboard_summary.json",
        "headline_label": "Bank Rate",
        "headline_key": "bank_rate_latest",
        "framework": "GS UK statistics logic",
    },
    {
        "code": "US",
        "name": "United States",
        "file": "us_2026Q2_v1.html",
        "currency": "USD",
        "institution": "Fed",
        "summary": "us_dashboard_summary.json",
        "headline_label": "Fed funds",
        "headline_key": "fed_funds_latest",
        "framework": "GS US statistics logic",
    },
]


def _read_json(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text())
    except json.JSONDecodeError:
        return {}


def _ce4_cards() -> list[dict]:
    pipeline = DataPipeline()
    cards: list[dict] = []
    for country in CE4_COUNTRIES:
        code = country["code"]
        frame = pipeline.fetch_country(code)
        coverage = pipeline.validate_coverage(frame)
        verified, watch, low = _source_mix(frame)
        dropped = len(
            [
                spec
                for spec in INDICATOR_MANIFEST_48
                if is_dropped_proxy_indicator(code, spec.indicator_id)
            ]
        )
        rendered = int(coverage.get("indicator_count", 0))
        expected = int(coverage.get("expected", rendered))
        proxy = int(coverage.get("proxy_count", 0))
        cards.append(
            {
                **country,
                "category": "CEE-4 v4 public dashboard",
                "charts": rendered,
                "expected": expected,
                "proxy_fills": proxy,
                "gaps_or_dropped": dropped,
                "gaps_label": "Dropped proxy slots",
                "headline_label": "Policy rate",
                "headline": f"{_latest_value(frame, code, 'policy_rate')}%",
                "secondary_label": "10Y yield",
                "secondary": f"{_latest_value(frame, code, 'sov_yield_10y')}%",
                "quality": f"{verified} verified · {watch} watch · {low} low",
                "status": "watch" if proxy else "clean",
            }
        )
    return cards


def _data_first_cards() -> list[dict]:
    cards: list[dict] = []
    for country in DATA_FIRST_COUNTRIES:
        summary = _read_json(OUTPUT / country["summary"])
        charts = int(summary.get("charts") or 0)
        data_gaps = int(summary.get("data_gaps") or 0)
        low_confidence = int(summary.get("low_confidence") or 0)
        source_groups = int(summary.get("source_groups") or 0)
        cards.append(
            {
                **{key: country[key] for key in ("code", "name", "file", "currency", "institution")},
                "category": "data-first country page",
                "charts": charts,
                "expected": charts,
                "proxy_fills": 0,
                "gaps_or_dropped": data_gaps,
                "gaps_label": "Official data gaps",
                "headline_label": country["headline_label"],
                "headline": str(summary.get(country["headline_key"]) or "n/a"),
                "secondary_label": "Source groups",
                "secondary": str(source_groups),
                "quality": f"{source_groups} source groups · {low_confidence} low-confidence charts",
                "framework": country["framework"],
                "status": "clean",
            }
        )
    return cards


def _card_html(card: dict, *, prefix: str) -> str:
    href = f"{prefix}{card['file']}"
    status_class = "warn" if card.get("status") == "watch" else "clean"
    rendered_label = "Rendered indicators" if card["code"] in {"HU", "PL", "CZ", "RO"} else "Rendered charts"
    return f"""
  <a href="{escape(href)}" class="card {status_class}" data-country="{escape(card['code'])}">
    <div class="card-kicker">{escape(card['currency'])} · {escape(card['institution'])} · {escape(card['category'])}</div>
    <h2>{escape(card['name'])}</h2>
    <div class="stats">
      <div class="stat"><span>{rendered_label}</span><strong>{card['charts']}/{card['expected']}</strong></div>
      <div class="stat"><span>Proxy fills</span><strong>{card['proxy_fills']}</strong></div>
      <div class="stat"><span>{escape(card['gaps_label'])}</span><strong>{card['gaps_or_dropped']}</strong></div>
      <div class="stat"><span>{escape(card['headline_label'])}</span><strong>{escape(card['headline'])}</strong></div>
      <div class="stat"><span>{escape(card['secondary_label'])}</span><strong>{escape(card['secondary'])}</strong></div>
      <div class="stat"><span>Source quality</span><strong>{escape(card['quality'])}</strong></div>
    </div>
  </a>"""


def _html(cards: list[dict], *, prefix: str, docs_prefix: str) -> str:
    total_charts = sum(int(card["charts"]) for card in cards)
    total_proxy = sum(int(card["proxy_fills"]) for card in cards)
    total_gaps = sum(int(card["gaps_or_dropped"]) for card in cards)
    generated = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")
    card_markup = "".join(_card_html(card, prefix=prefix) for card in cards)
    archive_json_href = f"{prefix}dashboard_archive_summary.json" if prefix else "dashboard_archive_summary.json"
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Country Primer — Macro Dashboard Archive</title>
<style>
:root {{
  --bg: #f4efe7;
  --fg: #171310;
  --muted: #63574e;
  --accent: #8a593d;
  --border: rgba(23, 19, 16, 0.14);
  --card: rgba(255, 252, 246, 0.76);
  --success: #3f6f50;
  --warn: #9d3d2e;
  --font-display: "Iowan Old Style", "Songti SC", "Noto Serif SC", Georgia, serif;
  --font-body: "Avenir Next", "PingFang SC", "Noto Sans SC", "Segoe UI", sans-serif;
}}
* {{ box-sizing: border-box; }}
html {{ scroll-behavior: smooth; }}
body {{
  margin: 0;
  background:
    radial-gradient(circle at top left, rgba(138, 89, 61, 0.15), transparent 24%),
    radial-gradient(circle at top right, rgba(54, 75, 97, 0.12), transparent 22%),
    linear-gradient(180deg, #f8f4ed 0%, #f4efe7 48%, #efe7db 100%);
  color: var(--fg);
  font-family: var(--font-body);
  font-size: 14px;
  line-height: 1.6;
}}
body::before {{
  content: "";
  position: fixed;
  inset: 0;
  pointer-events: none;
  background:
    linear-gradient(to right, rgba(23, 19, 16, 0.025) 1px, transparent 1px),
    linear-gradient(to bottom, rgba(23, 19, 16, 0.02) 1px, transparent 1px);
  background-size: 48px 48px;
  mask-image: linear-gradient(180deg, rgba(0, 0, 0, 0.45), transparent 85%);
}}
.topbar {{
  position: sticky;
  top: 0;
  z-index: 20;
  display: flex;
  justify-content: space-between;
  gap: 16px;
  padding: 12px 32px;
  border-bottom: 1px solid var(--border);
  background: rgba(244, 239, 231, 0.86);
  backdrop-filter: blur(14px);
  font-size: 11px;
  letter-spacing: 0.12em;
  text-transform: uppercase;
}}
.brand {{ font-family: var(--font-display); font-size: 15px; letter-spacing: 0.16em; }}
.brand span {{ color: var(--accent); }}
.container {{ position: relative; max-width: 1180px; margin: 0 auto; padding: 48px 24px; }}
header {{ border-bottom: 1px solid var(--border); padding-bottom: 32px; margin-bottom: 24px; }}
h1 {{
  margin: 0;
  max-width: 980px;
  font-family: var(--font-display);
  font-size: clamp(34px, 6vw, 72px);
  line-height: 0.92;
  letter-spacing: -0.06em;
  font-weight: 500;
}}
.subtitle {{ max-width: 880px; color: var(--muted); font-size: 17px; line-height: 1.7; }}
code {{ overflow-wrap: anywhere; word-break: break-word; }}
.meta-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 10px; margin: 24px 0; }}
.meta-chip {{
  background: var(--card);
  border: 1px solid var(--border);
  padding: 14px 16px;
}}
.meta-chip strong {{ display: block; font-family: var(--font-display); font-size: 28px; font-weight: 500; }}
.meta-chip span {{ color: var(--muted); font-size: 11px; letter-spacing: 0.08em; text-transform: uppercase; }}
.grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 14px; }}
.card {{
  display: block;
  color: inherit;
  text-decoration: none;
  background: var(--card);
  border: 1px solid var(--border);
  border-top: 3px solid var(--success);
  padding: 24px;
  transition: transform 0.18s ease, border-color 0.18s ease, background 0.18s ease;
}}
.card.warn {{ border-top-color: var(--warn); }}
.card:hover {{ transform: translateY(-2px); background: rgba(255, 252, 246, 0.95); border-color: rgba(23, 19, 16, 0.28); }}
.card-kicker {{ color: var(--accent); font-size: 11px; letter-spacing: 0.1em; text-transform: uppercase; }}
.card h2 {{ margin: 8px 0 16px; font-family: var(--font-display); font-weight: 500; font-size: 34px; }}
.stats {{ display: grid; gap: 7px; }}
.stat {{ display: flex; justify-content: space-between; gap: 16px; border-bottom: 1px solid var(--border); padding: 7px 0; }}
.stat span {{ color: var(--muted); }}
.stat strong {{ text-align: right; font-family: var(--font-display); font-weight: 500; }}
.links {{ margin-top: 24px; display: flex; gap: 10px; flex-wrap: wrap; }}
.links a {{
  color: var(--accent);
  border: 1px solid var(--border);
  background: var(--card);
  padding: 8px 13px;
  text-decoration: none;
  border-radius: 999px;
}}
footer {{ margin-top: 36px; padding-top: 24px; border-top: 1px solid var(--border); color: var(--muted); font-size: 12px; }}
@media (max-width: 720px) {{
  .topbar {{ align-items: flex-start; flex-direction: column; padding: 12px 20px; }}
  .container {{ padding: 34px 18px; }}
}}
</style>
</head>
<body>
<div class="topbar">
  <div class="brand">East Meridian <span>/ Country Primer</span></div>
  <div>Macro Dashboard Archive · CEE-4 v4 + China + UK + US</div>
</div>
<main class="container">
  <header>
    <h1>Macro Dashboard Archive</h1>
    <p class="subtitle">Generated archive for the CEE-4 public dashboards and the China, UK, and US data-first pages. Cards are rebuilt from the latest country summaries and the CE4 canonical pipeline, then exported to <code>{escape(archive_json_href)}</code> so homepage data stays linked to dashboard builds.</p>
  </header>
  <section class="meta-grid" aria-label="coverage summary">
    <div class="meta-chip"><strong>{total_charts}</strong><span>rendered chart slots</span></div>
    <div class="meta-chip"><strong>{total_proxy}</strong><span>remaining proxy fills</span></div>
    <div class="meta-chip"><strong>{total_gaps}</strong><span>gaps or dropped slots</span></div>
    <div class="meta-chip"><strong>{len(cards)}</strong><span>country dashboards</span></div>
  </section>
  <section class="grid" aria-label="country dashboards">
{card_markup}
  </section>
  <nav class="links" aria-label="documentation links">
    <a href="{docs_prefix}DATA_SOURCE_CATALOG.md">Data Source Catalog</a>
    <a href="{docs_prefix}DATA_FRESHNESS_AUDIT.md">Freshness Audit</a>
    <a href="{docs_prefix}PROXY_REVIEW.md">Proxy Review</a>
    <a href="{prefix}macro_framework_proposal.html">Framework Proposal</a>
    <a href="{escape(archive_json_href)}">Archive JSON</a>
  </nav>
  <footer>
    Generated {generated} from country dashboard summaries and canonical CE4 data. Research artefact only, not investment advice.
  </footer>
</main>
</body>
</html>
"""


def _write(path: Path, content: str) -> None:
    path.write_text("\n".join(line.rstrip() for line in content.splitlines()) + "\n")


def build_archive() -> tuple[Path, Path, Path]:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    cards = _ce4_cards() + _data_first_cards()
    payload = {
        "generated": datetime.now(UTC).isoformat(),
        "source": "Generated from CE4 DataPipeline plus output/*_dashboard_summary.json files.",
        "cards": cards,
    }
    ARCHIVE_JSON.write_text(json.dumps(payload, indent=2, ensure_ascii=False))
    output_index = OUTPUT / "index.html"
    root_index = ROOT / "index.html"
    _write(output_index, _html(cards, prefix="", docs_prefix="../"))
    _write(root_index, _html(cards, prefix="output/", docs_prefix=""))
    return root_index, output_index, ARCHIVE_JSON


if __name__ == "__main__":
    for path in build_archive():
        print(f"Wrote {path} ({path.stat().st_size:,} bytes)")
