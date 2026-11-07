import csv
import os
import logging
import tempfile
from typing import Any, Dict, Optional
import zoneinfo
from datetime import datetime

import mysql.connector

from flyql import parse, ParserError, FlyqlError
from flyql.generators.starrocks import Column, to_sql_where

from telescope.constants import UTC_ZONE, CHART_QUERY_TIMEOUT_SECONDS
from telescope.columns import ParsedColumn
from telescope.flyql_errors import format_flyql_error
from telescope.flyql_registry import transformer_registry
from telescope.models import Source, SourceColumn

from telescope.fetchers.request import (
    DataRequest,
    GraphDataRequest,
    ChartDataRequest,
)
from telescope.fetchers.response import (
    AutocompleteResponse,
    DataResponse,
    GraphDataResponse,
    ChartDataResponse,
)
from telescope.fetchers.fetcher import BaseFetcher
from telescope.fetchers.chart import ChartPlan, agg_expression, quote_column
from telescope.fetchers.models import Row
from telescope.fetchers.search import body_column, next_cursor

from telescope.utils import convert_to_base_sr, get_telescope_column

logger = logging.getLogger("telescope.fetchers.starrocks")

CHART_AGGS = {
    "count": "count(*)",
    "sum": "sum({c})",
    "avg": "avg({c})",
    "min": "min({c})",
    "max": "max({c})",
    "quantile": "percentile_approx({c}, {l})",
    "uniq": "approx_count_distinct({c})",
}


SSL_CERTS_PARAMS = {
    "ca_cert": "ssl_ca",
    "client_cert": "ssl_cert",
    "client_cert_key": "ssl_key",
}
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


def build_group_by_value(group_by: ParsedColumn) -> str:
    # If the name is the root name, ignore the presence of dots as we
    # should assume the intent is to group by the identified column rather
    # than a nested field.
    if "." in group_by.name and group_by.root_name != group_by.name:
        # Use the csv module to split respecting quotes
        spl = list(csv.reader([group_by.name], delimiter=".", quotechar="'"))[0]
        if group_by.is_map():
            map_keys = "][".join(escape_param(x) for x in spl[1:])
            return f"{group_by.root_name}[{map_keys}]"
        elif group_by.is_array():
            array_index = int(".".join(spl[1]))
            return f"{group_by.root_name}[{array_index}]"
        elif group_by.is_json():
            json_path = spl[1:]
            # Starrocks documents that you double quote any json path elements
            # that contain dots. Let's just do it unconditionally.
            json_path = [f'"{x}"' for x in json_path]
            json_path_str = "->".join([escape_param(x) for x in json_path])
            return f"cast(`{group_by.root_name}`->{json_path_str} as string)"
        elif group_by.jsonstring:
            json_path = spl[1:]
            # Starrocks documents that you double quote any json path elements
            # that contain dots. Let's just do it unconditionally.
            json_path = [f'"{x}"' for x in json_path]
            json_path_str = "->".join([escape_param(x) for x in json_path])
            return (
                f"cast(parse_json(`{group_by.root_name}`)->{json_path_str} as string)"
            )
        else:
            raise ValueError
    return f"`{group_by.root_name}`"


class StarrocksConnect:
    def __init__(self, data: dict):
        self.data = data
        self.temp_dir = None
        self._client = None
        self.client_kwargs = {}

    @property
    def client(self):
        if self._client is None:
            self._client = mysql.connector.connect(**self.client_kwargs)
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


def starrocks_cursor_time(value) -> str:
    """A row time as a literal StarRocks compares back to the time column exactly."""
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d %H:%M:%S.%f")
    return str(value)


def starrocks_row_hash(source: Source) -> str:
    """Orders rows sharing a timestamp by a hash of their scalar columns."""
    parts = [
        f"CAST(`{name}` AS STRING)"
        for name in sorted(source._columns.keys())
        if not source._columns[name]
        .type.lower()
        .startswith(("array", "map", "struct", "json", "bitmap", "hll"))
    ]
    return f"murmur_hash3_32(concat_ws('|', {', '.join(parts)}))"


