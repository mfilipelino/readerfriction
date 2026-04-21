"""REQ-065 context_width = mean(arg_count + distinct self attrs) along path."""

from __future__ import annotations

import ast

from readerfriction.models import FunctionIR, FunctionRef, MetricResult


def compute(
    path: list[FunctionRef],
    ir_by_ref: dict[FunctionRef, FunctionIR],
    node_by_ref: dict[FunctionRef, ast.FunctionDef | ast.AsyncFunctionDef],
) -> MetricResult:
    if not path:
        return MetricResult(name="context_width", value=0.0, display="0.0")

    total = 0
    counted = 0
    for ref in path:
        ir = ir_by_ref.get(ref)
        if ir is None:
            continue
        counted += 1
        node = node_by_ref.get(ref)
        self_attrs = _distinct_self_attrs(node) if node is not None else 0
        total += ir.arg_count + self_attrs

    mean = (total / counted) if counted else 0.0
    return MetricResult(
        name="context_width",
        value=round(mean, 2),
        display=f"{mean:.2f}",
    )


def _distinct_self_attrs(node: ast.FunctionDef | ast.AsyncFunctionDef) -> int:
    names: set[str] = set()
    for child in ast.walk(node):
        if (
            isinstance(child, ast.Attribute)
            and isinstance(child.value, ast.Name)
            and child.value.id in {"self", "cls"}
        ):
            names.add(child.attr)
    return len(names)


__all__ = ["compute"]
