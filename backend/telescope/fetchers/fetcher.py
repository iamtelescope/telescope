from typing import Optional
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
    def validate_query(cls, query) -> bool:
        raise NotImplementedError

    @classmethod
    def autocomplete(cls, request: AutocompleteRequest) -> AutocompleteResponse:
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
