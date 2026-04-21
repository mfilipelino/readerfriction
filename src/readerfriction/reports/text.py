"""Terminal text report using ``rich``."""

from __future__ import annotations

import io

from rich.console import Console
from rich.table import Table

from readerfriction.models import ScanResult
from readerfriction.reports.markdown import METRIC_DISPLAY_ORDER, METRIC_LABELS

SEVERITY_STYLES = {
    "ok": "bold green",
    "warn": "bold yellow",
    "error": "bold red",
}


def render(result: ScanResult, *, color: bool = True) -> str:
    console = Console(
        record=True,
        color_system="auto" if color else None,
        width=100,
        file=io.StringIO(),
        force_terminal=False,
    )
    style = SEVERITY_STYLES.get(result.severity, "bold")
    console.print(
        f"[bold]ReaderFriction[/bold] — {result.root}",
    )
    console.print(
        f"score [bold]{result.score}[/bold]  "
        f"severity [{style}]{result.severity}[/{style}]  "
        f"files {result.scanned_files}"
    )

    console.print()
    table = Table(title="Summary", title_style="bold", show_lines=False)
    table.add_column("Metric")
    table.add_column("Value", justify="right")
    for key in METRIC_DISPLAY_ORDER:
        metric = result.summary.get(key)
        if metric is None:
            continue
        table.add_row(METRIC_LABELS[key], metric.display)
    console.print(table)

    for entry in result.entrypoints:
        console.print()
        console.print(
            f"[bold]{entry.ref.qualname}[/bold] "
            f"(score {entry.score}, {entry.ref.file}:{entry.ref.lineno})"
        )
        path_display = " -> ".join(ref.qualname for ref in entry.path)
        console.print(f"path: {path_display}")
        table = Table(show_lines=False)
        table.add_column("Metric")
        table.add_column("Value", justify="right")
        for key in METRIC_DISPLAY_ORDER:
            metric = entry.metrics.get(key)
            if metric is None:
                continue
            table.add_row(METRIC_LABELS[key], metric.display)
        console.print(table)

    return console.export_text()


__all__ = ["render"]
