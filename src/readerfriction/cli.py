"""ReaderFriction CLI entrypoint."""

from __future__ import annotations

import re
from enum import Enum
from pathlib import Path

import typer

from readerfriction import __version__
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
from readerfriction.pipeline import scan_project, scan_project_detail
from readerfriction.reports import agent_prompt, json_report, markdown, text

app = typer.Typer(
    name="rf",
    no_args_is_help=True,
    add_completion=False,
    help=(
        "ReaderFriction — measure navigational complexity in Python codebases.\n\n"
        "Commands:\n"
        "  scan     Report metrics for every entrypoint in a project.\n"
        "  trace    Show the chosen trace path from one entrypoint.\n"
        "  explain  Explain why rf classified one function as a wrapper.\n"
        "  report   Render a markdown report (good for PR comments).\n"
        "  diff     Compare rf scores between two local project paths.\n"
        "  agent    Emit a prompt that tells an AI coding agent how to\n"
        "           lower the score WITHOUT gaming the metric (no\n"
        "           one-file collapse, no function merging, no classifier\n"
        "           evasion). See docs/limits-and-anti-gaming.md.\n"
        "  config   Print the default [tool.readerfriction] TOML with\n"
        "           inline comments — copy into your pyproject.toml to\n"
        "           customise weights, thresholds, or max_file_lines.\n\n"
        "All commands accept --format {text,json,markdown}, --out <file>,\n"
        "--exclude <glob>, and --config <pyproject.toml>. --fail-on\n"
        "'metric OP number' makes scan/report exit 1 when the threshold\n"
        "trips.\n\n"
        "Configuration lives under [tool.readerfriction] in pyproject.toml.\n"
        "Run `rf config` to print the defaults (weights per metric, warn/\n"
        "error thresholds for the severity label, max_file_lines for\n"
        "haystack detection, wrapper_threshold for the 8-rule classifier,\n"
        "exclude globs). Run any command with --help for its full option list."
    ),
)


class OutputFormat(str, Enum):
    text = "text"
    json = "json"
    markdown = "markdown"


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(f"readerfriction {__version__}")
        raise typer.Exit()


@app.callback()
def _main(
    version: bool = typer.Option(
        False,
        "--version",
        callback=_version_callback,
        is_eager=True,
        help="Show the installed ReaderFriction version and exit.",
    ),
) -> None:
    """Root callback; only hosts the --version flag."""


FAIL_ON_PATTERN = re.compile(
    r"^\s*(?P<metric>[a-z_]+)\s*(?P<op>>=|<=|==|>|<)\s*(?P<value>\d+(?:\.\d+)?)\s*$"
)


@app.command()
def scan(
    path: Path = typer.Argument(
        ..., exists=True, help="Project root directory (or single .py file) to scan."
    ),
    format: OutputFormat = typer.Option(
        OutputFormat.text,
        "--format",
        help="Output format: 'text' (rich tables), 'json' (schema-validated), 'markdown'.",
    ),
    out: Path | None = typer.Option(
        None, "--out", help="Write output to this path instead of stdout."
    ),
    fail_on: str | None = typer.Option(
        None,
        "--fail-on",
        help=(
            "Exit 1 if the expression is truthy. Grammar: "
            "'<metric> <op> <number>' where metric ∈ {score, trace_depth, "
            "file_jumps, wrapper_depth, thin_wrapper_count, context_width, "
            "flow_fragmentation, pass_through_ratio} and op ∈ {>, >=, <, <=, ==}. "
            "Example: --fail-on 'score>30'."
        ),
    ),
    exclude: list[str] = typer.Option(
        [],
        "--exclude",
        help=(
            "Glob pattern to exclude from discovery (repeatable). "
            "Default excludes venv, .venv, build, dist, __pycache__, .git, "
            ".tox, .mypy_cache, .pytest_cache, .ruff_cache."
        ),
    ),
    config_path: Path | None = typer.Option(
        None,
        "--config",
        help=(
            "Path to a pyproject.toml containing [tool.readerfriction]. "
            "Defaults to the nearest pyproject.toml walking up from the scan target."
        ),
    ),
    no_color: bool = typer.Option(
        False, "--no-color", help="Disable ANSI colour in text output."
    ),
) -> None:
    """Scan a project and report metrics for every entrypoint.

    Output includes: total score (weighted sum), severity (ok/warn/error
    against configurable thresholds), per-entrypoint metrics, and the
    chosen trace path from each entrypoint to the first meaningful
    (non-wrapper) function.
    """

    result = _run_scan(path, exclude, config_path)
    _write(_render(result, format, color=not no_color), out)
    _apply_fail_on(fail_on, result)


