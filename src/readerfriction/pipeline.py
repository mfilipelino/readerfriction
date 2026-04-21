"""End-to-end pipeline: paths → ScanResult.

Kept deliberately small — the heavy lifting lives in the specialist modules.
This file is the single place where we wire them together for the CLI.
"""

from __future__ import annotations

import ast
from collections.abc import Iterable
from pathlib import Path

from readerfriction.classify.wrappers import classify_function
from readerfriction.config import Config
from readerfriction.graph.callgraph import CallGraph, build_call_graph
from readerfriction.metrics import (
    context_width,
    file_jumps,
    flow_fragmentation,
    pass_through_ratio,
    thin_wrappers,
    trace_depth,
    wrapper_depth,
)
from readerfriction.metrics import (
    score as score_module,
)
from readerfriction.metrics.path_select import all_reachable_functions, select_trace_path
from readerfriction.models import (
    EntrypointResult,
    FunctionIR,
    FunctionRef,
    MetricResult,
    ModuleIR,
    ParseError,
    ScanResult,
    Severity,
)
from readerfriction.parser.ast_parse import ParsedModule, parse_file
from readerfriction.parser.discover import discover_python_files
from readerfriction.parser.entrypoints import detect_entrypoints


def scan_project(root: Path, config: Config) -> ScanResult:
    root = root.resolve()
    files = discover_python_files(root, config.all_excludes)
    parsed_modules = [parse_file(path, root) for path in files]

    modules = [pm.ir for pm in parsed_modules]
    parse_errors: list[ParseError] = [pe for m in modules for pe in m.parse_errors]

    cg = build_call_graph(modules)
    ir_by_ref, node_by_ref = _index_parsed(parsed_modules)
    wrappers = _classify_all(parsed_modules, config.wrapper_threshold, ir_by_ref)

    entries = detect_entrypoints(modules)
    entry_results: list[EntrypointResult] = []
    for entry in entries:
        entry_results.append(
            _compute_entrypoint(entry, cg, wrappers, ir_by_ref, node_by_ref, config)
        )

    summary = _summarise(entry_results, cg, wrappers, ir_by_ref)
    total_score = score_module.compute(summary, config.weights)
    severity = _severity_for(total_score, config)

    return ScanResult(
        root=str(root),
        scanned_files=len(files),
        parse_errors=parse_errors,
        entrypoints=entry_results,
        summary=summary,
        score=total_score,
        severity=severity,
    )


def _index_parsed(
    parsed_modules: Iterable[ParsedModule],
) -> tuple[
    dict[FunctionRef, FunctionIR],
    dict[FunctionRef, ast.FunctionDef | ast.AsyncFunctionDef],
]:
    ir_by_ref: dict[FunctionRef, FunctionIR] = {}
    node_by_ref: dict[FunctionRef, ast.FunctionDef | ast.AsyncFunctionDef] = {}
    for pm in parsed_modules:
        for func in pm.ir.functions:
            ir_by_ref[func.ref] = func
            node = pm.function_nodes.get(func.ref.qualname)
            if node is not None:
                node_by_ref[func.ref] = node
    return ir_by_ref, node_by_ref


def _classify_all(
    parsed_modules: Iterable[ParsedModule],
    threshold: int,
    ir_by_ref: dict[FunctionRef, FunctionIR],
) -> set[FunctionRef]:
    wrappers: set[FunctionRef] = set()
    for pm in parsed_modules:
        for func in pm.ir.functions:
            node = pm.function_nodes.get(func.ref.qualname)
            if node is None:
                continue
            classification = classify_function(func.ref, node, threshold=threshold)
            if classification.is_wrapper:
                wrappers.add(func.ref)
    # Silence the unused-arg warning: ir_by_ref not needed here but kept for
    # future callers that might pass extra signals in.
    _ = ir_by_ref
    return wrappers


def _compute_entrypoint(
    entry: FunctionRef,
    cg: CallGraph,
    wrappers: set[FunctionRef],
    ir_by_ref: dict[FunctionRef, FunctionIR],
    node_by_ref: dict[FunctionRef, ast.FunctionDef | ast.AsyncFunctionDef],
    config: Config,
) -> EntrypointResult:
    path = select_trace_path(cg, entry, wrappers)
    in_scope = all_reachable_functions(cg, entry)

    metrics: dict[str, MetricResult] = {
        "trace_depth": trace_depth.compute(path),
        "file_jumps": file_jumps.compute(path),
        "wrapper_depth": wrapper_depth.compute(path, wrappers),
        "thin_wrapper_count": thin_wrappers.compute(path, wrappers),
        "flow_fragmentation": flow_fragmentation.compute(cg, path),
        "context_width": context_width.compute(path, ir_by_ref, node_by_ref),
        "pass_through_ratio": pass_through_ratio.compute(in_scope, wrappers),
    }
    score = score_module.compute(metrics, config.weights)

    return EntrypointResult(
        ref=entry,
        path=path,
        metrics=metrics,
        score=score,
    )


def _summarise(
    entries: list[EntrypointResult],
    cg: CallGraph,
    wrappers: set[FunctionRef],
    ir_by_ref: dict[FunctionRef, FunctionIR],
) -> dict[str, MetricResult]:
    """Project-level summary: max of each metric across entrypoints, plus the
    global ``pass_through_ratio`` over all in-scope functions.
    """

    all_in_scope = set(ir_by_ref.keys())
    if not entries:
        ptr = pass_through_ratio.compute(all_in_scope, wrappers)
        return {"pass_through_ratio": ptr, "trace_depth": _zero("trace_depth"), "file_jumps": _zero("file_jumps"), "wrapper_depth": _zero("wrapper_depth"), "thin_wrapper_count": _zero("thin_wrapper_count"), "flow_fragmentation": _zero("flow_fragmentation"), "context_width": _zero("context_width")}

    aggregated: dict[str, MetricResult] = {}
    for key in (
        "trace_depth",
        "file_jumps",
        "wrapper_depth",
        "thin_wrapper_count",
        "flow_fragmentation",
        "context_width",
    ):
        values = [e.metrics[key].value for e in entries]
        peak = max(values)
        if key == "context_width":
            aggregated[key] = MetricResult(name=key, value=peak, display=f"{peak:.2f}")
        else:
            aggregated[key] = MetricResult(
                name=key, value=peak, display=str(round(peak))
            )

    aggregated["pass_through_ratio"] = pass_through_ratio.compute(all_in_scope, wrappers)
    _ = cg  # unused; kept for symmetry should we introduce graph-level summaries.
    return aggregated


def _zero(name: str) -> MetricResult:
    return MetricResult(name=name, value=0.0, display="0")


def _severity_for(score: int, config: Config) -> Severity:
    if score >= config.thresholds.error:
        return "error"
    if score >= config.thresholds.warn:
        return "warn"
    return "ok"


def _unused() -> None:
    """Keep ``ModuleIR`` import alive for tools that track re-exports."""

    _ = ModuleIR


__all__ = ["scan_project"]
