# Source Discovery Matrix

Date: 2026-05-20

Purpose: track remaining transparent proxies and decide which indicators should become official adapters, curated manual series, public-market derived series, or intentionally retained low-confidence proxies.

Use this file together with:

```bash
make proxy-report
```

## Current Baseline

Latest baseline after commit `611e590`:

| Country | Proxy count |
|---|---:|
| Hungary | 26 |
| Poland | 26 |
| Czechia | 29 |
| Romania | 30 |

## Priority Matrix

| Indicator | Countries still proxied | Target source | Source class | Current status | Next action |
|---|---|---|---|---|---|
| `gross_ext_debt` | HU, PL, CZ, RO | ECB BPS, World Bank QEDS/WDI, IMF IFS/DataMapper | Official statistical | World Bank WDI/QEDS candidates did not cover CEE-4 in first test | Revisit ECB BPS series-code construction; if still brittle, search IMF IFS mirrors. |
| `gas_storage_level` | HU, PL, CZ, RO | GIE AGSI, ENTSOG, national energy operators | Official/industry API | GIE AGSI identified; API likely requires registration/API key | Test AGSI only if an API key is available; otherwise use national operator data or curated manual series. |
| `foreign_ownership_bonds` | HU, PL, CZ, RO | National debt offices, ministries of finance, central banks | National official | Open | Implement national-source adapter if stable CSV/PDF/table endpoints exist. |
| `fx_loan_share` | HU, PL, CZ, RO | National central banks, ECB BSI/CBD | National official | Open | Start with central bank financial stability/statistics pages. |
| `avg_debt_maturity` | HU only | Hungary debt office / AKK | National official | Open | Eurostat has no HU observations in current query; find AKK time series or use curated manual annual series. |
| `cb_balance_sheet_gdp` | RO only | NBR, IMF IFS, central bank balance-sheet statements | National official | Open | Search NBR balance sheet statistics or IMF IFS mirror. |
| `foreign_bank_share` | RO only | NBR, EBRD, ECB consolidated banking statistics | Official/manual | Open | World Bank GFDD lacks Romania coverage; search NBR/EBRD. |
| `short_term_ext_debt` | CZ only | IMF ARA, World Bank QEDS/WDI, national external debt stats | Official statistical | Open | Current IMF ARA adapter did not replace CZ; test alternate series or national external debt table. |
| `import_prices_yoy` | HU, PL, CZ, RO | Eurostat STS, national statistical offices | Official statistical | Blocked once | Prior Eurostat query returned poor CEE coverage; re-test dimensions and national stats. |
| `equity_index` | CZ, RO | Local exchanges, Yahoo alternatives, exchange CSVs | Public market | Open | Test Prague Stock Exchange and Bucharest Stock Exchange data pages before more Yahoo symbol guessing. |
| `equity_yoy` | CZ, RO | Derived from `equity_index` | Derived market | Dependent | Implement after index-level feed is stable. |
| `equity_vol_30d` | PL, CZ, RO | Derived from daily index close | Derived market | Partially dependent | Fix symbol/feed coverage first; keep vendor warning. |
| `sovereign_rating` | HU, PL, CZ, RO | Rating agency releases, Trading Economics-style pages if acceptable | Curated manual | Recommended manual | Add to `config/manual_indicators.yaml` with notch scale and references. |
| `edp_status` | HU, PL, CZ, RO | European Commission/Council EDP pages | Curated manual | Recommended manual | Add numeric policy-state series with references and review dates. |
| `eu_funds_absorption` | HU, PL, CZ, RO | EC cohesion/RRF programme dashboards | Curated manual | Recommended manual | Track programme-cycle absorption as manual or semi-manual. |
| `contingent_liabilities` | None after current adapter | Eurostat `gov_cl_guar` | Official statistical | Wired in current worktree | Uses total stock of general-government guarantees, % GDP; narrower than full contingent liabilities. |
| `cb_forward_guidance` | HU, PL, CZ, RO | Central bank statements/minutes | Curated manual | Recommended manual | Better as qualitative score with event references. |
| `manufacturing_pmi` | HU, PL, CZ, RO | S&P/HCOB, local PMI releases | Vendor/survey | Hard | Keep proxy unless stable public historical data exists. |
| `oecd_cli` | HU, PL, CZ, RO | OECD SDMX | Blocked | Low priority | Prior OECD CLI query did not cover CEE-4; consider replacing with EC ESI or Germany Ifo spillover. |
| `ifo_expectations` | HU, PL, CZ, RO | Ifo Germany/Eurozone | Spillover survey | Reframe | If retained, label as Germany/Eurozone demand-spillover proxy, not domestic indicator. |
| `truck_km_index` | HU, PL, CZ, RO | Toll-road operators, logistics platforms | Alternative data | Hard | Low priority; keep proxy or remove from core. |
| `cds_5y` | HU, PL, CZ, RO | Paid market vendors | Vendor market | Hard | Keep proxy or replace with sovereign spread when vendor unavailable. |
| `embi_spread` | HU, PL, CZ, RO | JP Morgan/vendor | Vendor market | Hard | Keep proxy; open substitute is sovereign spread vs Bund. |
| `breakeven_5y5y` | HU, PL, CZ, RO | Inflation-linked bond curves/vendor | Vendor market | Hard | Keep proxy unless national linker curves are publicly available. |
| `fx_implied_vol` | HU, PL, CZ, RO | FX options vendors | Vendor market | Hard | Keep proxy; public source unlikely. |
| `fx_3m_forward` | HU, PL, CZ, RO | FX forwards/vendor; derived covered-interest proxy | Vendor/derived | Medium | Could derive synthetic forward points from spot and interest differentials, but label clearly. |
| `equity_fwd_pe` | HU, PL, CZ, RO | FactSet/Bloomberg/MSCI/vendor | Vendor valuation | Hard | Keep proxy or remove from core if no vendor access. |
| `equity_pb` | HU, PL, CZ, RO | Exchange factsheets/vendor | Vendor valuation | Hard | Keep proxy or curate annual factsheets. |
| `equity_div_yield` | HU, PL, CZ, RO | Exchange factsheets/vendor | Vendor valuation | Hard | Keep proxy or curate annual factsheets. |
| `portfolio_flows` | HU, PL, CZ, RO | IMF BOP/IIP, IMF Capital Flows, ECB BOP | Official/lagged | Partially blocked | IMF capital-flow series tested but stops around 2014; try ECB BOP financial account. |
| `administered_prices` | HU, PL, CZ, RO | Eurostat HICP administered prices if accessible | Official statistical | Open | Dataset name `prc_hicp_ap` returned no useful dimensions in first test; search Eurostat metadata. |
| `carry_trade_return` | HU, PL, CZ, RO | Derived FX spot plus rate differential | Derived market | Open | Existing adapter needs EUR short-rate source; consider ECB ESTER or Euribor series. |

