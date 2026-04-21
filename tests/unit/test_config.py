"""REQ-080..REQ-082 config precedence."""

from __future__ import annotations

from pathlib import Path

from readerfriction.config import (
    DEFAULT_EXCLUDES,
    Config,
    find_pyproject,
    load_config,
)


def test_req_080_pyproject_loaded(tmp_path: Path) -> None:
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        """
[tool.readerfriction]
wrapper_threshold = 4
exclude = ["tests/fixtures/*"]

[tool.readerfriction.weights]
trace_depth = 5
""".strip()
    )
    config = load_config(pyproject)
    assert config.wrapper_threshold == 4
    assert "tests/fixtures/*" in config.exclude
    assert config.weights.trace_depth == 5
    # untouched keys keep defaults
    assert config.weights.file_jumps == 3


def test_req_081_cli_overrides(tmp_path: Path) -> None:
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        """
[tool.readerfriction]
wrapper_threshold = 4
""".strip()
    )
    overrides = {"wrapper_threshold": 7, "weights": {"file_jumps": 10}}
    config = load_config(pyproject, overrides=overrides)
    assert config.wrapper_threshold == 7
    assert config.weights.file_jumps == 10


def test_req_082_weights_configurable() -> None:
    config = Config.model_validate(
        {
            "weights": {
                "trace_depth": 10,
                "file_jumps": 10,
                "wrapper_depth": 10,
                "thin_wrapper_count": 10,
                "context_width": 10,
                "flow_fragmentation": 10,
            }
        }
    )
    assert config.weights.trace_depth == 10
    assert config.weights.flow_fragmentation == 10


def test_defaults_when_no_pyproject() -> None:
    config = load_config(None)
    assert config.wrapper_threshold == 6
    assert config.weights.trace_depth == 2


def test_all_excludes_prepends_defaults(tmp_path: Path) -> None:
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        """
[tool.readerfriction]
exclude = ["custom/*"]
""".strip()
    )
    config = load_config(pyproject)
    for d in DEFAULT_EXCLUDES:
        assert d in config.all_excludes
    assert "custom/*" in config.all_excludes


def test_find_pyproject_walks_upward(tmp_path: Path) -> None:
    root = tmp_path / "project"
    (root / "src" / "pkg").mkdir(parents=True)
    (root / "pyproject.toml").write_text("[tool.readerfriction]\n")
    assert find_pyproject(root / "src" / "pkg") == root / "pyproject.toml"


def test_find_pyproject_returns_none_when_missing(tmp_path: Path) -> None:
    assert find_pyproject(tmp_path) is None
