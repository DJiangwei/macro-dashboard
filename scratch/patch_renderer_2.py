import re
from pathlib import Path

path = Path("src/country_primer/page_renderer.py")
text = path.read_text()

# We want to add native and mirror before generated_date
text = text.replace(
    "    generated_date = datetime.now(UTC).date().isoformat()",
    """    native = sum(1 for item in series_list if item.get("source_authority") == "official primary" and item.get("observations"))
    mirror = sum(1 for item in series_list if item.get("source_authority") == "official mirror" and item.get("observations"))
    generated_date = datetime.now(UTC).date().isoformat()"""
)

path.write_text(text)
