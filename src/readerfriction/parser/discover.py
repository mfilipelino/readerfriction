"""Recursively find ``*.py`` files under one or more roots."""

from __future__ import annotations

from pathlib import Path

from readerfriction.utils.paths import matches_any


def discover_python_files(root: Path, excludes: list[str]) -> list[Path]:
    """Return all ``.py`` files under ``root``, excluding any glob match.

    The returned list is sorted lexicographically for deterministic output
    (REQ-023). ``excludes`` is expected to already include the defaults; see
    ``Config.all_excludes``.
    """

    root = root.resolve()
    if root.is_file():
        return [root] if root.suffix == ".py" else []

    results: list[Path] = []
    for path in root.rglob("*.py"):
        if matches_any(path, root, excludes):
            continue
        results.append(path)
    return sorted(results)


__all__ = ["discover_python_files"]
