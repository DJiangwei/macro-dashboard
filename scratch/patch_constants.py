import re
from pathlib import Path

path = Path("src/country_primer/page_renderer.py")
text = path.read_text()

constants = """
BG = "#f4efe7"
FG = "#171310"
MUTED = "#63574e"
ACCENT = "#8a593d"
PAPER = "rgba(255,252,246,0.90)"
FONT = "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif"
"""

# Remove old ACCENT
text = re.sub(r'ACCENT = "#8a593d"\n', '', text)
text = text.replace('import json', f'import json\n{constants}')

path.write_text(text)
