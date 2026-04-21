"""REQ-060 trace_depth = hops on the chosen trace path."""

from __future__ import annotations

from readerfriction.models import FunctionRef, MetricResult


def compute(path: list[FunctionRef]) -> MetricResult:
    hops = max(len(path) - 1, 0)
    return MetricResult(name="trace_depth", value=float(hops), display=str(hops))


__all__ = ["compute"]
