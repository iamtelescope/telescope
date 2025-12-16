import os
import logging
import tempfile
from typing import Dict

import mysql.connector

from flyql.core.parser import parse, ParserError
from flyql.core.exceptions import FlyqlError
from flyql.generators.starrocks.generator import to_sql, Field

from telescope.models import SourceField

from telescope.fetchers.request import (
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


logger = logging.getLogger("telescope.fetchers.starrocks")


SSL_CERTS_PARAMS = ["ssl_ca", "ssl_cert", "ssl_key"]
OPTIONAL_SSL_PARAMS = ["tls_versions"]

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
        date_clause = f"`{date_field}` BETWEEN date(to_datetime_ntz({time_from}, 3)) and date(to_datetime_ntz({time_to}, 3))  AND "
    return f"{date_clause}`{time_field}` BETWEEN to_datetime_ntz({time_from}, 3) and to_datetime_ntz({time_to}, 3)"


class StarrocksConnect:
    def __init__(self, data: dict):
        self.data = data
        self.temp_dir = None
        self._client = None
        self.client_kwargs = {}

    @property
    def client(self):
        if self._client is None:
            self._client = mysql.connector.connect(
               **self.client_kwargs
            )
        return self._client

    def __enter__(self, *args, **kwargs):
        client_kwargs = {
            "host": self.data["host"],
            "port": self.data["port"],
            "user": self.data["user"],
            "password": self.data["password"],
            "ssl_disabled": not self.data["ssl"],
            "ssl_verify_cert": self.data["verify"],
        }
        for name in OPTIONAL_SSL_PARAMS:
            if self.data.get(name) and self.data[name] != "":
                client_kwargs[name] = self.data[name]

        self.temp_dir = tempfile.TemporaryDirectory()

        for name in SSL_CERTS_PARAMS:
            if self.data.get(name):
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


class ConnectionTestResponseNg:
    def __init__(
        self,
    ):
        self.result = False
        self.error = ""

    def as_dict(self) -> dict:
        return {
            "result": self.result,
            "error": self.error,
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
    def test_connection_ng(cls, data: dict) -> ConnectionTestResponseNg:
        response = ConnectionTestResponseNg()
        with StarrocksConnect(data) as c:
            try:
                cur = c.client.cursor()
                cur.execute("SELECT now()")
            except Exception as err:
                response.error = str(err)
                logger.exception("connection test failed: %s", err)
            else:
                response.result = True
        return response

    @classmethod
    def test_connection(cls, data: dict) -> ConnectionTestResponse:
        response = ConnectionTestResponse()
        target = f"`{data['database']}`.`{data['table']}`"
        with StarrocksConnect(data) as c:
            try:
                cur = c.client.cursor()
                cur.execute(f"SELECT 1 FROM {target} LIMIT 1")
            except Exception as err:
                response.reachability["error"] = str(err)
                response.schema["error"] = "Skipped due to reachability test failed"
            else:
                response.reachability["result"] = True
                try:
                    cur = c.client.cursor()
                    cur.execute(
                        "select name, type from system.columns where database = '%s' and table = '%s'"
                        % (data["database"], data["table"])
                    )
                    row = cur.fetchone()
                except Exception as err:
                    response.schema["error"] = str(err)
                else:
                    assert row
                    response.schema["result"] = True
                    response.schema["data"] = [
                        get_telescope_field(row[0], row[1])
                    ]
                try:
                    cur = c.client.cursor()
                    cur.execute(f"SHOW CREATE TABLE {target}")
                    row = cur.fetchone()
                    assert row
                    response.schema["raw"] = row[0]
                except Exception as err:
                    logger.exception(
                        "failed to get raw table schema (ignoring): %s", err
                    )

        return response

    @classmethod
    def get_schema(cls, data: dict):
        """Get schema without testing connection"""
        result = None
        target = f"`{data['database']}`.`{data['table']}`"
        with StarrocksConnect(data) as c:
            # First validate the table exists - this will throw an error if it doesn't
            cur = c.client.cursor()
            cur.execute(f"SELECT 1 FROM {target} LIMIT 1")
            cur.fetchall()

            # Now get the schema
            cur.execute(
                "select column_name, column_type from information_schema.columns where table_schema = '%s' and table_name = '%s'"
                % (data["database"], data["table"])
            )
            result = cur.fetchall()
        return [get_telescope_field(x[0], x[1]) for x in result]

    @classmethod
    def autocomplete(cls, source, field, time_from, time_to, value):
        incomplete = False
        from_db_table = f"{source.data['database']}.{source.data['table']}"
        time_clause = build_time_clause(
            source.time_field, source.date_field, time_from, time_to
        )
        query = f"SELECT DISTINCT {field} FROM {from_db_table} WHERE {time_clause} and {field} LIKE %(value)s ORDER BY {field} LIMIT 500"

        if source.data.get("settings"):
            query += f" SETTINGS {source.data['settings']}"

        with StarrocksConnect(source.conn.data) as c:
            cur = c.client.cursor()
            cur.execute(query, {"value": f"%{value}%"})
            result = cur.fetchall()
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
                group_by_value = f"`{group_by.root_name}`"

        total = 0
        time_clause = build_time_clause(
            request.source.time_field,
            request.source.date_field,
            request.time_from,
            request.time_to,
        )
        from_db_table = (
            f"{request.source.data['database']}.{request.source.data['table']}"
        )

        time_field_type = convert_to_base_ch(
            request.source._fields[request.source.time_field].type.lower()
        )
        to_time_zone = ""
        # TODO: Understand what timezone handling is required
        # if time_field_type in ["datetime", "datetime64"]:
        #     to_time_zone = f"toTimeZone({request.source.time_field}, 'UTC')"
        # elif time_field_type in ["timestamp", "uint64", "int64"]:
        #     to_time_zone = f"toTimeZone(to_datetime_ntz({request.source.time_field}, 3), 'UTC')"
        if time_field_type in ["datetime", "datetime64"]:
            to_time_zone = f"`{request.source.time_field}`"
        elif time_field_type in ["timestamp", "uint64", "int64"]:
            to_time_zone = f"toTimeZone(to_datetime_ntz({request.source.time_field}, 3), 'UTC')"

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
            stats_time_selector = f"unix_timestamp(time_slice({to_time_zone}, INTERVAL {stats_interval_seconds} SECOND)) * 1000"
        else:
            if time_field_type in ["datetime", "timestamp", "uint64"]:
                stats_time_selector = f"unix_timestamp({to_time_zone})*1000"
            elif time_field_type == "datetime64":
                stats_time_selector = f"unix_timestamp({to_time_zone})"

        with StarrocksConnect(request.source.conn.data) as c:
            stat_sql = f"SELECT {stats_time_selector} as t, COUNT() as Count"
            if group_by_value:
                stat_sql += f", {group_by_value} as `{group_by.name}`"
            stat_sql += f" FROM {from_db_table} WHERE {time_clause} AND {filter_clause} AND {raw_where_clause} GROUP BY t"
            if group_by_value:
                stat_sql += f", `{group_by.name}`"
            stat_sql += " ORDER BY t"

            if request.source.data.get("settings"):
                stat_sql += f" SETTINGS {request.source.data['settings']}"

            cur = c.client.cursor()
            print(stat_sql)
            cur.execute(stat_sql)
            for item in cur.fetchall():
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
        tz,
    ):
        if request.query:
            parser = parse(request.query)
            filter_clause = to_sql(
                parser.root, fields=flyql_clickhouse_fields(request.source._fields)
            )
        else:
            filter_clause = "true"

        order_by_clause = f"ORDER BY `{request.source.time_field}` DESC"
        raw_where_clause = request.raw_query or "true"

        time_clause = build_time_clause(
            request.source.time_field,
            request.source.date_field,
            request.time_from,
            request.time_to,
        )
        from_db_table = (
            f"{request.source.data['database']}.{request.source.data['table']}"
        )

        fields_names = sorted(request.source._fields.keys())
        fields_to_select = []
        for field in fields_names:
            # TODO: Understand what timezone handling is required
            # if field == request.source.time_field:
            #     time_field_type = convert_to_base_ch(
            #         request.source._fields[request.source.time_field].type.lower()
            #     )
            #     if time_field_type in ["datetime", "datetime64"]:
            #         fields_to_select.append(f"toTimeZone({field}, 'UTC')")
            #     elif time_field_type in ["timestamp", "uint64", "int64"]:
            #         fields_to_select.append(f"toTimeZone(toDateTime({field}), 'UTC')")
            # else:
                fields_to_select.append(f'`{field}`')
        fields_to_select = ", ".join(fields_to_select)

        settings_clause = ""
        if request.source.data.get("settings"):
            settings_clause = f" SETTINGS {request.source.data['settings']}"

        select_query = f"SELECT uuid_numeric(),{fields_to_select} FROM {from_db_table} WHERE {time_clause} AND {filter_clause} AND {raw_where_clause} {order_by_clause} LIMIT {request.limit}{settings_clause}"

        rows = []

        with StarrocksConnect(request.source.conn.data) as c:
            selected_fields = [request.source._record_pseudo_id_field] + fields_names
            cur = c.client.cursor()
            cur.execute(select_query)
            for item in cur.fetchall():
                rows.append(
                    Row(
                        source=request.source,
                        selected_fields=selected_fields,
                        values=item,
                        tz=tz,
                    )
                )
        return DataResponse(rows=rows)
