#!/usr/bin/env python3
"""FRED MCP Server & CLI Connector for Country Primer.

Implements the five official St. Louis Fed FRED MCP Connector tools
(https://mcp.stlouisfed.org / https://fredhelp.stlouisfed.org/fred/data/ai/fred-mcp-connector/):
  1. fred-search-series
  2. fred-get-series-metadata
  3. fred-get-series-observations
  4. fred-download-series-observations-link
  5. fred-graph-series

Supports both:
  - Standard MCP JSON-RPC 2.0 over stdio (default when invoked with no args)
  - Direct CLI execution (`--cli search|metadata|observations|download-link|graph`)

Authentication:
  Reads `FRED_API_KEY` from environment or `.env.local` in the repository root.
  Never logs or echoes `FRED_API_KEY` in output or error messages.
  For `fred-get-series-observations` with `units="lin"` and no API key,
  automatically falls back to the public `fredgraph.csv` endpoint.
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import os
import re
import sys
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

import requests

ROOT = Path(__file__).resolve().parents[1]
FRED_API_BASE = "https://api.stlouisfed.org/fred"
FRED_GRAPH_CSV = "https://fred.stlouisfed.org/graph/fredgraph.csv"
FRED_GRAPH_PAGE = "https://fred.stlouisfed.org/graph/"
PROTOCOL_VERSION = "2024-11-05"

VALID_UNITS = ("lin", "chg", "ch1", "pch", "pc1", "pca", "cch", "cca", "log")
VALID_FREQUENCIES = ("d", "w", "bw", "m", "q", "sa", "a")
VALID_AGG_METHODS = ("avg", "sum", "eop")


def _redact_secrets(text: str) -> str:
    """Scrub any api_key query parameter from error messages or URLs."""
    return re.sub(r"api_key=[^&\s'\"]+", "api_key=REDACTED", str(text))


def _load_fred_api_key() -> str:
    """Load FRED_API_KEY from environment or repo-local .env.local / .env."""
    env_key = os.environ.get("FRED_API_KEY", "").strip()
    if env_key:
        return env_key
    for fname in (".env.local", ".env"):
        env_path = ROOT / fname
        if not env_path.exists():
            continue
        for raw_line in env_path.read_text(encoding="utf-8", errors="ignore").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, val = line.split("=", 1)
            if key.strip() == "FRED_API_KEY":
                cleaned = val.strip().strip('"').strip("'")
                if cleaned:
                    return cleaned
    return ""


def _fred_get(endpoint: str, params: dict[str, Any], timeout: int = 20) -> dict[str, Any]:
    api_key = _load_fred_api_key()
    if not api_key:
        raise RuntimeError(
            "FRED_API_KEY is not configured in environment or .env.local. "
            "Set FRED_API_KEY or use fred-get-series-observations with units='lin' for fredgraph.csv fallback."
        )
    query = {k: v for k, v in params.items() if v is not None and v != ""}
    query["api_key"] = api_key
    query["file_type"] = "json"
    url = f"{FRED_API_BASE}/{endpoint.lstrip('/')}"
    try:
        resp = requests.get(url, params=query, timeout=timeout)
        resp.raise_for_status()
        return resp.json()
    except Exception as exc:
        raise RuntimeError(f"FRED API request failed for {endpoint}: {_redact_secrets(str(exc))}") from None


def fred_search_series(
    search_text: str,
    *,
    search_type: str = "full_text",
    limit: int = 15,
    order_by: str = "search_rank",
    sort_order: str = "desc",
    tag_names: str | None = None,
    filter_variable: str | None = None,
    filter_value: str | None = None,
) -> dict[str, Any]:
    """Search FRED data series by keywords, concepts, or filters."""
    if not search_text or not str(search_text).strip():
        raise ValueError("search_text is required")
    capped_limit = max(1, min(int(limit or 15), 100))
    payload = _fred_get(
        "series/search",
        {
            "search_text": str(search_text).strip(),
            "search_type": search_type or "full_text",
            "limit": capped_limit,
            "order_by": order_by or "search_rank",
            "sort_order": sort_order or "desc",
            "tag_names": tag_names,
            "filter_variable": filter_variable,
            "filter_value": filter_value,
        },
    )
    items = []
    for s in payload.get("seriess", []) or []:
        notes = str(s.get("notes") or "").strip()
        if len(notes) > 400:
            notes = notes[:397] + "..."
        items.append(
            {
                "id": s.get("id"),
                "title": s.get("title"),
                "units": s.get("units"),
                "units_short": s.get("units_short"),
                "frequency": s.get("frequency"),
                "frequency_short": s.get("frequency_short"),
                "seasonal_adjustment": s.get("seasonal_adjustment"),
                "seasonal_adjustment_short": s.get("seasonal_adjustment_short"),
                "observation_start": s.get("observation_start"),
                "observation_end": s.get("observation_end"),
                "last_updated": s.get("last_updated"),
                "popularity": s.get("popularity"),
                "Url": f"https://fred.stlouisfed.org/series/{s.get('id')}",
                "notes": notes,
            }
        )
    return {
        "search_text": search_text,
        "count": payload.get("count", len(items)),
        "returned": len(items),
        "series": items,
    }


def fred_get_series_metadata(
    series_id: str,
    *,
    include_release: bool = True,
    include_tags: bool = False,
) -> dict[str, Any]:
    """Retrieve comprehensive metadata for a specific FRED series."""
    sid = str(series_id or "").strip().upper()
    if not sid:
        raise ValueError("series_id is required")
    payload = _fred_get("series", {"series_id": sid})
    series_list = payload.get("seriess", []) or []
    if not series_list:
        raise LookupError(f"FRED series not found: {sid}")
    meta = series_list[0]
    result: dict[str, Any] = {
        "id": meta.get("id", sid),
        "title": meta.get("title"),
        "units": meta.get("units"),
        "units_short": meta.get("units_short"),
        "frequency": meta.get("frequency"),
        "frequency_short": meta.get("frequency_short"),
        "seasonal_adjustment": meta.get("seasonal_adjustment"),
        "seasonal_adjustment_short": meta.get("seasonal_adjustment_short"),
        "observation_start": meta.get("observation_start"),
        "observation_end": meta.get("observation_end"),
        "realtime_start": meta.get("realtime_start"),
        "realtime_end": meta.get("realtime_end"),
        "last_updated": meta.get("last_updated"),
        "popularity": meta.get("popularity"),
        "series_url": f"https://fred.stlouisfed.org/series/{sid}",
        "notes": str(meta.get("notes") or "").strip(),
    }
    if include_release:
        try:
            rel_payload = _fred_get("series/release", {"series_id": sid})
            releases = rel_payload.get("releases", []) or []
            if releases:
                rel = releases[0]
                result["release"] = {
                    "id": rel.get("id"),
                    "name": rel.get("name"),
                    "press_release": rel.get("press_release"),
                    "link": rel.get("link"),
                }
        except Exception:
            pass
    if include_tags:
        try:
            tag_payload = _fred_get("series/tags", {"series_id": sid})
            tags = tag_payload.get("tags", []) or []
            result["tags"] = [
                {"name": t.get("name"), "group_id": t.get("group_id"), "notes": t.get("notes")}
                for t in tags[:25]
            ]
        except Exception:
            pass
    return result


def _fetch_fredgraph_csv_fallback(
    series_id: str,
    *,
    observation_start: str | None = None,
    observation_end: str | None = None,
) -> list[dict[str, Any]]:
    params: dict[str, str] = {"id": series_id}
    if observation_start:
        params["cosd"] = observation_start
    if observation_end:
        params["coed"] = observation_end
    resp = requests.get(FRED_GRAPH_CSV, params=params, timeout=20)
    resp.raise_for_status()
    reader = csv.DictReader(io.StringIO(resp.text))
    rows: list[dict[str, Any]] = []
    for row in reader:
        d = (row.get("DATE") or row.get("observation_date") or "").strip()
        val_raw = (row.get(series_id) or "").strip()
        if not d or not val_raw or val_raw == ".":
            continue
        try:
            rows.append({"date": d, "value": float(val_raw)})
        except ValueError:
            continue
    return rows


def fred_get_series_observations(
    series_id: str,
    *,
    observation_start: str | None = None,
    observation_end: str | None = None,
    units: str = "lin",
    frequency: str | None = None,
    aggregation_method: str = "avg",
    realtime_start: str | None = None,
    realtime_end: str | None = None,
    limit: int = 240,
    sort_order: str = "asc",
) -> dict[str, Any]:
    """Retrieve observations for a FRED series with optional transformations and frequency aggregation."""
    sid = str(series_id or "").strip().upper()
    if not sid:
        raise ValueError("series_id is required")
    units_clean = (units or "lin").strip().lower()
    if units_clean not in VALID_UNITS:
        raise ValueError(f"Invalid units '{units_clean}'. Must be one of {VALID_UNITS}")
    freq_clean = frequency.strip().lower() if frequency else None
    if freq_clean and freq_clean not in VALID_FREQUENCIES:
        raise ValueError(f"Invalid frequency '{freq_clean}'. Must be one of {VALID_FREQUENCIES}")
    agg_clean = (aggregation_method or "avg").strip().lower()
    if agg_clean not in VALID_AGG_METHODS:
        raise ValueError(f"Invalid aggregation_method '{agg_clean}'. Must be one of {VALID_AGG_METHODS}")

    api_key = _load_fred_api_key()
    if not api_key and units_clean == "lin" and not freq_clean:
        obs = _fetch_fredgraph_csv_fallback(
            sid,
            observation_start=observation_start,
            observation_end=observation_end,
        )
        if sort_order == "desc":
            obs = list(reversed(obs))
        if limit and len(obs) > int(limit):
            obs = obs[-int(limit) :] if sort_order == "asc" else obs[: int(limit)]
        return {
            "series_id": sid,
            "source_mode": "fredgraph_csv_fallback",
            "units": units_clean,
            "frequency": freq_clean,
            "count": len(obs),
            "latest": obs[-1] if (obs and sort_order == "asc") else (obs[0] if obs else None),
            "observations": obs,
        }

    payload = _fred_get(
        "series/observations",
        {
            "series_id": sid,
            "observation_start": observation_start,
            "observation_end": observation_end,
            "units": units_clean,
            "frequency": freq_clean,
            "aggregation_method": agg_clean if freq_clean else None,
            "realtime_start": realtime_start,
            "realtime_end": realtime_end,
            "sort_order": sort_order or "asc",
        },
    )
    obs: list[dict[str, Any]] = []
    for item in payload.get("observations", []) or []:
        d = str(item.get("date") or "").strip()
        v = str(item.get("value") or "").strip()
        if not d or not v or v == ".":
            continue
        try:
            obs.append({"date": d, "value": float(v)})
        except ValueError:
            continue

    total_count = len(obs)
    if limit and len(obs) > int(limit):
        obs = obs[-int(limit) :] if (sort_order or "asc") == "asc" else obs[: int(limit)]

    latest = None
    if obs:
        latest = obs[-1] if (sort_order or "asc") == "asc" else obs[0]

    return {
        "series_id": sid,
        "source_mode": "fred_v1_api",
        "units": payload.get("units", units_clean),
        "output_type": payload.get("output_type"),
        "observation_start": payload.get("observation_start"),
        "observation_end": payload.get("observation_end"),
        "total_valid_observations": total_count,
        "returned_observations": len(obs),
        "latest": latest,
        "observations": obs,
    }


def fred_download_series_observations_link(
    series_id: str,
    *,
    file_format: str = "csv",
    observation_start: str | None = None,
    observation_end: str | None = None,
    units: str = "lin",
    frequency: str | None = None,
    aggregation_method: str = "avg",
) -> dict[str, Any]:
    """Generate direct download links (CSV/JSON/XML) for a FRED series without exposing API keys."""
    sid = str(series_id or "").strip().upper()
    if not sid:
        raise ValueError("series_id is required")
    fmt = (file_format or "csv").strip().lower()
    if fmt not in ("csv", "json", "xml"):
        raise ValueError("file_format must be 'csv', 'json', or 'xml'")

    csv_params: dict[str, str] = {"id": sid}
    if observation_start:
        csv_params["cosd"] = observation_start
    if observation_end:
        csv_params["coed"] = observation_end
    if units and units != "lin":
        csv_params["transformation"] = units
    if frequency:
        csv_params["fq"] = frequency
    if aggregation_method and aggregation_method != "avg":
        csv_params["fqa"] = aggregation_method

    public_csv_url = f"{FRED_GRAPH_CSV}?{urlencode(csv_params)}"

    api_params: dict[str, str] = {"series_id": sid, "file_type": fmt}
    if observation_start:
        api_params["observation_start"] = observation_start
    if observation_end:
        api_params["observation_end"] = observation_end
    if units:
        api_params["units"] = units
    if frequency:
        api_params["frequency"] = frequency
        api_params["aggregation_method"] = aggregation_method or "avg"
    api_template_url = f"{FRED_API_BASE}/series/observations?{urlencode(api_params)}&api_key=$FRED_API_KEY"

    return {
        "series_id": sid,
        "file_format": fmt,
        "series_page_url": f"https://fred.stlouisfed.org/series/{sid}",
        "public_csv_download_url": public_csv_url,
        "api_download_url_template": api_template_url,
    }


def fred_graph_series(
    series: list[Any],
    *,
    observation_start: str | None = None,
    observation_end: str | None = None,
    title: str | None = None,
) -> dict[str, Any]:
    """Generate an interactive FRED graph URL and chart configuration for up to 5 series."""
    if not series or not isinstance(series, list):
        raise ValueError("series must be a non-empty list of up to 5 series IDs or specs")
    if len(series) > 5:
        raise ValueError("fred-graph-series supports at most 5 series per graph")

    normalized: list[dict[str, str]] = []
    for item in series:
        if isinstance(item, str):
            sid = item.strip().upper()
            if sid:
                normalized.append({"series_id": sid, "units": "lin", "axis": "left"})
        elif isinstance(item, dict):
            sid = str(item.get("series_id") or item.get("id") or "").strip().upper()
            if sid:
                spec = {
                    "series_id": sid,
                    "units": str(item.get("units") or "lin").strip().lower(),
                    "axis": str(item.get("axis") or "left").strip().lower(),
                }
                if item.get("frequency"):
                    spec["frequency"] = str(item["frequency"]).strip().lower()
                normalized.append(spec)
    if not normalized:
        raise ValueError("No valid series_id found in series argument")

    ids = [s["series_id"] for s in normalized]
    graph_params: dict[str, str] = {"id": ",".join(ids)}
    if observation_start:
        graph_params["cosd"] = observation_start
    if observation_end:
        graph_params["coed"] = observation_end

    return {
        "title": title or f"FRED Graph: {', '.join(ids)}",
        "series_count": len(normalized),
        "series": normalized,
        "observation_start": observation_start,
        "observation_end": observation_end,
        "fred_graph_url": f"{FRED_GRAPH_PAGE}?{urlencode(graph_params)}",
        "fred_csv_url": f"{FRED_GRAPH_CSV}?{urlencode(graph_params)}",
    }


MCP_TOOLS: list[dict[str, Any]] = [
    {
        "name": "fred-search-series",
        "description": (
            "Search for economic data series across FRED by keywords, concepts, or filters. "
            "Returns series ID, title, units, frequency, seasonal adjustment, observation range, "
            "last updated timestamp, and popularity."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "search_text": {
                    "type": "string",
                    "description": "Keywords or series concept to search across FRED (e.g., 'real broad dollar index', 'core PCE').",
                },
                "search_type": {
                    "type": "string",
                    "enum": ["full_text", "series_id"],
                    "default": "full_text",
                },
                "limit": {
                    "type": "integer",
                    "default": 15,
                    "description": "Maximum number of results to return (1-100).",
                },
                "order_by": {
                    "type": "string",
                    "enum": [
                        "search_rank",
                        "series_id",
                        "title",
                        "units",
                        "frequency",
                        "seasonal_adjustment",
                        "realtime_start",
                        "realtime_end",
                        "last_updated",
                        "observation_start",
                        "observation_end",
                        "popularity",
                        "group_popularity",
                    ],
                    "default": "search_rank",
                },
                "sort_order": {
                    "type": "string",
                    "enum": ["asc", "desc"],
                    "default": "desc",
                },
                "tag_names": {
                    "type": "string",
                    "description": "Optional semicolon-delimited FRED tag names (e.g. 'usa;monthly;nsa').",
                },
                "filter_variable": {
                    "type": "string",
                    "enum": ["frequency", "units", "seasonal_adjustment"],
                },
                "filter_value": {
                    "type": "string",
                },
            },
            "required": ["search_text"],
        },
    },
    {
        "name": "fred-get-series-metadata",
        "description": (
            "Retrieve comprehensive metadata for a specific FRED series, including units, frequency, "
            "seasonal adjustment, release/source details, observation start/end dates, last updated timestamp, "
            "and methodology notes."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "series_id": {
                    "type": "string",
                    "description": "Exact FRED series ID (e.g., 'CPIAUCSL', 'GDPC1', 'RTWEXBGS').",
                },
                "include_release": {
                    "type": "boolean",
                    "default": True,
                    "description": "Whether to include official release metadata.",
                },
                "include_tags": {
                    "type": "boolean",
                    "default": False,
                    "description": "Whether to include FRED series tags.",
                },
            },
            "required": ["series_id"],
        },
    },
    {
        "name": "fred-get-series-observations",
        "description": (
            "Retrieve observation values for a specific FRED series, with optional date ranges, "
            "unit transformations (lin, chg, ch1, pch, pc1, pca, cch, cca, log), frequency aggregation "
            "(d, w, bw, m, q, sa, a), and real-time vintage dates."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "series_id": {
                    "type": "string",
                    "description": "Exact FRED series ID.",
                },
                "observation_start": {
                    "type": "string",
                    "description": "Start date in YYYY-MM-DD format.",
                },
                "observation_end": {
                    "type": "string",
                    "description": "End date in YYYY-MM-DD format.",
                },
                "units": {
                    "type": "string",
                    "enum": list(VALID_UNITS),
                    "default": "lin",
                    "description": (
                        "Data transformation: lin=Levels, chg=Change, ch1=Change from Year Ago, "
                        "pch=% Change, pc1=% Change from Year Ago, pca=Compounded Annual Rate of Change, "
                        "cch=Continuously Compounded Rate of Change, cca=Continuously Compounded Annual Rate of Change, log=Natural Log."
                    ),
                },
                "frequency": {
                    "type": "string",
                    "enum": list(VALID_FREQUENCIES),
                    "description": "Optional frequency aggregation (d, w, bw, m, q, sa, a).",
                },
                "aggregation_method": {
                    "type": "string",
                    "enum": list(VALID_AGG_METHODS),
                    "default": "avg",
                    "description": "Aggregation method when frequency is specified: avg, sum, or eop.",
                },
                "realtime_start": {
                    "type": "string",
                    "description": "Real-time period start date (YYYY-MM-DD).",
                },
                "realtime_end": {
                    "type": "string",
                    "description": "Real-time period end date (YYYY-MM-DD).",
                },
                "limit": {
                    "type": "integer",
                    "default": 240,
                    "description": "Maximum number of observations to return.",
                },
                "sort_order": {
                    "type": "string",
                    "enum": ["asc", "desc"],
                    "default": "asc",
                },
            },
            "required": ["series_id"],
        },
    },
    {
        "name": "fred-download-series-observations-link",
        "description": (
            "Generate direct download links (CSV, JSON, or XML) for a FRED series with optional "
            "date ranges, unit transformations, and frequency aggregation."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "series_id": {"type": "string"},
                "file_format": {
                    "type": "string",
                    "enum": ["csv", "json", "xml"],
                    "default": "csv",
                },
                "observation_start": {"type": "string"},
                "observation_end": {"type": "string"},
                "units": {
                    "type": "string",
                    "enum": list(VALID_UNITS),
                    "default": "lin",
                },
                "frequency": {
                    "type": "string",
                    "enum": list(VALID_FREQUENCIES),
                },
                "aggregation_method": {
                    "type": "string",
                    "enum": list(VALID_AGG_METHODS),
                    "default": "avg",
                },
            },
            "required": ["series_id"],
        },
    },
    {
        "name": "fred-graph-series",
        "description": (
            "Generate an interactive FRED graph URL and chart configuration for up to 5 FRED series, "
            "supporting unit transformations, frequency aggregation, date ranges, and left/right Y axes."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "series": {
                    "type": "array",
                    "description": "List of up to 5 series IDs or objects with series_id, units, frequency, axis.",
                    "items": {
                        "oneOf": [
                            {"type": "string"},
                            {
                                "type": "object",
                                "properties": {
                                    "series_id": {"type": "string"},
                                    "units": {"type": "string", "enum": list(VALID_UNITS)},
                                    "frequency": {"type": "string", "enum": list(VALID_FREQUENCIES)},
                                    "axis": {"type": "string", "enum": ["left", "right"]},
                                },
                                "required": ["series_id"],
                            },
                        ]
                    },
                },
                "observation_start": {"type": "string"},
                "observation_end": {"type": "string"},
                "title": {"type": "string"},
            },
            "required": ["series"],
        },
    },
]


def dispatch_tool_call(name: str, arguments: dict[str, Any] | None) -> dict[str, Any]:
    """Execute one of the 5 FRED MCP tools and return its structured dictionary result."""
    args = arguments or {}
    if name == "fred-search-series":
        return fred_search_series(
            args.get("search_text", ""),
            search_type=args.get("search_type", "full_text"),
            limit=args.get("limit", 15),
            order_by=args.get("order_by", "search_rank"),
            sort_order=args.get("sort_order", "desc"),
            tag_names=args.get("tag_names"),
            filter_variable=args.get("filter_variable"),
            filter_value=args.get("filter_value"),
        )
    if name == "fred-get-series-metadata":
        return fred_get_series_metadata(
            args.get("series_id", ""),
            include_release=bool(args.get("include_release", True)),
            include_tags=bool(args.get("include_tags", False)),
        )
    if name == "fred-get-series-observations":
        return fred_get_series_observations(
            args.get("series_id", ""),
            observation_start=args.get("observation_start"),
            observation_end=args.get("observation_end"),
            units=args.get("units", "lin"),
            frequency=args.get("frequency"),
            aggregation_method=args.get("aggregation_method", "avg"),
            realtime_start=args.get("realtime_start"),
            realtime_end=args.get("realtime_end"),
            limit=args.get("limit", 240),
            sort_order=args.get("sort_order", "asc"),
        )
    if name == "fred-download-series-observations-link":
        return fred_download_series_observations_link(
            args.get("series_id", ""),
            file_format=args.get("file_format", "csv"),
            observation_start=args.get("observation_start"),
            observation_end=args.get("observation_end"),
            units=args.get("units", "lin"),
            frequency=args.get("frequency"),
            aggregation_method=args.get("aggregation_method", "avg"),
        )
    if name == "fred-graph-series":
        return fred_graph_series(
            args.get("series", []),
            observation_start=args.get("observation_start"),
            observation_end=args.get("observation_end"),
            title=args.get("title"),
        )
    raise ValueError(f"Unknown FRED MCP tool: {name}")


def handle_jsonrpc_message(message: dict[str, Any]) -> dict[str, Any] | None:
    """Process a single MCP JSON-RPC 2.0 request/notification and return a response dict (or None)."""
    method = message.get("method", "")
    msg_id = message.get("id")
    params = message.get("params") or {}

    if method.startswith("notifications/"):
        return None

    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": msg_id,
            "result": {
                "protocolVersion": params.get("protocolVersion") or PROTOCOL_VERSION,
                "capabilities": {"tools": {"listChanged": False}},
                "serverInfo": {
                    "name": "fred-mcp-connector",
                    "version": "1.0.0",
                },
            },
        }

    if method == "ping":
        return {"jsonrpc": "2.0", "id": msg_id, "result": {}}

    if method == "tools/list":
        return {
            "jsonrpc": "2.0",
            "id": msg_id,
            "result": {"tools": MCP_TOOLS},
        }

    if method == "tools/call":
        tool_name = params.get("name", "")
        tool_args = params.get("arguments") or {}
        try:
            data = dispatch_tool_call(tool_name, tool_args)
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {
                    "content": [
                        {
                            "type": "text",
                            "text": json.dumps(data, indent=2, ensure_ascii=False),
                        }
                    ],
                    "isError": False,
                },
            }
        except Exception as exc:
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {
                    "content": [
                        {
                            "type": "text",
                            "text": json.dumps(
                                {"error": _redact_secrets(str(exc)), "tool": tool_name},
                                indent=2,
                                ensure_ascii=False,
                            ),
                        }
                    ],
                    "isError": True,
                },
            }

    return {
        "jsonrpc": "2.0",
        "id": msg_id,
        "error": {
            "code": -32601,
            "message": f"Method not found: {method}",
        },
    }


def serve_stdio() -> None:
    """Run the MCP server loop over stdin/stdout."""
    for raw_line in sys.stdin:
        line = raw_line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except json.JSONDecodeError as exc:
            err_resp = {
                "jsonrpc": "2.0",
                "id": None,
                "error": {"code": -32700, "message": f"Parse error: {exc}"},
            }
            sys.stdout.write(json.dumps(err_resp) + "\n")
            sys.stdout.flush()
            continue

        resp = handle_jsonrpc_message(msg)
        if resp is not None:
            sys.stdout.write(json.dumps(resp, ensure_ascii=False) + "\n")
            sys.stdout.flush()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="FRED MCP Server & CLI Connector")
    parser.add_argument(
        "--cli",
        choices=["search", "metadata", "observations", "download-link", "graph", "tools"],
        help="Run a FRED MCP tool directly from the CLI instead of starting stdio MCP mode.",
    )
    parser.add_argument("target", nargs="*", help="Query string or series ID(s)")
    parser.add_argument("--start", dest="observation_start", help="Observation start YYYY-MM-DD")
    parser.add_argument("--end", dest="observation_end", help="Observation end YYYY-MM-DD")
    parser.add_argument("--units", default="lin", help="FRED units transformation (default: lin)")
    parser.add_argument("--frequency", help="FRED frequency aggregation (d, w, bw, m, q, sa, a)")
    parser.add_argument("--limit", type=int, default=15, help="Max results / observations")
    args = parser.parse_args(argv)

    if not args.cli:
        serve_stdio()
        return 0

    if args.cli == "tools":
        print(json.dumps(MCP_TOOLS, indent=2, ensure_ascii=False))
        return 0

    if args.cli == "search":
        query = " ".join(args.target).strip()
        res = fred_search_series(query, limit=args.limit)
        print(json.dumps(res, indent=2, ensure_ascii=False))
        return 0

    if args.cli == "metadata":
        if not args.target:
            parser.error("series_id is required for --cli metadata")
        res = fred_get_series_metadata(args.target[0], include_release=True, include_tags=True)
        print(json.dumps(res, indent=2, ensure_ascii=False))
        return 0

    if args.cli == "observations":
        if not args.target:
            parser.error("series_id is required for --cli observations")
        res = fred_get_series_observations(
            args.target[0],
            observation_start=args.observation_start,
            observation_end=args.observation_end,
            units=args.units,
            frequency=args.frequency,
            limit=args.limit,
        )
        print(json.dumps(res, indent=2, ensure_ascii=False))
        return 0

    if args.cli == "download-link":
        if not args.target:
            parser.error("series_id is required for --cli download-link")
        res = fred_download_series_observations_link(
            args.target[0],
            observation_start=args.observation_start,
            observation_end=args.observation_end,
            units=args.units,
            frequency=args.frequency,
        )
        print(json.dumps(res, indent=2, ensure_ascii=False))
        return 0

    if args.cli == "graph":
        if not args.target:
            parser.error("At least one series_id is required for --cli graph")
        res = fred_graph_series(
            args.target,
            observation_start=args.observation_start,
            observation_end=args.observation_end,
        )
        print(json.dumps(res, indent=2, ensure_ascii=False))
        return 0

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
