import pytest

from rest_framework.test import APIClient

from tests.data import get_docker_connection_data


@pytest.fixture
def api_client(root_user):
    client = APIClient()
    client.force_authenticate(user=root_user)
    return client


@pytest.fixture
def unauth_client():
    return APIClient()


@pytest.mark.django_db
def test_create_connection(api_client):
    data = get_docker_connection_data()
    response = api_client.post("/api/v1/connections", data, format="json")
    assert response.status_code == 200
    assert "id" in response.data


@pytest.mark.django_db
def test_get_connection(api_client):
    data = get_docker_connection_data()
    create_response = api_client.post("/api/v1/connections", data, format="json")
    pk = create_response.data["id"]

    response = api_client.get(f"/api/v1/connections/{pk}")
    assert response.status_code == 200
    assert response.data["name"] == data["name"]


@pytest.mark.django_db
def test_list_connections(api_client):
    data = get_docker_connection_data()
    api_client.post("/api/v1/connections", data, format="json")

    response = api_client.get("/api/v1/connections")
    assert response.status_code == 200
    assert isinstance(response.data, list)
    assert len(response.data) >= 1


@pytest.mark.django_db
def test_update_connection(api_client):
    data = get_docker_connection_data()
    create_response = api_client.post("/api/v1/connections", data, format="json")
    pk = create_response.data["id"]

    data["name"] = "Updated Docker Connection"
    response = api_client.patch(f"/api/v1/connections/{pk}", data, format="json")
    assert response.status_code == 200
    assert "id" in response.data


@pytest.mark.django_db
def test_delete_connection(api_client):
    from telescope.models import Connection

    data = get_docker_connection_data()
    create_response = api_client.post("/api/v1/connections", data, format="json")
    pk = create_response.data["id"]

    response = api_client.delete(f"/api/v1/connections/{pk}")
    assert response.status_code == 200

    assert not Connection.objects.filter(pk=pk).exists()


@pytest.mark.django_db
def test_unauthenticated_request(unauth_client):
    data = get_docker_connection_data()

    assert unauth_client.post(
        "/api/v1/connections", data, format="json"
    ).status_code in (401, 403)
    assert unauth_client.patch(
        "/api/v1/connections/1", data, format="json"
    ).status_code in (401, 403)
    assert unauth_client.delete("/api/v1/connections/1").status_code in (401, 403)
