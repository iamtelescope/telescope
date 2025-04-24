from typing import Dict, Any

from django.db import transaction
from django.contrib.auth.models import User

from rest_framework.request import Request

from telescope.rbac import permissions
from telescope.rbac.roles import SourceRole
from telescope.rbac.helpers import (
    get_source,
    get_sources,
    grant_source_role,
    require_global_permissions,
    require_source_permissions,
    user_has_source_permissions,
)

from telescope.models import Source
from telescope.serializers.source import (
    SourceSerializer,
    SourceWithConnectionSerializer,
    SourceKindSerializer,
    NewClickhouseSourceSerializer,
    NewDockerSourceSerializer,
    UpdateClickhouseSourceSerializer,
    UpdateDockerSourceSerializer,
    SourceCreateResponseSerializer,
    SourceUpdateResponseSerializer,
)

from telescope.services.exceptions import SerializerValidationError


class SourceService:
    def get(self, user: User, slug: str):
        source = get_source(
            user=user,
            slug=slug,
            required_permissions=[permissions.Source.READ.value],
        )

        serializer_class = SourceSerializer
        if user_has_source_permissions(
            user=user,
            source_slug=slug,
            required_permissions=[permissions.Source.EDIT.value],
        ):
            serializer_class = SourceWithConnectionSerializer

        serializer = serializer_class(source)
        return serializer.data

    def list(self, user: User):
        sources = get_sources(
            user=user,
            required_permissions=[permissions.Source.READ.value],
        )
        return SourceSerializer(sources, many=True).data

    def create(self, user: User, data: Dict[str, Any]):
        require_global_permissions(user, [permissions.Global.CREATE_SOURCE.value])
        kind_serializer = SourceKindSerializer(data=data)
        if not kind_serializer.is_valid():
            raise SerializerValidationError(kind_serializer)

        kind = kind_serializer.data["kind"]
        if kind == "clickhouse":
            serializer_cls = NewClickhouseSourceSerializer
        elif kind == "docker":
            serializer_cls = NewDockerSourceSerializer
        serializer = serializer_cls(data=data)
        if not serializer.is_valid():
            raise SerializerValidationError(serializer)
        else:
            with transaction.atomic():
                source = Source.create(kind=kind, data=serializer.data)
                grant_source_role(source=source, role=SourceRole.OWNER.value, user=user)
                return SourceCreateResponseSerializer(source).data

    def update(self, user: User, slug: str, data: Dict[str, Any]):
        require_source_permissions(
            user=user,
            source_slug=slug,
            required_permissions=[permissions.Source.EDIT.value],
        )

        source = Source.objects.get(slug=slug)
        if source.kind == "clickhouse":
            serializer_cls = UpdateClickhouseSourceSerializer
        elif source.kind == "docker":
            serializer_cls = UpdateDockerSourceSerializer
        else:
            raise ValueError("Unknown kind")

        serializer = serializer_cls(data=data)
        if not serializer.is_valid():
            raise SerializerValidationError(serializer)
        else:
            with transaction.atomic():
                for key, value in serializer.data.items():
                    if key != "slug":
                        setattr(source, key, value)
                source.save()
                return SourceUpdateResponseSerializer(source).data

    def delete(self, user: User, slug: str):
        require_source_permissions(
            user=user,
            source_slug=slug,
            required_permissions=[permissions.Source.DELETE.value],
        )
        with transaction.atomic():
            Source.objects.get(slug=slug).delete()
