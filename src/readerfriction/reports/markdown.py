"""Deterministic markdown report for ``ScanResult``."""

from __future__ import annotations

from pathlib import Path

from readerfriction.models import ScanResult

METRIC_DISPLAY_ORDER: tuple[str, ...] = (
    "trace_depth",
    "file_jumps",
    "wrapper_depth",
    "thin_wrapper_count",
    "flow_fragmentation",
    "context_width",
    "pass_through_ratio",
)

METRIC_LABELS: dict[str, str] = {
    "trace_depth": "Trace depth",
    "file_jumps": "File jumps",
    "wrapper_depth": "Wrapper depth",
    "thin_wrapper_count": "Thin wrappers",
    "flow_fragmentation": "Flow fragmentation",
    "context_width": "Context width",
    "pass_through_ratio": "Pass-through ratio",
}


def render(result: ScanResult) -> str:
    lines: list[str] = []
    root_display = _relative(result.root)
    lines.append(f"# ReaderFriction — `{root_display}`")
    lines.append("")
    lines.append(f"**Score:** {result.score}  —  **Severity:** {result.severity}")
    lines.append("")
    lines.append(f"_Scanned {result.scanned_files} file(s)._")
    lines.append("")

    lines.append("## Summary")
    lines.append("")
    lines.append("| Metric | Value |")
    lines.append("| --- | --- |")
    for key in METRIC_DISPLAY_ORDER:
        metric = result.summary.get(key)
        if metric is None:
            continue
        lines.append(f"| {METRIC_LABELS[key]} | {metric.display} |")
    lines.append("")

    lines.append("## Entrypoints")
    lines.append("")
    if not result.entrypoints:
        lines.append("_No entrypoints detected._")
    else:
        for entry in result.entrypoints:
            file_rel = _relative(entry.ref.file)
            lines.append(f"### `{entry.ref.qualname}` (score {entry.score})")
            lines.append("")
            lines.append(f"- **Location:** `{file_rel}:{entry.ref.lineno}`")
            lines.append(f"- **Path:** {_format_path(entry.path)}")
            lines.append("")
            lines.append("| Metric | Value |")
            lines.append("| --- | --- |")
            for key in METRIC_DISPLAY_ORDER:
                metric = entry.metrics.get(key)
                if metric is None:
                    continue
                lines.append(f"| {METRIC_LABELS[key]} | {metric.display} |")
            lines.append("")

    if result.parse_errors:
        lines.append("## Parse errors")
        lines.append("")
        for err in result.parse_errors:
            file_rel = _relative(err.file)
            lines.append(f"- `{file_rel}:{err.line}` — {err.message}")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def _format_path(path: list) -> str:
    if not path:
        return "_(empty)_"
    return " → ".join(f"`{ref.qualname}`" for ref in path)


def _relative(absolute: str) -> str:
    if not absolute:
        return absolute
    try:
        path = Path(absolute)
    except (TypeError, ValueError):
        return absolute
    return path.name if path.is_absolute() else absolute


__all__ = ["render"]
