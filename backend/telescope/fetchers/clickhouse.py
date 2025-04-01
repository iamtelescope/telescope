from typing import List

import clickhouse_driver as clickhouse
from clickhouse_driver.util.escape import escape_param

from flyql.parser import parse, ParserError
from flyql.exceptions import FlyqlError
from flyql_generators.clickhouse import to_sql, Field

from telescope.models import SourceField
from telescope.fields import ParsedField

from telescope.fetchers.request import (
    AutocompleteRequest,
    DataRequest,
    GraphDataRequest,
)
from telescope.fetchers.response import (
    AutocompleteResponse,
    DataResponse,
    GraphDataResponse,
)
from telescope.fetchers.fetcher import BaseFetcher
from telescope.fetchers.models import Row

from telescope.utils import convert_to_base_ch, get_telescope_field


def flyql_clickhouse_fields(source_fields: List[SourceField]):
    return {
        field.name: Field(
            name=field.name,
            jsonstring=field.jsonstring,
            _type=field.type,
            values=field.values,
        )
        for _, field in source_fields.items()
    }


def get_client_kwargs(data):
    return {
        "host": data["host"],
        "port": data["port"],
        "user": data["user"],
        "password": data["password"],
        "secure": data["ssl"],
    }


def get_source_database_conn_kwargs(source):
    return get_client_kwargs(source.connection)


class ConnectionTestResponse:
    def __init__(
        self,
    ):
        self.reachability = {
            "result": False,
            "error": "",
        }
        self.schema = {
            "result": False,
            "error": "",
            "data": [],
        }

    def as_dict(self) -> dict:
        return {
            "reachability": self.reachability,
            "schema": self.schema,
        }


