"""MCP over streamable HTTP at /api/mcp: stateless, one JSON response per POST.
Transport choices follow HyperDX packages/api/src/mcp/app.ts (MIT)."""

import json
from types import SimpleNamespace

import mcp.types as types
from django.http import HttpResponse, JsonResponse
from mcp.shared.version import SUPPORTED_PROTOCOL_VERSIONS
from pydantic import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from telescope.auth.token import TokenAuth
from telescope_api2.throttle import TokenRateThrottle
from telescope_mcp import tools

SERVER_INFO = types.Implementation(name="telescope", title="Telescope", version="1.0")
INSTRUCTIONS = (
    "Telescope reads logs, traces and metrics stored in ClickHouse and other sources. "
    "Start with list_sources, then describe_source for its columns, then search or chart. "
    "Times are epoch milliseconds or now, now-15m, now-1h, now-1d. "
    "Queries use FlyQL, e.g. ServiceName = 'payment' and SeverityText = 'ERROR'."
)


class McpTokenAuth(TokenAuth):
    """API v2 token auth that also takes `Authorization: Bearer <token>`, which MCP clients send."""

    def authenticate(self, request):
        scheme, _, token = request.headers.get("Authorization", "").partition(" ")
        if scheme == "Bearer":
            request = SimpleNamespace(headers={"Authorization": f"Token {token}"})
        return super().authenticate(request)

    def authenticate_header(self, request):
        return 'Bearer realm="telescope"'


def dump(model):
    return model.model_dump(by_alias=True, exclude_none=True, mode="json")


def rpc_error(id, code, message):
    return {"jsonrpc": "2.0", "id": id, "error": {"code": code, "message": message}}


def initialize(params):
    asked = params.get("protocolVersion")
    version = (
        asked if asked in SUPPORTED_PROTOCOL_VERSIONS else types.LATEST_PROTOCOL_VERSION
    )
    return dump(
        types.InitializeResult(
            protocolVersion=version,
            capabilities=types.ServerCapabilities(
                tools=types.ToolsCapability(listChanged=False)
            ),
            serverInfo=SERVER_INFO,
            instructions=INSTRUCTIONS,
        )
    )


def handle(user, message):
    """The JSON-RPC reply to one message, or None for notifications and responses."""
    try:
        parsed = types.JSONRPCMessage.model_validate(message).root
    except ValidationError:
        return rpc_error(None, types.INVALID_REQUEST, "Invalid JSON-RPC message")
    if not isinstance(parsed, types.JSONRPCRequest):
        return None
    params = parsed.params or {}
    if parsed.method == "initialize":
        result = initialize(params)
    elif parsed.method == "ping":
        result = {}
    elif parsed.method == "tools/list":
        result = {"tools": tools.listing()}
    elif parsed.method == "tools/call":
        result = tools.call(user, params.get("name"), params.get("arguments") or {})
        if result is None:
            return rpc_error(
                parsed.id, types.INVALID_PARAMS, f"Unknown tool: {params.get('name')}"
            )
    else:
        return rpc_error(
            parsed.id, types.METHOD_NOT_FOUND, f"Method not found: {parsed.method}"
        )
    return {"jsonrpc": "2.0", "id": parsed.id, "result": result}


class McpView(APIView):
    authentication_classes = [McpTokenAuth]
    permission_classes = [IsAuthenticated]
    throttle_classes = [TokenRateThrottle]

    def get(self, request):
        # Stateless: no server-initiated stream and no sessions to end, so 405 per spec.
        return HttpResponse(status=405, headers={"Allow": "POST"})

    delete = get

    def post(self, request):
        version = request.headers.get("Mcp-Protocol-Version")
        if version and version not in SUPPORTED_PROTOCOL_VERSIONS:
            error = rpc_error(
                None, types.INVALID_REQUEST, f"Unsupported protocol version: {version}"
            )
            return JsonResponse(error, status=400)
        try:
            body = json.loads(request.body)
        except ValueError:
            error = rpc_error(None, types.PARSE_ERROR, "Parse error")
            return JsonResponse(error, status=400)
        messages = body if isinstance(body, list) else [body]
        replies = [r for r in (handle(request.user, m) for m in messages) if r]
        if not replies:
            return HttpResponse(status=202)
        return JsonResponse(
            replies if isinstance(body, list) else replies[0], safe=False
        )
