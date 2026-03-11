import pytest

from unittest.mock import patch

from telescope.models import HealthCheck


@pytest.mark.django_db
def test_liveness_returns_ok(client):
    response = client.get("/liveness")
    assert response.status_code == 200
    assert response.content == b"ok"
    assert response["Content-Type"] == "text/plain"


@pytest.mark.django_db
def test_readiness_returns_ok_when_db_healthy(client):
    response = client.get("/readiness")
    assert response.status_code == 200
    assert response.content == b"ok"
    assert response["Content-Type"] == "text/plain"


@pytest.mark.django_db
def test_readiness_returns_503_when_row_missing(client):
    HealthCheck.objects.filter(key="status").delete()
    response = client.get("/readiness")
    assert response.status_code == 503
    assert response.content == b"error"
    assert response["Content-Type"] == "text/plain"


@pytest.mark.django_db
def test_readiness_returns_503_on_db_error(client):
    with patch.object(HealthCheck.objects, "get", side_effect=Exception("db error")):
        response = client.get("/readiness")
    assert response.status_code == 503
    assert response.content == b"error"


@pytest.mark.django_db
def test_liveness_no_auth_required(client):
    response = client.get("/liveness")
    assert response.status_code == 200


@pytest.mark.django_db
def test_readiness_no_auth_required(client):
    response = client.get("/readiness")
    assert response.status_code == 200
