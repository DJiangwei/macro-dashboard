# Project Lessons Learned

Date: 2026-06-19

Use this file as operational memory for future agents maintaining the macro
dashboard. These notes summarize the lessons learned while expanding and
publishing the CE4, China, UK, and US dashboards.

## 1. Publish Discipline

- Do not stop at a local build. The work is complete only after the commit is
  pushed, GitHub Pages reports the same commit as `built`, and live URLs pass a
  cache-busted smoke test.
- The reliable sequence is:

```bash
make build-v4
make data-catalog
make freshness-audit
make validate
git add .
git commit -m "<clear message>"
git push origin main
gh api repos/DJiangwei/macro-dashboard/pages/builds/latest --jq '.status + " " + .commit'
```

- After Pages is `built`, fetch live URLs with a commit cache-buster such as
  `?v=<short_commit>`. Browser caching can otherwise make stale pages look like
  deployment failures.
- Always check both the country page and the archive pages:
  `index.html`, `output/index.html`, and `output/dashboard_archive_summary.json`.
  The archive must update when any country dashboard changes.
- Finish with `git status --short --branch`; the ideal final state is
  `main...origin/main` with no local modifications.

## 2. Source Hierarchy

- Prefer native official sources for release-sensitive work. Use mirrors only
  when they are stable, clearly labelled, and validated against expected dates.
- US dashboard: FRED is the primary backbone for public US macro time series.
  Prefer FRED-backed BEA, BLS, Census, Fed, Treasury, and Realtor series where
  available. Use `FRED_API_KEY` from the runtime environment only; never commit
  it.
- UK dashboard: prefer ONS, Bank of England, HMRC/GOV.UK, OBR, and DESNZ native
  endpoints before FRED/OECD/BIS mirrors. UK monthly activity, labour, prices,
  fiscal, property transactions, and energy charts should lean native where
  possible.
- China dashboard: AKShare is useful for China-native and high-frequency series,
  especially where official APIs are hard to automate. Treat AKShare-wrapped
  Eastmoney/Sina/PBC/NBS-style data as reusable but not contractually official;
  watch for schema drift and validate latest dates after each expansion.
- CE4 dashboard: keep replacing proxies with Eurostat, ECB, BIS, IMF, World
  Bank, OECD, national central bank, national statistics office, debt office,
  and energy-market adapters. If a source is not reproducible, make that visible
  rather than silently fabricating continuity.

## 3. Secrets And Environment

- API keys must live in `.env.local` or the caller environment and be loaded by
  `scripts/uv_project.sh`. They must not appear in configs, generated HTML,
  summaries, docs, commits, or command output copied into docs.
- Before committing, run a secret scan for known keys and generic API-key
  patterns. A good scan should only hit blank examples in `.env.example`.
- The project environment is intentionally pinned with `uv`; do not assume the
  user's global Python packages are available to Codex or another agent.

## 4. Chart Transform Logic

- Match each chart to the economic question. Many macro series should not be
  shown as raw levels just because the source returns an index or value.
- Use YoY for inflation, retail-sales growth, output growth, house-price
  momentum, production growth, and other year-over-year macro comparisons.
- Use MoM or QoQ for high-frequency momentum: monthly GDP, retail sales,
  industrial production, real PCE, CPI/core CPI/core PCE, and similar release
  reaction charts.
- Keep levels only where the level itself is the signal: policy rates, yields,
  unemployment rates, participation rates, balances, inventories, debt ratios,
  FX levels, and index levels when the label explicitly says index.
- Every indicator's `label`, `unit`, `transform`, source footnote, summary key,
  and validation assertion must agree. A chart labelled YoY but rendered as an
  index is worse than a missing chart because it creates false confidence.
- When adding a better momentum version of a series, consider keeping the level
  only if it answers a different question. Otherwise the dashboard becomes busy
  without becoming smarter.

## 5. Data Quality And Freshness

- "Latest available" means latest valid source observation, not today's date.
  Official series can be monthly or quarterly and naturally lag by release
  calendar. Validate freshness against frequency and release expectations.
- Use quality statuses honestly:
  `verified` for direct official or strongly validated data, `watch` for mirrors
  or sources with known lag/schema risk, `low_confidence` for weak matches, and
  `unavailable` for explicit gaps.
- Do not hide data problems. Footnotes and quality badges are better than
  beautiful but misleading charts.
- If a fallback returns too few charts or suspiciously stale data, fail the
  build or preserve previous output rather than overwriting the dashboard with a
  degraded page.
- After changing configs, inspect the generated summary JSON, not only the HTML.
  The summary feeds archive cards and is often where stale headline values show
  up first.

## 6. Validation Patterns

- Add validation assertions whenever adding important indicators. Assert chart
  IDs, chart counts, Plotly plot counts, summary keys, and source footnote tokens.
- For country pages, verify:
  chart-card count equals Plotly div count equals `Plotly.newPlot` count;
  chart IDs are unique; required bilingual titles render; and `Official Data
  Gaps` remains present.
- For the archive, verify country card totals such as `92/92` or `164/164` and
  root links to every generated dashboard.
- Keep `make validate` as the gate before every commit. If an assertion feels
  annoying, it is probably protecting the live dashboard from a regression we
  have already seen.

## 7. UI And Layout

- Keep the UK, US, China, and CE4 pages visually aligned. The preferred chart
  layout is the CE4-style two-column desktop grid with readable card spacing,
  not dense multi-column chart packing.
- Keep Plotly modebar behavior consistent across dashboards unless there is a
  deliberate reason to remove it.
- Data-quality notes should be visible but restrained: concise footnotes,
  badges, or section notes are preferable to long warning blocks that overpower
  the charts.
- Bilingual UI should switch languages rather than rendering English and Chinese
  at the same time.

## 8. Common Maintenance Checklist

- Before editing: read `AGENTS.md`, this file, `README.md`, and any relevant
  country config or generator.
- After editing data configs or generators: run the specific country builder
  first, inspect the summary JSON, then run the full build.
- Before commit: run `make validate`, `git diff --check`, and a secret scan.
- After push: wait for GitHub Pages `built`, then run live smoke tests with a
  cache-busting query string.
- If a source cannot be automated reliably, document the gap and either keep a
  transparent quality flag or drop the indicator if it is not decision-useful.
