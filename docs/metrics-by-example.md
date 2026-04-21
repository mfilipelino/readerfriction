# Metrics, by example

Every metric in ReaderFriction is computed from a **static call graph**
`G = (V, E)` and a **trace path** `P*` — the longest simple path from an
entrypoint to the first non-wrapper function along that path.

Full formal definitions live in [`../spec/metrics.md`](../spec/metrics.md).
This page walks through each metric with a minimal code example.

> Notation: the call path is shown as `a → b → c` meaning function `a`
> calls `b`, which calls `c`. Bold nodes are the first meaningful (non-wrapper)
> function on the path — where `P*` ends.

---

## Shared example — "wrapper-chain"

We reuse this one example for most metrics. The full sources live under
[`../spec/examples/wrapper-chain/project/`](../spec/examples/wrapper-chain/project/).

```python
# cli.py
from handlers import handle
def main(arg): return handle(arg)

# handlers.py
from services import run
def handle(arg): return run(arg)

# services.py
from repos import fetch
def run(arg): return fetch(arg)

# repos.py
from db import query
def fetch(arg): return query(arg)

# db.py
def query(key):
    value = _TABLE.get(key)
    if value is None: raise KeyError(key)
    for prefix in ("mr. ", "ms. "):
        if key.startswith(prefix): key = key[len(prefix):]
    return f"{key}={value}"
```

Classifier output:

| function | is_wrapper | why |
|---|---|---|
| `cli.main`        | ✅ | one call, returns it, args pass through |
| `handlers.handle` | ✅ | same |
| `services.run`    | ✅ | same |
| `repos.fetch`     | ✅ | same |
| `db.query`        | ❌ | has a loop, branching, and f-string transformation |

Trace path `P*`: `cli.main → handlers.handle → services.run → repos.fetch → **db.query**`.

---

## 1. `trace_depth` — hops to meaningful logic

> **Formula:** `trace_depth = len(P*) - 1`

The number of call boundaries the reader must cross before reaching a
function that does real work.

```python
P*        = [main, handle, run, fetch, query]   # len 5
trace_depth = 5 - 1 = 4
```

**What it tells you:** "The reader has to trace 4 hops before anything
interesting happens." High values usually mean you have a chain of thin
wrappers hiding the logic.

---

## 2. `file_jumps` — distinct files on the path

> **Formula:** `file_jumps = |{file_of(p) : p ∈ P*}| - 1`

```python
files_on_path = {"cli.py", "handlers.py", "services.py", "repos.py", "db.py"}
file_jumps    = 5 - 1 = 4
```

**What it tells you:** the reader has to open four new files while
following the main flow. Pairs with `trace_depth` — a 4-hop path that
stays in one file is much cheaper to read than one that crosses four.

A one-file flow has `file_jumps = 0`:

```python
# app.py
def parse(raw): ...
def main(raw):
    numbers = parse(raw)
    return sum(numbers)

# P* stays in app.py → file_jumps = 0
```

---

## 3. `wrapper_depth` — longest run of consecutive wrappers

> **Formula:** `wrapper_depth = max run of W(p)=True along P*`

Count the longest stretch of thin wrappers back-to-back on the trace path.

```python
W(main)   = True
W(handle) = True
W(run)    = True
W(fetch)  = True
W(query)  = False

wrapper_depth = 4    # main..fetch is a 4-long run of True
```

Compare with a path that only has one wrapper in the middle:

```python
#          True    False    True   False
P* = [entry, helper, compute, log, emit]
#            ↑                ↑
#            single wrapper   single wrapper
wrapper_depth = 1
```

**What it tells you:** if the max run is ≥ 3, you are reading a
"pass-through tower" — the reader has to step past at least three
wrapper functions in a row without learning anything new.

---

## 4. `thin_wrapper_count` — total wrappers on path

> **Formula:** `thin_wrapper_count = |{p ∈ P* : W(p) = True}|`

Like `wrapper_depth`, but counts every wrapper, not just the longest run.

```python
P*               = [main, handle, run, fetch, query]
wrappers_on_path = [main, handle, run, fetch]
thin_wrapper_count = 4
```

A path with two separate wrappers (not consecutive) would score 2 here
even though `wrapper_depth = 1`.

---

## 5. `flow_fragmentation` — branching along the main path

> **Formula:**
> ```
> fan_out(v) = |{u : v → u ∈ E, u ≠ <external>}|
> flow_fragmentation = fan_out(p₀) + Σ max(0, fan_out(pᵢ) - 1)  for i ∈ [1, n-1]
> ```

The entrypoint contributes its whole fan-out; every *intermediate* node
contributes any branches *beyond the one that continues the trace path*.

