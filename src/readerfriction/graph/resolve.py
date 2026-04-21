"""Resolve call-site names to ``FunctionRef``s across modules."""

from __future__ import annotations

from collections.abc import Iterable

from readerfriction.models import FunctionIR, FunctionRef, ModuleIR


class SymbolTable:
    """Module-level symbol lookup.

    Resolves a name reference at a call site inside function ``caller`` in
    ``module`` to a concrete ``FunctionRef`` when possible; otherwise returns
    ``None``, meaning the caller should route the edge to ``<external>``.
    """

    def __init__(self, modules: Iterable[ModuleIR]) -> None:
        self._modules: list[ModuleIR] = list(modules)
        # module name -> function name -> FunctionRef  (top-level functions only)
        self._by_module: dict[str, dict[str, FunctionRef]] = {}
        # qualname -> FunctionRef (method lookup "ClassName.method")
        self._by_qualname: dict[str, FunctionRef] = {}
        self._index()

    def _index(self) -> None:
        for module in self._modules:
            funcs: dict[str, FunctionRef] = {}
            for func in module.functions:
                self._by_qualname[func.ref.qualname] = func.ref
                qualname_tail = func.ref.qualname.removeprefix(module.module + ".")
                if "." in qualname_tail:
                    continue  # skip nested / methods for module-top table
                funcs[func.name] = func.ref
            self._by_module[module.module] = funcs

    def module_functions(self, module: str) -> dict[str, FunctionRef]:
        return self._by_module.get(module, {})

    def resolve(
        self,
        caller: FunctionIR,
        call_name: str,
        module: ModuleIR,
    ) -> FunctionRef | None:
        """Return the target ``FunctionRef`` for ``call_name`` or None if external.

        Resolution rules (tried in order):
          1. Dotted call ``self.xyz`` → look up method on the enclosing class.
          2. Dotted call ``module_alias.func`` → use ``module.imports``.
          3. Bare name ``func`` → current module's top-level functions.
          4. Bare name ``func`` → imported name (``from x import func``).
        """

        if not call_name:
            return None

        parts = call_name.split(".")
        if len(parts) >= 2 and parts[0] == "self":
            return self._resolve_self_method(caller, parts[1])

        if len(parts) >= 2:
            head = parts[0]
            import_target = module.imports.get(head)
            if import_target is not None:
                candidate = f"{import_target}.{'.'.join(parts[1:])}"
                if candidate in self._by_qualname:
                    return self._by_qualname[candidate]
                # If head imports a whole module, tail(last) is the function name
                if len(parts) == 2:
                    ref = self._by_module.get(import_target, {}).get(parts[1])
                    if ref is not None:
                        return ref
            return None

        name = parts[0]
        ref = self._by_module.get(module.module, {}).get(name)
        if ref is not None:
            return ref

        import_target = module.imports.get(name)
        if import_target is None:
            return None

        # "from pkg.mod import func" → target module "pkg.mod", fn "func"
        if "." in import_target:
            module_part, _, func_part = import_target.rpartition(".")
            ref = self._by_module.get(module_part, {}).get(func_part)
            if ref is not None:
                return ref
        return None

    def _resolve_self_method(self, caller: FunctionIR, method_name: str) -> FunctionRef | None:
        # Caller qualname: "<module>.<Class>.<method>". Look up sibling method.
        parts = caller.ref.qualname.split(".")
        if len(parts) < 3:
            return None
        class_qualname = ".".join(parts[:-1])
        candidate = f"{class_qualname}.{method_name}"
        return self._by_qualname.get(candidate)


__all__ = ["SymbolTable"]
