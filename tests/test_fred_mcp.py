"""Tests for the FRED MCP Connector server (scripts/fred_mcp_server.py)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

import fred_mcp_server as fms


def test_mcp_initialize_and_tools_list() -> None:
    init_resp = fms.handle_jsonrpc_message(
        {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2024-11-05"}}
    )
    assert init_resp is not None
    assert init_resp["id"] == 1
    assert init_resp["result"]["serverInfo"]["name"] == "fred-mcp-connector"

    list_resp = fms.handle_jsonrpc_message({"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
    assert list_resp is not None
    tools = list_resp["result"]["tools"]
    tool_names = [t["name"] for t in tools]
    assert tool_names == [
        "fred-search-series",
        "fred-get-series-metadata",
        "fred-get-series-observations",
        "fred-download-series-observations-link",
        "fred-graph-series",
    ]


def test_fred_download_link_and_graph_tools_offline() -> None:
    dl_resp = fms.handle_jsonrpc_message(
        {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {
                "name": "fred-download-series-observations-link",
                "arguments": {
                    "series_id": "rtwexbgs",
                    "observation_start": "2020-01-01",
                    "units": "pc1",
                },
            },
        }
    )
    assert dl_resp is not None
    assert dl_resp["result"]["isError"] is False
    payload = json.loads(dl_resp["result"]["content"][0]["text"])
    assert payload["series_id"] == "RTWEXBGS"
    assert "id=RTWEXBGS" in payload["public_csv_download_url"]
    assert "transformation=pc1" in payload["public_csv_download_url"]
    assert "$FRED_API_KEY" in payload["api_download_url_template"]

    graph_resp = fms.handle_jsonrpc_message(
        {
            "jsonrpc": "2.0",
            "id": 4,
            "method": "tools/call",
            "params": {
                "name": "fred-graph-series",
                "arguments": {
                    "series": [
                        "DTWEXBGS",
                        {"series_id": "RTWEXBGS", "units": "lin", "axis": "right"},
                    ],
                    "observation_start": "2020-01-01",
                    "title": "Broad Dollar Nominal vs Real",
                },
            },
        }
    )
    assert graph_resp is not None
    assert graph_resp["result"]["isError"] is False
    g_payload = json.loads(graph_resp["result"]["content"][0]["text"])
    assert g_payload["series_count"] == 2
    assert "DTWEXBGS%2CRTWEXBGS" in g_payload["fred_graph_url"] or "DTWEXBGS,RTWEXBGS" in g_payload["fred_graph_url"]


def test_secret_redaction_strips_api_key() -> None:
    raw = "HTTPSConnectionPool: url: /fred/series?series_id=GDPC1&api_key=abcdef1234567890&file_type=json"
    redacted = fms._redact_secrets(raw)
    assert "abcdef1234567890" not in redacted
    assert "api_key=REDACTED" in redacted


def test_mocked_search_metadata_and_observations(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_fred_get(endpoint: str, params: dict, timeout: int = 20) -> dict:
        if endpoint == "series/search":
            return {
                "count": 1,
                "seriess": [
                    {
                        "id": "RTWEXBGS",
                        "title": "Real Broad Dollar Index",
                        "units": "Index Jan 2006=100",
                        "units_short": "Index Jan 2006=100",
                        "frequency": "Monthly",
                        "frequency_short": "M",
                        "seasonal_adjustment": "Not Seasonally Adjusted",
                        "seasonal_adjustment_short": "NSA",
                        "observation_start": "2006-01-01",
                        "observation_end": "2026-09-01",
                        "last_updated": "2026-10-01 15:20:26-05",
                        "popularity": 68,
                        "notes": "Real broad dollar index from Fed H.10.",
                    }
                ],
            }
        if endpoint == "series":
            return {
                "seriess": [
                    {
                        "id": params["series_id"],
                        "title": "Real Broad Dollar Index",
                        "units": "Index Jan 2006=100",
                        "units_short": "Index Jan 2006=100",
                        "frequency": "Monthly",
                        "frequency_short": "M",
                        "seasonal_adjustment": "Not Seasonally Adjusted",
                        "seasonal_adjustment_short": "NSA",
                        "observation_start": "2006-01-01",
                        "observation_end": "2026-09-01",
                        "last_updated": "2026-10-01 15:20:26-05",
                        "popularity": 68,
                        "notes": "Real broad dollar index from Fed H.10.",
                    }
                ]
            }
        if endpoint == "series/release":
            return {"releases": [{"id": 17, "name": "H.10 Foreign Exchange Rates", "press_release": True}]}
        if endpoint == "series/observations":
            return {
                "units": params.get("units", "lin"),
                "output_type": 1,
                "observation_start": "2006-01-01",
                "observation_end": "2026-09-01",
                "observations": [
                    {"date": "2026-08-01", "value": "115.2"},
                    {"date": "2026-09-01", "value": "114.8"},
                    {"date": "2026-10-01", "value": "."},
                ],
            }
        return {}

    monkeypatch.setattr(fms, "_fred_get", fake_fred_get)
    monkeypatch.setattr(fms, "_load_fred_api_key", lambda: "dummy_key")

    search_res = fms.dispatch_tool_call("fred-search-series", {"search_text": "real broad dollar"})
    assert search_res["returned"] == 1
    assert search_res["series"][0]["id"] == "RTWEXBGS"

    meta_res = fms.dispatch_tool_call("fred-get-series-metadata", {"series_id": "RTWEXBGS"})
    assert meta_res["id"] == "RTWEXBGS"
    assert meta_res["release"]["name"] == "H.10 Foreign Exchange Rates"

    obs_res = fms.dispatch_tool_call(
        "fred-get-series-observations",
        {"series_id": "RTWEXBGS", "units": "lin", "limit": 10},
    )
    assert obs_res["returned_observations"] == 2
    assert obs_res["latest"] == {"date": "2026-09-01", "value": 114.8}
