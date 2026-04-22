# Metric Definitions

Let `G = (V, E)` be the call graph, where:

- `V` = every `FunctionRef` in scope ∪ `{<external>}`
- `E` = directed edges `u → v` when `u` statically calls `v`
- `entry(G) ⊂ V` = detected entrypoints
- `W(v) ∈ {True, False}` = output of the thin-wrapper classifier on `v`

A **trace path** `P = (p₀, p₁, …, pₙ)` is a simple path starting at an
entrypoint (`p₀ ∈ entry(G)`) and ending at a *meaningful* function
(`W(pₙ) = False`), chosen to maximise `n`.

Call the chosen path `P*(G)`. Ties broken by lexicographic order on
`(qualname_of(p₀), qualname_of(pₙ), length)`.

---

## §1 trace_depth

```
trace_depth = len(P*) - 1        # number of hops, not nodes
```

Edge cases:

- IF no entrypoint reaches any meaningful function THEN `trace_depth = 0`.
- The sentinel `<external>` is never included in `P*`.

## §2 file_jumps

```
file_jumps = |{file_of(p) : p ∈ P*}| - 1
```

i.e., distinct source files crossed along `P*`, minus 1 (a path that stays in
one file has zero jumps).

## §3 wrapper_depth

```
wrapper_depth = max run of consecutive nodes p in P* with W(p) = True
```

If no wrappers on the path, `wrapper_depth = 0`.

## §4 thin_wrapper_count

```
thin_wrapper_count = |{p ∈ P* : W(p) = True}|
```

## §5 flow_fragmentation

Fragmentation proxies how scattered the logic is *from the entrypoint*:

```
fan_out(v) = |{u : v → u ∈ E, u ≠ <external>}|
flow_fragmentation = fan_out(p₀) + Σ_{i ∈ [1, n-1]} max(0, fan_out(pᵢ) - 1)
```

Rationale: each extra outgoing branch along the main path forces the reader
to decide which child continues the story. Fan-out at the entrypoint counts
fully because the reader must choose a path to begin with.

## §6 context_width

```
context_width = Σ_{p ∈ P*} (arg_count(p) + distinct_self_attrs(p))
              / len(P*)                              # arithmetic mean
```

Where `distinct_self_attrs(p)` is the count of distinct `self.<name>`
attributes read or written inside `p` (methods only; 0 for free functions).

## §7a long_files

```
long_files = |{f ∈ files(P*) : line_count(f) > max_file_lines}|
```

where `line_count(f)` is the total number of lines in the source file
`f` (including blanks and comments — kept deterministic), and
`files(P*)` is the set of distinct files crossed by the trace path.

Default `max_file_lines = 500`. Configurable via
`[tool.readerfriction].max_file_lines`.

Edge cases:

- IF `P*` is empty THEN `long_files = 0`.
- A file that failed to parse is counted as having 0 lines (its
  functions will not appear on any path, so it will not normally
  contribute to this metric).

Rationale: a file that does not comfortably fit on one screen is a
reader-friction signal that `file_jumps` alone cannot detect. A single
2000-line haystack file containing 10 functions scores zero on
`file_jumps` (it is one file) but takes substantial effort to navigate.
`long_files` makes this cost visible in the score. Specifically, this
metric closes **Attack A** from `docs/limits-and-anti-gaming.md`
(collapsing many files into one) at the `rf`-metric level rather than
only via external tooling.

## §7 pass_through_ratio

```
pass_through_ratio = |{v ∈ V : W(v) = True}| / |V_scope|
V_scope            = V \ {<external>}
```

`pass_through_ratio ∈ [0, 1]` and is rounded to 3 decimal places in output.

## §8 reader_friction_score

Default weights (override via `[tool.readerfriction]`):

```
score = 2 * trace_depth
      + 3 * file_jumps
      + 3 * long_files
      + 3 * wrapper_depth
      + 2 * thin_wrapper_count
      + 2 * context_width
      + 2 * flow_fragmentation
```

`pass_through_ratio` is **reported** but not part of the score (it is a
population statistic, not a path statistic). Its value is used for severity
colouring in text reports.

The score is a non-negative integer after rounding (`context_width` and
`flow_fragmentation` are rounded to the nearest integer before multiplying).