## Candidate First Sprint

The next implementation sprint should target:

1. `gross_ext_debt`
2. `gas_storage_level`
3. `foreign_ownership_bonds`

Reason:

- They are important macro risk indicators.
- They are more likely to have official or semi-official sources than valuation/vendor metrics.
- They reduce proxy dependence without changing dashboard design.

## Validation Rules

Before wiring any source:

1. Confirm all covered countries.
2. Confirm latest observation date.
3. Confirm frequency and units.
4. Confirm the indicator definition matches the chart label.
5. Confirm missing-country fallback remains transparent.
6. Confirm output footnote states whether the series is official, derived, manual, vendor, or proxy.

## Update Log

| Date | Change | Result |
|---|---|---|
| 2026-05-20 | Created matrix after `611e590` | Baseline proxy counts: HU 26, PL 26, CZ 29, RO 30. |
| 2026-05-20 | Tested World Bank external-debt candidates | `DT.DOD.DECT.GN.ZS`, `DT.DOD.DECT.CD`, and `DT.DOD.DSTC.IR.ZS` did not provide usable CEE-4 coverage through current World Bank adapter. |
| 2026-05-20 | Investigated GIE AGSI | AGSI is the right source family for storage fullness, but public wrappers/documentation indicate API-key registration is likely required. |
| 2026-05-20 | Wired Eurostat `gov_cl_guar` | `contingent_liabilities` now uses total stock of general-government guarantees, % GDP, for HU/PL/CZ/RO. |
