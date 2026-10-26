# Contributing

## Development setup

Fork and clone the repository, then run these commands from the repository root
with Python 3.11 or 3.12 for the development tools. The package supports Python
3.8+; CI tests installation and client behavior on Python 3.8 and 3.11.
The activation command below is for macOS/Linux;
on Windows PowerShell use `venv\Scripts\Activate.ps1`.

```bash
python -m venv venv
source venv/bin/activate
python -m pip install -r requirements/e2e.in
python -m pip install pre-commit build twine
python -m pip install --no-deps --no-build-isolation -e .
pre-commit install
```

`requirements/e2e.in` includes runtime dependencies, build support, and the S3
client used by the tests. CI installs the generated Linux lock file with
`python -m pip install --require-hashes -r requirements/e2e.txt`.
See [dependency guidance](internal/specs/python-dependency-hashes.md) before
changing dependency inputs or regenerating lock files.

## Checks

Run the same dependency and import checks as the compatibility workflow:

```bash
python -m pip check
python -c "import vbase_api"
pre-commit run --all-files
```

The hooks run Black, isort, and file/YAML checks. To run the test suite:

```bash
python -m unittest discover -s tests -v
```

The client tests run without credentials. To check runtime compatibility in a
separate Python 3.8 or 3.11 virtual environment, run:

```bash
python -m pip install .
python -m pip check
python -m unittest tests.test_api_client -v
```

The suite also contains live file-integrity integration tests. Without the
required API and AWS credentials they skip; a skipped run does not verify live
behavior. See the [test environment guide](internal/specs/e2e-file-integrity.md)
for the required environment variables and service setup. Never put credentials
in issues, commits, or test output.

Check distribution packaging when changing package metadata:

```bash
python -m build
python -m twine check dist/*
```

## Reporting issues

Check [existing issues](https://github.com/validityBase/vbase-api-py/issues)
before opening a bug report or feature request. Include the package and Python
versions, operating system, steps to reproduce, and expected versus actual
behavior. Use the provided issue template and redact credentials and private data.
Do not report security vulnerabilities or share exploit details in public issues.

## Everyday pull requests

Add user-facing changes to `CHANGELOG.md` under `[Unreleased]`, grouped as
Added, Changed, Deprecated, Removed, Fixed, or Security. Include the PR reference
when available. Internal changes may omit an entry with an explanation in the
PR; dependency changes that affect users still need an entry.

Do not change `src/vbase_api/_version.py` in ordinary PRs. Keep related tests,
documentation, and specifications aligned. Shared release tooling is tested in
`validityBase/vbase-github-actions`.

## Releases

Follow [RELEASE_MANAGEMENT.md](RELEASE_MANAGEMENT.md) to run **Prepare release**
with a patch, minor, or major increment, approve CI workflows for the generated
Release PR, review it, and verify publication.

Ordinary PRs do not publish packages. Automation updates the version and
changelog in a Release PR. Merging that reviewed PR to `main` automatically
pushes its matching tag and starts publication.
