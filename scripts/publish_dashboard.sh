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
  NEXT_PHASE_PLAN.md \
  README.md \
  SOURCE_DISCOVERY_MATRIX.md \
  pyproject.toml \
  requirements.txt \
  uv.lock \
  build_v4.py \
  config/indicator_manifest_48.yaml \
  config/manual_indicators.yaml \
  src/country_primer/data_fetcher.py \
  src/country_primer/fetch.py \
  scripts/doctor_env.py \
  scripts/publish_dashboard.sh \
  scripts/proxy_report.py \
  scripts/uv_project.sh \
  output/*_v4.html

if git diff --cached --quiet; then
  echo "No changes to commit."
else
  git commit -m "$MESSAGE"
  git push
fi

COMMIT="$(git rev-parse HEAD)"

if command -v gh >/dev/null 2>&1; then
  echo "Waiting for GitHub Pages build for $COMMIT..."
  ATTEMPT=0
  while [ "$ATTEMPT" -lt 30 ]; do
    STATUS="$(gh api repos/DJiangwei/macro-dashboard/pages/builds/latest --jq '.status' 2>/dev/null || echo unknown)"
    BUILD_COMMIT="$(gh api repos/DJiangwei/macro-dashboard/pages/builds/latest --jq '.commit' 2>/dev/null || echo unknown)"
    ERROR="$(gh api repos/DJiangwei/macro-dashboard/pages/builds/latest --jq '.error.message // empty' 2>/dev/null || true)"
    echo "Pages status: $STATUS ($BUILD_COMMIT)"
    if [ "$STATUS" = "built" ] && [ "$BUILD_COMMIT" = "$COMMIT" ]; then
      break
    fi
    if [ "$STATUS" = "errored" ]; then
      echo "GitHub Pages build failed: $ERROR"
      exit 1
    fi
    ATTEMPT=$((ATTEMPT + 1))
    sleep 5
  done
else
  echo "gh not found; skipping Pages build polling."
fi

echo "Running online smoke tests..."
curl -L "https://djiangwei.github.io/macro-dashboard/?v=$COMMIT" | rg -n "v4 Framework|Hungary|macro-dashboard"
curl -L "https://djiangwei.github.io/macro-dashboard/output/hungary_2026Q2_v4.html?v=$COMMIT" | rg -n "Hungary Dashboard|IMF Assessing Reserve Adequacy|chart-financial_stability-bank_car"
curl -L "https://djiangwei.github.io/macro-dashboard/output/poland_2026Q2_v4.html?v=$COMMIT" | rg -n "Poland Dashboard|IMF Assessing Reserve Adequacy|chart-financial_stability-bank_car"
curl -L "https://djiangwei.github.io/macro-dashboard/output/czechia_2026Q2_v4.html?v=$COMMIT" | rg -n "Czechia Dashboard|IMF Assessing Reserve Adequacy|chart-financial_stability-bank_car"
curl -L "https://djiangwei.github.io/macro-dashboard/output/romania_2026Q2_v4.html?v=$COMMIT" | rg -n "Romania Dashboard|IMF Assessing Reserve Adequacy|chart-financial_stability-bank_car"
