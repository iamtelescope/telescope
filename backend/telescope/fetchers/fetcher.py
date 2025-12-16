from typing import Any, Optional
import zoneinfo
from telescope.fetchers.request import (
    AutocompleteRequest,
    DataRequest,
    GraphDataRequest,
    DataAndGraphDataRequest,
)
from telescope.fetchers.response import (
    AutocompleteResponse,
    DataResponse,
    GraphDataResponse,
    DataAndGraphDataResponse,
)


class BaseFetcher:
    @classmethod
    def validate_query(cls, source, query) -> tuple[bool, Any]:
        raise NotImplementedError

    @classmethod
    def autocomplete(cls, source, field, time_from, time_to, value) -> AutocompleteResponse:
        raise NotImplementedError

    @classmethod
    def fetch_data(
        cls, request: DataRequest, tz: Optional[zoneinfo.ZoneInfo] = None
    ) -> DataResponse:
        raise NotImplementedError

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
