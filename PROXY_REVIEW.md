# Proxy Indicator Review

Date: 2026-05-23

Purpose: decide which remaining proxy indicators should be kept, replaced, reframed, converted to manual maintenance, or removed from the dashboard. This file is the working decision layer above `SOURCE_DISCOVERY_MATRIX.md`.

Current proxy baseline:

| Country | Proxy count | Total indicators | Share |
|---|---:|---:|---:|
| Hungary | 9 | 114 | 7.9% |
| Poland | 9 | 114 | 7.9% |
| Czechia | 9 | 114 | 7.9% |
| Romania | 13 | 114 | 11.4% |

Proxy union: 14 indicators.

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
| `gas_storage_level` | HU, PL, CZ, RO | Replace | Important external/energy buffer; official or industry API likely exists, but GIE AGSI needs API-key access. | Try AGSI with API key; otherwise test ENTSOG and national gas operators. |
| `fx_loan_share` | HU, CZ | Replace | Important balance-sheet vulnerability measure; PL and RO already use IMF FSI. | Search MNB and CNB public tables; CNB ARAD may require an API key. |
| `cb_balance_sheet_gdp` | RO | Replace | Useful monetary-policy/liquidity indicator; Romania gap is source-specific. | Search BNR statistical balance-sheet tables or IMF IFS mirror. |
| `foreign_bank_share` | RO | Replace or Manual | Useful financial-structure metric, but annual and slow-moving. | Search BNR/EBRD/ECB banking statistics; if no clean API, curate annual snapshots. |
| `equity_index` | RO | Replace | Needed to derive Romania equity YoY and volatility. | Find stable BVB BET daily/monthly feed; avoid Yahoo if rate-limited/unreliable. |
| `equity_yoy` | RO | Replace after `equity_index` | Pure derived indicator; should disappear once Romania headline index is wired. | Derive automatically from `equity_index`. |
| `equity_vol_30d` | PL, RO | Replace | Derived from daily index data; more sourceable than valuation metrics. | Find stable WIG/WIG20 and BET daily close feeds. |
| `cds_5y` | HU, PL, CZ, RO | Keep or Replace with spread | CDS is vendor market data; open substitutes are imperfect. | Prefer sovereign spread vs Bund as public replacement, or keep clearly marked proxy. |
| `embi_spread` | HU, PL, CZ, RO | Remove or Replace with spread | EMBI is vendor/J.P. Morgan data and overlaps with sovereign spread indicators. | Remove unless a public sovereign-risk spread definition is chosen. |
| `breakeven_5y5y` | HU, PL, CZ, RO | Keep or Remove | Inflation-swap/linker curve data is typically vendor-controlled. | Keep only as conceptual placeholder; otherwise remove from public dashboard. |
| `fx_implied_vol` | HU, PL, CZ, RO | Keep or Remove | FX options data is vendor-controlled and hard to replicate with public sources. | Keep as low-confidence proxy only if useful for trading lens. |
| `equity_fwd_pe` | HU, PL, CZ, RO | Manual or Remove | Forward earnings valuation is vendor/analyst-consensus based. | Use manual factsheet snapshots if available; otherwise remove. |
| `equity_pb` | HU, PL, CZ, RO | Manual or Remove | P/B may appear in exchange/index factsheets, but API coverage is unlikely. | Search exchange factsheets; otherwise curate annual/quarterly snapshots. |
| `equity_div_yield` | HU, PL, CZ, RO | Manual or Remove | Dividend yield can be factsheet-based but is not reliably API-driven. | Search exchange factsheets; otherwise curate snapshots. |

## Resolved In Current Sprint

| Indicator | Resolution | Treatment |
|---|---|---|
| `cb_forward_guidance` | Converted to manual | Dated hawk/dove communication score with central-bank source links; still `low_confidence` because it is qualitative research input. |
| `ifo_expectations` | Reframed and wired | Replaced Ifo placeholder with Eurostat Germany Industry Confidence as an external-demand spillover signal. |
| `oecd_cli` | Reframed and wired | Replaced unavailable OECD CLI slot with Eurostat Employment Expectations Indicator. |
| `manufacturing_pmi` | Reframed and wired | Replaced vendor PMI placeholder with Eurostat Industry Confidence Indicator; footnotes state it is not an S&P PMI. |
| `truck_km_index` | Reframed and wired | Replaced toll-road truck-km placeholder with Eurostat quarterly road freight activity in million tonne-kilometres. |

## Proposed Implementation Order

1. Replace Romania/Poland equity data first because `equity_index` unlocks `equity_yoy` and `equity_vol_30d`.
2. Replace energy and balance-sheet vulnerabilities: `gas_storage_level`, `fx_loan_share`, `cb_balance_sheet_gdp`, and `foreign_bank_share`.
3. Decide whether vendor-market indicators should remain as placeholders: `cds_5y`, `embi_spread`, `breakeven_5y5y`, `fx_implied_vol`, and equity valuation metrics.
4. Decide whether vendor-only valuation and market-risk placeholders should remain visible or be removed from the public dashboard.

## User Decisions Needed

Before deleting any chart, confirm these choices:

1. Should vendor-only market indicators remain as explicit low-confidence placeholders, or should the public dashboard remove them?
2. Should equity valuation metrics be manually curated from exchange/factsheet snapshots, or removed until a paid data source exists?
