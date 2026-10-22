"""Increment the package version and finalize Unreleased for a Release PR."""

import argparse
import datetime
import re
from pathlib import Path

from .validate_release import source_version


def next_version(current: str, bump: str) -> str:
    number = r"(0|[1-9][0-9]*)"
    if not re.fullmatch(rf"{number}\.{number}\.{number}", current):
        raise ValueError("Current version must be stable X.Y.Z.")
    if bump not in ("major", "minor", "patch"):
        raise ValueError("Choose a major, minor, or patch increment.")
    parts = list(map(int, current.split(".")))
    index = ("major", "minor", "patch").index(bump)
    parts[index] += 1
    parts[index + 1 :] = [0] * (2 - index)
    return ".".join(map(str, parts))


def prepare_release(root: Path, bump: str, date: datetime.date) -> str:
    current = source_version(root)
    version = next_version(current, bump)
    version_file = root / "src/vbase_api/_version.py"
    contents, count = re.subn(
        r"(?m)^__version__\s*=\s*(['\"])[^'\"\n]+\1[^\S\n]*$",
        f'__version__ = "{version}"',
        version_file.read_text(encoding="utf-8"),
    )
    if count != 1:
        raise ValueError("Expected a single plain __version__ assignment.")

    changelog_file = root / "CHANGELOG.md"
    changelog = changelog_file.read_text(encoding="utf-8")
    headings = list(re.finditer(r"(?m)^## (.+)$", changelog))
    if not headings or headings[0][1] != "[Unreleased]":
        raise ValueError("CHANGELOG.md must start with an [Unreleased] section.")
    if sum(h[1] == "[Unreleased]" for h in headings) != 1:
        raise ValueError("Expected exactly one [Unreleased] section.")
    if any(h[1].startswith(f"[{version}]") for h in headings):
        raise ValueError(f"CHANGELOG.md already contains version {version}.")
    end = headings[1].start() if len(headings) > 1 else len(changelog)
    if not re.search(r"(?m)^- \S", changelog[headings[0].end() : end]):
        raise ValueError("Add at least one user-facing entry under [Unreleased].")
    start = headings[0].end()
    changelog = (
        changelog[:start]
        + f"\n\n## [{version}] - {date.isoformat()}"
        + changelog[start:]
    )
    version_file.write_text(contents, encoding="utf-8")
    changelog_file.write_text(changelog, encoding="utf-8")
    return version


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bump", required=True, choices=("patch", "minor", "major"))
    args = parser.parse_args()
    try:
        version = prepare_release(
            Path(__file__).resolve().parents[2],
            args.bump,
            datetime.datetime.now(datetime.timezone.utc).date(),
        )
    except (ValueError, OSError) as error:
        parser.exit(1, f"Release preparation failed: {error}\n")
    print(version)


if __name__ == "__main__":
    main()
