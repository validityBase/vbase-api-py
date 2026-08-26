# GitHub Actions

## Policy
- Third-party actions are pinned by full commit SHA for reproducibility.
- Shared vBase-owned actions and reusable workflows use `validityBase/vbase-github-actions` with reviewed release tags such as `@v1`.
- Workflow permissions are declared explicitly and kept minimal.
- Secrets must come from GitHub Secrets or deployment configuration, never from committed files or logs.
- Dependency layout and lock policy are canonical in
  `internal/specs/python-dependency-hashes.md`.

## Dependencies

See `internal/specs/python-dependency-hashes.md` for dependency layout, lock
policy, and package metadata rules.

Do not restore a local `.github/actions/setup-python-deps` copy. Use `validityBase/vbase-github-actions/.github/actions/setup-python-deps@v1` for requirements-file based Python dependency setup.

## Workflows

### `.github/workflows/python-compatibility.yml`
- Runs on pull requests, pushes to `main`, and manual `workflow_dispatch`.
- Resolves the published runtime ranges from `requirements.in` on Python 3.11
  and 3.12.
- Builds and installs the package, checks dependency consistency with
  `python -m pip check`, and verifies that `vbase_api` imports successfully.

### `.github/workflows/python-dependency-locks.yml`
- Runs on pull requests, pushes to `main`, and manual `workflow_dispatch`.
- Installs `requirements/tools.txt` through `setup-python-deps@v1` with Python 3.12 and `require-hashes: "true"`.
- Regenerates `requirements/docs.txt`, `requirements/e2e.txt`, and `requirements/tools.txt`; the workflow fails if committed lock files differ.
- Installs `requirements/docs.txt` and checks installed dependency consistency with `python -m pip check`.
- Runs `tests.test_retries` against the checkout through `PYTHONPATH=src`
  without requiring live API credentials.

### `.github/workflows/documentation-publishing.yml`
- Runs on pushes to `main` and manual dispatch.
- Delegates to `validityBase/vbase-github-actions/.github/workflows/publish-docs.yml@v1`.
- Installs `requirements/docs.txt` with `require-hashes: true`.
- Builds Sphinx Markdown docs into `docs/_build/markdown` and rewrites generated module references before publishing.
- Publishes to the central docs repository.
- Uses `DOCS_REPO_ACCESS_TOKEN` for the central docs repository.

### `.github/workflows/repo-backup.yml`
- Runs daily at 02:17 UTC and can be triggered manually.
- Delegates to `validityBase/vbase-github-actions/.github/workflows/repo-backup.yml@v1`.
- Uses the reviewed moving major tag for validityBase-owned shared workflows so centrally reviewed fixes roll forward without per-repository pin updates.
- Creates a full-history git bundle, checksum, and metadata file under the shared `github-backups` object storage prefix.
- Passes `VBASE_COMMON_REPO_READ_TOKEN` and maps `VBASE_REPO_BACKUP_SECRETS_TOKEN` to the shared workflow's `BWS_ACCESS_TOKEN`.
- Reads object storage credentials from the `vbase-repo-backups` Bitwarden project instead of storing provider credentials directly in GitHub Secrets.

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
- Uses a matrix over `ubuntu-latest`, `macos-latest`, and `windows-latest`, plus
  `source` and `pypi` install sources, to cover the client-library platform
  matrix and the latest published PyPI package.
- Runs the matrix with `max-parallel: 1` to preserve the current sequential
  execution behavior while keeping platform and package-source coverage.
- Maps each OS job to a dedicated staging API key secret, then exposes that key
  to the test process as `VBASE_API_KEY`:
  `FILE_INTEGRITY_E2E_VBASE_API_KEY_UBUNTU`,
  `FILE_INTEGRITY_E2E_VBASE_API_KEY_MACOS`, and
  `FILE_INTEGRITY_E2E_VBASE_API_KEY_WINDOWS`.
- Installs `requirements/e2e.txt` through `setup-python-deps@v1` with
  Python 3.12 and `require-hashes: "true"`, then either installs the checkout in
  editable mode (`install_source=source`) or installs the latest published
  `vbase-api` package from PyPI (`install_source=pypi`), and runs
  `python -m unittest tests.test_file_integrity_e2e -v`.
- Exposes the selected install source to the tests as
  `VBASE_API_PACKAGE_SOURCE`; the tests log the imported package version/path
  and assert that the PyPI matrix leg does not import `vbase_api` from the
  repository checkout.
- Runtime app/API/S3 credentials come directly from GitHub Actions secrets:
  the OS-specific file-integrity API key secret, `S3_VALIDATION_BUCKET`,
  `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, and optional
  `AWS_SESSION_TOKEN`.
- Non-secret live E2E configuration comes from GitHub Actions variables:
  `BASE_URL` and `AWS_REGION`.
- Stored bytes are verified by reading the returned `file_object.file_path`
  directly from S3 and comparing exact byte length, SHA3-256 CID, and full
  content for text and binary files.
