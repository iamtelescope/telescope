import pytest

from django.contrib.auth.models import User

from telescope.models import Source, SourceColumn, SavedView, Connection
from telescope.constants import VIEW_SCOPE_SOURCE, VIEW_SCOPE_PERSONAL


@pytest.mark.django_db
def test_root_user_exist(root_user):
    assert isinstance(root_user, User)
    assert root_user.username == "test_root"
    assert root_user.is_superuser is True
    assert User.objects.filter(username="test_root").exists()


@pytest.mark.django_db
def test_user_exist(test_user):
    assert isinstance(test_user, User)
    assert test_user.username == "test_user"
    assert test_user.is_superuser is False
    assert User.objects.filter(username="test_user").exists()


@pytest.mark.django_db
def test_hacker_user_exist(hacker_user):
    assert isinstance(hacker_user, User)
    assert hacker_user.username == "test_hacker"
    assert hacker_user.is_superuser is False
    assert User.objects.filter(username="test_hacker").exists()


@pytest.mark.django_db
def test_docker_source_fixture(docker_source):
    assert isinstance(docker_source, Source)
    assert docker_source.kind == "docker"
    assert docker_source.support_raw_query is False
    assert "container" in docker_source.context_columns
    assert docker_source.columns["time"]["type"] == "datetime"
    assert docker_source.columns["time"]["autocomplete"] is False
    assert docker_source.columns["time"]["suggest"] is True
    assert docker_source.columns["message"]["type"] == "string"
    assert docker_source.columns["message"]["display_name"] == "IsMessage"
    assert docker_source.columns["message"]["autocomplete"] is True
    assert docker_source.columns["message"]["jsonstring"] is True
    assert isinstance(docker_source.permissions, set)
    for key, value in docker_source._columns.items():
        assert isinstance(key, str)
        assert isinstance(value, SourceColumn)


@pytest.mark.django_db
def test_clickhouse_source_fixture(clickhouse_source):
    assert isinstance(clickhouse_source, Source)
    assert clickhouse_source.kind == "clickhouse"
    assert clickhouse_source.support_raw_query is True
    assert clickhouse_source.context_columns == {}
    assert clickhouse_source.columns["event_time"]["type"] == "DateTime64(3)"
    assert clickhouse_source.columns["event_time"]["autocomplete"] is False
    assert clickhouse_source.columns["event_time"]["suggest"] is True
    assert clickhouse_source.columns["message"]["type"] == "String"
    assert clickhouse_source.columns["message"]["display_name"] == "IsMessage"
    assert clickhouse_source.columns["message"]["autocomplete"] is True
    assert clickhouse_source.columns["message"]["jsonstring"] is True
    assert isinstance(clickhouse_source.permissions, set)
    for key, value in clickhouse_source._columns.items():
        assert isinstance(key, str)
        assert isinstance(value, SourceColumn)


@pytest.mark.django_db
def test_personal_saved_view_fixture(personal_saved_view, test_user, docker_source):
    assert isinstance(personal_saved_view, SavedView)
    assert personal_saved_view.slug == "test-view-personal"
    assert personal_saved_view.name == "Test View Personal"
    assert personal_saved_view.description == "test view description"
    assert personal_saved_view.scope == VIEW_SCOPE_PERSONAL
    assert personal_saved_view.source == docker_source
    assert personal_saved_view.user == test_user
    assert personal_saved_view.shared is False


@pytest.mark.django_db
def test_personal_saved_view_fixture(
    shared_personal_saved_view, test_user, docker_source
):
    assert isinstance(shared_personal_saved_view, SavedView)
    assert shared_personal_saved_view.slug == "test-view-personal-shared"
    assert shared_personal_saved_view.name == "Test View Personal Shared"
    assert shared_personal_saved_view.description == "test view description"
    assert shared_personal_saved_view.scope == VIEW_SCOPE_PERSONAL
    assert shared_personal_saved_view.source == docker_source
    assert shared_personal_saved_view.user == test_user
    assert shared_personal_saved_view.shared is True


@pytest.mark.django_db
def test_source_saved_view(source_saved_view, root_user, docker_source):
    assert isinstance(source_saved_view, SavedView)
    assert source_saved_view.slug == "test-view-source-scoped"
    assert source_saved_view.name == "Test View Source Scoped"
    assert source_saved_view.description == "test view description"
    assert source_saved_view.scope == VIEW_SCOPE_SOURCE
    assert source_saved_view.source == docker_source
    assert source_saved_view.user == root_user
    assert source_saved_view.shared is False


