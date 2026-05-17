#!/usr/bin/env sh
set -eu

ROOT="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
cd "$ROOT"

if [ "$#" -lt 1 ]; then
  echo "Usage: scripts/publish_dashboard.sh \"commit message\""
  exit 2
fi

MESSAGE="$1"

scripts/uv_project.sh sync
make doctor
make build-v4
make validate

git add \
  .gitignore \
  .python-version \
  AGENTS.md \
  Makefile \
  README.md \
  pyproject.toml \
  requirements.txt \
  uv.lock \
  build_v4.py \
  config/indicator_manifest_48.yaml \
  config/manual_indicators.yaml \
  src/country_primer/data_fetcher.py \
  scripts/doctor_env.py \
  scripts/publish_dashboard.sh \
  scripts/uv_project.sh \
  output/*_v4.html

if git diff --cached --quiet; then
  echo "No changes to commit."
else
  git commit -m "$MESSAGE"
  git push
fi

make publish-check
