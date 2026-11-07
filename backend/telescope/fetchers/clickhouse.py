import os
import re
import logging
import tempfile
from typing import Dict, Optional
import zoneinfo

import clickhouse_connect

from flyql import parse, ParserError, FlyqlError
from flyql.generators.clickhouse import Column, to_sql_where

from telescope.constants import UTC_ZONE, CHART_QUERY_TIMEOUT_SECONDS
from telescope.flyql_errors import format_flyql_error
from telescope.flyql_registry import transformer_registry

from telescope.models import SourceColumn

from telescope.fetchers.request import (
    AutocompleteRequest,
    DataRequest,
    GraphDataRequest,
    ChartDataRequest,
)
from telescope.fetchers.response import (
    AutocompleteResponse,
    DataResponse,
    GraphDataResponse,
    JsonKeyEntry,
    JsonKeysResponse,
    ChartDataResponse,
)
from telescope.fetchers.fetcher import BaseFetcher
from telescope.fetchers.chart import (
    ChartPlan,
    agg_expression,
    quote_column,
    with_formulas,
)
from telescope.fetchers.models import Row
from telescope.fetchers.search import body_column, next_cursor

from telescope.utils import convert_to_base_ch, get_telescope_column

logger = logging.getLogger("telescope.fetchers.clickhouse")

CHART_AGGS = {
    "count": "count()",
    "sum": "sum({c})",
    "avg": "avgOrNull({c})",
    "min": "minOrNull({c})",
    "max": "maxOrNull({c})",
    "quantile": "quantileOrNull({l})({c})",
    "uniq": "uniq({c})",
    "last_value": "argMaxOrNull({c}, {t})",
    "any": "anyOrNull({c})",
    # With a per-series condition (the If combinator).
    "count_if": "countIf({w})",
    "sum_if": "sumIf({c}, {w})",
    "avg_if": "avgOrNullIf({c}, {w})",
    "min_if": "minOrNullIf({c}, {w})",
    "max_if": "maxOrNullIf({c}, {w})",
    "quantile_if": "quantileOrNullIf({l})({c}, {w})",
    "uniq_if": "uniqIf({c}, {w})",
    "last_value_if": "argMaxOrNullIf({c}, {t}, {w})",
    "any_if": "anyOrNullIf({c}, {w})",
}


SSL_CERTS_PARAMS = ["ca_cert", "client_cert", "client_cert_key"]
OPTIONAL_SSL_PARAMS = ["server_host_name", "tls_mode"]

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


def _client_query(client, sql, **kw):
    # Every ClickHouse query goes through here; the hook for query attribution.
    return client.query(sql, **kw)


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
        date_clause = f"{date_column} BETWEEN toDate(fromUnixTimestamp64Milli({time_from})) and toDate(fromUnixTimestamp64Milli({time_to})) AND "
    return f"{date_clause}`{time_column}` BETWEEN fromUnixTimestamp64Milli({time_from}) and fromUnixTimestamp64Milli({time_to})"


def build_group_by_value(group_by) -> str:
    if "." in group_by.name:
        spl = group_by.name.split(".")
        if group_by.jsonstring:
            json_path = spl[1:]
            json_path = ", ".join([escape_param(x) for x in json_path])
            return f"JSONExtractString({group_by.root_name}, {json_path})"
        elif group_by.is_map():
            map_key = ".".join(spl[1:])
            return f"{group_by.root_name}[{escape_param(map_key)}]"
        elif group_by.is_array():
            array_index = int(".".join(spl[1]))
            return f"{group_by.root_name}[{array_index}]"
        else:
            raise ValueError
    return f"toString({group_by.root_name})"


# Per time column type: the Int64 cursor value of a row, and the column-typed bound for a cursor parameter.
CURSOR_EXPRESSIONS = {
    "datetime64": ("toUnixTimestamp64Nano({c})", "fromUnixTimestamp64Nano({p})"),
    "datetime": ("toInt64(toUnixTimestamp({c}))", "toDateTime({p})"),
    "int64": ("toInt64({c})", "{p}"),
}

