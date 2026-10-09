from pathlib import Path
code = Path("scripts/build_uk_dashboard.py").read_text()
code = code.replace("\\n", "\n")
Path("scripts/build_uk_dashboard.py").write_text(code)
