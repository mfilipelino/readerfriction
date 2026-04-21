# Thin-wrapper heuristic (concise)

Normative text: [`spec/wrapper-heuristic.md`](../spec/wrapper-heuristic.md).

A function is a **thin wrapper** when all four *disqualifier* rules match
(no loops, no meaningful branching, no substantial transformation, no
meaningful validation) and the total count of matched rules meets the
configured threshold (default 6 of 8).

## The eight rules

| ID   | What it looks for |
|------|-------------------|
| W-01 | Short body (≤ 3 statements) |
| W-02 | Exactly one non-trivial call |
| W-03 | Returns (or `await`s) that call |
| W-04 | No loops *(disqualifier)* |
| W-05 | No meaningful branching *(disqualifier)* |
| W-06 | No arithmetic / f-string / comprehension / lambda transformation *(disqualifier)* |
| W-07 | No `assert` and no calls to validation-like names *(disqualifier)* |
| W-08 | Arguments pass through with no re-composition |
