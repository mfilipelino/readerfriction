# Metrics (concise)

- Formal definitions: [`spec/metrics.md`](../spec/metrics.md).
- Worked examples for every metric: [`metrics-by-example.md`](metrics-by-example.md).

This page is a quick reference.

- **trace_depth** — hops on the chosen path from an entrypoint to the first
  meaningful (non-wrapper) function.
- **file_jumps** — distinct files crossed on that path, minus 1.
- **long_files** — count of files on the path whose total line count
  exceeds `max_file_lines` (default 500). Catches "haystack" files
  that `file_jumps` alone would score zero.
- **wrapper_depth** — longest run of consecutive thin wrappers on the path.
- **thin_wrapper_count** — number of wrappers on the path.
- **flow_fragmentation** — branching at the entrypoint + extra branches along
  the path. High fragmentation means the reader must keep multiple sibling
  helpers in mind.
- **context_width** — mean of `arg_count + distinct self.* attrs` along the
  path. Proxy for state the reader has to hold.
- **pass_through_ratio** — wrappers / functions in scope. Reported, not
  scored.

The aggregate score:

```
score = 2 * trace_depth
      + 3 * file_jumps
      + 3 * long_files
      + 3 * wrapper_depth
      + 2 * thin_wrapper_count
      + 2 * context_width
      + 2 * flow_fragmentation
```

Weights override in `pyproject.toml` — see [`spec/config.md`](../spec/config.md).
