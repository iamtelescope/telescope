"""The OpenAPI 3 description served at /api/v1/openapi.json."""

OBJ = {"type": "object", "additionalProperties": True}
PAGE_PARAMS = [
    {"name": "page", "in": "query", "schema": {"type": "integer", "minimum": 1}},
    {
        "name": "page_size",
        "in": "query",
        "schema": {"type": "integer", "minimum": 1, "maximum": 500, "default": 50},
    },
]
ERRORS = {
    "400": {"description": "Invalid request: `validation` or `errors`"},
    "401": {"description": "Missing or unknown token"},
    "403": {"description": "Insufficient permissions"},
    "404": {"description": "Not found, or not visible to the token's user"},
    "429": {"description": "Rate limit exceeded; see Retry-After"},
}


def path_param(name, type_="string"):
    return {"name": name, "in": "path", "required": True, "schema": {"type": type_}}


def op(summary, body=None, ok="200", params=None, schema=None):
    responses = {ok: {"description": "OK"}, **ERRORS}
    if ok != "204":
        responses[ok]["content"] = {"application/json": {"schema": schema or OBJ}}
    out = {"summary": summary, "responses": responses}
    if params:
        out["parameters"] = params
    if body:
        out["requestBody"] = {
            "required": True,
            "content": {"application/json": {"schema": body}},
        }
    return out


def page_of(name):
    return {
        "type": "object",
        "properties": {
            "data": {
                "type": "array",
                "items": {"$ref": f"#/components/schemas/{name}"},
            },
            "page": {"type": "integer"},
            "page_size": {"type": "integer"},
            "total": {"type": "integer"},
            "has_more": {"type": "boolean"},
        },
    }


def ref(name):
    return {"$ref": f"#/components/schemas/{name}"}


def crud(name, key, key_type="string"):
    item = [path_param(key, key_type)]
    return {
        "list": {
            "get": op(f"List {name}s", params=PAGE_PARAMS, schema=page_of(name)),
            "post": op(f"Create a {name}", body=ref(name), ok="201", schema=ref(name)),
        },
        "item": {
            "get": op(f"Get a {name}", params=item, schema=ref(name)),
            "patch": op(
                f"Update a {name}", body=ref(name), params=item, schema=ref(name)
            ),
            "delete": op(f"Delete a {name}", params=item, ok="204"),
        },
    }


TIME = {"type": "string", "description": "ms timestamp or relative, e.g. now-1h"}
SEARCH_REQUEST = {
    "type": "object",
    "required": ["columns", "from", "to", "limit"],
    "properties": {
        "columns": {"type": "string", "description": "Comma separated column names"},
        "query": {"type": "string", "description": "FlyQL"},
        "raw_query": {"type": "string", "description": "SQL WHERE (RAW_QUERY only)"},
        "text": {"type": "string", "description": "Full-text search on the body"},
        "from": TIME,
        "to": TIME,
        "limit": {"type": "integer"},
        "context_columns": OBJ,
        "before": {**OBJ, "description": "The `cursor` of the previous page"},
    },
}
CHART_REQUEST = {
    "type": "object",
    "required": ["from", "to", "display", "series"],
    "properties": {
        "query": {"type": "string"},
        "raw_query": {"type": "string"},
        "from": TIME,
        "to": TIME,
        "display": {"type": "string", "example": "line"},
        "series": {"type": "array", "items": OBJ, "example": [{"agg": "count"}]},
        "group_by": {"type": "string"},
        "granularity": {"type": "string", "default": "auto"},
        "limit": {"type": "integer"},
        "params": OBJ,
    },
}
DEBUG = {
    "debug": {
        "type": "object",
        "description": "Only for users with RAW_QUERY on the source",
        "properties": {"sql": {"type": "array", "items": {"type": "string"}}},
    }
}

dashboards = crud("Dashboard", "slug")
alerts = crud("Alert", "id", "integer")
views = crud("SavedView", "view_slug")
for method in views["item"].values():
    method["parameters"] = [path_param("source")] + method["parameters"]
views["list"]["get"]["parameters"] = PAGE_PARAMS + [
    {"name": "source", "in": "query", "schema": {"type": "string"}}
]
source = [path_param("slug")]

SPEC = {
    "openapi": "3.0.3",
    "info": {"title": "Telescope API", "version": "2.0.0"},
    "servers": [{"url": "/"}],
    "security": [{"token": []}],
    "components": {
        "securitySchemes": {
            "token": {
                "type": "apiKey",
                "in": "header",
                "name": "Authorization",
                "description": "`Token <api token>`",
            }
        },
        "schemas": {
            "Dashboard": {
                **OBJ,
                "properties": {
                    "slug": {"type": "string", "readOnly": True},
                    "name": {"type": "string"},
                    "description": {"type": "string"},
                    "shared": {"type": "boolean"},
                    "version": {"type": "integer"},
                    "data": OBJ,
                },
            },
            "Alert": {
                **OBJ,
                "properties": {
                    "id": {"type": "integer", "readOnly": True},
                    "name": {"type": "string"},
                    "kind": {"type": "string", "enum": ["search", "tile"]},
                    "interval": {"type": "string"},
                    "threshold_type": {"type": "string"},
                    "threshold": {"type": "number"},
                    "state": {"type": "string", "readOnly": True},
                },
            },
            "SavedView": {
                **OBJ,
                "properties": {
                    "slug": {"type": "string", "readOnly": True},
                    "source": {"type": "string"},
                    "name": {"type": "string"},
                    "description": {"type": "string"},
                    "scope": {"type": "string", "enum": ["personal", "source"]},
                    "shared": {"type": "boolean"},
                    "data": OBJ,
                },
            },
        },
    },
    "paths": {
        "/api/v1/dashboards": dashboards["list"],
        "/api/v1/dashboards/{slug}": dashboards["item"],
        "/api/v1/alerts": alerts["list"],
        "/api/v1/alerts/{id}": alerts["item"],
        "/api/v1/saved-views": views["list"],
        "/api/v1/saved-views/{source}/{view_slug}": views["item"],
        "/api/v1/sources": {"get": op("List sources", schema={"type": "array"})},
        "/api/v1/sources/{slug}": {"get": op("Get a source", params=source)},
        "/api/v1/connections": {
            "get": op("List connections", schema={"type": "array"})
        },
        "/api/v1/sources/{slug}/search": {
            "post": op(
                "Search rows, newest first",
                body=SEARCH_REQUEST,
                params=source,
                schema={
                    "type": "object",
                    "properties": {
                        "columns": {"type": "array", "items": OBJ},
                        "rows": {"type": "array", "items": OBJ},
                        "cursor": {**OBJ, "nullable": True},
                        **DEBUG,
                    },
                },
            )
        },
        "/api/v1/sources/{slug}/chart": {
            "post": op(
                "Aggregate into a chart",
                body=CHART_REQUEST,
                params=source,
                schema={**OBJ, "properties": DEBUG},
            )
        },
    },
}
