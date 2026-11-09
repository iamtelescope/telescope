from typing import Any, Iterator, Optional
import zoneinfo
from telescope.fetchers.models import Row
from telescope.fetchers.request import (
    AutocompleteRequest,
    DataRequest,
    GraphDataRequest,
    DataAndGraphDataRequest,
    ChartDataRequest,
)
from telescope.fetchers.response import (
    AutocompleteResponse,
    DataResponse,
    GraphDataResponse,
    DataAndGraphDataResponse,
    JsonKeysResponse,
    ChartDataResponse,
)


class BaseFetcher:
    @classmethod
    def validate_query(cls, source, query) -> tuple[bool, Any]:
        raise NotImplementedError

    @classmethod
    def autocomplete(
        cls, source, column, time_from, time_to, value
    ) -> AutocompleteResponse:
        raise NotImplementedError

    @classmethod
    def discover_json_keys(
        cls, source, column, segments, time_from, time_to
    ) -> JsonKeysResponse:
        return JsonKeysResponse(keys=[])

    @classmethod
    def fetch_data(
        cls, request: DataRequest, tz: Optional[zoneinfo.ZoneInfo] = None
    ) -> DataResponse:
        raise NotImplementedError

    @classmethod
    def stream_data(
        cls, request: DataRequest, tz: Optional[zoneinfo.ZoneInfo] = None
    ) -> Iterator[Row]:
        """Every row of the request (limit None); here one fetch_data, which reads all logs anyway."""
        response = cls.fetch_data(request, tz=tz)
        if response.error:
            raise ValueError(response.error)
        yield from response.rows

    @classmethod
    def fetch_graph_data(cls, request: GraphDataRequest) -> GraphDataResponse:
        raise NotImplementedError

    @classmethod
    def fetch_data_and_graph(
        cls,
        request: DataAndGraphDataRequest,
        tz: Optional[zoneinfo.ZoneInfo] = None,
    ) -> DataAndGraphDataResponse:
        raise NotImplementedError("Combined fetch not supported for this source type")

    @classmethod
    def fetch_chart_data(cls, request: ChartDataRequest) -> ChartDataResponse:
        raise NotImplementedError
