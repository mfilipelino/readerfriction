"""REQ-061 file_jumps = distinct files on the trace path minus 1."""

from __future__ import annotations

from readerfriction.models import FunctionRef, MetricResult


def compute(path: list[FunctionRef]) -> MetricResult:
    files = {p.file for p in path if p.file}
    jumps = max(len(files) - 1, 0)
    return MetricResult(name="file_jumps", value=float(jumps), display=str(jumps))


__all__ = ["compute"]
