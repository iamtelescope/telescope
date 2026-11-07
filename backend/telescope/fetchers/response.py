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
        cursor: Optional[Dict] = None,
    ):
        self.rows = rows
        self.error = error
        self.message = message
        self.cursor = cursor


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


class ChartDataResponse:
    def __init__(
        self,
        kind: str,
        time_from: int,
        time_to: int,
        granularity: Optional[str] = None,
        step_ms: Optional[int] = None,
        timestamps: Optional[List[int]] = None,
        series: Optional[List[Dict]] = None,
        value=None,
        columns: Optional[List[Dict]] = None,
        rows: Optional[List[Dict]] = None,
        truncated: bool = False,
    ):
        self.kind = kind
        self.time_from = time_from
        self.time_to = time_to
        self.granularity = granularity
        self.step_ms = step_ms
        self.timestamps = timestamps or []
        self.series = series or []
        self.value = value
        self.columns = columns or []
        self.rows = rows or []
        self.truncated = truncated

    def as_dict(self) -> Dict:
        data = {"kind": self.kind, "from": self.time_from, "to": self.time_to}
        if self.kind == "timeseries":
            data.update(
                granularity=self.granularity,
                step_ms=self.step_ms,
                timestamps=self.timestamps,
                series=self.series,
                truncated=self.truncated,
            )
        elif self.kind == "number":
            data["value"] = self.value
        else:
            data.update(columns=self.columns, rows=self.rows, truncated=self.truncated)
        return data