@pytest.mark.django_db
def test_personal_root_saved_view_fixture(
    personal_root_saved_view, root_user, docker_source
):
    assert isinstance(personal_root_saved_view, SavedView)
    assert personal_root_saved_view.slug == "test-view-personal-root"
    assert personal_root_saved_view.name == "Test View Personal Root"
    assert personal_root_saved_view.description == "test view description"
    assert personal_root_saved_view.scope == VIEW_SCOPE_PERSONAL
    assert personal_root_saved_view.source == docker_source
    assert personal_root_saved_view.user == root_user
    assert personal_root_saved_view.shared is False


@pytest.mark.django_db
def test_personal_root_shared_saved_view_fixture(
    personal_root_shared_saved_view, root_user, docker_source
):
    assert isinstance(personal_root_shared_saved_view, SavedView)
    assert personal_root_shared_saved_view.slug == "test-view-personal-root-shared"
    assert personal_root_shared_saved_view.name == "Test View Personal Root Shared"
    assert personal_root_shared_saved_view.description == "test view description"
    assert personal_root_shared_saved_view.scope == VIEW_SCOPE_PERSONAL
    assert personal_root_shared_saved_view.source == docker_source
    assert personal_root_shared_saved_view.user == root_user
    assert personal_root_shared_saved_view.shared is True


@pytest.mark.django_db
def test_kubernetes_source_fixture(kubernetes_source):
    assert isinstance(kubernetes_source, Source)
    assert kubernetes_source.kind == "kubernetes"
    assert kubernetes_source.support_raw_query is False
    assert "contexts" in kubernetes_source.context_columns
    assert "namespaces" in kubernetes_source.context_columns
    assert kubernetes_source.columns["time"]["type"] == "datetime"
    assert kubernetes_source.columns["time"]["autocomplete"] is False
    assert kubernetes_source.columns["time"]["suggest"] is True
    assert kubernetes_source.columns["message"]["type"] == "string"
    assert kubernetes_source.columns["message"]["display_name"] == "IsMessage"
    assert kubernetes_source.columns["message"]["autocomplete"] is False
    assert kubernetes_source.columns["message"]["jsonstring"] is True
    assert isinstance(kubernetes_source.permissions, set)
    for key, value in kubernetes_source._columns.items():
        assert isinstance(key, str)
        assert isinstance(value, SourceColumn)


@pytest.mark.django_db
def test_kubernetes_connection_fixture(kubernetes_connection):
    assert isinstance(kubernetes_connection, Connection)
    assert kubernetes_connection.kind == "kubernetes"
    assert kubernetes_connection.name == "Kubernetes Connection"
    assert "kubeconfig" in kubernetes_connection.data
    assert "kubeconfig_hash" in kubernetes_connection.data
    assert "kubeconfig_is_local" in kubernetes_connection.data
    assert kubernetes_connection.data["kubeconfig_is_local"] is False


@pytest.mark.django_db
def test_kubernetes_personal_saved_view_fixture(
    kubernetes_personal_saved_view, test_user, kubernetes_source
):
    assert isinstance(kubernetes_personal_saved_view, SavedView)
    assert kubernetes_personal_saved_view.slug == "test-view-kubernetes-personal"
    assert kubernetes_personal_saved_view.name == "Test View Kubernetes Personal"
    assert kubernetes_personal_saved_view.description == "test view description"
    assert kubernetes_personal_saved_view.scope == "personal"
    assert kubernetes_personal_saved_view.source == kubernetes_source
    assert kubernetes_personal_saved_view.user == test_user
    assert kubernetes_personal_saved_view.shared is False


@pytest.mark.django_db
def test_kubernetes_source_saved_view_fixture(
    kubernetes_source_saved_view, root_user, kubernetes_source
):
    assert isinstance(kubernetes_source_saved_view, SavedView)
    assert kubernetes_source_saved_view.slug == "test-view-kubernetes-source"
    assert kubernetes_source_saved_view.name == "Test View Kubernetes Source"
    assert kubernetes_source_saved_view.description == "test view description"
    assert kubernetes_source_saved_view.scope == "source"
    assert kubernetes_source_saved_view.source == kubernetes_source
    assert kubernetes_source_saved_view.user == root_user
    assert kubernetes_source_saved_view.shared is False
