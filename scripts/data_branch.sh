#!/usr/bin/env sh
# Persistent data for GitHub Pages option C (see docs/PAGES_DEPLOYMENT.md).
#
#   scripts/data_branch.sh pull                 # overlay the data branch onto this checkout
#   scripts/data_branch.sh push "message"       # commit this checkout's data files to the data branch
#   scripts/data_branch.sh bootstrap            # create the data branch (refuses if it exists)
#   scripts/data_branch.sh files                # list the files a push would publish
#
# The data branch holds only build state: canonical frames, summaries and the
# other JSON artifacts in output/, data/*.json caches, and data/accumulated/
# (history of short-window sources, which cannot be refetched: a push that
# would drop any of its dates is refused unless ALLOW_ACCUMULATED_SHRINK=1). Pages are always
# rebuilt from it with `make rebuild-ui`; HTML is never stored there.
set -eu

ROOT="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
cd "$ROOT"
BRANCH="${DATA_BRANCH:-data}"
REMOTE="${DATA_REMOTE:-origin}"

data_files() {
  # Tracked or generated data files in this checkout, one per line.
  ls output/*.json output/*.md data/*.json data/accumulated/*.json 2>/dev/null || true
}

copy_into() {
  target="$1"
  data_files | tar -cf - -T - | tar -xf - -C "$target"
}

remote_exists() {
  git ls-remote --exit-code --heads "$REMOTE" "$BRANCH" >/dev/null 2>&1
}

cmd="${1:-}"
case "$cmd" in
  pull)
    if ! remote_exists; then
      echo "No '$BRANCH' branch on $REMOTE; keeping the data in this checkout." >&2
      exit 0
    fi
    git fetch --quiet --depth=1 "$REMOTE" "$BRANCH"
    git archive FETCH_HEAD -- output data | tar -xf - -C "$ROOT"
    echo "Overlaid $REMOTE/$BRANCH ($(git rev-parse --short FETCH_HEAD)) onto output/ and data/."
    ;;
  push)
    message="${2:-Update dashboard data}"
    if ! remote_exists; then
      echo "No '$BRANCH' branch on $REMOTE; run 'scripts/data_branch.sh bootstrap' first." >&2
      exit 1
    fi
    tmp="$(mktemp -d)"
    trap 'git worktree remove --force "$tmp" >/dev/null 2>&1 || true; rm -rf "$tmp"' EXIT
    git fetch --quiet --depth=1 "$REMOTE" "$BRANCH"
    git worktree add --quiet --detach "$tmp" FETCH_HEAD
    if [ -d "$tmp/data/accumulated" ] && [ "${ALLOW_ACCUMULATED_SHRINK:-0}" != "1" ]; then
      python3 "$ROOT/scripts/accumulated_guard.py" "$tmp/data/accumulated" "$ROOT/data/accumulated"
    fi
    # Replace the data set wholesale so artifacts that are no longer generated disappear.
    git -C "$tmp" rm -rq --ignore-unmatch -- output data
    mkdir -p "$tmp/output" "$tmp/data"
    copy_into "$tmp"
    git -C "$tmp" add -A -- output data
    if git -C "$tmp" diff --cached --quiet; then
      echo "Data branch already up to date."
      exit 0
    fi
    git -C "$tmp" commit --quiet -m "$message"
    git -C "$tmp" push --quiet "$REMOTE" "HEAD:refs/heads/$BRANCH"
    echo "Pushed $(git -C "$tmp" rev-parse --short HEAD) to $REMOTE/$BRANCH."
    ;;
  bootstrap)
    if remote_exists; then
      echo "'$BRANCH' already exists on $REMOTE; nothing to do." >&2
      exit 1
    fi
    tmp="$(mktemp -d)"
    trap 'git worktree remove --force "$tmp" >/dev/null 2>&1 || true; rm -rf "$tmp"' EXIT
    git worktree add --quiet --detach "$tmp" HEAD
    git -C "$tmp" checkout --quiet --orphan "$BRANCH"
    git -C "$tmp" rm -rfq .
    mkdir -p "$tmp/output" "$tmp/data"
    copy_into "$tmp"
    cat > "$tmp/README.md" <<'README'
# Dashboard data branch

Build state for the macro dashboard: canonical frames, summaries and other
JSON artifacts (`output/`) and source caches (`data/`). Written by the
scheduled refresh; read by the Pages deploy, which rebuilds every page from
these files with `make rebuild-ui`. Do not commit code here.
README
    git -C "$tmp" add -A
    git -C "$tmp" commit --quiet -m "Bootstrap data branch from $(git rev-parse --short HEAD)"
    git -C "$tmp" push --quiet "$REMOTE" "HEAD:refs/heads/$BRANCH"
    echo "Created $REMOTE/$BRANCH from $(git rev-parse --short HEAD)."
    ;;
  files)
    data_files
    ;;
  *)
    echo "Usage: scripts/data_branch.sh pull | push [message] | bootstrap | files" >&2
    exit 2
    ;;
esac
