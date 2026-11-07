# Telescope MCP server

Telescope serves a [Model Context Protocol](https://modelcontextprotocol.io/) server at `/api/mcp`
(streamable HTTP, stateless, JSON responses). It authenticates with a personal API token
(Profile, `/profile`, "New API token"), sent as `Authorization: Bearer <token>` or `Authorization: Token <token>`,
and every tool checks the same permissions as the UI and `/api/v1`.

## Connect

```bash
claude mcp add --transport http telescope https://telescope.example.com/api/mcp \
  --header "Authorization: Bearer <token>"
```

Other clients take the same URL and header. To inspect it:

```bash
npx @modelcontextprotocol/inspector --cli https://telescope.example.com/api/mcp --transport http \
  --header "Authorization: Bearer <token>" --method tools/list
```

## Tools

| Tool | Hint | What |
|---|---|---|
| `list_sources` | read-only | Sources you can read, with your permissions. |
| `describe_source` | read-only | Columns and types, time/severity columns, defaults, OTel roles. Needs `read`. |
| `search` | read-only | Rows for a FlyQL query, as `POST /api/v1/sources/<slug>/search`; at most 200 per call, paged with `before`. Needs `use` (`raw_query` needs raw query rights). |
| `chart` | read-only | Time series, number or grouped table, as `POST /api/v1/sources/<slug>/chart`. Needs `use`. |
| `get_trace` | read-only | One trace from an OTel traces source as a span tree. Needs `use`. |
| `list_dashboards`, `get_dashboard` | read-only | As `GET /api/v1/dashboards[/<slug>]`. |
| `upsert_tile` | write | Adds a tile, or replaces fields of the tile with that id; validated like a dashboard save. Needs edit rights. |
| `list_alerts` | read-only | Alerts on sources you can use, optionally one dashboard's tile alerts. |

Responses over 50,000 characters lose items from their largest list and carry a `trimmed` note
(`field`, `returned`, `total`); a trimmed search drops its `cursor`. Queries are tagged
`{"surface":"mcp"}` in `system.query_log.log_comment`, and calls share the API v2 rate limit.
A JSON-RPC batch (protocol 2025-03-26) takes at most 20 messages, each counted against that limit.
