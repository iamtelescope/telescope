from typing import List
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
        time_from: int,
        time_to: int,
        limit: int,
    ):
        self.source = source
        self.query = query
        self.time_from = time_from
        self.time_to = time_to
        self.limit = limit


class GraphDataRequest:
    def __init__(
        self,
        source: Source,
        query: str,
        time_from: int,
        time_to: int,
        group_by: List[ParsedField],
    ):
        self.source = source
        self.query = query
        self.time_from = time_from
        self.time_to = time_to
        self.group_by = group_by
