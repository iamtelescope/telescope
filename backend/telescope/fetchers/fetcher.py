from typing import Optional
import zoneinfo
from telescope.fetchers.request import (
    AutocompleteRequest,
    DataRequest,
    GraphDataRequest,
)
from telescope.fetchers.response import (
    AutocompleteResponse,
    DataResponse,
    GraphDataResponse,
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
