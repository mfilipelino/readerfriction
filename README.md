# ReaderFriction — `rf`

**rf** = **r**eader **f**riction. The CLI command `rf` is short for
`ReaderFriction`; the Python package and PyPI name remain `readerfriction`.

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
Worked examples: [`docs/metrics-by-example.md`](docs/metrics-by-example.md).

### Metric snippets at a glance

Minimum code, maximum clarity — see
[`docs/metrics-by-example.md`](docs/metrics-by-example.md) for the full
walk-through.

**trace_depth** — hops before meaningful logic.

```
main  →  handle  →  run  →  fetch  →  query   ← meaningful leaf
        (wrap)   (wrap) (wrap)     (non-wrapper)

len(path) - 1 = 5 - 1 = 4
```

**file_jumps** — distinct source files on the path minus 1.

```
cli.py → handlers.py → services.py → repos.py → db.py
|{files}| - 1 = 5 - 1 = 4
```

**wrapper_depth** — longest consecutive run of thin wrappers on the path.

```
W(main)=T  W(handle)=T  W(run)=T  W(fetch)=T  W(query)=F
         run of 4 Trues → wrapper_depth = 4
```

**thin_wrapper_count** — total wrappers on the path: 4 (same example).

**flow_fragmentation** — branching pressure along the main path.

```python
# main calls six sibling helpers, no chain:
def main(path):
    users    = load_users(path)
    accounts = load_accounts(path)
    validate_users(users)
    validate_accounts(accounts)
    records  = merge_records(users, accounts)
    emit_report(records)

fan_out(main) = 6   →  flow_fragmentation = 6
```

**context_width** — mean of `arg_count + distinct self.* attrs` along the
path. Tiny wrappers with one arg each give `1.00`; a method touching
three `self.*` attrs with two args contributes `5` for that hop.

**pass_through_ratio** — project-level wrapper density:

```
4 wrappers / 5 functions = 0.800   # reported, not scored
```

**score** — weighted sum (weights configurable):

```
score = 2·4 + 3·4 + 3·4 + 2·4 + 2·1 + 2·1 = 44   # wrapper-chain
score = 2·1 + 3·0 + 3·0 + 2·0 + 2·1 + 2·2 =  8   # clean-flow
```

A 5.5× gap between fixtures that are just a few files each — which is
exactly the signal `rf` is built to surface.

## A tiny example

Given `cli → handler → service → repo → db`, where the middle three are
thin wrappers:

```
$ rf scan spec/examples/wrapper-chain/project
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
# from PyPI (once released)
pip install readerfriction
uv pip install readerfriction

# as a global CLI tool
uv tool install readerfriction

# from GitHub (latest main)
pip install git+https://github.com/mfilipelino/readerfriction.git

# editable, from a local clone
uv pip install -e .
```

## Quickstart

```bash
rf scan src/
rf trace src/cli.py:main
rf explain src/service.py:run_job
rf report src/ --format markdown --out reader-friction.md
rf diff src/ --base ../old-src/
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

## Background

ReaderFriction's metrics build on decades of empirical work on code
readability, comprehension, and complexity. These are the sources that
shaped the design; each bullet notes which metric it supports.

- **Buse, R. P. L., & Weimer, W. R. (2010).** *Learning a Metric for Code
  Readability.* IEEE Transactions on Software Engineering 36(4): 546–558.
  [doi:10.1109/TSE.2009.70](https://doi.org/10.1109/TSE.2009.70) — empirical
  evidence that readability is measurable and correlates with defects;
  supports **context width** and the overall friction-score approach.
- **Scalabrino, S., Bavota, G., Vendome, C., Linares-Vásquez, M.,
  Poshyvanyk, D., & Oliveto, R. (2017 / 2019).** *Automatically Assessing
  Code Understandability: How Far Are We?* ASE 2017 (extended in IEEE TSE
  2019).
  [ASE preprint PDF](https://www.cs.wm.edu/~denys/pubs/ASE'17-Readability.pdf) —
  shows no single metric captures understandability; motivates a
  **composite** score instead of a single number.
- **Campbell, G. A. (2018).** *Cognitive Complexity: A new way of measuring
  understandability.* SonarSource white paper (also in Proc. TechDebt 2018,
  [doi:10.1145/3194164.3194186](https://doi.org/10.1145/3194164.3194186)).
  [PDF](https://www.sonarsource.com/docs/CognitiveComplexity.pdf) — direct
  inspiration for **flow fragmentation** and for taking nesting / branching
  into account when they affect reading, not just control flow.
- **Siegmund, J., Kästner, C., Apel, S., Parnin, C., Bethmann, A., Leich,
  T., Saake, G., & Brechmann, A. (2014).** *Understanding Understanding
  Source Code with Functional Magnetic Resonance Imaging.* ICSE 2014:
  378–389. [doi:10.1145/2568225.2568252](https://doi.org/10.1145/2568225.2568252) —
  fMRI evidence that code reading activates working-memory regions;
  grounds **context width** and **trace depth** as cognitive-load proxies.
- **LaToza, T. D., Venolia, G., & DeLine, R. (2006).** *Maintaining Mental
  Models: A Study of Developer Work Habits.* ICSE 2006: 492–501.
  [doi:10.1145/1134285.1134355](https://doi.org/10.1145/1134285.1134355) —
  developers report real pain tracing across modules; justifies **file
  jumps** and **wrapper depth** as first-class signals.
- **McCabe, T. J. (1976).** *A Complexity Measure.* IEEE Transactions on
  Software Engineering SE-2(4): 308–320.
  [doi:10.1109/TSE.1976.233837](https://doi.org/10.1109/TSE.1976.233837) —
  the original local-complexity metric ReaderFriction *complements* rather
  than replaces; cyclomatic complexity stops at function boundaries, `rf`
  picks up where it leaves off.
- **Fowler, M. (2018).** *Refactoring: Improving the Design of Existing
  Code* (2nd ed.), Addison-Wesley. See the *Inline Function* refactoring.
  [Book site](https://refactoring.com/) — practitioner grounding for the
  **thin-wrapper** heuristic: a function that does nothing but forward is
  a candidate to inline.

## Contributing

See [`CONTRIBUTING.md`](CONTRIBUTING.md). Spec lives under [`spec/`](spec/)
and is normative — changes start there.

## License

MIT — see [`LICENSE`](LICENSE).
