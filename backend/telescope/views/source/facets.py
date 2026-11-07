import logging

from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from rest_framework import serializers
from rest_framework.response import Response
from rest_framework.views import APIView

from telescope.models import Source
from telescope.fetchers.facets import FacetRequest, body_column, fetch_facets
from telescope.rbac import permissions
from telescope.rbac.manager import RBACManager
from telescope.response import UIResponse
from telescope.serializers.source import SourceDataRequestSerializer

logger = logging.getLogger("telescope.views.source.facets")
rbac_manager = RBACManager()

MAX_FACETS = 50
MAX_SAMPLE = 10_000_000


class SourceFacetsRequestSerializer(SourceDataRequestSerializer):
    columns = serializers.ListField(
        child=serializers.CharField(), required=False, max_length=MAX_FACETS
    )
    map_keys = serializers.DictField(
        child=serializers.ListField(child=serializers.CharField(), max_length=20),
        required=False,
    )
    text = serializers.CharField(allow_blank=True, required=False, default="")
    limit = serializers.IntegerField(min_value=1, max_value=100, default=10)
    sample = serializers.IntegerField(
        min_value=1, max_value=MAX_SAMPLE, default=100_000
    )

    def validate_columns(self, value):
        columns = self.context["source"]._columns
        unknown = [name for name in value if name not in columns]
        if unknown:
            raise serializers.ValidationError(f"unknown column: {unknown[0]}")
        return list(dict.fromkeys(value))

    def validate_map_keys(self, value):
        columns = self.context["source"]._columns
        for name in value:
            if name not in columns:
                raise serializers.ValidationError(f"unknown column: {name}")
        return {name: list(dict.fromkeys(keys)) for name, keys in value.items()}

    def validate_text(self, value):
        if value and not body_column(self.context["source"]):
            raise serializers.ValidationError("text search needs a body column")
        return value

    def validate(self, attrs):
        attrs = super().validate(attrs)
        facets = len(attrs.get("columns", [])) + sum(
            len(k) for k in attrs.get("map_keys", {}).values()
        )
        if facets > MAX_FACETS:
            raise serializers.ValidationError(f"at most {MAX_FACETS} facets")
        return attrs


class SourceFacetsView(APIView):
    @method_decorator(login_required)
    def post(self, request, slug):
        response = UIResponse()
        try:
            source = rbac_manager.get_source(
                user=request.user,
                source_slug=slug,
                required_permissions=[permissions.Source.USE.value],
                fetch_connection=True,
            )
        except Source.DoesNotExist:
            response.mark_failed("source not found")
            return Response(response.as_dict())
        serializer = SourceFacetsRequestSerializer(
            data=request.data, context={"source": source, "user": request.user}
        )
        if not serializer.is_valid():
            response.validation["result"] = False
            response.validation["columns"] = serializer.errors
            return Response(response.as_dict())
        data = serializer.validated_data
        try:
            response.data = fetch_facets(
                FacetRequest(
                    source=source,
                    time_from=data["from"],
                    time_to=data["to"],
                    query=data.get("query") or "",
                    raw_query=data.get("raw_query") or "",
                    text=data.get("text") or "",
                    columns=data.get("columns", []),
                    map_keys=data.get("map_keys", {}),
                    limit=data["limit"],
                    sample=data["sample"],
                    context_columns=data.get("context_columns") or {},
                )
            )
        except Exception as err:
            logger.exception("facets failed: %s", err)
            response.mark_failed(str(err))
        return Response(response.as_dict())
