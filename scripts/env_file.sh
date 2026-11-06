# shellcheck shell=sh
# Load KEY=VALUE lines from a dotenv file literally, the way the Python loaders
# read it: no shell expansion (a "$" inside a token stays a "$"), spaces around
# "=" allowed, one pair of surrounding quotes removed, comments and blank lines
# skipped. Sourcing the file instead broke on such values, and the shell's
# error message printed part of the secret.
load_env_file() {
  while IFS= read -r line || [ -n "$line" ]; do
    line=$(printf '%s' "$line" | tr -d '\r' | sed 's/^[[:space:]]*//; s/^export[[:space:]][[:space:]]*//')
    case "$line" in
      '' | '#'*) continue ;;
      *=*) ;;
      *) continue ;;
    esac
    key=$(printf '%s' "${line%%=*}" | sed 's/[[:space:]]*$//')
    case "$key" in
      '' | [0-9]* | *[!A-Za-z0-9_]*) continue ;;
    esac
    value=$(printf '%s' "${line#*=}" | sed 's/^[[:space:]]*//; s/[[:space:]]*$//')
    case "$value" in
      \"*\") value=${value#\"}; value=${value%\"} ;;
      \'*\') value=${value#\'}; value=${value%\'} ;;
    esac
    export "$key=$value"
  done < "$1"
}
