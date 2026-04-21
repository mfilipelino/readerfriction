"""Thin-wrapper classifier implementing the 8-rule heuristic (REQ-070/071).

The rules are codified in ``spec/wrapper-heuristic.md``. Each rule returns
True when it fires *in favour of* "thin wrapper".
"""

from __future__ import annotations

import ast

from readerfriction.models import FunctionRef, WrapperClassification

TRIVIAL_CALLEES: frozenset[str] = frozenset(
    {
        "len", "str", "int", "float", "bool", "list", "tuple",
        "dict", "set", "bytes", "frozenset", "print",
    }
)

ALLOWED_DECORATORS: frozenset[str] = frozenset(
    {
        "staticmethod",
        "classmethod",
        "property",
        "cached_property",
        "lru_cache",
        "cache",
        "wraps",
        "functools.lru_cache",
        "functools.cache",
        "functools.wraps",
        "functools.cached_property",
    }
)

VALIDATION_NAMES: frozenset[str] = frozenset(
    {"validate", "assert_valid", "check", "ensure", "require"}
)

ALL_RULES: tuple[str, ...] = (
    "W-01",
    "W-02",
    "W-03",
    "W-04",
    "W-05",
    "W-06",
    "W-07",
    "W-08",
)


DISQUALIFIERS: frozenset[str] = frozenset({"W-04", "W-05", "W-06", "W-07"})


def classify_function(
    ref: FunctionRef,
    node: ast.FunctionDef | ast.AsyncFunctionDef,
    *,
    threshold: int = 6,
) -> WrapperClassification:
    """Return the wrapper classification for ``node``.

    ``threshold`` is the minimum number of matched rules required. In
    addition, any rule in :data:`DISQUALIFIERS` that does **not** match forces
    ``is_wrapper`` to False regardless of the total score — these rules are
    "no loops / no branching / no transformation / no validation" and
    represent substantive logic the reader must grasp.
    """

    if _has_disqualifying_decorator(node):
        return WrapperClassification(
            ref=ref,
            is_wrapper=False,
            matched_rules=[],
            score=0,
            threshold=threshold,
        )

    body = _non_docstring_body(node)
    non_trivial_calls = [c for c in _collect_calls(body) if not _is_trivial(c)]
    matched: list[str] = []

    if _rule_01_short_body(body):
        matched.append("W-01")
    if _rule_02_single_call(non_trivial_calls):
        matched.append("W-02")
    if _rule_03_returns_the_call(body, non_trivial_calls):
        matched.append("W-03")
    if _rule_04_no_loops(node):
        matched.append("W-04")
    if _rule_05_no_meaningful_branching(node):
        matched.append("W-05")
    if _rule_06_no_transformation(body):
        matched.append("W-06")
    if _rule_07_no_validation(node):
        matched.append("W-07")
    if _rule_08_args_one_to_one(node, non_trivial_calls):
        matched.append("W-08")

    matched_set = set(matched)
    disqualified = bool(DISQUALIFIERS - matched_set)
    passes_threshold = len(matched) >= threshold
    return WrapperClassification(
        ref=ref,
        is_wrapper=passes_threshold and not disqualified,
        matched_rules=matched,
        score=len(matched),
        threshold=threshold,
    )


def _has_disqualifying_decorator(
    node: ast.FunctionDef | ast.AsyncFunctionDef,
) -> bool:
    for deco in node.decorator_list:
        name = _decorator_name(deco)
        if name in ALLOWED_DECORATORS:
            continue
        # Unknown decorator → assume the function is meaningful.
        return True
    return False


def _decorator_name(node: ast.expr) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return f"{_decorator_name(node.value)}.{node.attr}"
    if isinstance(node, ast.Call):
        return _decorator_name(node.func)
    return ast.unparse(node)


def _non_docstring_body(node: ast.FunctionDef | ast.AsyncFunctionDef) -> list[ast.stmt]:
    body = list(node.body)
    if (
        body
        and isinstance(body[0], ast.Expr)
        and isinstance(body[0].value, ast.Constant)
        and isinstance(body[0].value.value, str)
    ):
        body = body[1:]
    return [s for s in body if not isinstance(s, ast.Pass)]


def _collect_calls(body: list[ast.stmt]) -> list[ast.Call]:
    """Collect call expressions, skipping anything inside a guard clause."""

    calls: list[ast.Call] = []
    for stmt in body:
        if isinstance(stmt, ast.If) and _is_guard_clause(stmt):
            continue
        for child in ast.walk(stmt):
            if isinstance(child, ast.Call):
                calls.append(child)
    return calls


