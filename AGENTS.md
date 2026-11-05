# Agent Operating Guide

Use this file as the first stop for any coding agent working in this repo.

Before making dashboard changes, also read `PROJECT_LESSONS.md`. It records
hard-earned operating lessons about publishing, source hierarchy, chart
transform logic, freshness checks, and secret handling.

## Environment

- Do not rely on the machine's global Python.
- Use the project-local uv wrapper:

```bash
scripts/uv_project.sh sync
make doctor
```

The wrapper keeps uv cache, Python installs, and the virtual environment inside
this repo:

- `.venv/`
- `.uv-cache/`
- `.uv-python/`

These directories are intentionally ignored by git.

## Common Commands

```bash
make build-v4
make validate
make publish-check
make publish MSG="clear commit message"
make proxy-report
```

`make validate` must pass before committing. It checks Python compilation,
prints each generated v4 country page's chart-shell count, confirms no empty chart
containers remain, validates the China/Japan/South Africa/UK/US canonical
data-frame exports, checks the macro workbench JSON artifacts, and runs
`git diff --check`.

`make build-v4` is the full synchronized build. It rebuilds CE4, China, Japan,
South Africa, UK, and US pages, then refreshes `DATA_SOURCE_CATALOG.md`,
`DATA_FRESHNESS_AUDIT.md`,
`output/freshness_audit.json`, `output/macro_workbench_summary.json`,
`output/release_monitor.json`, `output/what_changed.json`,
`output/data_gap_backlog.json`, and both archive entry points.

`make proxy-report` prints the transparent proxy count and proxy indicator list
for each CEE-4 country from generated archive/catalog artifacts. Use
`make proxy-report-live` only when you explicitly want to refetch the full CE4
pipeline.

Before replacing or deleting proxy indicators, read `PROXY_REVIEW.md`. It
records the current keep/replace/reframe/manual/remove recommendations so agents
do not re-triage the same dashboard gaps from scratch.

## Publishing Discipline

After dashboard changes:

```bash
make publish MSG="<clear message>"
```

The publish script rebuilds, validates, commits, pushes, polls the GitHub Pages
build when `gh` is available, and runs cache-busted online smoke tests. The work
is not complete until the GitHub Pages URLs show the new content.

The publish script intentionally stages the full repo after validation. Do not
replace that with a narrow allow-list unless the allow-list includes the data
catalog, freshness audit, archive summaries, canonical frames, and workbench
JSON outputs; otherwise the live index can drift away from country pages.

## Scope Registry

Every generated page is registered in `config/scopes.yaml` (id, slug, names,
currency, headline series, pipeline). Data-first pages are built by
`scripts/build_scope.py` (`--all`, one or more scope ids, `--snapshot`), which
fetches through the global fetcher registry in `src/country_primer/fetchers.py`.
Do not add per-country builder scripts; add a registry entry and an indicator
YAML instead. When refactoring the build, run `make rebuild-ui` and then
`make golden-diff`: it compares generated outputs with `HEAD` ignoring
timestamps and must report no differences unless data was meant to change.

## Adding a Country

A new data-first country is two files; no code changes:

1. An entry in `config/scopes.yaml` (id, slug, names, flag, region, currency,
   central bank, headline series).
2. `config/countries/<slug>.yaml` listing `templates` (see
   `config/templates/`: `sections_core`, `imf_baseline`, `bis_baseline`,
   `wb_structural`, `oecd_mirror`, `fred_fx`) and their `params`. Native
   series go under `indicators:`; an id that matches a template id replaces
   it, and `drop:` removes template ids. Tag core concepts with `concept:`.

Then refresh it once (`scripts/uv_project.sh run python scripts/build_scope.py
<ID>`), run `make rebuild-ui` and `make validate`. Probe template series first:
some FRED/OECD mirrors are discontinued for some countries, and those belong
under `data_gaps`, not on the page. India (`config/countries/india.yaml`) is
the reference example.

## Indicator Manifest

The v4 dashboard's canonical 48 indicators live in:

`config/indicator_manifest_48.yaml`

Change labels, source notes, quality status, chart type, section assignment, or
peer-overlay behavior there first. `src/country_primer/data_fetcher.py` loads
this YAML and only falls back to its embedded manifest if the file is missing.

## Scope

This repo lives at:

`/Users/jiangwei/Claude/Country_Primer`

Do not write outside this repo unless the user explicitly authorizes it.
