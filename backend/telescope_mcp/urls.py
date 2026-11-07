from django.urls import path

from telescope_mcp.views import McpView

urlpatterns = [
    path("api/mcp", McpView.as_view()),
    path("api/mcp/", McpView.as_view()),
]
