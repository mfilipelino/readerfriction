## Project name

**ReaderFriction**
**Tagline:** *Measure how hard code is to follow.*

## Product definition

ReaderFriction is an open-source Python CLI that analyzes **navigational complexity** in Python codebases:

* how many layers a reader must trace
* how much indirection exists
* how fragmented the main path is
* where wrappers and pass-through helpers add friction

It does **not** replace `complexipy`.

* `complexipy` = local mental complexity
* `readerfriction` = navigation burden across the main path

## Core metrics

ReaderFriction should own these:

* **Trace Depth** — how many hops before meaningful logic starts
* **File Jumps** — how many files the reader must cross
* **Wrapper Depth** — consecutive thin wrappers before real logic
* **Thin Wrapper Count** — pass-through helpers on the path
* **Flow Fragmentation** — how scattered the main path is
* **Context Width** — how much state the reader must hold in mind
* **Pass-Through Ratio** — thin wrappers / total functions in scope

## Core score

A good starting heuristic:

```text
reader_friction_score =
    2 * trace_depth +
    3 * file_jumps +
    3 * wrapper_depth +
    2 * thin_wrapper_count +
    2 * context_width +
    2 * flow_fragmentation
```

This should be configurable in `pyproject.toml`.

## CLI surface

```bash
readerfriction scan src/
readerfriction trace src/cli.py:main
readerfriction explain src/service.py:run_job
readerfriction report src/ --format markdown --out reader-friction.md
readerfriction diff . --base main --head HEAD
```

## Recommended stack

Use `uv` and keep the package modern and simple.

### Bootstrap

```bash
uv init readerfriction
uv add typer rich networkx pydantic libcst
uv add --dev pytest ruff pyright
```

### Tooling

* package manager: `uv`
* build backend: `hatchling`
* CLI: `typer`
* terminal output: `rich`
* graph model: `networkx`
* schemas: `pydantic`
* parsing: `ast` + optional `libcst`
* lint: `ruff`
* type check: `pyright`
* tests: `pytest`

## Suggested structure

```text
readerfriction/
├─ pyproject.toml
├─ README.md
├─ LICENSE
├─ CHANGELOG.md
├─ CONTRIBUTING.md
├─ docs/
├─ src/
│  └─ readerfriction/
│     ├─ cli.py
│     ├─ config.py
│     ├─ models.py
│     ├─ parser/
│     ├─ graph/
│     ├─ classify/
│     ├─ metrics/
│     ├─ integrations/
│     │  └─ complexipy.py
│     ├─ reports/
│     └─ utils/
└─ tests/
```

## Thin wrapper heuristic

A function is likely a thin wrapper if most are true:

* body has <= 3 simple statements
* exactly one nontrivial call
* returns that call directly
* no loops
* no meaningful branching
* no substantial transformation
* no meaningful validation
* no meaningful semantic abstraction

## README positioning

The README should open with this contrast:

> Most code-quality tools tell you whether a function is complex.
> ReaderFriction tells you whether the main path is painful to follow.

Then immediately show:

* why it exists
* what it measures
* a tiny wrapper-chain example
* quickstart
* sample output

## GitHub appeal

To make it feel like a real open-source project from day one, include:

* `LICENSE` → MIT
* `CONTRIBUTING.md`
* `CODE_OF_CONDUCT.md`
* `SECURITY.md`
* issue templates
* PR template
* `CHANGELOG.md`

## Recommended scope for v0.1

Ship only:

* Python static analysis
* entrypoint detection
* trace depth
* file jumps
* thin wrapper detection
* wrapper depth
* text and markdown report
* JSON output
* configurable thresholds

Do **not** try to solve:

* perfect dynamic dispatch
* runtime tracing
* multi-language support
* framework-specific magic

That would be scope creep.

## Acceptance criteria for v0.1

* installs via `uv`
* exposes working CLI
* scans Python project paths
* detects entrypoints
* computes trace depth, file jumps, wrapper depth, thin wrappers
* emits readable reports
* flags obvious wrapper-heavy flows in fixtures
* avoids flagging every short helper as bad

I can now turn this into a proper `README.md`, `SPEC.md`, and `pyproject.toml` starter set in the canvas.
