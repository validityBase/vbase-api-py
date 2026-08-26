# CLAUDE.md

This file provides minimal shared guidance for Claude Code and other agentic work in this repository.

## Project Overview

`vbase-api-py` is the Python client package for the vBase REST API. Package source lives under `src/vbase_api/`. Public documentation source lives under `docs/` and is published to the central docs repository by GitHub Actions.

## Development Commands

```bash
# Install the package locally
python -m pip install -r requirements.in
python -m pip install --no-deps --no-build-isolation -e .

# Build a distribution
python -m pip install build twine
python -m build
python -m twine check dist/*

# Build generated Markdown docs
python -m pip install --require-hashes -r requirements/docs.txt
sphinx-build -b markdown docs/ docs/_build/markdown

# Regenerate dependency locks
# See internal/specs/python-dependency-hashes.md.

# Run formatting hooks when available
pre-commit run --all-files
```

## Code Standards

- Dependency layout and lock policy are canonical in
  `internal/specs/python-dependency-hashes.md`; do not duplicate them here.
- Use Python `>=3.11` compatible syntax.
- Use `black` and `isort`; pre-commit configuration is in `.pre-commit-config.yaml`.
- Do not commit secrets, tokens, generated credentials, webhook URLs, or private environment payloads.

## GitHub Actions

- Third-party actions are pinned by full commit SHA.
- Shared vBase-owned actions and reusable workflows use reviewed `validityBase/vbase-github-actions` release tags such as `@v1`.
- Python dependency setup uses `validityBase/vbase-github-actions/.github/actions/setup-python-deps@v1` with generated requirements lock files.
- Documentation publishing delegates to `validityBase/vbase-github-actions/.github/workflows/publish-docs.yml@v1`.
- PyPI publishing uses trusted publishing through OIDC; do not add static PyPI API tokens.

See [internal/specs/github-actions.md](internal/specs/github-actions.md) for workflow details.

## Internal Documentation

- Persistent agent memory: [internal/agents/memory/MEMORY.md](internal/agents/memory/MEMORY.md)
- Dependency hashes: [internal/specs/python-dependency-hashes.md](internal/specs/python-dependency-hashes.md)
- Internal specs and guides: `internal/specs/`
- Public or generated documentation: `docs/`
