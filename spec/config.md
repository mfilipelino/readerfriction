# Configuration

Read from `[tool.readerfriction]` in the nearest `pyproject.toml`, walking
upward from the scan target. CLI flags override file values.

## Keys

```toml
[tool.readerfriction]
# Exclude globs (additive with defaults)
exclude = ["tests/fixtures/*", "scripts/*"]

# Wrapper heuristic
wrapper_threshold = 6      # matches required out of 8 rules

# Metric weights (used by reader_friction_score)
[tool.readerfriction.weights]
trace_depth         = 2
file_jumps          = 3
wrapper_depth       = 3
thin_wrapper_count  = 2
context_width       = 2
flow_fragmentation  = 2
# pass_through_ratio is not scored

# Severity thresholds (affect text report colours and --fail-on defaults)
[tool.readerfriction.thresholds]
warn   = 15
error  = 30
```

## Defaults

If a key is absent, the default from `Config` in `src/readerfriction/config.py`
applies. Defaults are the values shown above.

## Precedence

`CLI flag  >  pyproject.toml  >  built-in default`

Exactly this order. Tests enforce it.
