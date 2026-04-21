"""REQ-070 / REQ-071 thin-wrapper classifier."""

from __future__ import annotations

import ast
import textwrap
from pathlib import Path

import pytest

from readerfriction.classify.wrappers import classify_function
from readerfriction.models import FunctionRef
from readerfriction.parser.ast_parse import parse_file


def _classify(source: str, *, threshold: int = 6):
    tree = ast.parse(textwrap.dedent(source))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef | ast.AsyncFunctionDef))
    ref = FunctionRef(qualname="m." + func.name, file="m.py", lineno=func.lineno)
    return classify_function(ref, func, threshold=threshold)


@pytest.mark.parametrize(
    "case_name,source,expected_wrapper",
    [
        (
            "obvious_passthrough",
            """
            def handle(x):
                return run(x)
            """,
            True,
        ),
        (
            "double_passthrough_with_kwargs",
            """
            def fetch(user, *, level):
                return repo.get(user, level=level)
            """,
            True,
        ),
        (
            "one_liner_two_non_trivial_calls",
            """
            def mix(x):
                return outer(inner(x))
            """,
            False,
        ),
        (
            "arithmetic_helper",
            """
            def add(a, b):
                return a + b
            """,
            False,
        ),
        (
            "formatted_transform",
            """
            def shout(msg):
                return yell(f"hi {msg}")
            """,
            False,
        ),
        (
            "validator_raises",
            """
            def store(x):
                validate(x)
                return db.save(x)
            """,
            False,
        ),
        (
            "assert_validation",
            """
            def store(x):
                assert x is not None
                return db.save(x)
            """,
            False,
        ),
        (
            "guard_clause_ok",
            """
            def get(user):
                if user is None:
                    raise ValueError()
                return repo.fetch(user)
            """,
            True,
        ),
        (
            "meaningful_branching",
            """
            def decide(flag):
                if flag:
                    return foo()
                return bar()
            """,
            False,
        ),
        (
            "loop_disqualifies",
            """
            def each(items):
                for it in items:
                    do(it)
            """,
            False,
        ),
        (
            "async_await_wrapper",
            """
            async def fetch(user):
                return await repo.get(user)
            """,
            True,
        ),
        (
            "renamed_single_arg_passthrough",
            """
            def handle(user):
                return run(user)
            """,
            True,
        ),
        (
            "staticmethod_wrapper_allowed",
            """
            @staticmethod
            def run(x):
                return svc.do(x)
            """,
            True,
        ),
        (
            "custom_decorator_disqualifies",
            """
            @trace
            def run(x):
                return svc.do(x)
            """,
            False,
        ),
        (
            "empty_body_pass",
            """
            def nothing():
                pass
            """,
            False,
        ),
        (
            "expr_call_no_return",
            """
            def log(msg):
                logger.info(msg)
            """,
            True,
        ),
        (
            "list_comp_transform",
            """
            def names(users):
                return fmt([u.name for u in users])
            """,
            False,
        ),
        (
            "dict_comp_transform",
            """
            def by_id(users):
                return save({u.id: u for u in users})
            """,
            False,
        ),
    ],
)
def test_req_070_table(case_name: str, source: str, expected_wrapper: bool) -> None:
    result = _classify(source)
    assert result.is_wrapper is expected_wrapper, (case_name, result)


def test_req_071_rules_recorded() -> None:
    result = _classify(
        """
        def handle(x):
            return run(x)
        """
    )
    assert result.matched_rules  # at least some fired
    assert set(result.matched_rules) <= {
        "W-01", "W-02", "W-03", "W-04", "W-05", "W-06", "W-07", "W-08"
    }
    assert result.score == len(result.matched_rules)
    assert result.threshold == 6


def test_threshold_is_configurable() -> None:
    # A clear wrapper matches all 8 rules, so threshold lowering doesn't flip it.
    # But threshold raising can: threshold 9 means no function can qualify.
    source = """
    def handle(x):
        return run(x)
    """
    default = _classify(source)
    strict = _classify(source, threshold=9)
    assert default.is_wrapper is True
    assert strict.is_wrapper is False


def test_disqualifier_blocks_wrapper_classification() -> None:
    # Arithmetic helper matches many signal rules but W-06 (transformation)
    # fails, so it can never be classified as a wrapper even at threshold 0.
    source = """
    def add(a, b):
        return a + b
    """
    for threshold in (0, 3, 6):
        assert _classify(source, threshold=threshold).is_wrapper is False


def test_clean_flow_fixture_zero_false_positives(examples_root: Path) -> None:
    root = examples_root / "clean-flow" / "project"
    src = root / "app.py"
    parsed = parse_file(src, root)
    wrappers: list[str] = []
    for func in parsed.ir.functions:
        node = parsed.function_nodes[func.ref.qualname]
        result = classify_function(func.ref, node)
        if result.is_wrapper:
            wrappers.append(func.name)
    assert wrappers == [], f"clean-flow should have zero wrappers, got {wrappers}"


def test_wrapper_chain_fixture_detects_wrappers(examples_root: Path) -> None:
    root = examples_root / "wrapper-chain" / "project"
    found: list[str] = []
    for path in sorted(root.rglob("*.py")):
        parsed = parse_file(path, root)
        for func in parsed.ir.functions:
            node = parsed.function_nodes[func.ref.qualname]
            result = classify_function(func.ref, node)
            if result.is_wrapper:
                found.append(func.name)
    assert {"handle", "run", "fetch"} <= set(found)
    assert "query" not in found  # db.query has loops/transformation/branching
