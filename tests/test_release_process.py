"""Offline tests for the checks that guard PyPI publication."""

import io
import tempfile
import unittest
import zipfile
from pathlib import Path
from tarfile import TarInfo
from tarfile import open as tar_open

from internal.scripts.validate_release import release_notes, validate_distributions


class ReleaseValidationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.version_file = self.root / "src/vbase_api/_version.py"
        self.version_file.parent.mkdir(parents=True)
        self.version_file.write_text('__version__ = "0.1.4"\n', encoding="utf-8")
        self.changelog = self.root / "CHANGELOG.md"
        self.contents = (
            "# Changelog\n\n## [Unreleased]\n\n"
            "### Added\n- Future work must not appear in release notes.\n\n"
            "## [0.1.4] - 2026-10-22\n\n"
            "### Fixed\n- Fixed timeout handling (#12).\n\n"
            "## [0.1.3] - 2026-10-01\n\n### Added\n- Older release.\n"
        )
        self.changelog.write_text(self.contents, encoding="utf-8")
        self.dist = self.root / "dist"
        self.dist.mkdir()

    def distributions(
        self, wheel_version="0.1.4", sdist_version="0.1.4", name="vbase-api"
    ):
        with zipfile.ZipFile(
            self.dist / "vbase_api-0.1.4-py3-none-any.whl", "w"
        ) as wheel:
            wheel.writestr(
                "vbase_api-0.1.4.dist-info/METADATA",
                f"Metadata-Version: 2.4\nName: {name}\nVersion: {wheel_version}\n",
            )
        raw = (
            f"Metadata-Version: 2.4\nName: {name}\nVersion: {sdist_version}\n".encode()
        )
        with tar_open(self.dist / "vbase_api-0.1.4.tar.gz", "w:gz") as sdist:
            member = TarInfo("vbase_api-0.1.4/PKG-INFO")
            member.size = len(raw)
            sdist.addfile(member, io.BytesIO(raw))

    def test_extracts_only_matching_release_notes(self):
        self.assertEqual(
            release_notes(self.root, "v0.1.4"),
            "### Fixed\n- Fixed timeout handling (#12).\n",
        )

    def test_extracts_last_release_without_trailing_section(self):
        self.changelog.write_text(
            self.contents.split("## [0.1.3]")[0], encoding="utf-8"
        )
        self.assertEqual(
            release_notes(self.root, "v0.1.4"),
            "### Fixed\n- Fixed timeout handling (#12).\n",
        )

    def test_rejects_nonstable_or_malformed_tags(self):
        for tag in (
            "0.1.4",
            "main",
            "v0.1.4rc1",
            "v0.1.4-rc1",
            "v0.1.4+build1",
            "v00.1.4",
            "v0.01.4",
            "v0.1.04",
            "v0.1.4.1",
            "v0.1.4\n",
        ):
            with self.subTest(tag=tag), self.assertRaisesRegex(ValueError, "stable"):
                release_notes(self.root, tag)

    def test_rejects_source_version_mismatch(self):
        with self.assertRaisesRegex(ValueError, "__version__"):
            release_notes(self.root, "v0.1.5")

    def test_does_not_execute_version_file(self):
        self.version_file.write_text(
            'raise RuntimeError("must not execute")\n__version__ = "0.1.4"\n',
            encoding="utf-8",
        )
        self.assertIn("Fixed timeout", release_notes(self.root, "v0.1.4"))

    def test_requires_exactly_one_source_version(self):
        for contents in ('other = "0.1.4"', '__version__ = "0.1.4"\n' * 2):
            with self.subTest(contents=contents):
                self.version_file.write_text(contents, encoding="utf-8")
                with self.assertRaisesRegex(ValueError, "__version__"):
                    release_notes(self.root, "v0.1.4")

    def test_rejects_incomplete_changelog(self):
        for contents in (
            self.contents.replace("## [Unreleased]", "## [Upcoming]"),
            self.contents.replace("[0.1.4]", "[0.1.5]"),
            self.contents + "\n## [0.1.4] - 2026-10-22\n- Duplicate.\n",
            self.contents.replace("2026-10-22", "2026-02-30"),
            self.contents.replace("2026-10-22", "2026/10/22"),
            self.contents.replace("- Fixed timeout handling (#12).", ""),
            self.contents.replace(
                "## [0.1.4]", "## [0.1.5] - 2026-10-23\n- Newer.\n\n## [0.1.4]"
            ),
        ):
            with self.subTest(contents=contents):
                self.changelog.write_text(contents, encoding="utf-8")
                with self.assertRaises(ValueError):
                    release_notes(self.root, "v0.1.4")

    def test_accepts_matching_built_metadata(self):
        self.distributions()
        validate_distributions(self.dist, "0.1.4")

    def test_rejects_wrong_metadata_even_if_filenames_match(self):
        for kwargs in (
            {"wheel_version": "0.1.5"},
            {"sdist_version": "0.1.5"},
            {"name": "wrong-package"},
        ):
            with self.subTest(kwargs=kwargs):
                self.distributions(**kwargs)
                with self.assertRaisesRegex(ValueError, "name/version"):
                    validate_distributions(self.dist, "0.1.4")

    def test_rejects_missing_distribution(self):
        self.distributions()
        (self.dist / "vbase_api-0.1.4.tar.gz").unlink()
        with self.assertRaisesRegex(ValueError, "exactly one"):
            validate_distributions(self.dist, "0.1.4")

    def test_rejects_extra_files(self):
        self.distributions()
        (self.dist / "release-notes.md").write_text("notes", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "exactly one"):
            validate_distributions(self.dist, "0.1.4")

    def test_rejects_missing_wheel_metadata(self):
        self.distributions()
        with zipfile.ZipFile(self.dist / "vbase_api-0.1.4-py3-none-any.whl", "w"):
            pass
        with self.assertRaisesRegex(ValueError, "METADATA"):
            validate_distributions(self.dist, "0.1.4")

    def test_rejects_missing_source_metadata(self):
        self.distributions()
        with tar_open(self.dist / "vbase_api-0.1.4.tar.gz", "w:gz"):
            pass
        with self.assertRaisesRegex(ValueError, "PKG-INFO"):
            validate_distributions(self.dist, "0.1.4")


if __name__ == "__main__":
    unittest.main()
