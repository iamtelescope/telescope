import csv
import os
import logging
import tempfile
from typing import Any, Dict, Optional
import zoneinfo

import mysql.connector

from flyql.core.parser import parse, ParserError
from flyql.core.exceptions import FlyqlError
from flyql.generators.starrocks.generator import to_sql, Column

from telescope.constants import UTC_ZONE
from telescope.columns import ParsedColumn
from telescope.models import Source, SourceColumn

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

from telescope.utils import convert_to_base_sr, get_telescope_column


logger = logging.getLogger("telescope.fetchers.starrocks")


SSL_CERTS_PARAMS = {"ca_cert": "ssl_ca", "client_cert": "ssl_cert", "client_cert_key": "ssl_key"}
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


def build_time_clause(time_column, date_column, time_from, time_to):
    date_clause = ""
    if date_column:
        date_clause = f"`{date_column}` BETWEEN date(to_datetime_ntz({time_from}, 3)) and date(to_datetime_ntz({time_to}, 3))  AND "
    return f"{date_clause}`{time_column}` BETWEEN to_datetime_ntz({time_from}, 3) and to_datetime_ntz({time_to}, 3)"


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
        for config in OPTIONAL_SSL_PARAMS:
            if self.data.get(config) and self.data[config] != "":
                client_kwargs[config] = self.data[config]

        self.temp_dir = tempfile.TemporaryDirectory()

        for config, key in SSL_CERTS_PARAMS.items():
            if self.data.get(config):
                path = os.path.join(self.temp_dir.name, f"{config}.pem")
                with open(path, "w") as fd:
                    fd.write(self.data[config])
                client_kwargs[key] = path
        self.client_kwargs = client_kwargs
        return self

    def __exit__(self, *args, **kwargs):
        try:
            if self.temp_dir:
                self.temp_dir.cleanup()
        except Exception as err:
            logger.exception("error while tempdir cleanup (ignoring): %s", err)


