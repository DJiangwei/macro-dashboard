#!/usr/bin/env sh
set -eu
export PATH="/opt/homebrew/bin:$PATH"

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
  echo "gh not found; waiting for GitHub Pages deployment for $COMMIT..."
  ATTEMPT=0
  while [ "$ATTEMPT" -lt 30 ]; do
    if curl -sL "https://djiangwei.github.io/macro-dashboard/output/poland.html?v=$COMMIT" | rg -q "Poland Dashboard"; then
      echo "Pages build live for $COMMIT."
      break
    fi
    ATTEMPT=$((ATTEMPT + 1))
    sleep 5
  done
fi

echo "Running online smoke tests..."
curl -L "https://djiangwei.github.io/macro-dashboard/?v=$COMMIT" | rg -n "Macro Dashboard|Macro Workbench|dashboard_archive_summary.json"
curl -L "https://djiangwei.github.io/macro-dashboard/output/index.html?v=$COMMIT" | rg -n "Macro Dashboard|Macro Workbench|china.html|euro_area.html|japan.html|south_africa.html|uk.html|us.html|turkey.html|hong_kong.html|south_korea.html|taiwan.html|kazakhstan.html|uzbekistan.html|egypt.html|nigeria.html"
curl -L "https://djiangwei.github.io/macro-dashboard/output/macro_workbench_summary.json?v=$COMMIT" | rg -n "macro-workbench-v1|phase_coverage|heatmap|reer_valuation_monitor"
curl -L "https://djiangwei.github.io/macro-dashboard/output/release_monitor.json?v=$COMMIT" | rg -n "items"
curl -L "https://djiangwei.github.io/macro-dashboard/output/core_coverage_matrix.json?v=$COMMIT" | rg -n "core-coverage-v1|concept_count|priorities"
curl -L "https://djiangwei.github.io/macro-dashboard/output/source_health.json?v=$COMMIT" | rg -n "source-health-v1|circuit_breaker|countries"
curl -L "https://djiangwei.github.io/macro-dashboard/output/cee_canonical_frame.json?v=$COMMIT" | rg -n "cee-canonical-v2|series"
curl -L "https://djiangwei.github.io/macro-dashboard/output/china_canonical_frame.json?v=$COMMIT" | rg -n "data-first-canonical-v2|series"
curl -L "https://djiangwei.github.io/macro-dashboard/output/euro_area_canonical_frame.json?v=$COMMIT" | rg -n "data-first-canonical-v2|series"
curl -L "https://djiangwei.github.io/macro-dashboard/output/uk_canonical_frame.json?v=$COMMIT" | rg -n "data-first-canonical-v2|series"
curl -L "https://djiangwei.github.io/macro-dashboard/output/us_canonical_frame.json?v=$COMMIT" | rg -n "data-first-canonical-v2|series"
curl -L "https://djiangwei.github.io/macro-dashboard/output/japan_canonical_frame.json?v=$COMMIT" | rg -n "data-first-canonical-v2|series"
curl -L "https://djiangwei.github.io/macro-dashboard/output/south_africa_canonical_frame.json?v=$COMMIT" | rg -n "data-first-canonical-v2|series"
curl -L "https://djiangwei.github.io/macro-dashboard/output/turkey_canonical_frame.json?v=$COMMIT" | rg -n "data-first-canonical-v2|series"
curl -L "https://djiangwei.github.io/macro-dashboard/output/hong_kong_canonical_frame.json?v=$COMMIT" | rg -n "data-first-canonical-v2|series"
curl -L "https://djiangwei.github.io/macro-dashboard/output/south_korea_canonical_frame.json?v=$COMMIT" | rg -n "data-first-canonical-v2|series"
curl -L "https://djiangwei.github.io/macro-dashboard/output/taiwan_canonical_frame.json?v=$COMMIT" | rg -n "data-first-canonical-v2|series"
curl -L "https://djiangwei.github.io/macro-dashboard/output/kazakhstan_canonical_frame.json?v=$COMMIT" | rg -n "data-first-canonical-v2|series"
curl -L "https://djiangwei.github.io/macro-dashboard/output/uzbekistan_canonical_frame.json?v=$COMMIT" | rg -n "data-first-canonical-v2|series"
curl -L "https://djiangwei.github.io/macro-dashboard/output/egypt_canonical_frame.json?v=$COMMIT" | rg -n "data-first-canonical-v2|series"
curl -L "https://djiangwei.github.io/macro-dashboard/output/nigeria_canonical_frame.json?v=$COMMIT" | rg -n "data-first-canonical-v2|series"
curl -L "https://djiangwei.github.io/macro-dashboard/output/hungary.html?v=$COMMIT" | rg -n "Hungary Dashboard|Core 48|chart-financial_stability-bank_car"
curl -L "https://djiangwei.github.io/macro-dashboard/output/poland.html?v=$COMMIT" | rg -n "Poland Dashboard|Core 48|chart-financial_stability-bank_car"
curl -L "https://djiangwei.github.io/macro-dashboard/output/czechia.html?v=$COMMIT" | rg -n "Czechia Dashboard|Core 48|chart-financial_stability-bank_car"
curl -L "https://djiangwei.github.io/macro-dashboard/output/romania.html?v=$COMMIT" | rg -n "Romania Dashboard|Core 48|chart-financial_stability-bank_car"
curl -L "https://djiangwei.github.io/macro-dashboard/output/china.html?v=$COMMIT" | rg -n "China Dashboard|Core 48|Official Data Gaps|chart-real_gdp_growth"
curl -L "https://djiangwei.github.io/macro-dashboard/output/euro_area.html?v=$COMMIT" | rg -n "Euro Area Dashboard|Core 48|Official Data Gaps|chart-real_gdp_growth"
curl -L "https://djiangwei.github.io/macro-dashboard/output/uk.html?v=$COMMIT" | rg -n "UK Dashboard|Core 48|Official Data Gaps|chart-real_gdp_qoq"
curl -L "https://djiangwei.github.io/macro-dashboard/output/us.html?v=$COMMIT" | rg -n "US Dashboard|Core 48|Official Data Gaps|chart-real_gdp_growth"
curl -L "https://djiangwei.github.io/macro-dashboard/output/japan.html?v=$COMMIT" | rg -n "Japan Dashboard|Core 48|Official Data Gaps|chart-real_gdp_growth"
curl -L "https://djiangwei.github.io/macro-dashboard/output/south_africa.html?v=$COMMIT" | rg -n "South Africa Dashboard|Core 48|Official Data Gaps|chart-real_gdp_growth"
curl -L "https://djiangwei.github.io/macro-dashboard/output/turkey.html?v=$COMMIT" | rg -n "Turkey Dashboard|Core 48|Official Data Gaps|chart-real_gdp_growth"
curl -L "https://djiangwei.github.io/macro-dashboard/output/hong_kong.html?v=$COMMIT" | rg -n "Hong Kong Dashboard|Core 48|Official Data Gaps|chart-real_gdp_growth"
curl -L "https://djiangwei.github.io/macro-dashboard/output/south_korea.html?v=$COMMIT" | rg -n "South Korea Dashboard|Core 48|Official Data Gaps|chart-real_gdp_growth"
curl -L "https://djiangwei.github.io/macro-dashboard/output/taiwan.html?v=$COMMIT" | rg -n "Taiwan Dashboard|Core 48|Official Data Gaps|chart-real_gdp_yoy"
curl -L "https://djiangwei.github.io/macro-dashboard/output/kazakhstan.html?v=$COMMIT" | rg -n "Kazakhstan Dashboard|Core 48|Official Data Gaps|chart-real_gdp_growth"
curl -L "https://djiangwei.github.io/macro-dashboard/output/uzbekistan.html?v=$COMMIT" | rg -n "Uzbekistan Dashboard|Core 48|Official Data Gaps|chart-real_gdp_growth"
curl -L "https://djiangwei.github.io/macro-dashboard/output/egypt.html?v=$COMMIT" | rg -n "Egypt Dashboard|Core 48|Official Data Gaps|chart-real_gdp_growth"
curl -L "https://djiangwei.github.io/macro-dashboard/output/nigeria.html?v=$COMMIT" | rg -n "Nigeria Dashboard|Core 48|Official Data Gaps|chart-real_gdp_growth"
curl -L "https://djiangwei.github.io/macro-dashboard/output/chart_studio.html?v=$COMMIT" | rg -n "Macro Chart Studio|chart_studio_catalog.json"
curl -L "https://djiangwei.github.io/macro-dashboard/output/chart_studio_catalog.json?v=$COMMIT" | rg -n "countries|series"
curl -L "https://djiangwei.github.io/macro-dashboard/output/my_dashboard.html?v=$COMMIT" | rg -n "My Macro Dashboard|my_dashboard"
curl -L "https://djiangwei.github.io/macro-dashboard/output/policy_tracker.html?v=$COMMIT" | rg -n "Central Bank Policy|policy_tracker"
