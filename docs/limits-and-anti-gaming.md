# Limits & anti-gaming — read this before trusting the score

ReaderFriction measures **structural indirection in a static call graph**.
Structural indirection is correlated with reader difficulty, but it is
not the same thing. This page is the fair-warning doc.

## Three things `rf` does not actually measure

### 1. Reader difficulty

Readers don't struggle with *hops*, they struggle with hops where the
names tell them nothing. A 5-deep chain of `extract_payload →
authenticate → persist → retry → commit` is trivial to scan; a 2-hop
chain of `handle → process` is opaque. `rf` gives both paths structurally
the same score if the depth is the same. It can't read identifiers.

It also doesn't see:

- **IDE support.** Jump-to-definition compresses trace depth dramatically.
- **Reader familiarity.** Framework idioms look like noise to outsiders
  and like background to experts.
- **Dynamic dispatch.** Plugin registries, decorator-based routing,
  callback tables — invisible to the call graph, explicit in `rf`'s
  non-goals (REQ-900/901 in the spec).

So when someone says "`rf` measures reader friction," that's aspiration.
What it literally does is count structural features of the static call
graph. Those are worth counting. They are not a complete proxy.

### 2. Signal independence

The score is a weighted sum of six metrics, but they are not six
independent measurements. Three of them — `wrapper_depth`,
`thin_wrapper_count`, and (indirectly) `trace_depth` — are downstream of
a single 8-rule classifier. If the classifier flips on one function,
three numbers move together. The sum looks like a rich signal; the
underlying mechanism is essentially "classifier count × weights".

Practical consequence: **the classifier is a single point of failure
and a single point of attack**. An adversarial agent that wants a lower
score just has to disturb the classifier. Ways to do that:

- Add one more non-trivial call inside a wrapper → fails W-02.
- Add a counter increment or log line → body > 3 statements → fails W-01.
- Add a non-approved decorator → disqualifies the function entirely.
- Rename the function to a non-generic verb — doesn't affect the
  classifier but changes the human signal, so even `rf explain` won't
  see the difference.

None of these make the code meaningfully easier to read.

### 3. Validated weights

The default weights `2, 3, 3, 2, 2, 2` came straight from the product
brief. They are not fit to anything. Buse & Weimer (TSE 2010) trained
their readability metric against 120 human annotators and got 80%
agreement. Scalabrino et al. (ASE 2017 / TSE 2019) explicitly showed
that **none** of the 121 pre-existing metrics they tested predicted
code understandability reliably. `rf`'s formula has not been through
that crucible. The research I cite in the README supports the *concept*
of measuring navigation burden; it does not support this specific
formula.

Until those weights are fit to a human-labelled corpus, treat the
score as ordinal (higher is worse) rather than cardinal (44 vs. 32 is
a precise difference).

## Gaming scenarios, with the actual arithmetic

Baseline: `spec/examples/wrapper-chain/project/` — score **44**.

### Attack A — "put everything in one file"

Paste the 5 wrapper-chain files into one `app.py`. Functions and call
chain unchanged. Result:

| metric | before | after | Δ points |
|---|---|---|---|
| trace_depth | 4 | 4 | 0 |
| file_jumps | 4 | 0 | −12 |
| wrapper_depth | 4 | 4 | 0 |
| thin_wrapper_count | 4 | 4 | 0 |
| context_width | 1.0 | 1.0 | 0 |
| flow_fragmentation | 1 | 1 | 0 |
| **score** | **44** | **32** | **−12 (−27%)** |

**Not** caught by `complexipy`, Cognitive Complexity, or any per-function
complexity tool — the functions are unchanged. You need a *separate*
file-size or functions-per-file check to catch this.

### Attack B — "collapse the chain into one function"

Inline main → handle → run → fetch → query into a single `main(arg)`
function. Result:

