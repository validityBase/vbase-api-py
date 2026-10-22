# Release management

Releases publish the `vbase-api` package from `validityBase/vbase-api-py`.
A Release PR updates the version and changelog. After it merges to `main`,
pushing its matching tag publishes to PyPI and then creates the GitHub Release.

Run commands from the repository root. The examples use `0.1.4`; replace it
with the chosen version. Replace `YYYY-MM-DD`, `PREVIOUS_RELEASE_TAG`,
`RELEASE_PR_NUMBER`, and `MERGED_RELEASE_COMMIT_SHA` with their actual values.

## 1. Choose the version and create a branch

```bash
git switch main
git pull --ff-only origin main
git fetch origin --tags
cat src/vbase_api/_version.py
```

Continue from the version in that file:

| Change | Bump | Example from 0.1.3 |
| --- | --- | --- |
| Compatible bug fixes | PATCH | 0.1.4 |
| Compatible features | MINOR | 0.2.0 |
| Breaking API changes | MAJOR | 1.0.0 |

Use a stable `X.Y.Z` version without prerelease suffixes or leading zeroes.
Confirm it is unused on [PyPI](https://pypi.org/project/vbase-api/) and its tag
is unused. The tag check should print nothing:

```bash
git tag --list v0.1.4
git switch -c release/v0.1.4
```

## 2. Update the version and changelog

Set `src/vbase_api/_version.py` to:

```python
__version__ = "0.1.4"
```

Review `[Unreleased]` in `CHANGELOG.md`. To check for missing entries, inspect
commits since the previous release tag:

```bash
git log --no-merges --format='%h %s' PREVIOUS_RELEASE_TAG..origin/main
```

If no previous tag exists, have a maintainer choose the starting commit.
Write user-facing entries manually, with PR references where available.

Move the entries into a dated release section and retain an empty
`[Unreleased]` section above it:

```markdown
## [Unreleased]

## [0.1.4] - YYYY-MM-DD

### Fixed
- Describe the user-facing fix.
```

Use the release preparation date. The new version section must appear once,
be the newest release, and contain at least one bullet. Group entries under
Added, Changed, Deprecated, Removed, Fixed, or Security as appropriate.

## 3. Validate locally

Use a clean `dist/` directory containing no previous build artifacts:

```bash
python -m pip install build twine
python -m unittest tests.test_release_process -v
python internal/scripts/validate_release.py --tag v0.1.4
python -m build
python -m twine check dist/*
python internal/scripts/validate_release.py --tag v0.1.4 --dist-dir dist
git diff --check
git diff -- src/vbase_api/_version.py CHANGELOG.md
```

All checks must pass. The validator requires matching tag, source, changelog,
wheel, and source archive versions. Local validation does not publish.

## 4. Open and merge the Release PR

```bash
git add src/vbase_api/_version.py CHANGELOG.md
git commit -m "Release v0.1.4"
git push -u origin release/v0.1.4
gh pr create --repo validityBase/vbase-api-py --base main --head release/v0.1.4 --title "Release v0.1.4" --body "Bump vbase-api to 0.1.4 and finalize its changelog."
```

Add validation results to the PR description. Obtain independent review, wait
for required repository checks, and merge to `main`. If review changes the
version or changelog, rerun validation. Merging does not publish the package.

## 5. Tag the merged commit and publish

Get the Release PR's merged commit:

```bash
gh pr view RELEASE_PR_NUMBER --repo validityBase/vbase-api-py --json state,mergeCommit,url
git fetch origin main --tags
```

Confirm the state is `MERGED`. Use `mergeCommit.oid` as
`MERGED_RELEASE_COMMIT_SHA`, then check its ancestry and release files:

```bash
git merge-base --is-ancestor MERGED_RELEASE_COMMIT_SHA origin/main
git show MERGED_RELEASE_COMMIT_SHA:src/vbase_api/_version.py
git show MERGED_RELEASE_COMMIT_SHA:CHANGELOG.md
```

The ancestry check must succeed. Confirm the version and newest changelog
release are both `0.1.4`. After publication is approved, tag that commit:

```bash
git tag -a v0.1.4 MERGED_RELEASE_COMMIT_SHA -m "Release v0.1.4"
git push origin refs/tags/v0.1.4
```

**Pushing the tag starts publication.** The workflow validates the release,
publishes through the existing PyPI trusted publisher, and then creates the
GitHub Release from the changelog notes. Do not move or reuse a pushed tag.

## 6. Verify publication

1. Check **Publish Python Package to PyPI** on the repository's
   [Actions page](https://github.com/validityBase/vbase-api-py/actions).
   Build, PyPI publication, and GitHub Release creation must all succeed.
2. Confirm the version and both distribution files on
   [PyPI](https://pypi.org/project/vbase-api/).
3. Check the tag and notes on the
   [GitHub Release](https://github.com/validityBase/vbase-api-py/releases).
4. Install and check the published version in a fresh environment:

   ```bash
   python -m venv venv/release-check-0.1.4
   source venv/release-check-0.1.4/bin/activate
   python -m pip install --index-url https://pypi.org/simple --no-cache-dir vbase-api==0.1.4
   python -m pip check
   python -c "from importlib.metadata import version; import vbase_api; assert version('vbase-api') == vbase_api.__version__ == '0.1.4'; print(vbase_api.__file__); print(version('vbase-api'))"
   deactivate
   ```

   Use a new directory if the example environment already exists. Confirm the
   printed import path belongs to that environment and the version is `0.1.4`.

## Manual publication

For an approved manual publication, select an existing release tag containing
this workflow and validator:

```bash
gh workflow run publish-pypi.yml --repo validityBase/vbase-api-py --ref v0.1.4
```

Manual runs use the same validation. Branch refs are rejected. Do not dispatch
a version already published to PyPI.
