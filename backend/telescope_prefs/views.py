from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from rest_framework.views import APIView

from telescope_alerts.views import run
from telescope_prefs import services


class PinnedFacetsView(APIView):
    @method_decorator(login_required)
    def get(self, request, slug):
        return run(lambda: services.get_pinned(request.user, slug), "get pins")

    @method_decorator(login_required)
    def post(self, request, slug):
        return run(
            lambda: services.set_pinned(request.user, slug, request.data), "save pins"
        )


class FavoriteDashboardsView(APIView):
    @method_decorator(login_required)
    def get(self, request):
        return run(lambda: services.favorite_dashboards(request.user), "get favorites")


class FavoriteDashboardView(APIView):
    @method_decorator(login_required)
    def post(self, request, slug):
        return run(
            lambda: services.set_favorite_dashboard(request.user, slug, True),
            "add favorite",
        )

    @method_decorator(login_required)
    def delete(self, request, slug):
        return run(
            lambda: services.set_favorite_dashboard(request.user, slug, False),
            "remove favorite",
        )
