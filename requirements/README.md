# Python Requirements

Published package dependencies live in `requirements.in` as abstract ranges.
Do not generate a hash-locked base/runtime requirements file for package
metadata.

Human-edited terminal environment inputs live in `requirements/*.in`.
Generated hash-locked terminal environment files live in `requirements/*.txt`.

Do not edit generated `.txt` files by hand. Regenerate them with
the exact `pip-compile` command below.

## Regenerate Locks

Install the pinned lock tooling first:

```bash
python -m pip install --require-hashes -r requirements/tools.txt
```

Regenerate terminal environment lock files:

```bash
pip-compile --strip-extras --no-annotate --generate-hashes -o requirements/docs.txt requirements/docs.in
pip-compile --strip-extras --no-annotate --allow-unsafe --generate-hashes -o requirements/e2e.txt requirements/e2e.in
pip-compile --strip-extras --no-annotate --allow-unsafe --generate-hashes -o requirements/tools.txt requirements/tools.in
```

Private helper dependencies are installed separately from
`requirements/private.txt` with `--no-deps` and require
`VBASE_COMMON_REPO_READ_TOKEN`.
