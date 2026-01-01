import pytest
from unittest.mock import MagicMock
from datetime import datetime

from telescope.fetchers.graph_utils import generate_graph_from_rows
from telescope.fetchers.models import Row
from telescope.fields import ParsedField
from telescope.constants import UTC_ZONE


@pytest.fixture
def mock_source():
    source = MagicMock()
    source.id = 1
    source.name = "test-source"
    source.time_field = "time"
    source.uniq_field = "id"
    source._record_pseudo_id_field = "_id"
    return source


def create_row(source, timestamp_ms, data_dict):
    timestamp = datetime.fromtimestamp(timestamp_ms / 1000, UTC_ZONE)

    fields = ["time"] + [k for k in data_dict.keys() if k != "time"]
    values = [timestamp] + [data_dict[k] for k in data_dict.keys() if k != "time"]

    return Row(
        source=source,
        selected_fields=fields,
        values=values,
        tz=UTC_ZONE,
    )


def test_generate_graph_basic(mock_source):
    time_from = 1000000000000
    time_to = 1000000010000

    rows = [
        create_row(mock_source, 1000000001000, {"message": "log1"}),
        create_row(mock_source, 1000000002000, {"message": "log2"}),
        create_row(mock_source, 1000000003000, {"message": "log3"}),
    ]

    timestamps, data, total = generate_graph_from_rows(rows, time_from, time_to, None)

    assert len(timestamps) >= 2
    assert timestamps[0] == time_from
    assert timestamps[-1] == time_to
    assert total == 3
    assert "Rows" in data
    assert sum(data["Rows"]) == 3


def test_generate_graph_with_grouping(mock_source):
    time_from = 1000000000000
    time_to = 1000000010000

    rows = [
        create_row(
            mock_source, 1000000001000, {"namespace": "default", "message": "log1"}
        ),
        create_row(
            mock_source, 1000000002000, {"namespace": "default", "message": "log2"}
        ),
        create_row(
            mock_source, 1000000003000, {"namespace": "kube-system", "message": "log3"}
        ),
        create_row(
            mock_source, 1000000004000, {"namespace": "kube-system", "message": "log4"}
        ),
        create_row(
            mock_source, 1000000005000, {"namespace": "app-ns", "message": "log5"}
        ),
    ]

    group_by = ParsedField(
        name="namespace",
        root_name="namespace",
        type="string",
        jsonstring=False,
        display_name="namespace",
        modifiers=[],
    )

    timestamps, data, total = generate_graph_from_rows(
        rows, time_from, time_to, group_by
    )

    assert total == 5
    assert "default" in data
    assert "kube-system" in data
    assert "app-ns" in data
    assert sum(data["default"]) == 2
    assert sum(data["kube-system"]) == 2
    assert sum(data["app-ns"]) == 1


def test_generate_graph_json_grouping(mock_source):
    time_from = 1000000000000
    time_to = 1000000010000

    rows = [
        create_row(mock_source, 1000000001000, {"labels": '{"app": "frontend"}'}),
        create_row(mock_source, 1000000002000, {"labels": '{"app": "frontend"}'}),
        create_row(mock_source, 1000000003000, {"labels": '{"app": "backend"}'}),
        create_row(mock_source, 1000000004000, {"labels": '{"app": "worker"}'}),
    ]

    group_by = ParsedField(
        name="labels:app",
        root_name="labels",
        type="json",
        jsonstring=True,
        display_name="labels:app",
        modifiers=[],
    )

    timestamps, data, total = generate_graph_from_rows(
        rows, time_from, time_to, group_by
    )

    assert total == 4
    assert "frontend" in data
    assert "backend" in data
    assert "worker" in data
    assert sum(data["frontend"]) == 2
    assert sum(data["backend"]) == 1
    assert sum(data["worker"]) == 1


def test_generate_graph_json_nested_grouping(mock_source):
    time_from = 1000000000000
    time_to = 1000000010000

    rows = [
        create_row(
            mock_source, 1000000001000, {"metadata": '{"labels": {"tier": "frontend"}}'}
        ),
        create_row(
            mock_source, 1000000002000, {"metadata": '{"labels": {"tier": "backend"}}'}
        ),
    ]

    group_by = ParsedField(
        name="metadata:labels:tier",
        root_name="metadata",
        type="json",
        jsonstring=True,
        display_name="metadata:labels:tier",
        modifiers=[],
    )

    timestamps, data, total = generate_graph_from_rows(
        rows, time_from, time_to, group_by
    )

    assert total == 2
    assert "frontend" in data
    assert "backend" in data


