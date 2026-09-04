import pytest

from django.conf import settings
from django.contrib.auth.models import Group, User
from django.template.loader import render_to_string
from django.urls import reverse
from django.test import RequestFactory

from allauth.socialaccount.models import SocialAccount

from telescope.auth.forms import LoginForm
from telescope.models import Source, SourceRoleBinding
from telescope.rbac.manager import RBACManager
from telescope.rbac.permissions import Source as SourcePermission
from telescope.rbac.roles import SourceRole
from telescope.signals import add_keycloak_user_to_default_group
from telescope.views.auth.views import LoginView


@pytest.mark.django_db
def test_keycloak_oidc_app_uses_discovery_and_pkce():
    config = settings.SOCIALACCOUNT_PROVIDERS["openid_connect"]

    assert config["OAUTH_PKCE_ENABLED"] is True
    assert config["APPS"] == [
        {
            "provider_id": "keycloak",
            "name": "Keycloak",
            "client_id": "telescope",
            "secret": "test-keycloak-secret",
            "settings": {
                "server_url": "https://keycloak.example/realms/telescope",
            },
        }
    ]


@pytest.mark.django_db
def test_keycloak_login_and_callback_urls_are_reversible():
    assert (
        reverse("openid_connect_login", kwargs={"provider_id": "keycloak"})
        == "/login/oidc/keycloak/login/"
    )
    assert (
        reverse("openid_connect_callback", kwargs={"provider_id": "keycloak"})
        == "/login/oidc/keycloak/login/callback/"
    )


@pytest.mark.django_db
def test_login_page_shows_keycloak_post_button(root_user):
    request = RequestFactory().get("/login")
    context = dict(LoginView.extra_context)
    context["form"] = LoginForm()
    rendered = render_to_string("forms/login.html", context, request=request)

    assert 'id="keycloak_submit"' in rendered
    assert 'action="login/oidc/keycloak/login/"' in rendered
    assert 'name="csrfmiddlewaretoken"' in rendered


def test_forced_keycloak_template_clicks_keycloak_button():
    request = RequestFactory().get("/login")
    rendered = render_to_string(
        "forms/login.html",
        {
            "form": LoginForm(),
            "github_enabled": False,
            "okta_enabled": False,
            "keycloak_enabled": True,
            "force_auth_provider": "keycloak",
        },
        request=request,
    )

    assert 'document.getElementById("keycloak_submit").click()' in rendered
    assert '<div class="form-box">' in rendered


@pytest.mark.django_db
def test_whoami_uses_keycloak_claim_fallbacks(client):
    user = User.objects.create(username="database-user")
    SocialAccount.objects.create(
        user=user,
        provider="keycloak",
        uid="keycloak-user",
        extra_data={
            "preferred_username": "alice",
            "email": "alice@example.com",
            "picture": "https://avatar",
        },
    )
    client.force_login(user)

    response = client.get("/ui/v1/auth/whoami")
    data = response.json()["data"]

    assert data["type"] == "keycloak"
    assert data["username"] == "alice"
    assert data["avatar_url"] == "https://avatar"


@pytest.mark.django_db
def test_whoami_keycloak_falls_back_to_email_then_database_username(client):
    user = User.objects.create(username="database-user")
    SocialAccount.objects.create(
        user=user,
        provider="keycloak",
        uid="keycloak-user",
        extra_data={"email": "alice@example.com"},
    )
    client.force_login(user)

    response = client.get("/ui/v1/auth/whoami")
    data = response.json()["data"]

    assert data["type"] == "keycloak"
    assert data["username"] == "alice@example.com"
    assert data["avatar_url"] == ""

    account = SocialAccount.objects.get(user=user)
    account.extra_data = {}
    account.save(update_fields=["extra_data"])
    response = client.get("/ui/v1/auth/whoami")

    assert response.json()["data"]["username"] == "database-user"


@pytest.mark.django_db
def test_keycloak_login_signal_adds_only_configured_group():
    user = User.objects.create(username="alice")
    existing_group = Group.objects.create(name="existing-membership")
    user.groups.add(existing_group)
    SocialAccount.objects.create(
        user=user,
        provider="keycloak",
        uid="keycloak-user",
        extra_data={
            "groups": ["keycloak-admins"],
            "realm_access": {"roles": ["admin"]},
            "resource_access": {"telescope": {"roles": ["owner"]}},
        },
    )

    add_keycloak_user_to_default_group(request=None, user=user)

    assert set(user.groups.values_list("name", flat=True)) == {
        "existing-membership",
        "keycloak-users",
    }


@pytest.mark.django_db
def test_keycloak_default_group_name_is_configurable(monkeypatch):
    monkeypatch.setitem(
        settings.CONFIG["auth"]["providers"]["keycloak"],
        "default_group",
        "read only",
    )
    user = User.objects.create(username="alice")
    SocialAccount.objects.create(
        user=user,
        provider="keycloak",
        uid="keycloak-user",
        extra_data={},
    )

    add_keycloak_user_to_default_group(request=None, user=user)

    assert list(user.groups.values_list("name", flat=True)) == ["read only"]


@pytest.mark.django_db
def test_keycloak_group_inherits_configured_viewer_permissions(
    monkeypatch, docker_source
):
    monkeypatch.setitem(
        settings.CONFIG["auth"]["providers"]["keycloak"],
        "default_group",
        "read only",
    )
    user = User.objects.create(username="alice")
    SocialAccount.objects.create(
        user=user,
        provider="keycloak",
        uid="keycloak-user",
        extra_data={},
    )
    add_keycloak_user_to_default_group(request=None, user=user)
    group = Group.objects.get(name="read only")
    SourceRoleBinding.objects.create(
        group=group,
        source=docker_source,
        role=SourceRole.VIEWER.value,
    )

    rbac_manager = RBACManager()

    assert rbac_manager.require_permissions(
        user=user,
        model_class=Source,
        pk=docker_source.slug,
        required_permissions=[SourcePermission.READ.value],
    )
    assert not rbac_manager.require_permissions(
        user=user,
        model_class=Source,
        pk=docker_source.slug,
        required_permissions=[SourcePermission.USE.value],
        raise_exception=False,
    )


@pytest.mark.django_db
def test_logout_clears_local_session_without_keycloak_redirect(client, root_user):
    client.force_login(root_user)

    response = client.post("/logout")

    assert response.status_code == 302
    assert response["Location"] == "/"
    assert "keycloak" not in response["Location"].lower()
    assert "_auth_user_id" not in client.session
