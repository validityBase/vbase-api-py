# Python Dependency Hashes

This repository separates published package dependencies from terminal
environment locks.

`vbase-api-py` is an intermediate client library installed into downstream
applications, so published runtime dependencies must stay abstract and
resolver-friendly. CI docs publishing and lock tooling are terminal
environments owned by this repo, so those installs use pip hash-checking mode
for reproducibility.

Lock files are generated with Python 3.12 for CI parity. The package metadata
may still support older Python versions, but the committed locks represent the
CI install environment.

## Files

- `requirements.in` is the human-edited published runtime dependency source.
  It is read by `pyproject.toml` and must use dependency ranges rather than
  hash-locked pins. It is included in source distributions through
  `MANIFEST.in` so dynamic package metadata can be resolved during builds.
- `requirements/docs.in` is the human-edited documentation publishing input.
- `requirements/docs.txt` is generated from `requirements/docs.in` and
  includes package runtime and documentation build dependencies with hashes.
- `requirements/e2e.in` is the human-edited live E2E test environment
  input. It includes the package runtime dependencies plus public test-only S3
  dependencies.
- `requirements/e2e.txt` is generated from `requirements/e2e.in` and
  includes live E2E dependencies with hashes.
- `requirements/tools.in` is the human-edited lock-regeneration tooling
  input.
- `requirements/tools.txt` is generated from `requirements/tools.in`
  and includes the minimal `pip-tools` environment with hashes.

Do not create a generated base/runtime lock for package metadata. Do not edit
generated `.txt` lock files by hand.

## Developer Workflow

Install pinned lock-generation tooling from the minimal lock before running
`pip-compile`. Do not bootstrap with an unpinned `pip install pip-tools`,
because a different `pip-tools` version can produce a different lockfile.

```bash
python -m pip install --require-hashes -r requirements/tools.txt
```

To add or update a published runtime dependency:

```bash
# edit requirements.in
pip-compile --strip-extras --no-annotate --generate-hashes -o requirements/docs.txt requirements/docs.in
```

To add or update a docs dependency:

```bash
# edit requirements/docs.in
pip-compile --strip-extras --no-annotate --generate-hashes -o requirements/docs.txt requirements/docs.in
```

To add or update a live E2E dependency:

```bash
# edit requirements/e2e.in
pip-compile --strip-extras --no-annotate --allow-unsafe --generate-hashes -o requirements/e2e.txt requirements/e2e.in
```

To update the lock-generation tooling, edit the pinned `pip-tools==...`
constraint in `requirements/tools.in`, then regenerate
`requirements/tools.txt`.

```bash
# edit the pip-tools==... pin in requirements/tools.in
pip-compile --strip-extras --no-annotate --allow-unsafe --generate-hashes -o requirements/tools.txt requirements/tools.in
```

## CI Enforcement

`.github/workflows/python-dependency-locks.yml` enforces this policy on pull
requests, pushes to `main`, and manual runs. It installs the minimal
lock-generation tooling lock with `require-hashes: "true"`, regenerates
terminal environment lock files, fails if generated files differ from committed
files, installs the docs lock, and checks the installed dependency environment
with `python -m pip check`.