**Low fragmentation** (wrapper-chain): each intermediate node calls
exactly one in-scope function, so fan-out - 1 = 0 at every intermediate
step. The entrypoint `main` has fan-out 1.

```python
fan_out(main)   = 1         # calls handle only
fan_out(handle) = 1         # calls run only
fan_out(run)    = 1
fan_out(fetch)  = 1
flow_fragmentation = 1 + 0 + 0 + 0 = 1
```

**High fragmentation** (fragmented-flow fixture): `main` calls six sibling
helpers.

```python
# main.py
def main(path):
    users    = load_users(path)      # 1
    accounts = load_accounts(path)   # 2
    validate_users(users)            # 3
    validate_accounts(accounts)      # 4
    records  = merge_records(users, accounts)  # 5
    emit_report(records)             # 6

fan_out(main) = 6
flow_fragmentation = 6 + 0 = 6
```

**What it tells you:** the reader can't just keep descending — they have
to pick which sibling to follow next. High fan-out at the entrypoint is a
strong signal that the flow is scattered.

---

## 6. `context_width` — state the reader must hold

> **Formula:** `context_width = mean(arg_count(p) + distinct_self_attrs(p))` for `p ∈ P*`

For every function on the path we sum its parameter count and the number
of distinct `self.<name>` attributes it reads/writes; then take the
arithmetic mean.

```python
# Each wrapper-chain function takes exactly 1 arg, no self.* attrs.
arg_counts = [1, 1, 1, 1, 1]
self_attrs = [0, 0, 0, 0, 0]
context_width = (1+1+1+1+1) / 5 = 1.00
```

Richer example:

```python
class Service:
    def run(self, user_id, options):
        # touches self.db, self.cache, self.log → 3 self.* attrs
        record = self.db.get(user_id)
        if self.cache.get(record.id): return record
        self.log.info(...)
        return record

# arg_count = 2 (user_id, options — self excluded)
# self_attrs = 3 (db, cache, log)
# contribution = 2 + 3 = 5
```

**What it tells you:** low context width means each hop adds little new
state for the reader to hold in working memory. High context width
(arrays of args, heavy `self.*` usage) means the reader is juggling a lot.

---

## 7. `pass_through_ratio` — population statistic

> **Formula:** `pass_through_ratio = |wrappers| / |in-scope functions|`
> (rounded to 3 decimal places, range `[0, 1]`)

Unlike the path metrics above, this is a *project-level* ratio: how much
of your codebase is wrapper scaffolding vs. substantive code.

```python
# wrapper-chain has 5 functions, 4 wrappers
pass_through_ratio = 4 / 5 = 0.800
```

```python
# clean-flow has 3 functions, 0 wrappers
pass_through_ratio = 0 / 3 = 0.000
```

**What it tells you:** this metric is *reported* but deliberately
**not part of the score** — it's a population statistic, not a path
statistic. It's useful as a health gauge: if half your functions are
wrappers (`0.5`), the codebase is probably a maze.

---

## 8. `reader_friction_score` — the aggregate

> **Formula** (default weights, configurable via `[tool.readerfriction.weights]`):
> ```
> score = 2 * trace_depth
>       + 3 * file_jumps
>       + 3 * wrapper_depth
>       + 2 * thin_wrapper_count
>       + 2 * context_width
>       + 2 * flow_fragmentation
> ```
>
> `pass_through_ratio` is intentionally **excluded** from the score.

Plugging in the wrapper-chain numbers:

```python
score = 2 * 4   # trace_depth
      + 3 * 4   # file_jumps
      + 3 * 4   # wrapper_depth
      + 2 * 4   # thin_wrapper_count
      + 2 * 1   # context_width  (rounded 1.00 → 1)
      + 2 * 1   # flow_fragmentation
      = 8 + 12 + 12 + 8 + 2 + 2
      = 44
```

And the clean-flow fixture, which has `trace_depth=1, file_jumps=0,
wrapper_depth=0, thin_wrapper_count=0, context_width=1, flow_fragmentation=2`:

```python
score = 2*1 + 3*0 + 3*0 + 2*0 + 2*1 + 2*2 = 8
```

A 5.5× gap between the two tells you exactly what you'd expect: the
wrapper chain is dramatically harder to navigate than the clean flow,
even though both projects are tiny.

---

## Running these locally

The three worked examples above live as real fixtures. You can
reproduce every number on this page with:

```bash
rf scan spec/examples/wrapper-chain/project    --format json
rf scan spec/examples/clean-flow/project       --format json
rf scan spec/examples/fragmented-flow/project  --format json
```

For a per-function breakdown showing which of the 8 wrapper-rules
matched, use `rf explain`:

```bash
rf explain spec/examples/wrapper-chain/project/handlers.py:handle
```
