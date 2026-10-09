import re
from pathlib import Path

path = Path("src/country_primer/page_renderer.py")
text = path.read_text()

# Swap the order
old_str = """    data_mode: str,
    extra_cards: list[dict[str, Any]] | None = None,
    summary_key_ids: list[str],
    latest_value_key: str = "",
    latest_value_display: str = ""
) -> dict[str, Any]:"""
new_str = """    data_mode: str,
    summary_key_ids: list[str],
    extra_cards: list[dict[str, Any]] | None = None,
    latest_value_key: str = "",
    latest_value_display: str = ""
) -> dict[str, Any]:"""

text = text.replace(old_str, new_str)
path.write_text(text)
