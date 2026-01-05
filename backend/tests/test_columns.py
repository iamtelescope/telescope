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
            modifiers=[],
        )
        assert col.name == "labels.app"
        assert col.root_name == "labels"
        assert col.type == "json"
        assert col.jsonstring is True
        assert col.display_name == "Application"

    def test_as_dict(self):
        col = ParsedColumn(
            name="message",
            root_name="message",
            type="string",
            jsonstring=False,
            display_name="Message",
            modifiers=[{"name": "upper", "arguments": []}],
        )
        result = col.as_dict()
        assert result["name"] == "message"
        assert result["root_name"] == "message"
        assert result["type"] == "string"
        assert result["jsonstring"] is False
        assert result["display_name"] == "Message"
        assert len(result["modifiers"]) == 1

    def test_is_map(self):
        col = ParsedColumn("tags", "tags", "Map(String, String)", False, "Tags", [])
        assert col.is_map() is True

        col2 = ParsedColumn("msg", "msg", "string", False, "Message", [])
        assert col2.is_map() is False

    def test_is_array(self):
        col = ParsedColumn("items", "items", "Array(String)", False, "Items", [])
        assert col.is_array() is True

        col2 = ParsedColumn("msg", "msg", "string", False, "Message", [])
        assert col2.is_array() is False


class TestParseColumns:
    def test_simple_column(self):
        mock_source = MagicMock()
        mock_column = MagicMock()
        mock_column.name = "message"
        mock_column.type = "string"
        mock_column.jsonstring = False
        mock_column.display_name = "Message"
        mock_source._columns = {"message": mock_column}

        result = parse_columns(mock_source, "message")
        assert len(result) == 1
        assert result[0].name == "message"
        assert result[0].root_name == "message"
        assert result[0].type == "string"
        assert result[0].display_name == "Message"

    def test_nested_column(self):
        mock_source = MagicMock()
        mock_column = MagicMock()
        mock_column.name = "labels"
        mock_column.type = "json"
        mock_column.jsonstring = True
        mock_column.display_name = "Labels"
        mock_source._columns = {"labels": mock_column}

        result = parse_columns(mock_source, "labels.app")
        assert len(result) == 1
        assert result[0].name == "labels.app"
        assert result[0].root_name == "labels"
        assert result[0].type == "json"
        assert result[0].jsonstring is True

    def test_multiple_columns(self):
        mock_source = MagicMock()
        mock_msg = MagicMock()
        mock_msg.name = "message"
        mock_msg.type = "string"
        mock_msg.jsonstring = False
        mock_msg.display_name = ""
        mock_status = MagicMock()
        mock_status.name = "status"
        mock_status.type = "int64"
        mock_status.jsonstring = False
        mock_status.display_name = "Status"
        mock_source._columns = {"message": mock_msg, "status": mock_status}

        result = parse_columns(mock_source, "message, status")
        assert len(result) == 2
        assert result[0].name == "message"
        assert result[1].name == "status"

    def test_column_with_alias(self):
        mock_source = MagicMock()
        mock_column = MagicMock()
        mock_column.name = "message"
        mock_column.type = "string"
        mock_column.jsonstring = False
        mock_column.display_name = "Log Message"
        mock_source._columns = {"message": mock_column}

        result = parse_columns(mock_source, "message as msg")
        assert len(result) == 1
        assert result[0].display_name == "msg"

    def test_column_with_modifiers(self):
        mock_source = MagicMock()
        mock_column = MagicMock()
        mock_column.name = "message"
        mock_column.type = "string"
        mock_column.jsonstring = False
        mock_column.display_name = ""
        mock_source._columns = {"message": mock_column}

        result = parse_columns(mock_source, "message|upper|chars(10)")
        assert len(result) == 1
        assert len(result[0].modifiers) == 2

    def test_unknown_column_raises_error(self):
        mock_source = MagicMock()
        mock_source._columns = {"message": MagicMock()}

        with pytest.raises(ColumnsParserError) as exc_info:
            parse_columns(mock_source, "unknown_column")

        assert "unknown_column" in str(exc_info.value)
        assert exc_info.value.errno == 100

    def test_nested_unknown_root_raises_error(self):
        mock_source = MagicMock()
        mock_source._columns = {"labels": MagicMock()}

        with pytest.raises(ColumnsParserError) as exc_info:
            parse_columns(mock_source, "unknown.nested.field")

        assert "unknown" in str(exc_info.value)
