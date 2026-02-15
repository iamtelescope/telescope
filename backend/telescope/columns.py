from flyql.columns import (
    parse as parse_columns_flyql,
    ParserError as ColumnsParserError,
)


class ParsedColumn:
    def __init__(
        self,
        name,
        root_name,
        type,
        jsonstring,
        display_name,
        modifiers,
        segments=None,
        is_segmented=False,
    ):
        self.name = name
        self.root_name = root_name
        self.type = type
        self.jsonstring = jsonstring
        self.display_name = display_name
        self.modifiers = modifiers
        self.segments = segments
        self.is_segmented = is_segmented

    def as_dict(self):
        result = {
            "name": self.name,
            "root_name": self.root_name,
            "type": self.type,
            "jsonstring": self.jsonstring,
            "display_name": self.display_name,
            "modifiers": self.modifiers,
            "segments": self.segments,
            "is_segmented": self.is_segmented,
        }
        if self.segments:
            result["segments"] = self.segments
        return result

    def is_map(self):
        return "Map" in self.type

    def is_array(self):
        return "Array" in self.type


def parse_columns(source, text):
    flyql_columns = parse_columns_flyql(text)
    parsed_columns = []

    for flyql_col in flyql_columns:
        source_column_name = flyql_col.name.split(".")[0]

        if source_column_name not in source._columns:
            raise ColumnsParserError(
                message=f"Source have no '{source_column_name}' column", errno=100
            )

        source_column = source._columns[source_column_name]
        titled_name = (
            flyql_col.name.title() if ":" not in flyql_col.name else flyql_col.name
        )
        display_name = (
            flyql_col.alias
            if flyql_col.alias
            else source_column.display_name or titled_name
        )

        parsed_columns.append(
            ParsedColumn(
                name=flyql_col.name,
                root_name=source_column.name,
                type=source_column.type,
                jsonstring=source_column.jsonstring,
                display_name=display_name,
                modifiers=flyql_col.modifiers,
                segments=flyql_col.segments,
                is_segmented=flyql_col.is_segmented,
            )
        )

    return parsed_columns
