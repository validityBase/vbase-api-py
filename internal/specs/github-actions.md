# GitHub Actions

## Policy
- Third-party actions are pinned by full commit SHA for reproducibility.
- Shared vBase-owned actions and reusable workflows use `validityBase/vbase-github-actions` with reviewed release tags such as `@v1`.
- Workflow permissions are declared explicitly and kept minimal.
- Python installs for docs and lock verification use generated hash-locked terminal environment requirements with `require-hashes`.
- Secrets must come from GitHub Secrets or deployment configuration, never from committed files or logs.

## Dependencies

Published runtime dependencies live in `requirements.in` as abstract ranges and
are read by `pyproject.toml`. Documentation publishing, live E2E tests, and
lock tooling are terminal environments owned by this repository, so their
generated lock files live under `requirements/` and are installed with
`require-hashes`.

Do not restore a local `.github/actions/setup-python-deps` copy. Use `validityBase/vbase-github-actions/.github/actions/setup-python-deps@v1` for requirements-file based Python dependency setup.

## Workflows

### `.github/workflows/python-dependency-locks.yml`
- Runs on pull requests, pushes to `main`, and manual `workflow_dispatch`.
- Installs `requirements/tools.txt` through `setup-python-deps@v1` with Python 3.12 and `require-hashes: "true"`.
- Regenerates `requirements/docs.txt`, `requirements/e2e.txt`, and `requirements/tools.txt`; the workflow fails if committed lock files differ.
- Installs `requirements/docs.txt` and checks installed dependency consistency with `python -m pip check`.

### `.github/workflows/documentation-publishing.yml`
- Runs on pushes to `main` and manual dispatch.
- Delegates to `validityBase/vbase-github-actions/.github/workflows/publish-docs.yml@v1`.
- Installs `requirements/docs.txt` with `require-hashes: true`.
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
- Skips forked pull requests because the live E2E job requires repository
  secrets. Same-repository pull requests, pushes, and manual runs execute the
  job.
- Uses an OS matrix over `ubuntu-latest`, `macos-latest`, and `windows-latest`
  to cover the client-library platform matrix.
- Runs the OS matrix with `max-parallel: 1` because each job uses the same
  staging API key. Serial execution avoids overlapping blockchain transactions
  from the same live account while preserving OS coverage.
- Installs `requirements/e2e.txt` through `setup-python-deps@v1` with
  Python 3.12 and `require-hashes: "true"`, installs the package in editable
  mode, and runs `python -m unittest tests.test_file_integrity_e2e -v`.
- Runtime app/API/S3 credentials come directly from GitHub Actions secrets:
  `VBASE_API_KEY`, `BASE_URL`, `S3_VALIDATION_BUCKET`, `AWS_ACCESS_KEY_ID`,
  `AWS_SECRET_ACCESS_KEY`, optional `AWS_SESSION_TOKEN`, and `AWS_REGION`.
- Stored bytes are verified by reading the returned `file_object.file_path`
  directly from S3 and comparing exact byte length, SHA3-256 CID, and full
  content for text and binary files.
