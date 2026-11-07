from unittest.mock import MagicMock, patch

import pytest
from flyql import parse
from rest_framework.test import APIClient

from telescope.fetchers import clickhouse
from telescope.fetchers.chart import VariableError, bind_query, flyql_literal
from telescope.fetchers.response import ChartDataResponse
from telescope.models import Dashboard
from telescope.rbac.manager import RBACManager
from telescope.rbac.roles import SourceRole
from telescope.serializers.dashboard import upgrade_dashboard_data

from tests.api.dashboards.test_views import chart_body
from tests.data import get_dashboard_data
from tests.fetchers.test_chart_sql import ch_calls, make_request, make_source

rbac_manager = RBACManager()

PARAMS = {
    "svc": "payment",
    "many": ["payment", "cart"],
    "empty": "",
    "none": [],
    "n": 5,
    "evil": "x' or 1=1",
}


@pytest.mark.parametrize(
    "query, expected",
    [
        ("ServiceName = $svc", "ServiceName = 'payment'"),
        ("ServiceName = $many", "ServiceName in ['payment', 'cart']"),
        ("ServiceName != $many", "ServiceName not in ['payment', 'cart']"),
        ("ServiceName in [$many, 'ad']", "ServiceName in ['payment', 'cart', 'ad']"),
        ("ServiceName in [$svc]", "ServiceName in ['payment']"),
        ("code = $n", "code = 5"),
        ("ServiceName = $evil", "ServiceName = 'x\\' or 1=1'"),
        ("a = 1 and b = $empty", "a = 1"),
        ("not (a = $none) or c = 2", "c = 2"),
        ("a in [$none]", ""),
        ("a = $n and (b = $svc or c = $empty)", "(a = 5 and b = 'payment')"),
        ("not a = $svc", "not a = 'payment'"),
        ("attrs.'http.method'|lower = $svc", "attrs.'http.method'|lower = 'payment'"),
        ("level = 'ERROR'", "level = 'ERROR'"),
        ("price = '$5'", "price = '$5'"),
        ("", ""),
    ],
)
def test_bind_query(query, expected):
    assert bind_query(query, PARAMS) == expected


@pytest.mark.parametrize(
    "query, name, message",
    [
        ("a = $missing", "missing", "no value for $missing"),
        ("a ~ $many", "many", "several values need = or != instead of ~"),
        ("a = ago($svc)", "svc", "$svc cannot be used inside a function"),
        ("a = $1", "1", "no value for $1"),
    ],
)
def test_bind_query_errors(query, name, message):
    with pytest.raises(VariableError) as err:
        bind_query(query, PARAMS)
    assert (err.value.name, err.value.message) == (name, message)


@pytest.mark.parametrize(
    "value",
    ["plain", "q'uote", 'dq"x', "x\\'y", "a\\b", "ü€ \t", "' or 1=1 --", "''", "$x"],
)
def test_literal_round_trips_through_flyql(value):
    expression = parse(f"a = {flyql_literal('v', value)}").root.left.expression
    assert expression.value == value


@pytest.mark.parametrize("value", ["line\nbreak", "cr\r", "ends\\"])
def test_literal_rejects_values_flyql_cannot_carry(value):
    with pytest.raises(VariableError):
        flyql_literal("v", value)


def test_injection_is_a_quoted_literal_in_sql():
    with patch("telescope.fetchers.clickhouse.ClickhouseConnect") as connect:
        client = MagicMock()
        connect.return_value.__enter__.return_value.client = client
        client.query.return_value.result_rows = [(0,)]
        source = make_source("clickhouse", "DateTime64(3)")
        query = bind_query("service = $evil", PARAMS)
        clickhouse.Fetcher.fetch_chart_data(
            make_request(source, display="number", query=query)
        )
        [(sql, _, _)] = ch_calls(client)
    assert "AND (service = 'x\\' or 1=1') AND" in sql


def client_for(user):
    client = APIClient()
    client.force_login(user)
    return client


def post_chart(user, source, fetcher, **changes):
    with patch("telescope.views.source.views.get_fetchers") as get_fetchers:
        get_fetchers.return_value = {"clickhouse": fetcher}
        return (
            client_for(user)
            .post(
                f"/ui/v1/sources/{source.slug}/chartData",
                chart_body(**changes),
                format="json",
            )
            .json()
        )


def number_fetcher():
    fetcher = MagicMock()
    fetcher.fetch_chart_data.return_value = ChartDataResponse("number", 1, 2, value=3)
    return fetcher


@pytest.mark.django_db
def test_chart_data_binds_params(root_user, clickhouse_source):
    fetcher = number_fetcher()
    result = post_chart(
        root_user,
        clickhouse_source,
        fetcher,
        display="number",
        query="hostname = $host",
        dashboard_query="thread_name = $kind",
        params={"host": ["a", "b"], "kind": "Select", "unused": "x"},
    )
    assert result["validation"]["result"] is True, result["validation"]
    request = fetcher.fetch_chart_data.call_args.args[0]
    assert request.query == "(hostname in ['a', 'b']) and (thread_name = 'Select')"


@pytest.mark.django_db
def test_chart_data_empty_optional_variable_drops_the_filter(
    root_user, clickhouse_source
):
    fetcher = number_fetcher()
    post_chart(
        root_user,
        clickhouse_source,
        fetcher,
        display="number",
        query="hostname = $host",
        params={"host": []},
    )
    assert fetcher.fetch_chart_data.call_args.args[0].query == ""


@pytest.mark.django_db
def test_chart_data_missing_variable_is_a_validation_error(
    root_user, clickhouse_source
):
    fetcher = number_fetcher()
    result = post_chart(
        root_user,
        clickhouse_source,
        fetcher,
        display="number",
        dashboard_query="hostname = $host",
    )
    assert not fetcher.fetch_chart_data.called
    assert result["validation"]["result"] is False
    assert result["validation"]["fields"] == {
        "params": {"host": ["no value for $host"]}
    }


