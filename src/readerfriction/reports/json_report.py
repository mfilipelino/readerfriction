"""JSON serialisation for ``ScanResult`` / ``TraceResult`` / ``ExplainResult``."""

from __future__ import annotations

import json

from pydantic import BaseModel


def render(model: BaseModel) -> str:
    """Return the canonical JSON form for a result model.

    Keys are sorted and the payload is indented so diffs are reviewable.
    """

    return json.dumps(
        model.model_dump(mode="json"),
        indent=2,
        sort_keys=True,
    )


__all__ = ["render"]
