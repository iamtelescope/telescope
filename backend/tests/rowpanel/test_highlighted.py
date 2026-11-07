"""P3.4: data.otel.highlighted, the per-source keys the Overview tab shows first."""

import pytest

from telescope.models import Source
from telescope.services.exceptions import SerializerValidationError
from telescope_otel.detect import detect
from telescope_otel.roles import validate_otel
from tests.otel import columns as C
from tests.otel.test_source_otel import payload

ERROR = "highlighted must be a list of at most 50 attribute keys"


def test_highlighted_is_a_list_of_keys():
    otel = {"signal": "logs", "highlighted": ["k8s.pod.name", "ServiceName"]}
    assert validate_otel(otel, None) == []


@pytest.mark.parametrize(
    "value", ["k8s.pod.name", [""], [1], ["x" * 257], ["k"] * 51, {"a": 1}]
)
def test_bad_highlighted_is_rejected(value):
    assert validate_otel({"signal": "logs", "highlighted": value}, None) == [ERROR]


@pytest.mark.django_db
def test_source_stores_highlighted(service, root_user, clickhouse_connection):
    otel = dict(detect("otel_logs", C.LOGS)["otel"], highlighted=["http.route"])
    service.create(user=root_user, data=payload("hl", clickhouse_connection, otel=otel))
    assert Source.objects.get(slug="hl").data["otel"]["highlighted"] == ["http.route"]
    otel["highlighted"] = "http.route"
    with pytest.raises(SerializerValidationError) as err:
        service.create(
            user=root_user, data=payload("hl2", clickhouse_connection, otel=otel)
        )
    assert err.value.serializer.errors["otel"] == [ERROR]
