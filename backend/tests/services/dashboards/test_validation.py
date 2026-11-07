import copy

import pytest

from telescope.fetchers.chart import is_numeric_column_type
from telescope.rbac.manager import RBACManager
from telescope.rbac.roles import SourceRole
from telescope.serializers.dashboard import DashboardDataSerializer

from tests.data import get_dashboard_data

rbac_manager = RBACManager()


def validate(data, user, old_sources=(), old_raw_queries=()):
    serializer = DashboardDataSerializer(
        data=data,
        context={
            "user": user,
            "old_sources": set(old_sources),
            "old_raw_queries": set(old_raw_queries),
        },
    )
    serializer.is_valid()
    return serializer


def chart_data(source_slug="clickhouse", **chart):
    data = get_dashboard_data(source_slug)
    data["tiles"][0]["chart"].update(chart)
    return data


def chart_errors(serializer, tile=0):
    return serializer.errors["tiles"][tile]["chart"]


@pytest.mark.django_db
def test_valid_data(root_user, clickhouse_source):
    serializer = validate(get_dashboard_data(), root_user)
    assert serializer.is_valid(), serializer.errors
    tiles = serializer.validated_data["tiles"]
    assert tiles[0]["chart"]["granularity"] == "auto"
    assert tiles[0]["chart"]["query"] == ""
    assert tiles[1]["chart"] == {"display": "text", "text": "Runbook"}


@pytest.mark.django_db
@pytest.mark.parametrize(
    "path",
    [
        [],
        ["time"],
        ["tiles", 0],
        ["tiles", 0, "chart"],
        ["tiles", 1, "chart"],
        ["tiles", 0, "chart", "series", 0],
    ],
)
def test_unknown_keys_rejected(root_user, clickhouse_source, path):
    data = get_dashboard_data()
    target = data
    for key in path:
        target = target[key]
    target["extra"] = 1
    serializer = validate(data, root_user)
    assert not serializer.is_valid()
    assert "unknown key" in str(serializer.errors)


@pytest.mark.django_db
def test_duplicate_tile_id(root_user, clickhouse_source):
    data = get_dashboard_data()
    data["tiles"][1]["id"] = "t1"
    serializer = validate(data, root_user)
    assert serializer.errors["tiles"] == ["duplicate tile id t1"]


@pytest.mark.django_db
@pytest.mark.parametrize(
    "tile, field",
    [
        ({"x": 13, "w": 12}, "w"),
        ({"x": 24, "w": 1}, "x"),
        ({"w": 0}, "w"),
        ({"w": 25}, "w"),
        ({"h": 49}, "h"),
        ({"h": 0}, "h"),
        ({"y": -1}, "y"),
        ({"y": 10001}, "y"),
        ({"id": "bad id"}, "id"),
        ({"id": "x" * 33}, "id"),
        ({"title": "x" * 129}, "title"),
    ],
)
def test_tile_grid_rules(root_user, clickhouse_source, tile, field):
    data = get_dashboard_data()
    data["tiles"][0].update(tile)
    serializer = validate(data, root_user)
    assert field in serializer.errors["tiles"][0]


@pytest.mark.django_db
def test_tile_fits_right_edge(root_user, clickhouse_source):
    data = get_dashboard_data()
    data["tiles"][0].update({"x": 12, "w": 12})
    assert validate(data, root_user).is_valid()


