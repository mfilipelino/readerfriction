"""Render an agent-ready refactoring prompt from a ScanResult.

The prompt is designed to be piped verbatim into an AI coding agent
(Claude Code, Aider, Cursor, etc.) as a user or system message. It
front-loads what NOT to do because naively optimising the ReaderFriction
score is gameable — see ``docs/limits-and-anti-gaming.md``.
"""

from __future__ import annotations

from readerfriction.models import EntrypointResult, FunctionRef, ScanResult


def render(result: ScanResult, wrappers: set[FunctionRef]) -> str:
    """Return a markdown prompt describing the refactors the agent should apply."""

    sections: list[str] = []
    sections.append(_header(result))
    sections.append(_what_rf_measures())
    sections.append(_dont_list())
    sections.append(_do_list(result, wrappers))
    sections.append(_offenders_section(result, wrappers))
    sections.append(_verification_section())
    return "\n\n".join(sections).rstrip() + "\n"


# ---------------------------------------------------------------------------


def _header(result: ScanResult) -> str:
    return (
        "# Refactoring task: reduce navigational complexity\n\n"
        f"You are refactoring a Python codebase rooted at `{result.root}`. "
        f"A static analysis tool called ReaderFriction (`rf`) reports a "
        f"score of **{result.score}** with severity **{result.severity}** "
        f"across {result.scanned_files} file(s). Higher is worse. "
        "Your job is to lower the score by making the code easier to read, "
        "NOT by rearranging it to trick the metric. The rules below tell "
        "you which refactors count as real improvements and which are "
        "forbidden shortcuts."
    )


def _what_rf_measures() -> str:
    return (
        "## What rf measures\n\n"
        "ReaderFriction measures structural indirection in the static "
        "call graph — how many hops, files, and pass-through wrappers a "
        "reader crosses between an entrypoint and meaningful logic. The "
        "score is a weighted sum of six path-level metrics:\n\n"
        "- `trace_depth` (weight 2) — hops from entrypoint to the first "
        "non-wrapper function\n"
        "- `file_jumps` (3) — distinct source files on that path\n"
        "- `wrapper_depth` (3) — longest run of consecutive thin wrappers\n"
        "- `thin_wrapper_count` (2) — total wrappers on the path\n"
        "- `context_width` (2) — mean of arg count + distinct self.* "
        "attributes per function along the path\n"
        "- `flow_fragmentation` (2) — fan-out pressure (branching at the "
        "entrypoint and along the path)\n\n"
        "A separate `pass_through_ratio` (wrappers / total functions) is "
        "reported but not scored. A function is classified as a thin "
        "wrapper when it has ≤ 3 statements, exactly one non-trivial "
        "call, returns that call, and has no loops, branches, "
        "transformations, or validation."
    )


def _dont_list() -> str:
    return (
        "## FORBIDDEN changes (these game the score without improving the code)\n\n"
        "Do not apply any of the following. They are cheap gradients that "
        "lower the `rf` score but do not make the code easier to read — "
        "a human reviewer will notice, and other tools may catch you.\n\n"
        "1. **Do NOT collapse multiple files into one file.** Moving "
        "five small modules into one 2000-line module drops `file_jumps` "
        "but produces an unreadable haystack. Keep modules separated "
        "along the existing domain boundaries.\n"
        "2. **Do NOT merge functions on the path into one giant "
        "function.** Inlining a *meaningful* callee into its sole caller "
        "is sometimes fine, but merging an entire chain into one 200-line "
        "function replaces one form of complexity with another. Target "
        "thin wrappers specifically (see DO list below).\n"
        "3. **Do NOT add no-op statements** (logging, metrics counters, "
        "debug prints, extra comments, trivial assertions) to wrappers "
        "just to defeat the 8-rule wrapper classifier. The classifier "
        "will stop flagging the function but it is still a pass-through.\n"
        "4. **Do NOT rename wrappers to sound meaningful.** A function "
        "called `normalise_payload` that still does `return "
        "inner.do(x)` is still a wrapper.\n"
        "5. **Do NOT hide calls behind dynamic dispatch** (registries, "
        "getattr, `importlib.import_module`) to make `rf`'s call graph "
        "give up on that path. That lowers the score because `rf` can't "
        "see dynamic calls, but it makes the code harder to read, not "
        "easier.\n"
        "6. **Do NOT delete or skip tests** to suppress failures. Every "
        "pre-existing test must still pass after the refactor."
    )


def _do_list(result: ScanResult, wrappers: set[FunctionRef]) -> str:
    recs: list[str] = []
    for entry in result.entrypoints:
        recs.extend(_recommendations_for(entry, wrappers))
    if not recs:
        recs.append(
            "- No high-priority structural refactors detected. The "
            "codebase is already within healthy ranges for rf."
        )
    body = "\n".join(recs)
    return (
        "## ALLOWED refactors — apply in priority order\n\n"
        "These genuinely improve readability; they happen to also lower "
        "the `rf` score.\n\n"
        f"{body}"
    )


