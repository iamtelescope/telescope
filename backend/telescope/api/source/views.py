from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from telescope.services.source import SourceService
from telescope.auth.token import TokenAuth

source_srv = SourceService()


class SourceView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [TokenAuth]

    def get(self, request, slug=None):
        if slug is None:
            return Response(source_srv.list(user=request.user))
        else:
            return Response(source_srv.get(user=request.user, slug=slug))

    def post(self, request):
        return Response(
            source_srv.create(user=request.user, data=request.data, raise_is_valid=True)
        )

    def patch(self, request, pk):
        return Response(
            source_srv.update(
                user=request.user, slug=pk, data=request.data, raise_is_valid=True
            )
        )

    def delete(self, request, pk):
        return Response(source_srv.delete(user=request.user, slug=pk))
