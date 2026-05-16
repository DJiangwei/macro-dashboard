"""Environment doctor for coding agents working on Country Primer."""
from __future__ import annotations

import importlib.metadata
import platform
import sys


REQUIRED = {
    "jinja2": "jinja2",
    "pandas": "pandas",
    "plotly": "plotly",
    "pyyaml": "yaml",
    "requests": "requests",
}


def main() -> None:
    print(f"Python executable: {sys.executable}")
    print(f"Python version: {platform.python_version()}")
    if sys.version_info[:2] != (3, 12):
        raise SystemExit("Expected Python 3.12.x. Run `uv sync` and use `uv run ...`.")

    missing: list[str] = []
    for package, import_name in REQUIRED.items():
        try:
            __import__(import_name)
            version = importlib.metadata.version(package)
        except Exception:
            missing.append(package)
            continue
        print(f"{package}: {version}")

    if missing:
        raise SystemExit(f"Missing dependencies: {', '.join(missing)}. Run `uv sync`.")

    print("Environment OK.")


if __name__ == "__main__":
    main()
