# Agent Operating Guide

Use this file as the first stop for any coding agent working in this repo.

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
containers remain, and runs `git diff --check`.

`make proxy-report` prints the transparent proxy count and proxy indicator list
for each CEE-4 country.

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
