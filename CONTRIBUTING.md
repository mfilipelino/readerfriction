# Contributing to ReaderFriction

Thank you for your interest! ReaderFriction is a young project; small,
focused contributions are the easiest to review and land.

## Development setup

```bash
uv sync --all-extras
uv run pytest
uv run ruff check
uv run pyright
```

## Ground rules

1. **Spec-first.** If your change alters observable behaviour, update `spec/`
   in the same pull request. `spec/traceability.md` must reference any new
   requirement id.
2. **Tests required.** Every new module ships with unit tests. Every new
   requirement gets an integration test whose id contains the `REQ-###`
   number.
3. **No scope creep.** v0.1 non-goals are listed in `spec/requirements.md`
   (REQ-900..REQ-903). Issues proposing those features will be deferred.
4. **Determinism.** Outputs must be byte-identical across runs on the same
   inputs.

## Commit messages

Imperative, present tense, short first line (≤ 72 chars). Reference relevant
`REQ-###` ids in the body when meaningful.

## Code style

`ruff` and `pyright` are authoritative. Run both before opening a PR.

## Release process

1. Bump `version` in `pyproject.toml` and add a `## [x.y.z] - YYYY-MM-DD`
   entry to `CHANGELOG.md`. Commit on `main`.
2. `uv build` locally and run `uvx twine check dist/*` to sanity-check
   metadata.
3. Tag: `git tag -a v0.1.0 -m "v0.1.0" && git push --tags`.
4. The `release` workflow builds the sdist + wheel, publishes to PyPI via
   [trusted publishing](https://docs.pypi.org/trusted-publishers/), and
   attaches the artifacts to a GitHub Release.

Trusted publishing requires a one-time PyPI configuration: add this repo as
a trusted publisher for the `readerfriction` project with environment name
`pypi` (matches `.github/workflows/release.yml`). No API tokens live in the
repo.
