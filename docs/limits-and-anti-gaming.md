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

### Attack C — "defeat the wrapper classifier"

Add one innocuous line to `handle`, `run`, and `fetch`:

```python
def handle(arg):
    counter.inc("handle")  # ← defeats W-02 (now 2 non-trivial calls)
    return run(arg)
```

Result:

| metric | before | after |
|---|---|---|
| wrapper_depth | 4 | 0 |
| thin_wrapper_count | 4 | 0 |
| trace_depth | 4 | drops to the first non-wrapper (now `handle`) = 1 |
| **score** | **44** | ≈ **18** |

No tool catches this. The code is structurally identical; the
classifier just lost 3 of 4 wrappers.

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
