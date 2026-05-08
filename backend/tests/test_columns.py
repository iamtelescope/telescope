import pytest
from unittest.mock import MagicMock

from telescope.columns import ParsedColumn, parse_columns
from flyql.columns import ParserError as ColumnsParserError


class TestParsedColumn:
    def test_init(self):
        col = ParsedColumn(
            name="labels.app",
            root_name="labels",
            type="json",
            jsonstring=True,
            display_name="Application",
            transformers=[],
            renderers=[],
        )
        assert col.name == "labels.app"
        assert col.root_name == "labels"
        assert col.type == "json"
        assert col.jsonstring is True
        assert col.display_name == "Application"
        assert col.transformers == []
        assert col.renderers == []

    def test_as_dict_with_transformers(self):
        col = ParsedColumn(
            name="message",
            root_name="message",
            type="string",
            jsonstring=False,
            display_name="Message",
            transformers=[{"name": "upper", "arguments": []}],
            renderers=[],
        )
        result = col.as_dict()
        assert result["name"] == "message"
        assert result["root_name"] == "message"
        assert result["type"] == "string"
        assert result["jsonstring"] is False
        assert result["display_name"] == "Message"
        assert result["transformers"] == [{"name": "upper", "arguments": []}]
        assert result["renderers"] == []

    def test_as_dict_with_renderers(self):
        col = ParsedColumn(
            name="payload",
            root_name="payload",
            type="string",
            jsonstring=False,
            display_name="Payload",
            transformers=[{"name": "json", "arguments": []}],
            renderers=[{"name": "highlight", "arguments": []}],
        )
        result = col.as_dict()
        assert result["transformers"] == [{"name": "json", "arguments": []}]
        assert result["renderers"] == [{"name": "highlight", "arguments": []}]

    def test_as_dict_normalises_empty(self):
        col = ParsedColumn(
            name="message",
            root_name="message",
            type="string",
            jsonstring=False,
            display_name="Message",
        )
        result = col.as_dict()
        assert result["transformers"] == []
        assert result["renderers"] == []

    def test_is_map(self):
        col = ParsedColumn(
            "tags",
            "tags",
            "Map(String, String)",
            False,
            "Tags",
        )
        assert col.is_map() is True

        col2 = ParsedColumn("msg", "msg", "string", False, "Message")
        assert col2.is_map() is False

    def test_is_array(self):
        col = ParsedColumn("items", "items", "Array(String)", False, "Items")
        assert col.is_array() is True

        col2 = ParsedColumn("msg", "msg", "string", False, "Message")
        assert col2.is_array() is False


def _make_source(columns):
    source = MagicMock()
    source._columns = columns
    return source


def _make_column(name, type_="string", jsonstring=False, display_name=""):
    col = MagicMock()
    col.name = name
    col.type = type_
    col.jsonstring = jsonstring
    col.display_name = display_name
    return col


class TestParseColumns:
    def test_simple_column(self):
        source = _make_source(
            {"message": _make_column("message", "string", display_name="Message")}
        )

        result = parse_columns(source, "message")
        assert len(result) == 1
        assert result[0].name == "message"
        assert result[0].root_name == "message"
        assert result[0].type == "string"
        assert result[0].display_name == "Message"
        assert result[0].transformers == []
        assert result[0].renderers == []

    def test_nested_column(self):
        source = _make_source(
            {
                "labels": _make_column(
                    "labels", "json", jsonstring=True, display_name="Labels"
                )
            }
        )

        result = parse_columns(source, "labels.app")
        assert len(result) == 1
        assert result[0].name == "labels.app"
        assert result[0].root_name == "labels"
        assert result[0].type == "json"
        assert result[0].jsonstring is True

    def test_multiple_columns(self):
        source = _make_source(
            {
                "message": _make_column("message"),
                "status": _make_column("status", "int64", display_name="Status"),
            }
        )

        result = parse_columns(source, "message, status")
        assert len(result) == 2
        assert result[0].name == "message"
        assert result[1].name == "status"

    def test_column_with_alias(self):
        source = _make_source(
            {"message": _make_column("message", display_name="Log Message")}
        )

        result = parse_columns(source, "message as msg")
        assert len(result) == 1
        assert result[0].display_name == "msg"

    def test_column_with_transformers(self):
        source = _make_source({"message": _make_column("message")})

        result = parse_columns(source, "message|upper|chars(10)")
        assert len(result) == 1
        names = [t["name"] for t in result[0].transformers]
        assert names == ["upper", "chars"]
        assert result[0].renderers == []

    def test_unknown_column_raises_error(self):
        source = _make_source({"message": _make_column("message")})

        with pytest.raises(ColumnsParserError) as exc_info:
            parse_columns(source, "unknown_column")

        assert "unknown_column" in str(exc_info.value)
        assert exc_info.value.errno == 100

    def test_nested_unknown_root_raises_error(self):
        source = _make_source({"labels": _make_column("labels", "json")})

        with pytest.raises(ColumnsParserError) as exc_info:
            parse_columns(source, "unknown.nested.field")

        assert "unknown" in str(exc_info.value)
