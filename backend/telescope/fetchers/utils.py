import re
import json
import logging
from typing import Optional, Dict, Any, List, Tuple

logger = logging.getLogger("telescope.fetchers.utils")


def normalize_body_to_dict(body: str) -> dict:
    try:
        parsed = json.loads(body)
        if isinstance(parsed, dict):
            return parsed
        else:
            return {"message": body}
    except (json.JSONDecodeError, ValueError):
        return {"message": body}


def extract_severity_with_rules(message: str, severity_rules: Dict[str, Any]) -> str:
    if not severity_rules or not isinstance(severity_rules, dict):
        return "UNKNOWN"

    extract_rules = severity_rules.get("extract", [])
    remap_rules = severity_rules.get("remap", [])

    for rule in extract_rules:
        rule_type = rule.get("type")
        extracted = None

        if rule_type == "json":
            extracted = apply_json_rule(message, rule)
        elif rule_type == "regex":
            extracted = apply_regex_rule(message, rule)

        if extracted is not None:
            return apply_remap(extracted, remap_rules)

    return "UNKNOWN"


def apply_json_rule(message: str, rule: Dict[str, Any]) -> Optional[str]:
    try:
        data = json.loads(message)

        path = rule.get("path", [])
        if not isinstance(path, list):
            return None

        if not path:
            return None

        current = data
        for key in path:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                return None

        return str(current)
    except (json.JSONDecodeError, Exception):
        return None


def apply_regex_rule(message: str, rule: Dict[str, Any]) -> Optional[str]:
    try:
        pattern = rule.get("pattern")
        group = rule.get("group", 0)
        case_insensitive = rule.get("case_insensitive", False)

        flags = re.IGNORECASE if case_insensitive else 0
        match = re.search(pattern, message, flags=flags)
        if match:
            return match.group(group)
    except (re.error, IndexError, Exception):
        return None


def apply_remap(extracted_value: str, remap_rules: List[Dict[str, Any]]) -> str:
    if not remap_rules:
        return extracted_value

    for rule in remap_rules:
        pattern = rule.get("pattern")
        target_value = rule.get("value")
        case_insensitive = rule.get("case_insensitive", False)

        if not pattern or not target_value:
            continue

        flags = re.IGNORECASE if case_insensitive else 0

        try:
            if re.fullmatch(pattern, extracted_value, flags=flags):
                return target_value
        except re.error:
            continue

    return extracted_value


def generate_graph_from_rows(
    rows: List,
    time_from: int,
    time_to: int,
    group_by: Optional = None,
    group_by_severity: bool = False,
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

    groupper_name = "Rows" if not group_by and not group_by_severity else None

    for row in rows:
        ts_ms = row.time["unixtime"]
        if bucket_interval_ms > 1000:
            ts_key = int(ts_ms / bucket_interval_ms) * bucket_interval_ms
        else:
            ts_key = int(ts_ms / 1000) * 1000
        unique_ts.add(ts_key)

        if group_by_severity:
            groupper_name = row.severity if row.severity else "__none__"
        elif group_by:
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
