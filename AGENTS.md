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
```

`make validate` must pass before committing. It checks Python compilation,
confirms each v4 country page has 48 chart shells, confirms no empty chart
containers remain, and runs `git diff --check`.

## Publishing Discipline

After dashboard changes:

```bash
git add <changed files>
git commit -m "<clear message>"
git push
make publish-check
```

The work is not complete until the GitHub Pages URLs show the new content.

## Scope

This repo lives at:

`/Users/jiangwei/Claude/Country_Primer`

Do not write outside this repo unless the user explicitly authorizes it.
