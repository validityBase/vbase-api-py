# Agent Memory

## GitHub Actions
- Third-party GitHub Actions are pinned to full commit SHAs.
- vBase-owned shared actions use reviewed `validityBase/vbase-github-actions` version tags.
- The local `.github/actions/setup-python-deps` action is intentional: this repo has `pyproject.toml` packaging and no requirements files, so it supports `mode: build` and `mode: docs`.
- Documentation publishing uses `validityBase/vbase-github-actions/.github/actions/publish-docs@v1`.
- PyPI publishing uses trusted publishing through OIDC with `id-token: write`; do not add static PyPI API tokens.

## Documentation Layout
- `CLAUDE.md` is the root instruction entry point and should stay short.
- `AGENTS.md` is a thin pointer for Codex, ChatGPT coding agents, and Copilot-style agents; do not duplicate full instructions there.
- Internal specs, guides, and persistent memory live under `internal/`.
- Published documentation source stays under `docs/`.
