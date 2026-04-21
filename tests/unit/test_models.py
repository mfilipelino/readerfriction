"""REQ-094 schema parity + REQ-032 IR field coverage."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

from readerfriction.models import (
    CallEdge,
    EntrypointResult,
    ExplainResult,
    FunctionIR,
    FunctionRef,
    MetricResult,
    ModuleIR,
    ReportResult,
    ScanResult,
    TraceResult,
    WrapperClassification,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from gen_schemas import MODELS, build_schemas  # noqa: E402


@pytest.mark.parametrize("filename,model", list(MODELS.items()))
def test_req_094_schema_parity(filename: str, model: type, contracts_dir: Path) -> None:
    on_disk = json.loads((contracts_dir / filename).read_text())
    regenerated = model.model_json_schema()
    assert on_disk == regenerated, (
        f"Schema drift in {filename}. Run `uv run python scripts/gen_schemas.py`."
    )


def test_schemas_cover_all_outputs(contracts_dir: Path) -> None:
    expected = {
        "scan-result.schema.json",
        "trace-result.schema.json",
        "explain-result.schema.json",
        "report-result.schema.json",
    }
    actual = {p.name for p in contracts_dir.glob("*.schema.json")}
    assert actual == expected


def test_schemas_are_sorted_and_indented(contracts_dir: Path) -> None:
    for name, schema in build_schemas().items():
        expected = json.dumps(schema, indent=2, sort_keys=True) + "\n"
        assert (contracts_dir / name).read_text() == expected


def test_req_032_function_ir_fields() -> None:
    ref = FunctionRef(qualname="pkg.mod.foo", file="pkg/mod.py", lineno=10)
    ir = FunctionIR(
        ref=ref,
        name="foo",
        module="pkg.mod",
        arg_count=2,
        is_async=False,
        is_method=False,
        decorator_names=["staticmethod"],
        call_sites=["bar", "baz"],
    )
    assert ir.model_dump()["arg_count"] == 2
    assert ir.model_dump()["is_async"] is False
    # round-trip
    round_tripped = FunctionIR.model_validate_json(ir.model_dump_json())
    assert round_tripped == ir


def test_models_reject_unknown_fields() -> None:
    ref = FunctionRef(qualname="a.b", file="a.py", lineno=1)
    with pytest.raises(ValueError):
        ModuleIR.model_validate({"path": "a.py", "module": "a", "functions": [], "extra": 1})

    with pytest.raises(ValueError):
        CallEdge.model_validate(
            {
                "caller": ref.model_dump(),
                "callee": ref.model_dump(),
                "call_lineno": 2,
                "external": False,
                "oops": True,
            }
        )


def test_scan_result_round_trip() -> None:
    ref = FunctionRef(qualname="m.main", file="m.py", lineno=3)
    metric = MetricResult(name="trace_depth", value=2.0, display="2")
    entry = EntrypointResult(
        ref=ref,
        path=[ref],
        metrics={"trace_depth": metric},
        score=4,
    )
    scan = ScanResult(
        root="/tmp/x",
        scanned_files=1,
        entrypoints=[entry],
        summary={"trace_depth": metric},
        score=4,
        severity="ok",
    )
    blob = scan.model_dump_json()
    assert ScanResult.model_validate_json(blob) == scan


def test_trace_and_explain_models() -> None:
    ref = FunctionRef(qualname="m.f", file="m.py", lineno=1)
    metric = MetricResult(name="file_jumps", value=1, display="1")
    trace = TraceResult(entry=ref, path=[ref], metrics={"file_jumps": metric})
    assert TraceResult.model_validate_json(trace.model_dump_json()) == trace

    classification = WrapperClassification(
        ref=ref,
        is_wrapper=False,
        matched_rules=["W-01"],
        score=1,
        threshold=6,
    )
    explain = ExplainResult(
        target=ref,
        classification=classification,
        arg_count=1,
        decorators=[],
    )
    assert ExplainResult.model_validate_json(explain.model_dump_json()) == explain


def test_report_result_accepts_no_base() -> None:
    metric = MetricResult(name="score", value=0, display="0")
    head = ScanResult(
        root="/tmp/y",
        scanned_files=0,
        entrypoints=[],
        summary={"score": metric},
        score=0,
        severity="ok",
    )
    result = ReportResult(head=head)
    assert result.base is None
    assert result.delta is None
