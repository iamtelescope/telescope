from django.conf import settings
from django.contrib.auth import get_user_model, login


class TestingAuthMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        model = get_user_model()
        user, created = model.objects.get_or_create(
            username=settings.CONFIG["auth"]["testing_auth_username"],
            defaults={
                "is_superuser": True,
            },
        )
        login(request, user, backend="django.contrib.auth.backends.ModelBackend")
        return self.get_response(request)
