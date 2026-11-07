"""Data for the dashboard search (log rows) and patterns tiles: the explorer and patterns
requests plus the dashboard filter and `$variables`, answered like chartData."""

import logging

from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from rest_framework import serializers
from rest_framework.response import Response
from rest_framework.views import APIView

from telescope.constants import UTC_ZONE
from telescope.fetchers import get_fetchers
from telescope.fetchers.chart import VariableError, bind_query
from telescope.fetchers.request import DataRequest
from telescope.models import Source
from telescope.patterns.fetch import KINDS, PatternRequest, fetch_patterns
from telescope.query_attribution import debug_sql
from telescope.rbac import permissions
from telescope.rbac.manager import RBACManager
from telescope.response import UIResponse
from telescope.serializers.dashboard import ParamValueField, SEARCH_TILE_MAX_LIMIT
from telescope.serializers.source import SourceDataRequestSerializer
from telescope.views.source.patterns import SourcePatternsRequestSerializer

logger = logging.getLogger("telescope.views.source.tiles")
rbac_manager = RBACManager()


class TileRequestSerializer(SourceDataRequestSerializer):
    """Binds `params` into `query` and `dashboard_query`, then ANDs them into `query`."""

    dashboard_query = serializers.CharField(
        allow_blank=True, allow_null=True, required=False
    )
    params = serializers.DictField(
        child=ParamValueField(), required=False, default=dict
    )

    # Queries are checked in validate(), once their variables are bound.
    def validate_query(self, value):
        return value or ""

    def validate_dashboard_query(self, value):
        return value or ""

    def validate(self, attrs):
        attrs = super().validate(attrs)
        errors, queries = {}, []
        for field in ("query", "dashboard_query"):
            try:
                bound = bind_query(attrs.get(field) or "", attrs["params"])
                bound = SourceDataRequestSerializer.validate_query(self, bound)
            except VariableError as err:
                errors.setdefault("params", {})[err.name] = [err.message]
                continue
            except serializers.ValidationError as err:
                errors[field] = err.detail
                continue
            if bound:
                queries.append(bound)
        if attrs["from"] >= attrs["to"]:
            errors["to"] = ["must be after from"]
        if errors:
            raise serializers.ValidationError(errors)
        attrs["query"] = (
            queries[0] if len(queries) == 1 else " and ".join(f"({q})" for q in queries)
        )
        return attrs


class SearchTileRequestSerializer(TileRequestSerializer):
    columns = serializers.CharField(required=False, allow_blank=True, default="")
    limit = serializers.IntegerField(
        required=False, default=50, min_value=1, max_value=SEARCH_TILE_MAX_LIMIT
    )

    def validate_columns(self, value):
        if not value:
            default = self.context["source"].default_chosen_columns or []
            value = default if isinstance(default, str) else ", ".join(default)
        return super().validate_columns(value)


class PatternsTileRequestSerializer(
    TileRequestSerializer, SourcePatternsRequestSerializer
):
    pass


def tile_source(request, slug, response):
    try:
        return rbac_manager.get_source(
            user=request.user,
            source_slug=slug,
            required_permissions=[permissions.Source.USE.value],
            fetch_connection=True,
        )
    except Source.DoesNotExist:
        response.mark_failed("Source not found or access denied")
        response.data = {"code": "no_access"}
        return None


class SourceSearchTileView(APIView):
    @method_decorator(login_required)
    def post(self, request, slug):
        response = UIResponse()
        source = tile_source(request, slug, response)
        if source is None:
            return Response(response.as_dict())
        serializer = SearchTileRequestSerializer(
            data=request.data, context={"source": source, "user": request.user}
        )
        if not serializer.is_valid():
            response.mark_invalid(serializer.errors)
            return Response(response.as_dict())
        data = serializer.validated_data
        try:
            result = get_fetchers()[source.kind].fetch_data(
                DataRequest(
                    source=source,
                    query=data["query"],
                    raw_query=data.get("raw_query") or "",
                    time_from=data["from"],
                    time_to=data["to"],
                    limit=data["limit"],
                    context_columns=data.get("context_columns") or {},
                    before=data.get("before"),
                ),
                tz=UTC_ZONE,
            )
            if result.error:
                raise ValueError(result.error)
        except Exception as err:
            logger.exception("search tile failed: %s", err)
            response.mark_failed(str(err))
            response.data = {"code": "query_failed"}
            return Response(response.as_dict())
        response.data = {
            "kind": "rows",
            "columns": [c.as_dict() for c in data["columns"]],
            "rows": [row.as_dict() for row in result.rows],
            "cursor": result.cursor,
            # The range as resolved on the server, so later pages reuse its 'now'.
            "time_from": data["from"],
            "time_to": data["to"],
        }
        if debug := debug_sql(request.user, slug):
            response.data["debug"] = debug
        return Response(response.as_dict())


class SourcePatternsTileView(APIView):
    @method_decorator(login_required)
    def post(self, request, slug):
        response = UIResponse()
        source = tile_source(request, slug, response)
        if source is None:
            return Response(response.as_dict())
        if source.kind not in KINDS:
            response.mark_invalid(
                {"display": [f"patterns are not supported for {source.kind} sources"]}
            )
            return Response(response.as_dict())
        serializer = PatternsTileRequestSerializer(
            data=request.data, context={"source": source, "user": request.user}
        )
        if not serializer.is_valid():
            response.mark_invalid(serializer.errors)
            return Response(response.as_dict())
        data = serializer.validated_data
        try:
            result = fetch_patterns(
                PatternRequest(
                    source=source,
                    time_from=data["from"],
                    time_to=data["to"],
                    column=data["column"],
                    query=data["query"],
                    raw_query=data.get("raw_query") or "",
                    sample=data["sample"],
                    context_columns=data.get("context_columns") or {},
                )
            )
        except Exception as err:
            logger.exception("patterns tile failed: %s", err)
            response.mark_failed(str(err))
            response.data = {"code": "query_failed"}
            return Response(response.as_dict())
        response.data = {"kind": "patterns", **result}
        return Response(response.as_dict())
