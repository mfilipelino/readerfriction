"""Path helpers used across layers."""

from __future__ import annotations

import fnmatch
from pathlib import Path


def matches_any(path: Path, root: Path, patterns: list[str]) -> bool:
    """Return True if ``path`` matches any exclude glob.

    Matches against both the absolute path and the path relative to ``root``,
    and also checks whether any component of the relative path equals an
    exclude directory name.
    """

    absolute = str(path)
    try:
        relative = str(path.relative_to(root))
    except ValueError:
        relative = absolute
    parts = set(path.parts)

    for pattern in patterns:
        if fnmatch.fnmatch(absolute, pattern):
            return True
        if fnmatch.fnmatch(relative, pattern):
            return True
        if pattern in parts:
            return True
        # Match nested directory name, e.g. "venv" should exclude "pkg/venv/x.py"
        rel_parts = Path(relative).parts
        if pattern in rel_parts:
            return True
    return False


def module_name_for(path: Path, root: Path) -> str:
    """Derive a dotted module name from a file path within ``root``."""

    path = path.resolve()
    root = root.resolve()
    try:
        rel = path.relative_to(root)
    except ValueError:
        rel = Path(path.name)
    parts = list(rel.with_suffix("").parts)
    if parts and parts[-1] == "__init__":
        parts.pop()
    return ".".join(parts) if parts else path.stem


__all__ = ["matches_any", "module_name_for"]
