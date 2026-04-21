"""ReaderFriction CLI entrypoint."""

from __future__ import annotations

import re
from enum import Enum
from pathlib import Path

import typer

from readerfriction.classify.wrappers import classify_function
from readerfriction.config import Config, find_pyproject, load_config
from readerfriction.graph.callgraph import build_call_graph
from readerfriction.models import (
    ExplainResult,
    FunctionRef,
    ScanResult,
    TraceResult,
)
from readerfriction.parser.ast_parse import parse_file
from readerfriction.parser.discover import discover_python_files
from readerfriction.pipeline import scan_project
from readerfriction.reports import json_report, markdown, text

app = typer.Typer(
    name="readerfriction",
    no_args_is_help=True,
    add_completion=False,
    help="Measure navigational complexity in Python codebases.",
)


class OutputFormat(str, Enum):
    text = "text"
    json = "json"
    markdown = "markdown"


FAIL_ON_PATTERN = re.compile(
    r"^\s*(?P<metric>[a-z_]+)\s*(?P<op>>=|<=|==|>|<)\s*(?P<value>\d+(?:\.\d+)?)\s*$"
)


@app.command()
def scan(
    path: Path = typer.Argument(..., exists=True),
    format: OutputFormat = typer.Option(OutputFormat.text, "--format"),
    out: Path | None = typer.Option(None, "--out"),
    fail_on: str | None = typer.Option(None, "--fail-on"),
    exclude: list[str] = typer.Option([], "--exclude"),
    config_path: Path | None = typer.Option(None, "--config"),
    no_color: bool = typer.Option(False, "--no-color"),
) -> None:
    """Scan a project path and report metrics."""

    result = _run_scan(path, exclude, config_path)
    _write(_render(result, format, color=not no_color), out)
    _apply_fail_on(fail_on, result)


@app.command()
def trace(
    target: str = typer.Argument(..., help="file.py:func"),
    format: OutputFormat = typer.Option(OutputFormat.text, "--format"),
    out: Path | None = typer.Option(None, "--out"),
    config_path: Path | None = typer.Option(None, "--config"),
    exclude: list[str] = typer.Option([], "--exclude"),
) -> None:
    """Trace a function along its chosen trace path."""

    file_path, func_name = _parse_target(target)
    root = file_path.parent
    config = _load_cli_config(config_path, exclude)
    scan_result = scan_project(root, config)
    trace_result = _build_trace_result(scan_result, file_path, func_name)
    _write(_render_trace(trace_result, format), out)


@app.command()
def explain(
    target: str = typer.Argument(..., help="file.py:func"),
    format: OutputFormat = typer.Option(OutputFormat.text, "--format"),
    out: Path | None = typer.Option(None, "--out"),
    config_path: Path | None = typer.Option(None, "--config"),
) -> None:
    """Explain wrapper classification for a function."""

    file_path, func_name = _parse_target(target)
    config = _load_cli_config(config_path, [])
    explain_result = _build_explain(file_path, func_name, config)
    _write(_render_explain(explain_result, format), out)


@app.command()
def report(
    path: Path = typer.Argument(..., exists=True),
    format: OutputFormat = typer.Option(OutputFormat.markdown, "--format"),
    out: Path | None = typer.Option(None, "--out"),
    exclude: list[str] = typer.Option([], "--exclude"),
    config_path: Path | None = typer.Option(None, "--config"),
    fail_on: str | None = typer.Option(None, "--fail-on"),
) -> None:
    """Render a report for a project."""

    result = _run_scan(path, exclude, config_path)
    _write(_render(result, format, color=False), out)
    _apply_fail_on(fail_on, result)


@app.command()
def diff(
    path: Path = typer.Argument(..., exists=True),
    base: Path = typer.Option(..., "--base", exists=True),
    head: Path | None = typer.Option(None, "--head"),
    format: OutputFormat = typer.Option(OutputFormat.text, "--format"),
    out: Path | None = typer.Option(None, "--out"),
    exclude: list[str] = typer.Option([], "--exclude"),
    config_path: Path | None = typer.Option(None, "--config"),
) -> None:
    """Compare two scan roots (v0.1 scope is local paths, not git refs)."""

    head_root = head or path
    config = _load_cli_config(config_path, exclude)
    base_scan = scan_project(base, config)
    head_scan = scan_project(head_root, config)

    delta = head_scan.score - base_scan.score
    symbol = "+" if delta > 0 else ("" if delta == 0 else "-")
    lines = [
        f"Base:  {base_scan.score} ({base})",
        f"Head:  {head_scan.score} ({head_root})",
        f"Delta: {symbol}{abs(delta)}",
    ]
    _write("\n".join(lines) + "\n", out)


# --- helpers ---------------------------------------------------------------


def _run_scan(
    path: Path, exclude: list[str], config_path: Path | None
) -> ScanResult:
    config = _load_cli_config(config_path, exclude)
    return scan_project(path, config)


def _load_cli_config(config_path: Path | None, extra_excludes: list[str]) -> Config:
    pyproject = config_path or find_pyproject(Path.cwd())
    overrides: dict[str, object] = {}
    if extra_excludes:
        overrides["exclude"] = list(extra_excludes)
    return load_config(pyproject, overrides=overrides)


