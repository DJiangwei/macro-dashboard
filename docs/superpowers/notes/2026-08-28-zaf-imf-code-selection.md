# South Africa IMF BOP (SDMX) code selection

Task 10 of the `2026-08-28-jp-za-depth-and-trust` plan. South Africa's planned
breadth source (Eskom) is undeliverable (all published CSV links 404; the data
only reaches Eskom's own pages through an undocumented WordPress admin-ajax
endpoint, which the project's source policy rules out — see `data_gaps` entry
"Eskom load-shedding stages" in `config/south_africa_indicators.yaml`). Breadth
instead comes from the IMF SDMX `BOP` dataflow (IMF.STA:BOP(21.0.0)), which
mirrors SARB's own BPM6 submission and is confirmed live for South Africa
through 2026-Q1.

## Method

`SERIES_NAME` comes back empty on every BOP row, so series keys such as
`ZAF.A_NFA_T.O_F4_S122.USD` are opaque without decoding the codelists that back
the `BOP_ACCOUNTING_ENTRY` and `INDICATOR` dimensions.

1. Pulled the DSD: `GET .../datastructure/IMF.STA/DSD_BOP?references=children`.
   This resolves the dimension order (`COUNTRY.BOP_ACCOUNTING_ENTRY.INDICATOR.UNIT.FREQUENCY`,
   `TIME_PERIOD` as the time dimension) and — via each dimension's concept —
   the codelist id/version backing it: `INDICATOR` → `CL_BOP_INDICATOR` v10.0.0,
   `BOP_ACCOUNTING_ENTRY` → `CL_BOP_ACCOUNTING_ENTRY` v3.3.0. The `references=children`
   query does **not** inline the codelists themselves (only the `Ref` pointers), so
   each codelist had to be fetched separately:
   `GET .../codelist/IMF.STA/CL_BOP_INDICATOR/10.0.0` (979 codes) and
   `GET .../codelist/IMF.STA/CL_BOP_ACCOUNTING_ENTRY/3.3.0` (97 codes).
2. Pulled full ZAF BOP data since 2023 with all dimensions wildcarded
   (`BOP/ZAF....Q`, `startPeriod=2024-01` per the brief's script, and a second,
   wider pull with `startPeriod=2023-01` used for this note) to find which
   `(entry, indicator, unit)` triples actually carry non-null `OBS_VALUE`
   through 2026-Q1, and to read each row's `UPDATE_DATE` attribute for
   freshness.
3. Joined the two: for every candidate with live data, looked up its entry code
   and indicator code by exact id match in the decoded codelists, confirmed the
   plain-English name, then **cross-checked signs and definitions against the
   BPM6 accounting identity** using the actual pulled numbers (below) rather
   than taking the codelist name at face value.

## A frequency trap the brief's template would have hit

The brief's config template omits `FREQUENCY` from the series key
(`ZAF.<ENTRY>.<INDICATOR>.USD`, 4 segments). That key *does* return data — but
BOP publishes both `A` (annual) and `Q` (quarterly) rows for the same
entry/indicator/unit, back to 1948 annual / 1960 quarterly. `sdmx_period_to_date`
in `adapters.py` maps a bare year `"2024"` to `"2024-01-01"` — the same date it
maps `"2024-Q1"` to. Requesting the wildcard-frequency key therefore returns
two different `OBS_VALUE`s for the same calendar date (one annual, one
quarterly-Q1), which `fetch_imf_sdmx` would silently interleave and sort,
corrupting the series. All accepted keys below append an explicit `.Q` to pin
the frequency dimension and get clean quarterly-only series (265 quarters,
1960-Q1 to 2026-Q1, for every accepted code).

## Correction: financial derivatives was missing from the first pass

