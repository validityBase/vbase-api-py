# GitHub Actions

## Policy
- Third-party actions are pinned by full commit SHA for reproducibility.
- Shared vBase-owned actions and reusable workflows use `validityBase/vbase-github-actions` with reviewed release tags such as `@v1`.
- Workflow permissions are declared explicitly and kept minimal.
- Python installs for docs and lock verification use generated hash-locked terminal environment requirements with `require-hashes`.
- Secrets must come from GitHub Secrets or deployment configuration, never from committed files or logs.

## Dependencies

Published runtime dependencies live in `requirements.in` as abstract ranges and are read by `pyproject.toml`.
Documentation publishing, live E2E tests, and lock tooling are terminal
environments owned by this repository, so their generated lock files live under
`requirements/lock/` and are installed with `require-hashes`.

Private helper dependencies live in `requirements-private.txt` and are installed
separately with `--no-deps`. The current private helper is `vbase-common`, which
provides `bw_sm` for Bitwarden Secrets Manager access. The workflow must provide
`VBASE_COMMON_REPO_READ_TOKEN` when installing that file.

Do not restore a local `.github/actions/setup-python-deps` copy. Use `validityBase/vbase-github-actions/.github/actions/setup-python-deps@v1` for requirements-file based Python dependency setup.

## Workflows

### `.github/workflows/python-dependency-locks.yml`
- Runs on pull requests, pushes to `main`, and manual `workflow_dispatch`.
- Installs `requirements/lock/tools.txt` through `setup-python-deps@v1` with Python 3.12 and `require-hashes: "true"`.
- Regenerates `requirements/lock/docs.txt`, `requirements/lock/e2e.txt`, and `requirements/lock/tools.txt`; the workflow fails if committed lock files differ.
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
- Sets up Python 3.12 for reproducible release builds and CI parity.
- Installs `build` and `twine`, builds Python package distributions, and checks them with `twine`.
- Uploads the distribution artifact from the build job.
- Publishes to PyPI through trusted publishing with OIDC.

### `.github/workflows/file-integrity-e2e.yml`
- Runs on pull requests, pushes to `main`, and manual `workflow_dispatch`.
- Uses an OS matrix over `ubuntu-latest`, `macos-latest`, and `windows-latest`
  to cover the VDT-831 client-library platform matrix.
- Runs the OS matrix with `max-parallel: 1` because each job uses the same
  staging Bitwarden runner user/API key. Serial execution avoids overlapping
  blockchain transactions from the same live account while preserving OS
  coverage.
- Installs `requirements/lock/e2e.txt` through `setup-python-deps@v1` with
  Python 3.12 and `require-hashes: "true"`, installs
  `requirements-private.txt` with `VBASE_COMMON_REPO_READ_TOKEN`, installs the
  package in editable mode, and runs `python -m unittest discover -s tests -v`
  through `ops/scripts/btenv.sh`.
- Runtime app/API/S3 credentials come from the Bitwarden project
  `vbase-django-tools-cypress-runner-stg`, accessed with the GitHub secret
  `VBASE_DJANGO_TOOLS_CYPRESS_RUNNER_STG_TOKEN`.
- The tests intentionally use the app/Cypress runner secret names:
  `BASE_URL` / `SITE_URL`, `VBASE_API_KEY_CYPRESS`, `S3_VALIDATION_BUCKET`,
  `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY` / `AWS_SECRET_KEY`, and
  `AWS_REGION` / `AWS_DEFAULT_REGION`.
- Stored bytes are verified by reading the returned `file_object.file_path`
  directly from S3 and comparing exact byte length, SHA3-256 CID, and full
  content for text and binary files.
