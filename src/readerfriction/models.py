"""Pydantic models that form the contract between layers and CLI outputs."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

SCHEMA_VERSION = "0.1"

Severity = Literal["ok", "warn", "error"]


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class FunctionRef(_Strict):
    """Stable pointer to a function — the same function always hashes the same."""

    qualname: str
    file: str
    lineno: int

    def __hash__(self) -> int:  # so FunctionRef can be networkx graph key
        return hash((self.qualname, self.file, self.lineno))


class CallEdge(_Strict):
    caller: FunctionRef
    callee: FunctionRef
    call_lineno: int
    external: bool = False


class FunctionIR(_Strict):
    """Intermediate representation used by the classifier + graph builder."""

    ref: FunctionRef
    name: str
    module: str
    arg_count: int
    is_async: bool
    is_method: bool
    decorator_names: list[str] = Field(default_factory=list)
    call_sites: list[str] = Field(default_factory=list)  # raw callee names at AST level


class ParseError(_Strict):
    file: str
    line: int
    message: str


class ModuleIR(_Strict):
    path: str
    module: str
    functions: list[FunctionIR] = Field(default_factory=list)
    has_main_guard: bool = False
    main_guard_calls: list[str] = Field(default_factory=list)
    imports: dict[str, str] = Field(default_factory=dict)  # local name -> dotted target
    parse_errors: list[ParseError] = Field(default_factory=list)


class WrapperClassification(_Strict):
    ref: FunctionRef
    is_wrapper: bool
    matched_rules: list[str]
    score: int
    threshold: int


class MetricResult(_Strict):
    name: str
    value: float
    display: str  # pre-formatted for reports
    detail: dict[str, str] = Field(default_factory=dict)


class EntrypointResult(_Strict):
    ref: FunctionRef
    path: list[FunctionRef]  # chosen trace path
    metrics: dict[str, MetricResult]
    score: int


class ScanResult(_Strict):
    schema_version: Literal["0.1"] = SCHEMA_VERSION
    root: str
    scanned_files: int
    parse_errors: list[ParseError] = Field(default_factory=list)
    entrypoints: list[EntrypointResult]
    summary: dict[str, MetricResult]
    score: int
    severity: Severity


class TraceResult(_Strict):
    schema_version: Literal["0.1"] = SCHEMA_VERSION
    entry: FunctionRef
    path: list[FunctionRef]
    wrappers: list[FunctionRef] = Field(default_factory=list)
    metrics: dict[str, MetricResult]


class ExplainResult(_Strict):
    schema_version: Literal["0.1"] = SCHEMA_VERSION
    target: FunctionRef
    classification: WrapperClassification
    arg_count: int
    decorators: list[str]
    callers: list[FunctionRef] = Field(default_factory=list)
    callees: list[FunctionRef] = Field(default_factory=list)


class ReportDelta(_Strict):
    before: int
    after: int
    delta: int


class ReportResult(_Strict):
    schema_version: Literal["0.1"] = SCHEMA_VERSION
    base: ScanResult | None = None
    head: ScanResult
    delta: ReportDelta | None = None


__all__ = [
    "SCHEMA_VERSION",
    "CallEdge",
    "EntrypointResult",
    "ExplainResult",
    "FunctionIR",
    "FunctionRef",
    "MetricResult",
    "ModuleIR",
    "ParseError",
    "ReportDelta",
    "ReportResult",
    "ScanResult",
    "Severity",
    "TraceResult",
    "WrapperClassification",
]
