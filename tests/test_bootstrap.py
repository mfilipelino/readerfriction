"""Phase 1 bootstrap tests. Covers REQ-001, REQ-002, REQ-003, REQ-010, REQ-011."""

from __future__ import annotations

import sys
import tomllib
from pathlib import Path

import pytest
from typer.testing import CliRunner

import readerfriction
from readerfriction.cli import app

runner = CliRunner()


def test_req_001_installable(repo_root: Path) -> None:
    pyproject = tomllib.loads((repo_root / "pyproject.toml").read_text())
    assert pyproject["project"]["name"] == "readerfriction"


def test_req_002_console_script(repo_root: Path) -> None:
    pyproject = tomllib.loads((repo_root / "pyproject.toml").read_text())
    scripts = pyproject["project"]["scripts"]
    assert scripts["rf"] == "readerfriction.cli:app"


def test_req_003_python_version(repo_root: Path) -> None:
    pyproject = tomllib.loads((repo_root / "pyproject.toml").read_text())
    assert pyproject["project"]["requires-python"] == ">=3.11"
    assert sys.version_info >= (3, 11)


def test_req_010_five_commands() -> None:
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0, result.output
    for command in ("scan", "trace", "explain", "report", "diff"):
        assert command in result.output


@pytest.mark.parametrize("command", ["scan", "trace", "explain", "report", "diff"])
def test_req_011_help_all_commands(command: str) -> None:
    result = runner.invoke(app, [command, "--help"])
    assert result.exit_code == 0, result.output


def test_package_version() -> None:
    assert readerfriction.__version__ == "0.1.0"


def test_cli_version_flag() -> None:
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0, result.output
    assert f"readerfriction {readerfriction.__version__}" in result.output
