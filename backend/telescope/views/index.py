from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.conf import settings
from django.http import HttpResponse

from rest_framework.views import APIView
from rest_framework.response import Response

from telescope.response import UIResponse
from telescope.models import HealthCheck


@login_required
def index(request):
    from django.conf import settings

    return render(request, "index.html", {"base_url": settings.BASE_URL or ""})


class ConfigView(APIView):
    @method_decorator(login_required)
    def get(self, request):
        response = UIResponse()
        response.data = settings.CONFIG.get("frontend", {})
        return Response(response.as_dict())


def liveness(request):
    return HttpResponse("ok", content_type="text/plain")


def readiness(request):
    try:
        HealthCheck.objects.get(key="status")
        return HttpResponse("ok", content_type="text/plain")
    except Exception:
        return HttpResponse("error", status=503, content_type="text/plain")
