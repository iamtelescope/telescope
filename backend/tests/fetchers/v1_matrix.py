"""v1 chart configs and fake database rows, shared by the golden capture and its regression test."""

from unittest.mock import MagicMock, patch

from telescope.fetchers import clickhouse, starrocks
from tests.fetchers.test_chart_sql import T0, make_request, make_source

SERIES = {
    "count": [{"agg": "count"}],
    "many": [
        {"agg": "count", "alias": "n"},
        {"agg": "sum", "column": "duration"},
        {"agg": "avg", "column": "duration"},
        {"agg": "quantile", "column": "duration", "level": 0.95},
        {"agg": "uniq", "column": "service"},
    ],
}
DISPLAYS = ["line", "stacked_bar", "number", "table", "bar"]


def cases():
    for kind in ["clickhouse", "starrocks"]:
        for display in DISPLAYS:
            for series_name, series in SERIES.items():
                if display in ("number", "bar") and len(series) > 1:
                    continue
                for group_by in [None, "service", "attrs.k"]:
                    if (display == "number") == bool(group_by) and display != "number":
                        pass
                    if display == "number" and group_by:
                        continue
                    if display == "bar" and not group_by:
                        continue
                    for query in ["", "service = 'a'"]:
                        yield f"{kind}-{display}-{series_name}-{group_by}-{bool(query)}", (
                            kind,
                            display,
                            series,
                            group_by,
                            query,
                        )


def fake_rows(sql, n):
    vals = tuple(range(1, n + 1))
    if "__telescope_t" in sql and "__telescope_g" in sql:
        return [(T0 + 60000, "a", *vals), (T0 + 120000, "", *vals)]
    if "__telescope_t" in sql:
        return [(T0 + 60000, *vals), (T0 + 120000, *(None for _ in vals))]
    if "__telescope_v" not in sql:
        return [("a",), ("",)]
    if "__telescope_g" in sql:
        return [("a", *vals), ("b", *vals)]
    return [vals]


def run_case(case):
    kind, display, series, group_by, query = case
    source = make_source(kind, "DateTime64(3)", settings="max_threads = 1")
    request = make_request(
        source, display=display, series=series, group_by=group_by, query=query
    )
    sqls = []
    if kind == "clickhouse":
        with patch("telescope.fetchers.clickhouse.ClickhouseConnect") as connect:
            client = MagicMock()
            connect.return_value.__enter__.return_value.client = client

            def query_fn(sql, **kw):
                sqls.append([sql, kw.get("parameters"), kw.get("settings")])
                return MagicMock(result_rows=fake_rows(sql, len(series)))

            client.query.side_effect = query_fn
            result = clickhouse.Fetcher.fetch_chart_data(request).as_dict()
    else:
        with patch("telescope.fetchers.starrocks.StarrocksConnect") as connect:
            cursor = MagicMock()
            connect.return_value.__enter__.return_value.client.cursor.return_value = (
                cursor
            )
            last = {}

            def execute(sql):
                sqls.append([sql, None, None])
                last["rows"] = fake_rows(sql, len(series))

            cursor.execute.side_effect = execute
            cursor.fetchall.side_effect = lambda: last["rows"]
            result = starrocks.Fetcher.fetch_chart_data(request).as_dict()
    return {"sqls": sqls, "result": result}
