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
- `requirements/src/docs.in` is the human-edited documentation publishing input.
- `requirements/lock/docs.txt` is generated from `requirements/src/docs.in` and
  includes package runtime and documentation build dependencies with hashes.
- `requirements/src/tools.in` is the human-edited lock-regeneration tooling
  input.
- `requirements/lock/tools.txt` is generated from `requirements/src/tools.in`
  and includes the minimal `pip-tools` environment with hashes.

Do not create a generated base/runtime lock for package metadata. Do not edit
generated `.txt` lock files by hand.

## Developer Workflow

Install pinned lock-generation tooling from the minimal lock before running
`pip-compile`. Do not bootstrap with an unpinned `pip install pip-tools`,
because a different `pip-tools` version can produce a different lockfile.

```bash
python -m pip install --require-hashes -r requirements/lock/tools.txt
```

To add or update a published runtime dependency:

```bash
# edit requirements.in
pip-compile --strip-extras --no-annotate --generate-hashes -o requirements/lock/docs.txt requirements/src/docs.in
```

To add or update a docs dependency:

```bash
# edit requirements/src/docs.in
pip-compile --strip-extras --no-annotate --generate-hashes -o requirements/lock/docs.txt requirements/src/docs.in
```

To update the lock-generation tooling, edit the pinned `pip-tools==...`
constraint in `requirements/src/tools.in`, then regenerate
`requirements/lock/tools.txt`.

```bash
# edit the pip-tools==... pin in requirements/src/tools.in
pip-compile --strip-extras --no-annotate --allow-unsafe --generate-hashes -o requirements/lock/tools.txt requirements/src/tools.in
```

## CI Enforcement

`.github/workflows/python-dependency-locks.yml` enforces this policy on pull
requests, pushes to `main`, and manual runs. It installs the minimal
lock-generation tooling lock with `require-hashes: "true"`, regenerates
terminal environment lock files, fails if generated files differ from committed
files, installs the docs lock, and checks the installed dependency environment
with `python -m pip check`.
