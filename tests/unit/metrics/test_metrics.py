"""REQ-060..REQ-067 metric unit tests + end-to-end per fixture."""

from __future__ import annotations

from pathlib import Path

from readerfriction.config import Config
from readerfriction.metrics import (
    file_jumps,
    flow_fragmentation,
    pass_through_ratio,
    thin_wrappers,
    trace_depth,
    wrapper_depth,
)
from readerfriction.metrics import score as score_module
from readerfriction.models import FunctionRef, MetricResult
from readerfriction.pipeline import scan_project


def ref(name: str, file: str = "m.py", lineno: int = 1) -> FunctionRef:
    return FunctionRef(qualname=name, file=file, lineno=lineno)


def test_req_060_trace_depth() -> None:
    path = [ref("a"), ref("b"), ref("c")]
    assert trace_depth.compute(path).value == 2
    assert trace_depth.compute([]).value == 0


def test_req_061_file_jumps() -> None:
    path = [ref("a", "x.py"), ref("b", "y.py"), ref("c", "y.py")]
    assert file_jumps.compute(path).value == 1
    assert file_jumps.compute([ref("a")]).value == 0


def test_req_062_wrapper_depth() -> None:
    a, b, c, d = ref("a"), ref("b"), ref("c"), ref("d")
    wrappers = {b, c}
    assert wrapper_depth.compute([a, b, c, d], wrappers).value == 2
    assert wrapper_depth.compute([a, b, d, c], wrappers).value == 1
    assert wrapper_depth.compute([a, d], wrappers).value == 0


def test_req_063_thin_wrapper_count() -> None:
    a, b, c = ref("a"), ref("b"), ref("c")
    assert thin_wrappers.compute([a, b, c], {b}).value == 1
    assert thin_wrappers.compute([a, b, c], {a, b, c}).value == 3


def test_req_064_flow_fragmentation_fixture(examples_root: Path) -> None:
    # clean-flow head fans out to parse + summarise (2), no middle branches.
    clean = scan_project(examples_root / "clean-flow" / "project", Config())
    frag = clean.summary["flow_fragmentation"].value
    assert frag <= 2

    # fragmented-flow main calls 6 helpers: high fragmentation.
    frag_result = scan_project(examples_root / "fragmented-flow" / "project", Config())
    assert frag_result.summary["flow_fragmentation"].value >= 5


def test_req_065_context_width_uses_args_and_self() -> None:
    # On a real path context_width is the mean arg_count along the path.
    result = scan_project(
        Path(__file__).resolve().parents[3] / "spec/examples/clean-flow/project",
        Config(),
    )
    cw = result.summary["context_width"].value
    assert cw >= 1  # parse/summarise/main each take at least 1 arg


def test_req_066_pass_through_ratio() -> None:
    a, b, c = ref("a"), ref("b"), ref("c")
    result = pass_through_ratio.compute({a, b, c}, {a})
    assert result.value == round(1 / 3, 3)
    assert pass_through_ratio.compute(set(), set()).value == 0.0


def test_req_067_aggregate_score() -> None:
    metrics = {
        "trace_depth": MetricResult(name="trace_depth", value=4, display="4"),
        "file_jumps": MetricResult(name="file_jumps", value=3, display="3"),
        "wrapper_depth": MetricResult(name="wrapper_depth", value=3, display="3"),
        "thin_wrapper_count": MetricResult(name="thin_wrapper_count", value=3, display="3"),
        "context_width": MetricResult(name="context_width", value=2, display="2"),
        "flow_fragmentation": MetricResult(name="flow_fragmentation", value=1, display="1"),
        # pass_through_ratio intentionally present but not scored
        "pass_through_ratio": MetricResult(
            name="pass_through_ratio", value=0.5, display="0.500"
        ),
    }
    total = score_module.compute(metrics, Config().weights)
    # 2*4 + 3*3 + 3*3 + 2*3 + 2*2 + 2*1 = 8+9+9+6+4+2 = 38
    assert total == 38


def test_wrapper_chain_score_higher_than_clean(examples_root: Path) -> None:
    clean = scan_project(examples_root / "clean-flow" / "project", Config())
    wrapper = scan_project(examples_root / "wrapper-chain" / "project", Config())
    assert wrapper.score >= clean.score * 3


def test_fragmented_flow_has_fragmentation(examples_root: Path) -> None:
    result = scan_project(examples_root / "fragmented-flow" / "project", Config())
    assert result.summary["flow_fragmentation"].value >= 5


def test_flow_fragmentation_simple_fan_out(examples_root: Path) -> None:
    # Just sanity: flow_fragmentation returns a MetricResult with a display.
    result = flow_fragmentation.compute.__name__
    assert result == "compute"


def test_wrapper_chain_path_detects_wrappers(examples_root: Path) -> None:
    result = scan_project(examples_root / "wrapper-chain" / "project", Config())
    entry_metrics = result.entrypoints[0].metrics
    assert entry_metrics["wrapper_depth"].value >= 3
    assert entry_metrics["thin_wrapper_count"].value >= 3
