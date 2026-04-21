"""REQ-064 flow_fragmentation metric."""

from __future__ import annotations

from readerfriction.graph.callgraph import EXTERNAL, CallGraph
from readerfriction.models import FunctionRef, MetricResult


def compute(cg: CallGraph, path: list[FunctionRef]) -> MetricResult:
    if not path:
        return MetricResult(name="flow_fragmentation", value=0.0, display="0")

    head_fan = _fan_out(cg, path[0])
    middle = 0
    for node in path[1:-1]:
        middle += max(0, _fan_out(cg, node) - 1)

    total = head_fan + middle
    return MetricResult(
        name="flow_fragmentation",
        value=float(total),
        display=str(total),
        detail={
            "head_fan_out": str(head_fan),
            "middle_extra_branches": str(middle),
        },
    )


def _fan_out(cg: CallGraph, node: FunctionRef) -> int:
    return sum(1 for s in cg.successors(node) if s != EXTERNAL)


__all__ = ["compute"]
