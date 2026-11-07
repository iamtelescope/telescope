"""Runs one raw SQL SELECT for a tile, read-only and bounded.

ClickHouse parses the query first (EXPLAIN AST); SETTINGS clauses and non-allowlisted table functions are refused.
"""

import datetime
import decimal
import math
import re
import uuid
from typing import Dict

from clickhouse_connect.driver.exceptions import DatabaseError

from telescope.constants import CHART_QUERY_TIMEOUT_SECONDS
from telescope.fetchers.chart import pick_granularity
from telescope.fetchers.clickhouse import ClickhouseConnect, _client_query
from telescope_rawsql.macros import MACRO_PARAMS, MacroError, expand_macros, scan

RAW_SQL_DISPLAY = "sql"
RAW_SQL_MAX_LENGTH = 20000
RAW_SQL_MAX_ROWS = 1000
RAW_SQL_MAX_BYTES = 10 * 1024 * 1024
LIMIT_PARAM = "rawSqlLimit"
RESERVED_PARAMS = set(MACRO_PARAMS) | {LIMIT_PARAM}
# Table functions that read nothing outside the query; url(), file(), remote() and the rest are refused.
SAFE_TABLE_FUNCTIONS = {
    "numbers",
    "numbers_mt",
    "zeros",
    "zeros_mt",
    "generateSeries",
    "generate_series",
    "values",
}
QUERY_SETTINGS = {
    "readonly": 2,
    "max_execution_time": CHART_QUERY_TIMEOUT_SECONDS,
    "max_result_rows": RAW_SQL_MAX_ROWS + 1,
    "max_result_bytes": RAW_SQL_MAX_BYTES,
    "result_overflow_mode": "throw",
}
WRAPPER_TOP = ["SelectWithUnionQuery (children 1)", " ExpressionList (children 1)"]
FIRST_WORD_RE = re.compile(r"(?:\s+|--[^\n]*|/\*.*?\*/|\()*(\w*)", re.S)


class RawSqlError(Exception):
    """A query that is refused before it runs."""


def build_query(sql: str, time_from: int, time_to: int, granularity: str, params):
    """(SQL to run, its query parameters). Variables only ever travel as parameters."""
    sql = sql.strip().rstrip(";").rstrip()
    if not sql:
        raise RawSqlError("SQL is empty")
    if FIRST_WORD_RE.match(sql).group(1).lower() not in ("select", "with"):
        raise RawSqlError("only SELECT queries are allowed")
    if any(c == ";" for _, c in scan(sql, 0)):
        raise RawSqlError("multi-statement queries are not allowed")
    try:
        sql = expand_macros(sql)
    except MacroError as err:
        raise RawSqlError(str(err))
    _, step_ms = pick_granularity(time_from, time_to, granularity)
    parameters = {k: v for k, v in (params or {}).items() if k not in RESERVED_PARAMS}
    parameters.update(
        startDateMilliseconds=time_from,
        endDateMilliseconds=time_to,
        intervalSeconds=step_ms // 1000,
        intervalMilliseconds=step_ms,
    )
    parameters[LIMIT_PARAM] = RAW_SQL_MAX_ROWS + 1
    # The LIMIT placeholder also keeps clickhouse_connect on server-side binding.
    query = f"SELECT * FROM (\n{sql}\n) LIMIT {{{LIMIT_PARAM}:UInt32}}"
    return query, parameters


def ast_error(ast_lines) -> str:
    """Why the parsed query is refused, or None."""
    # The wrapper is one SELECT; a UNION means the SQL closed its parenthesis.
    if ast_lines[:2] != WRAPPER_TOP:
        return "only a single SELECT query is allowed"
    for i, line in enumerate(ast_lines):
        node = line.strip()
        if node == "Set" or node.startswith("Set "):
            return "SETTINGS clauses are not allowed"
        parent = ast_lines[i - 1] if i else ""
        if node.startswith("Function ") and parent.strip().startswith(
            "TableExpression"
        ):
            name = node.split()[1]
            if name not in SAFE_TABLE_FUNCTIONS:
                return f"table function {name} is not allowed"
    return None


def clickhouse_message(err) -> str:
    text = str(err)
    start = text.find("DB::Exception: ")
    text = text[start + len("DB::Exception: ") :] if start >= 0 else text
    return text.strip().split("\n")[0][:500]


def json_value(value):
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    if value is None or isinstance(value, (bool, int, str)):
        return value
    if isinstance(value, decimal.Decimal):
        return float(value)
    if isinstance(value, (datetime.datetime, datetime.date)):
        return value.isoformat()
    if isinstance(value, (list, tuple)):
        return [json_value(v) for v in value]
    if isinstance(value, dict):
        return {str(k): json_value(v) for k, v in value.items()}
    if isinstance(value, bytes):
        return value.decode(errors="replace")
    if isinstance(value, uuid.UUID):
        return str(value)
    return str(value)


def run_raw_sql(
    connection, sql: str, time_from: int, time_to: int, granularity: str, params
) -> Dict:
    query, parameters = build_query(sql, time_from, time_to, granularity, params)
    with ClickhouseConnect(connection.data) as c:
        try:
            explained = _client_query(
                c.client,
                f"SELECT explain FROM (EXPLAIN AST {query})",
                parameters=parameters,
                settings=QUERY_SETTINGS,
            ).result_rows
        except DatabaseError as err:
            raise RawSqlError(clickhouse_message(err))
        error = ast_error([row[0] for row in explained])
        if error:
            raise RawSqlError(error)
        result = _client_query(
            c.client, query, parameters=parameters, settings=QUERY_SETTINGS
        )
    rows = result.result_rows
    return {
        "kind": "rows",
        "columns": [
            {"name": name, "type": t.name}
            for name, t in zip(result.column_names, result.column_types)
        ],
        "rows": [[json_value(v) for v in row] for row in rows[:RAW_SQL_MAX_ROWS]],
        "truncated": len(rows) > RAW_SQL_MAX_ROWS,
    }
