# Japan / South Africa Depth and Trust Surface

Date: 2026-08-28
Status: approved design, ready for implementation planning
Scope: `output/japan.html`, `output/south_africa.html`, and the shared quality model

## Goal

Make the Japan and South Africa pages usable for single-country depth work by a
macro PM: comprehensive coverage, native official sources, and a page that
communicates how far each number can be trusted.

Two constraints from the requester shape everything below:

1. **Depth with comprehensiveness.** Japan (46 charts) and South Africa (51) are
   the thinnest pages in the project against US 164, CEE ~110, China 105, UK 92.
   Breadth is a goal, not a trade-off against quality.
2. **No pruning; cross-check pairs are wanted.** Native series are added
   *alongside* existing mirrors where both answer the same question, following
   the SARB-vs-IMF pattern already on the South Africa page.

## Evidence

All measured against the live artefacts at commit `138fe66`.

### E1 — The authority classifier ranks the best sources worst

`data_quality.source_authority()` classifies by string-matching the source
*display name* against hardcoded token lists. Measured on the canonical frames:

| Source | Reality | Classified as |
|---|---|---|
| `SARB Web API` (11 series) | compiling central bank, same-day publication | `public_secondary` |
| `FRED / OECD (Stats SA)` | third-hand mirror | `official_mirror` |

The South African Reserve Bank ranks *below* a mirror of a mirror of its own
data. BOJ, e-Stat, and Eskom contain none of the matched tokens either, so every
native adapter added by this work would arrive misclassified.

### E2 — `verified` is unreachable for derived series

```python
elif (authority == "official_primary" and derivation == "observed"
      and freshness == "current" and validation == "passed"):
    status = "verified"
```

`derivation_type()` returns `derived` whenever `transform != "level"`. A
year-over-year inflation rate computed from an official index therefore can
never be `verified`, regardless of source quality. Japan and South Africa are
transform-heavy by design, so this caps most of both pages at `watch`.

Japan today: 29 `watch` + 17 `low_confidence`, **0 `verified`** out of 46.

### E3 — The reader never sees the trust dimensions

`source_authority`, `freshness`, `derivation`, and `comparability` are all
computed and stored in the canonical frames. The rendered page shows a single
pill. "watch" may mean stale, mirror-sourced, derived, or all three, and the
reader cannot distinguish them.

### E4 — Pipeline outcomes are unguarded

`scripts/freshness_audit.py` emitted zero records for every data-first page for
an unknown period because its chart regex predated the Core 48 view attributes.
`make validate` passed throughout: it asserts page structure, never pipeline
outcomes. Fixed on 2026-08-28, but the class of bug remains unguarded.

### E5 — Source feasibility (probed 2026-08-28)

| Source | Credential | Status |
|---|---|---|
| BOJ flat files | none | 16 stable ZIPs incl. CGPI, SPPI, monthly BoP, IIP, Flow of Funds |
| e-Stat | `ESTAT_APP_ID` | verified working (`STATUS=0`); free-text search times out, narrow `statsCode` lookups required |
| Eskom data portal | none | ~24 public CSV datasets across demand, outage, OCGT, renewables |
| IMF SDMX BOP/IIP/MFS | none | live through 2026-Q1, dozens of indicator codes, largely untapped |
| SARB Web API | none | capped at ~13 curated series; arbitrary QB codes return `[]` |
| Stats SA | n/a | behind an Incapsula WAF; not automatable |

## Design

### D1 — Adapters and data

Three new fetchers in a shared adapter module (not inside a builder):

| Adapter | Credential | Feeds |
|---|---|---|
| `fetch_boj_flatfile` | none | CGPI, SPPI, monthly BoP, IIP, Flow of Funds |
| `fetch_estat` | `ESTAT_APP_ID` | Statistics Bureau / MHLW / MLIT tables |
| `fetch_eskom_csv` | none | Eskom demand, outage performance, OCGT, renewables |

Japan Core-48 concept gaps closed with native official data:

| Concept | Today | After |
|---|---|---|
| `core_inflation` | missing | e-Stat CPI ex-fresh-food (BoJ policy reference) |
| `services_inflation` | missing | e-Stat CPI services subindex |
| `goods_inflation` | missing | e-Stat CPI goods subindex |
| `producer_price_inflation` | missing | BOJ CGPI |
| `vacancies` | missing | MHLW job-to-applicant ratio via e-Stat |
| `housing_activity` | missing | MLIT housing starts via e-Stat |
| `consumption_growth` | missing | e-Stat household survey |

Plus BOJ monthly balance of payments replacing the FRED `current_account_gdp`
series that is stuck at 2024-Q4 — the worst staleness on the page.

The table above names the *concepts* to close, not resolved series identifiers.
Only the e-Stat CPI table groups have been confirmed to exist (`statsCode`
`00200573`, five table groups including the 2015-base CPI). Each implementation
phase must begin with a discovery step that resolves the exact `statsDataId`,
column, unit, and seasonal-adjustment basis, and records them in the config the
same way the existing FRED series ids are recorded. A concept whose series
cannot be resolved and validated stays a documented gap rather than being filled
with an approximation.

South Africa gains the Eskom energy block. Available capacity, UCLF/OCLF, OCGT
load factors and renewable generation are country-specific: they are namespaced
`za:*` and deliberately do **not** occupy Core-48 slots. This deepens the page
without inflating its comparable-core count.

