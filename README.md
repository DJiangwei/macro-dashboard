# Country Primer

Generates a buy-side macro dashboard for any country as a single self-contained
HTML file. Built on top of the `openecon-data` MCP (FRED · Eurostat · IMF · BIS ·
World Bank · OECD), with ECB XML fallback for EUR-cross FX.

## Framework

Synthesis of three sources, mapped to one 7-section dashboard:

| Source | Contribution |
|---|---|
| **IMF Financial Programming & Policies** | The 4-account macro identity (Real / External / Fiscal / Monetary). Stock-flow consistency. |
| **Goldman Sachs "Understanding Economic Indicators"** | Lead/coincident/lag tagging, source attribution discipline, financial-conditions overlay. |
| **Buy-side PM lens** | Asset-side mirror: yield curve, sov spread, FX vs peers, regime classification. |

### 7 sections

1. **§1 Country Snapshot** — population, ratings, FX regime, central bank, partners.
2. **§2 Real Activity** — GDP, IP, retail sales, unemployment.
3. **§3 Prices & Wages** — CPI (with target band), core CPI, PPI, wages.
4. **§4 External Sector** — current account, trade, FX reserves, REER.
5. **§5 Fiscal & Sovereign** — gen-gov balance, debt/GDP, 10y yield.
6. **§6 Monetary & Financial** — policy rate, M3, private credit, EUR-cross.
7. **§7 Markets & Valuation** — equity index level + YoY.

Each chart shows a footer line: `Source: <provider> · Series: <id> · Updated <date> · Fetched <date>`.

## Quick start

This repo is pinned to Python 3.12 and uses `uv` as the preferred environment
manager so any coding agent can reproduce the same setup without relying on a
global Python install.

```bash
cd /Users/jiangwei/Claude/Country_Primer
scripts/uv_project.sh sync
make doctor
make build-v4
make validate
```

If an agent cannot use `uv`, fall back to:

```bash
python3.12 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
python scripts/doctor_env.py
```

```bash
cd /Users/jiangwei/Claude/Country_Primer
pip install -r requirements.txt
python -m country_primer HU --peers PL,CZ,RO --out output/hungary_2026Q2.html
open output/hungary_2026Q2.html
```

CLI flags:

- `country` (positional, ISO2) — e.g. `HU`
- `--peers PL,CZ,RO` — comma-separated peer ISO2s for overlay charts; defaults to country's `default_peers` from `config/countries.yaml`
- `--out path.html` — output path (defaults to `output/<iso>.html`)

## Data flow

```
[MCP openecon-data] ──► cache/<sha>.json ──┐
                                            ├──► fetch.py → Series ──► transform.py → charts.py → render.py → HTML
[ECB XML / WB API ] ────────────────────────┘
```

The MCP runs inside Claude Code (it is not a Python package), so `fetch.py`
reads previously-cached MCP responses from `cache/`. To refresh data for a new
country or a new run, ask Claude Code to "prefetch country X" — it will call
the MCP for every indicator in `config/indicators.yaml` and persist the
responses. The `fx_vs_eur` indicator is the exception: it uses the ECB XML
feed via `fetch.fetch_ecb_fx`, which works without prefetching.

## v4 data-pipeline architecture

The v4 dashboard also includes a dedicated canonical pipeline in
`src/country_primer/data_fetcher.py`. It follows the proposed architecture:

```
[EurostatFetcher / ECBFetcher / BISFetcher / NationalCBFetcher]
                         │
                         ▼
canonical macro table: [country, date, indicator_id, value]
                         │
                         ▼
build_v4.py → 114-indicator dashboard pages
```

The canonical manifest currently defines 114 core indicators across real
activity, prices/wages, external, fiscal/sovereign, monetary/financial,
markets/valuation, financial stability, demographics, and political economy.
The editable source of truth is `config/indicator_manifest_48.yaml`; the Python
module loads that file and only uses its embedded manifest as a fallback.
When a primary adapter is not yet wired, the pipeline emits a transparent proxy
series and marks it in the UI with quality footnotes. This keeps every country
page structurally complete while making uncertain data visible rather than
silently hiding it.

