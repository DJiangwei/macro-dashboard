---
name: fred-mcp
description: Query Federal Reserve Economic Data (FRED) using the 5 official St. Louis Fed FRED MCP Connector tools (fred-search-series, fred-get-series-metadata, fred-get-series-observations, fred-download-series-observations-link, fred-graph-series). Use when discovering US or global macro series on FRED, inspecting release/update metadata, pulling transformed or frequency-aggregated observations, or generating FRED download/chart links.
---

# FRED MCP Connector Skill

This skill integrates the St. Louis Fed's official **FRED MCP Connector** workflow ([documentation](https://fredhelp.stlouisfed.org/fred/data/ai/fred-mcp-connector/)) into the Country Primer workspace.

## Architecture: Remote OAuth vs. Local API-Key MCP Server

1. **Remote Hosted FRED MCP (`https://mcp.stlouisfed.org`)**:
   - Uses Streamable HTTP (`POST https://mcp.stlouisfed.org`) protected by OAuth 2.1 (`https://mcp.stlouisfed.org/.well-known/oauth-protected-resource`) and an interactive Okta browser login (separate from standard FRED API accounts).
   - Suitable for interactive desktop/web clients that support browser OAuth 2.1 dynamic client registration.

2. **Repo-Native FRED MCP Server (`scripts/fred_mcp_server.py`)**:
   - Implements the exact same 5 official FRED MCP tools over JSON-RPC 2.0 Stdio AND a direct CLI mode (`--cli`), reading `FRED_API_KEY` from `.env.local` (or falling back to `fredgraph.csv` for level series).
   - Never prints or logs `FRED_API_KEY`.

## Available Tools (5 Official Tools)

1. **`fred-search-series`**:
   - Search FRED by keywords/concepts (`search_text`), `search_type` (`full_text` or `series_id`), `tag_names`, `filter_variable`, `order_by`, and `limit`.
   - CLI:
     ```bash
     .venv/bin/python scripts/fred_mcp_server.py --cli search "real broad dollar index" --limit 10
     ```

2. **`fred-get-series-metadata`**:
   - Retrieve units, frequency, seasonal adjustment, `observation_start`, `observation_end`, `last_updated`, official release metadata (`include_release=true`), and tags (`include_tags=true`).
   - CLI:
     ```bash
     .venv/bin/python scripts/fred_mcp_server.py --cli metadata RTWEXBGS
     ```

3. **`fred-get-series-observations`**:
   - Fetch observations with optional date range (`--start`, `--end`), server-side unit transformations (`--units`: `lin`, `chg`, `ch1`, `pch`, `pc1`, `pca`, `cch`, `cca`, `log`), and frequency aggregation (`--frequency`: `d`, `w`, `bw`, `m`, `q`, `sa`, `a`).
   - CLI:
     ```bash
     .venv/bin/python scripts/fred_mcp_server.py --cli observations RTWEXBGS --start 2024-01-01 --units lin
     ```

4. **`fred-download-series-observations-link`**:
   - Generate direct public CSV (`fredgraph.csv`) and API download URL templates for a series with optional transformations and frequency aggregation.
   - CLI:
     ```bash
     .venv/bin/python scripts/fred_mcp_server.py --cli download-link RTWEXBGS --start 2020-01-01
     ```

5. **`fred-graph-series`**:
   - Generate an interactive FRED graph URL and CSV bundle URL for up to 5 series.
   - CLI:
     ```bash
     .venv/bin/python scripts/fred_mcp_server.py --cli graph RTWEXBGS DTWEXBGS --start 2020-01-01
     ```
