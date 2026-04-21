"""Symbol resolution across imports, same-module, and self methods."""

from __future__ import annotations

from pathlib import Path

from readerfriction.graph.resolve import SymbolTable
from readerfriction.parser.ast_parse import parse_file


def _parse_all(root: Path, sources: dict[str, str]):
    irs = []
    for name, source in sources.items():
        p = root / f"{name}.py"
        p.write_text(source)
        irs.append(parse_file(p, root).ir)
    return irs


def test_same_module_call(tmp_path: Path) -> None:
    irs = _parse_all(
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
    table = SymbolTable(irs)
    module = irs[0]
    foo = module.functions[0]
    bar_ref = module.functions[1].ref
    assert table.resolve(foo, "bar", module) == bar_ref


def test_from_import_resolves(tmp_path: Path) -> None:
    irs = _parse_all(
        tmp_path,
        {
            "a": """
from b import helper

def run():
    return helper()
""".lstrip(),
            "b": """
def helper():
    return 1
""".lstrip(),
        },
    )
    table = SymbolTable(irs)
    run = irs[0].functions[0]
    helper_ref = irs[1].functions[0].ref
    assert table.resolve(run, "helper", irs[0]) == helper_ref


def test_module_import_alias(tmp_path: Path) -> None:
    irs = _parse_all(
        tmp_path,
        {
            "a": """
import b as bb

def run():
    return bb.helper()
""".lstrip(),
            "b": """
def helper():
    return 1
""".lstrip(),
        },
    )
    table = SymbolTable(irs)
    run = irs[0].functions[0]
    helper_ref = irs[1].functions[0].ref
    assert table.resolve(run, "bb.helper", irs[0]) == helper_ref


def test_external_call_returns_none(tmp_path: Path) -> None:
    irs = _parse_all(
        tmp_path,
        {
            "a": """
import os

def run():
    return os.getcwd()
""".lstrip(),
        },
    )
    table = SymbolTable(irs)
    run = irs[0].functions[0]
    assert table.resolve(run, "os.getcwd", irs[0]) is None


def test_self_method_resolves(tmp_path: Path) -> None:
    irs = _parse_all(
        tmp_path,
        {
            "a": """
class C:
    def outer(self):
        return self.inner()
    def inner(self):
        return 1
""".lstrip(),
        },
    )
    table = SymbolTable(irs)
    outer = next(f for f in irs[0].functions if f.name == "outer")
    inner_ref = next(f.ref for f in irs[0].functions if f.name == "inner")
    assert table.resolve(outer, "self.inner", irs[0]) == inner_ref
