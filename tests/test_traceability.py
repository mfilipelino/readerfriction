"""Every REQ id in spec/traceability.md maps to a test id under tests/."""

from __future__ import annotations

import re
from pathlib import Path

REQ_PATTERN = re.compile(r"REQ-\d{3}")


def test_every_requirement_has_a_test(repo_root: Path) -> None:
    traceability = (repo_root / "spec/traceability.md").read_text()
    req_ids = sorted(set(REQ_PATTERN.findall(traceability)))

    test_files = list((repo_root / "tests").rglob("test_*.py"))
    all_test_text = "\n".join(f.read_text() for f in test_files)

    missing: list[str] = []
    for req in req_ids:
        token = req.replace("REQ-", "req_")
        if token not in all_test_text:
            missing.append(req)

    assert missing == [], (
        "These REQ ids in spec/traceability.md have no matching test "
        f"(looking for function names like test_{'req_001'}): {missing}"
    )


def test_traceability_covers_all_requirements_file_ids(repo_root: Path) -> None:
    requirements = (repo_root / "spec/requirements.md").read_text()
    traceability = (repo_root / "spec/traceability.md").read_text()
    declared = sorted(set(REQ_PATTERN.findall(requirements)))
    traced = sorted(set(REQ_PATTERN.findall(traceability)))
    missing = [r for r in declared if r not in traced]
    assert missing == [], f"Requirements not in traceability matrix: {missing}"
