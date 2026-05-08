from flyql import FlyqlError, Type
from flyql.columns import (
    parse as parse_columns_flyql,
    diagnose as diagnose_columns,
    ParserError as ColumnsParserError,
)
from flyql.core.column import Column as FlyqlColumn, ColumnSchema
from flyql.core.validator import CODE_UNKNOWN_COLUMN

from telescope.flyql_errors import format_flyql_error
from telescope.flyql_registry import renderer_registry, transformer_registry
from telescope.models import Source

COLUMNS_CAPABILITIES = {"transformers": True, "renderers": True}


def _build_validation_schema(source: Source) -> ColumnSchema:
    """Build a minimal ``ColumnSchema`` for ``flyql.columns.diagnose`` — we
    only need it to enumerate valid column names so transformer/renderer
    checks can run; actual column-type validation is handled elsewhere in
    Telescope, so every column is typed as ``Unknown`` here.
    """
    cols = {
        name: FlyqlColumn(name=name, column_type=Type.Unknown, match_name=name)
        for name in source._columns.keys()
    }
    return ColumnSchema(cols)


class ParsedColumn:
    def __init__(
        self,
        name,
        root_name,
        type,
        jsonstring,
        display_name,
        transformers=None,
        renderers=None,
        segments=None,
        is_segmented=False,
    ):
        self.name = name
        self.root_name = root_name
        self.type = type
        self.jsonstring = jsonstring
        self.display_name = display_name
        self.transformers = list(transformers) if transformers else []
        self.renderers = list(renderers) if renderers else []
        self.segments = segments
        self.is_segmented = is_segmented

    def as_dict(self):
        return {
            "name": self.name,
            "root_name": self.root_name,
            "type": self.type,
            "jsonstring": self.jsonstring,
            "display_name": self.display_name,
            "transformers": self.transformers,
            "renderers": self.renderers,
            "segments": self.segments,
            "is_segmented": self.is_segmented,
        }

    def is_map(self):
        return "map" in self.type.lower()

    def is_array(self):
        return "array" in self.type.lower()

    def is_json(self):
        return "json" in self.type.lower()


def parse_columns(source: Source, text: str) -> list[ParsedColumn]:
    flyql_columns = parse_columns_flyql(text, capabilities=COLUMNS_CAPABILITIES)

    # Validate transformer/renderer names and argument shapes against the
    # shared registries. Column-name errors are filtered out because
    # Telescope resolves dotted paths against ``source._columns`` below with
    # richer semantics than flyql's segment walker.
    for diag in diagnose_columns(
        flyql_columns,
        _build_validation_schema(source),
        registry=transformer_registry(),
        renderer_registry=renderer_registry(),
    ):
        if diag.severity == "error" and diag.code != CODE_UNKNOWN_COLUMN:
            raise FlyqlError(format_flyql_error(text, diag))

    parsed_columns = []

    for flyql_col in flyql_columns:
        renderers = list(flyql_col.renderers or [])
        if len(renderers) > 1:
            raise FlyqlError(
                f"at most one renderer per column (got {len(renderers)} on '{flyql_col.name}')"
            )

        # Column names can contain periods, and so we should split reluctantly and match
        # the longest possible column name from the source.
        source_column_name = None
        candidate = flyql_col.name
        while candidate:
            if candidate in source._columns:
                source_column_name = candidate
                break
            # Remove the last dot-separated suffix
            last_dot = candidate.rfind(".")
            if last_dot == -1:
                break
            candidate = candidate[:last_dot]

        if not source_column_name:
            raise ColumnsParserError(
                message=f"Source have no '{flyql_col.name}' column", errno=100
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
                transformers=list(flyql_col.transformers or []),
                renderers=renderers,
                segments=flyql_col.segments,
                is_segmented=flyql_col.is_segmented,
            )
        )

    return parsed_columns