@pytest.mark.django_db
@pytest.mark.parametrize(
    "chart, field, message",
    [
        ({"series": []}, "series", None),
        ({"series": [{"agg": "count"}] * 6}, "series", None),
        ({"series": [{"agg": "count", "column": "thread_id"}]}, "series", None),
        ({"series": [{"agg": "sum"}]}, "series", "This field is required."),
        (
            {"series": [{"agg": "quantile", "column": "thread_id", "level": 0.8}]},
            "series",
            "must be one of",
        ),
        (
            {"series": [{"agg": "sum", "column": "thread_id", "level": 0.5}]},
            "series",
            "level is only allowed for quantile",
        ),
        ({"series": [{"agg": "median"}]}, "series", None),
        ({"series": [{"agg": "count", "alias": "x" * 65}]}, "series", None),
        (
            {"series": [{"agg": "sum", "column": "hostname"}]},
            "series",
            "column hostname is not numeric",
        ),
        (
            {"series": [{"agg": "avg", "column": "nope"}]},
            "series",
            "source has no column nope",
        ),
        ({"display": "scatter"}, "display", None),
        ({"granularity": "7m"}, "granularity", None),
        ({"limit": 51}, "limit", "must be between 1 and 50"),
        ({"limit": 0}, "limit", None),
        (
            {"display": "table", "limit": 101},
            "limit",
            "must be between 1 and 100",
        ),
        (
            {"display": "number", "group_by": ""} | {"series": [{"agg": "count"}] * 2},
            "series",
            "number needs exactly 1 series",
        ),
        (
            {"display": "number", "group_by": "hostname"},
            "group_by",
            "number does not support group by",
        ),
        ({"display": "bar", "group_by": ""}, "group_by", "bar needs a group by"),
        (
            {"display": "bar", "series": [{"agg": "count"}] * 2},
            "series",
            "bar needs exactly 1 series",
        ),
        (
            {"group_by": "hostname, level, thread_name, thread_id"},
            "group_by",
            "at most 3 group by columns",
        ),
        ({"group_by": "nope"}, "group_by", "nope"),
        ({"number_format": {"unit": "number", "decimals": 7}}, "number_format", None),
        ({"number_format": {"unit": "eur", "decimals": 2}}, "number_format", None),
    ],
)
def test_chart_rules(root_user, clickhouse_source, chart, field, message):
    serializer = validate(chart_data(**chart), root_user)
    assert not serializer.is_valid()
    errors = chart_errors(serializer)
    assert field in errors, errors
    if message:
        assert message in str(errors[field])


@pytest.mark.django_db
@pytest.mark.parametrize(
    "chart",
    [
        {"series": [{"agg": "sum", "column": "thread_id"}]},
        {"series": [{"agg": "uniq", "column": "hostname"}]},
        {"series": [{"agg": "quantile", "column": "revision", "level": 0.95}]},
        {"display": "table", "limit": 100},
        {"display": "bar", "series": [{"agg": "count", "alias": "rows"}]},
        {"display": "number", "group_by": ""},
        {"number_format": {"unit": "bytes", "decimals": 2}},
        {"series": [{"agg": "count"}] * 5},
    ],
)
def test_chart_valid(root_user, clickhouse_source, chart):
    serializer = validate(chart_data(**chart), root_user)
    assert serializer.is_valid(), serializer.errors


@pytest.mark.django_db
def test_text_chart_rules(root_user, clickhouse_source):
    data = get_dashboard_data()
    data["tiles"][1]["chart"]["text"] = "x" * 10001
    assert "text" in validate(data, root_user).errors["tiles"][1]["chart"]
    data = get_dashboard_data()
    data["tiles"][1]["chart"]["source"] = "clickhouse"
    assert "source" in validate(data, root_user).errors["tiles"][1]["chart"]


@pytest.mark.django_db
def test_query_chart_needs_source(root_user, clickhouse_source):
    data = get_dashboard_data()
    del data["tiles"][0]["chart"]["source"]
    assert "source" in chart_errors(validate(data, root_user))


@pytest.mark.django_db
def test_docker_count_only(root_user, docker_source):
    data = chart_data(
        docker_source.slug, group_by="", series=[{"agg": "uniq", "column": "stream"}]
    )
    errors = chart_errors(validate(data, root_user))
    assert errors["series"][0]["agg"] == [
        "aggregation uniq is not supported for docker sources"
    ]
    data = chart_data(docker_source.slug, group_by="stream")
    assert validate(data, root_user).is_valid()


@pytest.mark.django_db
@pytest.mark.parametrize(
    "data_patch, field",
    [
        ({"refresh": "10s"}, "refresh"),
        ({"time": {"from": "yesterday", "to": "now"}}, "time"),
        ({"time": {"from": "now-1h"}}, "time"),
        ({"query": "x" * 10001}, "query"),
    ],
)
def test_data_rules(root_user, clickhouse_source, data_patch, field):
    data = get_dashboard_data()
    data.update(data_patch)
    assert field in validate(data, root_user).errors


@pytest.mark.django_db
def test_epoch_ms_time(root_user, clickhouse_source):
    data = get_dashboard_data()
    data["time"] = {"from": "1762423200000", "to": "1762426800000"}
    assert validate(data, root_user).is_valid()


@pytest.mark.django_db
def test_max_tiles(root_user, clickhouse_source):
    data = get_dashboard_data()
    note = data["tiles"][1]
    data["tiles"] = []
    for i in range(51):
        tile = copy.deepcopy(note)
        tile["id"] = f"n{i}"
        data["tiles"].append(tile)
    assert "tiles" in validate(data, root_user).errors
    data["tiles"] = data["tiles"][:50]
    assert validate(data, root_user).is_valid()


