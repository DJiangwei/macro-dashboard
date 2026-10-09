import re
from pathlib import Path

code = Path("scripts/build_us_dashboard.py").read_text()

# We want to keep imports, fetchers (fetch_fred_us, _fetch_bls_batch, fetch_bls_api, fetch_treasury_auctions), and _apply_transform, _load_config
# We will remove _fetch_one, fetch_all, _render_cards, _index_card, inject_output_index, inject_root_index, build
# Actually, wait, the simplest way is to manually compose the new file.

new_code = []
for line in code.splitlines():
    if line.startswith("from build_china_dashboard import"):
        new_code.append("from src.country_primer.page_renderer import build_country_page")
        new_code.append("from src.country_primer.data_first_pipeline import fetch_all")
    elif line.strip() in ("CSS,", "_chart_html,", "_format_value,", "_gaps_html,", "_json,", "_latest,", "_section_nav,", "_sections_html,", "_write_clean,"):
        pass
    else:
        new_code.append(line)

new_code_text = "\n".join(new_code)

# We will just replace everything from `def _fetch_one` down to the bottom with our new logic.
match = re.search(r"def _fetch_one\(", new_code_text)
if match:
    new_code_text = new_code_text[:match.start()]

new_code_text += """
def inject_output_index(summary: dict[str, Any]) -> None:
    index_path = OUTPUT / "index.html"
    if not index_path.exists():
        return
    html = index_path.read_text()
    html = re.sub(r"\\n\\s*<!-- US dashboard card -->.*?<!-- /US dashboard card -->", "", html, flags=re.S)
    card = f'''
  <!-- US dashboard card -->
  <a href="us.html" class="card clean">
    <div class="card-kicker">USD · FED · US data-first page</div>
    <h2>United States</h2>
    <div class="stats">
      <div class="stat"><span>Rendered charts</span><strong>{summary['charts']}</strong></div>
      <div class="stat"><span>Proxy fills</span><strong>0</strong></div>
      <div class="stat"><span>Official gaps tracked</span><strong>{summary['data_gaps']}</strong></div>
      <div class="stat"><span>Fed Funds Rate</span><strong>{summary.get('fed_funds_latest', 'n/a')}</strong></div>
      <div class="stat"><span>Source groups</span><strong>{summary['source_groups']}</strong></div>
      <div class="stat"><span>Framework</span><strong>GS US statistics logic</strong></div>
    </div>
  </a>
  <!-- /US dashboard card -->'''
    marker = '  </section>\\n  <nav class="links"'
    if marker in html:
        html = html.replace(marker, card + "\\n  </section>\\n  <nav class=\\"links\\"", 1)
    
    # ensure it says 6 country dashboards
    html = re.sub(r"Macro Dashboard Archive · CEE-4 v4 \\+ China[^<]*", "Macro Dashboard Archive · CEE-4 v4 + China + Japan + South Africa + UK + US", html)
    html = re.sub(
        r"Generated archive entry for the proxy-free CEE-4 dashboards plus the [^.]*\\.",
        "Generated archive entry for the proxy-free CEE-4 dashboards plus the China, Japan, South Africa, UK, and US data-first pages.",
        html,
    )
    html = html.replace("<strong>5</strong><span>country dashboards</span>", "<strong>6</strong><span>country dashboards</span>")
    
    from src.country_primer.page_renderer import _write_clean
    _write_clean(index_path, html)

def inject_root_index(summary: dict[str, Any]) -> None:
    index_path = ROOT / "index.html"
    if not index_path.exists():
        return
    html = index_path.read_text()
    html = re.sub(
        r'(<a href="output/us.html" class="card">.*?<span class="label">Charts</span><span class="value">)\\d+(</span>)',
        rf"\\g<1>{summary['charts']}\\2",
        html,
        count=1,
        flags=re.S,
    )
    from src.country_primer.page_renderer import _write_clean
    _write_clean(index_path, html)

def build(data_mode: str | None = None) -> Path:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    data_mode = (data_mode or os.environ.get("COUNTRY_PRIMER_DATA_MODE") or "refresh").strip().lower()
    config = _load_config()
    
    registry = {
        "fred_us": lambda spec, cache: fetch_fred_us(requests.Session(), spec),
        "bls_api": lambda spec, cache: fetch_bls_api(requests.Session(), spec),
        "treasury_auctions": lambda spec, cache: fetch_treasury_auctions(requests.Session(), spec)
    }

    if data_mode == "snapshot":
        series_list = load_canonical_data_first_frame(CANONICAL_JSON, config)
        cards = []
    else:
        from country_primer.source_health import SOURCE_HEALTH
        SOURCE_HEALTH.reset()
        series_list, cards = fetch_all(config, registry, max_workers=4)
        series_list = retain_last_known_good_series(series_list, CANONICAL_JSON, config)
        series_list = track_revisions_and_vintages(series_list, CANONICAL_JSON, config)

    charted = [item for item in series_list if item.get("observations")]
    min_chart_count = int(config.get("min_chart_count", 55))
    if len(charted) < min_chart_count:
        unavailable = [item["id"] for item in series_list if not item.get("observations")]
        raise RuntimeError(
            f"US dashboard fetched only {len(charted)} charts, below minimum {min_chart_count}. "
            "Set FRED_API_KEY for the official API path or retry later. "
            f"Unavailable indicators: {', '.join(unavailable[:12])}{'...' if len(unavailable) > 12 else ''}"
        )

    fed_funds = next((item for item in charted if item["id"] == "daily_fed_funds"), None)
    if fed_funds is None:
        fed_funds = next((item for item in charted if item["id"] == "effective_fed_funds"), None)
    
    from src.country_primer.page_renderer import _latest
    fed_latest = _latest(fed_funds) if fed_funds else None
    fed_latest_str = f"{float(fed_latest['value']):.2f}% ({fed_latest['date']})" if fed_latest else "n/a"

    summary = build_country_page(
        country_code="US",
        config=config,
        series_list=series_list,
        out_html=OUT_HTML,
        summary_json=SUMMARY_JSON,
        canonical_json=CANONICAL_JSON,
        data_mode=data_mode,
        summary_key_ids=["real_gdp_growth", "core_pce_inflation", "unemployment_rate", "nonfarm_payrolls_change", "effective_fed_funds"],
        extra_cards=cards,
        latest_value_key="fed_funds_latest",
        latest_value_display=fed_latest_str
    )

    inject_output_index(summary)
    inject_root_index(summary)
    
    if not os.environ.get("COUNTRY_PRIMER_SKIP_ARCHIVE"):
        from build_dashboard_archive import build_archive
        build_archive()
    return OUT_HTML

if __name__ == "__main__":
    path = build()
    print(f"Wrote {path} ({path.stat().st_size:,} bytes)")
"""

Path("scripts/build_us_dashboard.py").write_text(new_code_text)
