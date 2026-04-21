"""Select the ``P*`` trace path used by every metric.

``spec/metrics.md`` defines ``P*`` as the longest simple path from an
entrypoint to a non-wrapper function, with ties broken lexicographically.
"""

from __future__ import annotations

import networkx as nx

from readerfriction.graph.callgraph import EXTERNAL, CallGraph
from readerfriction.models import FunctionRef

MAX_PATH_LENGTH = 64  # safety cap; defends against pathological graphs


def select_trace_path(
    cg: CallGraph,
    entry: FunctionRef,
    wrappers: set[FunctionRef],
) -> list[FunctionRef]:
    """Return the chosen trace path starting at ``entry``.

    Uses DFS with a visited set (REQ-052) so cycles do not cause recursion.
    """

    if entry not in cg.graph:
        return [entry]

    best: list[FunctionRef] = [entry]
    best_key: tuple[str, str, int] = _path_key(best)

    stack: list[tuple[FunctionRef, list[FunctionRef], set[FunctionRef]]] = [
        (entry, [entry], {entry})
    ]

    while stack:
        _node, path, visited = stack.pop()
        if len(path) > MAX_PATH_LENGTH:
            continue
        leaf = path[-1]
        if leaf != entry and leaf not in wrappers and leaf != EXTERNAL:
            # leaf is a meaningful function — candidate path
            candidate = list(path)
            candidate_key = _path_key(candidate)
            if len(candidate) > len(best) or (
                len(candidate) == len(best) and candidate_key < best_key
            ):
                best = candidate
                best_key = candidate_key
        for succ in sorted(cg.successors(leaf), key=lambda r: (r.file, r.lineno, r.qualname)):
            if succ == EXTERNAL or succ in visited:
                continue
            stack.append((succ, [*path, succ], visited | {succ}))

    return best


def _path_key(path: list[FunctionRef]) -> tuple[str, str, int]:
    if not path:
        return ("", "", 0)
    return (path[0].qualname, path[-1].qualname, len(path))


def all_reachable_functions(cg: CallGraph, entry: FunctionRef) -> set[FunctionRef]:
    """Every in-scope function reachable from ``entry`` (excluding external)."""

    if entry not in cg.graph:
        return set()
    reachable = nx.descendants(cg.graph, entry) | {entry}
    reachable.discard(EXTERNAL)
    return reachable


__all__ = ["MAX_PATH_LENGTH", "all_reachable_functions", "select_trace_path"]
