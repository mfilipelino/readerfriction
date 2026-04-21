"""Load ``[tool.readerfriction]`` configuration with CLI precedence."""

from __future__ import annotations

import tomllib
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

DEFAULT_EXCLUDES: tuple[str, ...] = (
    "venv",
    ".venv",
    "build",
    "dist",
    "__pycache__",
    ".git",
    ".tox",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
)


class MetricWeights(BaseModel):
    model_config = ConfigDict(extra="forbid")

    trace_depth: int = 2
    file_jumps: int = 3
    wrapper_depth: int = 3
    thin_wrapper_count: int = 2
    context_width: int = 2
    flow_fragmentation: int = 2


class Thresholds(BaseModel):
    model_config = ConfigDict(extra="forbid")

    warn: int = 15
    error: int = 30


class Config(BaseModel):
    model_config = ConfigDict(extra="forbid")

    exclude: list[str] = Field(default_factory=list)
    wrapper_threshold: int = 6
    weights: MetricWeights = Field(default_factory=MetricWeights)
    thresholds: Thresholds = Field(default_factory=Thresholds)

    @property
    def all_excludes(self) -> list[str]:
        return [*DEFAULT_EXCLUDES, *self.exclude]


def find_pyproject(start: Path) -> Path | None:
    """Walk upward from ``start`` to find the nearest ``pyproject.toml``."""

    start = start.resolve()
    candidates = [start, *start.parents] if start.is_dir() else [start.parent, *start.parents]
    for directory in candidates:
        candidate = directory / "pyproject.toml"
        if candidate.is_file():
            return candidate
    return None


def load_config(
    pyproject_path: Path | None,
    overrides: dict[str, object] | None = None,
) -> Config:
    """Merge defaults ← pyproject.toml ← overrides (highest wins)."""

    file_data: dict[str, object] = {}
    if pyproject_path is not None and pyproject_path.is_file():
        data = tomllib.loads(pyproject_path.read_text())
        file_data = (
            data.get("tool", {}).get("readerfriction", {}) if isinstance(data, dict) else {}
        )

    merged = _deep_merge(file_data, overrides or {})
    return Config.model_validate(merged)


def _deep_merge(base: dict[str, object], override: dict[str, object]) -> dict[str, object]:
    out = dict(base)
    for key, value in override.items():
        if (
            key in out
            and isinstance(out[key], dict)
            and isinstance(value, dict)
        ):
            out[key] = _deep_merge(out[key], value)  # type: ignore[arg-type]
        else:
            out[key] = value
    return out


__all__ = [
    "DEFAULT_EXCLUDES",
    "Config",
    "MetricWeights",
    "Thresholds",
    "find_pyproject",
    "load_config",
]