| metric | before | after |
|---|---|---|
| trace_depth | 4 | 0 |
| file_jumps | 4 | 0 |
| wrapper_depth | 4 | 0 |
| thin_wrapper_count | 4 | 0 |
| context_width | 1.0 | 1.0 |
| flow_fragmentation | 1 | 0 |
| **score** | **44** | **2** |

This one is *partially* caught by per-function complexity tools, but
only if the merged function exceeds their thresholds. If the merged
function is short (wrapper-chain is short enough), even `complexipy`
won't flag it.

### Attack C — "defeat the wrapper classifier" (partially mitigated)

Original attack: add one innocuous line to each wrapper on the path.

```python
def handle(arg):
    logger.info("handling %s", arg)   # ← used to defeat W-02
    return run(arg)
```

**Before the v0.1.1 hardening,** this dropped score from 44 to ~18 on
the wrapper-chain fixture. Classifier lost 3 of 4 wrappers because
`logger.info` counted as a second "non-trivial call."

**After the v0.1.1 hardening:**

1. A conservative **telemetry-callee list** was added to the W-02 rule
   (logger method names, Prometheus/statsd counters, OpenTelemetry
   span operations, `pprint`). Calls to these are treated as trivial
   for W-02 purposes.
2. W-02 was promoted to a **disqualifier** alongside W-04/05/06/07, so
   a function with a *real* business side-effect call (e.g.
   `db.save(x); return run(x)`) correctly fails to classify as a
   wrapper — it was previously squeaking in at exactly 6/8 rules.

Empirical verification: applying the `logger.info` Attack C to the
fixture now keeps the score at **44** (unchanged). Verified with
`rf scan /tmp/rf-attack-c/project`.

**Residual gap.** A static name list is still an arms race. An agent
that writes `record_operation(x)` or invents a custom telemetry name
not on the list will still evade W-02. The principled fix is **option
B** from the original design discussion: move from a binary
`is_wrapper: bool` to a continuous `wrapper_score: float ∈ [0,1]` so
defeating one rule moves the score gradually, not off a cliff. That
change is in the roadmap at the end of this document but is deferred
out of v0.1 to keep the schema stable.

### Attack C' — "rename a wrapper to look meaningful"

Still works. No static tool can tell whether `extract_payload` *actually*
extracts a payload or just does `return inner.do(x)`. Review catches
this; `rf` cannot. This is a fundamental semantic limit and is the
reason the `rf agent` prompt lists "do not rename superficially" as a
forbidden change.

## Recommended tooling pairing (the practical fix for A and B)

`rf` alone does not catch Attack A (5 files → 1 big file) or Attack B
(5 functions → 1 giant function). `complexipy` catches Attack B when
the merged function is big enough; it does **not** catch Attack A.

The clean fix is a short section in your project's `pyproject.toml`
using tools you almost certainly already have:

```toml
# pyproject.toml — closes Attack A + Attack B with ruff alone

[tool.ruff.lint]
select = [
    # ... your existing selections ...
    "C901",     # McCabe cyclomatic complexity (Attack B: giant function)
    "PLR0912",  # too many branches           (Attack B)
    "PLR0913",  # too many arguments          (Attack B)
    "PLR0915",  # too many statements         (Attack B)
]

[tool.ruff.lint.mccabe]
max-complexity = 10

[tool.ruff.lint.pylint]
max-statements = 50    # fires if an "inlined chain" balloons a function
max-branches   = 12
max-args       = 5
```

Plus a **file-size ceiling** that `ruff` doesn't ship natively. One
line of shell in CI closes Attack A:

```bash
find src -name '*.py' -exec wc -l {} + \
  | awk '$1 > 500 { print; bad=1 } END { exit bad }'
```

Or as a pre-commit hook:

```yaml
# .pre-commit-config.yaml
- repo: local
  hooks:
    - id: no-haystack-files
      name: no Python file over 500 lines
      entry: bash -c 'find src tests -name "*.py" | xargs -I{} awk "END { if (NR > 500) { print FILENAME; exit 1 } }" {}'
      language: system
      pass_filenames: false
```

