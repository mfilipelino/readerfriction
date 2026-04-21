"""Acceptance criteria for v0.1 (from start.md)."""

from __future__ import annotations

import json
import tomllib
from pathlib import Path

from typer.testing import CliRunner

from readerfriction.cli import app

runner = CliRunner()


def test_ac_1_installs_via_uv(repo_root: Path) -> None:
    pyproject = tomllib.loads((repo_root / "pyproject.toml").read_text())
    assert pyproject["build-system"]["build-backend"] == "hatchling.build"
    assert pyproject["project"]["name"] == "readerfriction"


def test_ac_2_exposes_working_cli() -> None:
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    for cmd in ("scan", "trace", "explain", "report", "diff"):
        assert cmd in result.output


def test_ac_3_scans_python_project(examples_root: Path) -> None:
    result = runner.invoke(
        app, ["scan", str(examples_root / "wrapper-chain" / "project"), "--format", "json"]
    )
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["scanned_files"] > 0


def test_ac_4_detects_entrypoints(examples_root: Path) -> None:
    result = runner.invoke(
        app, ["scan", str(examples_root / "wrapper-chain" / "project"), "--format", "json"]
    )
    payload = json.loads(result.stdout)
    qualnames = [e["ref"]["qualname"] for e in payload["entrypoints"]]
    assert "cli.main" in qualnames


def test_ac_5_computes_all_metrics(examples_root: Path) -> None:
    result = runner.invoke(
        app, ["scan", str(examples_root / "wrapper-chain" / "project"), "--format", "json"]
    )
    payload = json.loads(result.stdout)
    for key in (
        "trace_depth",
        "file_jumps",
        "wrapper_depth",
        "thin_wrapper_count",
        "flow_fragmentation",
        "context_width",
        "pass_through_ratio",
    ):
        assert key in payload["summary"], key


def test_ac_6_emits_readable_reports(examples_root: Path, tmp_path: Path) -> None:
    for fmt in ("text", "markdown", "json"):
        target = tmp_path / f"rf.{fmt}"
        result = runner.invoke(
            app,
            [
                "scan",
                str(examples_root / "clean-flow" / "project"),
                "--format",
                fmt,
                "--out",
                str(target),
            ],
        )
        assert result.exit_code == 0, (fmt, result.output)
        assert target.exists()
        assert target.read_text().strip() != ""


def test_ac_7_flags_wrapper_heavy_flow(examples_root: Path) -> None:
    result = runner.invoke(
        app,
        ["scan", str(examples_root / "wrapper-chain" / "project"), "--format", "json"],
    )
    payload = json.loads(result.stdout)
    assert payload["severity"] == "error"
    assert payload["summary"]["wrapper_depth"]["value"] >= 3


def test_ac_8_does_not_flag_every_short_helper(examples_root: Path) -> None:
    result = runner.invoke(
        app,
        ["scan", str(examples_root / "clean-flow" / "project"), "--format", "json"],
    )
    payload = json.loads(result.stdout)
    assert payload["severity"] in {"ok", "warn"}
    assert payload["summary"]["wrapper_depth"]["value"] == 0


# --- REQ-900..REQ-903 (non-goals) --------------------------------------


def test_req_900_no_dynamic_dispatch(repo_root: Path) -> None:
    # We explicitly do not resolve dynamic dispatch. The code base must not
    # import runtime inference libraries.
    src = repo_root / "src"
    forbidden = ("pytype", "mypy_runtime", "runtime_introspection")
    for path in src.rglob("*.py"):
        text = path.read_text()
        for token in forbidden:
            assert token not in text, (path, token)


def test_req_901_no_runtime_tracing(repo_root: Path) -> None:
    src = repo_root / "src"
    for path in src.rglob("*.py"):
        text = path.read_text()
        assert "sys.settrace" not in text
        assert "sys.setprofile" not in text


def test_req_902_python_only(repo_root: Path) -> None:
    src = repo_root / "src"
    # Only .py files under src/readerfriction, nothing language-specific that
    # would suggest multi-language ambitions. Ignore cache artefacts.
    ignored_suffixes = {".py", ".pyc", ""}
    ignored_dirs = {"__pycache__"}
    ignored_names = {"py.typed"}  # PEP 561 typing marker — Python-only signal
    other: list[Path] = []
    for path in src.rglob("*"):
        if not path.is_file():
            continue
        if ignored_dirs & set(path.parts):
            continue
        if path.name in ignored_names:
            continue
        if path.suffix in ignored_suffixes:
            continue
        other.append(path)
    assert other == []


def test_req_903_no_framework_magic(repo_root: Path) -> None:
    # Entrypoint detection sticks to the decorator list spec'd in REQ-040.
    source = (repo_root / "src/readerfriction/parser/entrypoints.py").read_text()
    assert "ENTRYPOINT_DECORATOR_SUFFIXES" in source
    # No Flask-style route hooks etc.
    for bad in ("flask.route", "fastapi.get", "fastapi.post", "django"):
        assert bad not in source
