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
[release contract](https://github.com/validityBase/vbase-github-actions/blob/main/.github/actions/python-release/README.md).

The upload job remains in this repository's workflow so its existing PyPI
trusted-publisher identity is preserved. It calls the shared publication
composite action. GitHub Release creation depends on successful upload.

The shared contract defines release behavior and validation; it is not copied
into this repository. Package-specific settings are listed above.

Contributor guidance: [CONTRIBUTING.md](../../CONTRIBUTING.md).
Repository release settings and runbook link: [RELEASE_MANAGEMENT.md](../../RELEASE_MANAGEMENT.md).