def flyql_starrocks_columns(source_columns: Dict[str, SourceColumn]):
    return {
        column.name: Column(
            name=column.name,
            _type="jsonstring" if column.jsonstring else column.type,
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
            return False, format_flyql_error(query, err)
        else:
            try:
                assert parser.root
                to_sql_where(
                    parser.root,
                    columns=flyql_starrocks_columns(source._columns),
                    registry=transformer_registry(),
                )
            except FlyqlError as err:
                return False, format_flyql_error(query, err)

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
                    response.schema["data"] = [get_telescope_column(row[0], row[1])]
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
    def autocomplete(
        cls, source: Source, column: str, time_from, time_to, value: str
    ) -> AutocompleteResponse:
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
            filter_clause = to_sql_where(
                parser.root,
                columns=flyql_starrocks_columns(request.source._columns),
                registry=transformer_registry(),
            )
        else:
            filter_clause = "true"

        raw_where_clause = request.raw_query or "true"

        group_by = request.group_by[0] if request.group_by else None
        group_by_value = build_group_by_value(group_by) if group_by else ""

        total = 0
        time_clause = build_time_clause(
            request.source.time_column,
            request.source.date_column,
            request.time_from,
            request.time_to,
        )
        from_db_table = f"{request.source.data['catalog']}.{request.source.data['database']}.{request.source.data['table']}"

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
            to_time_zone = (
                f"toTimeZone(to_datetime_ntz({request.source.time_column}, 3), 'UTC')"
            )

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

            stat_sql = (
                f"SELECT {query_hints} {stats_time_selector} as t, COUNT() as Count"
            )
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
        source = request.source
        if request.query:
            parser = parse(request.query)
            assert parser.root
            filter_clause = to_sql_where(
                parser.root,
                columns=flyql_starrocks_columns(source._columns),
                registry=transformer_registry(),
            )
        else:
            filter_clause = "true"

        raw_where_clause = request.raw_query or "true"
        where = [filter_clause, raw_where_clause]
        if request.text:
            column = body_column(source)
            if not column:
                raise ValueError("source has no body column for text search")
            # mysql.connector interpolates client side, so the text is an escaped literal.
            where.append(
                f"instr(lower(CAST(`{column}` AS STRING)), lower({escape_param(request.text)})) > 0"
            )

        time_column = f"`{source.time_column}`"
        if source.uniq_column:
            tiebreak = f"CAST(`{source.uniq_column}` AS STRING)"
        else:
            tiebreak = starrocks_row_hash(source)
        offset = 0
        if request.before:
            bound = escape_param(str(request.before["time"]))
            if source.uniq_column:
                uniq = escape_param(str(request.before["uniq"]))
                where.append(
                    f"({time_column} < {bound} OR ({time_column} = {bound} AND {tiebreak} < {uniq}))"
                )
            else:
                where.append(f"{time_column} <= {bound}")
                offset = int(request.before.get("skip") or 0)
        order_by_clause = f"ORDER BY {time_column} DESC, {tiebreak} DESC"

        time_clause = build_time_clause(
            source.time_column,
            source.date_column,
            request.time_from,
            request.time_to,
        )
        where_clause = " AND ".join([time_clause] + where)
        from_db_table = (
            f"{source.data['catalog']}.{source.data['database']}.{source.data['table']}"
        )

        columns_names = sorted(source._columns.keys())
        columns_to_select = [f"`{column}`" for column in columns_names]
        columns_to_select.append(tiebreak if source.uniq_column else "NULL")
        columns_to_select = ", ".join(columns_to_select)

        query_hints = ""
        if source.data.get("settings"):
            query_hints = f"/*+ SET_VAR({source.data['settings']}) */"

        limit_clause = f"LIMIT {request.limit}"
        if offset:
            limit_clause += f" OFFSET {offset}"
        select_query = f"SELECT {query_hints} uuid_numeric(),{columns_to_select} FROM {from_db_table} WHERE {where_clause} {order_by_clause} {limit_clause}"

        rows = []
        keys = []

        assert source.conn
        with StarrocksConnect(source.conn.data) as c:
            selected_columns = [source._record_pseudo_id_column] + columns_names
            time_index = 1 + columns_names.index(source.time_column)
            cur = c.client.cursor()
            cur.execute(select_query)
            for item in cur.fetchall():
                keys.append((starrocks_cursor_time(item[time_index]), item[-1]))
                rows.append(
                    Row(
                        source=source,
                        selected_columns=selected_columns,
                        values=item[:-1],
                        tz=tz or UTC_ZONE,
                    )
                )
        return DataResponse(
            rows=rows,
            cursor=next_cursor(source, keys, request.limit, request.before),
        )

    @classmethod
    def fetch_chart_data(cls, request: ChartDataRequest) -> ChartDataResponse:
        source = request.source
        plan = ChartPlan(request)
        if request.query:
            parser = parse(request.query)
            assert parser.root
            filter_clause = to_sql_where(
                parser.root,
                columns=flyql_starrocks_columns(source._columns),
                registry=transformer_registry(),
            )
        else:
            filter_clause = "true"
        raw_where_clause = request.raw_query or "true"
        time_clause = build_time_clause(
            source.time_column, source.date_column, plan.time_from, plan.query_to
        )
        where = f"{time_clause} AND ({filter_clause}) AND ({raw_where_clause})"
        from_db_table = (
            f"{source.data['catalog']}.{source.data['database']}.{source.data['table']}"
        )
        hint_vars = f"query_timeout={CHART_QUERY_TIMEOUT_SECONDS}"
        if source.data.get("settings"):
            hint_vars += f", {source.data['settings']}"
        select = f"SELECT /*+ SET_VAR({hint_vars}) */"
        aggs = ", ".join(
            f"{agg_expression(CHART_AGGS, source, item)} AS `__telescope_v{i}`"
            for i, item in enumerate(request.series)
        )
        group = ""
        if plan.group_by:
            group = f"ifnull(cast({build_group_by_value(plan.group_by)} as string), '')"

        assert source.conn
        with StarrocksConnect(source.conn.data) as c:

            def run(sql):
                cur = c.client.cursor()
                cur.execute(sql)
                return cur.fetchall()

            if plan.kind == "number" or (plan.kind == "table" and not group):
                rows = run(f"{select} {aggs} FROM {from_db_table} WHERE {where}")
                return plan.number(rows) if plan.kind == "number" else plan.table(rows)
            if plan.kind == "table":
                return plan.table(
                    run(
                        f"{select} {group} AS `__telescope_g`, {aggs} FROM {from_db_table} WHERE {where}"
                        f" GROUP BY `__telescope_g` ORDER BY `__telescope_v0` DESC, `__telescope_g`"
                        f" LIMIT {plan.limit + 1}"
                    )
                )

            time_column = quote_column(source, source.time_column)
            time_type = convert_to_base_sr(
                source._columns[source.time_column].type.lower()
            )
            if time_type in ["timestamp", "uint64", "int64"]:
                time_column = f"to_datetime_ntz({time_column}, 3)"
            step = plan.step_ms // 1000
            # seconds_diff ignores the session time_zone, so buckets stay UTC like the filter.
            epoch = f"seconds_diff({time_column}, '1970-01-01 00:00:00')"
            bucket = f"floor({epoch} / {step}) * {plan.step_ms}"
            if not group:
                return plan.timeseries(
                    run(
                        f"{select} {bucket} AS `__telescope_t`, {aggs} FROM {from_db_table} WHERE {where}"
                        f" GROUP BY `__telescope_t` ORDER BY `__telescope_t`"
                    )
                )
            groups, truncated = plan.top_groups(
                run(
                    f"{select} {group} AS `__telescope_g` FROM {from_db_table} WHERE {where}"
                    f" GROUP BY `__telescope_g` ORDER BY count(*) DESC, `__telescope_g`"
                    f" LIMIT {plan.limit + 1}"
                )
            )
            if not groups:
                return plan.timeseries([], groups, truncated)
            # Values are escaped like the driver does; its %(name)s pass would also hit user literals.
            group_list = ", ".join(escape_param(str(g)) for g in groups)
            rows = run(
                f"{select} {bucket} AS `__telescope_t`, {group} AS `__telescope_g`, {aggs}"
                f" FROM {from_db_table} WHERE {where} AND {group} IN ({group_list})"
                f" GROUP BY `__telescope_t`, `__telescope_g` ORDER BY `__telescope_t`"
            )
            return plan.timeseries(rows, groups, truncated)
