"""Docs cover every CLI command and every metric."""

from __future__ import annotations

from pathlib import Path

COMMANDS = ("scan", "trace", "explain", "report", "diff")
METRICS = (
    "trace_depth",
    "file_jumps",
    "wrapper_depth",
    "thin_wrapper_count",
    "flow_fragmentation",
    "context_width",
    "pass_through_ratio",
)


def test_readme_mentions_all_commands(repo_root: Path) -> None:
    readme = (repo_root / "README.md").read_text()
    for cmd in COMMANDS:
        assert f"readerfriction {cmd}" in readme or f"`{cmd}`" in readme


def test_readme_mentions_all_metrics(repo_root: Path) -> None:
    # Match on either snake_case identifier or the human label used in reports.
    labels = {
        "trace_depth": ["trace depth", "Trace Depth"],
        "file_jumps": ["file jumps", "File Jumps"],
        "wrapper_depth": ["wrapper depth", "Wrapper Depth"],
        "thin_wrapper_count": ["thin wrapper", "Thin Wrapper"],
        "flow_fragmentation": ["flow fragmentation", "Flow Fragmentation"],
        "context_width": ["context width", "Context Width"],
        "pass_through_ratio": ["pass-through ratio", "Pass-Through Ratio"],
    }
    readme = (repo_root / "README.md").read_text()
    for metric, variants in labels.items():
        assert any(v.lower() in readme.lower() for v in variants), metric


def test_changelog_has_version(repo_root: Path) -> None:
    changelog = (repo_root / "CHANGELOG.md").read_text()
    assert "[0.1.0]" in changelog
