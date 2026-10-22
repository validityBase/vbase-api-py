"""Offline coverage for automatic version selection and changelog finalization."""

import datetime
import tempfile
import unittest
from pathlib import Path

from internal.scripts.prepare_release import next_version, prepare_release
from internal.scripts.validate_release import release_notes


class VersionIncrementTests(unittest.TestCase):
    def test_increments_and_resets_lower_components(self):
        for current, bump, expected in (
            ("0.1.3", "patch", "0.1.4"),
            ("0.1.3", "minor", "0.2.0"),
            ("0.1.3", "major", "1.0.0"),
            ("1.9.12", "minor", "1.10.0"),
            ("1.9.12", "major", "2.0.0"),
            ("0.0.0", "patch", "0.0.1"),
        ):
            with self.subTest(current=current, bump=bump):
                self.assertEqual(next_version(current, bump), expected)

    def test_rejects_nonstable_current_versions(self):
        for version in ("v1.2.3", "1.2", "01.2.3", "1.2.3rc1", "1.2.3+build"):
            with self.subTest(version=version), self.assertRaises(ValueError):
                next_version(version, "patch")

    def test_rejects_unknown_increment(self):
        with self.assertRaises(ValueError):
            next_version("0.1.3", "automatic")


class ReleasePreparationTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.version_file = self.root / "src/vbase_api/_version.py"
        self.version_file.parent.mkdir(parents=True)
        self.version_file.write_text('__version__ = "0.1.3"\n', encoding="utf-8")
        self.changelog = self.root / "CHANGELOG.md"
        self.contents = (
            "# Changelog\n\n## [Unreleased]\n\n### Fixed\n- Fix timeout (#12).\n\n"
            "## [0.1.2] - 2026-10-01\n\n### Added\n- Older entry.\n"
        )
        self.changelog.write_text(self.contents, encoding="utf-8")
        self.date = datetime.date(2026, 10, 22)

    def test_prepares_release_accepted_by_publish_validator(self):
        version = prepare_release(self.root, "patch", self.date)
        self.assertEqual(version, "0.1.4")
        self.assertEqual(self.version_file.read_text(), '__version__ = "0.1.4"\n')
        self.assertIn(
            "## [Unreleased]\n\n## [0.1.4] - 2026-10-22\n\n### Fixed",
            self.changelog.read_text(),
        )
        self.assertEqual(
            release_notes(self.root, "v0.1.4"), "### Fixed\n- Fix timeout (#12).\n"
        )
        self.assertTrue(
            self.changelog.read_text().endswith(
                "## [0.1.2] - 2026-10-01\n\n### Added\n- Older entry.\n"
            )
        )

    def test_prepares_first_release_without_older_changelog_sections(self):
        self.changelog.write_text(
            self.contents.split("## [0.1.2]")[0], encoding="utf-8"
        )
        version = prepare_release(self.root, "minor", self.date)
        self.assertEqual(version, "0.2.0")
        self.assertIn("Fix timeout", release_notes(self.root, "v0.2.0"))

    def test_supports_single_quoted_version(self):
        self.version_file.write_text("__version__ = '0.1.3'\n", encoding="utf-8")
        self.assertEqual(prepare_release(self.root, "major", self.date), "1.0.0")
        self.assertIn("Fix timeout", release_notes(self.root, "v1.0.0"))

    def test_rejects_invalid_changelog_without_editing_files(self):
        for contents in (
            "# Changelog\n\n## [Unreleased]\n",
            self.contents.replace("## [Unreleased]", "## [Upcoming]"),
            self.contents + "\n## [Unreleased]\n- Duplicate.\n",
            self.contents + "\n## [0.1.4] - 2026-10-10\n- Existing release.\n",
        ):
            with self.subTest(contents=contents):
                self.changelog.write_text(contents, encoding="utf-8")
                with self.assertRaises(ValueError):
                    prepare_release(self.root, "patch", self.date)
                self.assertEqual(self.changelog.read_text(), contents)
                self.assertEqual(
                    self.version_file.read_text(), '__version__ = "0.1.3"\n'
                )

    def test_rejects_a_second_run_until_new_entries_exist(self):
        prepare_release(self.root, "patch", self.date)
        with self.assertRaisesRegex(ValueError, "entry"):
            prepare_release(self.root, "patch", self.date)
        self.assertIn('"0.1.4"', self.version_file.read_text())


if __name__ == "__main__":
    unittest.main()
