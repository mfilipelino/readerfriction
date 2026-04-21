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