def test_generate_graph_missing_group_field(mock_source):
    time_from = 1000000000000
    time_to = 1000000010000

    rows = [
        create_row(mock_source, 1000000001000, {"namespace": "default"}),
        create_row(mock_source, 1000000002000, {"message": "no namespace"}),
        create_row(mock_source, 1000000003000, {"namespace": "kube-system"}),
    ]

    group_by = ParsedField(
        name="namespace",
        root_name="namespace",
        type="string",
        jsonstring=False,
        display_name="namespace",
        modifiers=[],
    )

    timestamps, data, total = generate_graph_from_rows(
        rows, time_from, time_to, group_by
    )

    assert total == 3
    assert "default" in data
    assert "kube-system" in data
    assert "__none__" in data
    assert sum(data["__none__"]) == 1


def test_generate_graph_large_timespan(mock_source):
    time_from = 1000000000000
    time_to = 1000000000000 + (3600 * 1000)

    rows = []
    for i in range(200):
        timestamp = time_from + (i * 10 * 1000)
        rows.append(create_row(mock_source, timestamp, {"message": f"log{i}"}))

    timestamps, data, total = generate_graph_from_rows(rows, time_from, time_to, None)

    assert total == 200
    assert "Rows" in data
    assert len(timestamps) <= 152
    assert sum(data["Rows"]) == 200


def test_generate_graph_short_timespan(mock_source):
    time_from = 1000000000000
    time_to = 1000000005000

    rows = [
        create_row(mock_source, 1000000000500, {"message": "log1"}),
        create_row(mock_source, 1000000000700, {"message": "log2"}),
        create_row(mock_source, 1000000001200, {"message": "log3"}),
    ]

    timestamps, data, total = generate_graph_from_rows(rows, time_from, time_to, None)

    assert total == 3
    assert sum(data["Rows"]) == 3


def test_generate_graph_empty_rows(mock_source):
    time_from = 1000000000000
    time_to = 1000000010000

    timestamps, data, total = generate_graph_from_rows([], time_from, time_to, None)

    assert total == 0
    assert len(timestamps) == 2
    assert timestamps == [time_from, time_to]
    if data:
        assert "Rows" in data
        assert all(count == 0 for count in data["Rows"])


def test_generate_graph_invalid_json_grouping(mock_source):
    time_from = 1000000000000
    time_to = 1000000010000

    rows = [
        create_row(mock_source, 1000000001000, {"labels": "not valid json"}),
        create_row(mock_source, 1000000002000, {"labels": '{"app": "valid"}'}),
    ]

    group_by = ParsedField(
        name="labels:app",
        root_name="labels",
        type="json",
        jsonstring=True,
        display_name="labels:app",
        modifiers=[],
    )

    timestamps, data, total = generate_graph_from_rows(
        rows, time_from, time_to, group_by
    )

    assert total == 2
    assert "__none__" in data
    assert "valid" in data
    assert sum(data["__none__"]) == 1
    assert sum(data["valid"]) == 1


def test_generate_graph_same_timestamp(mock_source):
    time_from = 1000000000000
    time_to = 1000000010000

    same_time = 1000000001000
    rows = [
        create_row(mock_source, same_time, {"message": "log1"}),
        create_row(mock_source, same_time, {"message": "log2"}),
        create_row(mock_source, same_time, {"message": "log3"}),
    ]

    timestamps, data, total = generate_graph_from_rows(rows, time_from, time_to, None)

    assert total == 3
    assert sum(data["Rows"]) == 3
    max_bucket_count = max(data["Rows"])
    assert max_bucket_count == 3


def test_generate_graph_grouping_with_multiple_timestamps(mock_source):
    time_from = 1000000000000
    time_to = 1000000010000

    rows = [
        create_row(mock_source, 1000000001000, {"namespace": "default"}),
        create_row(mock_source, 1000000002000, {"namespace": "default"}),
        create_row(mock_source, 1000000005000, {"namespace": "default"}),
        create_row(mock_source, 1000000001000, {"namespace": "kube-system"}),
        create_row(mock_source, 1000000006000, {"namespace": "kube-system"}),
    ]

    group_by = ParsedField(
        name="namespace",
        root_name="namespace",
        type="string",
        jsonstring=False,
        display_name="namespace",
        modifiers=[],
    )

    timestamps, data, total = generate_graph_from_rows(
        rows, time_from, time_to, group_by
    )

    assert total == 5
    assert "default" in data
    assert "kube-system" in data
    assert len(data["default"]) == len(timestamps)
    assert len(data["kube-system"]) == len(timestamps)
    assert sum(data["default"]) == 3
    assert sum(data["kube-system"]) == 2
