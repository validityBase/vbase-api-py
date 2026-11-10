# E2E File Integrity

## Scope

`vbase-api-py` owns client-library coverage for stamped-file integrity
scenarios. The tests verify that the Python client's public stamping methods
remain compatible with the app REST API and that stored file objects are
byte-identical to the original source bytes. CI runs the same live E2E scenarios
against the checked-out source package through `source-e2e.yml` on PRs,
`main` pushes, daily schedules, and manual runs. A separate `pypi-e2e.yml`
tests the latest published `vbase-api` package daily and on manual runs.
After a successful PyPI upload, the publication workflow calls PyPI E2E
against the exact released version using the release tag's test suite. Both
entry workflows share the steps in `file-integrity-e2e.yml`.

The publication workflow also runs the same suite against its built
distribution before uploading. It installs the exact tagged version from the
build artifact without querying a package index. Only a passing candidate
allows publication of that same artifact; no RC package is uploaded to PyPI.

The app repository owns Cypress coverage for the UI and direct app API flows.
This repository owns Python client coverage for:

- `VBaseAPIClient.create_stamp(...)`
- `VBaseAPIClient.upload_stamped_file(...)`
- `VBaseAPIClient.verify_stamps(...)` against unstamped and newly stamped CIDs

`tests/test_app_api_compatibility_e2e.py` is the client-owned compatibility
check. It calls the live app through the installed Python client and checks
both an empty verification response and a complete stamp-and-verify cycle.
The app PR workflow checks out this test from the client repository and runs it
against the PR's Docker app with the latest published `vbase-api` package. The
app's daily release workflow runs it against the selected deployed app; its
production run disables stamp creation and verifies only an unused CID. The
client's source PR and daily PyPI E2E workflows discover the same test.

## Covered Use Cases

### UC-A: `create_stamp` with storage preserves downloadable file bytes

For both text and binary files, the live E2E test:

1. creates a unique collection through `VBaseAPIClient.create_collection(...)`
2. calls `VBaseAPIClient.create_stamp(...)` with `store_stamped_file=True`
3. verifies the response `commitment_receipt.object_cid` and `set_cid`
4. resolves the returned `file_object.file_path`
5. downloads the stored object from `S3_VALIDATION_BUCKET` using that path
6. compares downloaded byte length, SHA3-256 CID, and exact bytes

### UC-B: `upload_stamped_file` preserves downloadable file bytes

For both text and binary files, the live E2E test:

1. creates a unique collection through `VBaseAPIClient.create_collection(...)`
2. stamps the expected object CID with `store_stamped_file=False`
3. waits until the stamp is visible through `VBaseAPIClient.verify_stamps(...)`
4. uploads the matching source file through `VBaseAPIClient.upload_stamped_file(...)`
5. verifies the upload response `commitment_receipt.object_cid` and `set_cid`
6. resolves the returned `file_object.file_path`
7. downloads the stored object from `S3_VALIDATION_BUCKET` using that path
8. compares downloaded byte length, SHA3-256 CID, and exact bytes

## Environment

Local runs skip live tests unless the required environment is present. In
GitHub Actions, the app API compatibility test fails if its API key is missing;
the client E2E workflow also validates its secrets before running tests.

CI loads credential values from GitHub Actions secrets and non-secret live test
configuration from GitHub Actions variables so the public package repository
keeps the live test wiring small and self-contained.

Required GitHub Actions secrets for Python client API calls:

- `FILE_INTEGRITY_E2E_VBASE_API_KEY_UBUNTU`
- `FILE_INTEGRITY_E2E_VBASE_API_KEY_MACOS`
- `FILE_INTEGRITY_E2E_VBASE_API_KEY_WINDOWS`

The workflow maps the OS-specific secret for the current matrix job into the
test process as `VBASE_API_KEY`. Local runs may still provide `VBASE_API_KEY`
directly.

Non-secret variable for Python client API calls:

- `BASE_URL`; defaults to `https://staging.app.vbase.com` if absent

Required secrets for stored-object downloads:

- `S3_VALIDATION_BUCKET`
- `AWS_ACCESS_KEY_ID`
- `AWS_SECRET_ACCESS_KEY`
- `AWS_SESSION_TOKEN` when temporary credentials are used

Non-secret variable for stored-object downloads:

- `AWS_REGION` or `AWS_DEFAULT_REGION`; defaults to `us-east-1` if both are
  absent

Optional:

- `FILE_INTEGRITY_E2E_TIMEOUT` defaults to `60`
- `FILE_INTEGRITY_E2E_API_WAIT_SECONDS` defaults to `60` for retrying transient
  live API `5xx` responses while setting up test collections
- `FILE_INTEGRITY_E2E_INDEX_WAIT_SECONDS` defaults to `120`
- `FILE_INTEGRITY_E2E_STORAGE_WAIT_SECONDS` defaults to `120`

The tests read S3 directly instead of calling the app web `/storage/download/`
endpoint because the app endpoint is protected by Django session login and is
already covered by Cypress in the app repository. Direct S3 reads keep this repo
focused on the Python client -> app REST API -> stored object contract without
adding a test-only app endpoint.

The workflow sets `VBASE_API_PACKAGE_SOURCE` to `source`, `artifact`, or `pypi` for each
matrix job. The test logs the imported package version/path and asserts that the
PyPI and artifact matrix legs import `vbase_api` from the installed package
rather than the repository checkout.

## Traceability

| Requirement | Use Case | Test |
| --- | --- | --- |
| Python client parses empty and populated app verification responses | App API compatibility | `tests/test_app_api_compatibility_e2e.py` |
| Client-library stamp-time upload preserves downloaded bytes for text and binary files | UC-A | `tests/test_file_integrity_e2e.py::VBaseAPIClientFileIntegrityE2ETests.test_create_stamp_with_storage_preserves_downloaded_file_bytes` |
| Client-library stamp-time upload returns expected `object_cid` and collection `set_cid` | UC-A | `tests/test_file_integrity_e2e.py::VBaseAPIClientFileIntegrityE2ETests.test_create_stamp_with_storage_preserves_downloaded_file_bytes` |
| Client-library manual stamped-file upload preserves downloaded bytes for text and binary files | UC-B | `tests/test_file_integrity_e2e.py::VBaseAPIClientFileIntegrityE2ETests.test_upload_stamped_file_preserves_downloaded_file_bytes` |
| Client-library manual stamped-file upload returns expected `object_cid` and collection `set_cid` | UC-B | `tests/test_file_integrity_e2e.py::VBaseAPIClientFileIntegrityE2ETests.test_upload_stamped_file_preserves_downloaded_file_bytes` |
| File-integrity client tests run across Linux, macOS, and Windows | UC-A, UC-B | `.github/workflows/file-integrity-e2e.yml` |
| Latest published `vbase-api` PyPI package remains compatible with the app REST API | UC-A, UC-B | `.github/workflows/pypi-e2e.yml` |
| Candidate distribution passes live E2E before upload | UC-A, UC-B | `.github/workflows/publish-pypi.yml` with `install-source=artifact` |
