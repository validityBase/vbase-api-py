#!/usr/bin/env bash
set -euo pipefail

# Generic Bitwarden environment wrapper.
#
# This script keeps token lookup, dependency checks, GitHub log masking, and
# dotenv file handling in one place. Domain-specific scripts should call this
# wrapper with a project name and the environment variable that holds that
# project's Bitwarden machine access token.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
BTENV="${BTENV_SCRIPT:-$ROOT_DIR/ops/scripts/btenv.py}"
DEFAULT_ORG_ID="${BTENV_DEFAULT_ORG_ID:-f8c92883-7bb9-4d29-a2d4-b137014f77af}"

# Prefer the caller-selected Python, then the active/project venv, then system
# Python. The selected interpreter must have vbase-common's bw_sm installed.
resolve_python_bin() {
  if [ -n "${BTENV_PYTHON:-}" ]; then
    printf '%s\n' "$BTENV_PYTHON"
    return 0
  fi

  if [ -n "${VIRTUAL_ENV:-}" ] && [ -x "$VIRTUAL_ENV/bin/python" ]; then
    printf '%s\n' "$VIRTUAL_ENV/bin/python"
    return 0
  fi

  if [ -x "$ROOT_DIR/venv/bin/python" ]; then
    printf '%s\n' "$ROOT_DIR/venv/bin/python"
    return 0
  fi

  if command -v python3 >/dev/null 2>&1; then
    command -v python3
    return 0
  fi

  command -v python
}

PYTHON_BIN="$(resolve_python_bin)"

PROJECT_NAME=""
TOKEN_ENV=""
ORG_ID=""
OUTPUT_FILE=""
REMAINING_ARGS=()

usage() {
  cat <<'EOF'
Usage:
  ops/scripts/btenv.sh run --project <name> --token-env <env-var> [--org-id <id>] -- <command> [args...]
  ops/scripts/btenv.sh dump --project <name> --token-env <env-var> [--org-id <id>] --output <file>
  ops/scripts/btenv.sh env --project <name> --token-env <env-var> [--org-id <id>]

Expected environment:
  <env-var> must contain the Bitwarden machine access token for the selected
  project. The helper loads secrets through ops/scripts/btenv.py and vbase-common
  bw_sm.

Optional environment:
  BTENV_PYTHON=/path/to/python
  BTENV_SCRIPT=/path/to/btenv.py
  BW_ORG_ID=<organization-id>
  BTENV_DEFAULT_ORG_ID=<default-organization-id>
EOF
}

parse_common_args() {
  PROJECT_NAME="${BTENV_PROJECT:-}"
  TOKEN_ENV="${BTENV_TOKEN_ENV:-}"
  ORG_ID="${BTENV_ORG_ID:-${BW_ORG_ID:-$DEFAULT_ORG_ID}}"
  OUTPUT_FILE=""
  REMAINING_ARGS=()

  while [ "$#" -gt 0 ]; do
    case "$1" in
      --project)
        [ "$#" -ge 2 ] || die "--project requires a value."
        PROJECT_NAME="$2"
        shift 2
        ;;
      --token-env)
        [ "$#" -ge 2 ] || die "--token-env requires a value."
        TOKEN_ENV="$2"
        shift 2
        ;;
      --org-id)
        [ "$#" -ge 2 ] || die "--org-id requires a value."
        ORG_ID="$2"
        shift 2
        ;;
      --output)
        [ "$#" -ge 2 ] || die "--output requires a value."
        OUTPUT_FILE="$2"
        shift 2
        ;;
      --)
        shift
        REMAINING_ARGS=("$@")
        return 0
        ;;
      -*)
        die "Unknown option: $1"
        ;;
      *)
        REMAINING_ARGS=("$@")
        return 0
        ;;
    esac
  done
}

die() {
  echo "$1" >&2
  exit 1
}

# Validate the project selector and the env var that stores the project-scoped
# Bitwarden access token before running any command that could call Bitwarden.
require_project_context() {
  if [ -z "$PROJECT_NAME" ]; then
    die "Missing Bitwarden project. Pass --project or set BTENV_PROJECT."
  fi

  if [ -z "$TOKEN_ENV" ]; then
    die "Missing Bitwarden token env var name. Pass --token-env or set BTENV_TOKEN_ENV."
  fi

  if [ -z "${!TOKEN_ENV:-}" ]; then
    echo "Missing Bitwarden access token for $PROJECT_NAME." >&2
    echo "Export $TOKEN_ENV locally or configure the matching GitHub Actions secret." >&2
    exit 1
  fi
}

