"""Build a ``networkx`` call graph from parsed modules."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

import networkx as nx

from readerfriction.graph.resolve import SymbolTable
from readerfriction.models import CallEdge, FunctionRef, ModuleIR

EXTERNAL = FunctionRef(qualname="<external>", file="", lineno=0)


@dataclass
class CallGraph:
    """Wraps the networkx DiGraph and exposes a few helpers."""

    graph: nx.DiGraph
    symbols: SymbolTable

    @property
    def nodes(self) -> list[FunctionRef]:
        return list(self.graph.nodes)

    def successors(self, node: FunctionRef) -> list[FunctionRef]:
        if node not in self.graph:
            return []
        return list(self.graph.successors(node))

    def edges(self) -> list[CallEdge]:
        out: list[CallEdge] = []
        for u, v, data in self.graph.edges(data=True):
            out.append(
                CallEdge(
                    caller=u,
                    callee=v,
                    call_lineno=data.get("call_lineno", 0),
                    external=data.get("external", False),
                )
            )
        return out


def build_call_graph(modules: Iterable[ModuleIR]) -> CallGraph:
    """Resolve every call site and emit a DiGraph.

    Unresolved targets become edges to ``EXTERNAL`` tagged ``external=True``
    (REQ-051). Cycles are preserved (REQ-052); traversal code must use
    visited sets.
    """

    modules = list(modules)
    symbols = SymbolTable(modules)
    graph: nx.DiGraph = nx.DiGraph()

    for module in modules:
        for func in module.functions:
            graph.add_node(func.ref)

    graph.add_node(EXTERNAL)

    for module in modules:
        for func in module.functions:
            for call_name in func.call_sites:
                target = symbols.resolve(func, call_name, module)
                if target is None:
                    graph.add_edge(
                        func.ref,
                        EXTERNAL,
                        call_lineno=func.ref.lineno,
                        external=True,
                        name=call_name,
                    )
                else:
                    graph.add_edge(
                        func.ref,
                        target,
                        call_lineno=func.ref.lineno,
                        external=False,
                        name=call_name,
                    )

    return CallGraph(graph=graph, symbols=symbols)


__all__ = ["EXTERNAL", "CallGraph", "build_call_graph"]
