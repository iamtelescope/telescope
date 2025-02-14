import clickhouse_driver as clickhouse

from flyql.parser import parse, ParserError
from flyql.exceptions import FlyqlError
from flyql_generators.clickhouse import to_sql, Field

from telescope.models import Row
from telescope.utils import get_source_database_conn_kwargs


def flyql_clickhouse_fields(source_fields):
    return {
        data["name"]: Field(
            name=data["name"], _type=data["type"], values=data["values"]
        )
        for _, data in source_fields.items()
    }


def validate_flyql_query(source, query):
    if not query:
        return True, None

    try:
        parser = parse(query)
    except ParserError as err:
        return False, err.message
    else:
        try:
            to_sql(parser.root, fields=flyql_clickhouse_fields(source._fields))
        except FlyqlError as err:
            return False, err.message

    return True, None


def autocomplete(source, field, time_from, time_to, value):
    incomplete = False
    items = []
    from_db_table = f"{source.connection['database']}.{source.connection['table']}"
    time_clause = f"{source.time_field} BETWEEN fromUnixTimestamp64Milli({time_from}) and fromUnixTimestamp64Milli({time_to})"
    query = f"SELECT DISTINCT {field} FROM {from_db_table} WHERE {time_clause} and {field} LIKE %(value)s ORDER BY {field} LIMIT 500"
    with clickhouse.Client(**get_source_database_conn_kwargs(source)) as client:
        result = client.execute(query, {"value": f"%{value}%"})
        items = [str(x[0]) for x in result]
    if len(items) >= 500:
        incomplete = True
    return items, incomplete


def fetch_data(
    source, query, time_from, time_to, limit, timezone, desc=True, get_stats=True
):
    if query:
        parser = parse(query)
        filter_clause = to_sql(
            parser.root, fields=flyql_clickhouse_fields(source._fields)
        )
    else:
        filter_clause = "true"

    order_by_clause = f"ORDER BY {source.time_field} DESC"

    total = 0
    time_clause = f"{source.time_field} BETWEEN fromUnixTimestamp64Milli({time_from}) and fromUnixTimestamp64Milli({time_to})"
    from_db_table = f"{source.connection['database']}.{source.connection['table']}"

    fields_names = sorted(source._fields.keys())
    fields_to_select = ", ".join(sorted(fields_names))
    select_query = f"SELECT generateUUIDv4(),{fields_to_select} FROM {from_db_table} WHERE {time_clause} AND {filter_clause} {order_by_clause} LIMIT {limit}"
    count_query = f"SELECT count() as c FROM {from_db_table} WHERE {time_clause} AND {filter_clause}"

    rows = []
    stats = {}
    stats_by_ts = {}
    unique_ts = set([time_from, time_to])
    seconds = int(time_to - time_from) / 1000
    stats_names = set()
    if seconds > 15:
        max_points = 150
        stats_interval_seconds = round(seconds / max_points)
        if stats_interval_seconds == 0:
            stats_interval_seconds = 1
        stats_time_selector = f"toUnixTimestamp(toStartOfInterval({source.time_field}, INTERVAL {stats_interval_seconds} second))*1000"
    else:
        if source._fields[source.time_field]["type"] == "datetime64":
            stats_time_selector = f"toUnixTimestamp64Milli({source.time_field})"
        else:
            stats_time_selector = f"toUnixTimestamp({source.time_field})*1000"

    with clickhouse.Client(**get_source_database_conn_kwargs(source)) as client:
        selected_fields = [source._record_pseudo_id_field] + fields_names
        for item in client.execute(select_query):
            rows.append(
                Row(
                    source=source,
                    selected_fields=selected_fields,
                    values=item,
                    timezone=timezone,
                )
            )
        if get_stats and rows:
            total = client.execute(count_query)[0][0]
            stat_sql = (
                f"SELECT {stats_time_selector} as t, "
                f"COUNT({source.severity_field}) as c, "
                f"{source.severity_field} FROM {from_db_table} "
                f"WHERE {time_clause} AND {filter_clause} GROUP BY t,{source.severity_field} ORDER by t"
            )
            for item in client.execute(stat_sql):
                ts, count, severity = item
                stats_names.add(severity)
                items = stats.get(severity, [])
                items.append((ts, count))
                stats[severity] = items
                unique_ts.add(ts)
                if severity not in stats_by_ts:
                    stats_by_ts[severity] = {ts: count}
                else:
                    stats_by_ts[severity][ts] = count
    stats = {
        "timestamps": sorted(unique_ts),
        "data": {},
        "meta": {
            "form": time_from,
            "to": time_to,
            "newest_row": 0,
            "oldest_row": 0,
            "total": total,
            "rows": len(rows),
        },
    }
    for name in stats_names:
        stats["data"][name] = []

    for ts in stats["timestamps"]:
        ts_sum = 0
        for name in stats_names:
            value = stats_by_ts.get(name, {}).get(ts, 0)
            stats["data"][name].append(value)
            ts_sum += value

    if rows:
        stats["meta"]["newest_row"] = int(rows[0].time["unixtime"])
        stats["meta"]["oldest_row"] = int(rows[-1].time["unixtime"])

    return rows, total, stats
