import re
from pathlib import Path

for name in ["build_south_africa_dashboard.py", "build_japan_dashboard.py", "build_uk_dashboard.py", "build_us_dashboard.py"]:
    p = Path("scripts") / name
    if not p.exists(): continue
    text = p.read_text()
    # Find something like r"\n\s*<!--
    # where the \n is a literal newline
    # We can just replace the literal newline inside the string.
    text = re.sub(r'html = re\.sub\(r"\n\\s\*<!--', r'html = re.sub(r"\\n\\s*<!--', text)
    p.write_text(text)
