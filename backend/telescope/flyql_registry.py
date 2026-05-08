"""Telescope's shared FlyQL transformer + renderer registries.

Built on top of FlyQL 0.0.48's `Transformer` / `Renderer` ABCs. These
registries are passed to every backend call site (fetchers, serializers,
SQL generators, matcher evaluators) so there is exactly one source of
truth for the transformer/renderer vocabulary across the stack.

Transformers are "registry-first": Telescope's definitions override any
same-named FlyQL built-in. UI-only transformers (`chars`, `json`, `fmt`,
…) raise `FlyqlError` from `sql()` so they error clearly if someone tries
to use them in a WHERE clause.
"""

import json as _json
from typing import Any, ClassVar, List, Optional, Tuple

import sqlparse

from flyql import (
    ArgSpec,
    FlyqlError,
    Renderer,
    RendererRegistry,
    Transformer,
    TransformerRegistry,
    Type,
)

# ---------------------------------------------------------------------------
# Transformers
# ---------------------------------------------------------------------------


def _ui_only_sql(name: str) -> str:
    raise FlyqlError(f"transformer '{name}' is UI-only and cannot be used in queries")


class CharsTransformer(Transformer):
    name = "chars"
    input_type = Type.String
    output_type = Type.String
    arg_schema: ClassVar[Tuple[ArgSpec, ...]] = (
        ArgSpec(type=Type.Int, required=True),
        ArgSpec(type=Type.Int, required=False),
    )

    def sql(self, dialect, column_ref, args=None):
        return _ui_only_sql(self.name)

    def apply(self, value, args=None):
        if value is None:
            return value
        a = args or []
        if not a:
            return value
        try:
            if len(a) >= 2:
                start = int(a[0])
                end = int(a[1])
            else:
                start = 0
                end = int(a[0])
            return str(value)[start:end]
        except (TypeError, ValueError):
            return value


class LinesTransformer(Transformer):
    name = "lines"
    input_type = Type.String
    output_type = Type.String
    arg_schema: ClassVar[Tuple[ArgSpec, ...]] = (
        ArgSpec(type=Type.Int, required=True),
        ArgSpec(type=Type.Int, required=False),
    )

    def sql(self, dialect, column_ref, args=None):
        return _ui_only_sql(self.name)

    def apply(self, value, args=None):
        if value is None:
            return value
        a = args or []
        if not a:
            return value
        try:
            if len(a) >= 2:
                start = int(a[0])
                end = int(a[1])
            else:
                start = 0
                end = int(a[0])
            return "\n".join(str(value).splitlines()[start:end])
        except (TypeError, ValueError):
            return value


class FirstlineTransformer(Transformer):
    name = "firstline"
    input_type = Type.String
    output_type = Type.String

    def sql(self, dialect, column_ref, args=None):
        return _ui_only_sql(self.name)

    def apply(self, value, args=None):
        if value is None:
            return value
        lines = str(value).splitlines()
        return lines[0] if lines else ""


class LastlineTransformer(Transformer):
    name = "lastline"
    input_type = Type.String
    output_type = Type.String

    def sql(self, dialect, column_ref, args=None):
        return _ui_only_sql(self.name)

    def apply(self, value, args=None):
        if value is None:
            return value
        lines = str(value).splitlines()
        return lines[-1] if lines else ""


class OnelineTransformer(Transformer):
    name = "oneline"
    input_type = Type.String
    output_type = Type.String

    def sql(self, dialect, column_ref, args=None):
        return _ui_only_sql(self.name)

    def apply(self, value, args=None):
        if value is None:
            return value
        return str(value).replace("\r\n", "").replace("\r", "").replace("\n", "")


class LowerTransformer(Transformer):
    name = "lower"
    input_type = Type.String
    output_type = Type.String

    def sql(self, dialect, column_ref, args=None):
        if dialect == "starrocks":
            return f"LOWER({column_ref})"
        return f"lower({column_ref})"

    def apply(self, value, args=None):
        if value is None:
            return value
        return str(value).lower()


