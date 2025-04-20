from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed

from telescope.models import APIToken


class TokenAuth(BaseAuthentication):
    def authenticate(self, request):
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Token "):
            return None
        token = auth_header.split(" ", 1)[1].strip()
        try:
            api_token = APIToken.objects.select_related("user").get(token=token)
        except APIToken.DoesNotExist:
            raise AuthenticationFailed("Permission denied")

        return api_token.user, None
