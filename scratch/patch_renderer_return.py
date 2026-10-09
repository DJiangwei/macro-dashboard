import re
from pathlib import Path

path = Path("src/country_primer/page_renderer.py")
text = path.read_text()

text = text.replace(') -> Path:', ') -> dict[str, Any]:')
text = text.replace('    return out_html\n', '    return summary\n')

path.write_text(text)
