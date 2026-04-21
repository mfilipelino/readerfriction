"""REQ-063 thin_wrapper_count on the trace path."""

from __future__ import annotations

from readerfriction.models import FunctionRef, MetricResult


def compute(path: list[FunctionRef], wrappers: set[FunctionRef]) -> MetricResult:
    count = sum(1 for node in path if node in wrappers)
    return MetricResult(
        name="thin_wrapper_count",
        value=float(count),
        display=str(count),
    )


__all__ = ["compute"]