@pytest.mark.django_db
def test_size_cap(root_user, clickhouse_source):
    data = get_dashboard_data()
    note = data["tiles"][1]
    data["tiles"] = []
    for i in range(30):
        tile = copy.deepcopy(note)
        tile["id"] = f"n{i}"
        tile["chart"]["text"] = "x" * 9000
        data["tiles"].append(tile)
    serializer = validate(data, root_user)
    assert serializer.errors == {
        "non_field_errors": ["data must be at most 262144 bytes"]
    }


@pytest.mark.django_db
def test_new_source_needs_use(test_user, clickhouse_source):
    errors = chart_errors(validate(get_dashboard_data(), test_user))
    assert errors["source"] == ["source clickhouse not found"]

    errors = chart_errors(validate(get_dashboard_data("missing"), test_user))
    assert errors["source"] == ["source missing not found"]

    rbac_manager.grant_source_role(
        clickhouse_source, SourceRole.VIEWER.value, user=test_user
    )
    errors = chart_errors(validate(get_dashboard_data(), test_user))
    assert errors["source"] == ["source clickhouse not found"]

    rbac_manager.grant_source_role(
        clickhouse_source, SourceRole.USER.value, user=test_user
    )
    assert validate(get_dashboard_data(), test_user).is_valid()


@pytest.mark.django_db
def test_old_source_not_rechecked(test_user, clickhouse_source):
    serializer = validate(get_dashboard_data(), test_user, old_sources={"clickhouse"})
    assert serializer.is_valid(), serializer.errors


@pytest.mark.parametrize(
    "kind, column_type, expected",
    [
        ("clickhouse", "UInt64", True),
        ("clickhouse", "Int8", True),
        ("clickhouse", "Float32", True),
        ("clickhouse", "Decimal(18, 4)", True),
        ("clickhouse", "Nullable(Float64)", True),
        ("clickhouse", "LowCardinality(Nullable(UInt32))", True),
        ("clickhouse", "nullable(int64)", True),
        ("clickhouse", "String", False),
        ("clickhouse", "DateTime64(3)", False),
        ("clickhouse", "Array(UInt64)", False),
        ("clickhouse", "Enum8('a' = 1)", False),
        ("starrocks", "bigint", True),
        ("starrocks", "BIGINT(20)", True),
        ("starrocks", "decimal(10,2)", True),
        ("starrocks", "double", True),
        ("starrocks", "varchar(65533)", False),
        ("starrocks", "datetime", False),
        ("docker", "int", False),
    ],
)
def test_is_numeric_column_type(kind, column_type, expected):
    assert is_numeric_column_type(kind, column_type) is expected


@pytest.mark.django_db
def test_raw_query_needs_raw_query_permission(test_user, clickhouse_source):
    rbac_manager.grant_source_role(
        clickhouse_source, SourceRole.USER.value, user=test_user
    )
    data = chart_data(raw_query="1 = 1")
    assert chart_errors(validate(data, test_user)) == {
        "raw_query": ["Insufficient permissions to use source raw queries"]
    }
    stored = {("t1", "clickhouse", "1 = 1")}
    assert validate(data, test_user, old_raw_queries=stored).is_valid()
    changed = chart_data(raw_query="2 = 2")
    assert not validate(changed, test_user, old_raw_queries=stored).is_valid()

    rbac_manager.grant_source_role(
        clickhouse_source, SourceRole.RAW_QUERY_USER.value, user=test_user
    )
    assert validate(changed, test_user).is_valid()


@pytest.mark.django_db
def test_raw_query_on_lost_source_must_be_unchanged(test_user, clickhouse_source):
    data = chart_data(raw_query="1 = 1")
    stored = {("t1", "clickhouse", "1 = 1")}
    old = ["clickhouse"]
    assert validate(data, test_user, old, stored).is_valid()
    assert chart_errors(validate(chart_data(raw_query="2 = 2"), test_user, old)) == {
        "raw_query": ["Insufficient permissions to use source raw queries"]
    }


@pytest.mark.django_db
def test_raw_query_needs_source_support(root_user, docker_source):
    serializer = validate(chart_data("docker", raw_query="1 = 1"), root_user)
    assert chart_errors(serializer)["raw_query"] == [
        "This source does not support raw queries"
    ]
