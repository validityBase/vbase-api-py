# Contributing

## Everyday pull requests

Add user-facing changes to `CHANGELOG.md` under `[Unreleased]`, grouped as
Added, Changed, Deprecated, Removed, Fixed, or Security. Include the PR reference
when available. Internal changes may omit an entry with an explanation in the
PR; dependency changes that affect users still need an entry.

Do not change `src/vbase_api/_version.py` in ordinary PRs. Keep related tests,
documentation, and internal specifications aligned. See [CLAUDE.md](CLAUDE.md)
for development checks. Release validation tests run without service credentials:

```bash
python -m unittest tests.test_release_process -v
```

## Release PR

The version in `src/vbase_api/_version.py` is the starting point; do not reset
it to the example version in a ticket. This repository publishes as `vbase-api`
on PyPI and imports as `vbase_api`.

1. Choose the next version: PATCH for compatible bug fixes, MINOR for compatible
   features, MAJOR for breaking API changes. Only stable `X.Y.Z` versions are
   supported; prereleases are outside this pilot.
2. Create `release/vX.Y.Z` from current `main`.
3. Set `__version__` in `src/vbase_api/_version.py` to `X.Y.Z`.
4. Move the accumulated changelog entries into `## [X.Y.Z] - YYYY-MM-DD`
   immediately below a fresh `## [Unreleased]` section. Use the actual release
   preparation date and include at least one entry. Historical releases before
   this changelog was introduced are not reconstructed.
5. Validate locally, replacing the example tag with the chosen version:

   ```bash
   python internal/scripts/validate_release.py --tag vX.Y.Z
   python -m build
   python -m twine check dist/*
   python internal/scripts/validate_release.py --tag vX.Y.Z --dist-dir dist
   ```

   Use a clean `dist/` directory: exactly one wheel and one source archive are
   expected. These commands build and validate; they do not publish.
6. Open a Release PR containing the version and changelog changes. Obtain an
   independent review, wait for required repository checks, and merge to `main`.
   Do not push a release tag before merge.

## Publish the merged release

A maintainer explicitly authorizes publication by pushing the release tag.
Tag the merged Release PR commit, rather than whichever commit happens to be
checked out locally. Replace the placeholders below with the chosen version
and the merged commit SHA:

```bash
git fetch origin main --tags
git tag -a vX.Y.Z MERGED_RELEASE_COMMIT_SHA -m "Release vX.Y.Z"
git push origin refs/tags/vX.Y.Z
```

The publish workflow checks that the tag targets a commit in `main`, validates
the stable tag against the source version and dated changelog section, builds
and checks both distributions, and verifies their name/version metadata. It
publishes to PyPI through the existing `pypi` environment using OIDC. Only after
PyPI publication succeeds does a separate job automatically create the GitHub
Release with the matching changelog notes. Creating a GitHub Release does not
trigger another publication.

After publishing, confirm the version on
[PyPI](https://pypi.org/project/vbase-api/) and its GitHub Release, then install
the exact version in a clean environment and check it:

```bash
python -m pip install vbase-api==X.Y.Z
python -m pip check
python -c "from importlib.metadata import version; import vbase_api; print(version('vbase-api'))"
```

## Manual publication and recovery

For an explicitly authorized emergency run, dispatch the workflow at an existing
release tag using GitHub CLI:

```bash
gh workflow run publish-pypi.yml --ref vX.Y.Z
```

Do not dispatch at `main` or another branch: the workflow rejects branch refs.
Manual and tag-push runs use the same checks. Workflow runs for the same ref are
serialized, and an active publication is never cancelled by a newer run.

- If validation or the build fails before upload, inspect and fix the cause.
  Do not move or reuse a pushed release tag; use a corrected Release PR and a
  new version when source changes are needed.
- If publication fails, first inspect PyPI to determine whether either artifact
  was uploaded. Retry the failed job only when nothing was published and the
  cause was transient. Already uploaded files are not silently skipped or
  overwritten. For a partial publication, stop and assess the published files;
  use a new corrective version if needed.
- If PyPI publication succeeded but GitHub Release creation failed, rerun only
  the failed GitHub Release job. Do not rerun the successful upload. If a Release
  already exists, inspect its tag and notes before taking any further action.
- If a published package is faulty, prepare a corrective release with a new
  version. Do not move the tag or attempt to replace published artifacts.

This is the `vbase-api-py` pilot. Apply the process to `vbase-py` only after the
pilot release has been published and verified, as a separate change.