`make build-v4` also builds the China, UK, and US data-first pages from
`config/china_indicators.yaml`, `config/uk_indicators.yaml`, and
`config/us_indicators.yaml` via their dedicated scripts, then updates
`output/index.html` so the archive page stays synchronized.

To rebuild and publish the site:

```bash
make publish MSG="Update dashboard"
```

### Optional Data Credentials

Some public-interest sources require user credentials or an account-specific
download URL before they can be refreshed unattended. Copy `.env.example` to
`.env` locally and export the variables before running `make build-v4`.

```bash
set -a
. ./.env
set +a
make build-v4
```

Supported optional sources:

| Variable | Purpose |
|---|---|
| `FRED_API_KEY` | Enables the official FRED API for the UK and US pages. If unset, their scripts fall back to FRED's public graph CSV endpoint. For the US page, set this key for complete regular refreshes; the generator refuses to overwrite output if the fallback returns fewer than 55 charts. |
| `GIE_AGSI_API_KEY` | Enables GIE AGSI+ country-level gas-storage fill data for `gas_storage_level`. |
| `GIE_AGSI_BASE_URL` | Optional override for the AGSI+ API base URL. Defaults to `https://agsi.gie.eu/api`. |
| `STOOQ_API_KEY` | Enables the default Stooq CSV URL template if it works for the user's Stooq account. |
| `STOOQ_WIG20_CSV_URL` | Exact Stooq CSV download URL for Poland WIG20 daily closes. |
| `STOOQ_BET_CSV_URL` | Exact Stooq CSV download URL for Romania BET daily closes. |

If these variables are missing or a source rejects automated access, the
dashboard keeps the existing transparent proxy and marks it in the UI. This is
intentional: a failed credentialed source should not silently become fake data.

To review the remaining transparent proxies and decide whether to keep, replace,
reframe, manually maintain, or remove them:

```bash
make proxy-report
open PROXY_REVIEW.md
```

## Adding a country

1. Add it to `config/countries.yaml` with name, ISO codes, currency, central
   bank, FX regime, sovereign ratings, equity index, default peers.
2. Ask Claude Code to prefetch the new country's indicators (the catalog uses
   `{country}` / `{currency}` / `{equity_index}` placeholders and runs the same
   set of queries automatically).
3. Run `python -m country_primer <ISO2>`.

## Adding an indicator

1. Add an entry to the relevant section in `config/indicators.yaml`:
   ```yaml
   - key: my_indicator
     label: "Display label, unit"
     mcp_query: "{country} <natural-language query>"
     chart: line  # or bar / peer_overlay
     peers: false  # set true for cross-country overlay
     derived_yoy: false  # set true if MCP returns level → render YoY
   ```
2. Prefetch via Claude Code, then re-run the CLI.
3. Optionally extend the section's commentary template in `commentary.py`.

## Project layout

```
Country_Primer/
├── config/
│   ├── indicators.yaml      # 7-section catalog (single source of truth)
│   ├── indicator_manifest_48.yaml # v4 canonical manifest, now 114 indicators
│   ├── countries.yaml       # country metadata + peer sets
│   └── chart_templates.yaml # Plotly defaults
├── src/country_primer/
│   ├── fetch.py             # cache reader + ECB XML / World Bank fallbacks
│   ├── catalog.py           # YAML loader + placeholder resolution
│   ├── transform.py         # YoY / latest-print
│   ├── charts.py            # Plotly factory (line, bar, peer_overlay)
│   ├── commentary.py        # deterministic per-section macro commentary
│   ├── render.py            # Jinja2 → standalone HTML
│   └── cli.py               # CLI entry point
├── templates/
│   └── dashboard.html.j2
├── pyproject.toml          # pinned Python/dependency contract
├── .python-version         # Python 3.12 for pyenv/asdf/uv-aware agents
├── Makefile                # standard setup/build/validate commands
├── scripts/
│   ├── doctor_env.py       # environment self-check
│   ├── build_china_dashboard.py # China chart/data page from public APIs
│   ├── publish_dashboard.sh # one-command build/validate/commit/push/check
│   └── uv_project.sh       # uv wrapper that keeps cache/python inside repo
├── AGENTS.md               # operating guide for coding agents
├── cache/                   # raw MCP responses (offline-replay)
└── output/                  # generated HTML reports
```

