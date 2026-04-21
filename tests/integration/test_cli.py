"""REQ-010..REQ-014, REQ-100..REQ-103 end-to-end CLI tests."""

from __future__ import annotations

import json
from pathlib import Path

import jsonschema
import pytest
from typer.testing import CliRunner

from readerfriction.cli import app

runner = CliRunner()


def _invoke(*args: str):
    return runner.invoke(app, list(args))


@pytest.fixture
def wrapper_chain_root(examples_root: Path) -> Path:
    return examples_root / "wrapper-chain" / "project"


@pytest.fixture
def clean_root(examples_root: Path) -> Path:
    return examples_root / "clean-flow" / "project"


@pytest.fixture
def fragmented_root(examples_root: Path) -> Path:
    return examples_root / "fragmented-flow" / "project"


def test_req_100_exit_zero(wrapper_chain_root: Path) -> None:
    result = _invoke("scan", str(wrapper_chain_root))
    assert result.exit_code == 0, result.output


def test_req_012_scan_json_validates(
    wrapper_chain_root: Path, contracts_dir: Path
) -> None:
    result = _invoke("scan", str(wrapper_chain_root), "--format", "json")
    assert result.exit_code == 0
    schema = json.loads((contracts_dir / "scan-result.schema.json").read_text())
    jsonschema.validate(json.loads(result.stdout), schema)


def test_req_013_markdown_deterministic(wrapper_chain_root: Path) -> None:
    first = _invoke("scan", str(wrapper_chain_root), "--format", "markdown")
    second = _invoke("scan", str(wrapper_chain_root), "--format", "markdown")
    assert first.exit_code == 0 == second.exit_code
    assert first.stdout == second.stdout


def test_req_014_out_flag(wrapper_chain_root: Path, tmp_path: Path) -> None:
    target = tmp_path / "rf.md"
    result = _invoke(
        "scan",
        str(wrapper_chain_root),
        "--format",
        "markdown",
        "--out",
        str(target),
    )
    assert result.exit_code == 0
    assert target.exists()
    assert target.read_text().startswith("# ReaderFriction")


def test_req_101_fail_on_triggers_exit_one(wrapper_chain_root: Path) -> None:
    result = _invoke(
        "scan",
        str(wrapper_chain_root),
        "--format",
        "json",
        "--fail-on",
        "score>10",
    )
    assert result.exit_code == 1, result.output


def test_fail_on_passes_when_threshold_not_breached(clean_root: Path) -> None:
    result = _invoke(
        "scan",
        str(clean_root),
        "--format",
        "json",
        "--fail-on",
        "score>100",
    )
    assert result.exit_code == 0, result.output


def test_req_102_invalid_target_exits_two() -> None:
    result = _invoke("trace", "bogus")
    assert result.exit_code == 2


def test_req_103_missing_path_exits_two(tmp_path: Path) -> None:
    result = _invoke("scan", str(tmp_path / "missing"))
    assert result.exit_code == 2


def test_trace_command(wrapper_chain_root: Path) -> None:
    cli_path = wrapper_chain_root / "cli.py"
    result = _invoke(
        "trace",
        f"{cli_path}:main",
        "--format",
        "json",
    )
    assert result.exit_code == 0, result.output
    payload = json.loads(result.stdout)
    assert payload["entry"]["qualname"] == "cli.main"
    qualnames = [n["qualname"] for n in payload["path"]]
    assert "db.query" in qualnames
    assert "handlers.handle" in qualnames


def test_explain_command(wrapper_chain_root: Path) -> None:
    handler = wrapper_chain_root / "handlers.py"
    result = _invoke(
        "explain",
        f"{handler}:handle",
        "--format",
        "json",
    )
    assert result.exit_code == 0, result.output
    payload = json.loads(result.stdout)
    assert payload["target"]["qualname"] == "handlers.handle"
    assert payload["classification"]["is_wrapper"] is True


def test_report_markdown_matches_golden(
    wrapper_chain_root: Path, examples_root: Path, tmp_path: Path
) -> None:
    target = tmp_path / "rf.md"
    result = _invoke(
        "report",
        str(wrapper_chain_root),
        "--format",
        "markdown",
        "--out",
        str(target),
    )
    assert result.exit_code == 0
    golden = (examples_root / "wrapper-chain" / "expected.md").read_text()
    assert target.read_text() == golden


def test_diff_command(
    wrapper_chain_root: Path, clean_root: Path
) -> None:
    result = _invoke(
        "diff",
        str(wrapper_chain_root),
        "--base",
        str(clean_root),
    )
    assert result.exit_code == 0, result.output
    assert "Delta" in result.stdout


def test_scan_clean_flow_low_score(clean_root: Path) -> None:
    result = _invoke("scan", str(clean_root), "--format", "json")
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["score"] < 20
    assert payload["severity"] in {"ok", "warn"}


def test_scan_wrapper_chain_high_score(wrapper_chain_root: Path) -> None:
    result = _invoke("scan", str(wrapper_chain_root), "--format", "json")
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["score"] >= 30
    assert payload["severity"] == "error"


def test_scan_fragmented_flow_detects_fragmentation(
    fragmented_root: Path,
) -> None:
    result = _invoke("scan", str(fragmented_root), "--format", "json")
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["summary"]["flow_fragmentation"]["value"] >= 5
