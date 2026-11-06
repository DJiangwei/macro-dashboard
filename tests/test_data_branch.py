"""The data branch carries accumulated history and never loses dates on a push."""
import importlib.util
import json
import shutil
import subprocess
from pathlib import Path


def _guard():
    spec = importlib.util.spec_from_file_location("accumulated_guard", "scripts/accumulated_guard.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _history(path: Path, *dates: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"observations": [{"date": day, "value": 1.0} for day in dates]}))


def test_files_lists_accumulated_history(tmp_path) -> None:
    (tmp_path / "scripts").mkdir()
    shutil.copy("scripts/data_branch.sh", tmp_path / "scripts" / "data_branch.sh")
    for name in ("output/a.json", "data/b.json", "data/accumulated/base_x.json"):
        (tmp_path / name).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / name).write_text("{}")
    result = subprocess.run(["sh", str(tmp_path / "scripts" / "data_branch.sh"), "files"], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert set(result.stdout.split()) == {"output/a.json", "data/b.json", "data/accumulated/base_x.json"}


def test_guard_flags_missing_and_shortened_files(tmp_path) -> None:
    branch, local = tmp_path / "branch", tmp_path / "local"
    _history(branch / "x.json", "2026-08-01", "2026-08-02")
    _history(branch / "y.json", "2026-08-01")
    _history(local / "x.json", "2026-08-02", "2026-08-03")
    assert _guard().shrinking_files(branch, local) == ["x.json", "y.json"]


def test_guard_passes_a_superset(tmp_path) -> None:
    branch, local = tmp_path / "branch", tmp_path / "local"
    _history(branch / "x.json", "2026-08-01", "2026-08-02")
    _history(local / "x.json", "2026-08-01", "2026-08-02", "2026-08-03")
    _history(local / "new.json", "2026-08-03")
    assert _guard().shrinking_files(branch, local) == []
