"""Detect entrypoint functions per REQ-040 / REQ-041."""

from __future__ import annotations

from collections.abc import Iterable

from readerfriction.models import FunctionIR, FunctionRef, ModuleIR

ENTRYPOINT_DECORATOR_SUFFIXES: frozenset[str] = frozenset(
    {
        "command",
        "callback",
        "group",
    }
)


def detect_entrypoints(modules: Iterable[ModuleIR]) -> list[FunctionRef]:
    """Return the set of detected entrypoints across all parsed modules.

    REQ-040 rules (any matches):
      (a) function named ``main``
      (b) function referenced inside ``if __name__ == "__main__":``
      (c) function decorated with ``@app.command``, ``@app.callback``,
          ``@click.command``, ``@click.group``, or any decorator whose final
          attribute is ``command``.
    """

    modules = list(modules)
    explicit: list[FunctionRef] = []
    for module in modules:
        guard_calls = set(module.main_guard_calls)
        for func in module.functions:
            if _is_entrypoint(func, guard_calls):
                explicit.append(func.ref)

    if explicit:
        return _dedupe(explicit)

    return _fallback_public_top_level(modules)


def _is_entrypoint(func: FunctionIR, guard_calls: set[str]) -> bool:
    if func.name == "main":
        return True
    if func.name in guard_calls:
        return True
    for decorator in func.decorator_names:
        if decorator.split(".")[-1] in ENTRYPOINT_DECORATOR_SUFFIXES:
            return True
    return False


def _fallback_public_top_level(modules: list[ModuleIR]) -> list[FunctionRef]:
    """REQ-041 fallback: every public top-level function counts."""

    refs: list[FunctionRef] = []
    for module in modules:
        for func in module.functions:
            if func.is_method:
                continue
            if func.name.startswith("_"):
                continue
            # Only top-level (qualname: module.funcname has exactly one trailing segment)
            qualname_tail = func.ref.qualname.removeprefix(module.module + ".")
            if "." in qualname_tail:
                continue
            refs.append(func.ref)
    return _dedupe(refs)


def _dedupe(refs: list[FunctionRef]) -> list[FunctionRef]:
    seen: set[FunctionRef] = set()
    out: list[FunctionRef] = []
    for ref in refs:
        if ref in seen:
            continue
        seen.add(ref)
        out.append(ref)
    return sorted(out, key=lambda r: (r.file, r.lineno, r.qualname))


__all__ = ["ENTRYPOINT_DECORATOR_SUFFIXES", "detect_entrypoints"]
