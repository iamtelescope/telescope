import json
from typing import List, Dict, Tuple, Optional
from telescope.fetchers.models import Row
from flyql.columns import ParsedColumn


def generate_graph_from_rows(
    rows: List[Row],
    time_from: int,
    time_to: int,
    group_by: Optional[ParsedColumn] = None,
) -> Tuple[List[int], Dict[str, List[int]], int]:

    stats_by_ts = {}
    unique_ts = {time_from, time_to}
    total = len(rows)

    seconds = int(time_to - time_from) / 1000
    if seconds > 15:
        max_points = 150
        stats_interval_seconds = round(seconds / max_points)
        if stats_interval_seconds == 0:
            stats_interval_seconds = 1
        bucket_interval_ms = stats_interval_seconds * 1000
    else:
        bucket_interval_ms = 1000

    groupper_name = "Rows" if not group_by else None

    for row in rows:
        ts_ms = row.time["unixtime"]
        if bucket_interval_ms > 1000:
            ts_key = int(ts_ms / bucket_interval_ms) * bucket_interval_ms
        else:
            ts_key = int(ts_ms / 1000) * 1000
        unique_ts.add(ts_key)

        if group_by:
            if "." in group_by.name:
                spl = group_by.name.split(".")
                json_path = spl[1:]
                try:
                    data = json.loads(row.data[spl[0]])
                    for key in json_path:
                        data = data.get(key, {})
                    if not data:
                        groupper_name = "__none__"
                    else:
                        groupper_name = str(data)
                except (json.JSONDecodeError, KeyError, TypeError):
                    groupper_name = "__none__"
            else:
                groupper_name = str(row.data.get(group_by.name, "__none__"))

        if groupper_name not in stats_by_ts:
            stats_by_ts[groupper_name] = {}

        if ts_key not in stats_by_ts[groupper_name]:
            stats_by_ts[groupper_name][ts_key] = 1
        else:
            stats_by_ts[groupper_name][ts_key] += 1

    timestamps = sorted(unique_ts)
    data = {}

    for name in stats_by_ts.keys():
        data[name] = []

    for ts in timestamps:
        for name in stats_by_ts.keys():
            value = stats_by_ts.get(name, {}).get(ts, 0)
            data[name].append(value)

    return timestamps, data, total
