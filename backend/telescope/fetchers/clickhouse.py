import os
import logging
import tempfile
from typing import Dict

import clickhouse_connect

from flyql.core.parser import parse, ParserError
from flyql.core.exceptions import FlyqlError
from flyql.generators.clickhouse.generator import to_sql, Field

from telescope.models import SourceField

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


logger = logging.getLogger("telescope.fetchers.clickhouse")


SSL_CERTS_PARAMS = ["ca_certs", "certfile", "keyfile"]
OPTIONAL_SSL_PARAMS = ["ssl_version", "ciphers", "server_hostname", "alt_hosts"]

ESCAPE_CHARS_MAP = {
    "\b": "\\b",
    "\f": "\\f",
    "\r": "\\r",
    "\n": "\\n",
    "\t": "\\t",
    "\0": "\\0",
    "\a": "\\a",
    "\v": "\\v",
    "\\": "\\\\",
    "'": "\\'",
}


def escape_param(item: str) -> str:
    if item is None:
        return "NULL"
    elif isinstance(item, str):
        return "'%s'" % "".join(ESCAPE_CHARS_MAP.get(c, c) for c in item)
    else:
        return item


def build_time_clause(time_field, date_field, time_from, time_to):
    date_clause = ""
    if date_field:
        date_clause = f"{date_field} BETWEEN toDate(fromUnixTimestamp64Milli({time_from})) and toDate(fromUnixTimestamp64Milli({time_to})) AND "
    return f"{date_clause}{time_field} BETWEEN fromUnixTimestamp64Milli({time_from}) and fromUnixTimestamp64Milli({time_to})"


class ClickhouseConnect:
    def __init__(self, data: dict):
        self.data = data
        self.temp_dir = None
        self._client = None
        self.client_kwargs = {}

    @property
    def client(self):
        if self._client is None:
            self._client = clickhouse_connect.get_client(
                apply_server_timezone=False, **self.client_kwargs
            )
        return self._client

    def __enter__(self, *args, **kwargs):
        client_kwargs = {
            "host": self.data["host"],
            "port": self.data["port"],
            "user": self.data["user"],
            "password": self.data["password"],
            "secure": self.data["ssl"],
            "verify": self.data["verify"],
        }
        for name in OPTIONAL_SSL_PARAMS:
            if self.data[name] != "":
                client_kwargs[name] = self.data[name]

        self.temp_dir = tempfile.TemporaryDirectory()

        for name in SSL_CERTS_PARAMS:
            if self.data[name]:
                path = os.path.join(self.temp_dir.name, f"{name}.pem")
                with open(path, "w") as fd:
                    fd.write(self.data[name])
                client_kwargs[name] = path
        self.client_kwargs = client_kwargs
        return self

    def __exit__(self, *args, **kwargs):
        try:
            if self.temp_dir:
                self.temp_dir.cleanup()
        except Exception as err:
            logger.exception("error while tempdir cleanup (ignoring): %s", err)


def flyql_clickhouse_fields(source_fields: Dict[str, SourceField]):
    return {
        field.name: Field(
            name=field.name,
            jsonstring=field.jsonstring,
            _type=field.type,
            values=field.values,
        )
        for _, field in source_fields.items()
    }


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
            "raw": "",
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
        with ClickhouseConnect(data) as c:
            try:
                c.client.query(f"SELECT 1 FROM {target} LIMIT 1")
            except Exception as err:
                response.reachability["error"] = str(err)
                response.schema["error"] = "Skipped due to reachability test failed"
            else:
                response.reachability["result"] = True
                try:
                    result = c.client.query(
                        "select name, type from system.columns where database = '%s' and table = '%s'"
                        % (data["database"], data["table"])
                    )
                except Exception as err:
                    response.schema["error"] = str(err)
                else:
                    response.schema["result"] = True
                    response.schema["data"] = [
                        get_telescope_field(x[0], x[1]) for x in result.result_rows
                    ]
                try:
                    result = c.client.query(f"SHOW CREATE TABLE {target}")
                    response.schema["raw"] = result.result_rows[0][0]
                except Exception as err:
                    logger.exception(
                        "failed to get raw table schema (ignoring): %s", err
                    )

        return response

    @classmethod
    def autocomplete(cls, source, field, time_from, time_to, value):
        incomplete = False
        from_db_table = f"{source.connection['database']}.{source.connection['table']}"
        time_clause = build_time_clause(
            source.time_field, source.date_field, time_from, time_to
        )
        query = f"SELECT DISTINCT {field} FROM {from_db_table} WHERE {time_clause} and {field} LIKE %(value)s ORDER BY {field} LIMIT 500"
        with ClickhouseConnect(source.connection) as c:
            result = c.client.query(query, {"value": f"%{value}%"})
            items = [str(x[0]) for x in result.result_rows]
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

        raw_where_clause = request.raw_query or "true"

        group_by_value = ""
        group_by = request.group_by[0] if request.group_by else None
        if group_by:
            if ":" in group_by.name:
                spl = group_by.name.split(":")
                if group_by.jsonstring:
                    json_path = spl[1:]
                    json_path = ", ".join([escape_param(x) for x in json_path])
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
        time_clause = build_time_clause(
            request.source.time_field,
            request.source.date_field,
            request.time_from,
            request.time_to,
        )
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

        with ClickhouseConnect(request.source.connection) as c:
            stat_sql = f"SELECT {stats_time_selector} as t, COUNT() as Count"
            if group_by_value:
                stat_sql += f", {group_by_value} as `{group_by.name}`"
            stat_sql += f" FROM {from_db_table} WHERE {time_clause} AND {filter_clause} AND {raw_where_clause} GROUP BY t"
            if group_by_value:
                stat_sql += f", `{group_by.name}`"
            stat_sql += " ORDER BY t"
            for item in c.client.query(stat_sql).result_rows:
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

        time_clause = build_time_clause(
            request.source.time_field,
            request.source.date_field,
            request.time_from,
            request.time_to,
        )
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

        rows = []

        with ClickhouseConnect(request.source.connection) as c:
            selected_fields = [request.source._record_pseudo_id_field] + fields_names
            for item in c.client.query(select_query).result_rows:
                rows.append(
                    Row(
                        source=request.source,
                        selected_fields=selected_fields,
                        values=item,
                        timezone=timezone,
                    )
                )
        return DataResponse(rows=rows)
