import pytest
from unittest.mock import MagicMock
from country_primer.adapters import (
    fetch_ecb_sdmx,
    fetch_eurostat_jsonstat,
    fetch_spread,
    sdmx_period_to_date,
)

def test_sdmx_period_to_date_formats():
    assert sdmx_period_to_date("2024-M01") == "2024-01-01"
    assert sdmx_period_to_date("2024M01") == "2024-01-01"
    assert sdmx_period_to_date("2024-Q1") == "2024-01-01"
    assert sdmx_period_to_date("2024Q3") == "2024-07-01"
    assert sdmx_period_to_date("2024-05") == "2024-05-01"
    assert sdmx_period_to_date("2024-W10") == "2024-03-04"
    assert sdmx_period_to_date("2024-10-15") == "2024-10-15"
    assert sdmx_period_to_date("2024") == "2024-01-01"

def test_fetch_ecb_sdmx_mock():
    mock_csv = """KEY,TIME_PERIOD,OBS_VALUE,TITLE
FM.D.U2.EUR.4F.KR.DFR.LEV,2024-01-01,4.00,Deposit Facility Rate
FM.D.U2.EUR.4F.KR.DFR.LEV,2024-06-01,3.75,Deposit Facility Rate
FM.D.U2.EUR.4F.KR.DFR.LEV,2024-09-01,3.50,Deposit Facility Rate
"""
    session = MagicMock()
    mock_response = MagicMock()
    mock_response.text = mock_csv
    session.get.return_value = mock_response

    spec = {
        "id": "policy_rate",
        "flow": "FM",
        "series": "D.U2.EUR.4F.KR.DFR.LEV",
    }
    result = fetch_ecb_sdmx(session, spec)
    assert result["id"] == "policy_rate"
    assert len(result["observations"]) == 3
    assert result["observations"][0] == {"date": "2024-01-01", "value": 4.00}
    assert result["observations"][-1] == {"date": "2024-09-01", "value": 3.50}

def test_fetch_eurostat_jsonstat_mock():
    mock_json = {
        "version": "2.0",
        "class": "dataset",
        "id": ["freq", "unit", "geo", "time"],
        "size": [1, 1, 1, 3],
        "dimension": {
            "freq": {"category": {"index": {"Q": 0}}},
            "unit": {"category": {"index": {"CLV_PCH_PRE": 0}}},
            "geo": {"category": {"index": {"EA": 0}}},
            "time": {"category": {"index": {"2024-Q1": 0, "2024-Q2": 1, "2024-Q3": 2}}},
        },
        "value": {"0": 0.3, "1": 0.2, "2": 0.4},
    }
    session = MagicMock()
    mock_response = MagicMock()
    mock_response.json.return_value = mock_json
    session.get.return_value = mock_response

    spec = {
        "id": "real_gdp_growth",
        "dataset": "namq_10_gdp",
        "filters": {"freq": "Q", "unit": "CLV_PCH_PRE", "geo": "EA"},
    }
    result = fetch_eurostat_jsonstat(session, spec)
    assert result["id"] == "real_gdp_growth"
    assert len(result["observations"]) == 3
    assert result["observations"][0] == {"date": "2024-01-01", "value": 0.3}
    assert result["observations"][1] == {"date": "2024-04-01", "value": 0.2}
    assert result["observations"][2] == {"date": "2024-07-01", "value": 0.4}

def test_fetch_spread_mock():
    session = MagicMock()
    
    spec = {
        "id": "it_de_spread",
        "factor": 100,  # Convert percentage to bps
        "primary": {
            "fetcher": "ecb_sdmx",
            "flow": "IRS",
            "series": "M.IT.10Y",
        },
        "secondary": {
            "fetcher": "ecb_sdmx",
            "flow": "IRS",
            "series": "M.DE.10Y",
        },
    }

    csv_it = """TIME_PERIOD,OBS_VALUE\n2024-01-01,3.80\n2024-02-01,3.90\n"""
    csv_de = """TIME_PERIOD,OBS_VALUE\n2024-01-01,2.20\n2024-02-01,2.40\n"""

    resp_it = MagicMock()
    resp_it.text = csv_it
    resp_de = MagicMock()
    resp_de.text = csv_de
    session.get.side_effect = [resp_it, resp_de]

    result = fetch_spread(session, spec)
    assert result["id"] == "it_de_spread"
    assert len(result["observations"]) == 2
    # 3.80 - 2.20 = 1.60 * 100 = 160.0 bps
    assert result["observations"][0] == {"date": "2024-01-01", "value": 160.0}
    # 3.90 - 2.40 = 1.50 * 100 = 150.0 bps
    assert result["observations"][1] == {"date": "2024-02-01", "value": 150.0}
