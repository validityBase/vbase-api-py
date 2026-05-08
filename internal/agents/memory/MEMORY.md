# Agent Memory

## GitHub Actions
- Third-party GitHub Actions are pinned to full commit SHAs.
- vBase-owned shared actions use reviewed `validityBase/vbase-github-actions` version tags.
- The local `.github/actions/setup-python-deps` action is intentional: this repo has `pyproject.toml` packaging and no requirements files, so it supports `mode: build` and `mode: docs`.
- Documentation publishing uses `validityBase/vbase-github-actions/.github/actions/publish-docs@v1`.
- PyPI publishing uses trusted publishing through OIDC with `id-token: write`; do not add static PyPI API tokens.
