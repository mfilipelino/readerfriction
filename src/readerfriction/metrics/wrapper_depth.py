"""REQ-062 wrapper_depth = max consecutive wrappers on the trace path."""

from __future__ import annotations

from readerfriction.models import FunctionRef, MetricResult


def compute(path: list[FunctionRef], wrappers: set[FunctionRef]) -> MetricResult:
    current = 0
    best = 0
    for node in path:
        if node in wrappers:
            current += 1
            best = max(best, current)
        else:
            current = 0
    return MetricResult(name="wrapper_depth", value=float(best), display=str(best))


__all__ = ["compute"]
