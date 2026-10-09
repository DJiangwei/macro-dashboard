import re
from pathlib import Path

path = Path("src/country_primer/page_renderer.py")
text = path.read_text()

# Remove the import I just added
text = text.replace("from country_primer.cross_checks import evaluate_cross_checks\n", "", 1)

# Add it after future imports
text = text.replace("from __future__ import annotations\n", "from __future__ import annotations\nfrom country_primer.cross_checks import evaluate_cross_checks\n", 1)

path.write_text(text)
