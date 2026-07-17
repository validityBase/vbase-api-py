#!/usr/bin/env python3
"""Bitwarden env helper.

Commands:
  btenv env | init
  btenv dump [.env]
  btenv help
"""

from __future__ import annotations

import os
import re
import shlex
import sys
from pathlib import Path

from bw_sm.core import BitwardenSecretManager

ROOT = Path(__file__).resolve().parents[2]
OPS_DIR = ROOT / "ops"
PROJECT_SETTINGS_FILE = OPS_DIR / ".bw-project"
ENV_KEY_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")

DEFAULT_PROJECT_NAME = "vbase-django-tools-cypress-runner-stg"
DEFAULT_ORGANIZATION_ID = "f8c92883-7bb9-4d29-a2d4-b137014f77af"
HELP_TEXT = """
Usage:

  # Setup alias
  alias btenv="python ops/scripts/btenv.py"

  btenv env
  btenv init
      Print shell exports for project settings and all project secrets.
      Use with eval:
      eval "$(btenv env)"

  btenv dump [.env]
      Write project secrets to a dotenv file (.env by default).

  btenv help
      Show this help text.

Expected environment:
  BWS_ACCESS_TOKEN must already be exported.

Project settings source priority:
  1) BW_PROJECT / BW_ORG_ID from environment
  2) BW_PROJECT / BW_ORG_ID in ops/.bw-project
  3) built-in defaults
"""


def usage() -> None:
    """Print CLI usage instructions."""
    print(HELP_TEXT)


def parse_bw_project_file() -> dict[str, str]:
    """Parse key/value settings from ops/.bw-project."""
    if not PROJECT_SETTINGS_FILE.exists():
        return {}

    values: dict[str, str] = {}
    for raw_line in PROJECT_SETTINGS_FILE.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()

        if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
            value = value[1:-1]

        values[key] = value

    return values


def resolve_project_settings() -> tuple[str, str]:
    """Resolve project name and organization id from env/file/defaults."""
    file_values = parse_bw_project_file()

    project_name = (
        os.environ.get("BW_PROJECT", "").strip()
        or file_values.get("BW_PROJECT", "").strip()
        or file_values.get("PROJECT_NAME", "").strip()
        or DEFAULT_PROJECT_NAME
    )
    organization_id = (
        os.environ.get("BW_ORG_ID", "").strip()
        or file_values.get("BW_ORG_ID", "").strip()
        or file_values.get("ORGANIZATION_ID", "").strip()
        or DEFAULT_ORGANIZATION_ID
    )

    return project_name, organization_id


def require_access_token() -> str:
    """Return BWS token, failing fast if missing."""
    token = os.environ.get("BWS_ACCESS_TOKEN", "").strip()
    if not token:
        raise SystemExit("BWS_ACCESS_TOKEN is not set. Export it before running btenv.")
    return token


def get_manager() -> BitwardenSecretManager:
    """Build a configured BitwardenSecretManager instance."""
    access_token = require_access_token()
    project_name, organization_id = resolve_project_settings()

    manager_kwargs = {
        "bw_token": access_token,
        "project_name": project_name,
        "organization_id": organization_id,
    }
    return BitwardenSecretManager(**manager_kwargs)


def get_project_secrets() -> tuple[str, str, dict[str, str]]:
    """Fetch project metadata and secret key/value mapping."""
    manager = get_manager()
    project = manager.resolve_project()
    secrets = manager.get_project_secrets()
    return project.name, project.id, secrets


def iter_shell_safe_secrets(secrets: dict[str, str]) -> list[tuple[str, str]]:
    """Filter and return shell-safe secret key/value pairs."""
    safe_items: list[tuple[str, str]] = []

    for key in sorted(secrets):
        if not ENV_KEY_PATTERN.match(key):
            print(f"Skipping non-shell env key: {key!r}", file=sys.stderr)
            continue
        safe_items.append((key, secrets[key]))

    return safe_items


def print_env_exports() -> int:
    """Print shell export commands for project settings and secrets."""
    project_name_setting, organization_id = resolve_project_settings()
    resolved_project_name, _project_id, secrets = get_project_secrets()

    print(f"export BW_PROJECT={shlex.quote(project_name_setting)}")
    print(f"export BW_ORG_ID={shlex.quote(organization_id)}")
    print(f"export PROJECT_NAME={shlex.quote(resolved_project_name)}")

    for key, value in iter_shell_safe_secrets(secrets):
        print(f"export {key}={shlex.quote(value)}")

    return 0


def dump_env(output_file: str) -> int:
    """Write project secrets to a dotenv file."""
    _project_name, _project_id, secrets = get_project_secrets()
    lines = []

    for key, value in iter_shell_safe_secrets(secrets):
        escaped = (
            value.replace("\\", "\\\\")
            .replace('"', '\\"')
            .replace("\n", "\\n")
        )
        lines.append(f'{key}="{escaped}"')

    output_path = Path(output_file)
    if output_path.exists():
        output_path.chmod(0o600)
    file_descriptor = os.open(
        output_path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600
    )
    with os.fdopen(file_descriptor, "w", encoding="utf-8") as output:
        output.write("\n".join(lines) + "\n")
    output_path.chmod(0o600)

    print(f"Wrote {output_file}")
    return 0


def main() -> int:
    """CLI entry point."""
    args = sys.argv[1:]

    if not args:
        usage()
        return 1

    cmd = args[0]
    if cmd in {"help", "-h", "--help"}:
        if len(args) != 1:
            usage()
            return 1
        usage()
        return 0

    if cmd in {"env", "init"}:
        if len(args) != 1:
            usage()
            return 1
        return print_env_exports()

    if cmd == "dump":
        if len(args) > 2:
            usage()
            return 1
        output_file = args[1] if len(args) == 2 else ".env"
        return dump_env(output_file)

    usage()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
