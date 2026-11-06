#!/usr/bin/env sh
set -eu

ROOT="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
export UV_CACHE_DIR="$ROOT/.uv-cache"
export UV_PYTHON_INSTALL_DIR="$ROOT/.uv-python"

if [ -f "$ROOT/.env.local" ]; then
  # shellcheck source=scripts/env_file.sh
  . "$ROOT/scripts/env_file.sh"
  load_env_file "$ROOT/.env.local"
fi

if command -v uv >/dev/null 2>&1; then
  UV_BIN="$(command -v uv)"
elif [ -x "$HOME/.local/bin/uv" ]; then
  UV_BIN="$HOME/.local/bin/uv"
else
  echo "uv is required. Install it from https://docs.astral.sh/uv/." >&2
  exit 127
fi

exec "$UV_BIN" --directory "$ROOT" "$@"