The full anti-gaming pipeline:

```bash
# 1. Navigation burden across the main path
rf scan src/

# 2. Local complexity inside each function
uv tool run complexipy src/       # or: ruff check --select=C901,PLR0915

# 3. File-size gate (catches Attack A)
find src -name '*.py' -exec wc -l {} + | awk '$1 > 500 { exit 1 }'

# 4. Lint + types clean
ruff check src/
pyright src/

# 5. All tests pass
pytest
```

Any one of these alone is gameable. All five together are very hard to
game without actually improving the code — which is exactly the idea.
Each tool is responsible for one axis; `rf`'s axis is navigation
indirection.

## What `rf` genuinely flags well

Despite the critique above, `rf` is not useless. It reliably surfaces
three real anti-patterns that pure local-complexity tools miss:

1. **Literal pass-through chains** — the wrapper-chain fixture. When a
   call graph has a deep chain of actual pass-through functions, `rf`
   catches it and local metrics don't.
2. **Entrypoint fan-out ("God main")** — `flow_fragmentation` rises
   when an entrypoint dispatches to many siblings. This is a genuine
   readability hazard and no per-function metric catches it.
3. **Scaffolding-heavy codebases** — `pass_through_ratio` reports a
   codebase-wide wrapper ratio. If half your functions are wrappers
   (`0.5+`) you have a problem. This one is hard to game by rearranging.

Use `rf` to notice these. That's its job.

## Guidance: diagnostic, not reward

**Safe uses of `rf`:**

- "Is the score trending up month over month?" — a legitimate signal.
- `rf explain <file>:<func>` — tells you *why* a specific function
  flagged, which is what you actually need to decide what to do.
- Reviewing the longest path in a PR.
- Onboarding: new engineer opens a codebase, runs `rf scan`, reads the
  top entrypoints' reports — gets a navigation map before reading code.

**Unsafe uses of `rf`:**

- **CI gate on the absolute score.** `rf < 15 or fail` is an open
  invitation for Attack A — rearrangement without improvement.
  If you do use `--fail-on`, gate on *deltas* ("score didn't get
  worse"), not thresholds.
- **Reward signal for an AI agent.** All three attacks above are
  cheap for an agent and none of them improve the code. If you point
  a code-generating agent at `rf` as a loss, it will learn Attack C
  before it learns to inline a real wrapper.
- **Single-number quality assessment.** It isn't one. Look at the
  per-entrypoint breakdown and the wrapper classifications, not just
  `score`.

## What would make `rf` actually defensible

Future work, if this matters enough to chase:

- **Continuous wrapper score.** Replace `is_wrapper: bool` with
  `wrapper_score: float ∈ [0, 1]` derived from how many of the 8 rules
  fire. Path metrics would sum or average the soft score instead of
  counting boolean flags. This removes the cliff at the threshold
  boundary — adversarial evasions (adding one disqualifying statement,
  using an unlisted telemetry name) would move the score gradually
  instead of cleanly off-by-one. This is the principled fix for
  Attack C that the current telemetry-list patch only partially
  addresses.
- **Validation corpus.** Score the tool against code rated by
  humans for navigation difficulty. Fit the weights; don't guess them.
- **Name-quality features.** A path through five well-named hops is
  not a path through five opaque ones. Static name features (length,
  whether it's a verb, whether it matches the calling context) would
  narrow the gap between structure and difficulty.
- **Decouple the classifier.** Treat wrapper-detection,
  fragmentation, and context separately so the score has independent
  axes, not three correlated downstream metrics.
- **Dispatch-aware call graph.** Optional plugin that understands
  specific frameworks (Django URLs, typer registries, Flask routes)
  and closes the REQ-900 gap for those cases.

Without those, `rf` is a v0.1 diagnostic tool with a real and
defensible scope: it finds call-graph indirection that local-complexity
tools can't see, and it's honest about the rest.
