# Development

This page is for contributors working on `llama-index-opendma`.
The project uses [uv](https://docs.astral.sh/uv/) for dependency management,
builds, and command execution.

## Setup

Create or update the local development environment:

```bash
uv sync --all-packages --dev
```

When working with examples that parse richer document formats, install the
optional LlamaIndex reader packages into the environment:

```bash
uv run --with llama-index-readers-file --with llama-index-readers-docling python --version
```

After dependency changes, run `uv sync --all-packages --dev` again to update the
lockfile and local environment.

## Package Layout

This repository is a uv workspace containing multiple publishable packages:

- `packages/llama-index-readers-opendma`: reader integration
- `packages/llama-index-retrievers-opendma`: retriever integration
- `packages/llama-index-tools-opendma`: tools integration

## Common Commands

Run tests:

```bash
uv run pytest
uv run pytest packages/llama-index-readers-opendma/tests/unit
uv run pytest packages/llama-index-readers-opendma/tests/integration
uv run pytest packages/llama-index-retrievers-opendma/tests/unit
uv run pytest packages/llama-index-tools-opendma/tests/unit
```

Run integration tests against the tutorial repository:

```bash
docker run -p 8080:8080 ghcr.io/opendma/tutorial-xmlrepo:0.8.1
OPENDMA_TUTORIAL_ENDPOINT=http://localhost:8080/opendma
uv run pytest packages/llama-index-readers-opendma/tests/integration
```

On PowerShell:

```powershell
docker run -p 8080:8080 ghcr.io/opendma/tutorial-xmlrepo:0.8.1
$env:OPENDMA_TUTORIAL_ENDPOINT = "http://localhost:8080/opendma"
uv run pytest packages\llama-index-readers-opendma\tests\integration
```

Lint, format, and type-check:

```bash
uv run ruff check .
uv run ruff format .
uv run --package llama-index-readers-opendma mypy -p llama_index.readers.opendma
uv run --package llama-index-retrievers-opendma mypy -p llama_index.retrievers.opendma
uv run --package llama-index-tools-opendma mypy -p llama_index.tools.opendma
uv run --package llama-index-readers-opendma mypy --explicit-package-bases packages/llama-index-readers-opendma/tests
uv run --package llama-index-retrievers-opendma mypy --explicit-package-bases packages/llama-index-retrievers-opendma/tests
uv run --package llama-index-tools-opendma mypy --explicit-package-bases packages/llama-index-tools-opendma/tests
```

Build all packages:

```bash
uv build --all-packages
```

## Test Locations

- `packages/llama-index-readers-opendma/tests/unit`: in-process tests for
  reader validation and pure reader behavior.
- `packages/llama-index-readers-opendma/tests/integration`: tests against the
  OpenDMA tutorial repository.
- `packages/llama-index-retrievers-opendma/tests/unit`: in-process tests for
  retriever validation and query generation.
- `packages/llama-index-tools-opendma/tests/unit`: in-process tests for
  tools.
- `docs/examples`: runnable examples, not part of the automated test suite.

## Release

Prepare and publish a release. Each package has its own version in its package
`pyproject.toml`; update every package being released before building.

```bash
OPENDMA_TUTORIAL_ENDPOINT=http://localhost:8080/opendma
uv sync --all-packages --dev
uv run pytest
uv run ruff check .
uv run --package llama-index-readers-opendma mypy -p llama_index.readers.opendma
uv run --package llama-index-retrievers-opendma mypy -p llama_index.retrievers.opendma
uv run --package llama-index-tools-opendma mypy -p llama_index.tools.opendma
uv build --all-packages
git tag X.Y.Z
git push origin X.Y.Z
uv publish
```

The root `pyproject.toml` is a workspace configuration and is not published.
Published versions live in:

- `packages/llama-index-readers-opendma/pyproject.toml`
- `packages/llama-index-retrievers-opendma/pyproject.toml`
- `packages/llama-index-tools-opendma/pyproject.toml`

If your `uv` version supports package-scoped version changes, you can use:

```bash
# remove .dev before building a release
uv version --bump stable
uv version --package llama-index-readers-opendma --bump stable
uv version --package llama-index-retrievers-opendma --bump stable
uv version --package llama-index-tools-opendma --bump stable
# bump to next minor/major and add .dev
uv version --bump minor --bump dev
uv version --package llama-index-readers-opendma --bump minor --bump dev
uv version --package llama-index-retrievers-opendma --bump minor --bump dev
uv version --package llama-index-tools-opendma --bump minor --bump dev
```

Make sure to manually update `__version__` in `packages/*/src/__init__.py` as
it is not touched by `uv version --bump`.

Double check that the dependency on `llama-index-readers-opendma` in
`llama-index-retrievers-opendma` and `llama-index-tools-opendma` is updated
to match the new version.

Otherwise, edit the package `pyproject.toml` files directly.

Before publishing, make sure `dist/` only contains artifacts intended for this
release. Use `uv publish --token` or the standard PyPI token environment
variables according to the release environment.
