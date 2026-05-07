# GitHub Actions

## Policy
- Third-party actions are pinned by full commit SHA for reproducibility.
- Shared vBase-owned actions use `validityBase/vbase-github-actions` with reviewed release tags such as `@v1`.
- Workflow permissions are declared explicitly and kept minimal.
- Secrets must come from GitHub Secrets or deployment configuration, never from committed files or logs.

## Local Python Setup Action
This repository intentionally keeps `.github/actions/setup-python-deps/action.yml`.

Unlike repositories that install dependencies from `requirements.txt`, this package is driven by `pyproject.toml` and the local action has two repository-specific modes:

- `build`: installs `build` for PyPI distribution builds.
- `docs`: installs the package itself plus `sphinx` and `sphinx-markdown-builder`.

Do not replace this local action with the shared `setup-python-deps@v1` unless the shared action supports this repository's `pyproject.toml` build/docs workflow.

## Workflows

### `.github/workflows/documentation-publishing.yml`
- Runs on pushes to `main` and manual dispatch.
- Sets up Python 3.x with the pinned `actions/setup-python` action.
- Uses the local `setup-python-deps` action in `docs` mode.
- Builds Sphinx Markdown docs into `docs/_build/markdown`.
- Rewrites generated module references before publishing.
- Copies generated Markdown files to `docs_generated`.
- Publishes to the central docs repository with `validityBase/vbase-github-actions/.github/actions/publish-docs@v1`.
- Uses `DOCS_REPO_ACCESS_TOKEN` for the central docs repository.

### `.github/workflows/publish-pypi.yml`
- Runs on published GitHub releases and manual dispatch.
- Builds Python package distributions with the local `setup-python-deps` action in `build` mode.
- Uploads the distribution artifact from the build job.
- Publishes to PyPI through trusted publishing with OIDC.