class Fetcher(BaseFetcher):
    @classmethod
    def validate_query(cls, source, query):
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

    @classmethod
    def test_connection(cls, data: dict) -> ConnectionTestResponse:
        response = ConnectionTestResponse()
        target = f"`{data['database']}`.`{data['table']}`"
        with clickhouse.Client(**get_client_kwargs(data)) as client:
            try:
                client.execute(f"SELECT 1 FROM {target} LIMIT 1")
            except Exception as err:
                response.reachability["error"] = str(err)
                response.schema["error"] = "Skipped due to reachability test failed"
            else:
                response.reachability["result"] = True
                try:
                    result = client.execute(f"DESCRIBE TABLE {target} FORMAT JSON")
                except Exception as err:
                    response.schema["error"] = str(err)
                else:
                    response.schema["result"] = True
                    response.schema["data"] = [
                        get_telescope_field(x[0], x[1]) for x in result
                    ]
        return response

    @classmethod
    def autocomplete(cls, source, field, time_from, time_to, value):
        incomplete = False
        from_db_table = f"{source.connection['database']}.{source.connection['table']}"
        time_clause = f"{source.time_field} BETWEEN fromUnixTimestamp64Milli({time_from}) and fromUnixTimestamp64Milli({time_to})"
        query = f"SELECT DISTINCT {field} FROM {from_db_table} WHERE {time_clause} and {field} LIKE %(value)s ORDER BY {field} LIMIT 500"
        with clickhouse.Client(**get_source_database_conn_kwargs(source)) as client:
            result = client.execute(query, {"value": f"%{value}%"})
            items = [str(x[0]) for x in result]
        if len(items) >= 500:
            incomplete = True
        return AutocompleteResponse(items=items, incomplete=incomplete)

    @classmethod
    def fetch_graph_data(
        cls,
        request: GraphDataRequest,
    ):
        if request.query:
            parser = parse(request.query)
            filter_clause = to_sql(
                parser.root, fields=flyql_clickhouse_fields(request.source._fields)
            )
        else:
            filter_clause = "true"

        order_by_clause = f"ORDER BY {request.source.time_field} DESC"
        raw_where_clause = request.raw_query or "true"

        group_by_value = ""
        group_by = request.group_by[0] if request.group_by else None
        if group_by:
            if ":" in group_by.name:
                spl = group_by.name.split(":")
                if group_by.jsonstring:
                    json_path = spl[1:]
                    json_path = ", ".join(
                        [escape_param(x, context=None) for x in json_path]
                    )
                    group_by_value = (
                        f"JSONExtractString({group_by.root_name}, {json_path})"
                    )
                elif group_by.is_map():
                    map_key = ":".join(spl[1:])
                    group_by_value = f"{group_by.root_name}['{map_key}']"
                elif group_by.is_array():
                    array_index = int(":".join(spl[1]))
                    group_by_value = f"{group_by.root_name}[{array_index}]"
                else:
                    raise ValueError
            else:
                group_by_value = f"toString({group_by.root_name})"

        total = 0
        time_clause = f"{request.source.time_field} BETWEEN fromUnixTimestamp64Milli({request.time_from}) and fromUnixTimestamp64Milli({request.time_to})"
        from_db_table = f"{request.source.connection['database']}.{request.source.connection['table']}"

        time_field_type = convert_to_base_ch(
            request.source._fields[request.source.time_field].type.lower()
        )
        to_time_zone = ""
        if time_field_type in ["datetime", "datetime64"]:
            to_time_zone = f"toTimeZone({request.source.time_field}, 'UTC')"
        elif time_field_type in ["timestamp", "uint64", "int64"]:
            to_time_zone = f"toTimeZone(toDateTime({request.source.time_field}), 'UTC')"

        fields_names = sorted(request.source._fields.keys())
        fields_to_select = []
        for field in fields_names:
            if field == request.source.time_field:
                fields_to_select.append(to_time_zone)
            else:
                fields_to_select.append(field)
        fields_to_select = ", ".join(fields_to_select)

        rows = []
        stats = {}
        stats_by_ts = {}
        unique_ts = {request.time_from, request.time_to}
        seconds = int(request.time_to - request.time_from) / 1000
        stats_names = set()
        stats_time_selector = ""
        if seconds > 15:
            max_points = 150
            stats_interval_seconds = round(seconds / max_points)
            if stats_interval_seconds == 0:
                stats_interval_seconds = 1
            stats_time_selector = f"toUnixTimestamp(toStartOfInterval({to_time_zone}, toIntervalSecond({stats_interval_seconds}))) * 1000"
        else:
            if time_field_type in ["datetime", "timestamp", "uint64"]:
                stats_time_selector = f"toUnixTimestamp({to_time_zone})*1000"
            elif time_field_type == "datetime64":
                stats_time_selector = f"toUnixTimestamp64Milli({to_time_zone})"

        with clickhouse.Client(
            **get_source_database_conn_kwargs(request.source)
        ) as client:
            stat_sql = f"SELECT {stats_time_selector} as t, COUNT() as Count"
            if group_by_value:
                stat_sql += f", {group_by_value} as `{group_by.name}`"
            stat_sql += f" FROM {from_db_table} WHERE {time_clause} AND {filter_clause} AND {raw_where_clause} GROUP BY t"
            if group_by_value:
                stat_sql += f", `{group_by.name}`"
            stat_sql += " ORDER BY t"
            for item in client.execute(stat_sql):
                if group_by_value:
                    ts, count, groupper = item
                    if not groupper:
                        groupper = "__none__"
                else:
                    ts, count = item
                    groupper = "Rows"

                stats_names.add(groupper)
                items = stats.get(groupper, [])
                items.append((ts, count))
                total += count
                stats[groupper] = items
                unique_ts.add(ts)
                if groupper not in stats_by_ts:
                    stats_by_ts[groupper] = {ts: count}
                else:
                    stats_by_ts[groupper][ts] = count
        stats = {
            "timestamps": sorted(unique_ts),
            "data": {},
        }
        for name in stats_names:
            stats["data"][name] = []

        for ts in stats["timestamps"]:
            for name in stats_names:
                value = stats_by_ts.get(name, {}).get(ts, 0)
                stats["data"][name].append(value)

        return GraphDataResponse(
            timestamps=stats["timestamps"],
            data=stats["data"],
            total=total,
        )

    @classmethod
    def fetch_data(
        self,
        request: DataRequest,
        timezone,
    ):
        if request.query:
            parser = parse(request.query)
            filter_clause = to_sql(
                parser.root, fields=flyql_clickhouse_fields(request.source._fields)
            )
        else:
            filter_clause = "true"

        order_by_clause = f"ORDER BY {request.source.time_field} DESC"
        raw_where_clause = request.raw_query or "true"

        time_clause = f"{request.source.time_field} BETWEEN fromUnixTimestamp64Milli({request.time_from}) and fromUnixTimestamp64Milli({request.time_to})"
        from_db_table = f"{request.source.connection['database']}.{request.source.connection['table']}"

        fields_names = sorted(request.source._fields.keys())
        fields_to_select = []
        for field in fields_names:
            if field == request.source.time_field:
                time_field_type = convert_to_base_ch(
                    request.source._fields[request.source.time_field].type.lower()
                )
                if time_field_type in ["datetime", "datetime64"]:
                    fields_to_select.append(f"toTimeZone({field}, 'UTC')")
                elif time_field_type in ["timestamp", "uint64", "int64"]:
                    fields_to_select.append(f"toTimeZone(toDateTime({field}), 'UTC')")
            else:
                fields_to_select.append(field)
        fields_to_select = ", ".join(fields_to_select)
        select_query = f"SELECT generateUUIDv4(),{fields_to_select} FROM {from_db_table} WHERE {time_clause} AND {filter_clause} AND {raw_where_clause} {order_by_clause} LIMIT {request.limit}"
        count_query = f"SELECT count() as c FROM {from_db_table} WHERE {time_clause} AND {filter_clause} AND {raw_where_clause}"

        rows = []

        with clickhouse.Client(
            **get_source_database_conn_kwargs(request.source)
        ) as client:
            selected_fields = [request.source._record_pseudo_id_field] + fields_names
            for item in client.execute(select_query):
                rows.append(
                    Row(
                        source=request.source,
                        selected_fields=selected_fields,
                        values=item,
                        timezone=timezone,
                    )
                )
        return DataResponse(rows=rows)
