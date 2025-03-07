from typing import List, Dict
from telescope.fetchers.models import Row


class AutocompleteResponse:
    def __init__(
        self,
        items: List[str],
        incomplete: bool,
    ):
        self.items = items
        self.incomplete = incomplete


class DataResponse:
    def __init__(
        self,
        rows: List[Row],
    ):
        self.rows = rows


class GraphDataResponse:
    def __init__(
        self,
        timestamps: List[int],
        data: Dict[str, List[int]],
        total: int,
    ):
        self.timestamps = timestamps
        self.data = data
        self.total = total
