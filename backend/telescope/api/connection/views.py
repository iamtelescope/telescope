from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from telescope.services.connection import ConnectionService
from telescope.auth.token import TokenAuth

connection_srv = ConnectionService()


class ConnectionView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [TokenAuth]

    def get(self, request, pk=None):
        if pk is None:
            return Response(connection_srv.list(user=request.user))
        else:
            return Response(connection_srv.get(user=request.user, pk=pk))

    def post(self, request):
        return Response(
            connection_srv.create(
                user=request.user, data=request.data, raise_is_valid=True
            )
        )

    def patch(self, request, pk):
        return Response(
            connection_srv.update(
                user=request.user, pk=pk, data=request.data, raise_is_valid=True
            )
        )

    def delete(self, request, pk):
        return Response(connection_srv.delete(user=request.user, pk=pk))
