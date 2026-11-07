"""Patterns of a row sample: Drain clusters with sample and estimated counts, a trend and a FlyQL filter.

Grouping, scaling and trend follow HyperDX `common-utils/src/drain/mine-patterns.ts` (MIT).
"""

import math

from telescope.fetchers.chart import GRANULARITY_SECONDS, STANDARD_STEPS
from telescope.patterns.drain import PARAM, Drain
from telescope.patterns.masking import MASK, normalize

TREND_BUCKETS = 24
MAX_SAMPLES = 3
MAX_PATTERNS = 200
# Bounds the clusters each message is compared against, so mining stays linear in the sample.
MAX_CLUSTERS = 200


def trend_step(time_from: int, time_to: int) -> int:
    size = math.ceil((time_to - time_from) / 1000 / TREND_BUCKETS)
    name = next((s for s in STANDARD_STEPS if GRANULARITY_SECONDS[s] >= size), "1d")
    return GRANULARITY_SECONDS[name] * 1000


def like_filter(column: str, template: str) -> str:
    """A FlyQL LIKE over the template: parameters, masks and tokens with quotes or backslashes become %."""
    parts = []
    for token in template.split(" "):
        if token == PARAM or "\\" in token or "'" in token or '"' in token:
            parts.append("%")
        else:
            token = token.replace("%", "\\%").replace("_", "\\_")
            parts.append(token.replace(PARAM, "%").replace(MASK, "%"))
    return f"{column} like '{' '.join(parts)}'"


def mine_patterns(rows, total, time_from, time_to, column):
    """rows: (time_ms, body) pairs; total: matching rows the sample stands for."""
    drain = Drain(max_clusters=MAX_CLUSTERS)
    step = trend_step(time_from, time_to)
    start = time_from // step * step
    buckets = list(range(start, time_to, step)) or [start]
    groups = {}
    for time_ms, body in rows:
        text = normalize(body)
        cluster = drain.add(text)
        group = groups.setdefault(
            cluster.id, {"cluster": cluster, "rows": [], "trend": [0] * len(buckets)}
        )
        if len(group["rows"]) < MAX_SAMPLES:
            group["rows"].append({"time": time_ms, "body": body})
        index = min(max((time_ms - start) // step, 0), len(buckets) - 1)
        group["trend"][index] += 1

    # Clusters the LRU evicted and re-created share a template; report them as one.
    merged = {}
    for group in groups.values():
        cluster = group["cluster"]
        same = merged.get(cluster.template)
        if same is None:
            merged[cluster.template] = dict(group, size=cluster.size)
            continue
        same["size"] += cluster.size
        same["rows"] = (same["rows"] + group["rows"])[:MAX_SAMPLES]
        same["trend"] = [a + b for a, b in zip(same["trend"], group["trend"])]

    scale = total / len(rows) if rows else 1
    patterns = []
    for template, group in merged.items():
        size = group["size"]
        patterns.append(
            {
                "id": str(group["cluster"].id),
                "pattern": template,
                "count": size,
                "est_total": max(round(size * scale), 1),
                "share": size / len(rows),
                "sample_rows": group["rows"],
                "trend": [round(c * scale) for c in group["trend"]],
                "filter": like_filter(column, template),
            }
        )
    patterns.sort(key=lambda p: (-p["count"], p["pattern"]))
    return {
        "patterns": patterns[:MAX_PATTERNS],
        "buckets": buckets,
        "step": step,
        "total": total,
        "sample_size": len(rows),
        "column": column,
    }