def _render(result: ScanResult, fmt: OutputFormat, *, color: bool) -> str:
    if fmt is OutputFormat.json:
        return json_report.render(result) + "\n"
    if fmt is OutputFormat.markdown:
        return markdown.render(result)
    return text.render(result, color=color)


def _render_trace(result: TraceResult, fmt: OutputFormat) -> str:
    if fmt is OutputFormat.json:
        return json_report.render(result) + "\n"
    path_str = " -> ".join(ref.qualname for ref in result.path)
    lines = [f"trace: {result.entry.qualname}", f"path:  {path_str}"]
    return "\n".join(lines) + "\n"


def _render_explain(result: ExplainResult, fmt: OutputFormat) -> str:
    if fmt is OutputFormat.json:
        return json_report.render(result) + "\n"
    lines = [
        f"target: {result.target.qualname}",
        f"wrapper: {result.classification.is_wrapper}",
        f"matched rules: {', '.join(result.classification.matched_rules) or '(none)'}",
        f"score: {result.classification.score}/8 (threshold {result.classification.threshold})",
    ]
    return "\n".join(lines) + "\n"


def _parse_target(target: str) -> tuple[Path, str]:
    if ":" not in target:
        raise typer.BadParameter("target must be file.py:func", param_hint="target")
    file_str, _, func = target.rpartition(":")
    path = Path(file_str)
    if not path.is_file():
        raise typer.BadParameter(f"file not found: {file_str}", param_hint="target")
    if not func:
        raise typer.BadParameter("missing function name", param_hint="target")
    return path, func


def _build_trace_result(
    scan_result: ScanResult, file_path: Path, func_name: str
) -> TraceResult:
    entry = _find_entry(scan_result, file_path, func_name)
    matched = next(
        (e for e in scan_result.entrypoints if e.ref == entry),
        None,
    )
    if matched is None:
        raise typer.BadParameter(
            f"no trace computed for {func_name}", param_hint="target"
        )
    return TraceResult(
        entry=entry,
        path=matched.path,
        metrics=matched.metrics,
        wrappers=[ref for ref in matched.path if _is_wrapper_on_path(ref, matched.path)],
    )


def _is_wrapper_on_path(_ref: FunctionRef, _path: list[FunctionRef]) -> bool:
    # For now the trace result does not distinguish wrappers — the metrics do.
    return False


def _find_entry(scan_result: ScanResult, file_path: Path, func_name: str) -> FunctionRef:
    target_file = str(file_path.resolve())
    for entry in scan_result.entrypoints:
        if entry.ref.file == target_file and entry.ref.qualname.endswith(f".{func_name}"):
            return entry.ref
    # Fall back to qualname match alone (file may disagree if called with a short path)
    for entry in scan_result.entrypoints:
        if entry.ref.qualname.endswith(f".{func_name}"):
            return entry.ref
    raise typer.BadParameter(
        f"no entrypoint {func_name} found in {file_path}", param_hint="target"
    )


def _build_explain(file_path: Path, func_name: str, config: Config) -> ExplainResult:
    root = file_path.parent
    parsed = parse_file(file_path, root)
    func = next(
        (f for f in parsed.ir.functions if f.name == func_name),
        None,
    )
    if func is None:
        raise typer.BadParameter(f"function {func_name} not in {file_path}")
    node = parsed.function_nodes.get(func.ref.qualname)
    if node is None:
        raise typer.BadParameter(f"AST missing for {func_name}")
    classification = classify_function(
        func.ref, node, threshold=config.wrapper_threshold
    )

    files = discover_python_files(root, config.all_excludes)
    modules = [parse_file(p, root).ir for p in files]
    cg = build_call_graph(modules)
    callers = sorted(
        {e.caller for e in cg.edges() if e.callee == func.ref},
        key=lambda r: r.qualname,
    )
    callees = sorted(
        cg.successors(func.ref),
        key=lambda r: r.qualname,
    )
    return ExplainResult(
        target=func.ref,
        classification=classification,
        arg_count=func.arg_count,
        decorators=func.decorator_names,
        callers=callers,
        callees=[c for c in callees if c.qualname != "<external>"],
    )


def _write(content: str, out: Path | None) -> None:
    if out is None:
        typer.echo(content, nl=False)
        return
    out.write_text(content)
    typer.echo(f"wrote {out}")


def _apply_fail_on(expression: str | None, result: ScanResult) -> None:
    if not expression:
        return
    m = FAIL_ON_PATTERN.match(expression)
    if m is None:
        raise typer.BadParameter(
            "expected 'metric OP number', e.g. 'score>20'", param_hint="--fail-on"
        )
    metric = m.group("metric")
    op = m.group("op")
    value = float(m.group("value"))

    observed = _metric_value(result, metric)
    if observed is None:
        raise typer.BadParameter(
            f"unknown metric '{metric}' for --fail-on", param_hint="--fail-on"
        )
    truthy = {
        ">": observed > value,
        ">=": observed >= value,
        "<": observed < value,
        "<=": observed <= value,
        "==": observed == value,
    }[op]
    if truthy:
        typer.echo(
            f"--fail-on triggered: {metric}={observed} {op} {value}", err=True
        )
        raise typer.Exit(code=1)


def _metric_value(result: ScanResult, metric: str) -> float | None:
    if metric == "score":
        return float(result.score)
    summary = result.summary.get(metric)
    if summary is None:
        return None
    return float(summary.value)


if __name__ == "__main__":
    app()