The first pass of this note charted 4 of the 5 standard BPM6 financial-account
functional categories (direct investment, portfolio investment, other
investment, reserve assets) and described them as "financial account and its
3 sub-categories" — a miscount of the standard taxonomy, not a deliberate
scope decision. **Financial derivatives (BPM6 category `F_F7`, "Financial
derivatives (other than reserves) and employee stock options") was never
examined, rejected, or disclosed as a gap.**

This was caught in review: the four charted sub-categories summed to
+$0.39bn against a reported Financial Account Balance of +$1.41bn for
2026-Q1 — an unexplained ~$1bn hole that a reader following this page's own
`capital_account_balance` caveat (which invites summing sub-components
against the balance) would have hit immediately. Re-running the same
resolution procedure used for the other twelve:

- `ZAF.NNAFANIL_T.F_F7.USD.Q` decodes to entry `NNAFANIL_T` (the same
  net-lending convention used for `D_F`/`P_F`/`O_F`) and indicator `F_F7` =
  "Financial derivatives (other than reserves) and employee stock options"
  in `CL_BOP_INDICATOR` v10.0.0 — the same codelist pull used throughout this
  note, re-checked directly against the cached codelist file rather than
  taken on trust.
- Live full-history pull (`ZAF.NNAFANIL_T.F_F7.USD.Q`) confirms 117
  consecutive quarters, 1997-Q1 through 2026-Q1, no gaps, `UPDATE_DATE`
  2026-08-28 on the latest observation — same freshness as every other
  accepted series.
- Sign convention confirmed the same way as `D_F`: `NNAFANIL_T.F_F7
  (1,018,884,366) = A_NFA_T.F_F7 (-3,895,071,766) - L_NIL_T.F_F7
  (-4,913,956,132)`. ✓
- **Full five-category identity now closes exactly**, not just approximately:
  `D_F (-298,735,623) + P_F (936,425,989) + O_F (-589,268,260) + F_F7
  (1,018,884,366) + R_F (344,158,130) = 1,411,464,602`, versus reported `FAB
  = 1,411,464,602.0675459` — matches to 1e-16 relative precision (floating-point
  noise only). This is materially stronger evidence than the four-category
  version in the first pass, which was off by ~$1.02bn (the exact size of
  `F_F7`) and should have been treated as a red flag rather than left as an
  unremarked ~28%-of-FAB gap.

`F_F7` passes the same four-part acceptance bar as the other twelve and is
now the 13th accepted series (`financial_derivatives_net`). It is *larger* in
magnitude than direct investment, other investment, or the reserve-asset flow
individually at 2026-Q1, so this was not a rounding-level omission. The two
caveats that referenced "three financial account sub-categories" or stated
the current-account identity without net errors and omissions
(`other_investment_net`, `capital_account_balance`) have been corrected in
the same commit as this note update.

## A builder wiring gap found and fixed

`build_south_africa_dashboard.py`'s `_fetch_one` called
`_apply_transform(fetch_imf_sdmx(session, spec))` for the `imf_sdmx` fetcher,
never `apply_scale(...)`. None of the five pre-existing `imf_sdmx` indicators
(`cpi_inflation_imf`, `cpi_mom`, `cpi_index`, `bank_capital_ratio`,
`bank_npl_ratio`) declare a `scale`, so this was latent. The BOP series below
are raw USD (billions-scale numbers) and need `scale: 1000000000` to render as
"USD bn" like the existing trade series — so the fetch path now reads
`_apply_transform(apply_scale(fetch_imf_sdmx(session, spec)))`, matching the
`fred` branch immediately above it. `apply_scale` is a no-op when `scale` is
unset, so this does not change the five existing `imf_sdmx` indicators.

## Accounting-identity cross-check

Using the 2026-Q1 pulled values (USD, full precision), the standard BPM6
identity holds to within rounding, which is strong independent confirmation
that the entry/indicator/sign decoding below is correct — not just that the
codelist names sound plausible:

- `GS (4,504,933,098) = G (5,031,638,283) + S (-526,705,184)` ✓
- `CAB (-463,015,825) = GS (4,504,933,098) + IN1 (-4,470,443,921) + IN2 (-497,505,002)` ✓
- `FAB (1,411,464,602) ≈ CAB (-463,015,825) + KAB (3,917,844) + EO (1,870,562,583) = 1,411,464,602` ✓ (exact)
- `NNAFANIL_T.D_F (-298,735,623) = A_NFA_T.D_F (940,894,780) - L_NIL_T.D_F (1,239,630,403)` ✓ (confirms the net-entry sign convention: net acquisition of assets minus net incurrence of liabilities)
- `FAB (1,411,464,602) = D_F (-298,735,623) + P_F (936,425,989) + O_F (-589,268,260) + F_F7 (1,018,884,366) + R_F (344,158,130)` ✓ (exact to floating-point precision — see the correction section above; the first pass checked only 4 of these 5 terms and was off by ~$1.02bn)

The last-4-quarter current account (2025-Q2 through 2026-Q1) sums to
+$0.40bn — a near-balanced current account, consistent with South Africa's
recent trajectory of a much-narrowed deficit on strong commodity terms of
trade. This is a plausibility check, not proof, but it rules out a sign
inversion or unit error of the kind this project has hit before.

## Accepted series (13)

All: dataflow `BOP`, frequency `Q`, unit `USD`, `source_authority: official_mirror`
(IMF is a mirror of SARB's own BPM6 submission, not SARB's own API), `scale: 1000000000`,
`unit: "USD bn"`, `start_date: "2000-01-01"` (data goes back to 1960-Q1; 2000
matches the truncation already used across the rest of the South Africa page).
Latest observation for every accepted series is 2026-Q1, `UPDATE_DATE` 2026-08-28
— two days before this note, well inside one quarterly release cycle.

| id (config) | SDMX key | Accounting entry (`CL_BOP_ACCOUNTING_ENTRY`) | Indicator (`CL_BOP_INDICATOR`) | Sign convention | 2026-Q1 value | Decision |
|---|---|---|---|---|---|---|
| `current_account_balance_bop` | `ZAF.NETCD_T.CAB.USD.Q` | `NETCD_T` = "Net (credits less debits)" | `CAB` = "Current account balance (credit less debit)" | + = surplus (credits > debits) | -0.463 bn | **Accept** |
| `goods_balance_bop` | `ZAF.NETCD_T.G.USD.Q` | `NETCD_T` | `G` = "Goods" | + = goods surplus | +5.032 bn | **Accept** |
| `services_balance_bop` | `ZAF.NETCD_T.S.USD.Q` | `NETCD_T` | `S` = "Services" | + = services surplus | -0.527 bn | **Accept** |
| `primary_income_balance` | `ZAF.NETCD_T.IN1.USD.Q` | `NETCD_T` | `IN1` = "Primary income" | + = net income receipts from abroad | -4.470 bn | **Accept** |
| `secondary_income_balance` | `ZAF.NETCD_T.IN2.USD.Q` | `NETCD_T` | `IN2` = "Secondary income" | + = net current transfers received | -0.498 bn | **Accept** |
| `capital_account_balance` | `ZAF.NETCD_T.KAB.USD.Q` | `NETCD_T` | `KAB` = "Capital account balance (credit less debit)" | + = surplus | +0.004 bn | **Accept** |
| `net_errors_omissions` | `ZAF.NETCD_T.EO.USD.Q` | `NETCD_T` | `EO` = "Net errors and omissions" | balancing item; no economic sign meaning | +1.871 bn | **Accept** |
| `financial_account_balance` | `ZAF.NNAFANIL_T.FAB.USD.Q` | `NNAFANIL_T` = "Net (net acquisition of financial assets less net incurrence of liabilities), Transactions" | `FAB` = "Financial account balance (assets less liabilities)" | + = SA net acquired more foreign financial assets than it incurred foreign liabilities (net lender) | +1.411 bn | **Accept** |
| `direct_investment_net` | `ZAF.NNAFANIL_T.D_F.USD.Q` | `NNAFANIL_T` | `D_F` = "Direct investment, Total financial assets/liabilities" | + = net FDI outflow (SA residents' net direct-investment asset acquisition > net direct-investment liabilities incurred) | -0.299 bn | **Accept** |
| `portfolio_investment_net` | `ZAF.NNAFANIL_T.P_F.USD.Q` | `NNAFANIL_T` | `P_F` = "Portfolio investment, Total financial assets/liabilities" | + = net portfolio outflow on this net basis (does **not** by itself mean foreigners were net sellers of SA bonds/equities — see caveat) | +0.936 bn | **Accept** |
| `other_investment_net` | `ZAF.NNAFANIL_T.O_F.USD.Q` | `NNAFANIL_T` | `O_F` = "Other investment, Total financial assets/liabilities" (loans, deposits, trade credit) | + = net outflow via loans/deposits/trade credit | -0.589 bn | **Accept** |
| `financial_derivatives_net` | `ZAF.NNAFANIL_T.F_F7.USD.Q` | `NNAFANIL_T` | `F_F7` = "Financial derivatives (other than reserves) and employee stock options" | + = net outflow via derivative/ESO positions, same convention as `D_F`/`P_F`/`O_F` | +1.019 bn | **Accept** (added after review; see correction section above) |
| `reserve_assets_flow` | `ZAF.A_T.R_F.USD.Q` | `A_T` = "Assets" | `R_F` = "Reserve assets, Total financial /liabilities" | + = reserve accumulation (transaction flow, **not** the reserve stock/level) | +0.344 bn | **Accept** |

The financial account is a 5-category BPM6 decomposition (direct, portfolio,
financial derivatives, other investment, reserve assets); `financial_account_balance`,
`direct_investment_net`, `portfolio_investment_net`, `other_investment_net`,
`financial_derivatives_net`, and `reserve_assets_flow` together chart the
balance and all five categories.

## Considered and rejected

| Candidate SDMX key | Decoded definition | Reason rejected |
|---|---|---|
| `ZAF.NETCD_T.GS.USD.Q` | Goods and services balance | Redundant once `G` and `S` are charted separately (`GS = G + S` exactly, confirmed above); the brief asks for goods/services as separate components, and two charts carry more information than one combined chart at the same budget cost. |
| `ZAF.NETCD_T.GSIN1.USD.Q` | Goods, services and primary income balance | Same redundancy reasoning; `GS + IN1` is already fully visible from three accepted charts. |
| `ZAF.NETCD_T.CABXEF.USD.Q` | Current account balance excluding exceptional financing | Near-identical to `CAB` for South Africa (no material exceptional-financing episodes in the sample window); adds a second, harder-to-explain current-account chart without adding information. Kept `CAB` only. |
| `ZAF.NNAFANIL_T.FABXRRI.USD.Q` | Financial account balance excluding reserves and related items | `FAB` and `R_F` (both accepted) already let a reader back this out (`FABXRRI ≈ FAB - RUE`); adding a third overlapping financial-account balance was judged clutter rather than depth, per "fewer well-understood series beats more." |
| `ZAF.NNAFANIL_T.RUE.USD.Q` | Reserves and related items (net) | Near-duplicate of `R_F` (344 vs 345 $mn in 2026-Q1 — both are "the reserve-asset line of the financial account," `RUE` folds in a couple of adjacent memo items). Picked `R_F` for the more literal, single-concept name. |
| `ZAF.A_T.R_AFR.USD.Q` | Reserve assets, adjusted using IMF accounting records | Same reserve-asset flow as `R_F`, adjusted for IMF accounting-record consistency (345.1 vs 344.2 $mn in 2026-Q1). Preferred plain `R_F` ("Total financial/liabilities") over the "adjusted" variant to avoid a caveat explaining what the adjustment is, since the difference is immaterial (<1%) and undocumented in the codelist beyond the name. |
| Sector/instrument detail under `D_F`, `P_F`, `O_F`, `F_F7`, `R_F` (e.g. `O_F4_S122`, `P_F3_S122_L`, `R_F11`, `R_F12`) | Instrument×sector breakdowns of the five accepted top-level financial-account codes (hundreds of live codes, per the earlier `979`-code indicator list) | Out of scope for the 10-15 target; the top-level `D_F`/`P_F`/`O_F`/`F_F7`/`R_F` already carry the main story. Left as a natural follow-on (same resolution procedure, mechanical to extend) rather than guessed at under time pressure. |
| Reserve-asset **level** (stock, not transaction flow) | Would require the IIP (International Investment Position) dataflow, not `BOP` | Explicitly out of scope for Task 10 per the plan's follow-on list ("IMF IIP and MFS_ODC expansion... Task 10 establishes the code-resolution procedure; applying it to the other dataflows is mechanical once done."). `BOP` only carries the *transaction flow* into/out of reserve assets each quarter, not the level of the SARB's gross reserves. The `data_gaps` entry for "Gross reserves, capital-flow detail, and sovereign risk spread" is updated (not removed) to reflect that BOP now supplies the capital-flow detail and a reserve-flow proxy, but the reserve **level** remains a gap. |
| Everything else in the 979-code `CL_BOP_INDICATOR` list not explicitly named above | — | Not examined individually; the search was targeted at the priority order the brief specifies (current account and its components, financial account, reserve assets) rather than an exhaustive sweep of all 979 codes. |

## Candidates examined vs. accepted

- Distinct `(entry, indicator, unit)` triples with live South African data since
  2023: **334** (from the wildcard pull).
  - Of these, 41 top-level/near-top-level codes touching the priority concepts
    (current account, its 4 components, capital account, errors and omissions,
    the financial account and its 5 BPM6 functional categories — direct,
    portfolio, financial derivatives, other investment, reserve assets — and
    reserve-asset variants/detail) were individually decoded against the
    codelists and cross-checked against the BPM6 identity.
- **13 accepted**, all passing (a) codelist-resolved definition, (b) confirmed
  unit (`USD`) and sign convention (verified via the identity chain above, not
  just the codelist name), (c) latest observation 2026-Q1 / updated 2026-08-28
  (within one release cycle), (d) a plain-English `caveat_en`. (Twelve from the
  first pass; `financial_derivatives_net` added after review caught its
  omission — see the correction section above.)
- **7 explicitly rejected** with reasons in the table above (redundant
  combinations or the wrong dataflow for what they'd need to represent).
- Sector/instrument sub-detail (hundreds of further live codes under the
  accepted top-level ones) was not pursued — left as documented follow-on
  work, not silently dropped.
