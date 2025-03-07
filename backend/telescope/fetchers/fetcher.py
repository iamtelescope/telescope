from telescope.fetchers.request import AutocompleteRequest, DataRequest
from telescope.fetchers.response import AutocompleteResponse, DataResponse


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
