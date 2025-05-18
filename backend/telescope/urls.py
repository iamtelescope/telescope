from django.urls import path, re_path


import telescope.views.index as index
import telescope.views.rbac.views as rbac
import telescope.views.source.views as source
import telescope.views.auth.views as auth

import telescope.api.source.views as source_api
import telescope.api.stub as stub_api

urlpatterns = [
    path("login", auth.LoginView.as_view(), name="login"),
    path("logout", auth.LogoutView.as_view(), name="logout"),
    path("setup", auth.SuperuserView.as_view(), name="setup"),
    path("api/v1/sources", source_api.SourceView.as_view()),
    path("api/v1/sources/", source_api.SourceView.as_view()),
    path("api/v1/sources/<slug:slug>", source_api.SourceView.as_view()),
    path("api/v1/sources/<slug:slug>/", source_api.SourceView.as_view()),
    path("ui/v1/config", index.ConfigView.as_view()),
    path("ui/v1/auth/whoami", auth.WhoAmIView.as_view()),
    path("ui/v1/auth/api_tokens", auth.UserAPITokenView.as_view()),
    path("ui/v1/auth/api_tokens/delete", auth.UserAPITokensDeleteView.as_view()),
    path("ui/v1/rbac/simpleusers", rbac.SimpleUserListView.as_view()),
    path("ui/v1/rbac/users", rbac.UserView.as_view()),
    path("ui/v1/rbac/users/<int:pk>", rbac.UserView.as_view()),
    path("ui/v1/rbac/simplegroups", rbac.SimpleGroupListView.as_view()),
    path("ui/v1/rbac/groups", rbac.GroupView.as_view()),
    path("ui/v1/rbac/groups/<int:pk>", rbac.GroupView.as_view()),
    path("ui/v1/rbac/groups/<int:pk>/addUsers", rbac.GroupAddUsersView.as_view()),
    path("ui/v1/rbac/groups/<int:pk>/removeUsers", rbac.GroupRemoveUsersView.as_view()),
    path("ui/v1/rbac/groups/<int:pk>/grantRole", rbac.GroupGrantRoleView.as_view()),
    path("ui/v1/rbac/groups/<int:pk>/revokeRole", rbac.GroupRevokeRoleView.as_view()),
    path("ui/v1/rbac/roles", rbac.RoleView.as_view()),
    path("ui/v1/rbac/roles/<slug:kind>/<slug:name>", rbac.RoleView.as_view()),
    path("ui/v1/sources", source.SourceView.as_view()),
    path(
        "ui/v1/services/testSourceConnection/<slug:kind>",
        source.SourceTestConnectionView.as_view(),
    ),
    path("ui/v1/sources/<slug:slug>", source.SourceView.as_view()),
    path("ui/v1/sources/<slug:slug>/savedViews", source.SourceSavedViewView.as_view()),
    path(
        "ui/v1/sources/<slug:slug>/savedViews/<slug:view_slug>",
        source.SourceSavedViewView.as_view(),
    ),
    path("ui/v1/sources/<slug:slug>/data", source.SourceDataView.as_view()),
    path("ui/v1/sources/<slug:slug>/graphData", source.SourceGraphDataView.as_view()),
    path(
        "ui/v1/sources/<slug:slug>/contextFieldData",
        source.SourceContextFieldDataView.as_view(),
    ),
    path(
        "ui/v1/sources/<slug:slug>/autocomplete",
        source.SourceDataAutocompleteView.as_view(),
    ),
    path(
        "ui/v1/sources/<slug:slug>/roleBindings", source.SourceRoleBindingView.as_view()
    ),
    path("ui/v1/sources/<slug:slug>/grantRole", source.SourceGrantRoleView.as_view()),
    path("ui/v1/sources/<slug:slug>/revokeRole", source.SourceRevokeRoleView.as_view()),
    path("ui/v1/sources/<slug:slug>", source.SourceView.as_view()),
    re_path("^api.*$", stub_api.ApiStubView.as_view()),
    re_path("^.*$", index.index),
]
