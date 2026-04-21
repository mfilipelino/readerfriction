"""REQ-020..REQ-023 file discovery."""

from __future__ import annotations

from pathlib import Path

from readerfriction.config import DEFAULT_EXCLUDES
from readerfriction.parser.discover import discover_python_files


def _write(path: Path, content: str = "") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)


def test_req_020_recursive_discovery(tmp_path: Path) -> None:
    _write(tmp_path / "a.py")
    _write(tmp_path / "pkg" / "b.py")
    _write(tmp_path / "pkg" / "sub" / "c.py")
    _write(tmp_path / "README.md")

    result = discover_python_files(tmp_path, excludes=list(DEFAULT_EXCLUDES))
    assert [p.name for p in result] == ["a.py", "b.py", "c.py"]


def test_req_021_default_excludes(tmp_path: Path) -> None:
    for name in DEFAULT_EXCLUDES:
        _write(tmp_path / name / "skip.py")
    _write(tmp_path / "keep.py")

    result = discover_python_files(tmp_path, excludes=list(DEFAULT_EXCLUDES))
    assert [p.name for p in result] == ["keep.py"]


def test_req_022_exclude_flag(tmp_path: Path) -> None:
    _write(tmp_path / "src" / "ok.py")
    _write(tmp_path / "scripts" / "gen.py")
    result = discover_python_files(
        tmp_path, excludes=[*DEFAULT_EXCLUDES, "scripts/*"]
    )
    assert [p.name for p in result] == ["ok.py"]


def test_req_023_lexicographic_order(tmp_path: Path) -> None:
    for name in ["c.py", "a.py", "b.py"]:
        _write(tmp_path / name)
    result = discover_python_files(tmp_path, excludes=list(DEFAULT_EXCLUDES))
    assert [p.name for p in result] == ["a.py", "b.py", "c.py"]


def test_single_file_input(tmp_path: Path) -> None:
    file_path = tmp_path / "x.py"
    _write(file_path)
    result = discover_python_files(file_path, excludes=list(DEFAULT_EXCLUDES))
    assert result == [file_path.resolve()]


def test_non_python_single_file_ignored(tmp_path: Path) -> None:
    file_path = tmp_path / "x.md"
    _write(file_path)
    result = discover_python_files(file_path, excludes=list(DEFAULT_EXCLUDES))
    assert result == []
