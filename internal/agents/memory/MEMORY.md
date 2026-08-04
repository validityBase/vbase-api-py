# Agent Memory

## GitHub Actions
- Third-party GitHub Actions are pinned to full commit SHAs.
- vBase-owned shared actions and reusable workflows use reviewed `validityBase/vbase-github-actions` version tags.
- Dependency layout, lock policy, and package metadata rules are canonical in
  `internal/specs/python-dependency-hashes.md`; keep that as the only detailed
  copy.
- Documentation publishing delegates to `validityBase/vbase-github-actions/.github/workflows/publish-docs.yml@v1`.
- Python dependency setup uses `validityBase/vbase-github-actions/.github/actions/setup-python-deps@v1`; do not restore a local `.github/actions/setup-python-deps` copy.
- PyPI publishing uses trusted publishing through OIDC with `id-token: write`; do not add static PyPI API tokens.
- Repository backups use `.github/workflows/repo-backup.yml`, which delegates
  to the shared `repo-backup.yml@v1` workflow and resolves generic object
  storage credentials from the `vbase-repo-backups` Bitwarden project.

## Documentation Layout
- `CLAUDE.md` is the root instruction entry point and should stay short.
- `AGENTS.md` is a thin pointer for Codex, ChatGPT coding agents, and Copilot-style agents; do not duplicate full instructions there.
- Internal specs, guides, and persistent memory live under `internal/`.
- Published documentation source stays under `docs/`.
