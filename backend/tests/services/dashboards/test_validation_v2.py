"""Dashboard data v3 and chart engine v2 validation."""

import pytest

from tests.data import get_dashboard_data
from tests.services.dashboards.test_validation import chart_data, chart_errors, validate

RATIO = [
    {"agg": "count", "alias": "errors", "where": "level = 'ERROR'", "hidden": True},
    {"agg": "count", "alias": "total", "hidden": True},
    {"agg": "formula", "formula": "errors / total * 100", "alias": "ratio"},
]


@pytest.mark.django_db
@pytest.mark.parametrize(
    "chart",
    [
        {"series": RATIO},
        {
            "display": "number",
            "group_by": "",
            "series": RATIO,
            "sparkline": True,
            "compare": True,
        },
        {"display": "pie", "group_by": "hostname"},
        {"display": "bar", "group_by": "hostname", "series": RATIO},
        {"group_by": "hostname, level, thread_name", "compare": True},
        {"series": [{"agg": "last_value", "column": "thread_id", "color": "#aabbcc"}]},
        {"series": [{"agg": "any", "column": "thread_id", "where": "x = 1"}]},
        {
            "display": "table",
            "color_rules": [{"op": "gt", "value": 10, "color": "#ff0000"}],
            "number_format": {
                "unit": "duration_ns",
                "decimals": 1,
                "prefix": "~",
                "suffix": "/s",
                "compact": True,
            },
        },
    ],
)
def test_chart_v2_valid(root_user, clickhouse_source, chart):
    serializer = validate(chart_data(**chart), root_user)
    assert serializer.is_valid(), serializer.errors


@pytest.mark.django_db
@pytest.mark.parametrize(
    "chart, field, message",
    [
        (
            {"series": [{"agg": "formula", "formula": "a + 1"}]},
            "series",
            "at least one query series",
        ),
        (
            {"series": [{"agg": "count"}, {"agg": "formula", "formula": "a + 1"}]},
            "series",
            "unknown series a",
        ),
        ({"series": [{"agg": "formula"}]}, "series", "required"),
        (
            {"series": [{"agg": "formula", "formula": "x", "column": "thread_id"}]},
            "series",
            "does not take a column",
        ),
        (
            {"series": [{"agg": "count", "formula": "x"}]},
            "series",
            "only allowed for agg formula",
        ),
        (
            {
                "series": [
                    {"agg": "count", "alias": "a"},
                    {"agg": "count", "alias": "a"},
                ]
            },
            "series",
            "duplicate alias a",
        ),
        (
            {"series": [{"agg": "last_value", "column": "hostname"}]},
            "series",
            "not numeric",
        ),
        ({"series": [{"agg": "count", "color": "red"}]}, "series", None),
        (
            {"display": "number", "series": RATIO[:2] + [{**RATIO[2], "hidden": True}]},
            "series",
            "needs exactly 1 series shown",
        ),
        (
            {"display": "pie", "group_by": ""},
            "group_by",
            "pie needs a group by column",
        ),
        (
            {
                "display": "pie",
                "group_by": "hostname",
                "series": [{"agg": "count"}] * 2,
            },
            "series",
            "pie needs exactly 1 series shown",
        ),
        ({"display": "table", "compare": True}, "compare", "previous period"),
        ({"sparkline": True}, "sparkline", "only number"),
        (
            {"color_rules": [{"op": "between", "value": 1, "color": "#000000"}]},
            "color_rules",
            None,
        ),
        ({"number_format": {"unit": "eur", "decimals": 2}}, "number_format", None),
    ],
)
def test_chart_v2_rules(root_user, clickhouse_source, chart, field, message):
    serializer = validate(chart_data(**chart), root_user)
    assert not serializer.is_valid()
    errors = chart_errors(serializer)
    assert field in errors, errors
    if message:
        assert message in str(errors[field])


@pytest.mark.django_db
def test_docker_keeps_count_only_and_one_group(root_user, docker_source):
    serializer = validate(
        chart_data(
            docker_source.slug,
            series=[{"agg": "count", "where": "x = 1"}],
            group_by="",
        ),
        root_user,
    )
    assert "series filters are not supported" in str(chart_errors(serializer))


@pytest.mark.django_db
def test_sections_and_tile_fields(root_user, clickhouse_source):
    data = get_dashboard_data()
    data["version"] = 3
    data["variables"] = []
    data["sections"] = [{"id": "s1", "title": "HTTP", "collapsed": True}]
    data["tiles"][0].update(section="s1", description="Requests per minute")
    serializer = validate(data, root_user)
    assert serializer.is_valid(), serializer.errors
    assert serializer.validated_data["sections"] == data["sections"]
    data["tiles"][1]["section"] = "nope"
    serializer = validate(data, root_user)
    assert "unknown section nope" in str(serializer.errors["tiles"])
    data["tiles"][1].pop("section")
    data["sections"].append({"id": "s1", "title": "again"})
    serializer = validate(data, root_user)
    assert "duplicate section id s1" in str(serializer.errors["sections"])


@pytest.mark.django_db
def test_v2_data_upgrades_to_v3(root_user, clickhouse_source):
    data = get_dashboard_data()
    data.update(version=2, variables=[])
    serializer = validate(data, root_user)
    assert serializer.is_valid(), serializer.errors
    assert serializer.validated_data["version"] == 3
    assert serializer.validated_data["sections"] == []
