# GitHub Actions

## Policy
- Third-party actions are pinned by full commit SHA for reproducibility.
- Shared vBase-owned release workflows and composite actions are pinned by full
  commit SHA; each release-tools-ref matches its workflow SHA. Non-release
  workflows may use reviewed shared release tags such as `@v1`.
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
- Resolves the published runtime ranges from `requirements.in` across the
  Python versions declared in the workflow matrix.
- Builds and installs the package, checks dependency consistency with
  `python -m pip check`, and verifies that `vbase_api` imports successfully.
- Runs offline client request/response and verification-response
  compatibility tests.

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

### Python release workflow wrappers

- `prepare-release.yml` dispatches the shared `prepare-python-release.yml` with
  an explicit bump and this repository's version-file setting.
- `tag-release.yml` delegates merged Release PR handling to the shared
  `tag-python-release.yml`, including validation and publication dispatch.
- `publish-pypi.yml` calls `build-python-release.yml`, verifies the built
  distributions through live E2E, and uploads through the directly invoked
  PyPA publisher inside its caller-owned `pypi` job. It calls
  `github-python-release.yml` only after successful publication.
- Wrappers pin the shared workflow and release-tools-ref to the same commit.
  Repository settings and release invariants are in
  [pypi-releases.md](pypi-releases.md). Generic scripts and tests are maintained
  in the shared-actions repository, without local copies.
- The OIDC upload job retains this repository's workflow identity; there is no
  static PyPI token. Bot-created PR workflows may require maintainer approval.
- After a successful PyPI upload, `publish-pypi.yml` calls the file-integrity
  E2E workflow with the validated release tag to test that exact published
  version. Verification failure fails the workflow without undoing publication.
- The pre-publication E2E gate downloads `python-package-distributions` from
  the build job, installs the exact tagged version without using an index,
  and runs the live suite. Failure prevents upload. The publisher downloads
  the same artifact after this gate, with no rebuild or prerelease upload.

### `.github/workflows/source-e2e.yml`
- Runs daily, on pull requests, on pushes to `main`, and on manual
  `workflow_dispatch`.
- Tests the checked-out source through the reusable live E2E workflow, including
  the app API verification contract and file integrity.
  Skips forked and Dependabot pull requests because live E2E requires
  repository secrets.
- The daily schedule runs on the default branch using the UTC cron declared
  in the workflow and becomes active after merge.

### `.github/workflows/pypi-e2e.yml`
- Runs daily and on manual `workflow_dispatch`. It does not run on PRs or
  ordinary `main` pushes.
- Tests the latest stable PyPI package against the app API and file storage
  unless a published `release-tag` is
  supplied, in which case it tests that exact version using the tag's tests.
- Exposes a reusable call with a required `release-tag` for the publication
  workflow. Secrets are inherited through each reusable-workflow call.

### `.github/workflows/file-integrity-e2e.yml`
- Contains the shared execution steps, invoked through `workflow_call` with
  an `install-source` of `source`, `artifact`, or `pypi` and an optional
  `release-tag` (required by artifact callers).
- Uses a matrix over `ubuntu-24.04`, `macos-latest`, and `windows-latest`, plus
  the caller-selected install source. Source and published-package results
  appear in separately named workflows.
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
  `vbase-api` package from PyPI (`install_source=pypi`), and discovers
  `test_*_e2e.py`. Older release tags continue to run the tests available in
  that tag's checkout.
- Calls that supply a `release-tag` check out that tag's test suite. PyPI
  calls install the exact indexed version; artifact calls install the exact
  candidate wheel locally. Both remove the `v` prefix from the version.
  Callers pass live test secrets; credentials are never embedded in workflow
  inputs or source.
- Exposes the selected install source to the tests as
  `VBASE_API_PACKAGE_SOURCE`; the tests log the imported package version/path
  and assert that PyPI and artifact matrix legs do not import `vbase_api`
  from the repository checkout.
- Runtime app/API/S3 credentials come directly from GitHub Actions secrets:
  the OS-specific file-integrity API key secret, `S3_VALIDATION_BUCKET`,
  `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, and optional
  `AWS_SESSION_TOKEN`.
- Non-secret live E2E configuration comes from GitHub Actions variables:
  `BASE_URL` and `AWS_REGION`.
- Stored bytes are verified by reading the returned `file_object.file_path`
  directly from S3 and comparing exact byte length, SHA3-256 CID, and full
  content for text and binary files.
