# Architecture

Pipeline (left-to-right, each stage pure and testable in isolation):

```
paths ─▶ parser.discover ─▶ parser.ast_parse ─▶ parser.entrypoints
                                                      │
                                                      ▼
                            graph.resolve ◀──┐   classify.wrappers
                                  │          │          │
                                  ▼          ▼          ▼
                           graph.callgraph ──────────────▶ metrics.* ─▶ score
                                                                │
                                                                ▼
                                                          reports.{json,text,md}
                                                                │
                                                                ▼
                                                              cli.py
```

## Module responsibilities

| Module                               | Input                           | Output                    |
|--------------------------------------|---------------------------------|---------------------------|
| `parser.discover`                    | roots, excludes                 | `list[Path]`              |
| `parser.ast_parse`                   | `Path`                          | `ModuleIR`                |
| `parser.entrypoints`                 | `ModuleIR`                      | `set[FunctionRef]`        |
| `graph.resolve`                      | all `ModuleIR`                  | symbol table              |
| `graph.callgraph`                    | IRs + symbol table              | `CallGraph`               |
| `classify.wrappers`                  | `FunctionIR`                    | `WrapperClassification`   |
| `metrics.*`                          | `CallGraph` + classifications   | `MetricResult`            |
| `metrics.score`                      | `list[MetricResult]`, weights   | `int`                     |
| `reports.{json,text,markdown}`       | `ScanResult` / `TraceResult`    | `str` or file             |
| `cli`                                | argv                            | exit code                 |

## Invariants

- **Pure core** — everything under `parser/`, `graph/`, `classify/`,
  `metrics/`, `reports/` is pure: no file I/O beyond what its input
  explicitly names; no ambient state; no mutable globals.
- **Dataclass-style data-in / data-out** — every boundary uses a Pydantic
  model from `models.py`. No stringly-typed dicts leaking between layers.
- **Determinism** — identical inputs produce byte-identical outputs.
