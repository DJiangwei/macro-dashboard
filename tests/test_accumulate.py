"""Short-window sources keep a growing history in data/accumulated/."""
import json
from datetime import date

import pytest


def _obs(*pairs):
    return [{"date": day, "value": value} for day, value in pairs]


def test_merge_keeps_old_dates_and_lets_fresh_values_win() -> None:
    from country_primer.accumulate import merge_observations

    merged, revisions = merge_observations(
        _obs(("2026-08-01", 10.0), ("2026-08-02", 11.0)),
        _obs(("2026-08-02", 12.0), ("2026-08-03", 13.0)),
        revised_on="2026-11-06",
    )
    assert merged == _obs(("2026-08-01", 10.0), ("2026-08-02", 12.0), ("2026-08-03", 13.0))
    assert revisions == [{"date": "2026-08-02", "previous": 11.0, "value": 12.0, "revised_on": "2026-11-06"}]


def test_accumulate_series_writes_and_extends_history(tmp_path) -> None:
    from country_primer.accumulate import accumulate_series

    first = {"id": "shfe_copper_stocks", "source_name": "SHFE", "observations": _obs(("2026-08-01", 1.0), ("2026-08-02", 2.0))}
    accumulate_series(first, "BASE", today=date(2026, 11, 6), directory=tmp_path)
    stored = json.loads((tmp_path / "base_shfe_copper_stocks.json").read_text())
    assert stored["schema_version"] == "accumulated-v1"

    second = {**first, "observations": _obs(("2026-08-02", 2.0), ("2026-08-03", 3.0))}
    result = accumulate_series(second, "BASE", today=date(2026, 11, 7), directory=tmp_path)
    assert [item["date"] for item in result["observations"]] == ["2026-08-01", "2026-08-02", "2026-08-03"]
    assert result["accumulated_since"] == "2026-08-01"


def test_empty_fetch_never_touches_the_file(tmp_path) -> None:
    from country_primer.accumulate import accumulate_series

    series = {"id": "shfe_zinc_stocks", "observations": _obs(("2026-08-01", 1.0))}
    accumulate_series(series, "BASE", today=date(2026, 11, 6), directory=tmp_path)
    path = tmp_path / "base_shfe_zinc_stocks.json"
    before = path.read_bytes()
    empty = {"id": "shfe_zinc_stocks", "observations": []}
    assert accumulate_series(empty, "BASE", today=date(2026, 11, 7), directory=tmp_path) == empty
    assert path.read_bytes() == before


def test_corrupt_file_raises_and_is_preserved(tmp_path) -> None:
    from country_primer.accumulate import accumulate_series

    path = tmp_path / "base_shfe_copper_stocks.json"
    path.write_text("{not json")
    series = {"id": "shfe_copper_stocks", "observations": _obs(("2026-08-01", 1.0))}
    with pytest.raises(RuntimeError, match="base_shfe_copper_stocks.json"):
        accumulate_series(series, "BASE", today=date(2026, 11, 6), directory=tmp_path)
    assert path.read_text() == "{not json"


def test_pipeline_accumulates_flagged_specs(tmp_path, monkeypatch) -> None:
    from country_primer import accumulate
    from country_primer.data_first_pipeline import fetch_all

    monkeypatch.setattr(accumulate, "ACCUMULATED_DIR", tmp_path)
    registry = {"fixed": lambda spec, cache: {"observations": _obs(("2026-08-01", 5.0))}}
    config = {
        "iso2": "BASE",
        "indicators": [
            {"id": "kept", "fetcher": "fixed", "accumulate": True},
            {"id": "plain", "fetcher": "fixed"},
        ],
    }
    series, _ = fetch_all(config, registry, sequential=True)
    by_id = {item["id"]: item for item in series}
    assert (tmp_path / "base_kept.json").exists()
    assert not (tmp_path / "base_plain.json").exists()
    assert by_id["kept"]["accumulated_since"] == "2026-08-01"
    assert "accumulated_since" not in by_id["plain"]