@pytest.mark.django_db
def test_chart_data_bound_query_is_validated(root_user, clickhouse_source):
    fetcher = number_fetcher()
    result = post_chart(
        root_user,
        clickhouse_source,
        fetcher,
        display="number",
        query="no_such_column = $v",
        params={"v": "x"},
    )
    assert not fetcher.fetch_chart_data.called
    assert list(result["validation"]["fields"]) == ["query"]


@pytest.mark.django_db
@pytest.mark.parametrize(
    "params",
    [{"v": {"a": 1}}, {"v": ["x"] * 101}, {"v": "x" * 1001}, {"v": [["x"]]}],
)
def test_chart_data_rejects_bad_params(root_user, clickhouse_source, params):
    result = post_chart(
        root_user, clickhouse_source, number_fetcher(), display="number", params=params
    )
    assert list(result["validation"]["fields"]["params"]) == ["v"]


def variables_data(source_slug, variables):
    data = get_dashboard_data(source_slug)
    data["version"] = 2
    data["variables"] = variables
    return data


def create(user, data):
    body = {"name": "Vars", "description": "", "shared": False, "data": data}
    return client_for(user).post("/ui/v1/dashboards", body, format="json").json()


GOOD_VARIABLES = [
    {
        "name": "host",
        "label": "Host",
        "type": "values",
        "source": "clickhouse",
        "column": "hostname",
        "multi": True,
        "required": True,
        "default": ["a"],
    },
    {
        "name": "kind",
        "type": "static",
        "options": ["Select", "Insert"],
        "default": "Select",
    },
    {"name": "q", "type": "text"},
]


@pytest.mark.django_db
def test_dashboard_with_variables_round_trips(root_user, clickhouse_source):
    created = create(root_user, variables_data(clickhouse_source.slug, GOOD_VARIABLES))
    assert created["result"] is True, created
    variables = created["data"]["data"]["variables"]
    assert variables[0] == GOOD_VARIABLES[0]
    assert variables[2] == {
        "name": "q",
        "type": "text",
        "multi": False,
        "required": False,
    }
    assert created["data"]["data"]["version"] == 2


@pytest.mark.django_db
@pytest.mark.parametrize(
    "variable, errors",
    [
        ({"name": "1x", "type": "text"}, {"name"}),
        ({"name": "x", "type": "values", "source": "clickhouse"}, {"column"}),
        ({"name": "x", "type": "static"}, {"options"}),
        ({"name": "x", "type": "text", "options": ["a"]}, {"options"}),
        ({"name": "x", "type": "text", "multi": True}, {"multi"}),
        ({"name": "x", "type": "text", "default": ["a"]}, {"default"}),
        (
            {"name": "x", "type": "static", "options": ["a"], "default": "b"},
            {"default"},
        ),
        ({"name": "x", "type": "text", "color": "red"}, {"color"}),
        (
            {"name": "x", "type": "values", "source": "clickhouse", "column": "nope"},
            {"column"},
        ),
        (
            {"name": "x", "type": "values", "source": "missing", "column": "hostname"},
            {"source"},
        ),
    ],
)
def test_dashboard_variable_validation(root_user, clickhouse_source, variable, errors):
    created = create(root_user, variables_data(clickhouse_source.slug, [variable]))
    assert created["validation"]["result"] is False
    assert set(created["validation"]["fields"]["data"]["variables"]["0"]) == errors


@pytest.mark.django_db
def test_dashboard_duplicate_variable(root_user, clickhouse_source):
    variables = [{"name": "x", "type": "text"}, {"name": "x", "type": "text"}]
    created = create(root_user, variables_data(clickhouse_source.slug, variables))
    assert created["validation"]["fields"]["data"]["variables"] == {
        "1": {"name": ["duplicate variable x"]}
    }


@pytest.mark.django_db
def test_variable_source_needs_use_permission(test_user, clickhouse_source):
    data = variables_data(clickhouse_source.slug, GOOD_VARIABLES[:1])
    data["tiles"] = []
    created = create(test_user, data)
    assert created["validation"]["fields"]["data"]["variables"] == {
        "0": {"source": ["source clickhouse not found"]}
    }
    rbac_manager.grant_source_role(
        clickhouse_source, SourceRole.USER.value, user=test_user
    )
    assert create(test_user, data)["result"] is True


@pytest.mark.django_db
def test_v1_dashboard_loads_unchanged(root_user, dashboard):
    v1 = get_dashboard_data(dashboard.data["tiles"][0]["chart"]["source"])
    assert "version" not in dashboard.data
    got = client_for(root_user).get(f"/ui/v1/dashboards/{dashboard.slug}").json()
    data = got["data"]["data"]
    assert data == {**v1, "version": 2, "variables": []}
    assert Dashboard.objects.get(pk=dashboard.pk).data == v1


@pytest.mark.django_db
def test_v1_data_is_accepted_and_stored_as_v2(root_user, clickhouse_source):
    created = create(root_user, get_dashboard_data(clickhouse_source.slug))
    assert created["result"] is True
    stored = Dashboard.objects.get(slug=created["data"]["slug"]).data
    assert (stored["version"], stored["variables"]) == (2, [])


def test_upgrade_leaves_v2_alone():
    data = {"version": 2, "variables": [{"name": "x", "type": "text"}]}
    assert upgrade_dashboard_data(data) is data
    v1 = {"tiles": []}
    assert upgrade_dashboard_data(v1) == {"tiles": [], "version": 2, "variables": []}
    assert v1 == {"tiles": []}
