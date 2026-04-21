"""Parse a Python file into a ``ModuleIR``."""

from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path

from readerfriction.models import FunctionIR, FunctionRef, ModuleIR, ParseError
from readerfriction.utils.paths import module_name_for


@dataclass(frozen=True)
class ParsedModule:
    """Carrier bundling the IR with the original AST, used by later stages."""

    ir: ModuleIR
    tree: ast.Module
    function_nodes: dict[str, ast.FunctionDef | ast.AsyncFunctionDef]


def parse_file(path: Path, root: Path) -> ParsedModule:
    """Parse ``path`` and return both the IR and retained AST nodes.

    On SyntaxError, return an empty IR with ``parse_errors`` populated
    (REQ-031); callers MUST NOT abort the scan in that case.
    """

    path = path.resolve()
    module_name = module_name_for(path, root)
    try:
        source = path.read_text()
        tree = ast.parse(source, filename=str(path))
    except SyntaxError as exc:
        return ParsedModule(
            ir=ModuleIR(
                path=str(path),
                module=module_name,
                parse_errors=[
                    ParseError(
                        file=str(path),
                        line=exc.lineno or 0,
                        message=exc.msg,
                    )
                ],
            ),
            tree=ast.Module(body=[], type_ignores=[]),
            function_nodes={},
        )

    functions, function_nodes = _extract_functions(tree, module_name, path)
    has_main_guard, main_calls = _inspect_main_guard(tree)
    imports = _collect_imports(tree)

    ir = ModuleIR(
        path=str(path),
        module=module_name,
        functions=functions,
        has_main_guard=has_main_guard,
        main_guard_calls=main_calls,
        imports=imports,
    )
    return ParsedModule(ir=ir, tree=tree, function_nodes=function_nodes)


def _extract_functions(
    tree: ast.Module,
    module_name: str,
    path: Path,
) -> tuple[list[FunctionIR], dict[str, ast.FunctionDef | ast.AsyncFunctionDef]]:
    functions: list[FunctionIR] = []
    nodes: dict[str, ast.FunctionDef | ast.AsyncFunctionDef] = {}

    def walk(node: ast.AST, prefix: list[str], is_method: bool) -> None:
        for child in ast.iter_child_nodes(node):
            if isinstance(child, ast.ClassDef):
                walk(child, [*prefix, child.name], True)
            elif isinstance(child, ast.FunctionDef | ast.AsyncFunctionDef):
                qualname = ".".join([module_name, *prefix, child.name])
                ref = FunctionRef(qualname=qualname, file=str(path), lineno=child.lineno)
                arg_count = _count_arguments(child, is_method=is_method)
                decorators = [_decorator_repr(d) for d in child.decorator_list]
                call_sites = sorted({_call_name(c) for c in _iter_calls(child)} - {""})
                ir = FunctionIR(
                    ref=ref,
                    name=child.name,
                    module=module_name,
                    arg_count=arg_count,
                    is_async=isinstance(child, ast.AsyncFunctionDef),
                    is_method=is_method,
                    decorator_names=decorators,
                    call_sites=call_sites,
                )
                functions.append(ir)
                nodes[qualname] = child
                walk(child, [*prefix, child.name], False)

    walk(tree, [], False)
    return functions, nodes


def _count_arguments(
    node: ast.FunctionDef | ast.AsyncFunctionDef, *, is_method: bool
) -> int:
    args = node.args
    total = (
        len(args.posonlyargs)
        + len(args.args)
        + len(args.kwonlyargs)
    )
    if args.vararg is not None:
        total += 1
    if args.kwarg is not None:
        total += 1
    if is_method and args.args and args.args[0].arg in {"self", "cls"}:
        total -= 1
    return total


def _decorator_repr(node: ast.expr) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return f"{_decorator_repr(node.value)}.{node.attr}"
    if isinstance(node, ast.Call):
        return _decorator_repr(node.func)
    return ast.unparse(node)


def _iter_calls(node: ast.AST):
    for child in ast.walk(node):
        if isinstance(child, ast.Call):
            yield child


def _call_name(node: ast.Call) -> str:
    func = node.func
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        parts: list[str] = [func.attr]
        current: ast.AST = func.value
        while isinstance(current, ast.Attribute):
            parts.append(current.attr)
            current = current.value
        if isinstance(current, ast.Name):
            parts.append(current.id)
        return ".".join(reversed(parts))
    return ""


def _inspect_main_guard(tree: ast.Module) -> tuple[bool, list[str]]:
    for node in tree.body:
        if not isinstance(node, ast.If):
            continue
        if _is_main_guard(node.test):
            calls = sorted({_call_name(c) for c in _iter_calls(node)} - {""})
            return True, calls
    return False, []


def _is_main_guard(test: ast.expr) -> bool:
    if not isinstance(test, ast.Compare):
        return False
    if len(test.ops) != 1 or not isinstance(test.ops[0], ast.Eq):
        return False
    left, right = test.left, test.comparators[0]
    names = {_expr_repr(left), _expr_repr(right)}
    return "__name__" in names and "'__main__'" in names


def _expr_repr(node: ast.expr) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Constant):
        return repr(node.value)
    return ast.unparse(node)


def _collect_imports(tree: ast.Module) -> dict[str, str]:
    imports: dict[str, str] = {}
    for node in tree.body:
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports[alias.asname or alias.name.split(".")[0]] = alias.name
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            for alias in node.names:
                imports[alias.asname or alias.name] = (
                    f"{module}.{alias.name}" if module else alias.name
                )
    return imports


__all__ = ["ParsedModule", "parse_file"]
