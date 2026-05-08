from typing import List, Dict, Optional
from telescope.fetchers.models import Row


class AutocompleteResponse:
    def __init__(
        self,
        items: List[str],
        incomplete: bool,
    ):
        self.items = items
        self.incomplete = incomplete


class JsonKeyEntry:
    def __init__(self, name: str, type: str, has_children: bool):
        self.name = name
        self.type = type
        self.has_children = has_children

    def as_dict(self) -> Dict[str, object]:
        return {
            "name": self.name,
            "type": self.type,
            "hasChildren": self.has_children,
        }


class JsonKeysResponse:
    def __init__(self, keys: List[JsonKeyEntry]):
        self.keys = keys


class DataResponse:
    def __init__(
        self,
        rows: List[Row],
        error: Optional[str] = None,
        message: Optional[str] = None,
    ):
        self.rows = rows
        self.error = error
        self.message = message


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


class DataAndGraphDataResponse:
    def __init__(
        self,
        rows: List[Row],
        graph_timestamps: List[int],
        graph_data: Dict[str, List[int]],
        graph_total: int,
        error: Optional[str] = None,
        message: Optional[str] = None,
    ):
        self.rows = rows
        self.graph_timestamps = graph_timestamps
        self.graph_data = graph_data
        self.graph_total = graph_total
        self.error = error
        self.message = message
