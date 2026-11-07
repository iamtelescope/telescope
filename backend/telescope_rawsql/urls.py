from django.urls import path

from telescope_rawsql import views

urlpatterns = [
    path("ui/v1/rawsql/connections", views.RawSqlConnectionsView.as_view()),
    path("ui/v1/rawsql/connections/<int:pk>/query", views.RawSqlQueryView.as_view()),
]
