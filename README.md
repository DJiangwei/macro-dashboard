# Country Primer

Generates a buy-side macro dashboard for any country as a single self-contained
HTML file. Built on top of the `openecon-data` MCP (FRED · EIA · Eurostat · IMF · BIS ·
World Bank · OECD), with ECB XML fallback for EUR-cross FX.

## Framework

Framework v2 combines three research lenses with a shared nine-pillar,
48-concept ontology in `config/framework_v2.yaml`:

| Source | Contribution |
|---|---|
| **IMF Financial Programming & Policies** | The 4-account macro identity (Real / External / Fiscal / Monetary). Stock-flow consistency. |
| **Goldman Sachs "Understanding Economic Indicators"** | Lead/coincident/lag tagging, source attribution discipline, financial-conditions overlay. |
| **Buy-side PM lens** | Asset-side mirror: yield curve, sov spread, FX vs peers, regime classification. |

The comparable core covers growth/demand, production/cycle, labour/income,
prices/costs, housing/investment, external/FX, fiscal/sovereign,
monetary/financial conditions, and stability/structural risk. Country pages
default to the Core 48 view; the All deep-dive charts control reveals
country-specific extensions without discarding them.

Each chart shows a footer line: `Source: <provider> · Series: <id> · Updated <date> · Fetched <date>`.

## Quick start

This repo is pinned to Python 3.12 and uses `uv` as the preferred environment
manager so any coding agent can reproduce the same setup without relying on a
global Python install.

```bash
cd /Users/jiangwei/Claude/Country_Primer
scripts/uv_project.sh sync
make doctor
make refresh-data
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
python -m country_primer HU --peers PL,CZ,RO --out output/hungary.html
open output/hungary.html
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
canonical macro table: observations + source, concept, quality, and projection metadata
                         │
                         ▼
build_v4.py → stable country pages + latest snapshot + compact historical snapshot
```

The CEE manifest currently defines 114 country indicators across real
activity, prices/wages, external, fiscal/sovereign, monetary/financial,
markets/valuation, financial stability, demographics, and political economy.
The editable source of truth is `config/indicator_manifest_48.yaml`; shared
economic concepts and compatibility aliases live in `config/framework_v2.yaml`.
When no validated public series exists, the public page omits that chart and
records the gap instead of emitting a proxy.

`make build-v4` also builds the China, UK, and US data-first pages from
`config/china_indicators.yaml`, `config/uk_indicators.yaml`, and
`config/us_indicators.yaml` via their dedicated scripts, then updates
`output/index.html` so the archive page stays synchronized. Public country
routes are stable (`output/hungary.html` through `output/us.html`) and do not
encode a quarter or generator version.

The same build now refreshes the machine-readable workbench layer used by the
home/archive pages:

- `output/cee_build_snapshot.json` stores the latest CEE indicator rows from the
  same fetch used to render country pages. Archive cards and consistency checks
  consume this snapshot rather than refetching live values.
- `output/cee_canonical_frame.json` stores the full CEE chart history in compact
  `cee-canonical-v2` form. Together with the three data-first canonical files,
  it lets `make rebuild-ui` regenerate all seven pages without network access.
- `output/*_canonical_frame.json` uses `data-first-canonical-v2` for China, UK,
  and US: metadata is stored once per series and observations are compact
  `[date, value]` pairs.
- `output/macro_workbench_summary.json` aggregates country cards, regime
  signals, cross-country heatmap values, data-gap priorities, and phase
  coverage in one JSON artifact for future agents or front-end views.
- `output/release_monitor.json`, `output/what_changed.json`, and
  `output/data_gap_backlog.json` expose freshness, release attention, and
  remaining official-data gaps without scraping HTML.
- `output/dashboard_archive_summary.json` links the archive cards back to the
  workbench so `index.html` and `output/index.html` stay data-synchronized.
- `output/source_health.json` records source-level calls, empty responses,
  structured failure reasons, and circuit-breaker state for the latest live
  refresh. Temporary failures retain the last-known-good canonical series with
  an explicit `refresh_fallback/watch` marker instead of silently deleting a
  chart.
- `output/core_coverage_matrix.json` and `CORE_COVERAGE_MATRIX.md` report the
  seven-country by 48-concept comparable-core matrix and rank gaps by explicit
  macro-value weights rather than raw chart count.

