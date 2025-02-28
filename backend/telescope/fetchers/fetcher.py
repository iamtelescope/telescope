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
    def validate_query(self, query) -> bool:
        raise NotImplementedError

    @classmethod
    def autocomplete(self, request: AutocompleteRequest) -> AutocompleteResponse:
        raise NotImplementedError

    @classmethod
    def fetch_data(self, request: DataRequest) -> DataResponse:
        raise NotImplementedError

    @classmethod
    def fetch_graph_data(self, request: GraphDataRequest) -> GraphDataResponse:
        raise NotImplementedError
