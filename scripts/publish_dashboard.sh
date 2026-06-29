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
curl -L "https://djiangwei.github.io/macro-dashboard/output/index.html?v=$COMMIT" | rg -n "Macro Dashboard Archive|Macro Workbench|china_2026Q2_v1.html|uk_2026Q2_v1.html|us_2026Q2_v1.html"
curl -L "https://djiangwei.github.io/macro-dashboard/output/macro_workbench_summary.json?v=$COMMIT" | rg -n "macro-workbench-v1|phase_coverage|heatmap"
curl -L "https://djiangwei.github.io/macro-dashboard/output/release_monitor.json?v=$COMMIT" | rg -n "items"
curl -L "https://djiangwei.github.io/macro-dashboard/output/china_canonical_frame.json?v=$COMMIT" | rg -n "data-first-canonical-v1|records"
curl -L "https://djiangwei.github.io/macro-dashboard/output/uk_canonical_frame.json?v=$COMMIT" | rg -n "data-first-canonical-v1|records"
curl -L "https://djiangwei.github.io/macro-dashboard/output/us_canonical_frame.json?v=$COMMIT" | rg -n "data-first-canonical-v1|records"
curl -L "https://djiangwei.github.io/macro-dashboard/output/hungary_2026Q2_v4.html?v=$COMMIT" | rg -n "Hungary Dashboard|IMF Assessing Reserve Adequacy|chart-financial_stability-bank_car"
curl -L "https://djiangwei.github.io/macro-dashboard/output/poland_2026Q2_v4.html?v=$COMMIT" | rg -n "Poland Dashboard|IMF Assessing Reserve Adequacy|chart-financial_stability-bank_car"
curl -L "https://djiangwei.github.io/macro-dashboard/output/czechia_2026Q2_v4.html?v=$COMMIT" | rg -n "Czechia Dashboard|IMF Assessing Reserve Adequacy|chart-financial_stability-bank_car"
curl -L "https://djiangwei.github.io/macro-dashboard/output/romania_2026Q2_v4.html?v=$COMMIT" | rg -n "Romania Dashboard|IMF Assessing Reserve Adequacy|chart-financial_stability-bank_car"
curl -L "https://djiangwei.github.io/macro-dashboard/output/china_2026Q2_v1.html?v=$COMMIT" | rg -n "China Dashboard|Official Data Gaps|chart-real_gdp_growth"
curl -L "https://djiangwei.github.io/macro-dashboard/output/uk_2026Q2_v1.html?v=$COMMIT" | rg -n "UK Dashboard|Official Data Gaps|chart-real_gdp_qoq"
curl -L "https://djiangwei.github.io/macro-dashboard/output/us_2026Q2_v1.html?v=$COMMIT" | rg -n "US Dashboard|Official Data Gaps|chart-real_gdp_growth"
