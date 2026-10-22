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
python -m unittest tests.test_release_process tests.test_release_automation -v
```

## Releases

Follow [RELEASE_MANAGMENT.md](RELEASE_MANAGMENT.md) to run **Prepare release**
with a patch, minor, or major increment, approve CI workflows for the generated
Release PR, review it, and verify publication.

Ordinary PRs do not publish packages. Automation updates the version and
changelog in a Release PR. Merging that reviewed PR to `main` automatically
pushes its matching tag and starts publication.
