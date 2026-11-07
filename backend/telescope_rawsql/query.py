"""Runs one raw SQL SELECT for a tile, read-only and bounded.

ClickHouse parses the query first (EXPLAIN AST); SETTINGS clauses, non-allowlisted table functions and functions that
read server files, settings or other tables are refused. EXPLAIN QUERY TREE then checks every table it reads.
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
# Scalar functions that read server files or settings, or tables the query does not name.
REFUSED_FUNCTIONS = {"file", "getServerSetting", "joinGet", "joinGetOrNull"}
REFUSED_PREFIX = "dict"
RAW_SQL_MAX_MEMORY = 1024**3
RAW_SQL_MAX_ROWS_TO_READ = 1_000_000_000
RAW_SQL_MAX_THREADS = 4
QUERY_SETTINGS = {
    "readonly": 2,
    "max_execution_time": CHART_QUERY_TIMEOUT_SECONDS,
    "max_result_rows": RAW_SQL_MAX_ROWS + 1,
    "max_result_bytes": RAW_SQL_MAX_BYTES,
    "result_overflow_mode": "throw",
    "max_memory_usage": RAW_SQL_MAX_MEMORY,
    "max_rows_to_read": RAW_SQL_MAX_ROWS_TO_READ,
    "read_overflow_mode": "throw",
    "max_threads": RAW_SQL_MAX_THREADS,
}
# A table the query reads; aliases are renamed __tableN, and FINAL/SAMPLE follow the name.
TABLE_RE = re.compile(r"^\s*TABLE id: \d+,(?: alias: \w+,)? table_name: (.*)$")
TABLE_MODIFIERS_RE = re.compile(r", (?:final|sample_size|sample_offset): .*$")
MAX_SAFE_INT = 2**53 - 1
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
        if not node.startswith("Function "):
            continue
        name = node.split()[1]
        parent = ast_lines[i - 1] if i else ""
        if parent.strip().startswith("TableExpression"):
            if name not in SAFE_TABLE_FUNCTIONS:
                return f"table function {name} is not allowed"
        elif name in REFUSED_FUNCTIONS or name.startswith(REFUSED_PREFIX):
            return f"function {name} is not allowed"
    return None


def table_error(tree_lines, tables: set) -> str:
    """Why the analyzed query is refused (it reads a table outside `tables`), or None."""
    for line in tree_lines:
        match = TABLE_RE.match(line)
        if match:
            name = TABLE_MODIFIERS_RE.sub("", match.group(1))
            if name not in tables:
                return f"table {name} is not a source you can query on this connection"
    return None


def clickhouse_message(err) -> str:
    text = str(err)
    start = text.find("DB::Exception: ")
    text = text[start + len("DB::Exception: ") :] if start >= 0 else text
    return text.strip().split("\n")[0][:500]


def json_value(value):
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    if isinstance(value, int) and not isinstance(value, bool):
        # JSON numbers above 2^53 lose digits in the browser.
        return value if abs(value) <= MAX_SAFE_INT else str(value)
    if value is None or isinstance(value, (bool, str)):
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
    connection,
    tables: set,
    sql: str,
    time_from: int,
    time_to: int,
    granularity: str,
    params,
) -> Dict:
    """Runs `sql` on `connection` if it reads only `tables` ("db.table")."""
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
        # Analysis errors (an unknown table, a type mismatch) are query failures.
        tree = _client_query(
            c.client,
            f"SELECT explain FROM (EXPLAIN QUERY TREE {query})",
            parameters=parameters,
            settings=QUERY_SETTINGS,
        ).result_rows
        error = table_error([row[0] for row in tree], tables)
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
