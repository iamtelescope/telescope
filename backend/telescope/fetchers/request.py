from typing import List, Dict
from telescope.models import Source
from flyql.columns import ParsedColumn


class AutocompleteRequest:
    def __init__(
        self,
        source: Source,
        column: str,
        time_from: int,
        time_to: int,
        value: str,
    ):
        self.source = source
        self.column = column
        self.time_from = time_from
        self.time_to = time_to
        self.value = value


class DataRequest:
    def __init__(
        self,
        source: Source,
        query: str,
        raw_query: str,
        time_from: int,
        time_to: int,
        limit: int,
        context_columns: Dict,
        order_by_expression: str = "",
    ):
        self.source = source
        self.query = query
        self.raw_query = raw_query
        self.time_from = time_from
        self.time_to = time_to
        self.limit = limit
        self.context_columns = context_columns
        self.order_by_expression = order_by_expression


class GraphDataRequest:
    def __init__(
        self,
        source: Source,
        query: str,
        raw_query: str,
        time_from: int,
        time_to: int,
        group_by: List[ParsedColumn],
        context_columns: Dict,
    ):
        self.source = source
        self.query = query
        self.raw_query = raw_query
        self.time_from = time_from
        self.time_to = time_to
        self.group_by = group_by
        self.context_columns = context_columns


class DataAndGraphDataRequest:
    def __init__(
        self,
        source: Source,
        query: str,
        raw_query: str,
        time_from: int,
        time_to: int,
        limit: int,
        group_by: List[ParsedColumn],
        context_columns: Dict,
    ):
        self.source = source
        self.query = query
        self.raw_query = raw_query
        self.time_from = time_from
        self.time_to = time_to
        self.limit = limit
        self.group_by = group_by
        self.context_columns = context_columns
