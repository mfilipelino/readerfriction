"""REQ-030..REQ-032 AST parsing."""

from __future__ import annotations

from pathlib import Path

from readerfriction.parser.ast_parse import parse_file


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)


def test_req_030_module_ir(tmp_path: Path) -> None:
    src = tmp_path / "pkg" / "mod.py"
    _write(
        src,
        """
def foo(x):
    return x

async def bar():
    return 1

class C:
    def baz(self, y):
        return self.method(y)
    @staticmethod
    def st():
        pass
""".lstrip(),
    )
    result = parse_file(src, tmp_path)
    names = [f.name for f in result.ir.functions]
    assert names == ["foo", "bar", "baz", "st"]


def test_req_032_function_ir_fields(tmp_path: Path) -> None:
    src = tmp_path / "m.py"
    _write(
        src,
        """
def foo(a, b, *args, c=1, **kwargs):
    bar(a)
    return c
""".lstrip(),
    )
    result = parse_file(src, tmp_path)
    func = result.ir.functions[0]
    assert func.name == "foo"
    assert func.module == "m"
    assert func.ref.file == str(src)
    assert func.ref.lineno == 1
    assert func.arg_count == 5  # a, b, *args, c, **kwargs
    assert func.is_async is False
    assert func.is_method is False
    assert "bar" in func.call_sites


def test_method_arg_count_excludes_self(tmp_path: Path) -> None:
    src = tmp_path / "m.py"
    _write(
        src,
        """
class C:
    def method(self, a, b):
        return a + b
""".lstrip(),
    )
    ir = parse_file(src, tmp_path).ir
    method = ir.functions[0]
    assert method.is_method is True
    assert method.arg_count == 2


def test_req_031_syntax_error_recorded(tmp_path: Path) -> None:
    src = tmp_path / "broken.py"
    _write(src, "def foo(:\n")
    result = parse_file(src, tmp_path)
    assert result.ir.functions == []
    assert len(result.ir.parse_errors) == 1
    assert result.ir.parse_errors[0].file == str(src.resolve())


def test_main_guard_detected(tmp_path: Path) -> None:
    src = tmp_path / "cli.py"
    _write(
        src,
        """
def main():
    return 1

if __name__ == "__main__":
    main()
""".lstrip(),
    )
    ir = parse_file(src, tmp_path).ir
    assert ir.has_main_guard is True
    assert "main" in ir.main_guard_calls


def test_imports_collected(tmp_path: Path) -> None:
    src = tmp_path / "m.py"
    _write(
        src,
        """
import os
import json as j
from pathlib import Path as P
from pkg import something
""".lstrip(),
    )
    ir = parse_file(src, tmp_path).ir
    assert ir.imports["os"] == "os"
    assert ir.imports["j"] == "json"
    assert ir.imports["P"] == "pathlib.Path"
    assert ir.imports["something"] == "pkg.something"


def test_decorator_names_collected(tmp_path: Path) -> None:
    src = tmp_path / "m.py"
    _write(
        src,
        """
import typer

app = typer.Typer()

@app.command()
def run():
    pass
""".lstrip(),
    )
    ir = parse_file(src, tmp_path).ir
    run = next(f for f in ir.functions if f.name == "run")
    assert "app.command" in run.decorator_names