@app.command()
def trace(
    target: str = typer.Argument(
        ..., help="Target entrypoint as 'file.py:func' (e.g. 'src/cli.py:main')."
    ),
    format: OutputFormat = typer.Option(
        OutputFormat.text, "--format", help="Output format."
    ),
    out: Path | None = typer.Option(None, "--out", help="Destination file."),
    config_path: Path | None = typer.Option(
        None, "--config", help="Path to pyproject.toml with [tool.readerfriction]."
    ),
    exclude: list[str] = typer.Option(
        [], "--exclude", help="Additional exclude globs."
    ),
) -> None:
    """Print the chosen trace path from one entrypoint.

    The trace path is the longest simple path (up to the max-length cap)
    from the entrypoint to the first non-wrapper function, ties broken
    lexicographically. Useful for confirming what rf considers the
    'main path' before interpreting a score.
    """

    file_path, func_name = _parse_target(target)
    root = file_path.parent
    config = _load_cli_config(config_path, exclude)
    scan_result = scan_project(root, config)
    trace_result = _build_trace_result(scan_result, file_path, func_name)
    _write(_render_trace(trace_result, format), out)


@app.command()
def explain(
    target: str = typer.Argument(
        ..., help="Target function as 'file.py:func'."
    ),
    format: OutputFormat = typer.Option(
        OutputFormat.text, "--format", help="Output format."
    ),
    out: Path | None = typer.Option(None, "--out", help="Destination file."),
    config_path: Path | None = typer.Option(
        None, "--config", help="Path to pyproject.toml."
    ),
) -> None:
    """Explain the wrapper classification for a single function.

    Shows which of the 8 wrapper-heuristic rules (W-01..W-08) fired, the
    threshold, and the list of callers and callees. Use this to decide
    whether a function flagged as a wrapper should actually be inlined
    or whether rf is confused.
    """

    file_path, func_name = _parse_target(target)
    config = _load_cli_config(config_path, [])
    explain_result = _build_explain(file_path, func_name, config)
    _write(_render_explain(explain_result, format), out)


@app.command()
def report(
    path: Path = typer.Argument(..., exists=True, help="Project root to report on."),
    format: OutputFormat = typer.Option(
        OutputFormat.markdown,
        "--format",
        help="Default 'markdown'; also accepts 'text' and 'json'.",
    ),
    out: Path | None = typer.Option(
        None,
        "--out",
        help="Write the report here; common usage is '--out reader-friction.md'.",
    ),
    exclude: list[str] = typer.Option([], "--exclude", help="Exclude globs."),
    config_path: Path | None = typer.Option(None, "--config", help="pyproject path."),
    fail_on: str | None = typer.Option(
        None, "--fail-on", help="Exit 1 if the expression is truthy (see scan --help)."
    ),
) -> None:
    """Render a report for a project.

    Same data as 'scan' but defaults to markdown output so the result
    can be pasted into a PR comment or committed to the repository.
    """

    result = _run_scan(path, exclude, config_path)
    _write(_render(result, format, color=False), out)
    _apply_fail_on(fail_on, result)


@app.command()
def diff(
    path: Path = typer.Argument(
        ..., exists=True, help="HEAD project root (defaults to --head if omitted)."
    ),
    base: Path = typer.Option(
        ..., "--base", exists=True, help="BASE project root to compare against."
    ),
    head: Path | None = typer.Option(
        None, "--head", help="HEAD project root (overrides positional path)."
    ),
    format: OutputFormat = typer.Option(
        OutputFormat.text, "--format", help="Output format."
    ),
    out: Path | None = typer.Option(None, "--out", help="Destination file."),
    exclude: list[str] = typer.Option([], "--exclude", help="Exclude globs."),
    config_path: Path | None = typer.Option(None, "--config", help="pyproject path."),
) -> None:
    """Compare rf scores between two local project paths.

    v0.1 scope is local directories only — git-ref support is a 0.2
    follow-up. Prints base score, head score, and the delta.
    """

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


