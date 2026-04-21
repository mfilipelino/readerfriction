# ReaderFriction — `project`

**Score:** 44  —  **Severity:** error

_Scanned 5 file(s)._

## Summary

| Metric | Value |
| --- | --- |
| Trace depth | 4 |
| File jumps | 4 |
| Wrapper depth | 4 |
| Thin wrappers | 4 |
| Flow fragmentation | 1 |
| Context width | 1.00 |
| Pass-through ratio | 0.800 |

## Entrypoints

### `cli.main` (score 44)

- **Location:** `cli.py:4`
- **Path:** `cli.main` → `handlers.handle` → `services.run` → `repos.fetch` → `db.query`

| Metric | Value |
| --- | --- |
| Trace depth | 4 |
| File jumps | 4 |
| Wrapper depth | 4 |
| Thin wrappers | 4 |
| Flow fragmentation | 1 |
| Context width | 1.00 |
| Pass-through ratio | 0.800 |
