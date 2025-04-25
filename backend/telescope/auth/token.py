from django.conf import settings
from django.contrib.auth import get_user_model

from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed

from telescope.models import APIToken


class TokenAuth(BaseAuthentication):
    def authenticate(self, request):
        if settings.CONFIG["auth"]["enable_testing_auth"]:
            model = get_user_model()
            user, created = model.objects.get_or_create(
                username=settings.CONFIG["auth"]["testing_auth_username"],
                defaults={
                    "is_superuser": True,
                },
            )
            return user, None
        else:
            auth_header = request.headers.get("Authorization")
            if not auth_header or not auth_header.startswith("Token "):
                return None
            token = auth_header.split(" ", 1)[1].strip()
            try:
                api_token = APIToken.objects.select_related("user").get(token=token)
            except APIToken.DoesNotExist:
                raise AuthenticationFailed("Permission denied")

            return api_token.user, None