The build commands deliberately separate data acquisition from presentation:

```bash
make refresh-check  # seven lightweight live-vs-snapshot headline probes
make refresh-data   # networked full refresh and snapshot update
make rebuild-ui     # no data-source calls; render only from snapshots
make validate       # deterministic, offline contracts and tests
```

`make build-v4` remains a backward-compatible alias for `make refresh-data`.
Official release cadence overrides live in `config/release_calendars.yaml`.

The China page uses AKShare for a China-native high-frequency layer including
CPI/PPI headline and momentum, urban/rural CPI, enterprise-goods prices,
agricultural/commodity/energy price indexes, PMI, industrial value added,
logistics prosperity, civil-aviation load factors, fixed-asset investment,
retail sales, consumer confidence, customs trade values/growth/balance, money
supply, new RMB loans, TSF flow, LPR, RRR, SHIBOR, A-share market capitalization,
turnover, margin balances, electricity consumption, selected Beijing/Shanghai
housing-price samples, reserves/gold, fiscal revenue execution, and tax
receipts. These charts are labelled as AKShare-wrapped
Eastmoney/Sina/PBC-style web data rather than official NBS/PBOC API contracts;
schema drift, upstream availability, and concept coverage should be checked
whenever China data is expanded.

The UK page prioritises native ONS, Bank of England, HMRC/GOV.UK, OBR, and
DESNZ endpoints for release-sensitive work. It now includes ONS/HMRC PAYE RTI
payrolled employees, pay, employee flows, and median pay growth; HMRC residential
and non-residential property transactions; ONS CPI/CPIH/RPI/PPI and household
energy components; BoE rates, sterling, money, and credit series; ONS public
sector borrowing, cash, debt, receipts, expenditure, tax, benefits, and OBR
forecast rows. Remaining UK gaps are mostly proprietary/vendor surveys such as
GS CAI/FCI, PMI, CBI/BCC/BRC/RICS, pay settlements, expectations surveys, and
deeper credit-condition or debt-instrument microdata.

To rebuild and publish the site:

```bash
make publish MSG="Update dashboard"
```

### Optional Data Credentials

Some public-interest sources require user credentials or an account-specific
download URL before they can be refreshed unattended. Copy `.env.example` to
`.env.local` locally; `scripts/uv_project.sh` loads it automatically before
running project commands. Never commit real keys.

```bash
set -a
. ./.env.local
set +a
make build-v4
```

Supported optional sources:

| Variable | Purpose |
|---|---|
| `FRED_API_KEY` | Enables the official FRED API for the US page and the remaining UK FRED/OECD/BIS/IMF mirror series. If unset, those scripts fall back to FRED's public graph CSV endpoint. UK release-sensitive series use native ONS/BoE endpoints where validated. For the US page, set this key for complete regular refreshes; the generator refuses to overwrite output if the fallback returns fewer than 55 charts. |
| `EIA_API_KEY` | Enables EIA Open Data API v2 fetches for future energy, oil, gas, and US energy macro adapters. The CE4 gas-storage path still prefers GIE/Eurostat where those sources are more country-specific. |
| `GIE_AGSI_API_KEY` | Enables GIE AGSI+ country-level gas-storage fill data for `gas_storage_level`. |
| `GIE_AGSI_BASE_URL` | Optional override for the AGSI+ API base URL. Defaults to `https://agsi.gie.eu/api`. |
| `STOOQ_API_KEY` | Enables the default Stooq CSV URL template if it works for the user's Stooq account. |
| `STOOQ_WIG20_CSV_URL` | Exact Stooq CSV download URL for Poland WIG20 daily closes. |
| `STOOQ_BET_CSV_URL` | Exact Stooq CSV download URL for Romania BET daily closes. |

If these variables are missing or a source rejects automated access, the
dashboard retains a previously validated canonical observation where one
exists and marks it `refresh_fallback/watch`; otherwise it marks the series
unavailable. It never creates a synthetic replacement merely to preserve a
chart count.

To review intentionally dropped historical proxy slots and source gaps:

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
│   ├── macro_workbench.py  # archive/workbench JSON + regime/heatmap layer
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
