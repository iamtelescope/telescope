"""data.otel through the source create/update service (the serializer hook)."""

import pytest

from telescope.models import Source
from telescope.services.exceptions import SerializerValidationError
from telescope_otel.detect import detect
from tests.otel import columns as C


def payload(slug, conn, cols=C.LOGS, table="otel_logs", otel=..., **changes):
    data = {"database": "otel", "table": table}
    if otel is ...:
        otel = detect(table, cols)["otel"]
    if otel is not None or "otel" in changes:
        data["otel"] = otel
    body = {
        "kind": "clickhouse",
        "slug": slug,
        "name": slug,
        "description": "",
        "time_column": "Timestamp",
        "date_column": "",
        "severity_column": "",
        "default_chosen_columns": "Timestamp",
        "columns": C.source_columns(cols),
        "connection": {"connection_id": conn.id},
        "data": data,
    }
    body.update(changes)
    return body


@pytest.mark.django_db
def test_create_stores_otel(service, root_user, clickhouse_connection):
    service.create(user=root_user, data=payload("otl", clickhouse_connection))
    otel = Source.objects.get(slug="otl").data["otel"]
    assert otel["signal"] == "logs"
    assert otel["roles"]["trace_id"] == "TraceId"


@pytest.mark.django_db
def test_create_rejects_missing_column(service, root_user, clickhouse_connection):
    otel = {"signal": "logs", "roles": {"trace_id": "trace_id"}}
    with pytest.raises(SerializerValidationError) as err:
        service.create(
            user=root_user, data=payload("otl", clickhouse_connection, otel=otel)
        )
    assert err.value.serializer.errors["otel"] == ["column trace_id not found"]
    assert not Source.objects.filter(slug="otl").exists()


@pytest.mark.django_db
def test_create_rejects_unknown_link(service, root_user, clickhouse_connection):
    otel = {"signal": "logs", "links": {"traces": "nope"}}
    with pytest.raises(SerializerValidationError) as err:
        service.create(
            user=root_user, data=payload("otl", clickhouse_connection, otel=otel)
        )
    assert err.value.serializer.errors["otel"] == ["source nope not found"]


@pytest.mark.django_db
def test_links_between_sources(service, root_user, clickhouse_connection):
    service.create(
        user=root_user,
        data=payload("tr", clickhouse_connection, cols=C.TRACES, table="otel_traces"),
    )
    otel = dict(detect("otel_logs", C.LOGS)["otel"], links={"traces": "tr"})
    service.create(user=root_user, data=payload("lg", clickhouse_connection, otel=otel))
    assert Source.objects.get(slug="lg").data["otel"]["links"] == {"traces": "tr"}


@pytest.mark.django_db
def test_source_without_otel_has_no_block(service, root_user, clickhouse_connection):
    service.create(
        user=root_user, data=payload("plain", clickhouse_connection, otel=None)
    )
    assert Source.objects.get(slug="plain").data == {
        "database": "otel",
        "table": "otel_logs",
    }


@pytest.mark.django_db
def test_null_otel_is_dropped(service, root_user, clickhouse_connection):
    body = payload("nul", clickhouse_connection, otel=None)
    body["data"]["otel"] = None
    service.create(user=root_user, data=body)
    assert "otel" not in Source.objects.get(slug="nul").data


@pytest.mark.django_db
def test_update_keeps_validating(service, root_user, clickhouse_connection):
    service.create(user=root_user, data=payload("otl", clickhouse_connection))
    bad = payload(
        "otl", clickhouse_connection, otel={"signal": "logs", "roles": {"body": "msg"}}
    )
    with pytest.raises(SerializerValidationError) as err:
        service.update(user=root_user, slug="otl", data=bad)
    assert err.value.serializer.errors["otel"] == ["column msg not found"]
    # Saving without the block removes the roles, as the wizard does when they are turned off.
    service.update(
        user=root_user,
        slug="otl",
        data=payload("otl", clickhouse_connection, otel=None),
    )
    assert "otel" not in Source.objects.get(slug="otl").data
