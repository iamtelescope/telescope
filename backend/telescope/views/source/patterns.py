import logging

from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from rest_framework import serializers
from rest_framework.response import Response
from rest_framework.views import APIView

from telescope.fetchers.search import body_column
from telescope.models import Source
from telescope.patterns.fetch import KINDS, PatternRequest, fetch_patterns
from telescope.rbac import permissions
from telescope.rbac.manager import RBACManager
from telescope.response import UIResponse
from telescope.serializers.source import SourceDataRequestSerializer

logger = logging.getLogger("telescope.views.source.patterns")
rbac_manager = RBACManager()

MAX_SAMPLE = 100_000


class SourcePatternsRequestSerializer(SourceDataRequestSerializer):
    column = serializers.CharField(required=False, allow_blank=True, default="")
    sample = serializers.IntegerField(min_value=1, max_value=MAX_SAMPLE, default=10_000)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields.pop("columns", None)
        self.fields.pop("limit", None)

    def validate_column(self, value):
        source = self.context["source"]
        value = value or body_column(source)
        if not value:
            raise serializers.ValidationError("source has no body column")
        if value not in source._columns:
            raise serializers.ValidationError(f"unknown column: {value}")
        return value


class SourcePatternsView(APIView):
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
        if source.kind not in KINDS:
            response.mark_failed(
                f"patterns are not supported for {source.kind} sources"
            )
            return Response(response.as_dict())
        serializer = SourcePatternsRequestSerializer(
            data=request.data, context={"source": source, "user": request.user}
        )
        if not serializer.is_valid():
            response.validation["result"] = False
            response.validation["columns"] = serializer.errors
            return Response(response.as_dict())
        data = serializer.validated_data
        try:
            response.data = fetch_patterns(
                PatternRequest(
                    source=source,
                    time_from=data["from"],
                    time_to=data["to"],
                    column=data["column"],
                    query=data.get("query") or "",
                    raw_query=data.get("raw_query") or "",
                    text=data.get("text") or "",
                    sample=data["sample"],
                    context_columns=data.get("context_columns") or {},
                )
            )
        except Exception as err:
            logger.exception("patterns failed: %s", err)
            response.mark_failed(str(err))
        return Response(response.as_dict())
