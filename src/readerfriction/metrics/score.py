"""REQ-067 aggregate reader_friction_score.

``pass_through_ratio`` is intentionally excluded from the score (per
``spec/metrics.md §8``) — it is a population statistic, not a path statistic.
"""

from __future__ import annotations

from readerfriction.config import MetricWeights
from readerfriction.models import MetricResult

SCORED_METRICS: tuple[str, ...] = (
    "trace_depth",
    "file_jumps",
    "wrapper_depth",
    "thin_wrapper_count",
    "context_width",
    "flow_fragmentation",
)


def compute(metrics: dict[str, MetricResult], weights: MetricWeights) -> int:
    total = 0
    weights_dict = weights.model_dump()
    for name in SCORED_METRICS:
        metric = metrics.get(name)
        if metric is None:
            continue
        weight = int(weights_dict.get(name, 0))
        total += weight * round(metric.value)
    return total


__all__ = ["SCORED_METRICS", "compute"]
