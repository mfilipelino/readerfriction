# Requirements (EARS)

Each requirement uses **EARS** form:

- *WHEN* `<trigger>` **the system SHALL** `<response>`
- *WHILE* `<state>` **the system SHALL** `<response>`
- *IF* `<condition>` **THEN the system SHALL** `<response>`
- **The system SHALL** `<ubiquitous invariant>`

Test IDs embed the requirement ID, e.g. `test_req_012_scan_emits_json`.

---

## Installability & packaging

- **REQ-001** — The system SHALL ship as a Python package named
  `readerfriction` installable via `uv pip install -e .`.
- **REQ-002** — WHEN the package is installed THEN the system SHALL register a
  console script named `readerfriction` that dispatches to
  `readerfriction.cli:app`.
- **REQ-003** — The system SHALL target Python ≥ 3.11 and SHALL NOT import
  third-party libraries outside those declared in `pyproject.toml`.

## CLI surface

- **REQ-010** — The system SHALL expose exactly five commands: `scan`,
  `trace`, `explain`, `report`, `diff`.
- **REQ-011** — WHEN invoked with `--help` THEN each command SHALL print a
  usage summary listing its flags and exit 0.
- **REQ-012** — WHEN invoked with `--format json` THEN the system SHALL write
  a payload that validates against the corresponding schema in
  `spec/contracts/`.
- **REQ-013** — WHEN invoked with `--format markdown` THEN the system SHALL
  write deterministic markdown; two runs on the same input SHALL produce
  byte-identical output.
- **REQ-014** — WHEN `--out <path>` is provided THEN the system SHALL write
  the report to `<path>` and print nothing to stdout beyond a one-line
  completion notice.

## Discovery

- **REQ-020** — WHEN given a directory path THEN the system SHALL recursively
  find all `*.py` files under that path.
- **REQ-021** — The system SHALL exclude the following directories by
  default: `venv`, `.venv`, `build`, `dist`, `__pycache__`, `.git`, `.tox`,
  `.mypy_cache`, `.pytest_cache`, `.ruff_cache`.
- **REQ-022** — WHEN `--exclude <glob>` is passed THEN the system SHALL
  additionally exclude files whose path matches the glob.
- **REQ-023** — The system SHALL return discovered files in lexicographic
  order for determinism.

## Parsing

- **REQ-030** — WHEN parsing a Python file THEN the system SHALL produce a
  `ModuleIR` containing every top-level and nested `FunctionDef` /
  `AsyncFunctionDef`.
- **REQ-031** — IF parsing fails with `SyntaxError` THEN the system SHALL
  record the error in `ScanResult.parse_errors` and continue with remaining
  files (the scan SHALL NOT abort).
- **REQ-032** — Each `FunctionIR` SHALL record: `name`, `qualname`, `file`,
  `lineno`, `arg_count`, `is_async`, and the raw AST body (used only by the
  wrapper classifier).

## Entrypoint detection

- **REQ-040** — The system SHALL mark a function as an entrypoint when any of:
  (a) its name is `main`; (b) it is called from an `if __name__ ==
  "__main__":` block; (c) it is decorated with `@app.command`,
  `@app.callback`, `@click.command`, `@click.group`, or any decorator whose
  attribute name is `command`.
- **REQ-041** — IF no entrypoint is detected in a scanned project THEN the
  system SHALL fall back to treating every *public* top-level function
  (name not starting with `_`) as an entrypoint and SHALL emit a warning.

## Call graph

- **REQ-050** — The system SHALL build a `networkx.DiGraph` whose nodes are
  functions and whose edges represent resolved static calls.
- **REQ-051** — IF a call target cannot be resolved THEN the system SHALL
  route the edge to a sentinel node `<external>` and mark the edge
  `external=True`.
- **REQ-052** — The system SHALL preserve cycles in the call graph; WHILE
  traversing THEN it SHALL NOT enter an infinite loop (visited-set guards
  required).

## Metrics (see `metrics.md`)

- **REQ-060** — The system SHALL compute `trace_depth` per `metrics.md §1`.
- **REQ-061** — The system SHALL compute `file_jumps` per `metrics.md §2`.
- **REQ-062** — The system SHALL compute `wrapper_depth` per `metrics.md §3`.
- **REQ-063** — The system SHALL compute `thin_wrapper_count` per
  `metrics.md §4`.
- **REQ-064** — The system SHALL compute `flow_fragmentation` per
  `metrics.md §5`.
- **REQ-065** — The system SHALL compute `context_width` per `metrics.md §6`.
- **REQ-066** — The system SHALL compute `pass_through_ratio` per
  `metrics.md §7`.
- **REQ-068** — The system SHALL compute `long_files` per
  `metrics.md §7a`. The default ``max_file_lines`` is 500, overridable
  via ``[tool.readerfriction].max_file_lines`` (REQ-082 extends to this
  key).
- **REQ-067** — The system SHALL compute the aggregate
  `reader_friction_score` using the weighted sum defined in `metrics.md §8`.

## Thin-wrapper classifier (see `wrapper-heuristic.md`)

- **REQ-070** — The system SHALL evaluate eight sub-rules per function and
  classify a function as a thin wrapper when the number of matched rules
  meets or exceeds `Config.wrapper_threshold` (default 6).
- **REQ-071** — WHEN a classification is produced THEN the system SHALL
  record which sub-rules matched, enabling `explain` output.

## Configurability

- **REQ-080** — The system SHALL read `[tool.readerfriction]` from the
  nearest `pyproject.toml` walking upward from the scan target.
- **REQ-081** — IF a CLI flag and a config file disagree THEN the system
  SHALL use the CLI flag.
- **REQ-082** — The system SHALL expose configurable weights (one per
  metric), exclude patterns, and wrapper threshold. See `config.md`.

## Output contracts

- **REQ-090** — WHEN `scan` finishes THEN the JSON output SHALL validate
  against `spec/contracts/scan-result.schema.json`.
- **REQ-091** — WHEN `trace` finishes THEN the JSON output SHALL validate
  against `spec/contracts/trace-result.schema.json`.
- **REQ-092** — WHEN `explain` finishes THEN the JSON output SHALL validate
  against `spec/contracts/explain-result.schema.json`.
- **REQ-093** — WHEN `report` finishes THEN the JSON output SHALL validate
  against `spec/contracts/report-result.schema.json`.
- **REQ-094** — The schemas SHALL be generated from Pydantic models and a
  test SHALL assert parity between generated and committed schemas.

## Exit codes

- **REQ-100** — WHEN a command completes successfully THEN the system SHALL
  exit 0.
- **REQ-101** — IF `--fail-on <expr>` is set and the expression is true
  against the result THEN the system SHALL exit 1.
- **REQ-102** — IF the user passes invalid arguments THEN the system SHALL
  exit 2 and print a usage message to stderr.
- **REQ-103** — IF an unhandled internal error occurs THEN the system SHALL
  exit 3 and print a traceback to stderr.

## Non-goals (explicit)

- **REQ-900** — The system SHALL NOT attempt dynamic dispatch resolution
  (e.g., resolving calls through runtime type inference).
- **REQ-901** — The system SHALL NOT perform runtime tracing.
- **REQ-902** — The system SHALL NOT parse languages other than Python.
- **REQ-903** — The system SHALL NOT hard-code framework-specific knowledge
  beyond the entrypoint decorator list in REQ-040.
