from django.urls import path, re_path


import telescope.views.index as index
import telescope.views.rbac.views as rbac
import telescope.views.source.views as source
import telescope.views.auth.views as auth


urlpatterns = [
    path("login", auth.LoginView.as_view(), name="login"),
    path("logout", auth.LogoutView.as_view(), name="logout"),
    path("setup", auth.SuperuserView.as_view(), name="setup"),
    path("ui/v1/auth/whoami", auth.WhoAmIView.as_view()),
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
    path("ui/v1/sources/testConnection", source.SourceTestConnectionView.as_view()),
    path("ui/v1/sources/<slug:slug>", source.SourceView.as_view()),
    path("ui/v1/sources/<slug:slug>/logs", source.SourceLogsView.as_view()),
    path(
        "ui/v1/sources/<slug:slug>/autocomplete",
        source.SourceLogsAutocompleteView.as_view(),
    ),
    path(
        "ui/v1/sources/<slug:slug>/roleBindings", source.SourceRoleBindingView.as_view()
    ),
    path("ui/v1/sources/<slug:slug>/grantRole", source.SourceGrantRoleView.as_view()),
    path("ui/v1/sources/<slug:slug>/revokeRole", source.SourceRevokeRoleView.as_view()),
    path("ui/v1/sources/<slug:slug>", source.SourceView.as_view()),
    re_path("^.*$", index.index),
]
