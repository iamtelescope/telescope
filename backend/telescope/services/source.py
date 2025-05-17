import os
import hashlib
from typing import Dict, Any

from django.db import transaction
from django.utils.text import slugify
from django.utils import timezone
from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied

from telescope.constants import VIEW_SCOPE_SOURCE, VIEW_SCOPE_PERSONAL
from telescope.rbac import permissions
from telescope.rbac.roles import SourceRole
from telescope.rbac.helpers import (
    get_source,
    get_sources,
    get_source_saved_views,
    get_source_saved_view,
    grant_source_role,
    require_global_permissions,
    require_source_permissions,
    user_has_source_permissions,
    require_saved_view_ownership,
    calculate_view_permissions,
)

from telescope.services.helpers import check_user_hit_create_saved_views_limit
from telescope.models import Source, SavedView
from telescope.serializers.source import (
    SourceSerializer,
    SourceWithConnectionSerializer,
    SourceKindSerializer,
    SourceSavedViewSerializer,
    NewSourceSavedViewSerializer,
    UpdateSourceSavedViewSerializer,
    NewClickhouseSourceSerializer,
    NewDockerSourceSerializer,
    UpdateClickhouseSourceSerializer,
    UpdateDockerSourceSerializer,
    SourceCreateResponseSerializer,
    SourceUpdateResponseSerializer,
    SourceSavedViewScopeSerializer,
)

from telescope.services.exceptions import SerializerValidationError


class SourceSavedViewService:
    def __init__(self, slug: str):
        self.slug = slug

    def get(self, user: User, view_slug: str):
        with transaction.atomic():
            saved_view = get_source_saved_view(
                user=user,
                source_slug=self.slug,
                view_slug=view_slug,
                required_permissions=[permissions.Source.READ.value],
            )
            return SourceSavedViewSerializer(saved_view).data

    def list(self, user: User):
        with transaction.atomic():
            saved_views = get_source_saved_views(
                user=user,
                source_slug=self.slug,
                required_permissions=[permissions.Source.READ.value],
            )
            return SourceSavedViewSerializer(saved_views, many=True).data

    def create(self, user: User, slug: str, data: Dict[str, Any], raise_is_valid=False):
        scope_serializer = SourceSavedViewScopeSerializer(data=data)
        if not scope_serializer.is_valid(raise_exception=raise_is_valid):
            raise SerializerValidationError(scope_serializer.errors)

        with transaction.atomic():
            scope = scope_serializer.validated_data["scope"]
            required_permissions = [permissions.Source.READ.value]

            if scope == VIEW_SCOPE_SOURCE:
                required_permissions = [permissions.Source.EDIT.value]
            require_source_permissions(
                user=user,
                source_slug=self.slug,
                required_permissions=required_permissions,
            )
            serializer = NewSourceSavedViewSerializer(data=data)
            if not serializer.is_valid(raise_exception=raise_is_valid):
                raise SerializerValidationError(serializer)
            else:
                source = Source.objects.get(slug=slug)
                ok, message = check_user_hit_create_saved_views_limit(user, source)
                if not ok:
                    raise ValueError(message)
                salt = hashlib.sha1(os.urandom(32)).hexdigest()[:6]
                slugified = slugify(serializer.validated_data["name"])
                saved_view = SavedView.objects.create(
                    slug=f"{slugified}-{salt}",
                    name=serializer.validated_data["name"],
                    description=serializer.validated_data["description"],
                    scope=scope,
                    source=source,
                    user=user,
                    updated_by=user,
                    shared=serializer.validated_data["shared"],
                    data=serializer.validated_data["data"],
                )

                saved_view.add_perms(
                    calculate_view_permissions(user, source, saved_view)
                )

                return SourceSavedViewSerializer(saved_view).data

    def delete(self, user: User, view_slug: str):
        with transaction.atomic():
            saved_view = get_source_saved_view(
                user=user,
                source_slug=self.slug,
                view_slug=view_slug,
                required_permissions=[permissions.Source.READ.value],
            )
            if saved_view.scope == VIEW_SCOPE_SOURCE:
                require_source_permissions(
                    user=user,
                    source_slug=self.slug,
                    required_permissions=[permissions.Source.EDIT.value],
                )
            else:
                require_saved_view_ownership(user, saved_view)

            saved_view.delete()

    def update(self, user: User, slug: str, data: Dict[str, Any], raise_is_valid=False):
        scope_serializer = SourceSavedViewScopeSerializer(data=data)
        if not scope_serializer.is_valid(raise_exception=raise_is_valid):
            raise SerializerValidationError(scope_serializer.errors)

        with transaction.atomic():
            source = Source.objects.get(slug=self.slug)
            saved_view = SavedView.objects.get(source=source, slug=slug)

            scope = scope_serializer.validated_data["scope"]

            required_permissions = [permissions.Source.READ.value]
            if scope == VIEW_SCOPE_SOURCE:
                required_permissions = [permissions.Source.EDIT.value]
            require_source_permissions(
                user=user,
                source_slug=self.slug,
                required_permissions=required_permissions,
            )

            if scope == VIEW_SCOPE_PERSONAL:
                require_saved_view_ownership(user, saved_view)

            serializer = UpdateSourceSavedViewSerializer(data=data)
            if not serializer.is_valid(raise_exception=raise_is_valid):
                raise SerializerValidationError(serializer)
            else:
                for key, value in serializer.validated_data.items():
                    if key != "slug":
                        setattr(saved_view, key, value)

                saved_view.updated_by = user
                saved_view.updated_at = timezone.now()
                saved_view.save()
                saved_view.add_perms(
                    calculate_view_permissions(user, source, saved_view)
                )
                return SourceSavedViewSerializer(saved_view).data


class SourceService:
    def get(self, user: User, slug: str):
        with transaction.atomic():
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
        with transaction.atomic():
            sources = get_sources(
                user=user,
                required_permissions=[permissions.Source.READ.value],
            )
            return SourceSerializer(sources, many=True).data

    def create(self, user: User, data: Dict[str, Any], raise_is_valid=False):
        with transaction.atomic():
            require_global_permissions(user, [permissions.Global.CREATE_SOURCE.value])
            kind_serializer = SourceKindSerializer(data=data)
            if not kind_serializer.is_valid(raise_exception=raise_is_valid):
                raise SerializerValidationError(kind_serializer)

            kind = kind_serializer.data["kind"]
            if kind == "clickhouse":
                serializer_cls = NewClickhouseSourceSerializer
            elif kind == "docker":
                serializer_cls = NewDockerSourceSerializer
            serializer = serializer_cls(data=data)
            if not serializer.is_valid(raise_exception=raise_is_valid):
                raise SerializerValidationError(serializer)
            else:
                source = Source.create(kind=kind, data=serializer.data)
                grant_source_role(source=source, role=SourceRole.OWNER.value, user=user)
                return SourceCreateResponseSerializer(source).data

    def update(self, user: User, slug: str, data: Dict[str, Any], raise_is_valid=False):
        with transaction.atomic():
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
            if not serializer.is_valid(raise_exception=raise_is_valid):
                raise SerializerValidationError(serializer)
            else:
                for key, value in serializer.validated_data.items():
                    if key != "slug":
                        setattr(source, key, value)
                source.save()
                return SourceUpdateResponseSerializer(source).data

    def delete(self, user: User, slug: str):
        with transaction.atomic():
            require_source_permissions(
                user=user,
                source_slug=slug,
                required_permissions=[permissions.Source.DELETE.value],
            )
            Source.objects.get(slug=slug).delete()