def _is_trivial(call: ast.Call) -> bool:
    return _call_simple_name(call) in TRIVIAL_CALLEES


def _call_simple_name(call: ast.Call) -> str:
    func = call.func
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        return func.attr
    return ""


def _rule_01_short_body(body: list[ast.stmt]) -> bool:
    return len(body) <= 3


def _rule_02_single_call(calls: list[ast.Call]) -> bool:
    return len(calls) == 1


def _rule_03_returns_the_call(
    body: list[ast.stmt],
    non_trivial_calls: list[ast.Call],
) -> bool:
    if not body or not non_trivial_calls:
        return False
    last = body[-1]
    tracked = non_trivial_calls[0]

    if isinstance(last, ast.Return):
        value = last.value
        if isinstance(value, ast.Await):
            value = value.value
        return isinstance(value, ast.Call) and value is tracked

    if isinstance(last, ast.Expr):
        value = last.value
        if isinstance(value, ast.Await):
            value = value.value
        return isinstance(value, ast.Call) and value is tracked

    return False


def _rule_04_no_loops(node: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    for child in ast.walk(node):
        if isinstance(child, ast.For | ast.While | ast.AsyncFor):
            return False
        if (
            isinstance(child, ast.ListComp | ast.DictComp | ast.SetComp | ast.GeneratorExp)
            and len(child.generators) > 1
        ):
            return False
    return True


def _rule_05_no_meaningful_branching(node: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    for child in ast.walk(node):
        if isinstance(child, ast.Match):
            return False
        if isinstance(child, ast.If) and not _is_guard_clause(child):
            return False
    return True


def _is_guard_clause(node: ast.If) -> bool:
    if node.orelse:
        return False
    return all(isinstance(s, ast.Raise) for s in node.body)


def _rule_06_no_transformation(body: list[ast.stmt]) -> bool:
    """Scan non-guard statements for transformation expressions.

    Guard-clause ``If`` blocks (``if cond: raise ...`` with no ``else``) are
    allowed under W-05 and their internal comparisons must not fail W-06.
    """

    for stmt in body:
        if isinstance(stmt, ast.If) and _is_guard_clause(stmt):
            continue
        for child in ast.walk(stmt):
            if isinstance(child, ast.BinOp | ast.BoolOp | ast.Compare | ast.UnaryOp):
                return False
            if isinstance(child, ast.JoinedStr | ast.ListComp | ast.DictComp | ast.SetComp):
                return False
            if isinstance(child, ast.GeneratorExp | ast.Lambda):
                return False
    # Nested non-trivial calls in argument positions also count as transformation.
    for stmt in body:
        if isinstance(stmt, ast.If) and _is_guard_clause(stmt):
            continue
        for child in ast.walk(stmt):
            if not isinstance(child, ast.Call):
                continue
            for arg in list(child.args) + [kw.value for kw in child.keywords]:
                if isinstance(arg, ast.Call) and not _is_trivial(arg):
                    return False
    return True


def _rule_07_no_validation(node: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    for child in ast.walk(node):
        if isinstance(child, ast.Assert):
            return False
        if isinstance(child, ast.Call):
            name = _call_simple_name(child)
            if name in VALIDATION_NAMES:
                return False
            if any(name.endswith(v) and name != v for v in VALIDATION_NAMES):
                return False
    return True


def _rule_08_args_one_to_one(
    node: ast.FunctionDef | ast.AsyncFunctionDef,
    non_trivial_calls: list[ast.Call],
) -> bool:
    if not non_trivial_calls:
        return False
    call = non_trivial_calls[0]

    params: set[str] = set()
    for a in node.args.posonlyargs + node.args.args + node.args.kwonlyargs:
        params.add(a.arg)
    if node.args.vararg is not None:
        params.add(node.args.vararg.arg)
    if node.args.kwarg is not None:
        params.add(node.args.kwarg.arg)
    params |= {"self", "cls"}

    arg_names: list[str] = []
    for arg in call.args:
        if isinstance(arg, ast.Name):
            arg_names.append(arg.id)
        elif isinstance(arg, ast.Starred) and isinstance(arg.value, ast.Name):
            arg_names.append(arg.value.id)
        else:
            return False
    for kw in call.keywords:
        if isinstance(kw.value, ast.Name):
            arg_names.append(kw.value.id)
        else:
            return False

    if not arg_names:
        return False
    return set(arg_names) <= params


__all__ = [
    "ALLOWED_DECORATORS",
    "ALL_RULES",
    "TRIVIAL_CALLEES",
    "VALIDATION_NAMES",
    "classify_function",
]
