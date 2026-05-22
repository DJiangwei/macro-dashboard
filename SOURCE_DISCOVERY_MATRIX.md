# Source Discovery Matrix

Date: 2026-05-21

Purpose: track remaining transparent proxies and decide which indicators should become official adapters, curated manual series, public-market derived series, or intentionally retained low-confidence proxies.

Use this file together with:

```bash
make proxy-report
```

## Current Baseline

Latest baseline after the 2026-05-22 source-wiring pass:

| Country | Proxy count |
|---|---:|
| Hungary | 15 |
| Poland | 15 |
| Czechia | 18 |
| Romania | 20 |

## Priority Matrix

| Indicator | Countries still proxied | Target source | Source class | Current status | Next action |
|---|---|---|---|---|---|
| `gross_ext_debt` | None | ECB BPS plus Eurostat GDP | Official statistical / derived ratio | Wired | Uses ECB balance-of-payments liability components scaled by Eurostat rolling four-quarter GDP; footnote flags direct-investment intercompany-debt caveat. |
| `gas_storage_level` | HU, PL, CZ, RO | GIE AGSI, ENTSOG, national energy operators | Official/industry API | GIE AGSI official API tested; direct country query rejects missing API key | Use AGSI after API-key setup; otherwise test national operator data or curated manual series. |
| `foreign_ownership_bonds` | None | Eurostat government debt by holder sector | Official statistical / derived ratio | Wired | Uses rest-of-world-held Maastricht debt divided by total holder-sector Maastricht debt; relabeled as total government debt share because the common CEE-4 Eurostat denominator is not local-bond-only. |
| `fx_loan_share` | HU, CZ | IMF FSI, national central banks | Official statistical / national official | Partially wired | IMF FSI `FSFC_PT` replaces proxies where recent quarterly coverage exists for PL and RO; HU is absent and CZ stops in 2014. CNB ARAD has relevant currency-split loan tables but its REST API requires a user API key. |
| `avg_debt_maturity` | None | Hungary debt office / AKK | National official snapshot | Wired | Hungary uses official AKK Average Time to Maturity snapshots in `config/manual_indicators.yaml`; other covered countries continue to use Eurostat remaining-maturity data. |
| `cb_balance_sheet_gdp` | RO only | NBR, IMF IFS, central bank balance-sheet statements | National official | Open | Search NBR balance sheet statistics or IMF IFS mirror. |
| `foreign_bank_share` | RO only | NBR, EBRD, ECB consolidated banking statistics | Official/manual | Open | World Bank GFDD lacks Romania coverage; search NBR/EBRD. |
| `short_term_ext_debt` | None | IMF ARA, CNB external debt and reserves | Official statistical / national official | Wired | Czechia uses CNB USD quarterly short-term external debt divided by matching CNB quarter-end international reserves because IMF ARA coverage is missing. |
| `import_prices_yoy` | RO | Eurostat STS, national statistical offices | Official statistical | Partially wired | Czechia uses CZSO open-data monthly total import-price YoY, Hungary uses KSH STADAT monthly external-trade total import-price YoY, and Poland uses GUS DBW variable 329 industrial-products-total import YoY. Eurostat `sts_inpi_m` has poor non-euro CEE coverage. |
| `equity_index` | CZ, RO | Local exchanges, Yahoo alternatives, exchange CSVs | Public market | PSE API discovered | Prague `/api/indexes` historical PX data works through direct API probing, but Python `requests` connection timed out on 2026-05-22; avoid adding a build-path dependency until access is robust. Continue with BVB and alternate exchange downloads. |
| `equity_yoy` | CZ, RO | Derived from `equity_index` | Derived market | Dependent | Implement after index-level feed is stable. |
| `equity_vol_30d` | PL, CZ, RO | Derived from daily index close | Derived market | Partially dependent | Fix symbol/feed coverage first; keep vendor warning. |
| `sovereign_rating` | None | Rating agency releases | Curated manual | Wired | Maintained in `config/manual_indicators.yaml` as a 21-notch average; update after S&P, Moody's, Fitch, or Scope actions. |
| `edp_status` | None | European Commission/Council EDP pages | Curated manual | Wired | Maintained in `config/manual_indicators.yaml` as a qualitative policy-risk score with event dates. |
| `eu_funds_absorption` | None | European Commission Cohesion Open Data | Official statistical / derived ratio | Wired | Uses 2021-2027 cumulative total net payments divided by latest adopted EU plan for CF, EMFAF, ERDF, ESF+, and JTF. |
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
| `portfolio_flows` | None | ECB BPS | Official statistical | Wired | Uses monthly portfolio-investment liabilities transactions vis-a-vis rest of world; positive readings are non-resident net liability incurrence. |
| `administered_prices` | None | Eurostat HICP item weights | Official statistical / derived | Wired | Uses the HICP `AP` special aggregate item weight from current ECOICOP v2 weights and converts per-mille weight to percent of basket; do not substitute AP inflation. |
| `carry_trade_return` | None | Eurostat 3M short-term rates | Derived market | Wired | Carry-only spread uses local 3M short rate less euro-area 3M short rate; it excludes spot FX movement, roll-down, and costs. |

