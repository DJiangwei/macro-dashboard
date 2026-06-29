# Proxy Indicator Review

Date: 2026-05-25

Purpose: decide which remaining proxy indicators should be kept, replaced, reframed, converted to manual maintenance, or removed from the dashboard. This file is the working decision layer above `SOURCE_DISCOVERY_MATRIX.md`.

Current public-dashboard proxy baseline after dropping the remaining proxy-only slots:

| Country | Proxy count | Total indicators | Share |
|---|---:|---:|---:|
| Hungary | 0 | 110 | 0.0% |
| Poland | 0 | 113 | 0.0% |
| Czechia | 0 | 109 | 0.0% |
| Romania | 0 | 109 | 0.0% |

Proxy union: 0 rendered indicators.

## Decision Categories

| Decision | Meaning | Dashboard treatment |
|---|---|---|
| Replace | Search for a reusable official, exchange, or public API source. | Keep chart for now with `low_confidence`, then wire adapter when found. |
| Reframe | Current label over-promises; keep the idea but rename or change the definition. | Update label, note, and source logic before treating as final. |
| Manual | Better maintained as a curated snapshot with dated source notes. | Move to `config/manual_indicators.yaml` if source cadence is low. |
| Keep | Public source is unlikely; retain as a clearly marked placeholder/proxy only if analytically useful. | Keep `low_confidence` and explicit footnotes. |
| Remove | Low signal or weak sourceability; better to reduce dashboard clutter. | Remove from chart sections after user approval. |

## Dropped From Public Dashboard

| Indicator | Countries dropped | Rationale | Future restore condition |
|---|---|---|---|
| `ara_metric` | CZ | IMF ARA coverage is unavailable for Czechia in the current public adapter, which otherwise fell back to transparent proxy data. | Restore only with a reusable IMF ARA, CNB, or manually validated reserve-adequacy source that is explicitly not a proxy fill. |
| `breakeven_5y5y` | HU, PL, CZ, RO | Inflation-swap/linker curve data is typically vendor-controlled; the public adapter fell back to proxy data. | Restore only with a reusable linker/swap curve source or a licensed vendor feed. |
| `equity_fwd_pe` | HU, CZ, RO | Forward earnings valuation is vendor/analyst-consensus based; public exchange coverage is uneven. | Restore with exchange factsheets, index provider aggregate P/E snapshots, or a licensed consensus feed. |
| `equity_pb` | HU, CZ, RO | P/B may appear in exchange/index factsheets, but no robust public adapter is wired for these countries. | Restore with exchange/index-provider aggregate P/B snapshots. |
| `equity_div_yield` | HU, CZ, RO | Dividend yield can be factsheet-based but is not reliably API-driven for all remaining countries. | Restore with exchange/index-provider aggregate dividend-yield snapshots. |
| `equity_vol_30d` | RO | Requires BVB BET daily close history or an official volatility snapshot; current adapter only has level and 1Y performance snapshots. | Restore with a stable BVB daily-close feed, factsheet volatility field, or configured market-data credential. |

## Resolved In Current Sprint

| Indicator | Resolution | Treatment |
|---|---|---|
| `cb_forward_guidance` | Converted to manual | Dated hawk/dove communication score with central-bank source links; still `low_confidence` because it is qualitative research input. |
| `ifo_expectations` | Reframed and wired | Replaced Ifo placeholder with Eurostat Germany Industry Confidence as an external-demand spillover signal. |
| `oecd_cli` | Reframed and wired | Replaced unavailable OECD CLI slot with Eurostat Employment Expectations Indicator. |
| `manufacturing_pmi` | Reframed and wired | Replaced vendor PMI placeholder with Eurostat Industry Confidence Indicator; footnotes state it is not an S&P PMI. |
| `truck_km_index` | Reframed and wired | Replaced toll-road truck-km placeholder with Eurostat quarterly road freight activity in million tonne-kilometres. |
| `cds_5y` | Reframed and wired | Replaced vendor CDS placeholder with a public 10Y sovereign spread-vs-Bund substitute from Eurostat yields. |
| `embi_spread` | Reframed and wired | Replaced JPMorgan EMBI placeholder with a public 10Y sovereign spread-vs-Bund substitute from Eurostat yields. |
| `fx_implied_vol` | Reframed and wired | Replaced vendor FX options implied-vol placeholder with ECB-derived 21-trading-day realised FX volatility; footnote states it is not implied vol. |
| `foreign_bank_share` | Converted to manual official snapshot | Replaced Romania proxy with NBR Annual Report market share of credit institutions with majority foreign capital, including branches of foreign credit institutions, in net banking-sector assets. |
| `cb_balance_sheet_gdp` | Converted to manual official-data snapshot | Replaced Romania proxy with NBR monthly-bulletin central-bank total assets scaled by Romania 2024 current-price GDP; retained `watch` because the snapshot is stale and should be refreshed from BNR monthly bulletins. |
| `fx_loan_share` | Partially converted to official secondary-source snapshots | Replaced Hungary and Czechia proxies with OeNB CESEE report snapshots sourced from national central banks, wiiw, and OeNB. Poland and Romania continue to use IMF FSI coverage. |
| `gas_storage_level` | Converted to official seasonal snapshots | Replaced four-country proxy with ENTSOG Summer/Winter Supply Outlook storage-fullness snapshots based on AGSI+ data; retained `watch` because no-key builds are seasonal rather than daily. |
| Poland equity market metrics | Wired official GPW Benchmark snapshots | Replaced Poland `equity_vol_30d`, `equity_fwd_pe`, `equity_pb`, and `equity_div_yield` proxies with WIG20 GPW Benchmark snapshots; retained `watch` because these are current factsheet-style observations rather than full historical series. |
| Romania equity index | Wired official BVB snapshot | Replaced Romania `equity_index` proxy with the official Bucharest Stock Exchange BET profile snapshot; retained `watch` because it is a current profile observation rather than a full historical close feed. |
| Romania equity YoY | Wired official BVB performance snapshot | Replaced Romania `equity_yoy` proxy with the official BVB BET `1 an (%)` index-performance table value; retained `watch` because it is a snapshot rather than a locally recomputed history-derived series. |

## Proposed Implementation Order

1. Keep the public dashboard proxy-free by default.
2. Restore dropped slots only when the adapter can return non-proxy source data.
3. Use `DATA_SOURCE_CATALOG.md` as the first stop for future model/developer handoff.

## User Decisions Needed

No immediate decision needed. The remaining proxy-only slots have been dropped from rendered pages.
