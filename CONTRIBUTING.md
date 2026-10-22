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

## Releases

Follow [RELEASE_MANAGMENT.md](RELEASE_MANAGMENT.md) for the complete maintainer
runbook: choosing a version, preparing the changelog, opening and reviewing the
Release PR, tagging the merged commit, and verifying publication.

Ordinary PRs do not publish packages. A Release PR updates the version and
changelog; after it merges to `main`, a maintainer pushes the matching release
tag to start publication.
