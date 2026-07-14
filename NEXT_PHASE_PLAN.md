# Macro Dashboard Framework v2: Operating Plan

Updated: 2026-07-13

This is the current handoff for future models and developers. The pre-v2 plan
is archived under `docs/archive/` and should not be used as the active build
contract.

## Current State

- Seven country pages use stable routes: `output/hungary.html`,
  `poland.html`, `czechia.html`, `romania.html`, `china.html`, `uk.html`, and
  `us.html`.
- The shared ontology is `config/framework_v2.yaml`: nine macro pillars and 48
  comparable core concepts. Country-specific indicators remain available as
  deep-dive extensions.
- Public pages default to Core 48 view. The All deep-dive charts switch reveals
  every country-specific chart without changing the underlying data.
- CEE pages contain no rendered proxy rows. Unsupported slots are omitted and
  documented rather than fabricated.
- A CEE build fetches each country once and writes
  `output/cee_build_snapshot.json`. Country pages, root/archive cards,
  workbench output, and the consistency check consume that same snapshot.
- China, UK, and US canonical files use `data-first-canonical-v2`. Series
  metadata is stored once and observations are compact `[date, value]` pairs.
- `make validate` is offline and deterministic. Live source refresh is a build
  concern, not a validation side effect.

## Framework Contract

The nine pillars are:

1. Growth and domestic demand
2. Production and business cycle
3. Labour and household income
4. Prices, wages, and costs
5. Housing and investment
6. External balance and FX
7. Fiscal and sovereign
8. Monetary, credit, and financial conditions
9. Financial stability and structural risk

Every series has two identities:

- `indicator_id`: source/country implementation, such as `cpi_yoy` or
  `cpi_yoy_akshare`.
- `concept_id`: comparable economic concept, such as `headline_inflation`.

If a series has no core mapping, its concept ID is namespaced, for example
`us:pending_home_sales`. Do not force a country-specific concept into a shared
slot unless definition, transformation, frequency, and unit are comparable.

## Data Quality Contract

Quality is multi-dimensional. Future adapters must retain these fields:

- `source_authority`: official primary, official mirror, public wrapper,
  manual curated, or public secondary.
- `derivation`: observed, derived, substitute, manual, or projection.
- `freshness_status`: current, due, stale, projection, future date, or missing.
- `validation_status`: passed, watch, or failed.
- `comparability`: high, medium, or low.
- `quality_status`: verified, watch, low confidence, or unavailable.

Release-aware default age limits live in
`src/country_primer/data_quality.py`. Override them only when an official
release calendar justifies a different threshold. A data point should not be
marked verified merely because the HTTP request succeeded.

Mixed actual/forecast series must mark a dated `actual_through` boundary and
row-level `is_projection`. Do not draw forecasts as observed history.

## Routine Workflow

```bash
scripts/uv_project.sh sync
make doctor
make build-v4
make validate
make publish MSG="Describe the data or framework change"
```

`make build-v4` is the source-refresh path and requires network access.
`make validate` never refetches data. After a successful push,
`scripts/publish_dashboard.sh` waits for the exact GitHub Pages commit and
smoke-tests all stable routes with a cache-busting query string.

Optional credentials belong only in `.env.local`, which is ignored by Git.
Never place API keys in configs, generated HTML, summary JSON, tests, or docs.

## Adapter Acceptance Checklist

1. Confirm the economic definition before selecting a series code.
2. Prefer native official APIs over mirrors; document why a mirror is needed.
3. Validate dimensions, unit, seasonal adjustment, frequency, and geography.
4. Check latest date, missing values, history length, cadence gaps, and jumps.
5. Define transformations explicitly, including YoY/MoM annualisation.
6. Assign a core concept only if cross-country comparability is defensible.
7. Add or update a focused test.
8. Run the complete build, offline validation, and browser smoke test.
9. Confirm the homepage card equals the country-page value from the same build.

## Next Optimisation Phases

### P1: Source Reliability and Release Calendars

- Add per-source circuit breakers and structured failure reasons instead of
  broad exception swallowing.
- Add release-calendar overrides for ONS, BEA/BLS, NBS/PBC, Eurostat, and
  central-bank series so `due` is based on expected publication dates.
- Split refresh into `make refresh-data` and `make rebuild-ui`; the latter
  should use committed/cache snapshots and avoid network calls.
- Add a non-blocking `make refresh-check` that compares live headline data with
  the committed snapshot without changing generated output.

### P2: Comparable Core Coverage

- Produce a 7-country by 48-concept coverage matrix from canonical metadata.
- Prioritise missing concepts by macro value, not by chart count.
- Resolve remaining semantic substitutes such as local-yield spread versus
  licensed EMBI/CDS; keep names economically explicit where exact public data
  does not exist.
- Expand China official-native adapters where stable NBS/PBC/SAFE structured
  endpoints can replace public wrappers.

### P3: Vintage and Revision Awareness

- Store release vintage and fetch timestamp separately from observation date.
- Add revision flags for GDP, labour, CPI, fiscal, and balance-of-payments data.
- For high-value releases, retain prior vintage to support surprise and
  revision analysis rather than overwriting history silently.

### P4: Trading Workbench

- Build release-surprise views only after consensus licensing is resolved.
- Add transformation-aware regime signals with explicit confidence weights.
- Separate slow structural scores from fast cyclical indicators.
- Keep portfolio/trade conclusions outside the data-quality score.

### P5: Generator Consolidation

- Migrate China, UK, and US source adapters behind a shared fetcher protocol.
- Keep country configs declarative and move repeated HTML/summary logic into a
  single renderer.
- Preserve country-specific sections as deep-dive modules while rendering the
  common nine-pillar core from the shared ontology.

## Non-Negotiable Rules

- Never fabricate, interpolate, or silently backfill a missing economic series.
- Never label a confidence survey as PMI, employment expectations as OECD CLI,
  or a local sovereign spread as CDS/EMBI without an explicit substitute label.
- Never let homepage cards refetch independently from country pages.
- Never commit credentials.
- Never publish without `make validate` and an online stable-route smoke test.