## Candidate First Sprint

The next implementation sprint should target:

1. `gas_storage_level`
2. `fx_loan_share`
3. `cb_balance_sheet_gdp`

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
| 2026-05-21 | Wired curated `sovereign_rating` and `edp_status` | Removed both indicators from proxy inventory for HU/PL/CZ/RO; manual policy/rating series carry `watch` quality badges. |
| 2026-05-21 | Wired ECB BPS component adapter for `gross_ext_debt` | Removed `gross_ext_debt` from proxy inventory for HU/PL/CZ/RO; output is a component-based % GDP estimate with explicit caveat. |
| 2026-05-22 | Wired Cohesion Open Data payment adapter for `eu_funds_absorption` | Removed `eu_funds_absorption` from proxy inventory for HU/PL/CZ/RO; ratio uses official cumulative payments over latest adopted EU plan. |
| 2026-05-22 | Rechecked Eurostat HICP administered prices | AP inflation is directly available, but the dashboard slot is a basket share; derive it from administered composition and HICP weights instead of relabeling the metric. |
| 2026-05-22 | Wired Eurostat HICP item-weight adapter for `administered_prices` | Removed `administered_prices` from proxy inventory for HU/PL/CZ/RO via the official `AP` special aggregate weight in `prc_hicp_iw`. |
| 2026-05-22 | Corrected Eurostat carry short-rate legs | Removed `carry_trade_return` from proxy inventory for HU/PL/CZ/RO by using explicit local and euro-area 3M short-rate series. |
| 2026-05-22 | Wired AKK Hungary maturity snapshots | Removed `avg_debt_maturity` from Hungary proxy inventory with manually maintained official end-2024 and preliminary end-2025 Average Time to Maturity values. |
| 2026-05-22 | Wired Eurostat government-debt holder ratio for `foreign_ownership_bonds` | Removed the holder indicator from proxy inventory for HU/PL/CZ/RO and tightened the label from local bonds to total government debt to preserve the harmonized Eurostat definition. |
| 2026-05-22 | Wired IMF FSI `FSFC_PT` for recent `fx_loan_share` coverage | Removed `fx_loan_share` proxies for Poland and Romania; rejected missing Hungary and stale Czechia coverage so those two remain explicit source-discovery tasks. |
| 2026-05-22 | Wired ECB BPS portfolio-liability transactions for `portfolio_flows` | Removed `portfolio_flows` from proxy inventory for HU/PL/CZ/RO with monthly rest-of-world portfolio liability-flow series and explicit sign convention. |
| 2026-05-22 | Wired Czech CNB short-term external-debt ratio | Removed Czechia `short_term_ext_debt` proxy with quarterly CNB USD short-term external debt over matched CNB USD international reserves. |