def flyql_starrocks_columns(source_columns: Dict[str, SourceColumn]):
    return {
        column.name: Column(
            name=column.name,
            jsonstring=column.jsonstring,
            _type=column.type,
            values=column.values,
        )
        for _, column in source_columns.items()
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
    def validate_query(cls, source: Source, query: str) -> tuple[bool, Optional[str]]:
        if not query:
            return True, None

        try:
            parser = parse(query)
        except ParserError as err:
            return False, err.message
        else:
            try:
                assert parser.root
                to_sql(parser.root, columns=flyql_starrocks_columns(source._columns))
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
                        get_telescope_column(row[0], row[1])
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
    def get_schema(cls, data: dict) -> list[dict[str, Any]]:
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
        return [get_telescope_column(x[0], x[1]) for x in result]

    @classmethod
    def autocomplete(cls, source: Source, column: str, time_from, time_to, value: str) -> AutocompleteResponse:
        incomplete = False
        from_db_table = f"{source.data['database']}.{source.data['table']}"
        time_clause = build_time_clause(
            source.time_column, source.date_column, time_from, time_to
        )
        query_hints = ""
        if source.data.get("settings"):
            query_hints = f"/*+ SET_VAR({source.data['settings']}) */"
        query = f"SELECT {query_hints} DISTINCT `{column}` FROM {from_db_table} WHERE {time_clause} and CAST(`{column}` AS STRING) LIKE %(value)s ORDER BY `{column}` LIMIT 500"

        assert source.conn
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
    ) -> GraphDataResponse:
        if request.query:
            parser = parse(request.query)
            assert parser.root
            filter_clause = to_sql(
                parser.root, columns=flyql_starrocks_columns(request.source._columns)
            )
        else:
            filter_clause = "true"

        raw_where_clause = request.raw_query or "true"

        group_by_value = ""
        group_by = request.group_by[0] if request.group_by else None
        if group_by:
            assert isinstance(group_by, ParsedColumn)
            # If the name is the root name, ignore the presence of dots as we
            # should assume the intent is to group by the identified column rather
            # than a nested field.
            if "." in group_by.name and group_by.root_name != group_by.name:
                # Use the csv module to split respecting quotes
                spl = list(csv.reader([group_by.name], delimiter=".", quotechar="'"))[0]
                if group_by.is_map():
                    map_key = "']['".join(spl[1:])
                    group_by_value = f"{group_by.root_name}['{map_key}']"
                elif group_by.is_array():
                    array_index = int(".".join(spl[1]))
                    group_by_value = f"{group_by.root_name}[{array_index}]"
                elif group_by.is_json():
                    json_path = spl[1:]
                    # Starrocks documents that you double quote any json path elements
                    # that contain dots. Let's just do it unconditionally.
                    json_path = [f'"{x}"' for x in json_path]
                    json_path_str = "->".join([escape_param(x) for x in json_path])
                    group_by_value = (
                        f"cast(`{group_by.root_name}`->{json_path_str} as string)"
                    )
                elif group_by.jsonstring:
                    json_path = spl[1:]
                    # Starrocks documents that you double quote any json path elements
                    # that contain dots. Let's just do it unconditionally.
                    json_path = [f'"{x}"' for x in json_path]
                    json_path_str = "->".join([escape_param(x) for x in json_path])
                    group_by_value = (
                        f"cast(parse_json(`{group_by.root_name}`)->{json_path_str} as string)"
                    )
                else:
                    raise ValueError
            else:
                group_by_value = f"`{group_by.root_name}`"

        total = 0
        time_clause = build_time_clause(
            request.source.time_column,
            request.source.date_column,
            request.time_from,
            request.time_to,
        )
        from_db_table = (
            f"{request.source.data['catalog']}.{request.source.data['database']}.{request.source.data['table']}"
        )

        time_column_type = convert_to_base_sr(
            request.source._columns[request.source.time_column].type.lower()
        )
        to_time_zone = ""
        # TODO: Understand what timezone handling is required
        # if time_column_type in ["datetime", "datetime64"]:
        #     to_time_zone = f"toTimeZone({request.source.time_column}, 'UTC')"
        # elif time_column_type in ["timestamp", "uint64", "int64"]:
        #     to_time_zone = f"toTimeZone(to_datetime_ntz({request.source.time_column}, 3), 'UTC')"
        if time_column_type in ["datetime", "datetime64"]:
            to_time_zone = f"`{request.source.time_column}`"
        elif time_column_type in ["timestamp", "uint64", "int64"]:
            to_time_zone = f"toTimeZone(to_datetime_ntz({request.source.time_column}, 3), 'UTC')"

        columns_names = sorted(request.source._columns.keys())
        columns_to_select = []
        for column in columns_names:
            if column == request.source.time_column:
                columns_to_select.append(to_time_zone)
            else:
                columns_to_select.append(column)

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
            if time_column_type in ["datetime", "timestamp", "uint64"]:
                stats_time_selector = f"unix_timestamp({to_time_zone})*1000"
            elif time_column_type == "datetime64":
                stats_time_selector = f"unix_timestamp({to_time_zone})"

        assert request.source.conn
        with StarrocksConnect(request.source.conn.data) as c:
            query_hints = ""
            if request.source.data.get("settings"):
                query_hints = f"/*+ SET_VAR({request.source.data['settings']}) */"

            stat_sql = f"SELECT {query_hints} {stats_time_selector} as t, COUNT() as Count"
            if group_by_value:
                assert group_by
                stat_sql += f", {group_by_value} as `{group_by.name}`"
            stat_sql += f" FROM {from_db_table} WHERE {time_clause} AND {filter_clause} AND {raw_where_clause} GROUP BY t"
            if group_by_value:
                assert group_by
                stat_sql += f", `{group_by.name}`"
            stat_sql += " ORDER BY t"

            cur = c.client.cursor()
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
        cls,
        request: DataRequest,
        tz: Optional[zoneinfo.ZoneInfo] = None,
    ):
        if request.query:
            parser = parse(request.query)
            assert parser.root
            filter_clause = to_sql(
                parser.root, columns=flyql_starrocks_columns(request.source._columns)
            )
        else:
            filter_clause = "true"

        order_by_clause = f"ORDER BY `{request.source.time_column}` DESC"
        raw_where_clause = request.raw_query or "true"

        time_clause = build_time_clause(
            request.source.time_column,
            request.source.date_column,
            request.time_from,
            request.time_to,
        )
        from_db_table = (
            f"{request.source.data['catalog']}.{request.source.data['database']}.{request.source.data['table']}"
        )

        columns_names = sorted(request.source._columns.keys())
        columns_to_select = []
        for column in columns_names:
            # TODO: Understand what timezone handling is required
            # if column == request.source.time_column:
            #     time_column_type = convert_to_base_sr(
            #         request.source._columns[request.source.time_column].type.lower()
            #     )
            #     if time_column_type in ["datetime", "datetime64"]:
            #         columns_to_select.append(f"toTimeZone({column}, 'UTC')")
            #     elif time_column_type in ["timestamp", "uint64", "int64"]:
            #         columns_to_select.append(f"toTimeZone(toDateTime({column}), 'UTC')")
            # else:
                columns_to_select.append(f'`{column}`')
        columns_to_select = ", ".join(columns_to_select)

        query_hints = ""
        if request.source.data.get("settings"):
            query_hints = f"/*+ SET_VAR({request.source.data['settings']}) */"

        select_query = f"SELECT {query_hints} uuid_numeric(),{columns_to_select} FROM {from_db_table} WHERE {time_clause} AND {filter_clause} AND {raw_where_clause} {order_by_clause} LIMIT {request.limit}"

        rows = []

        assert request.source.conn
        with StarrocksConnect(request.source.conn.data) as c:
            selected_columns = [request.source._record_pseudo_id_column] + columns_names
            cur = c.client.cursor()
            cur.execute(select_query)
            for item in cur.fetchall():
                rows.append(
                    Row(
                        source=request.source,
                        selected_columns=selected_columns,
                        values=item,
                        tz=tz or UTC_ZONE,
                    )
                )
        return DataResponse(rows=rows)
