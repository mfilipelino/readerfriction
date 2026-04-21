# ReaderFriction — Specification

This directory is the **normative** specification for ReaderFriction v0.1.
Implementation in `src/` and tests in `tests/` must conform to it.

## How to read this spec

1. **`requirements.md`** — Numbered EARS requirements (`REQ-###`). Every
   requirement must be satisfied by at least one test (see `traceability.md`).
2. **`architecture.md`** — Module boundaries and the data-flow pipeline.
3. **`metrics.md`** — Mathematical definitions of the seven metrics and the
   aggregate score.
4. **`wrapper-heuristic.md`** — The thin-wrapper classifier rules.
5. **`cli.md`** — Command contracts: arguments, exit codes, stdout/stderr.
6. **`config.md`** — `[tool.readerfriction]` configuration keys.
7. **`contracts/*.schema.json`** — JSON Schemas for every CLI output payload.
   Source of truth is `src/readerfriction/models.py`; these files are
   generated and committed so diffs are reviewable.
8. **`examples/`** — Golden input projects + expected outputs used both as
   documentation and as end-to-end tests.
9. **`traceability.md`** — Matrix linking each requirement to modules + tests.

## Change protocol

- A spec change lands **before** the code change.
- Spec changes must update `traceability.md` in the same commit.
- Breaking changes bump the minor version until 1.0, the major after.

## Non-goals for v0.1

Taken verbatim from `start.md`:

- Perfect dynamic dispatch resolution
- Runtime tracing
- Multi-language support
- Framework-specific magic

These are explicitly **out of scope** and should be rejected at review time.
