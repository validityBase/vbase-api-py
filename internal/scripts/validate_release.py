"""Validate a stable release without importing the package or publishing anything."""

import argparse
import ast
import datetime
import re
import tarfile
import zipfile
from email.parser import BytesParser
from pathlib import Path


def source_version(root: Path) -> str:
    """Read the single literal package version without executing package code."""
    tree = ast.parse((root / "src/vbase_api/_version.py").read_text(encoding="utf-8"))
    versions = [
        ast.literal_eval(node.value)
        for node in tree.body
        if isinstance(node, ast.Assign)
        and any(isinstance(t, ast.Name) and t.id == "__version__" for t in node.targets)
    ]
    if len(versions) != 1 or not isinstance(versions[0], str):
        raise ValueError("Expected exactly one literal __version__ assignment.")
    return versions[0]


def release_notes(root: Path, tag: str) -> str:
    """Require matching source/changelog versions and return just this release's notes."""
    number = r"(0|[1-9][0-9]*)"
    if not re.fullmatch(rf"v{number}\.{number}\.{number}", tag):
        raise ValueError("Release tag must be stable vX.Y.Z (no prerelease).")
    version = tag[1:]
    if source_version(root) != version:
        raise ValueError("Tag does not match __version__ in src/vbase_api/_version.py.")

    changelog = (root / "CHANGELOG.md").read_text(encoding="utf-8")
    headings = list(re.finditer(r"(?m)^## (.+)$", changelog))
    if not headings or headings[0][1] != "[Unreleased]":
        raise ValueError("CHANGELOG.md must start with an [Unreleased] section.")
    matches = [h for h in headings if h[1].startswith(f"[{version}]")]
    if len(matches) != 1 or len(headings) < 2 or matches[0] != headings[1]:
        raise ValueError(
            "The newest changelog release must match the tag exactly once."
        )
    heading = re.fullmatch(
        rf"\[{re.escape(version)}\] - (\d{{4}}-\d{{2}}-\d{{2}})", matches[0][1]
    )
    if not heading:
        raise ValueError("Release heading must be [X.Y.Z] - YYYY-MM-DD.")
    datetime.date.fromisoformat(heading[1])
    end = headings[2].start() if len(headings) > 2 else len(changelog)
    notes = changelog[matches[0].end() : end].strip()
    if not re.search(r"(?m)^- \S", notes):
        raise ValueError("Release notes must contain at least one changelog entry.")
    return notes + "\n"


def validate_distributions(dist_dir: Path, version: str) -> None:
    """Check the actual metadata of both distributions, rather than filenames alone."""
    wheels = list(dist_dir.glob("*.whl"))
    sdists = list(dist_dir.glob("*.tar.gz"))
    if len(wheels) != 1 or len(sdists) != 1 or len(list(dist_dir.iterdir())) != 2:
        raise ValueError("Expected exactly one wheel and one source distribution.")
    with zipfile.ZipFile(wheels[0]) as wheel:
        names = [n for n in wheel.namelist() if n.endswith(".dist-info/METADATA")]
        if len(names) != 1:
            raise ValueError("Wheel must contain exactly one METADATA file.")
        wheel_metadata = wheel.read(names[0])
    with tarfile.open(sdists[0]) as sdist:
        members = [
            m for m in sdist.getmembers() if re.fullmatch(r"[^/]+/PKG-INFO", m.name)
        ]
        if len(members) != 1 or not members[0].isfile():
            raise ValueError("Source distribution must contain one root PKG-INFO file.")
        with sdist.extractfile(members[0]) as metadata:
            sdist_metadata = metadata.read()
    for raw in (wheel_metadata, sdist_metadata):
        metadata = BytesParser().parsebytes(raw)
        if metadata["Name"] != "vbase-api" or metadata["Version"] != version:
            raise ValueError(
                "Distribution name/version must match vbase-api and the tag."
            )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tag", required=True)
    parser.add_argument("--dist-dir", type=Path)
    parser.add_argument("--notes-file", type=Path)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    try:
        notes = release_notes(root, args.tag)
        if args.dist_dir is not None:
            validate_distributions(args.dist_dir, args.tag[1:])
        if args.notes_file is not None:
            args.notes_file.write_text(notes, encoding="utf-8")
    except (ValueError, OSError) as error:
        parser.exit(1, f"Release validation failed: {error}\n")
    print(f"Release validation passed: {args.tag}")


if __name__ == "__main__":
    main()
