# CLAUDE.md

This file provides minimal shared guidance for Claude Code and other agentic work in this repository.

## Project Overview

`vbase-api-py` is the Python client package for the vBase REST API. Package source lives under `src/vbase_api/`. Public documentation source lives under `docs/` and is published to the central docs repository by GitHub Actions.

## Development Commands

```bash
# Install the package locally
python -m pip install -e .

# Build a distribution
python -m pip install build
python -m build

# Build generated Markdown docs
python -m pip install -e . sphinx sphinx-markdown-builder
sphinx-build -b markdown docs/ docs/_build/markdown

# Run formatting hooks when available
pre-commit run --all-files
```

## Code Standards

- Python package metadata is in `pyproject.toml`; keep runtime dependencies there unless this repo adopts requirements lock files separately.
- Use Python `>=3.8` compatible syntax unless the package metadata changes.
- Use `black` and `isort`; pre-commit configuration is in `.pre-commit-config.yaml`.
- Do not commit secrets, tokens, generated credentials, webhook URLs, or private environment payloads.

## GitHub Actions

- Third-party actions are pinned by full commit SHA.
- Shared vBase-owned actions use reviewed `validityBase/vbase-github-actions` release tags such as `@v1`.
- This repository intentionally keeps `.github/actions/setup-python-deps/action.yml` because packaging/docs jobs are driven by `pyproject.toml` modes rather than requirements files.
- PyPI publishing uses trusted publishing through OIDC; do not add static PyPI API tokens.

See [internal/specs/github-actions.md](internal/specs/github-actions.md) for workflow details.

## Internal Documentation

- Persistent agent memory: [internal/agents/memory/MEMORY.md](internal/agents/memory/MEMORY.md)
- Internal specs and guides: `internal/specs/`
- Public or generated documentation: `docs/`
