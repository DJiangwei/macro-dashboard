import re
from pathlib import Path

code = Path("scripts/build_china_dashboard.py").read_text()

new_code = []
for line in code.splitlines():
    if line.startswith("def _chart_html"):
        break
    new_code.append(line)

new_code_text = "\n".join(new_code)
# Actually, the original build_china_dashboard.py had the fetchers up until `def fetch_all`
match = re.search(r"def fetch_all\(", new_code_text)
if match:
    new_code_text = new_code_text[:match.start()]

new_code_text += """
def inject_index(summary: dict[str, Any]) -> None:
    index_path = OUTPUT / "index.html"
    if not index_path.exists():
        return
    html = index_path.read_text()
    html = re.sub(r"\\n\\s*<!-- China dashboard card -->.*?<!-- /China dashboard card -->", "", html, flags=re.S)
    
    card = f'''
  <!-- China dashboard card -->
  <a href="china.html" class="card clean">
    <div class="card-kicker">CNY · PBC · China data-first page</div>
    <h2>China</h2>
    <div class="stats">
      <div class="stat"><span>Rendered charts</span><strong>{summary['charts']}</strong></div>
      <div class="stat"><span>Proxy fills</span><strong>0</strong></div>
      <div class="stat"><span>Official gaps tracked</span><strong>{summary['data_gaps']}</strong></div>
      <div class="stat"><span>Latest USD/CNY fixing</span><strong>{summary.get('usd_cny_latest', 'n/a')}</strong></div>
      <div class="stat"><span>Source groups</span><strong>{summary['source_groups']}</strong></div>
      <div class="stat"><span>Framework</span><strong>GS China statistics logic</strong></div>
    </div>
  </a>
  <!-- /China dashboard card -->'''
    
    marker = '  </section>\\n  <nav class="links"'
    if marker in html:
        html = html.replace(marker, card + "\\n  </section>\\n  <nav class=\\"links\\"", 1)
        
    html = html.replace("<title>Country Primer — CEE-4 Macro Dashboard</title>", "<title>Country Primer — Macro Dashboard Archive</title>")
    html = html.replace("CEE-4 Macro Dashboard · v4 · Proxy-free public pages", "Macro Dashboard Archive · CEE-4 v4 + China")
    html = html.replace("<h1>CEE-4 Macro Dashboard</h1>", "<h1>Macro Dashboard Archive</h1>")
    html = html.replace(
        "Generated archive entry for the four country dashboards. This page is rebuilt by <code>build_v4.py ALL</code>, so its links, indicator counts, proxy status, and quality summary stay synchronized with the individual country pages.",
        "Generated archive entry for the proxy-free CEE-4 dashboards plus the China data-first page. This page is rebuilt by <code>make build-v4</code>, so links, indicator counts, proxy status, and quality summary stay synchronized with generated pages.",
    )
    html = html.replace("<span>rendered country-indicator slots</span>", "<span>CEE-4 rendered indicator slots</span>")
    html = html.replace("<strong>4</strong><span>country dashboards</span>", "<strong>5</strong><span>country dashboards</span>")
    
    from country_primer.page_renderer import _write_clean
    _write_clean(index_path, html)

def build(data_mode: str | None = None) -> Path:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    data_mode = (data_mode or os.environ.get("COUNTRY_PRIMER_DATA_MODE") or "refresh").strip().lower()
    config = _load_config()
    
    def get_safe_rows(cache):
        if "safe_rows" not in cache:
            cache["safe_rows"] = _safe_rows()
        return cache["safe_rows"]

    registry = {
        "world_bank": lambda spec, cache: fetch_world_bank(spec),
        "imf_datamapper": lambda spec, cache: fetch_imf_datamapper(spec),
        "fred_graph_csv": lambda spec, cache: fetch_fred_graph(spec),
        "akshare_table": lambda spec, cache: fetch_akshare_table(spec, cache),
        "akshare_wide_year_month": lambda spec, cache: fetch_akshare_wide_year_month(spec, cache),
        "eastmoney_industry_indicator": lambda spec, cache: fetch_eastmoney_industry_indicator(spec),
        "safe_rmb_midpoint": lambda spec, cache: fetch_safe_midpoint(spec, get_safe_rows(cache)),
        "pbc_card": lambda spec, cache: fetch_pbc_card(spec),
    }

    if data_mode == "snapshot":
        series_list = load_canonical_data_first_frame(CANONICAL_JSON, config)
        previous_summary = json.loads(SUMMARY_JSON.read_text()) if SUMMARY_JSON.exists() else {}
        cards = list(previous_summary.get("latest_cards") or [
            {**card, "value": "n/a", "updated": "n/a"}
            for card in config.get("latest_cards", [])
        ])
    else:
        from country_primer.source_health import SOURCE_HEALTH
        from country_primer.data_first_pipeline import fetch_all
        SOURCE_HEALTH.reset()
        series_list, cards = fetch_all(config, registry, sequential=True)
        series_list = retain_last_known_good_series(series_list, CANONICAL_JSON, config)
        series_list = track_revisions_and_vintages(series_list, CANONICAL_JSON, config)

    charted = [item for item in series_list if item.get("observations")]
    usd_cny = next((item for item in charted if item["id"] == "usd_cny_midpoint"), None)
    from country_primer.page_renderer import _latest, build_country_page
    usd_latest = _latest(usd_cny) if usd_cny else None
    usd_latest_str = f"{float(usd_latest['value']):.4f} ({usd_latest['date']})" if usd_latest else "n/a"

    summary = build_country_page(
        country_code="CN",
        config=config,
        series_list=series_list,
        out_html=OUT_HTML,
        summary_json=SUMMARY_JSON,
        canonical_json=CANONICAL_JSON,
        data_mode=data_mode,
        summary_key_ids=SUMMARY_KEY_IDS,
        extra_cards=cards,
        latest_value_key="usd_cny_latest",
        latest_value_display=usd_latest_str
    )

    inject_index(summary)
    
    if not os.environ.get("COUNTRY_PRIMER_SKIP_ARCHIVE"):
        from build_dashboard_archive import build_archive
        build_archive()
    return OUT_HTML

if __name__ == "__main__":
    path = build()
    print(f"Wrote {path} ({path.stat().st_size:,} bytes)")
"""

# Need to make sure SUMMARY_KEY_IDS is defined in new_code_text. It should be if we didn't remove it.
# Let's check where SUMMARY_KEY_IDS is.
match = re.search(r"SUMMARY_KEY_IDS = \[.*?\]", new_code_text, re.DOTALL)
if not match:
    # it might have been below fetch_all
    new_code_text = "SUMMARY_KEY_IDS = ['real_gdp_growth', 'core_cpi_inflation', 'urban_surveyed_unemployment_rate', 'manufacturing_pmi', 'usd_cny_midpoint']\n" + new_code_text

Path("scripts/build_china_dashboard.py").write_text(new_code_text)
