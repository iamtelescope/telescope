from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import NotFound

from telescope.services.source import SourceService
from telescope.auth.token import TokenAuth

source_srv = SourceService()


class ApiStubView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [TokenAuth]

    def get(self, *args, **kwargs):
        raise NotFound

    def post(self, *args, **kwargs):
        raise NotFound

    def patch(self, *args, **kwargs):
        raise NotFound

    def delete(self, *args, **kwargs):
        raise NotFound