## Coverage (v1, Hungary baseline: 19/21 charts populated)

Multi-tier fallback chain — for each indicator we try the MCP cache first,
then a per-indicator direct API fallback registered in `cli.FALLBACKS`,
then a generic FX fallback for `fx_*` keys via ECB XML:

| Section | Indicator | Source (active) | Frequency | Latest |
|---|---|---|---|---|
| Real Activity | Real GDP YoY | Eurostat tec00115 | annual | 2025 |
|  | Industrial production YoY | Eurostat sts_inpr_m (I21 → derived) | monthly | Feb 2026 |
|  | Retail sales YoY | Eurostat sts_trtu_m (I21 → derived) | monthly | Feb 2026 |
|  | Unemployment | Eurostat ei_lmhr_m | monthly | Feb 2026 |
| Prices & Wages | Headline CPI YoY | Eurostat prc_hicp_manr | monthly | Dec 2025 |
|  | Core CPI YoY | BIS WS_LONG_CPI | monthly | Feb 2026 |
|  | PPI YoY | Eurostat sts_inppd_m (I21 → derived) | monthly | Feb 2026 |
|  | Wage growth | Eurostat lc_lci_r2_q | quarterly | Q4 2025 |
| External | Current account % GDP | IMF WEO BCA_NGDPD | annual | 2025 |
|  | Trade balance | — | — | **gap** |
|  | FX reserves | World Bank FI.RES.TOTL.CD | annual | 2024 |
|  | REER | BIS WS_EER | monthly | Mar 2026 |
| Fiscal & Sovereign | Gen-gov balance % GDP | IMF WEO GGXCNL_NGDP | annual | 2025 |
|  | Gross debt % GDP | Eurostat teina225 | annual | 2025 |
|  | 10y sovereign yield | Eurostat irt_lt_mcby_m | monthly | Mar 2026 |
| Monetary & Financial | Policy rate | BIS WS_CBPOL | monthly | Mar 2026 |
|  | M3 broad money | — | — | **gap** |
|  | Private credit % GDP | Eurostat tipsbp10 | annual | 2025 |
|  | EUR cross | ECB XML eurofxref | daily | live |
| Markets & Valuation | Equity index level | Yahoo Finance (OTP.BD as BUX proxy) | monthly | Apr 2026 |
|  | Equity YoY | Yahoo Finance (derived) | monthly | Apr 2026 |

### Visualisation conventions

- **Unified x-axis range**: all monthly/daily charts share a 5-year window
  ending today; annual charts share a 12-year window. Latest dates align
  visually across panels.
- **Latest-print marker**: every chart highlights the most recent data point
  with a coloured dot + bold value annotation (date in caption).
- **Source footer**: each chart shows
  `Source · Series · Updated · Fetched` so any number can be traced back to
  its source URL (printed in chart attribution).
- **Fixed chart height (420 px)** with a unified card border — eliminates
  the ragged-grid look the v1 had.

### Known gaps

- **Trade balance** — Eurostat `bop_eu6_m` exceeds free 5M-row extraction
  cap; needs API key or pre-aggregated dataset. Workaround: derive from
  current account.
- **M3 broad money** — no free monthly EM-CEE source via MCP or open
  Eurostat dataset. Could pull from MNB statistics page (HU) or BIS
  WS_LBS_D_PUB (cross-border).

## License & disclaimer

Personal research tool. Not investment advice.
