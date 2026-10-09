import re
from pathlib import Path

path = Path("src/country_primer/page_renderer.py")
text = path.read_text()

# We need to add _render_cards.
render_cards_func = """
def _render_cards(series_list: list[dict[str, Any]], extra_cards: list[dict[str, Any]], summary_key_ids: list[str]) -> str:
    by_id = {item["id"]: item for item in series_list}
    cards_html: list[str] = []
    
    # Renders the headline IDs from the series list
    for indicator_id in summary_key_ids[:4]:
        series = by_id.get(indicator_id)
        latest = _latest(series) if series else None
        if not series or not latest:
            continue
        cards_html.append(f'''
<div class="data-card">
  <span><span data-lang="en">{escape(series.get('label_en', series.get('label', '')))}</span><span data-lang="zh">{escape(series.get('label_zh', series.get('label', '')))}</span></span>
  <strong>{_format_value(float(latest['value']), series.get('unit', ''))}</strong>
  <small>{escape(str(latest['date']))} · {escape(series.get('source_name', ''))}</small>
</div>''')
        
    for card in extra_cards:
        cards_html.append(f'''
<div class="data-card">
  <span><span data-lang="en">{escape(card.get('label_en', card.get('label', '')))}</span><span data-lang="zh">{escape(card.get('label_zh', card.get('label', '')))}</span></span>
  <strong>{escape(str(card.get('value', 'n/a')))}</strong>
  <small>{escape(str(card.get('updated', 'n/a')))} · {escape(card.get('source', 'Extra'))}</small>
</div>''')
        
    return "\\n".join(cards_html)
"""

text = text.replace('from country_primer.source_health import write_source_health_report',
                    'from country_primer.source_health import write_source_health_report\n' + render_cards_func)

# Fix render_html signature to take summary_key_ids
text = text.replace(
    'def render_html(config: dict[str, Any], series_list: list[dict[str, Any]], cards: list[dict[str, Any]]) -> str:',
    'def render_html(config: dict[str, Any], series_list: list[dict[str, Any]], cards: list[dict[str, Any]], summary_key_ids: list[str] = None) -> str:'
)
text = text.replace('{_render_cards(series_list, cards)}', '{_render_cards(series_list, cards, summary_key_ids or [])}')

# Fix build_country_page calling render_html
text = text.replace('html = render_html(config, series_list, extra_cards or [])', 'html = render_html(config, series_list, extra_cards or [], summary_key_ids)')

path.write_text(text)
