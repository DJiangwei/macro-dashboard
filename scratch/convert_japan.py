import re
import os
from pathlib import Path

code = Path("scripts/build_japan_dashboard.py").read_text()

new_code = []
for line in code.splitlines():
    if line.startswith("from build_china_dashboard import"):
        new_code.append("from country_primer.page_renderer import build_country_page")
        new_code.append("from country_primer.data_first_pipeline import fetch_all")
    elif line.strip() in ("CSS,", "_format_value,", "_gaps_html,", "_latest,", "_section_nav,", "_sections_html,", "_write_clean,"):
        pass
    else:
        new_code.append(line)

new_code_text = "\\n".join(new_code)
match = re.search(r"def _fetch_one\(", new_code_text)
if match:
    new_code_text = new_code_text[:match.start()]

new_code_text += """
def inject_output_index(summary: dict[str, Any]) -> None:
    index_path = OUTPUT / "index.html"
    if not index_path.exists():
        return
    html = index_path.read_text()
    html = re.sub(r"\\n\\s*<!-- JP dashboard card -->.*?<!-- /JP dashboard card -->", "", html, flags=re.S)
    
    card = f'''
  <!-- JP dashboard card -->
  <a href="japan.html" class="card clean">
    <div class="card-kicker">JPY · BOJ · Japan data-first page</div>
    <h2>Japan</h2>
    <div class="stats">
      <div class="stat"><span>Rendered charts</span><strong>{summary['charts']}</strong></div>
      <div class="stat"><span>Proxy fills</span><strong>0</strong></div>
      <div class="stat"><span>Data gaps tracked</span><strong>{summary['data_gaps']}</strong></div>
      <div class="stat"><span>Target Rate</span><strong>{summary.get('boj_rate_latest', 'n/a')}</strong></div>
      <div class="stat"><span>Source groups</span><strong>{summary['source_groups']}</strong></div>
      <div class="stat"><span>Framework</span><strong>GS Japan statistics logic</strong></div>
    </div>
  </a>
  <!-- /JP dashboard card -->'''
  
    marker = '  </section>\\n  <nav class="links"'
    if marker in html:
        html = html.replace(marker, card + "\\n  </section>\\n  <nav class=\\"links\\"", 1)
        
    html = re.sub(r"Macro Dashboard Archive · CEE-4 v4 \\+ China[^<]*", "Macro Dashboard Archive · CEE-4 v4 + China + Japan + South Africa + UK + US", html)
    html = re.sub(
        r"Generated archive entry for the proxy-free CEE-4 dashboards plus the [^.]*\\.",
        "Generated archive entry for the proxy-free CEE-4 dashboards plus the China, Japan, South Africa, UK, and US data-first pages.",
        html,
    )
    html = html.replace("<strong>5</strong><span>country dashboards</span>", "<strong>6</strong><span>country dashboards</span>")
    
    from country_primer.page_renderer import _write_clean
    _write_clean(index_path, html)

def build(data_mode: str | None = None) -> Path:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    data_mode = (data_mode or os.environ.get("COUNTRY_PRIMER_DATA_MODE") or "refresh").strip().lower()
    config = _load_config()
    
    registry = {
        "fred_us": lambda spec, cache: fetch_fred_us(requests.Session(), spec),
        "boj_time_series": lambda spec, cache: fetch_boj_flatfile(requests.Session(), spec),
        "stat_go_jp_api": lambda spec, cache: fetch_estat(requests.Session(), spec),
    }

    if data_mode == "snapshot":
        series_list = load_canonical_data_first_frame(CANONICAL_JSON, config)
    else:
        from country_primer.source_health import SOURCE_HEALTH
        from country_primer.data_first_pipeline import fetch_all
        SOURCE_HEALTH.reset()
        series_list, _ = fetch_all(config, registry, max_workers=4)
        series_list = retain_last_known_good_series(series_list, CANONICAL_JSON, config)
        series_list = track_revisions_and_vintages(series_list, CANONICAL_JSON, config)

    charted = [item for item in series_list if item.get("observations")]
    boj_rate = next((item for item in charted if item["id"] == "boj_policy_balance_rate"), None)
    
    from country_primer.page_renderer import _latest, build_country_page
    boj_latest = _latest(boj_rate) if boj_rate else None
    boj_latest_str = f"{float(boj_latest['value']):.2f}% ({boj_latest['date']})" if boj_latest else "n/a"

    summary = build_country_page(
        country_code="JP",
        config=config,
        series_list=series_list,
        out_html=OUT_HTML,
        summary_json=SUMMARY_JSON,
        canonical_json=CANONICAL_JSON,
        data_mode=data_mode,
        summary_key_ids=SUMMARY_KEY_IDS,
        latest_value_key="boj_rate_latest",
        latest_value_display=boj_latest_str
    )

    inject_output_index(summary)
    
    if not os.environ.get("COUNTRY_PRIMER_SKIP_ARCHIVE"):
        from build_dashboard_archive import build_archive
        build_archive()
    return OUT_HTML

if __name__ == "__main__":
    path = build()
    print(f"Wrote {path} ({path.stat().st_size:,} bytes)")
"""

Path("scripts/build_japan_dashboard.py").write_text(new_code_text)
