from typing import List, Dict
from telescope.models import Source
from telescope.fields import ParsedField


class AutocompleteRequest:
    def __init__(
        self,
        source: Source,
        field: str,
        time_from: int,
        time_to: int,
        value: str,
    ):
        self.source = source
        self.field = field
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
        context_fields: Dict,
    ):
        self.source = source
        self.query = query
        self.raw_query = raw_query
        self.time_from = time_from
        self.time_to = time_to
        self.limit = limit
        self.context_fields = context_fields


class GraphDataRequest:
    def __init__(
        self,
        source: Source,
        query: str,
        raw_query: str,
        time_from: int,
        time_to: int,
        group_by: List[ParsedField],
        context_fields: Dict,
    ):
        self.source = source
        self.query = query
        self.raw_query = raw_query
        self.time_from = time_from
        self.time_to = time_to
        self.group_by = group_by
        self.context_fields = context_fields


class DataAndGraphDataRequest:
    def __init__(
        self,
        source: Source,
        query: str,
        raw_query: str,
        time_from: int,
        time_to: int,
        limit: int,
        group_by: List[ParsedField],
        context_fields: Dict,
    ):
        self.source = source
        self.query = query
        self.raw_query = raw_query
        self.time_from = time_from
        self.time_to = time_to
        self.limit = limit
        self.group_by = group_by
        self.context_fields = context_fields
