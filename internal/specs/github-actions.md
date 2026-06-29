# GitHub Actions

## Policy
- Third-party actions are pinned by full commit SHA for reproducibility.
- Shared vBase-owned actions and reusable workflows use `validityBase/vbase-github-actions` with reviewed release tags such as `@v1`.
- Workflow permissions are declared explicitly and kept minimal.
- Python installs for docs and lock verification use generated hash-locked terminal environment requirements with `require-hashes`.
- Secrets must come from GitHub Secrets or deployment configuration, never from committed files or logs.

## Dependencies

Published runtime dependencies live in `requirements.in` as abstract ranges and are read by `pyproject.toml`.
Documentation publishing and lock tooling are terminal environments owned by this repository, so their generated lock files live under `requirements/lock/` and are installed with `require-hashes`.

Do not restore a local `.github/actions/setup-python-deps` copy. Use `validityBase/vbase-github-actions/.github/actions/setup-python-deps@v1` for requirements-file based Python dependency setup.

## Workflows

### `.github/workflows/python-dependency-locks.yml`
- Runs on pull requests, pushes to `main`, and manual `workflow_dispatch`.
- Installs `requirements/lock/tools.txt` through `setup-python-deps@v1` with Python 3.12 and `require-hashes: "true"`.
- Regenerates `requirements/lock/docs.txt` and `requirements/lock/tools.txt`; the workflow fails if committed lock files differ.
- Installs `requirements/lock/docs.txt` and checks installed dependency consistency with `python -m pip check`.

### `.github/workflows/documentation-publishing.yml`
- Runs on pushes to `main` and manual dispatch.
- Delegates to `validityBase/vbase-github-actions/.github/workflows/publish-docs.yml@v1`.
- Installs `requirements/lock/docs.txt` with `require-hashes: true`.
- Builds Sphinx Markdown docs into `docs/_build/markdown` and rewrites generated module references before publishing.
- Publishes to the central docs repository.
- Uses `DOCS_REPO_ACCESS_TOKEN` for the central docs repository.

### `.github/workflows/publish-pypi.yml`
- Runs on published GitHub releases and manual dispatch.
- Installs `build` and `twine`, builds Python package distributions, and checks them with `twine`.
- Uploads the distribution artifact from the build job.
- Publishes to PyPI through trusted publishing with OIDC.
