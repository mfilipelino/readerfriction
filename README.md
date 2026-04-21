# ReaderFriction

> Most code-quality tools tell you whether a function is complex.
> ReaderFriction tells you whether the main path is painful to follow.

**ReaderFriction** is a Python CLI that analyses **navigational complexity**:

- How many layers a reader must trace
- How much indirection exists
- How fragmented the main path is
- Where wrappers and pass-through helpers add friction

It is complementary to `complexipy`:

- `complexipy` = *local* mental complexity inside a function.
- `readerfriction` = *navigation burden* across the main path.

## What it measures

- **Trace Depth** — hops before meaningful logic starts
- **File Jumps** — files the reader must cross
- **Wrapper Depth** — consecutive thin wrappers before real logic
- **Thin Wrapper Count** — pass-through helpers on the path
- **Flow Fragmentation** — how scattered the main path is
- **Context Width** — state the reader must hold in mind
- **Pass-Through Ratio** — wrappers / functions in scope

Formal definitions: [`spec/metrics.md`](spec/metrics.md).

## A tiny example

Given `cli → handler → service → repo → db`, where the middle three are
thin wrappers:

```
$ readerfriction scan spec/examples/wrapper-chain/project
score            29
trace_depth       4   hops
file_jumps        4   files
wrapper_depth     3   consecutive wrappers on path
thin_wrappers     3
flow_fragmentation 1
```

Clean flows score close to zero; wrapper-heavy flows score high.

## Install

```bash
uv pip install -e .
```

## Quickstart

```bash
readerfriction scan src/
readerfriction trace src/cli.py:main
readerfriction explain src/service.py:run_job
readerfriction report src/ --format markdown --out reader-friction.md
readerfriction diff src/ --base ../old-src/
```

## Configure

```toml
# pyproject.toml
[tool.readerfriction]
wrapper_threshold = 6

[tool.readerfriction.weights]
trace_depth = 2
file_jumps = 3
wrapper_depth = 3
thin_wrapper_count = 2
context_width = 2
flow_fragmentation = 2
```

See [`spec/config.md`](spec/config.md) for every key.

## How it works

Static analysis only. ReaderFriction parses your code with `ast`, builds a
call graph with `networkx`, classifies thin wrappers using an 8-rule
heuristic ([`spec/wrapper-heuristic.md`](spec/wrapper-heuristic.md)), and
computes the seven metrics above.

ReaderFriction does **not** run your code and does **not** chase dynamic
dispatch. v0.1 non-goals are listed in
[`spec/requirements.md`](spec/requirements.md) (REQ-900..REQ-903).

## Contributing

See [`CONTRIBUTING.md`](CONTRIBUTING.md). Spec lives under [`spec/`](spec/)
and is normative — changes start there.

## License

MIT — see [`LICENSE`](LICENSE).