Naming discipline: BOJ's SPPI is producer-side services prices, not consumer
services inflation. `services_inflation` maps to the e-Stat CPI services
subindex; SPPI is kept as `jp:services_ppi`.

South Africa core CPI, expanded unemployment, and QES earnings remain documented
gaps. Stats SA is not automatable and SARB does not carry them.

### D2 — Trust model fixes

1. `source_authority` becomes a **declared field in the indicator config**, with
   the existing string matcher as fallback. The config author validated the
   source and should assert its tier rather than have it inferred from a display
   name. The matcher's `official_primary` list is extended with BOJ, e-Stat,
   SARB, Eskom, MHLW, MLIT, METI.
2. Split the derivation gate. A **declared, documented transform of an official
   series** (`yoy_pct`, `pct_change`) remains eligible for `verified`. A
   **substitute standing in for a different concept** does not, and continues to
   be caught by `comparability: low`.
3. Render authority and freshness as separate chips; the quality pill states its
   reason instead of asserting a verdict.
4. Page-level provenance line: `38 native official · 12 mirror · 0 wrapper`, so
   the mix is visible and improvement is measurable across builds.

### D3 — Cross-check divergence indicator

Pairs are **declared, not auto-detected**, because auto-pairing on shared
`concept_id` would create false pairs across differing definitions, units, or
transforms.

```yaml
cross_checks:
  - concept: headline_inflation
    primary:   cpi_inflation        # SARB - compiling authority
    secondary: cpi_inflation_imf    # IMF SDMX - independent path
    tolerance_pp: 0.15
```

Computation aligns on common dates only, same frequency and transform, and
stores `n_common`, `latest_diff`, `max_abs_diff`, `n_breaches`,
`last_breach_date`, and `status` (`agree` / `minor` / `diverged`).

Rendering: one line under the chart footer of both members of the pair, plus a
page-level roll-up (`4 cross-checks · 3 agree · 1 diverged`).

Default tolerances by concept type: rates 0.15pp, yields 5bp, index levels 0.5%.
Overridable per pair.

Rationale, in priority order:

1. **A regression test on the new adapters, surfaced to the user.** Three
   adapters are being written against unfamiliar formats. If a parser mis-scales
   a series or selects the wrong column, the cross-check fails loudly.
2. Catches revision-timing splits between publication paths.
3. Catches definitional drift such as rebasing or reweighting on one path only.

Because of (1), cross-check results are written to the summary JSON and asserted
in `make validate`.

### D4 — Guards and testing

New assertions in `scripts/validate_outputs.py`:

- Every dashboard in `COUNTRY_FILES` produces freshness records (would have
  caught E4)
- Every canonical series carries non-empty `source_authority`, `freshness`,
  `derivation`
- No series from a declared-native adapter classifies as `public_secondary`
- Cross-check results are within tolerance

Testing respects the existing contract that `make validate` is offline and
deterministic. Trimmed fixtures (one BOJ ZIP, one e-Stat JSON response, one
Eskom CSV) live in `tests/fixtures/`; parser unit tests run against them offline.
Live probes are added to `make refresh-check`, not to validation.

### D5 — Rollout

Six independently shippable phases, ordered by blast radius:

| # | Phase | Scope | Risk |
|---|---|---|---|
| 1 | Quality-model fixes (D2.1, D2.2) + declared authority | all 9 countries | highest, shared code |
| 2 | Guards and fixtures | all | low, additive |
| 3 | BOJ + Eskom adapters | JP, ZA | low, no credential |
| 4 | e-Stat adapter | JP | medium, credential-gated |
| 5 | Cross-checks + validate assertions | JP, ZA | low |
| 6 | Trust surface rendering | all | presentation only |

Phase 1 touches `data_quality.py`, shared by all nine pages, so quality pills
will move everywhere. Mitigation: run through `make rebuild-ui` (snapshot-only,
zero network), diff the before/after quality distributions, and review that
shift before publishing. No data changes in that phase, so every pill movement
is attributable to the scoring change.

The e-Stat adapter degrades gracefully: absent `ESTAT_APP_ID`, its indicators
fall back to their existing `data_gaps` entries rather than failing the build.

### D6 — Debt owned by this work

`fetch_imf_sdmx` currently lives in `scripts/build_japan_dashboard.py` and
`build_south_africa_dashboard.py` imports it from there — a builder importing a
fetcher from another builder. It moves into the shared adapter module along with
the three new adapters. This is targeted cleanup of code this work touches, not
the broader P5 generator consolidation, which remains a separate project.

## Non-goals

- **Vintage and revision tracking (P3).** Agreed as the immediately-following
  spec. It requires a new storage schema, revision detection, and migration of
  five canonical frames, and would blur both pieces of work if folded in here.
- **P5 generator consolidation.** Separate project.
- Cross-country or regime/positioning features (the requester selected
  single-country depth over those).
- Defeating the Stats SA WAF.

## Risks

| Risk | Mitigation |
|---|---|
| BOJ ZIP internals unknown; Shift-JIS encoding likely | Parse one before committing to the config shape; fixture-test the parser |
| e-Stat slow (30s timeout observed on free-text search) | Narrow `statsCode`/`statsDataId` lookups only, generous read timeouts |
| Eskom CSV path is dated (`/2026/07/`) | Discover the link from the page, as `build_uk_dashboard` already does for GOV.UK |
| Phase 1 shifts quality pills on all nine pages | Snapshot-only rebuild, diff distributions, review before publish |
| New breadth could dilute quality | All new breadth comes from native official sources, so authority and coverage move together |
