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

git add .

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
curl -L "https://djiangwei.github.io/macro-dashboard/?v=$COMMIT" | rg -n "Macro Dashboard Archive|Macro Workbench|dashboard_archive_summary.json"
curl -L "https://djiangwei.github.io/macro-dashboard/output/index.html?v=$COMMIT" | rg -n "Macro Dashboard Archive|Macro Workbench|china.html|japan.html|south_africa.html|uk.html|us.html"
curl -L "https://djiangwei.github.io/macro-dashboard/output/macro_workbench_summary.json?v=$COMMIT" | rg -n "macro-workbench-v1|phase_coverage|heatmap"
curl -L "https://djiangwei.github.io/macro-dashboard/output/release_monitor.json?v=$COMMIT" | rg -n "items"
curl -L "https://djiangwei.github.io/macro-dashboard/output/core_coverage_matrix.json?v=$COMMIT" | rg -n "core-coverage-v1|concept_count|priorities"
curl -L "https://djiangwei.github.io/macro-dashboard/output/source_health.json?v=$COMMIT" | rg -n "source-health-v1|circuit_breaker|countries"
curl -L "https://djiangwei.github.io/macro-dashboard/output/cee_canonical_frame.json?v=$COMMIT" | rg -n "cee-canonical-v2|series"
curl -L "https://djiangwei.github.io/macro-dashboard/output/china_canonical_frame.json?v=$COMMIT" | rg -n "data-first-canonical-v2|series"
curl -L "https://djiangwei.github.io/macro-dashboard/output/uk_canonical_frame.json?v=$COMMIT" | rg -n "data-first-canonical-v2|series"
curl -L "https://djiangwei.github.io/macro-dashboard/output/us_canonical_frame.json?v=$COMMIT" | rg -n "data-first-canonical-v2|series"
curl -L "https://djiangwei.github.io/macro-dashboard/output/japan_canonical_frame.json?v=$COMMIT" | rg -n "data-first-canonical-v2|series"
curl -L "https://djiangwei.github.io/macro-dashboard/output/south_africa_canonical_frame.json?v=$COMMIT" | rg -n "data-first-canonical-v2|series"
curl -L "https://djiangwei.github.io/macro-dashboard/output/hungary.html?v=$COMMIT" | rg -n "Hungary Dashboard|Core 48|chart-financial_stability-bank_car"
curl -L "https://djiangwei.github.io/macro-dashboard/output/poland.html?v=$COMMIT" | rg -n "Poland Dashboard|Core 48|chart-financial_stability-bank_car"
curl -L "https://djiangwei.github.io/macro-dashboard/output/czechia.html?v=$COMMIT" | rg -n "Czechia Dashboard|Core 48|chart-financial_stability-bank_car"
curl -L "https://djiangwei.github.io/macro-dashboard/output/romania.html?v=$COMMIT" | rg -n "Romania Dashboard|Core 48|chart-financial_stability-bank_car"
curl -L "https://djiangwei.github.io/macro-dashboard/output/china.html?v=$COMMIT" | rg -n "China Dashboard|Core 48|Official Data Gaps|chart-real_gdp_growth"
curl -L "https://djiangwei.github.io/macro-dashboard/output/uk.html?v=$COMMIT" | rg -n "UK Dashboard|Core 48|Official Data Gaps|chart-real_gdp_qoq"
curl -L "https://djiangwei.github.io/macro-dashboard/output/us.html?v=$COMMIT" | rg -n "US Dashboard|Core 48|Official Data Gaps|chart-real_gdp_growth"
curl -L "https://djiangwei.github.io/macro-dashboard/output/japan.html?v=$COMMIT" | rg -n "Japan Dashboard|Core 48|Official Data Gaps|chart-real_gdp_growth"
curl -L "https://djiangwei.github.io/macro-dashboard/output/south_africa.html?v=$COMMIT" | rg -n "South Africa Dashboard|Core 48|Official Data Gaps|chart-real_gdp_growth"
