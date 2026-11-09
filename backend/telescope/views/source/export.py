"""Download of every row matching an explorer query, streamed as JSON or CSV."""

import json
import logging
from datetime import datetime
from functools import partial

from django.contrib.auth.decorators import login_required
from django.http import StreamingHttpResponse
from django.utils.decorators import method_decorator
from django.views.decorators.clickjacking import xframe_options_sameorigin
from rest_framework import serializers
from rest_framework.response import Response
from rest_framework.views import APIView

from telescope.constants import UTC_ZONE
from telescope.fetchers import get_fetchers
from telescope.fetchers.request import DataRequest
from telescope.models import Source
from telescope.rbac import permissions
from telescope.rbac.manager import RBACManager
from telescope.response import UIResponse
from telescope.serializers.source import SourceDataRequestSerializer

logger = logging.getLogger("telescope.views.source.export")
rbac_manager = RBACManager()

CHUNK_BYTES = 64 * 1024
CONTENT_TYPES = {"json": "application/json", "csv": "text/csv; charset=utf-8"}


class SourceExportRequestSerializer(SourceDataRequestSerializer):
    format = serializers.ChoiceField(choices=list(CONTENT_TYPES))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields.pop("limit", None)
        self.fields.pop("before", None)


def column_value(column, data):
    """Value of a (possibly segmented) column, as the explorer's columnValue() reads it."""
    if not column.is_segmented:
        return data.get(column.root_name)
    segments = column.segments or (column.name.split(".") if column.name else [])
    cur = data
    for i, seg in enumerate(segments):
        if (
            isinstance(cur, (list, tuple))
            and str(seg).isdigit()
            and int(seg) < len(cur)
        ):
            cur = cur[int(seg)]
        elif isinstance(cur, dict) and seg in cur:
            cur = cur[seg]
        elif i == 0 and ".".join(segments) in cur:
            # A dotted top-level name (e.g. `container.id`) lives flat in `data`.
            return cur[".".join(segments)]
        else:
            return None
    return cur


def csv_field(value) -> str:
    if value is None:
        text = ""
    elif isinstance(value, bool):
        text = "true" if value else "false"
    elif isinstance(value, (dict, list, tuple)):
        text = json.dumps(value, default=str, ensure_ascii=False, separators=(",", ":"))
    else:
        text = str(value)
    if any(c in text for c in '",\r\n'):
        return '"' + text.replace('"', '""') + '"'
    return text


def row_time_iso(row) -> str:
    return f"{row.time['datetime'].replace(' ', 'T')}.{row.time['microseconds']}Z"


def encode_json(rows):
    yield "["
    for i, row in enumerate(rows):
        data = json.dumps(row.as_dict(), default=str, ensure_ascii=False)
        yield ("\n" if i == 0 else ",\n") + data
    yield "\n]\n"


def encode_csv(rows, columns):
    # Same layout as the explorer's toCsv(): RFC 4180 with CRLF line ends.
    yield ",".join(csv_field(c) for c in ["Time"] + [c.name for c in columns]) + "\r\n"
    for row in rows:
        data = row.as_dict()["data"]
        fields = [row_time_iso(row)] + [column_value(c, data) for c in columns]
        yield ",".join(csv_field(f) for f in fields) + "\r\n"


def chunked(parts):
    buffer, size = [], 0
    for part in parts:
        data = part.encode()
        buffer.append(data)
        size += len(data)
        if size >= CHUNK_BYTES:
            yield b"".join(buffer)
            buffer, size = [], 0
    if buffer:
        yield b"".join(buffer)


def body(first, rows, encode, slug):
    def all_rows():
        if first is not None:
            yield first
        yield from rows

    try:
        yield from chunked(encode(all_rows()))
    except Exception as err:
        # Raising ends the response without its last chunk, so the download shows as failed.
        logger.exception("export of %s failed: %s", slug, err)
        raise
    finally:
        rows.close()


def filename(slug, time_from, time_to, fmt) -> str:
    def stamp(ms):
        return datetime.fromtimestamp(ms / 1000, UTC_ZONE).strftime("%Y%m%dT%H%M%SZ")

    return f"{slug}_{stamp(time_from)}_{stamp(time_to)}.{fmt}"


# The explorer reads an error response from the hidden frame it posts into.
@method_decorator(xframe_options_sameorigin, name="dispatch")
class SourceExportView(APIView):
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
            return Response(response.as_dict(), status=404)

        data = request.data
        if "params" in data:
            # The explorer posts a form, so the browser streams the file to disk.
            try:
                data = json.loads(data["params"])
            except ValueError as err:
                response.mark_failed(f"params: {err}")
                return Response(response.as_dict(), status=400)
        serializer = SourceExportRequestSerializer(
            data=data, context={"source": source, "user": request.user}
        )
        if not serializer.is_valid():
            response.validation["result"] = False
            response.validation["columns"] = serializer.errors
            return Response(response.as_dict(), status=400)
        v = serializer.validated_data

        data_request = DataRequest(
            source=source,
            query=v.get("query", ""),
            raw_query=v.get("raw_query", ""),
            time_from=v["from"],
            time_to=v["to"],
            limit=None,
            context_columns=v.get("context_columns") or {},
            text=v.get("text") or "",
        )
        rows = get_fetchers()[source.kind].stream_data(data_request, tz=UTC_ZONE)
        try:
            # The query starts here, so its errors still get an error response.
            first = next(rows, None)
        except Exception as err:
            logger.exception("export of %s failed: %s", slug, err)
            response.mark_failed(str(err))
            return Response(response.as_dict(), status=400)

        if v["format"] == "csv":
            encode = partial(encode_csv, columns=v["columns"])
        else:
            encode = encode_json
        stream = StreamingHttpResponse(
            body(first, rows, encode, slug), content_type=CONTENT_TYPES[v["format"]]
        )
        name = filename(slug, v["from"], v["to"], v["format"])
        stream["Content-Disposition"] = f'attachment; filename="{name}"'
        return stream