STRING_TYPE_RE = re.compile(
    r"((lowcardinality|nullable)\()*(string|fixedstring\(\d+\))\)*"
)
UNHASHABLE_TYPES = ("json", "object", "dynamic", "variant")


def cursor_ms(time_column_type: str, value: int) -> Optional[int]:
    """The cursor as an inclusive upper time bound in ms, when the column type allows it."""
    if time_column_type == "datetime64":
        return -(-value // 1_000_000)
    if time_column_type == "datetime":
        return value * 1000
    return None


def row_tiebreak(source) -> str:
    """Orders rows sharing a timestamp: the uniq column, else a hash of the whole row."""
    if source.uniq_column:
        return f"toString(`{source.uniq_column}`)"
    parts = []
    for name in sorted(source._columns.keys()):
        if any(t in source._columns[name].type.lower() for t in UNHASHABLE_TYPES):
            parts.append(f"toString(`{name}`)")
        else:
            parts.append(f"`{name}`")
    return f"cityHash64({', '.join(parts)})"


def text_clause(source, text: str, params: dict) -> Optional[str]:
    """Case-insensitive substring match of bare text on the body column, bound as a parameter."""
    if not text:
        return None
    column = body_column(source)
    if not column:
        raise ValueError("source has no body column for text search")
    params["telescope_text"] = text
    expr = f"`{column}`"
    if not STRING_TYPE_RE.fullmatch(source._columns[column].type.lower()):
        expr = f"toString({expr})"
    return f"positionCaseInsensitiveUTF8({expr}, {{telescope_text:String}}) > 0"


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


def _clickhouse_jsontype_to_flyql(ch_types):
    """Map the set of ClickHouse JSONType() outputs observed at a key to a
    single flyql display type. Mixed types fall back to 'unknown'."""
    if not ch_types:
        return "unknown"
    mapping = {
        "Object": "object",
        "Array": "array",
        "String": "string",
        "Bool": "bool",
        "Int64": "int",
        "UInt64": "int",
        "Double": "float",
        "Null": "unknown",
    }
    flyql_types = {mapping.get(t, "unknown") for t in ch_types if t != "Null"}
    if len(flyql_types) == 1:
        return next(iter(flyql_types))
    return "unknown"


def flyql_clickhouse_columns(source_columns: Dict[str, SourceColumn]):
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
    def validate_query(cls, source, query):
        if not query:
            return True, None

        try:
            parser = parse(query)
        except ParserError as err:
            return False, format_flyql_error(query, err)
        else:
            try:
                to_sql_where(
                    parser.root,
                    columns=flyql_clickhouse_columns(source._columns),
                    registry=transformer_registry(),
                )
            except FlyqlError as err:
                return False, format_flyql_error(query, err)

        return True, None

    @classmethod
    def test_connection_ng(cls, data: dict) -> ConnectionTestResponseNg:
        response = ConnectionTestResponseNg()
        with ClickhouseConnect(data) as c:
            try:
                _client_query(c.client, "SELECT now()")
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
        with ClickhouseConnect(data) as c:
            try:
                _client_query(c.client, f"SELECT 1 FROM {target} LIMIT 1")
            except Exception as err:
                response.reachability["error"] = str(err)
                response.schema["error"] = "Skipped due to reachability test failed"
            else:
                response.reachability["result"] = True
                try:
                    result = _client_query(
                        c.client,
                        "select name, type from system.columns where database = %(database)s and table = %(table)s",
                        parameters={
                            "database": data["database"],
                            "table": data["table"],
                        },
                    )
                except Exception as err:
                    response.schema["error"] = str(err)
                else:
                    response.schema["result"] = True
                    response.schema["data"] = [
                        get_telescope_column(x[0], x[1]) for x in result.result_rows
                    ]
                try:
                    result = _client_query(c.client, f"SHOW CREATE TABLE {target}")
                    response.schema["raw"] = result.result_rows[0][0]
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
        with ClickhouseConnect(data) as c:
            # First validate the table exists - this will throw an error if it doesn't
            _client_query(c.client, f"SELECT 1 FROM {target} LIMIT 1")

            # Now get the schema
            result = _client_query(
                c.client,
                "select name, type from system.columns where database = %(database)s and table = %(table)s",
                parameters={"database": data["database"], "table": data["table"]},
            )
        return [get_telescope_column(x[0], x[1]) for x in result.result_rows]

    @classmethod
    def discover_json_keys(cls, source, column, segments, time_from, time_to):
        if column not in source._columns:
            raise ValueError(f"Invalid column: {column!r}")
        source_column = source._columns[column]
        col_type = (source_column.type or "").lower()
        is_jsonstring = source_column.jsonstring or col_type == "jsonstring"
        is_json = "json" in col_type and not is_jsonstring
        is_map = "map(" in col_type

        from_db_table = f"{source.data['database']}.{source.data['table']}"
        time_clause = build_time_clause(
            source.time_column, source.date_column, time_from, time_to
        )
        settings_clause = (
            f" SETTINGS {source.data['settings']}"
            if source.data.get("settings")
            else ""
        )

        if is_jsonstring or is_json:
            # `JSONExtractKeysAndValuesRaw` returns Array(Tuple(String, String));
            # variadic path args dive into nested objects. We aggregate over a
            # recent sample (ordered by time DESC) so the editor reflects what
            # the user is currently looking at, not the full table.
            path_params = {f"path_{i}": seg for i, seg in enumerate(segments[1:])}
            path_args_sql = "".join(
                f", {{path_{i}:String}}" for i in range(len(segments) - 1)
            )
            non_empty_clause = (
                f" AND `{column}` != '' AND isValidJSON(`{column}`)"
                if is_jsonstring
                else ""
            )
            sql = (
                f"WITH sample AS ("
                f"  SELECT JSONExtractKeysAndValuesRaw(`{column}`{path_args_sql}) AS kv"
                f"  FROM {from_db_table}"
                f"  WHERE {time_clause}{non_empty_clause}"
                f"  ORDER BY `{source.time_column}` DESC"
                f"  LIMIT 1000"
                f") "
                f"SELECT pair.1 AS key, groupUniqArray(JSONType(pair.2)) AS types "
                f"FROM sample ARRAY JOIN kv AS pair "
                f"GROUP BY key ORDER BY key LIMIT 200"
            ) + settings_clause
            with ClickhouseConnect(source.conn.data) as c:
                result = _client_query(c.client, sql, parameters=path_params)
                entries = []
                for row in result.result_rows:
                    key, types = row[0], row[1] or []
                    ch_types = [str(t) for t in types]
                    has_children = any(t == "Object" for t in ch_types)
                    entries.append(
                        JsonKeyEntry(
                            name=str(key),
                            type=_clickhouse_jsontype_to_flyql(ch_types),
                            has_children=has_children,
                        )
                    )
            return JsonKeysResponse(keys=entries)

        if is_map:
            # Map(K, V) is flat; `mapKeys()` returns Array(K). We only support
            # discovery at the root level — nested maps would require recursing
            # the value type, which is uncommon. Deeper segments return empty.
            if len(segments) > 1:
                return JsonKeysResponse(keys=[])
            sql = (
                f"SELECT k, COUNT() AS cnt FROM ("
                f"  SELECT arrayJoin(mapKeys(`{column}`)) AS k"
                f"  FROM {from_db_table}"
                f"  WHERE {time_clause}"
                f"  ORDER BY `{source.time_column}` DESC"
                f"  LIMIT 1000"
                f") GROUP BY k ORDER BY cnt DESC LIMIT 200"
            ) + settings_clause
            with ClickhouseConnect(source.conn.data) as c:
                result = _client_query(c.client, sql)
                entries = [
                    JsonKeyEntry(name=str(row[0]), type="string", has_children=False)
                    for row in result.result_rows
                ]
            return JsonKeysResponse(keys=entries)

        return JsonKeysResponse(keys=[])

    @classmethod
    def autocomplete(cls, source, column, time_from, time_to, value):
        if column not in source._columns:
            raise ValueError(f"Invalid column: {column!r}")
        incomplete = False
        from_db_table = f"{source.data['database']}.{source.data['table']}"
        time_clause = build_time_clause(
            source.time_column, source.date_column, time_from, time_to
        )
        query = f"SELECT DISTINCT {column} FROM {from_db_table} WHERE {time_clause} and {column} LIKE %(value)s ORDER BY {column} LIMIT 500"

        if source.data.get("settings"):
            query += f" SETTINGS {source.data['settings']}"

        with ClickhouseConnect(source.conn.data) as c:
            result = _client_query(c.client, query, parameters={"value": f"%{value}%"})
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
            filter_clause = to_sql_where(
                parser.root,
                columns=flyql_clickhouse_columns(request.source._columns),
                registry=transformer_registry(),
            )
        else:
            filter_clause = "true"

        raw_where_clause = request.raw_query or "true"
        params = {}
        text = text_clause(request.source, request.text, params)
        if text:
            raw_where_clause = f"({raw_where_clause}) AND {text}"

        group_by = request.group_by[0] if request.group_by else None
        group_by_value = build_group_by_value(group_by) if group_by else ""

        total = 0
        time_clause = build_time_clause(
            request.source.time_column,
            request.source.date_column,
            request.time_from,
            request.time_to,
        )
        from_db_table = (
            f"{request.source.data['database']}.{request.source.data['table']}"
        )

        time_column_type = convert_to_base_ch(
            request.source._columns[request.source.time_column].type.lower()
        )
        to_time_zone = ""
        if time_column_type in ["datetime", "datetime64"]:
            to_time_zone = f"toTimeZone(`{request.source.time_column}`, 'UTC')"
        elif time_column_type in ["timestamp", "uint64", "int64"]:
            to_time_zone = (
                f"toTimeZone(toDateTime(`{request.source.time_column}`), 'UTC')"
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
            stats_time_selector = f"toUnixTimestamp(toStartOfInterval({to_time_zone}, toIntervalSecond({stats_interval_seconds}))) * 1000"
        else:
            if time_column_type in ["datetime", "timestamp", "uint64"]:
                stats_time_selector = f"toUnixTimestamp({to_time_zone})*1000"
            elif time_column_type == "datetime64":
                stats_time_selector = f"toUnixTimestamp64Milli({to_time_zone})"

        assert request.source.conn
        with ClickhouseConnect(request.source.conn.data) as c:
            stat_sql = f"SELECT {stats_time_selector} as t, COUNT() as Count"
            if group_by_value:
                assert group_by
                stat_sql += f", {group_by_value} as `{group_by.name}`"
            stat_sql += f" FROM {from_db_table} WHERE {time_clause} AND {filter_clause} AND {raw_where_clause} GROUP BY t"
            if group_by_value:
                assert group_by
                stat_sql += f", `{group_by.name}`"
            stat_sql += " ORDER BY t"

            if request.source.data.get("settings"):
                stat_sql += f" SETTINGS {request.source.data['settings']}"

            for item in _client_query(
                c.client, stat_sql, parameters=params or None
            ).result_rows:
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
            filter_clause = to_sql_where(
                parser.root,
                columns=flyql_clickhouse_columns(source._columns),
                registry=transformer_registry(),
            )
        else:
            filter_clause = "true"

        raw_where_clause = request.raw_query or "true"
        params = {}
        where = [filter_clause, raw_where_clause]
        text = text_clause(source, request.text, params)
        if text:
            where.append(text)

        time_column = f"`{source.time_column}`"
        time_column_type = convert_to_base_ch(
            source._columns[source.time_column].type.lower()
        )
        cursor_value, cursor_bound = CURSOR_EXPRESSIONS.get(
            time_column_type, CURSOR_EXPRESSIONS["int64"]
        )
        cursor_value = cursor_value.format(c=time_column)
        tiebreak = row_tiebreak(source)
        offset = 0
        time_to = request.time_to
        if request.before:
            params["telescope_before_time"] = int(request.before["time"])
            bound = cursor_bound.format(p="{telescope_before_time:Int64}")
            if source.uniq_column:
                params["telescope_before_uniq"] = str(request.before["uniq"])
                where.append(
                    f"({time_column} < {bound} OR ({time_column} = {bound}"
                    f" AND {tiebreak} < {{telescope_before_uniq:String}}))"
                )
            else:
                where.append(f"{time_column} <= {bound}")
                offset = int(request.before.get("skip") or 0)
            # Narrow the scanned range so partition and primary key pruning apply.
            before_ms = cursor_ms(time_column_type, params["telescope_before_time"])
            if before_ms is not None:
                time_to = max(request.time_from, min(time_to, before_ms))

        time_clause = build_time_clause(
            source.time_column,
            source.date_column,
            request.time_from,
            time_to,
        )
        where_clause = " AND ".join([time_clause] + where)
        order_by_clause = f"ORDER BY {time_column} DESC, {tiebreak} DESC"
        from_db_table = f"{source.data['database']}.{source.data['table']}"

        columns_names = sorted(source._columns.keys())
        columns_to_select = []
        for column in columns_names:
            if column == source.time_column:
                if time_column_type in ["datetime", "datetime64"]:
                    columns_to_select.append(f"toTimeZone(`{column}`, 'UTC')")
                elif time_column_type in ["timestamp", "uint64", "int64"]:
                    columns_to_select.append(
                        f"toTimeZone(toDateTime(`{column}`), 'UTC')"
                    )
            else:
                columns_to_select.append(f"`{column}`")
        columns_to_select.append(cursor_value)
        columns_to_select.append(tiebreak if source.uniq_column else "NULL")
        columns_to_select = ", ".join(columns_to_select)

        settings_clause = ""
        if source.data.get("settings"):
            settings_clause = f" SETTINGS {source.data['settings']}"

        limit_clause = f"LIMIT {request.limit}"
        if offset:
            limit_clause += f" OFFSET {offset}"
        select_query = f"SELECT generateUUIDv4(),{columns_to_select} FROM {from_db_table} WHERE {where_clause} {order_by_clause} {limit_clause}{settings_clause}"

        rows = []
        keys = []

        assert source.conn
        with ClickhouseConnect(source.conn.data) as c:
            selected_columns = [source._record_pseudo_id_column] + columns_names
            result = _client_query(c.client, select_query, parameters=params or None)
            for item in result.result_rows:
                keys.append((item[-2], item[-1]))
                rows.append(
                    Row(
                        source=source,
                        selected_columns=selected_columns,
                        values=item[:-2],
                        tz=tz or UTC_ZONE,
                    )
                )
        return DataResponse(
            rows=rows,
            cursor=next_cursor(source, keys, request.limit, request.before),
        )

    @classmethod
    def fetch_chart_data(cls, request: ChartDataRequest) -> ChartDataResponse:
        return with_formulas(request, cls._fetch_chart_sql)

    @classmethod
    def _flyql_sql(cls, source, query: str) -> str:
        if not query:
            return "true"
        return to_sql_where(
            parse(query).root,
            columns=flyql_clickhouse_columns(source._columns),
            registry=transformer_registry(),
        )

    @classmethod
    def _fetch_chart_sql(cls, request: ChartDataRequest) -> ChartDataResponse:
        source = request.source
        plan = ChartPlan(request)
        filter_clause = cls._flyql_sql(source, request.query)
        raw_where_clause = request.raw_query or "true"
        time_clause = build_time_clause(
            source.time_column, source.date_column, plan.time_from, plan.query_to
        )
        where = f"{time_clause} AND ({filter_clause}) AND ({raw_where_clause})"
        from_db_table = f"{source.data['database']}.{source.data['table']}"
        settings_clause = ""
        if source.data.get("settings"):
            settings_clause = f" SETTINGS {source.data['settings']}"
        aggs = ", ".join(
            f"{agg_expression(CHART_AGGS, source, item, cls._series_where(source, item))}"
            f" AS `__telescope_v{i}`"
            for i, item in enumerate(request.series)
        )
        exprs = [
            f"ifNull(toString({build_group_by_value(g)}), '')" for g in plan.group_bys
        ]
        if len(exprs) == 1:
            aliases = ["`__telescope_g`"]
        else:
            aliases = [f"`__telescope_g{i}`" for i in range(len(exprs))]
        group = ", ".join(f"{e} AS {a}" for e, a in zip(exprs, aliases))
        group_aliases = ", ".join(aliases)

        assert source.conn
        with ClickhouseConnect(source.conn.data) as c:

            def run(sql, parameters=None):
                return _client_query(
                    c.client,
                    sql + settings_clause,
                    parameters=parameters,
                    settings={"max_execution_time": CHART_QUERY_TIMEOUT_SECONDS},
                ).result_rows

            if plan.kind == "number" or (plan.kind == "table" and not group):
                rows = run(f"SELECT {aggs} FROM {from_db_table} WHERE {where}")
                return plan.number(rows) if plan.kind == "number" else plan.table(rows)
            if plan.kind == "table":
                return plan.table(
                    run(
                        f"SELECT {group}, {aggs} FROM {from_db_table} WHERE {where}"
                        f" GROUP BY {group_aliases} ORDER BY `__telescope_v0` DESC, {group_aliases}"
                        f" LIMIT {plan.limit + 1}"
                    )
                )

            time_column = quote_column(source, source.time_column)
            time_type = convert_to_base_ch(
                source._columns[source.time_column].type.lower()
            )
            if time_type in ["timestamp", "uint64", "int64"]:
                time_column = f"toDateTime({time_column})"
            step = plan.step_ms // 1000
            bucket = f"intDiv(toUnixTimestamp({time_column}), {step}) * {plan.step_ms}"
            if not group:
                return plan.timeseries(
                    run(
                        f"SELECT {bucket} AS `__telescope_t`, {aggs} FROM {from_db_table} WHERE {where}"
                        f" GROUP BY `__telescope_t` ORDER BY `__telescope_t`"
                    )
                )
            groups, truncated = plan.top_groups(
                run(
                    f"SELECT {group} FROM {from_db_table} WHERE {where}"
                    f" GROUP BY {group_aliases} ORDER BY count() DESC, {group_aliases}"
                    f" LIMIT {plan.limit + 1}"
                )
            )
            if not groups:
                return plan.timeseries([], groups, truncated)
            if len(exprs) == 1:
                restrict = f"{exprs[0]} IN {{groups:Array(String)}}"
            else:
                types = ", ".join(["String"] * len(exprs))
                restrict = (
                    f"tuple({', '.join(exprs)}) IN {{groups:Array(Tuple({types}))}}"
                )
            rows = run(
                f"SELECT {bucket} AS `__telescope_t`, {group}, {aggs}"
                f" FROM {from_db_table} WHERE {where} AND {restrict}"
                f" GROUP BY `__telescope_t`, {group_aliases} ORDER BY `__telescope_t`",
                {"groups": groups},
            )
            return plan.timeseries(rows, groups, truncated)

    @classmethod
    def _series_where(cls, source, series) -> Optional[str]:
        return (
            f"({cls._flyql_sql(source, series['where'])})"
            if series.get("where")
            else None
        )