# btenv.py imports bw_sm from vbase-common; in CI that package is installed via
# requirements-private.txt after VBASE_COMMON_REPO_READ_TOKEN is configured.
require_btenv_deps() {
  if ! "$PYTHON_BIN" -c "import bw_sm" >/dev/null 2>&1; then
    cat >&2 <<EOF
Missing Python dependency: bw_sm.

Install the Bitwarden helper dependencies in the Python environment used by this command:

  $PYTHON_BIN -m pip install --require-hashes -r requirements/lock/e2e.txt
  VBASE_COMMON_REPO_READ_TOKEN="<github-token>" $PYTHON_BIN -m pip install --no-deps -r requirements-private.txt

You can also set BTENV_PYTHON=/path/to/python if you want to use a different environment.
EOF
    exit 1
  fi
}

# Run the Python helper with its expected environment names. Callers keep their
# own token variable names; btenv.py only needs BWS_ACCESS_TOKEN.
run_btenv_py() {
  local token_value
  token_value="${!TOKEN_ENV}"

  require_btenv_deps
  BWS_ACCESS_TOKEN="$token_value" BW_PROJECT="$PROJECT_NAME" BW_ORG_ID="$ORG_ID" "$PYTHON_BIN" "$BTENV" "$@"
}

add_github_mask() {
  local value="$1"

  value="${value//'%'/'%25'}"
  value="${value//$'\r'/'%0D'}"
  value="${value//$'\n'/'%0A'}"
  printf '::add-mask::%s\n' "$value"
}

# Mask values that were exported into the current process before the child
# command can echo them in GitHub Actions logs.
mask_exported_values() {
  local exports="$1"
  local line key value

  [ "${GITHUB_ACTIONS:-}" = "true" ] || return 0

  while IFS= read -r line; do
    case "$line" in
      export\ *=*) ;;
      *) continue ;;
    esac

    key="${line#export }"
    key="${key%%=*}"

    case "$key" in
      BW_PROJECT|BW_ORG_ID|PROJECT_NAME) continue ;;
    esac

    value="${!key-}"
    [ -n "$value" ] && add_github_mask "$value"
  done <<< "$exports"
}

# Dotenv output is used by Docker Compose. Mask each written value because
# Compose failures or debug output can otherwise reveal the generated file.
mask_env_file_values() {
  local env_file="$1"

  [ "${GITHUB_ACTIONS:-}" = "true" ] || return 0

  local line value
  while IFS= read -r line || [ -n "$line" ]; do
    case "$line" in
      *=*) ;;
      *) continue ;;
    esac

    value="${line#*=}"
    if [[ "$value" == \"*\" && "$value" == *\" ]]; then
      value="${value:1:${#value}-2}"
      value="${value//\\n/$'\n'}"
      value="${value//\\\"/\"}"
      value="${value//\\\\/\\}"
    fi

    [ -n "$value" ] && add_github_mask "$value"
  done < "$env_file"
}

command_env() {
  parse_common_args "$@"
  require_project_context
  run_btenv_py env
}

# Write a project dotenv file with private permissions, then mask every value
# for GitHub Actions. The file path is chosen by the caller.
command_dump() {
  parse_common_args "$@"
  require_project_context

  if [ -z "$OUTPUT_FILE" ]; then
    die "Missing output file. Pass --output <file>."
  fi

  run_btenv_py dump "$OUTPUT_FILE" >&2
  chmod 600 "$OUTPUT_FILE"
  mask_env_file_values "$OUTPUT_FILE"
}

# Load project secrets into this shell, mask them, then replace this process
# with the requested command so signal handling and exit codes stay natural.
command_run() {
  local env_exports

  parse_common_args "$@"
  require_project_context

  if [ "${#REMAINING_ARGS[@]}" -eq 0 ]; then
    die "Missing command to run after Bitwarden env is loaded."
  fi

  env_exports="$(run_btenv_py env)"
  eval "$env_exports"
  mask_exported_values "$env_exports"
  exec "${REMAINING_ARGS[@]}"
}

main() {
  local command="${1:-}"

  case "$command" in
    env)
      shift
      command_env "$@"
      ;;
    dump)
      shift
      command_dump "$@"
      ;;
    run)
      shift
      command_run "$@"
      ;;
    help|-h|--help)
      usage
      ;;
    *)
      usage >&2
      exit 1
      ;;
  esac
}

main "$@"
