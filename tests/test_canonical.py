import json

from dashboard_summary_utils import write_canonical_data_first_frame


def test_canonical_v2_deduplicates_metadata(tmp_path) -> None:
    path = tmp_path / "frame.json"
    metadata = write_canonical_data_first_frame(
        path,
        "UK",
        [{
            "id": "cpi_yoy",
            "section": "prices",
            "label_en": "CPI",
            "label_zh": "CPI",
            "unit": "% YoY",
            "frequency": "monthly",
            "source_name": "ONS",
            "series": "D7G7",
            "source_url": "https://www.ons.gov.uk/",
            "observations": [
                {"date": "2026-05-01", "value": 2.1},
                {"date": "2026-06-01", "value": 2.0},
            ],
        }],
    )
    payload = json.loads(path.read_text())
    assert payload["schema_version"] == "data-first-canonical-v2"
    assert payload["series"][0]["concept_id"] == "headline_inflation"
    assert payload["series"][0]["observations"] == [["2026-05-01", 2.1], ["2026-06-01", 2.0]]
    assert metadata["series_count"] == 1
    assert metadata["observation_count"] == 2
