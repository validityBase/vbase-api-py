# Release management

This guide covers the `vbase-api-py` pilot. The GitHub repository is
`validityBase/vbase-api-py`, the PyPI package is `vbase-api`, and the Python
import is `vbase_api`. Rollout to `vbase-py` follows a verified pilot release
as a separate change.

## How a release works

1. Regular PRs add user-facing entries under `[Unreleased]` without changing the
   package version.
2. A maintainer opens a **Release PR** that increments the version and moves the
   accumulated entries into a dated changelog release section.
3. The Release PR is independently reviewed, passes required checks, and merges
   to `main`. Merging does not publish the package.
4. A maintainer pushes a matching `vX.Y.Z` tag on the merged Release PR commit.
   **Pushing this tag starts publication to PyPI.**
5. The publish workflow validates and uploads the package, then automatically
   creates the GitHub Release with the matching changelog notes.

## Before starting

- The release-process implementation in PR #40 must be merged to `main` before
  the first Release PR. Its guide, validator, and workflow must be present in
  the commit being released.
- Start with a clean local checkout. Run `git status --short` and resolve any
  existing work before switching branches.
- Use Python 3.11 or newer, Git, and an authenticated GitHub CLI (`gh`). Install
  build tools in your development environment with
  `python -m pip install build twine`. See [CLAUDE.md](CLAUDE.md) for the other
  repository checks.
- The releasing maintainer needs permission to push the branch and release tag.
  The repository's existing PyPI trusted publisher and `pypi` environment must
  permit the release run. Complete any configured environment approval when
  GitHub requests it. No static PyPI token is needed.

Commands below run from the repository root. They use **`0.1.4` as an example**
of a patch release after `0.1.3`; replace it everywhere with the version actually
chosen for this release. `YYYY-MM-DD`, `RELEASE_PR_NUMBER`, `PREVIOUS_RELEASE_TAG`,
and `MERGED_RELEASE_COMMIT_SHA` are placeholders, not literal values to run.

## 1. Choose the next version and create the branch

Refresh `main` and inspect the current version:

```bash
git switch main
git pull --ff-only origin main
git fetch origin --tags
cat src/vbase_api/_version.py
```

Continue from the version in that file; never reset it to a ticket's example.
Choose the bump based on the accumulated changes:

| Change | Version bump | Example starting from 0.1.3 |
| --- | --- | --- |
| Compatible bug fixes | PATCH | 0.1.4 |
| Compatible new features | MINOR | 0.2.0 |
| Breaking API changes | MAJOR | 1.0.0 |

Only stable `X.Y.Z` versions are supported. Do not use prerelease suffixes,
build metadata, or leading zeroes in a version component. Confirm that the
chosen version is unused on PyPI and that its tag does not already exist:

```bash
git tag --list v0.1.4
```

For an unused tag, the command prints nothing. Then create the release branch:

```bash
git switch -c release/v0.1.4
```

## 2. Update the version file

Edit `src/vbase_api/_version.py` so it contains the chosen version:

```python
__version__ = "0.1.4"
```

The file contains no `v` prefix. The corresponding Git tag will be `v0.1.4`.
The package metadata reads this file, so do not separately hardcode a version
in `pyproject.toml`.

## 3. Prepare and review CHANGELOG.md

Read the existing `[Unreleased]` entries and check that they cover the changes
being released. Commit history can help find omissions. Once a maintainer has
identified the previous release tag, inspect the range:

```bash
git log --no-merges --format='%h %s' PREVIOUS_RELEASE_TAG..origin/main
```

If there is no previous release tag, have a maintainer choose the starting
commit explicitly and use that commit in place of `PREVIOUS_RELEASE_TAG`.
Do not guess a release boundary or treat all repository history as new changes.
Changelog preparation is currently manual; there is no "Prepare release"
GitHub Action in this implementation.

Rewrite relevant messages as user-facing entries, with PR references when
available. Do not copy every commit automatically: merge noise, internal CI
work, and repeated messages may not describe a user-visible change. Dependency
changes still need entries when they affect users.

Move the accumulated entries into a new dated release section immediately
below a fresh `[Unreleased]` section. For example:

```markdown
## [Unreleased]

## [0.1.4] - YYYY-MM-DD

### Changed
- Added a documented release process with tag validation and automatic GitHub Releases after PyPI publication.
```

Use the actual release preparation date in `YYYY-MM-DD` format. Keep any older
release sections below the new one. The newest release section must match the
version exactly, appear once, and contain at least one bullet entry. Use the
appropriate Added, Changed, Deprecated, Removed, Fixed, or Security categories.
Historical releases before the changelog was introduced are not reconstructed.

## 4. Validate locally

Use a clean `dist/` directory. If it already contains files from another build,
move those files out before running the following commands:

```bash
python -m unittest tests.test_release_process -v
python internal/scripts/validate_release.py --tag v0.1.4
python -m build
python -m twine check dist/*
python internal/scripts/validate_release.py --tag v0.1.4 --dist-dir dist
```

All commands must pass. The validator checks the stable tag against the source
version and dated changelog section. After the build, it also requires exactly
one wheel and one source archive whose metadata identifies `vbase-api` at the
chosen version. These commands do not publish anything or create a Git tag.

Inspect the Release PR's intended changes:

```bash
git diff --check
git diff -- src/vbase_api/_version.py CHANGELOG.md
```