class UpperTransformer(Transformer):
    name = "upper"
    input_type = Type.String
    output_type = Type.String

    def sql(self, dialect, column_ref, args=None):
        if dialect == "starrocks":
            return f"UPPER({column_ref})"
        return f"upper({column_ref})"

    def apply(self, value, args=None):
        if value is None:
            return value
        return str(value).upper()


class SliceTransformer(Transformer):
    name = "slice"
    input_type = Type.String
    output_type = Type.String
    arg_schema: ClassVar[Tuple[ArgSpec, ...]] = (
        ArgSpec(type=Type.Int, required=True),
        ArgSpec(type=Type.Int, required=False),
    )

    def sql(self, dialect, column_ref, args=None):
        return _ui_only_sql(self.name)

    def apply(self, value, args=None):
        if value is None:
            return value
        a = args or []
        try:
            start = int(a[0]) if len(a) >= 1 else 0
            if len(a) >= 2:
                end = int(a[1])
                return value[start:end]
            return value[start:]
        except (TypeError, ValueError):
            return value


class SplitTransformer(Transformer):
    name = "split"
    input_type = Type.String
    output_type = Type.Array
    arg_schema: ClassVar[Tuple[ArgSpec, ...]] = (
        ArgSpec(type=Type.String, required=False),
    )

    def sql(self, dialect, column_ref, args=None):
        a = args or []
        delimiter = a[0] if a else ","
        escaped = "'" + str(delimiter).replace("\\", "\\\\").replace("'", "\\'") + "'"
        if dialect == "clickhouse":
            if len(str(delimiter)) == 1:
                return f"splitByChar({escaped}, {column_ref})"
            return f"splitByString({escaped}, {column_ref})"
        if dialect == "starrocks":
            return f"SPLIT({column_ref}, {escaped})"
        return f"STRING_TO_ARRAY({column_ref}, {escaped})"

    def apply(self, value, args=None):
        if value is None:
            return value
        a = args or []
        delimiter = a[0] if a else ","
        return str(value).split(str(delimiter))


class JoinTransformer(Transformer):
    name = "join"
    input_type = Type.Array
    output_type = Type.String
    arg_schema: ClassVar[Tuple[ArgSpec, ...]] = (
        ArgSpec(type=Type.String, required=False),
    )

    def sql(self, dialect, column_ref, args=None):
        return _ui_only_sql(self.name)

    def apply(self, value, args=None):
        if not isinstance(value, (list, tuple)):
            return value
        a = args or []
        joiner = str(a[0]) if a else ","
        try:
            return joiner.join(str(v) for v in value)
        except Exception:
            return value


class JsonTransformer(Transformer):
    name = "json"
    input_type = Type.String
    output_type = Type.Unknown

    def sql(self, dialect, column_ref, args=None):
        return _ui_only_sql(self.name)

    def apply(self, value, args=None):
        if value is None:
            return value
        try:
            return _json.loads(value) if isinstance(value, str) else value
        except (ValueError, TypeError):
            return value


class StrTransformer(Transformer):
    name = "str"
    input_type = Type.Unknown
    output_type = Type.String

    def sql(self, dialect, column_ref, args=None):
        return _ui_only_sql(self.name)

    def apply(self, value, args=None):
        if value is None:
            return value
        if isinstance(value, (dict, list)):
            try:
                return _json.dumps(value)
            except (TypeError, ValueError):
                return str(value)
        return str(value)


class TypeTransformer(Transformer):
    name = "type"
    input_type = Type.Unknown
    output_type = Type.String

    def sql(self, dialect, column_ref, args=None):
        return _ui_only_sql(self.name)

    def apply(self, value, args=None):
        if value is None:
            return "null"
        if isinstance(value, bool):
            return "boolean"
        if isinstance(value, (int, float)):
            return "number"
        if isinstance(value, str):
            return "string"
        if isinstance(value, (list, tuple)):
            return "array"
        if isinstance(value, dict):
            return "object"
        return type(value).__name__


_SQL_KEYWORDS = {
    "select",
    "insert",
    "update",
    "create",
    "grant",
    "revoke",
    "alter",
    "drop",
    "begin",
    "commit",
    "rollback",
    "with",
    "explain",
    "show",
    "set",
    "start",
}


