# Proxy Indicator Review

Date: 2026-05-25

Purpose: decide which remaining proxy indicators should be kept, replaced, reframed, converted to manual maintenance, or removed from the dashboard. This file is the working decision layer above `SOURCE_DISCOVERY_MATRIX.md`.

Current proxy baseline:

| Country | Proxy count | Total indicators | Share |
|---|---:|---:|---:|
| Hungary | 4 | 114 | 3.5% |
| Poland | 1 | 114 | 0.9% |
| Czechia | 4 | 114 | 3.5% |
| Romania | 7 | 114 | 6.1% |

Proxy union: 7 indicators.

## Decision Categories

| Decision | Meaning | Dashboard treatment |
|---|---|---|
| Replace | Search for a reusable official, exchange, or public API source. | Keep chart for now with `low_confidence`, then wire adapter when found. |
| Reframe | Current label over-promises; keep the idea but rename or change the definition. | Update label, note, and source logic before treating as final. |
| Manual | Better maintained as a curated snapshot with dated source notes. | Move to `config/manual_indicators.yaml` if source cadence is low. |
| Keep | Public source is unlikely; retain as a clearly marked placeholder/proxy only if analytically useful. | Keep `low_confidence` and explicit footnotes. |
| Remove | Low signal or weak sourceability; better to reduce dashboard clutter. | Remove from chart sections after user approval. |

## Recommended Decisions

| Indicator | Countries proxied | Recommendation | Rationale | Next action |
|---|---|---|---|---|
| `equity_index` | RO | Replace | Needed to derive Romania equity YoY and volatility. | Find stable BVB BET daily/monthly feed; avoid Yahoo if rate-limited/unreliable. |
| `equity_yoy` | RO | Replace after `equity_index` | Pure derived indicator; should disappear once Romania headline index is wired. | Derive automatically from `equity_index`. |
| `equity_vol_30d` | RO | Replace | Derived from daily index data; more sourceable than valuation metrics. | Find stable BVB BET daily close feed. |
| `breakeven_5y5y` | HU, PL, CZ, RO | Keep or Remove | Inflation-swap/linker curve data is typically vendor-controlled. | Keep only as conceptual placeholder; otherwise remove from public dashboard. |
| `equity_fwd_pe` | HU, CZ, RO | Manual or Remove | Forward earnings valuation is vendor/analyst-consensus based; the dashboard label has been softened to P/E where exchange factsheets are available. | Use exchange/factsheet snapshots if available; otherwise remove. |
| `equity_pb` | HU, CZ, RO | Manual or Remove | P/B may appear in exchange/index factsheets, but API coverage is uneven. | Search exchange factsheets; otherwise curate annual/quarterly snapshots. |
| `equity_div_yield` | HU, CZ, RO | Manual or Remove | Dividend yield can be factsheet-based but is not reliably API-driven. | Search exchange factsheets; otherwise curate snapshots. |

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

## Proposed Implementation Order

1. Replace Romania equity data first because `equity_index` unlocks `equity_yoy` and `equity_vol_30d`.
2. Decide whether vendor-market indicators should remain as placeholders: `breakeven_5y5y` and equity valuation metrics.
3. Decide whether vendor-only valuation and market-risk placeholders should remain visible or be removed from the public dashboard.

## User Decisions Needed

Before deleting any chart, confirm these choices:

1. Should vendor-only market indicators remain as explicit low-confidence placeholders, or should the public dashboard remove them?
2. Should equity valuation metrics be manually curated from exchange/factsheet snapshots, or removed until a paid data source exists?
