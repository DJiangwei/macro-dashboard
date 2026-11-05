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
scripts/uv_project.sh run python scripts/publish_smoke.py --version "$COMMIT"
