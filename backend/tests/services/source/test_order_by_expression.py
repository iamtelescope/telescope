import pytest

from telescope.models import Source
from tests.data import get_docker_source_data


@pytest.mark.django_db
def test_create_source_with_order_by_expression(root_user, service, docker_connection):
    """order_by_expression is persisted when set during source creation"""
    slug = "docker_with_order_by"
    source_data = get_docker_source_data(slug)
    source_data["connection"] = {"connection_id": docker_connection.id}
    source_data["order_by_expression"] = "timestamp DESC, id ASC"

    service.create(user=root_user, data=source_data)

    source = Source.objects.get(slug=slug)
    assert source.order_by_expression == "timestamp DESC, id ASC"


@pytest.mark.django_db
def test_create_source_without_order_by_expression_defaults_to_empty(
    root_user, service, docker_connection
):
    """order_by_expression defaults to empty string when not provided"""
    slug = "docker_no_order_by"
    source_data = get_docker_source_data(slug)
    source_data["connection"] = {"connection_id": docker_connection.id}

    service.create(user=root_user, data=source_data)

    source = Source.objects.get(slug=slug)
    assert source.order_by_expression == ""


@pytest.mark.django_db
def test_create_source_with_empty_order_by_expression(
    root_user, service, docker_connection
):
    """Explicitly setting order_by_expression to empty string is accepted"""
    slug = "docker_empty_order_by"
    source_data = get_docker_source_data(slug)
    source_data["connection"] = {"connection_id": docker_connection.id}
    source_data["order_by_expression"] = ""

    service.create(user=root_user, data=source_data)

    source = Source.objects.get(slug=slug)
    assert source.order_by_expression == ""


@pytest.mark.django_db
def test_update_source_order_by_expression(root_user, service, docker_source):
    """order_by_expression can be updated on an existing source"""
    data = get_docker_source_data(docker_source.slug)
    del data["connection"]
    data["order_by_expression"] = "timestamp DESC, request_id ASC"

    service.update(user=root_user, slug=docker_source.slug, data=data)

    source = Source.objects.get(slug=docker_source.slug)
    assert source.order_by_expression == "timestamp DESC, request_id ASC"


@pytest.mark.django_db
def test_update_source_clears_order_by_expression(root_user, service, docker_source):
    """order_by_expression can be cleared by updating to empty string"""
    # First, set a value
    data = get_docker_source_data(docker_source.slug)
    del data["connection"]
    data["order_by_expression"] = "timestamp DESC"
    service.update(user=root_user, slug=docker_source.slug, data=data)
    assert Source.objects.get(slug=docker_source.slug).order_by_expression == "timestamp DESC"

    # Now clear it
    data2 = get_docker_source_data(docker_source.slug)
    del data2["connection"]
    data2["order_by_expression"] = ""
    service.update(user=root_user, slug=docker_source.slug, data=data2)

    source = Source.objects.get(slug=docker_source.slug)
    assert source.order_by_expression == ""


@pytest.mark.django_db
def test_clickhouse_source_model_stores_order_by_expression(clickhouse_source):
    """order_by_expression is stored and readable directly on a ClickHouse Source instance"""
    clickhouse_source.order_by_expression = "toStartOfHour(event_time) DESC, event_time DESC"
    clickhouse_source.save()

    source = Source.objects.get(slug=clickhouse_source.slug)
    assert source.order_by_expression == "toStartOfHour(event_time) DESC, event_time DESC"