def _detect_lang(value: Any) -> Optional[str]:
    if isinstance(value, (dict, list)):
        return "json"
    if not isinstance(value, str):
        return None
    stripped = value.lstrip()
    if stripped.startswith(("{", "[")):
        return "json"
    first_word = ""
    for ch in stripped:
        if ch.isspace():
            break
        first_word += ch.lower()
    if first_word in _SQL_KEYWORDS:
        return "sql"
    return None


class FmtTransformer(Transformer):
    name = "fmt"
    input_type = Type.String
    output_type = Type.String
    arg_schema: ClassVar[Tuple[ArgSpec, ...]] = (
        ArgSpec(type=Type.String, required=False),
    )

    def sql(self, dialect, column_ref, args=None):
        return _ui_only_sql(self.name)

    def apply(self, value, args=None):
        if value is None:
            return value
        a = args or []
        lang = str(a[0]) if a else _detect_lang(value)
        if lang is None:
            return value
        try:
            if lang == "sql":
                return sqlparse.format(str(value), reindent=True, keyword_case="upper")
            if lang == "json":
                parsed = (
                    value if isinstance(value, (dict, list)) else _json.loads(value)
                )
                return _json.dumps(parsed, indent=4)
        except (ValueError, TypeError):
            return value
        return value


class FormatTransformer(FmtTransformer):
    name = "format"


# ---------------------------------------------------------------------------
# Renderers (display-only; no sql/apply)
# ---------------------------------------------------------------------------


class HighlightRenderer(Renderer):
    name = "highlight"
    arg_schema: ClassVar[Tuple[ArgSpec, ...]] = (
        ArgSpec(type=Type.String, required=False),
    )


class HlRenderer(Renderer):
    name = "hl"
    arg_schema: ClassVar[Tuple[ArgSpec, ...]] = (
        ArgSpec(type=Type.String, required=False),
    )


class HrefRenderer(Renderer):
    name = "href"
    arg_schema: ClassVar[Tuple[ArgSpec, ...]] = (
        ArgSpec(type=Type.String, required=True),
        ArgSpec(type=Type.String, required=False),
    )


# ---------------------------------------------------------------------------
# Registry factories
# ---------------------------------------------------------------------------


# NOTE: ``migrations/0023_split_source_modifiers.py`` carries its own frozen
# copy of these names — Django migrations must be deterministic, so it does
# not import from this module. If you add or rename a transformer/renderer
# here, the migration list does NOT need to follow (it only matters for
# splitting historical ``source.modifiers`` rows on first deploy of 0023).
_TRANSFORMER_CLASSES: List[type] = [
    CharsTransformer,
    LinesTransformer,
    FirstlineTransformer,
    LastlineTransformer,
    OnelineTransformer,
    LowerTransformer,
    UpperTransformer,
    SliceTransformer,
    SplitTransformer,
    JoinTransformer,
    JsonTransformer,
    StrTransformer,
    TypeTransformer,
    FmtTransformer,
    FormatTransformer,
]


_RENDERER_CLASSES: List[type] = [
    HighlightRenderer,
    HlRenderer,
    HrefRenderer,
]


def _build_transformer_registry() -> TransformerRegistry:
    registry = TransformerRegistry()
    for cls in _TRANSFORMER_CLASSES:
        registry.register(cls())
    return registry


def _build_renderer_registry() -> RendererRegistry:
    registry = RendererRegistry()
    for cls in _RENDERER_CLASSES:
        registry.register(cls())
    return registry


_TRANSFORMER_REGISTRY: Optional[TransformerRegistry] = None
_RENDERER_REGISTRY: Optional[RendererRegistry] = None


def transformer_registry() -> TransformerRegistry:
    global _TRANSFORMER_REGISTRY
    if _TRANSFORMER_REGISTRY is None:
        _TRANSFORMER_REGISTRY = _build_transformer_registry()
    return _TRANSFORMER_REGISTRY


def renderer_registry() -> RendererRegistry:
    global _RENDERER_REGISTRY
    if _RENDERER_REGISTRY is None:
        _RENDERER_REGISTRY = _build_renderer_registry()
    return _RENDERER_REGISTRY
