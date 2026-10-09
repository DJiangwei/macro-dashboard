import re
from pathlib import Path

code = Path("scripts/build_uk_dashboard.py").read_text()
code = re.sub(r"r\"\n\\s\*<!-- UK dashboard card -->\.\*\?<!-- \/UK dashboard card -->\"",
              r'r"\\n\\s*<!-- UK dashboard card -->.*?<!-- /UK dashboard card -->"', code)
code = code.replace("marker = '  </section>\n  <nav class=\"links\"'", "marker = '  </section>\\n  <nav class=\"links\"'")
code = code.replace("html.replace(marker, card + \"\n  </section>\n  <nav class=\\\"links\\\"\", 1)", "html.replace(marker, card + \"\\n  </section>\\n  <nav class=\\\"links\\\"\", 1)")

Path("scripts/build_uk_dashboard.py").write_text(code)
