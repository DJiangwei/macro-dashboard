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
```

`make validate` must pass before committing. It checks Python compilation,
confirms each v4 country page has 48 chart shells, confirms no empty chart
containers remain, and runs `git diff --check`.

## Publishing Discipline

After dashboard changes:

```bash
make publish MSG="<clear message>"
```

The work is not complete until the GitHub Pages URLs show the new content.

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
