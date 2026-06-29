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
containers remain, validates the China/UK/US canonical data-frame exports,
checks the macro workbench JSON artifacts, and runs `git diff --check`.

`make build-v4` is the full synchronized build. It rebuilds CE4, China, UK, and
US pages, then refreshes `DATA_SOURCE_CATALOG.md`, `DATA_FRESHNESS_AUDIT.md`,
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
