"""REQ-040 / REQ-041 entrypoint detection."""

from __future__ import annotations

from pathlib import Path

from readerfriction.parser.ast_parse import parse_file
from readerfriction.parser.entrypoints import detect_entrypoints


def _parse(path: Path, source: str, root: Path):
    path.write_text(source)
    return parse_file(path, root).ir


def test_req_040_detects_main_function(tmp_path: Path) -> None:
    ir = _parse(
        tmp_path / "a.py",
        """
def main():
    return 1
""".lstrip(),
        tmp_path,
    )
    entries = detect_entrypoints([ir])
    assert [e.qualname for e in entries] == ["a.main"]


def test_req_040_detects_name_main_call(tmp_path: Path) -> None:
    ir = _parse(
        tmp_path / "a.py",
        """
def run():
    return 1

if __name__ == "__main__":
    run()
""".lstrip(),
        tmp_path,
    )
    entries = detect_entrypoints([ir])
    assert [e.qualname for e in entries] == ["a.run"]


def test_req_040_detects_typer_command(tmp_path: Path) -> None:
    ir = _parse(
        tmp_path / "cli.py",
        """
import typer
app = typer.Typer()

@app.command()
def scan():
    pass

@app.callback()
def root():
    pass
""".lstrip(),
        tmp_path,
    )
    entries = detect_entrypoints([ir])
    names = {e.qualname for e in entries}
    assert names == {"cli.scan", "cli.root"}


def test_req_040_detects_click_command(tmp_path: Path) -> None:
    ir = _parse(
        tmp_path / "cli.py",
        """
import click

@click.command()
def main():
    pass

@click.group()
def cli():
    pass
""".lstrip(),
        tmp_path,
    )
    entries = detect_entrypoints([ir])
    names = {e.qualname for e in entries}
    assert names == {"cli.main", "cli.cli"}


def test_req_041_fallback_public_top_level(tmp_path: Path) -> None:
    ir = _parse(
        tmp_path / "lib.py",
        """
def helper():
    return 1

def _private():
    return 2

def also_public():
    return 3
""".lstrip(),
        tmp_path,
    )
    entries = detect_entrypoints([ir])
    names = {e.qualname for e in entries}
    assert names == {"lib.helper", "lib.also_public"}


def test_req_903_no_framework_magic_beyond_decorator_list(tmp_path: Path) -> None:
    ir = _parse(
        tmp_path / "a.py",
        """
def some_handler(request):
    return request
""".lstrip(),
        tmp_path,
    )
    # Falls back to public top-level; we intentionally do not recognise Flask's
    # implicit route bindings etc.
    entries = detect_entrypoints([ir])
    assert [e.qualname for e in entries] == ["a.some_handler"]


def test_examples_fixtures_detect_entrypoints(examples_root: Path) -> None:
    # Quick smoke across the three spec/examples projects.
    for example in ("wrapper-chain", "clean-flow", "fragmented-flow"):
        root = examples_root / example / "project"
        irs = []
        for py in sorted(root.rglob("*.py")):
            irs.append(parse_file(py, root).ir)
        entries = detect_entrypoints(irs)
        assert entries, f"no entrypoint in {example}"
