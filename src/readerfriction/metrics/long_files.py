"""REQ-068 long_files — count oversized files on the trace path.

A file that cannot comfortably fit on one screen is a reader-friction
signal that `rf` could not previously see: under `file_jumps` alone, a
2000-line haystack file scored zero regardless of its actual size.
`long_files` counts files on ``P*`` whose total line count exceeds
``max_file_lines`` (default 500, about ten screenfuls).

This metric exists specifically to penalise Attack A from
``docs/limits-and-anti-gaming.md`` (collapse many files into one) inside
`rf`'s number, rather than only via the external tooling recipe.

Design notes:

- File-level, not per-hop. Reordering functions within a file does not
  game the metric — only splitting the file does, which is the intended
  response.
- Line count is recorded at parse time (see ``parser.ast_parse.parse_file``)
  so there is no extra I/O in the metric itself.
- Files on the path that failed to parse are skipped.
"""

from __future__ import annotations

from pathlib import Path

from readerfriction.models import FunctionRef, MetricResult


def compute(
    path: list[FunctionRef],
    file_line_counts: dict[str, int],
    max_file_lines: int = 500,
) -> MetricResult:
    if not path:
        return MetricResult(
            name="long_files",
            value=0.0,
            display="0",
            detail={"threshold": str(max_file_lines)},
        )

    files_on_path: set[str] = {p.file for p in path if p.file}
    oversized: list[tuple[str, int]] = []
    for file_str in sorted(files_on_path):
        line_count = file_line_counts.get(file_str, 0)
        if line_count > max_file_lines:
            oversized.append((file_str, line_count))

    detail: dict[str, str] = {"threshold": str(max_file_lines)}
    if oversized:
        detail["files"] = "; ".join(
            f"{Path(f).name}:{n}" for f, n in oversized
        )

    return MetricResult(
        name="long_files",
        value=float(len(oversized)),
        display=str(len(oversized)),
        detail=detail,
    )


__all__ = ["compute"]
