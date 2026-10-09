import re
from pathlib import Path

for name in ["build_south_africa_dashboard.py", "build_japan_dashboard.py", "build_uk_dashboard.py", "build_us_dashboard.py"]:
    p = Path("scripts") / name
    if not p.exists(): continue
    text = p.read_text()
    
    text = text.replace("marker = '  </section>\n  <nav class=\"links\"'", "marker = '  </section>\\n  <nav class=\"links\"'")
    text = text.replace('html.replace(marker, card + "\n  </section>\n  <nav class=\\"links\\"", 1)', 'html.replace(marker, card + "\\n  </section>\\n  <nav class=\\"links\\"", 1)')
    p.write_text(text)
