"""REQ-050..REQ-052 call-graph construction."""

from __future__ import annotations

from pathlib import Path

from readerfriction.graph.callgraph import EXTERNAL, build_call_graph
from readerfriction.parser.ast_parse import parse_file


def _parse(root: Path, sources: dict[str, str]):
    irs = []
    for name, source in sources.items():
        p = root / f"{name}.py"
        p.write_text(source)
        irs.append(parse_file(p, root).ir)
    return irs


def test_req_050_digraph_built(tmp_path: Path) -> None:
    irs = _parse(
        tmp_path,
        {
            "a": """
def foo():
    return bar()

def bar():
    return 1
""".lstrip(),
        },
    )
    cg = build_call_graph(irs)
    foo = next(f.ref for f in irs[0].functions if f.name == "foo")
    bar = next(f.ref for f in irs[0].functions if f.name == "bar")
    assert cg.successors(foo) == [bar]


def test_req_051_external_sentinel(tmp_path: Path) -> None:
    irs = _parse(
        tmp_path,
        {
            "a": """
import os

def run():
    os.getcwd()
""".lstrip(),
        },
    )
    cg = build_call_graph(irs)
    run = irs[0].functions[0].ref
    assert EXTERNAL in cg.successors(run)
    edge = next(e for e in cg.edges() if e.caller == run and e.callee == EXTERNAL)
    assert edge.external is True


def test_req_052_cycles_preserved(tmp_path: Path) -> None:
    irs = _parse(
        tmp_path,
        {
            "a": """
def foo():
    return bar()

def bar():
    return foo()
""".lstrip(),
        },
    )
    cg = build_call_graph(irs)
    foo = next(f.ref for f in irs[0].functions if f.name == "foo")
    bar = next(f.ref for f in irs[0].functions if f.name == "bar")
    assert bar in cg.successors(foo)
    assert foo in cg.successors(bar)


def test_wrapper_chain_fixture(examples_root: Path) -> None:
    root = examples_root / "wrapper-chain" / "project"
    irs = [parse_file(p, root).ir for p in sorted(root.rglob("*.py"))]
    cg = build_call_graph(irs)
    qualnames = {n.qualname for n in cg.nodes}
    assert {"cli.main", "handlers.handle", "services.run", "repos.fetch", "db.query"} <= qualnames

    main = next(n for n in cg.nodes if n.qualname == "cli.main")
    handle = next(n for n in cg.nodes if n.qualname == "handlers.handle")
    run = next(n for n in cg.nodes if n.qualname == "services.run")
    fetch = next(n for n in cg.nodes if n.qualname == "repos.fetch")
    query = next(n for n in cg.nodes if n.qualname == "db.query")

    assert handle in cg.successors(main)
    assert run in cg.successors(handle)
    assert fetch in cg.successors(run)
    assert query in cg.successors(fetch)