def _recommendations_for(
    entry: EntrypointResult, wrappers: set[FunctionRef]
) -> list[str]:
    out: list[str] = []
    metrics = entry.metrics

    wrapper_depth = round(metrics["wrapper_depth"].value)
    thin_count = round(metrics["thin_wrapper_count"].value)
    fan_out = round(metrics["flow_fragmentation"].value)
    context = metrics["context_width"].value
    trace = round(metrics["trace_depth"].value)

    wrapper_names = [p.qualname for p in entry.path if p in wrappers]
    path_display = " → ".join(p.qualname for p in entry.path)

    if wrapper_depth >= 2:
        out.append(
            f"- **Inline the wrapper chain** on the path to "
            f"`{entry.ref.qualname}`:\n"
            f"    {path_display}\n"
            f"  The wrappers are: {', '.join(wrapper_names)}. "
            f"Each of these functions matches the wrapper heuristic — "
            f"short body, one non-trivial call, returns that call, no "
            f"real logic. Inline each wrapper into its single caller. "
            f"Keep the final non-wrapper on the path intact. Apply "
            f"Fowler's *Inline Function* refactor: move the body into "
            f"the caller, then delete the wrapper."
        )
    elif thin_count >= 1:
        out.append(
            f"- **Inline {thin_count} isolated wrapper(s)** on the "
            f"path to `{entry.ref.qualname}`: "
            f"{', '.join(wrapper_names)}. Each adds a hop without "
            f"meaningful logic."
        )

    if fan_out >= 4:
        out.append(
            f"- **Reduce fan-out at `{entry.ref.qualname}`** "
            f"(current flow_fragmentation = {fan_out}). The entrypoint "
            f"calls many sibling helpers, forcing the reader to pick "
            f"which to follow. Group related siblings into a named "
            f"orchestrator — e.g. replace six direct calls with one "
            f"`load_all()` + one `validate_all()`. This does NOT mean "
            f"merging the siblings; it means naming the control flow."
        )

    if context >= 4:
        out.append(
            f"- **Tighten context width at `{entry.ref.qualname}`** "
            f"(current mean = {context:.2f}). Functions on the path "
            f"accept many parameters or touch many `self.*` attributes. "
            f"Introduce a `dataclass` (or `TypedDict`) that groups "
            f"related arguments so each call passes one concept, not "
            f"five."
        )

    if trace >= 3 and wrapper_depth <= 1:
        out.append(
            f"- **Move meaningful logic closer to `{entry.ref.qualname}`** "
            f"(trace_depth = {trace}). The path is long but not because "
            f"of wrappers. Consider whether one of the intermediate "
            f"layers represents a genuine abstraction boundary; if not, "
            f"flatten it."
        )

    return out


def _offenders_section(result: ScanResult, wrappers: set[FunctionRef]) -> str:
    lines = [
        "## Specific functions flagged",
        "",
        "For each entrypoint below, `rf` reports the chosen trace path. "
        "Functions marked `WRAPPER` match the thin-wrapper heuristic.",
        "",
    ]
    for entry in result.entrypoints:
        lines.append(
            f"### `{entry.ref.qualname}` — score {entry.score}"
        )
        lines.append("")
        lines.append(f"Location: `{entry.ref.file}:{entry.ref.lineno}`")
        lines.append("")
        lines.append("Trace path:")
        lines.append("")
        for i, node in enumerate(entry.path):
            tag = "WRAPPER" if node in wrappers else "meaningful"
            lines.append(f"  {i + 1}. `{node.qualname}`  ({tag})")
        lines.append("")
        lines.append("Metrics:")
        for key in (
            "trace_depth",
            "file_jumps",
            "wrapper_depth",
            "thin_wrapper_count",
            "flow_fragmentation",
            "context_width",
            "pass_through_ratio",
        ):
            metric = entry.metrics.get(key)
            if metric is None:
                continue
            lines.append(f"- {key}: {metric.display}")
        lines.append("")
    return "\n".join(lines).rstrip()


def _verification_section() -> str:
    return (
        "## Verification checklist\n\n"
        "After every refactor, run ALL of the following and confirm "
        "each outcome. If any fails, revert that refactor and try "
        "something else.\n\n"
        "```bash\n"
        "# 1. rf score should drop\n"
        "rf scan <path> --format json\n\n"
        "# 2. Per-function complexity MUST NOT rise — if rf drops but\n"
        "#    cyclomatic/cognitive complexity spikes, you moved the\n"
        "#    problem instead of solving it.\n"
        "uv tool run complexipy <path>          # or radon cc <path>\n\n"
        "# 3. Lint + types clean\n"
        "ruff check <path>\n"
        "pyright <path>\n\n"
        "# 4. Every pre-existing test still passes\n"
        "pytest\n\n"
        "# 5. No file over ~500 lines after the refactor. If one is,\n"
        "#    you collapsed code that should stay separated.\n"
        "find <path> -name '*.py' -exec wc -l {} + | sort -n | tail\n"
        "```\n\n"
        "Report back: the rf score before vs after, the complexipy "
        "numbers before vs after, and a summary of which wrappers you "
        "inlined. If you considered a refactor and rejected it because "
        "it would violate a FORBIDDEN rule, mention that too."
    )


__all__ = ["render"]