## 5. Open and merge the Release PR

Commit only the version and changelog changes, push the branch, and open the PR:

```bash
git add src/vbase_api/_version.py CHANGELOG.md
git commit -m "Release v0.1.4"
git push -u origin release/v0.1.4
gh pr create --repo validityBase/vbase-api-py --base main --head release/v0.1.4 --title "Release v0.1.4" --body "Bump vbase-api to 0.1.4 and finalize its changelog."
```

Add the validation results to the PR description. The reviewer confirms the
version bump fits the changes, the notes are accurate, and the new version,
changelog heading, and intended tag agree. Obtain independent review and wait
for required repository checks before merging through the normal PR process.

Do not push the release tag while the PR is open. If review changes the version
or changelog, rerun local validation before merging.

## 6. Tag the merged Release PR commit

After merge, obtain the commit SHA GitHub records for that Release PR:

```bash
gh pr view RELEASE_PR_NUMBER --repo validityBase/vbase-api-py --json state,mergeCommit,url
git fetch origin main --tags
```

Confirm the PR state is `MERGED`. Use its `mergeCommit.oid` as
`MERGED_RELEASE_COMMIT_SHA`; this is the commit on `main`, including when the PR
was squash merged. Do not tag the pre-merge feature branch or use an arbitrary
local `HEAD`.

Check that the commit belongs to `main` and contains the expected release files:

```bash
git merge-base --is-ancestor MERGED_RELEASE_COMMIT_SHA origin/main
git show MERGED_RELEASE_COMMIT_SHA:src/vbase_api/_version.py
git show MERGED_RELEASE_COMMIT_SHA:CHANGELOG.md
```

The ancestry check must exit successfully; it prints nothing on success.
Confirm the version is `0.1.4` and the newest dated release section is `[0.1.4]`.

When the maintainer has approved publication, create and push the tag:

```bash
git tag -a v0.1.4 MERGED_RELEASE_COMMIT_SHA -m "Release v0.1.4"
git push origin refs/tags/v0.1.4
```

**The tag push publishes the package.** Do not move or reuse a pushed release
tag. A later source correction needs a new version and Release PR.

## 7. Monitor publication and verify the result

Open the repository's [Actions page](https://github.com/validityBase/vbase-api-py/actions)
and find **Publish Python Package to PyPI** for the tag. The jobs run in order:

| Job | Expected result |
| --- | --- |
| Build distribution | Tag and main ancestry checks pass; version, changelog, and both distribution files validate |
| Publish to PyPI | The existing trusted publisher uploads the built distributions using OIDC |
| Create GitHub Release | A release is created for the existing tag using only that version's changelog notes |

Confirm `0.1.4` is visible on
[PyPI](https://pypi.org/project/vbase-api/) with both distribution files. Check
the [GitHub Release](https://github.com/validityBase/vbase-api-py/releases) has the
right tag and changelog notes. Creating a GitHub Release does not trigger a
second publication.

Verify the published package in a new environment, rather than an editable
checkout or the environment used to build it. Use a fresh directory if the
example environment already exists; `venv/` is ignored by Git:

```bash
python -m venv venv/release-check-0.1.4
source venv/release-check-0.1.4/bin/activate
python -m pip install --index-url https://pypi.org/simple --no-cache-dir vbase-api==0.1.4
python -m pip check
python -c "from importlib.metadata import version; import vbase_api; assert version('vbase-api') == vbase_api.__version__ == '0.1.4'; print(vbase_api.__file__); print(version('vbase-api'))"
deactivate
```

On Windows PowerShell, activate the environment with
`.\venv\release-check-0.1.4\Scripts\Activate.ps1` instead of the `source` command.
The printed import path should point into the new environment, and the printed
version should be `0.1.4`.

Record the Release PR, tag, workflow run, PyPI version, GitHub Release, and
installation check results in VPY-32. The live pilot is not verified until
these checks pass; only then proceed with a separate `vbase-py` rollout.

## Emergency manual publication

For an explicitly authorized emergency run, dispatch at an existing release
tag that includes this release workflow and validator:

```bash
gh workflow run publish-pypi.yml --repo validityBase/vbase-api-py --ref v0.1.4
```

Use a tag, never `main` or another branch. This does not create a tag, bump the
version, or prepare the changelog. It runs the same checks and publication jobs
as a tag push. Do not use it to republish a version already uploaded to PyPI.
Runs for the same ref are serialized, without cancelling an active upload.

## Recovery

| Failure | Next step |
| --- | --- |
| Validation or build fails before upload | Read the failed step. For a transient issue, retry the failed job. If source changes are needed, prepare a corrected Release PR with a new version and tag. |
| PyPI upload fails and no files were published | Fix the transient or configuration issue and retry the failed job at the same unchanged tag. |
| PyPI upload fails after some files were published | Stop and inspect PyPI before retrying. Existing files are not silently skipped or overwritten; a corrected new version may be needed. |
| PyPI succeeds but GitHub Release creation fails | Rerun only the failed GitHub Release job using the Actions UI. Do not rerun the successful upload. If a Release already exists, inspect its tag and notes first. |
| A published package is faulty | Prepare a corrective Release PR with a new version. Do not move the tag or try to replace published artifacts. |

Manual dispatch runs the whole workflow; it is not a substitute for rerunning
only the failed GitHub Release job after a successful PyPI upload.
