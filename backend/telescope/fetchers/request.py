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
    ):
        self.source = source
        self.query = query
        self.raw_query = raw_query
        self.time_from = time_from
        self.time_to = time_to
        self.limit = limit
        self.context_columns = context_columns


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


class ChartDataRequest:
    def __init__(
        self,
        source: Source,
        query: str,
        raw_query: str,
        time_from: int,
        time_to: int,
        context_columns: Dict,
        display: str,
        series: List[Dict],
        group_by: List[ParsedColumn],
        granularity: str,
        limit: int,
    ):
        self.source = source
        self.query = query
        self.raw_query = raw_query
        self.time_from = time_from
        self.time_to = time_to
        self.context_columns = context_columns
        self.display = display
        self.series = series
        self.group_by = group_by
        self.granularity = granularity
        self.limit = limit
