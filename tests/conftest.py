from __future__ import annotations

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="session")
def repo_root() -> Path:
    return REPO_ROOT


@pytest.fixture(scope="session")
def examples_root(repo_root: Path) -> Path:
    return repo_root / "spec" / "examples"


@pytest.fixture(scope="session")
def contracts_dir(repo_root: Path) -> Path:
    return repo_root / "spec" / "contracts"