@app.command()
def agent(
    path: Path = typer.Argument(
        ..., exists=True, help="Project root to analyse for the agent prompt."
    ),
    out: Path | None = typer.Option(
        None, "--out", help="Write the prompt here instead of stdout."
    ),
    exclude: list[str] = typer.Option([], "--exclude", help="Exclude globs."),
    config_path: Path | None = typer.Option(None, "--config", help="pyproject path."),
) -> None:
    """Emit an AI-coding-agent prompt for refactoring the project.

    The prompt front-loads what NOT to do (don't collapse files, don't
    merge functions into one, don't defeat the wrapper classifier with
    no-op statements, don't rename superficially, don't hide calls
    behind dynamic dispatch) because the rf score is cheaply gameable
    if naively optimised. It then lists the real refactors to apply —
    inline wrapper chains, reduce entrypoint fan-out, tighten context
    width — with concrete targets derived from the current scan.

    Typical usage:

        rf agent src/ --out .claude/refactor-prompt.md
        claude -p "$(cat .claude/refactor-prompt.md)"

    Or pipe directly:

        rf agent src/ | claude -

    See docs/limits-and-anti-gaming.md for the reasoning behind every
    'do not' rule.
    """

    config = _load_cli_config(config_path, exclude)
    scan_result, wrappers = scan_project_detail(path, config)
    prompt_text = agent_prompt.render(scan_result, wrappers)
    _write(prompt_text, out)


@app.command()
def config(
    out: Path | None = typer.Option(
        None, "--out", help="Write the TOML here instead of stdout."
    ),
) -> None:
    """Print the default [tool.readerfriction] TOML for pyproject.toml.

    Useful when cloning the repo or adopting rf in a new project: run

        rf config >> pyproject.toml

    to append the defaults, then adjust. Every key is documented inline
    so the file is self-explanatory. See spec/config.md for the
    normative reference.
    """

    _write(_default_toml(), out)


def _default_toml() -> str:
    defaults = Config()
    weights = defaults.weights.model_dump()
    thresholds = defaults.thresholds.model_dump()
    lines = [
        "# Default ReaderFriction configuration. Copy into pyproject.toml",
        "# and adjust as needed. `rf config --help` explains every key.",
        "",
        "[tool.readerfriction]",
        "# Additional glob patterns to exclude from discovery. Defaults",
        "# already cover venv, .venv, build, dist, __pycache__, .git, .tox,",
        "# .mypy_cache, .pytest_cache, .ruff_cache.",
        f"exclude = {defaults.exclude!r}",
        "",
        "# 8-rule wrapper classifier threshold. A function matching at least",
        "# this many rules AND every disqualifier rule (W-02 / W-04 / W-05",
        "# / W-06 / W-07) is classified as a thin wrapper. Default 6 of 8.",
        f"wrapper_threshold = {defaults.wrapper_threshold}",
        "",
        "# Files on the trace path longer than this count as 'haystack' files",
        "# and contribute to the long_files metric. 500 lines is a typical",
        "# style-guide ceiling (Google ~400; Python community ~500).",
        f"max_file_lines = {defaults.max_file_lines}",
        "",
        "# Weights applied in the reader_friction_score aggregate. Higher =",
        "# more punishment. pass_through_ratio is reported but NOT scored.",
        "[tool.readerfriction.weights]",
        f"trace_depth        = {weights['trace_depth']}",
        f"file_jumps         = {weights['file_jumps']}",
        f"long_files         = {weights['long_files']}",
        f"wrapper_depth      = {weights['wrapper_depth']}",
        f"thin_wrapper_count = {weights['thin_wrapper_count']}",
        f"context_width      = {weights['context_width']}",
        f"flow_fragmentation = {weights['flow_fragmentation']}",
        "",
        "# Severity labels shown on the text report header. score < warn →",
        "# 'ok'; warn <= score < error → 'warn'; score >= error → 'error'.",
        "# Separate from --fail-on, which is an ad-hoc per-invocation gate.",
        "[tool.readerfriction.thresholds]",
        f"warn  = {thresholds['warn']}",
        f"error = {thresholds['error']}",
    ]
    return "\n".join(lines) + "\n"


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
