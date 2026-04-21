"""REQ-066 pass_through_ratio = wrappers / functions in scope."""

from __future__ import annotations

from readerfriction.models import FunctionRef, MetricResult


def compute(
    in_scope: set[FunctionRef],
    wrappers: set[FunctionRef],
) -> MetricResult:
    total = len(in_scope)
    if total == 0:
        return MetricResult(name="pass_through_ratio", value=0.0, display="0.000")
    ratio = round(len(wrappers & in_scope) / total, 3)
    return MetricResult(
        name="pass_through_ratio",
        value=ratio,
        display=f"{ratio:.3f}",
    )


__all__ = ["compute"]
