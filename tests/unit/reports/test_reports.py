"""REQ-012 / REQ-013 / REQ-090..094 report rendering."""

from __future__ import annotations

import json
import os
from pathlib import Path

import jsonschema
import pytest

from readerfriction.config import Config
from readerfriction.pipeline import scan_project
from readerfriction.reports import json_report, markdown, text

FIXTURES = ["wrapper-chain", "clean-flow", "fragmented-flow"]


@pytest.fixture(scope="module")
def scans(examples_root: Path) -> dict[str, object]:
    return {
        name: scan_project(examples_root / name / "project", Config())
        for name in FIXTURES
    }


@pytest.mark.parametrize("fixture", FIXTURES)
def test_req_012_json_validates(
    fixture: str,
    scans: dict[str, object],
    contracts_dir: Path,
) -> None:
    payload = json_report.render(scans[fixture])
    schema = json.loads((contracts_dir / "scan-result.schema.json").read_text())
    jsonschema.validate(json.loads(payload), schema)


def test_req_090_scan_schema_valid(
    scans: dict[str, object], contracts_dir: Path
) -> None:
    """Alias of REQ-012 for schema traceability."""
    payload = json_report.render(scans["wrapper-chain"])
    schema = json.loads((contracts_dir / "scan-result.schema.json").read_text())
    jsonschema.validate(json.loads(payload), schema)


def test_req_091_trace_schema_valid(contracts_dir: Path) -> None:
    from readerfriction.models import FunctionRef, MetricResult, TraceResult
    ref = FunctionRef(qualname="m.f", file="m.py", lineno=1)
    trace = TraceResult(
        entry=ref,
        path=[ref],
        metrics={"trace_depth": MetricResult(name="trace_depth", value=0, display="0")},
    )
    schema = json.loads((contracts_dir / "trace-result.schema.json").read_text())
    jsonschema.validate(json.loads(json_report.render(trace)), schema)


def test_req_092_explain_schema_valid(contracts_dir: Path) -> None:
    from readerfriction.models import (
        ExplainResult,
        FunctionRef,
        WrapperClassification,
    )
    ref = FunctionRef(qualname="m.f", file="m.py", lineno=1)
    explain = ExplainResult(
        target=ref,
        classification=WrapperClassification(
            ref=ref,
            is_wrapper=True,
            matched_rules=["W-01"],
            score=1,
            threshold=6,
        ),
        arg_count=1,
        decorators=[],
    )
    schema = json.loads((contracts_dir / "explain-result.schema.json").read_text())
    jsonschema.validate(json.loads(json_report.render(explain)), schema)


def test_req_093_report_schema_valid(
    scans: dict[str, object], contracts_dir: Path
) -> None:
    from readerfriction.models import ReportResult
    report_result = ReportResult(head=scans["wrapper-chain"])
    schema = json.loads((contracts_dir / "report-result.schema.json").read_text())
    jsonschema.validate(json.loads(json_report.render(report_result)), schema)


def test_req_013_markdown_deterministic(scans: dict[str, object]) -> None:
    for fixture in FIXTURES:
        first = markdown.render(scans[fixture])
        second = markdown.render(scans[fixture])
        assert first == second


@pytest.mark.parametrize("fixture", FIXTURES)
def test_markdown_golden(fixture: str, examples_root: Path, scans: dict[str, object]) -> None:
    golden = examples_root / fixture / "expected.md"
    rendered = markdown.render(scans[fixture])
    if os.environ.get("UPDATE_GOLDEN"):
        golden.write_text(rendered)
        return
    if not golden.exists():
        pytest.fail(
            f"missing golden {golden}; run with UPDATE_GOLDEN=1 to create it"
        )
    assert rendered == golden.read_text()


@pytest.mark.parametrize("fixture", FIXTURES)
def test_json_golden(fixture: str, examples_root: Path, scans: dict[str, object]) -> None:
    golden = examples_root / fixture / "expected.json"
    rendered = json_report.render(scans[fixture])
    # Normalise the absolute ``root`` field so golden files are stable across machines.
    payload = json.loads(rendered)
    payload["root"] = f"<{fixture}>"
    for entry in payload["entrypoints"]:
        entry["ref"]["file"] = _stable(entry["ref"]["file"])
        for node in entry["path"]:
            node["file"] = _stable(node["file"])
    for err in payload.get("parse_errors", []):
        err["file"] = _stable(err["file"])
    canonical = json.dumps(payload, indent=2, sort_keys=True) + "\n"

    if os.environ.get("UPDATE_GOLDEN"):
        golden.write_text(canonical)
        return
    if not golden.exists():
        pytest.fail(
            f"missing golden {golden}; run with UPDATE_GOLDEN=1 to create it"
        )
    assert canonical == golden.read_text()


def test_text_report_mentions_score(scans: dict[str, object]) -> None:
    output = text.render(scans["wrapper-chain"], color=False)
    assert "score" in output.lower()
    assert "ReaderFriction" in output


def _stable(path: str) -> str:
    """Turn absolute file paths into repo-relative ones for goldens."""

    if not path:
        return path
    try:
        p = Path(path).resolve()
    except OSError:
        return path
    # Keep only the last two components: project/file.py
    parts = p.parts[-2:]
    return str(Path(*parts))
