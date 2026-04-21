"""Regenerate spec/contracts/*.schema.json from Pydantic models.

Run manually (or from tests with ``UPDATE_SCHEMAS=1``). CI asserts that the
committed files match the regenerated ones.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from readerfriction.models import (  # noqa: E402
    ExplainResult,
    ReportResult,
    ScanResult,
    TraceResult,
)

MODELS = {
    "scan-result.schema.json": ScanResult,
    "trace-result.schema.json": TraceResult,
    "explain-result.schema.json": ExplainResult,
    "report-result.schema.json": ReportResult,
}


def build_schemas() -> dict[str, dict]:
    return {name: model.model_json_schema() for name, model in MODELS.items()}


def write_schemas(out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    for name, schema in build_schemas().items():
        target = out_dir / name
        target.write_text(json.dumps(schema, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    write_schemas(REPO_ROOT / "spec" / "contracts")
