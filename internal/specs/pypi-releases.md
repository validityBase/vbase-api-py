# Python package releases

## Repository configuration

- PyPI project: `vbase-api`.
- Version file: `src/vbase_api/_version.py`; version attribute: `__version__`.
- Changelog: `CHANGELOG.md`; default branch: `main`.
- Stable tags: `vX.Y.Z`; release branches: `release/vX.Y.Z`.
- Publication workflow: `publish-pypi.yml`; environment: `pypi`.

The three local workflow files declare triggers and call shared workflows in
`validityBase/vbase-github-actions`. Generic scripts and tests live there;
this repository contains no copies. Each reusable workflow and its
`release-tools-ref` must use the same pinned shared commit. Optional input
settings, including commit author defaults, are documented in the shared
[release contract](https://github.com/validityBase/vbase-github-actions/blob/90bb174056b74032c5f750473d2b42f4b1fa1797/.github/actions/python-release/README.md).

The upload job remains in this repository's workflow so its existing PyPI
trusted-publisher identity is preserved. It calls the shared publication
composite action. GitHub Release creation depends on successful upload.

## Behavior and validation

- An explicit patch/minor/major choice increments the current source version,
  resets lower components, and finalizes existing user-facing Unreleased notes.
- Empty notes, duplicate versions, existing target refs, and existing open
  Release PRs stop preparation. User impact is reviewed by maintainers.
- Review and required CI precede merge. Bot-created PR workflows may require
  **Approve workflows to run**. Merge authorizes publication.
- Only merged, same-repository release PRs targeting the default branch are
  automatically tagged, and the tag must match the source/changelog versions.
- Both automatic and manual publication validate stable tags, main ancestry,
  and wheel/sdist package metadata before OIDC upload.
- Shared tests cover both package layouts and configuration defaults/overrides.
  Live publication must be verified using the maintainer runbook.

Contributor guidance: [CONTRIBUTING.md](../../CONTRIBUTING.md).
Maintainer runbook: [RELEASE_MANAGEMENT.md](../../RELEASE_MANAGEMENT.md).
