# Release management

Follow the [shared release runbook](https://github.com/validityBase/vbase-github-actions/blob/main/RELEASE_MANAGEMENT.md)
for preparation, CI approval, review, automatic publication, and verification.
Release logic, tests, and the runbook are maintained in `vbase-github-actions`.

## Repository settings

| Setting | Value |
| --- | --- |
| Repository | `validityBase/vbase-api-py` |
| PyPI project | [`vbase-api`](https://pypi.org/project/vbase-api/) |
| Import name | `vbase_api` |
| Version file | `src/vbase_api/_version.py` |
| Changelog | `CHANGELOG.md` |
| Default branch | `main` |
| Release branch / tag | `release/vX.Y.Z` / `vX.Y.Z` |
| Publication workflow / environment | `publish-pypi.yml` / `pypi` |

Start preparation through this repository's **Actions → Prepare release**,
using `main` and an explicit patch/minor/major increment. The selected bump type determines the next version number, derived
from the current version in the version file.

Shared settings and defaults are in the
[action contract](https://github.com/validityBase/vbase-github-actions/blob/main/.github/actions/python-release/README.md).
