# E2E File Integrity

## Scope

`vbase-api-py` owns client-library coverage for stamped-file integrity
scenarios. The tests verify that the Python client's public stamping methods
remain compatible with the app REST API and that stored file objects are
byte-identical to the original source bytes. CI runs the same live E2E scenarios
against both the checked-out source package and the latest published
`vbase-api` package from PyPI.

The app repository owns Cypress coverage for the UI and direct app API flows.
This repository owns Python client coverage for:

- `VBaseAPIClient.create_stamp(...)`
- `VBaseAPIClient.upload_stamped_file(...)`

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

The live tests are skipped unless the required environment is present.

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

The workflow sets `VBASE_API_PACKAGE_SOURCE` to `source` or `pypi` for each
matrix job. The test logs the imported package version/path and asserts that the
PyPI matrix leg imports `vbase_api` from the installed package rather than the
repository checkout.

## Traceability

| Requirement | Use Case | Test |
| --- | --- | --- |
| Client-library stamp-time upload preserves downloaded bytes for text and binary files | UC-A | `tests/test_file_integrity_e2e.py::VBaseAPIClientFileIntegrityE2ETests.test_create_stamp_with_storage_preserves_downloaded_file_bytes` |
| Client-library stamp-time upload returns expected `object_cid` and collection `set_cid` | UC-A | `tests/test_file_integrity_e2e.py::VBaseAPIClientFileIntegrityE2ETests.test_create_stamp_with_storage_preserves_downloaded_file_bytes` |
| Client-library manual stamped-file upload preserves downloaded bytes for text and binary files | UC-B | `tests/test_file_integrity_e2e.py::VBaseAPIClientFileIntegrityE2ETests.test_upload_stamped_file_preserves_downloaded_file_bytes` |
| Client-library manual stamped-file upload returns expected `object_cid` and collection `set_cid` | UC-B | `tests/test_file_integrity_e2e.py::VBaseAPIClientFileIntegrityE2ETests.test_upload_stamped_file_preserves_downloaded_file_bytes` |
| File-integrity client tests run across Linux, macOS, and Windows | UC-A, UC-B | `.github/workflows/file-integrity-e2e.yml` |
| Latest published `vbase-api` PyPI package remains compatible with the app REST API | UC-A, UC-B | `.github/workflows/file-integrity-e2e.yml` with `install_source=pypi` |
