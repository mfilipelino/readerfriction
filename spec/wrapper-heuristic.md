# Thin-Wrapper Heuristic

A function `f` is a **thin wrapper** when **both** of the following hold:

1. Every rule in the **disqualifier set**
   `{W-02, W-04, W-05, W-06, W-07}` matches. These rules encode "exactly
   one non-trivial call / no loops / no meaningful branching / no
   substantial transformation / no meaningful validation". If any fires
   False, the function contains substantive logic and cannot be a
   wrapper.
2. The total number of matched rules meets or exceeds the configured
   threshold. Default threshold: **6 of 8**.

W-02 was added to the disqualifier set to close an evasion path: a
function with a real business side-effect call *and* a pass-through
return (e.g. `db.save(x); return run(x)`) could otherwise fire 6/8
rules and sneak in. The wrapper pattern by definition is "call exactly
one non-trivial thing and pass through" — W-02 must hold.

Each rule returns True if the rule *fires in favour of "thin wrapper"*, False
otherwise. For example, rule W-01 fires when the body is short.

---

## Rules

### W-01 — Short body

`len(non-docstring statements in f.body) ≤ 3`.

Docstrings (a bare `Expr(Constant(str))` as the first statement) are not
counted. `pass` is not counted.

### W-02 — Exactly one non-trivial call

A *non-trivial call* is an `ast.Call` node whose **final** name (the
callee itself for `foo(x)`, the attribute for `obj.foo(x)`) is **not**
in either of these sets:

**Trivial callees** (constructors / casts / primitives):
`len`, `str`, `int`, `float`, `bool`, `list`, `tuple`, `dict`, `set`,
`bytes`, `frozenset`, `print`.

**Telemetry callees** (observational side-effects that do not carry
business logic): stdlib logging + loguru method names (`log`, `info`,
`debug`, `warning`, `warn`, `error`, `critical`, `exception`, `fatal`);
Prometheus / statsd counter ops (`inc`, `incr`, `increment`, `observe`);
OpenTelemetry span operations (`record_exception`, `add_event`,
`set_attribute`, `set_tag`); debug output (`pprint`).

Rule fires when `|non_trivial_calls(f)| == 1`. This rule is a
**disqualifier** (see top of this document) — a function with zero or
more than one non-trivial call cannot be a thin wrapper.

The telemetry exemption closes Attack C from
[`docs/limits-and-anti-gaming.md`](../docs/limits-and-anti-gaming.md):
without it, adding a single `logger.info(...)` line to a pass-through
function defeated W-02 and cheaply lowered the `rf` score with no real
improvement to readability.

### W-03 — Returns the call

The last statement of `f.body` is either:

- `Return(Call(...))` where the call is the one counted in W-02, or
- `Return(Await(Call(...)))`, or
- `Expr(Call(...))` **only if** `f` has no explicit return and returns `None`
  implicitly. This handles call-only wrappers such as
  `def persist(x): db.save(x)`. Note that since logger/metrics calls are
  now treated as *trivial* for W-02 (see above), a function whose only
  call is `logger.info(x)` will fail W-02 and therefore fail to
  classify as a wrapper — which is correct: inlining it would drop the
  named log call.

### W-04 — No loops

`f.body` contains no `For`, `While`, `AsyncFor`, `comprehension` with more
than a single generator, or generator `yield` in a loop.

### W-05 — No meaningful branching

`f.body` contains no `If` / `Match` whose branches would let the reader
observe different side effects. A **guard clause** (`If(..., body=[Raise(...)
], orelse=[])`) does **not** disqualify — guards are considered wrapper-like.

### W-06 — No substantial transformation

No `BinOp`, `BoolOp`, `Compare`, `UnaryOp`, `JoinedStr`, `ListComp`,
`DictComp`, `SetComp`, `GeneratorExp`, `Lambda`, `Subscript` in *argument
positions* passed to the tracked call. Passing the wrapper's parameters
straight through does not count as transformation.

### W-07 — No meaningful validation

No `Assert` nodes; no calls to names in
`{"validate", "assert_valid", "check", "ensure", "require"}` (exact match
or suffix) before the tracked call.

### W-08 — Arguments map 1:1

Let `params(f)` be the parameter names of `f`. Let `args_of_call` be the
positional + keyword argument names used in the tracked call.

Rule fires when `set(args_of_call) ⊆ set(params(f)) ∪ {"self", "cls"}` **and**
`|args_of_call| ≥ 1`. That is, the wrapper passes its own parameters through
without introducing new identifiers.

---

## Decorators

`@staticmethod`, `@classmethod`, `@property`, `@cached_property`,
`@functools.lru_cache`, `@functools.cache`, and `@functools.wraps` do **not**
disqualify a function.

Any other decorator disqualifies the function (it is likely meaningful).

## Async

`async def` functions follow the same rules with `Await` treated as a
transparent wrapper over `Call` (see W-03).

## Output

The classifier returns:

```python
class WrapperClassification(BaseModel):
    is_wrapper: bool
    matched_rules: list[str]   # e.g. ["W-01", "W-02", "W-03", "W-04", "W-05", "W-08"]
    score: int                 # len(matched_rules)
    threshold: int             # copied from config so output is self-explanatory
```
